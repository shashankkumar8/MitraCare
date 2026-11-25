import asyncio, json, secrets, string, os, logging, hashlib
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, Response
import httpx
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc
from .database import Base, make_database
from .models import Profile, Member, Session as LoginSession, AuthAttempt, Invite, Medication, Dose, Appointment, CareTask, Audit, Notification
from .schemas import CreateProfile, Login, InviteCreate, JoinInvite, MedicationCreate, DoseAction, AppointmentCreate, CareTaskCreate, TaskCoachRequest
from .security import COOKIE, hash_secret, verify_secret, token_digest, create_session, current_member, require_write, pin_valid
from .engine import audit, materialize_doses, process_reminders, deliver_pending, as_utc, care_insights

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
ROOT = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(app.state.engine)
    task = asyncio.create_task(reminder_worker(app))
    yield
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass

app = FastAPI(title="MitraCare API", version="1.0.0", description="Patient-first shared medication and appointment coordination", lifespan=lifespan)
app.state.engine, app.state.SessionLocal = make_database()
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

def get_db():
    db = app.state.SessionLocal()
    try: yield db
    finally: db.close()

def auth(request: Request, db: DBSession = Depends(get_db)):
    member, _ = current_member(request, db)
    profile = db.get(Profile, member.profile_id)
    if not profile: raise HTTPException(401, "Care profile not found.")
    return member, profile

def set_login(response: Response, token: str):
    response.set_cookie(COOKIE, token, httponly=True, secure=os.getenv("COOKIE_SECURE", "false").lower() == "true", samesite="strict", max_age=43200, path="/")

def profile_payload(profile, member):
    return {"profile": {"id": profile.id, "name": profile.name, "timezone": profile.timezone, "code": profile.code}, "member": {"id": member.id, "name": member.name, "role": member.role, "email": member.email}}

@app.middleware("http")
async def harden_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api") else "no-cache"
    return response

@app.get("/")
def home(): return FileResponse(ROOT / "static" / "index.html")

@app.get("/api/health")
def health(): return {"status": "ok", "service": "mitracare", "version": "1.0.0"}

@app.post("/api/profiles", status_code=201)
def create_profile(data: CreateProfile, response: Response, db: DBSession = Depends(get_db)):
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try: ZoneInfo(data.timezone)
    except ZoneInfoNotFoundError: raise HTTPException(422, "Choose a valid timezone.")
    if data.email and "@" not in data.email: raise HTTPException(422, "Enter a valid email address.")
    code = "MT" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(7))
    profile = Profile(code=code, name=data.name.strip(), timezone=data.timezone)
    db.add(profile); db.flush()
    owner = Member(profile_id=profile.id, name=data.name.strip(), email=data.email.strip().lower(), role="patient", pin_hash=hash_secret(data.pin))
    db.add(owner); db.commit(); db.refresh(profile); db.refresh(owner)
    set_login(response, create_session(db, owner))
    audit(db, profile.id, owner.id, "profile_created", "Patient created a care profile")
    db.commit()
    return {**profile_payload(profile, owner), "profile_code": code, "message": "Save this profile code; it is needed with your PIN to sign in."}

@app.post("/api/auth/login")
def login(data: Login, request: Request, response: Response, db: DBSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    peer = request.client.host if request.client else "unknown"
    attempt_key = hashlib.sha256(f"{data.profile_code.strip().upper()}|{peer}".encode()).hexdigest()
    attempt = db.query(AuthAttempt).filter_by(key_hash=attempt_key).first()
    if attempt and attempt.locked_until and as_utc(attempt.locked_until) > now:
        raise HTTPException(429, "Too many attempts. Try again in 10 minutes.")
    profile = db.query(Profile).filter_by(code=data.profile_code.strip().upper()).first()
    members = db.query(Member).filter_by(profile_id=profile.id, active=True).all() if profile else []
    member = next((m for m in members if verify_secret(data.pin, m.pin_hash)), None)
    if not member:
        if not attempt:
            attempt = AuthAttempt(key_hash=attempt_key, failed_count=1, first_failed_at=now)
            db.add(attempt)
        else:
            if now - as_utc(attempt.first_failed_at) > timedelta(minutes=10):
                attempt.failed_count = 1; attempt.first_failed_at = now; attempt.locked_until = None
            else:
                attempt.failed_count += 1
            if attempt.failed_count >= 5: attempt.locked_until = now + timedelta(minutes=10)
        db.commit()
        raise HTTPException(401, "Profile code or PIN is incorrect.")
    if attempt: db.delete(attempt); db.commit()
    set_login(response, create_session(db, member))
    return profile_payload(profile, member)

@app.post("/api/auth/join")
def join(data: JoinInvite, response: Response, db: DBSession = Depends(get_db)):
    invite = db.query(Invite).filter_by(code_hash=token_digest(data.invite_code.strip().upper())).first()
    now = datetime.now(timezone.utc)
    if not invite or invite.used_at or as_utc(invite.expires_at) < now:
        raise HTTPException(400, "Invite is invalid, expired, or already used.")
    if data.email and "@" not in data.email: raise HTTPException(422, "Enter a valid email address.")
    member = Member(profile_id=invite.profile_id, name=data.name.strip(), email=data.email.strip().lower(), role=invite.role, pin_hash=hash_secret(data.pin))
    invite.used_at = now; db.add(member); db.flush()
    audit(db, invite.profile_id, invite.created_by, "member_joined", f"{data.name.strip()} joined as {invite.role}")
    db.commit(); db.refresh(member)
    profile = db.get(Profile, invite.profile_id)
    set_login(response, create_session(db, member))
    return profile_payload(profile, member)

@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db: DBSession = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if token: db.query(LoginSession).filter_by(token_hash=token_digest(token)).delete(); db.commit()
    response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
    return {"ok": True}

@app.get("/api/me")
def me(ctx=Depends(auth)):
    member, profile = ctx
    return profile_payload(profile, member)

@app.post("/api/invites", status_code=201)
def create_invite(data: InviteCreate, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    if member.role != "patient": raise HTTPException(403, "Only the patient can invite care-circle members.")
    if data.email and "@" not in data.email: raise HTTPException(422, "Enter a valid email address.")
    code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    inv = Invite(profile_id=profile.id, code_hash=token_digest(code), role=data.role, created_by=member.id, expires_at=datetime.now(timezone.utc)+timedelta(hours=24))
    db.add(inv); audit(db, profile.id, member.id, "invite_created", f"Invited {data.name} as {data.role}"); db.commit()
    return {"invite_code": code, "role": data.role, "expires_in_hours": 24, "share_message": f"Join {profile.name}'s MitraCare circle. Use invite code {code} and create your own 6–8 digit PIN. Expires in 24 hours."}

@app.get("/api/members")
def members(ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    rows = db.query(Member).filter_by(profile_id=profile.id, active=True).order_by(Member.id).all()
    return [{"id": m.id, "name": m.name, "role": m.role, "email": m.email} for m in rows]

@app.post("/api/medications", status_code=201)
def add_medication(data: MedicationCreate, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx; require_write(member)
    if data.end_date and data.end_date < data.start_date: raise HTTPException(422, "End date cannot be before start date.")
    if len(data.times) != len(set(data.times)): raise HTTPException(422, "Remove duplicate schedule times.")
    med = Medication(profile_id=profile.id, name=data.name.strip(), strength=data.strength.strip(), instructions=data.instructions.strip(), route=data.route, times_json=json.dumps(data.times), start_date=data.start_date, end_date=data.end_date, prescriber=data.prescriber.strip(), created_by=member.id)
    db.add(med); db.flush(); materialize_doses(db, profile)
    audit(db, profile.id, member.id, "medication_added", f"Added medication schedule: {med.name}"); db.commit(); db.refresh(med)
    return medication_json(med)

def medication_json(m):
    return {"id": m.id, "name": m.name, "strength": m.strength, "instructions": m.instructions, "route": m.route, "times": json.loads(m.times_json), "start_date": m.start_date, "end_date": m.end_date, "prescriber": m.prescriber, "active": m.active}

@app.get("/api/medications")
def medications(ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    return [medication_json(m) for m in db.query(Medication).filter_by(profile_id=profile.id).order_by(desc(Medication.active), Medication.name).all()]

@app.put("/api/medications/{med_id}")
def update_medication(med_id: int, data: MedicationCreate, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx; require_write(member)
    med = db.query(Medication).filter_by(id=med_id, profile_id=profile.id).first()
    if not med: raise HTTPException(404, "Medication not found.")
    if not med.active: raise HTTPException(409, "This schedule is paused. Add a new verified schedule instead.")
    if data.end_date and data.end_date < data.start_date: raise HTTPException(422, "End date cannot be before start date.")
    med.name = data.name.strip(); med.strength = data.strength.strip(); med.instructions = data.instructions.strip()
    med.route = data.route; med.times_json = json.dumps(data.times); med.start_date = data.start_date
    med.end_date = data.end_date; med.prescriber = data.prescriber.strip()
    materialize_doses(db, profile)
    from zoneinfo import ZoneInfo
    zone = ZoneInfo(profile.timezone); allowed = set(data.times)
    for dose in db.query(Dose).filter_by(profile_id=profile.id, medication_id=med.id, status="pending").all():
        local = as_utc(dose.scheduled_at).astimezone(zone)
        local_day = local.date().isoformat()
        valid_day = local_day >= data.start_date and (not data.end_date or local_day <= data.end_date)
        if not valid_day or local.strftime("%H:%M") not in allowed:
            dose.status = "superseded"
    audit(db, profile.id, member.id, "medication_updated", f"Updated verified medication schedule: {med.name}")
    db.commit(); db.refresh(med)
    return medication_json(med)

@app.patch("/api/medications/{med_id}/deactivate")
def deactivate_medication(med_id: int, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx; require_write(member)
    med = db.query(Medication).filter_by(id=med_id, profile_id=profile.id).first()
    if not med: raise HTTPException(404, "Medication not found.")
    if med.active:
        med.active = False
        now = datetime.now(timezone.utc)
        for dose in db.query(Dose).filter_by(profile_id=profile.id, medication_id=med.id, status="pending").all():
            if as_utc(dose.scheduled_at) >= now: dose.status = "superseded"
        audit(db, profile.id, member.id, "medication_deactivated", f"Deactivated medication: {med.name}"); db.commit()
    return {"ok": True, "medication": medication_json(med)}

@app.get("/api/dashboard")
def dashboard(ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    process_reminders(db, profile)
    now = datetime.now(timezone.utc)
    zone = ZoneInfo(profile.timezone)
    start = now - timedelta(days=7)
    recent = db.query(Dose).filter(Dose.profile_id == profile.id, Dose.scheduled_at >= start, Dose.scheduled_at <= now+timedelta(days=1)).all()
    total = sum(d.status in ("taken", "skipped", "missed") for d in recent)
    taken = sum(d.status == "taken" for d in recent)
    adherence = round(taken / total * 100) if total else None
    next_doses = db.query(Dose).filter(Dose.profile_id == profile.id, Dose.scheduled_at >= now-timedelta(hours=1), Dose.status != "superseded").order_by(Dose.scheduled_at).limit(40).all()
    meds = {m.id: m for m in db.query(Medication).filter_by(profile_id=profile.id).all()}
    dose_rows = []
    for d in next_doses:
        med = meds.get(d.medication_id)
        if med:
            when = as_utc(d.scheduled_at)
            dose_rows.append({"id": d.id, "medication_id": med.id, "medication": med.name, "strength": med.strength, "instructions": med.instructions, "scheduled_at": when.isoformat(), "local_time": when.astimezone(zone).strftime("%a, %d %b · %I:%M %p"), "status": "due" if d.status == "pending" and when <= now else d.status})
    upcoming_appts = db.query(Appointment).filter(Appointment.profile_id == profile.id, Appointment.starts_at >= now-timedelta(hours=2)).order_by(Appointment.starts_at).limit(8).all()
    appt_rows = [{"id": a.id, "clinician": a.clinician, "location": a.location, "starts_at": as_utc(a.starts_at).isoformat(), "local_time": as_utc(a.starts_at).astimezone(zone).strftime("%a, %d %b · %I:%M %p"), "local_day": as_utc(a.starts_at).astimezone(zone).strftime("%d"), "local_month": as_utc(a.starts_at).astimezone(zone).strftime("%b"), "notes": a.notes} for a in upcoming_appts]
    missed = sum(d.status == "missed" for d in recent)
    pending_alerts = db.query(Notification).filter_by(profile_id=profile.id, recipient="").order_by(desc(Notification.created_at)).limit(12).all()
    email_count = db.query(Member).filter(Member.profile_id == profile.id, Member.active == True, Member.email != "").count()
    email_ready = bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD") and email_count > 0)
    return {"profile": profile.name, "timezone": profile.timezone, "adherence_7d": adherence, "taken_7d": taken, "recorded_7d": total, "missed_7d": missed, "doses": dose_rows, "appointments": appt_rows, "notifications": [notification_json(n) for n in pending_alerts], "email_configured": email_ready, "email_recipients": email_count, "role": member.role}

@app.post("/api/doses/{dose_id}/mark")
def mark_dose(dose_id: int, data: DoseAction, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx; require_write(member)
    dose = db.query(Dose).filter_by(id=dose_id, profile_id=profile.id).first()
    if not dose: raise HTTPException(404, "Dose event not found.")
    if dose.status != "pending": raise HTTPException(409, f"This dose is already recorded as {dose.status}. Changes are locked to preserve the audit trail.")
    dose.status = data.action; dose.action_by = member.id; dose.action_at = datetime.now(timezone.utc); dose.note = data.note.strip()
    med = db.get(Medication, dose.medication_id)
    audit(db, profile.id, member.id, f"dose_{data.action}", f"{med.name if med else 'Medication'} dose #{dose.id} marked {data.action}")
    db.commit()
    return {"ok": True, "status": dose.status, "message": "Dose status saved. This record does not advise taking, skipping, or repeating a dose."}

@app.post("/api/appointments", status_code=201)
def add_appointment(data: AppointmentCreate, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx; require_write(member)
    starts = data.starts_at
    if starts.tzinfo is None: starts = starts.replace(tzinfo=ZoneInfo(profile.timezone))
    if starts.astimezone(timezone.utc) < datetime.now(timezone.utc)-timedelta(minutes=5): raise HTTPException(422, "Appointment must be in the future.")
    appt = Appointment(profile_id=profile.id, clinician=data.clinician.strip(), location=data.location.strip(), starts_at=starts.astimezone(timezone.utc), notes=data.notes.strip(), created_by=member.id)
    db.add(appt); db.flush(); audit(db, profile.id, member.id, "appointment_added", f"Added appointment with {appt.clinician}"); db.commit()
    return {"id": appt.id, "clinician": appt.clinician, "location": appt.location, "starts_at": as_utc(appt.starts_at).isoformat()}

@app.get("/api/appointments")
def appointments(ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    zone = ZoneInfo(profile.timezone)
    return [{"id": a.id, "clinician": a.clinician, "location": a.location, "starts_at": as_utc(a.starts_at).isoformat(), "local_time": as_utc(a.starts_at).astimezone(zone).strftime("%a, %d %b · %I:%M %p"), "local_day": as_utc(a.starts_at).astimezone(zone).strftime("%d"), "local_month": as_utc(a.starts_at).astimezone(zone).strftime("%b"), "notes": a.notes} for a in db.query(Appointment).filter_by(profile_id=profile.id).order_by(Appointment.starts_at).all()]

@app.post("/api/appointments/{appointment_id}/prep-kit", status_code=201)
def create_appointment_prep_kit(appointment_id: int, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    """Create an idempotent, non-clinical preparation checklist for a future appointment."""
    member, profile = ctx
    require_write(member)
    appointment = db.query(Appointment).filter_by(id=appointment_id, profile_id=profile.id).first()
    if not appointment:
        raise HTTPException(404, "Appointment not found in this care profile.")
    now = datetime.now(timezone.utc)
    starts_at = as_utc(appointment.starts_at)
    if starts_at <= now:
        raise HTTPException(409, "Visit preparation is available only for a future appointment.")

    marker = f"[visit-prep:{appointment.id}]"
    existing = db.query(CareTask).filter(
        CareTask.profile_id == profile.id,
        CareTask.description.like(f"%{marker}%"),
    ).order_by(CareTask.id).all()
    people = {m.id: m for m in db.query(Member).filter_by(profile_id=profile.id).all()}
    if existing:
        return {
            "created": False,
            "count": len(existing),
            "tasks": [task_json(task, people, profile) for task in existing],
            "message": "A preparation kit already exists for this visit. Existing tasks were returned.",
        }

    due_at = starts_at - timedelta(hours=2)
    if due_at < now:
        due_at = now
    items = [
        ("Visit prep · Confirm the details",
         "Confirm the appointment date, time, clinician and venue with the appointment contact.",
         "appointment"),
        ("Visit prep · Gather requested records",
         "Collect reports, documents or records the clinician has asked the patient to bring.",
         "appointment"),
        ("Visit prep · Arrange transport and a companion",
         "Confirm pickup, return arrangements and who will accompany the patient.",
         "transport"),
        ("Visit prep · Prepare questions for the clinician",
         "Write down questions for the visit. Ask the clinician about any care or medicine changes.",
         "follow_up"),
    ]
    created = []
    for title, description, category in items:
        task = CareTask(
            profile_id=profile.id,
            title=title,
            description=f"{description} {marker}",
            category=category,
            due_at=due_at,
            assigned_to=member.id,
            created_by=member.id,
            status="open",
        )
        db.add(task)
        created.append(task)
    db.flush()
    audit(db, profile.id, member.id, "appointment_prep_kit_created",
          f"Created four-item preparation kit for appointment #{appointment.id}")
    db.commit()
    for task in created:
        db.refresh(task)
    return {
        "created": True,
        "count": len(created),
        "tasks": [task_json(task, people, profile) for task in created],
        "message": "Four practical preparation tasks were assigned to you in Care Tasks.",
    }



def task_json(task: CareTask, people: dict[int, Member], profile: Profile):
    zone = ZoneInfo(profile.timezone)
    due = as_utc(task.due_at) if task.due_at else None
    completed = as_utc(task.completed_at) if task.completed_at else None
    assignee = people.get(task.assigned_to) if task.assigned_to else None
    actor = people.get(task.completed_by) if task.completed_by else None
    return {
        "id": task.id, "title": task.title, "description": task.description,
        "category": task.category, "status": task.status, "assigned_to": task.assigned_to,
        "assignee_name": assignee.name if assignee else "", "created_by": task.created_by,
        "completed_by": task.completed_by, "completed_by_name": actor.name if actor else "",
        "due_at": due.isoformat() if due else None,
        "due_local": due.astimezone(zone).strftime("%a, %d %b · %I:%M %p") if due else "",
        "completed_at": completed.isoformat() if completed else None,
        "created_at": as_utc(task.created_at).isoformat(),
    }


@app.get("/api/tasks")
def list_tasks(ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    rows = db.query(CareTask).filter_by(profile_id=profile.id).order_by(CareTask.status, CareTask.due_at, CareTask.id.desc()).limit(100).all()
    people = {m.id: m for m in db.query(Member).filter_by(profile_id=profile.id).all()}
    return [task_json(row, people, profile) for row in rows]


@app.post("/api/tasks", status_code=201)
def create_task(data: CareTaskCreate, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    require_write(member)
    assignee = None
    if data.assigned_to is not None:
        assignee = db.query(Member).filter_by(id=data.assigned_to, profile_id=profile.id, active=True).first()
        if not assignee or assignee.role == "family":
            raise HTTPException(422, "Choose an active patient or caregiver in this care circle.")
    due = data.due_at
    if due is not None:
        if due.tzinfo is None:
            due = due.replace(tzinfo=ZoneInfo(profile.timezone))
        due = due.astimezone(timezone.utc)
    task = CareTask(profile_id=profile.id, title=data.title.strip(), description=data.description.strip(),
                    category=data.category, due_at=due, assigned_to=assignee.id if assignee else None,
                    created_by=member.id, status="open")
    db.add(task)
    db.flush()
    audit(db, profile.id, member.id, "care_task_created", f"Created care follow-up: {task.title}")
    db.commit()
    db.refresh(task)
    people = {m.id: m for m in db.query(Member).filter_by(profile_id=profile.id).all()}
    return task_json(task, people, profile)


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: int, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    require_write(member)
    task = db.query(CareTask).filter_by(id=task_id, profile_id=profile.id).first()
    if not task:
        raise HTTPException(404, "Care task not found.")
    if task.status != "open":
        raise HTTPException(409, "This follow-up is already completed.")
    task.status = "completed"
    task.completed_by = member.id
    task.completed_at = datetime.now(timezone.utc)
    audit(db, profile.id, member.id, "care_task_completed", f"Completed care follow-up: {task.title}")
    db.commit()
    people = {m.id: m for m in db.query(Member).filter_by(profile_id=profile.id).all()}
    return task_json(task, people, profile)


@app.post("/api/tasks/{task_id}/reopen")
def reopen_task(task_id: int, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    require_write(member)
    task = db.query(CareTask).filter_by(id=task_id, profile_id=profile.id).first()
    if not task:
        raise HTTPException(404, "Care task not found.")
    if task.status != "completed":
        raise HTTPException(409, "Only a completed follow-up can be reopened.")
    task.status = "open"
    task.completed_by = None
    task.completed_at = None
    audit(db, profile.id, member.id, "care_task_reopened", f"Reopened care follow-up: {task.title}")
    db.commit()
    people = {m.id: m for m in db.query(Member).filter_by(profile_id=profile.id).all()}
    return task_json(task, people, profile)


@app.delete("/api/members/{member_id}")
def revoke_member_access(member_id: int, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    if member.role != "patient":
        raise HTTPException(403, "Only the patient can revoke care-circle access.")
    target = db.query(Member).filter_by(id=member_id, profile_id=profile.id, active=True).first()
    if not target or target.role == "patient" or target.id == member.id:
        raise HTTPException(404, "Care-circle member not found or cannot be removed.")
    target.active = False
    db.query(LoginSession).filter_by(member_id=target.id).delete(synchronize_session=False)
    audit(db, profile.id, member.id, "member_access_revoked", f"Revoked {target.role} access for {target.name}")
    db.commit()
    return {"ok": True, "message": f"Access revoked for {target.name}."}


@app.get("/api/task-coach")
def task_coach_config(ctx=Depends(auth)):
    member, profile = ctx
    return {
        "ai_available": bool(os.getenv("GEMINI_API_KEY")),
        "provider": "Google Gemini" if os.getenv("GEMINI_API_KEY") else None,
        "categories": ["appointment", "transport", "supplies", "follow_up", "other"],
        "privacy": "Only a fixed category label is sent to the optional AI provider. No profile, task title, notes, identity, medication or health details are transmitted.",
    }


@app.post("/api/task-coach")
async def task_coach(data: TaskCoachRequest, ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    require_write(member)
    if not data.consent:
        raise HTTPException(422, "Confirm consent before requesting a checklist.")
    templates = {
        "appointment": ["Confirm date, time and venue", "Check what documents or records to bring", "Arrange transport and an arrival contact", "Write down questions to discuss with the professional"],
        "transport": ["Confirm pickup time and address", "Agree who will accompany the person", "Check return-trip arrangements", "Share the plan with invited care-circle members"],
        "supplies": ["Check the item and quantity needed", "Confirm who will collect or order it", "Agree a completion date", "Tell the care circle when it is ready"],
        "follow_up": ["Confirm the person responsible", "Agree the next contact date", "Record the agreed outcome", "Share an update with the care circle"],
        "other": ["Write the next action clearly", "Assign one responsible person", "Choose a realistic due time", "Share completion status with the care circle"],
    }
    result = {"mode": "template", "provider": None, "items": templates[data.category],
              "notice": "Starter checklist only. Review and adapt it; no personal or health information was used."}
    key = os.getenv("GEMINI_API_KEY")
    if key:
        recent = db.query(Audit).filter(
            Audit.profile_id == profile.id,
            Audit.actor_id == member.id,
            Audit.action == "task_coach_used",
            Audit.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
        ).count()
        if recent >= 10:
            raise HTTPException(429, "Task Coach is limited to 10 requests per member per 24 hours.")
        model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        prompt = (
            "Create exactly four concise, non-clinical household coordination checklist items. "
            "The only user input is a fixed category enum. Do not mention medicines, diagnoses, "
            "treatment, symptoms, risk, health advice or emergencies. Return four numbered items only. "
            "Category: " + data.category
        )
        body = {
            "model": model,
            "store": False,
            "input": [{"type": "user_input", "content": prompt}],
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(
                    "https://generativelanguage.googleapis.com/v1beta/interactions",
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=body)
                response.raise_for_status()
                payload = response.json()
            parts = [
                part for step in payload.get("steps", []) if step.get("type") == "model_output"
                for part in step.get("content", []) if part.get("type") == "text"
            ]
            generated = "\n".join(str(part.get("text", "")) for part in parts if part.get("text"))
            items = [line.strip().lstrip("0123456789.-• ").strip() for line in generated.splitlines() if line.strip()]
            items = [item[:140] for item in items if item][:4]
            blocked = ("medicine", "medication", "dose", "diagnos", "treatment", "symptom", "prescrib", "emergency", "clinical")
            if len(items) == 4 and not any(word in " ".join(items).lower() for word in blocked):
                result = {"mode": "gemini", "provider": "Google Gemini", "model": model, "items": items,
                          "notice": "AI-generated generic coordination suggestions. Review before using; no personal or health details were sent."}
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            result["mode"] = "template_fallback"
            result["notice"] = "The AI service was unavailable. Generic starter suggestions are shown instead."
    audit(db, profile.id, member.id, "task_coach_used", f"Used non-clinical task checklist for category: {data.category}")
    db.commit()
    return result


def notification_json(n):
    return {"id": n.id, "kind": n.kind, "subject": n.subject, "body": n.body, "status": n.status, "created_at": as_utc(n.created_at).isoformat()}

@app.get("/api/insights")
def insights(ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    return care_insights(db, profile)

@app.get("/api/scorecard")
def care_operations_scorecard(ctx=Depends(auth), db: DBSession = Depends(get_db)):
    """Return descriptive care-operations metrics, never a clinical score or prediction."""
    member, profile = ctx
    now = datetime.now(timezone.utc)
    # Match the dashboard's schedule materialisation so this endpoint works independently.
    process_reminders(db, profile, now)
    zone = ZoneInfo(profile.timezone)

    checkin_start = now - timedelta(days=7)
    dose_events = db.query(Dose).filter(
        Dose.profile_id == profile.id,
        Dose.scheduled_at >= checkin_start,
        Dose.scheduled_at <= now,
        Dose.status != "superseded",
    ).all()
    human_recorded = sum(
        1 for dose in dose_events
        if dose.action_at is not None and dose.status in ("taken", "skipped")
    )
    scheduled_count = len(dose_events)
    auto_missed = sum(1 for dose in dose_events if dose.status == "missed" and dose.action_at is None)

    today_local = now.astimezone(zone).date()
    series_by_day = {}
    for offset in range(6, -1, -1):
        day = today_local - timedelta(days=offset)
        series_by_day[day.isoformat()] = {
            "date": day.isoformat(),
            "label": day.strftime("%a"),
            "scheduled": 0,
            "recorded": 0,
        }
    for dose in dose_events:
        day_key = as_utc(dose.scheduled_at).astimezone(zone).date().isoformat()
        if day_key in series_by_day:
            series_by_day[day_key]["scheduled"] += 1
            if dose.action_at is not None and dose.status in ("taken", "skipped"):
                series_by_day[day_key]["recorded"] += 1

    active_members = db.query(Member).filter_by(profile_id=profile.id, active=True).all()
    writable_member_ids = {item.id for item in active_members if item.role in ("patient", "caregiver")}
    open_tasks = db.query(CareTask).filter_by(profile_id=profile.id, status="open").all()
    owned_open = sum(1 for task in open_tasks if task.assigned_to in writable_member_ids)
    unassigned_open = len(open_tasks) - owned_open
    overdue_tasks = [
        task for task in open_tasks
        if task.due_at is not None and as_utc(task.due_at) < now
    ]
    due_next_24h = sum(
        1 for task in open_tasks
        if task.due_at is not None and now <= as_utc(task.due_at) <= now + timedelta(hours=24)
    )
    task_window_start = now - timedelta(days=30)
    tasks_created_30d = db.query(CareTask).filter(
        CareTask.profile_id == profile.id,
        CareTask.created_at >= task_window_start,
        CareTask.created_at <= now,
    ).all()
    completed_30d = sum(1 for task in tasks_created_30d if task.status == "completed")

    upcoming_appointments = db.query(Appointment).filter(
        Appointment.profile_id == profile.id,
        Appointment.starts_at >= now,
        Appointment.starts_at <= now + timedelta(days=30),
    ).order_by(Appointment.starts_at).all()
    prep_tasks = db.query(CareTask).filter(
        CareTask.profile_id == profile.id,
        CareTask.description.like("%[visit-prep:%"),
    ).all()
    upcoming_prep_tasks = []
    visits_with_prep_kit = 0
    for appointment in upcoming_appointments:
        marker = f"[visit-prep:{appointment.id}]"
        visit_tasks = [task for task in prep_tasks if marker in task.description]
        if visit_tasks:
            visits_with_prep_kit += 1
            upcoming_prep_tasks.extend(visit_tasks)
    completed_prep_tasks = sum(1 for task in upcoming_prep_tasks if task.status == "completed")

    next_appointment = upcoming_appointments[0] if upcoming_appointments else None
    return {
        "generated_at": now.isoformat(),
        "checkins": {
            "window_days": 7,
            "scheduled": scheduled_count,
            "human_recorded": human_recorded,
            "rate_percent": round(human_recorded / scheduled_count * 100) if scheduled_count else None,
            "automatically_marked_missed": auto_missed,
        },
        "tasks": {
            "open": len(open_tasks),
            "owned_open": owned_open,
            "unassigned_open": unassigned_open,
            "ownership_percent": round(owned_open / len(open_tasks) * 100) if open_tasks else None,
            "overdue": len(overdue_tasks),
            "due_next_24h": due_next_24h,
            "created_30d": len(tasks_created_30d),
            "completed_30d": completed_30d,
            "completion_percent": round(completed_30d / len(tasks_created_30d) * 100) if tasks_created_30d else None,
        },
        "appointments": {
            "next_30d": len(upcoming_appointments),
            "with_prep_kit": visits_with_prep_kit,
            "prep_coverage_percent": round(visits_with_prep_kit / len(upcoming_appointments) * 100) if upcoming_appointments else None,
            "prep_tasks_total": len(upcoming_prep_tasks),
            "prep_tasks_completed": completed_prep_tasks,
            "prep_task_completion_percent": round(completed_prep_tasks / len(upcoming_prep_tasks) * 100) if upcoming_prep_tasks else None,
            "next": {
                "clinician": next_appointment.clinician,
                "starts_at": as_utc(next_appointment.starts_at).isoformat(),
                "local_time": as_utc(next_appointment.starts_at).astimezone(zone).strftime("%a, %d %b · %I:%M %p"),
            } if next_appointment else None,
        },
        "series": list(series_by_day.values()),
        "definitions": {
            "checkins": "A human-recorded taken/skipped outcome divided by scheduled dose events in the past 7 days. Not proof of ingestion or treatment adherence.",
            "task_ownership": "Open coordination tasks assigned to an active patient/caregiver divided by all open coordination tasks.",
            "task_completion": "Tasks created in the past 30 days and marked completed divided by all tasks created in that period.",
            "visit_prep": "Upcoming appointments in the next 30 days with at least one Visit Ready Kit task divided by all upcoming appointments.",
            "scope": "Operational coordination metrics only; not a clinical score, risk prediction, or measure of treatment effectiveness.",
        },
    }


@app.get("/api/notifications")
def notifications(ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    return [notification_json(n) for n in db.query(Notification).filter_by(profile_id=profile.id, recipient="").order_by(desc(Notification.created_at)).limit(50).all()]

@app.get("/api/activity")
def activity(ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    rows = db.query(Audit).filter_by(profile_id=profile.id).order_by(desc(Audit.created_at)).limit(30).all()
    actors = {m.id: m.name for m in db.query(Member).filter_by(profile_id=profile.id).all()}
    return [{"actor": actors.get(a.actor_id, "MitraCare system"), "action": a.action.replace("_", " "), "detail": a.detail, "at": as_utc(a.created_at).isoformat()} for a in rows]

@app.get("/api/settings/reminders")
def reminder_settings(ctx=Depends(auth), db: DBSession = Depends(get_db)):
    member, profile = ctx
    email_count = db.query(Member).filter(Member.profile_id == profile.id, Member.active == True, Member.email != "").count()
    return {"email_configured": bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD") and email_count > 0), "alert_email_count": email_count, "dose_grace_minutes": 60, "upcoming_dose_minutes": 15, "appointment_leads_hours": [24, 1], "timezone": profile.timezone}

async def reminder_worker(app):
    while True:
        try:
            db = app.state.SessionLocal()
            try:
                profiles = db.query(Profile).all()
                for profile in profiles: process_reminders(db, profile)
                deliver_pending(db)
            finally: db.close()
        except Exception:
            logging.exception("Reminder worker iteration failed")
        await asyncio.sleep(60)


from .companion import router as companion_router
app.include_router(companion_router)
