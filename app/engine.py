import json, os, smtplib, logging, hashlib
from datetime import datetime, timedelta, date, time, timezone
from email.message import EmailMessage
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .models import Profile, Member, Medication, Dose, Appointment, CareTask, Audit, Notification

log = logging.getLogger("mitracare")
GRACE_MINUTES = 60

def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)

def profile_zone(profile: Profile):
    try: return ZoneInfo(profile.timezone)
    except ZoneInfoNotFoundError: return ZoneInfo("UTC")

def audit(db: Session, profile_id: int, actor_id: int, action: str, detail: str):
    db.add(Audit(profile_id=profile_id, actor_id=actor_id, action=action, detail=detail[:240]))

def queue_notification(
    db: Session,
    profile: Profile,
    key: str,
    kind: str,
    subject: str,
    body: str,
    *,
    known_keys: set[str] | None = None,
    email_addresses: list[str] | None = None,
) -> bool:
    """Queue one deduplicated in-app event and its optional email fan-out.

    The optional per-cycle caches let the reminder worker perform bounded,
    batched reads instead of querying once per event. Other callers can omit
    them and retain the safe single-event behaviour.
    """
    if known_keys is None:
        if db.query(Notification.id).filter_by(dedupe_key=key).first():
            return False
    else:
        if key in known_keys:
            return False
        # Track newly queued keys immediately; multiple events can be processed
        # before the transaction is flushed.
        known_keys.add(key)

    db.add(
        Notification(
            profile_id=profile.id,
            dedupe_key=key,
            kind=kind,
            subject=subject,
            body=body,
            recipient="",
            status="in_app",
        )
    )
    if email_addresses is None:
        recipients = db.query(Member).filter(
            Member.profile_id == profile.id,
            Member.active.is_(True),
            Member.email != "",
        ).all()
        addresses = sorted({m.email.strip().lower() for m in recipients if m.email.strip()})
    else:
        addresses = email_addresses

    for address in addresses:
        recipient_key = hashlib.sha256(address.encode("utf-8")).hexdigest()[:20]
        db.add(
            Notification(
                profile_id=profile.id,
                dedupe_key=f"{key}:email:{recipient_key}",
                kind=kind,
                subject=subject,
                body=body,
                recipient=address,
                status="queued",
            )
        )
    return True

def materialize_doses(db: Session, profile: Profile, now: datetime | None = None) -> int:
    """Materialize a bounded 15-day schedule window with one existing-event query."""
    now = as_utc(now or datetime.now(timezone.utc))
    zone = profile_zone(profile)
    local_today = now.astimezone(zone).date()
    meds = db.query(Medication).filter_by(profile_id=profile.id, active=True).all()
    if not meds:
        return 0

    # Every eligible schedule lies inside this local-date window. Fetch all
    # existing events once rather than issuing a SELECT for every medication
    # and time slot (the previous implementation had an N+1 query pattern).
    medication_ids = [med.id for med in meds]
    window_start = datetime.combine(local_today - timedelta(days=7), time.min, tzinfo=zone)
    window_end = datetime.combine(local_today + timedelta(days=8), time.min, tzinfo=zone)
    existing_rows = db.query(Dose.medication_id, Dose.scheduled_at).filter(
        Dose.profile_id == profile.id,
        Dose.medication_id.in_(medication_ids),
        Dose.scheduled_at >= window_start.astimezone(timezone.utc),
        Dose.scheduled_at < window_end.astimezone(timezone.utc),
    ).all()
    existing = {(medication_id, as_utc(scheduled_at)) for medication_id, scheduled_at in existing_rows}

    made = 0
    for med in meds:
        start = date.fromisoformat(med.start_date)
        end = date.fromisoformat(med.end_date) if med.end_date else local_today + timedelta(days=7)
        first = max(start, local_today - timedelta(days=7))
        last = min(end, local_today + timedelta(days=7))
        if last < first:
            continue
        for day_offset in range((last - first).days + 1):
            day = first + timedelta(days=day_offset)
            for hhmm in json.loads(med.times_json):
                hh, mm = map(int, hhmm.split(":"))
                scheduled = datetime.combine(day, time(hh, mm), tzinfo=zone).astimezone(timezone.utc)
                key = (med.id, scheduled)
                if key not in existing:
                    db.add(
                        Dose(
                            profile_id=profile.id,
                            medication_id=med.id,
                            scheduled_at=scheduled,
                            status="pending",
                        )
                    )
                    existing.add(key)
                    made += 1
    if made:
        db.flush()
    return made

def process_reminders(db: Session, profile: Profile, now: datetime | None = None):
    """Evaluate due reminders using batched reads and idempotent keys."""
    now = as_utc(now or datetime.now(timezone.utc))
    materialize_doses(db, profile, now)
    zone = profile_zone(profile)

    # Limit pending-dose work to events that can notify during this cycle.
    doses = db.query(Dose).filter(
        Dose.profile_id == profile.id,
        Dose.status == "pending",
        Dose.scheduled_at <= now + timedelta(minutes=15),
    ).all()
    medication_ids = {dose.medication_id for dose in doses}
    medications = db.query(Medication).filter(
        Medication.profile_id == profile.id,
        Medication.id.in_(medication_ids),
    ).all() if medication_ids else []
    medication_by_id = {med.id: med for med in medications}

    active_members = db.query(Member).filter(
        Member.profile_id == profile.id,
        Member.active.is_(True),
    ).all()
    people_by_id = {person.id: person for person in active_members}
    email_addresses = sorted({
        person.email.strip().lower()
        for person in active_members
        if person.email and person.email.strip()
    })

    appointments = db.query(Appointment).filter(
        Appointment.profile_id == profile.id,
        Appointment.starts_at >= now,
        Appointment.starts_at <= now + timedelta(hours=25),
    ).all()
    open_tasks = db.query(CareTask).filter_by(
        profile_id=profile.id,
        status="open",
    ).filter(CareTask.due_at.is_not(None)).all()

    # Build only the dedupe keys this cycle may emit; fetching the entire
    # notification history on every minute tick would itself grow unbounded.
    candidate_keys: set[str] = set()
    for dose in doses:
        due = as_utc(dose.scheduled_at)
        if now >= due + timedelta(minutes=GRACE_MINUTES):
            candidate_keys.add(f"dose:missed:{dose.id}")
        elif timedelta(0) <= due - now <= timedelta(minutes=15):
            candidate_keys.add(f"dose:upcoming:{dose.id}")
    for appointment in appointments:
        lead = as_utc(appointment.starts_at) - now
        if timedelta(hours=23, minutes=45) <= lead <= timedelta(hours=24, minutes=15):
            candidate_keys.add(f"appointment:24h:{appointment.id}")
        if timedelta(minutes=45) <= lead <= timedelta(hours=1, minutes=15):
            candidate_keys.add(f"appointment:1h:{appointment.id}")
    for task in open_tasks:
        task_due = as_utc(task.due_at)
        if timedelta(0) <= task_due - now <= timedelta(minutes=60):
            candidate_keys.add(f"care_task:due:{task.id}")
        elif now >= task_due + timedelta(minutes=60):
            candidate_keys.add(f"care_task:overdue:{task.id}")

    known_keys = set()
    if candidate_keys:
        rows = db.query(Notification.dedupe_key).filter(
            Notification.profile_id == profile.id,
            Notification.dedupe_key.in_(candidate_keys),
        ).all()
        known_keys = {row[0] for row in rows}

    for dose in doses:
        due = as_utc(dose.scheduled_at)
        med = medication_by_id.get(dose.medication_id)
        if not med:
            continue
        if not med.active:
            dose.status = "superseded"
            continue
        if now >= due + timedelta(minutes=GRACE_MINUTES):
            dose.status = "missed"
            queue_notification(
                db, profile, f"dose:missed:{dose.id}", "missed_dose",
                f"Missed dose check-in: {med.name}",
                f"A scheduled dose of {med.name} ({med.strength}) was not marked taken "
                f"within the {GRACE_MINUTES}-minute check-in window. Please check in with "
                "the patient. Do not double a dose; follow the prescribing clinician's instructions.",
                known_keys=known_keys, email_addresses=email_addresses,
            )
            audit(db, profile.id, None, "dose_missed", f"Dose #{dose.id} moved to missed after grace window")
        elif timedelta(0) <= due - now <= timedelta(minutes=15):
            queue_notification(
                db, profile, f"dose:upcoming:{dose.id}", "upcoming_dose",
                f"Upcoming medication: {med.name}",
                f"{med.name} ({med.strength}) is scheduled in about 15 minutes. This is a "
                "reminder only; follow the prescription label and clinician's instructions.",
                known_keys=known_keys, email_addresses=email_addresses,
            )

    for appointment in appointments:
        starts = as_utc(appointment.starts_at)
        lead = starts - now
        local_starts = starts.astimezone(zone)
        if timedelta(hours=23, minutes=45) <= lead <= timedelta(hours=24, minutes=15):
            queue_notification(
                db, profile, f"appointment:24h:{appointment.id}", "appointment",
                f"Tomorrow: appointment with {appointment.clinician}",
                f"Appointment at {local_starts.strftime('%a, %d %b %Y, %I:%M %p')} "
                f"({profile.timezone}). Location: {appointment.location or 'Not specified'}.",
                known_keys=known_keys, email_addresses=email_addresses,
            )
        if timedelta(minutes=45) <= lead <= timedelta(hours=1, minutes=15):
            queue_notification(
                db, profile, f"appointment:1h:{appointment.id}", "appointment",
                f"Appointment in about one hour: {appointment.clinician}",
                f"Appointment at {local_starts.strftime('%a, %d %b %Y, %I:%M %p')} "
                f"({profile.timezone}). Location: {appointment.location or 'Not specified'}.",
                known_keys=known_keys, email_addresses=email_addresses,
            )

    for care_task in open_tasks:
        task_due = as_utc(care_task.due_at)
        assignee = people_by_id.get(care_task.assigned_to)
        owner = assignee.name if assignee else "the care circle"
        if timedelta(0) <= task_due - now <= timedelta(minutes=60):
            queue_notification(
                db, profile, f"care_task:due:{care_task.id}", "care_task_due",
                f"Follow-up due soon: {care_task.title}",
                f"The coordination follow-up '{care_task.title}' is due at "
                f"{task_due.astimezone(zone).strftime('%a, %d %b %I:%M %p')}. "
                f"Assigned to: {owner}. Update it in Care Tasks.",
                known_keys=known_keys, email_addresses=email_addresses,
            )
        elif now >= task_due + timedelta(minutes=60):
            queue_notification(
                db, profile, f"care_task:overdue:{care_task.id}", "care_task_overdue",
                f"Follow-up is overdue: {care_task.title}",
                f"The coordination follow-up '{care_task.title}' is past its due time. "
                f"Assigned to: {owner}. Review it in Care Tasks.",
                known_keys=known_keys, email_addresses=email_addresses,
            )
    db.commit()

def deliver_pending(db: Session):
    host = os.getenv("SMTP_HOST"); user = os.getenv("SMTP_USER"); password = os.getenv("SMTP_PASSWORD")
    if not (host and user and password): return 0
    port = int(os.getenv("SMTP_PORT", "587")); sender = os.getenv("SMTP_FROM", user)
    now = datetime.now(timezone.utc)
    rows = db.query(Notification).filter(
        Notification.status.in_(["queued", "retrying"]),
        Notification.recipient != "",
    ).order_by(Notification.id).limit(50).all()
    sent = 0
    for row in rows:
        if row.next_attempt_at and as_utc(row.next_attempt_at) > now: continue
        try:
            msg = EmailMessage(); msg["Subject"] = row.subject; msg["From"] = sender; msg["To"] = row.recipient
            msg.set_content(row.body + "\n\nMitraCare is a coordination tool, not a source of medical advice.")
            with smtplib.SMTP(host, port, timeout=8) as smtp:
                smtp.starttls(); smtp.login(user, password); smtp.send_message(msg)
            row.status = "sent"; row.sent_at = now; row.last_error = ""; sent += 1
        except Exception as exc:
            row.attempts += 1
            row.last_error = type(exc).__name__
            if row.attempts >= 3:
                row.status = "failed"; row.next_attempt_at = None
            else:
                row.status = "retrying"
                row.next_attempt_at = now + timedelta(seconds=[60, 300, 900][row.attempts-1])
            log.warning("Email delivery attempt %s failed for notification %s: %s", row.attempts, row.id, type(exc).__name__)
    db.commit()
    return sent

def care_insights(db: Session, profile: Profile, now: datetime | None = None):
    """Explainable, descriptive routine signals; never predicts or advises clinical treatment."""
    now = as_utc(now or datetime.now(timezone.utc))
    zone = profile_zone(profile)
    rows = db.query(Dose).filter(
        Dose.profile_id == profile.id,
        Dose.scheduled_at >= now - timedelta(days=14),
        Dose.scheduled_at <= now,
        Dose.status.in_(["taken", "skipped", "missed"]),
    ).all()
    buckets = {"Morning": [], "Afternoon": [], "Evening": [], "Night": []}
    for row in rows:
        hour = as_utc(row.scheduled_at).astimezone(zone).hour
        key = "Morning" if 5 <= hour < 12 else "Afternoon" if 12 <= hour < 17 else "Evening" if 17 <= hour < 22 else "Night"
        buckets[key].append(row.status)
    signals = []
    for period, statuses in buckets.items():
        if len(statuses) >= 4:
            taken = statuses.count("taken")
            other = len(statuses) - taken
            ratio = other / len(statuses)
            if ratio >= 0.4:
                signals.append({
                    "title": f"{period.lower()} check-ins may need a closer look",
                    "detail": f"{taken} of {len(statuses)} scheduled {period.lower()} check-ins were marked taken in the last 14 days.",
                    "action": "Ask the patient whether this time of day is inconvenient, whether reminders are reaching them, or whether the record simply was not updated.",
                    "evidence": {"period": period, "taken": taken, "recorded": len(statuses), "window_days": 14},
                    "method": "Transparent time-of-day aggregation; shown only with at least 4 recorded events and at least 40% not marked taken.",
                })
    if not signals:
        signals.append({
            "title": "No clear routine friction pattern yet",
            "detail": f"{len(rows)} check-ins have been recorded in the last 14 days. More observations may be needed before a time-of-day pattern is useful.",
            "action": "Keep recording check-ins and ask the patient what kind of reminders feel helpful.",
            "evidence": {"recorded_events": len(rows), "window_days": 14},
            "method": "Rules-based descriptive analysis; no clinical prediction or treatment recommendation.",
        })
    return signals
