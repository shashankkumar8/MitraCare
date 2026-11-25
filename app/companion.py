"""Local, authenticated MitraCare care-coordination companion. No LLM or external API."""
import json
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, Literal
from sqlalchemy import desc
from sqlalchemy.orm import Session
from .engine import as_utc
from .models import Appointment, Audit, CareTask, Dose, Medication, Member, Profile
from .security import current_member

router = APIRouter(tags=["Mitra Companion"])

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=600)

class BriefRequest(BaseModel):
    kind: Literal["visit", "handover"]
    consent: bool = False

def get_db():
    from .main import app
    db = app.state.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_context(request: Request, db: Session = Depends(get_db)):
    member, _ = current_member(request, db)
    profile = db.get(Profile, member.profile_id)
    if not profile:
        raise HTTPException(401, "Care profile not found.")
    return member, profile

def local(dt, profile):
    if not dt:
        return "Not set"
    return as_utc(dt).astimezone(ZoneInfo(profile.timezone)).strftime("%a, %d %b %Y · %I:%M %p")

def chat_reply(message, db, member, profile):
    text = unicodedata.normalize("NFKC", message).casefold().strip()
    now = datetime.now(timezone.utc)
    people = db.query(Member).filter_by(profile_id=profile.id, active=True).order_by(Member.id).all()
    by_id = {p.id:p for p in people}
    tasks = db.query(CareTask).filter_by(profile_id=profile.id, status="open").order_by(
        CareTask.due_at.is_(None), CareTask.due_at, CareTask.id.desc()).limit(40).all()
    overdue = [t for t in tasks if t.due_at and as_utc(t.due_at) < now]
    appointments = db.query(Appointment).filter(
        Appointment.profile_id == profile.id,
        Appointment.starts_at >= now - timedelta(hours=2)
    ).order_by(Appointment.starts_at).limit(8).all()
    meds = db.query(Medication).filter_by(profile_id=profile.id, active=True).order_by(Medication.name).all()
    missed = db.query(Dose).filter(
        Dose.profile_id == profile.id, Dose.status == "missed",
        Dose.scheduled_at >= now-timedelta(days=7), Dose.scheduled_at <= now
    ).count()

    emergency = ("emergency", "chest pain", "not breathing", "can't breathe", "cannot breathe",
                 "unconscious", "seizure", "stroke", "severe bleeding", "overdose", "poisoning")
    if any(term in text for term in emergency):
        return ("MitraCare cannot assess an emergency or dispatch help. Contact your local "
                "emergency number or emergency service now; do not wait for this chat. "
                "If safe, tell the care circle who is contacting help. This app is not an emergency service.")

    clinical = ("diagnos", "symptom", "side effect", "interaction", "allerg", "dosage",
                "dose amount", "should i take", "can i take", "stop taking", "double dose",
                "extra dose", "which medicine", "what medicine", "treatment", "cure",
                "fever", "rash", "pain", "dizzy", "vomit", "blood pressure", "blood sugar",
                "prescription change")
    missed_advice = ("missed dose" in text or "forgot dose" in text or "forgotten dose" in text) and any(
        term in text for term in ("what should", "what do", "should i", "can i", "now"))
    if any(term in text for term in clinical) or missed_advice:
        return ("I can organise records, but I cannot diagnose, interpret symptoms, check drug "
                "interactions, or tell anyone whether to take, skip, repeat or change a dose. "
                "For a missed, late or uncertain dose, contact the prescribing clinician or "
                "pharmacist and follow the current prescription instructions. For severe or "
                "rapidly worsening symptoms, use local urgent/emergency care. I can show recorded "
                "check-ins or prepare a visit brief for a clinician.")

    if any(term in text for term in ("attention", "today's plan", "today plan", "priorities", "overview", "status")):
        lines = [f"{len(tasks)} open follow-up(s); {len(overdue)} past their due time.",
                 f"{missed} dose check-in(s) marked missed in the last 7 days." if missed else
                 "No missed dose check-ins recorded in the last 7 days."]
        if tasks:
            lines.append("Open follow-ups:\n" + "\n".join(
                f"• {t.title} — {by_id[t.assigned_to].name if t.assigned_to in by_id else 'Unassigned'} — {local(t.due_at,profile) if t.due_at else 'No due date'}"
                for t in tasks[:5]))
        lines.append("Next appointment: " + (appointments[0].clinician + " — " + local(appointments[0].starts_at, profile)
                                             if appointments else "none recorded"))
        lines.append("These are coordination records, not a clinical assessment or proof of physical ingestion.")
        return "\n\n".join(lines)

    if any(term in text for term in ("task", "follow-up", "follow up", "transport", "supplies", "assigned")):
        if not tasks:
            return "There are no open follow-ups. A patient or caregiver can open Care Tasks → Add follow-up, assign an owner and set a due time."
        return f"{len(tasks)} open follow-up(s):\n" + "\n".join(
            f"• [{'OVERDUE' if t in overdue else 'OPEN'}] {t.title} — {by_id[t.assigned_to].name if t.assigned_to in by_id else 'Unassigned'} — {local(t.due_at,profile) if t.due_at else 'No due date'}"
            for t in tasks[:8]) + "\n\nPatient and caregiver members can complete or reopen tasks; family members have view-only access."

    if any(term in text for term in ("appointment", "doctor visit", "clinic visit", "visit prep", "doctor")):
        if not appointments:
            return "No upcoming appointment is recorded. Add one under Appointments, then use Visit brief to prepare a record-based summary for discussion."
        return "Upcoming recorded appointment(s):\n" + "\n".join(
            f"• {a.clinician} — {local(a.starts_at,profile)}" + (f" · {a.location}" if a.location else "")
            for a in appointments[:5]) + "\n\nUse Visit brief to prepare the entered schedule and check-ins for verification with a clinician. It is not a clinical assessment."

    if any(term in text for term in ("care circle", "family", "caregiver", "who is")):
        return f"{len(people)} active care-circle member(s):\n" + "\n".join(
            f"• {p.name} — {p.role}" for p in people) + (
            "\n\nThe patient owns the profile and controls invitations. Caregivers can help manage routines and tasks. Family access is view-only; the patient can revoke access.")

    if any(term in text for term in ("reminder", "notification", "alert")):
        return ("CareLoop creates an in-app medication reminder about 15 minutes before a scheduled "
                "time, records an unconfirmed event as a missed check-in after a 60-minute grace "
                "window, and queues appointment reminders about 24 hours and 1 hour before a visit. "
                "Tasks with due times also get due-soon or overdue in-app reminders. Worker uptime "
                "affects delivery; email requires SMTP configuration. These are not emergency alerts.")

    if any(term in text for term in ("medication list", "medicines in my plan", "my medications", "medication schedule")):
        return (f"{len(meds)} active medication schedule(s) are recorded.\n" +
                "\n".join(f"• {m.name} {m.strength} — {', '.join(json.loads(m.times_json))}" for m in meds) +
                "\nThese are user-entered details, not a verified prescription. Verify them with the current prescription and clinician/pharmacist.")

    if any(term in text for term in ("visit brief", "handover", "report", "summary", "export")):
        return "Use Visit brief to prepare a clinician discussion summary, or Family handover for care-circle continuity. Both are assembled from existing profile records; review and share only with the patient's permission."
    if any(term in text for term in ("help", "how", "what can", "start", "use mitracare")):
        return ("I am Mitra, the local care-coordination guide. I can summarise tasks, appointments, "
                "care-circle roles and reminder rules, and prepare a clinician visit brief or family "
                "handover. Add schedules under Medications, visits under Appointments, and practical "
                "actions under Care Tasks. I do not diagnose or make medication decisions.")
    return ("I can help with MitraCare workflows and records visible to this care circle. Try "
            "“What needs attention today?”, “Show open tasks”, “When is the next appointment?”, "
            "“Who is in the care circle?” or “How do reminders work?”. You can also prepare a Visit "
            "brief or Family handover. I cannot answer clinical or medication-decision questions.")

@router.get("/api/companion/capabilities")
def companion_capabilities(ctx=Depends(require_context)):
    member, profile = ctx
    return {
        "role": member.role,
        "can_chat": True,
        "can_prepare_brief": member.role in ("patient", "caregiver"),
    }


@router.post("/api/companion/chat")
def companion_chat(data: ChatRequest, ctx=Depends(require_context), db: Session=Depends(get_db)):
    member, profile = ctx
    message = " ".join(data.message.strip().split())
    if not message:
        raise HTTPException(422, "Enter a question for the companion.")
    since = datetime.now(timezone.utc)-timedelta(minutes=10)
    count = db.query(Audit).filter(
        Audit.profile_id==profile.id, Audit.actor_id==member.id,
        Audit.action=="care_companion_chat", Audit.created_at>=since).count()
    if count >= 40:
        raise HTTPException(429, "Please pause briefly before sending another message.")
    # Only usage metadata is stored. Submitted text and generated reply are not persisted.
    db.add(Audit(profile_id=profile.id, actor_id=member.id, action="care_companion_chat",
                 detail="Used local care-coordination companion; message content not stored."))
    db.commit()
    return {"reply":chat_reply(message,db,member,profile),"mode":"local_rules","stored":False}

@router.post("/api/companion/brief")
def companion_brief(data: BriefRequest, ctx=Depends(require_context), db: Session=Depends(get_db)):
    member, profile = ctx
    if member.role == "family":
        raise HTTPException(403, "Ask the patient or a caregiver to prepare a care brief; family access is view-only.")
    if not data.consent:
        raise HTTPException(422, "Confirm that the patient has given permission to prepare this brief.")
    now = datetime.now(timezone.utc)
    members = db.query(Member).filter_by(profile_id=profile.id).order_by(Member.id).all()
    by_id = {p.id:p.name for p in members}
    meds = db.query(Medication).filter_by(profile_id=profile.id).order_by(Medication.name).all()
    med_map = {m.id:m.name for m in meds}
    active_meds = [m for m in meds if m.active]
    med_rows = [{"name":m.name,"strength":m.strength,"route":m.route,"times":json.loads(m.times_json),
                 "instructions_entered":m.instructions,"prescriber_entered":m.prescriber,
                 "start_date":m.start_date,"end_date":m.end_date or ""} for m in active_meds]
    appts = db.query(Appointment).filter(
        Appointment.profile_id==profile.id,
        Appointment.starts_at>=now-timedelta(days=30),
        Appointment.starts_at<=now+timedelta(days=180)).order_by(Appointment.starts_at).limit(20).all()
    appt_rows = [{"clinician":a.clinician,"location":a.location,"starts_at":as_utc(a.starts_at).isoformat(),
                  "local_time":local(a.starts_at,profile),"notes_entered":a.notes} for a in appts]
    doses = db.query(Dose).filter(
        Dose.profile_id==profile.id,Dose.scheduled_at>=now-timedelta(days=14),
        Dose.scheduled_at<=now,Dose.status.in_(("taken","skipped","missed"))
    ).order_by(desc(Dose.scheduled_at)).limit(100).all()
    dose_rows = [{"medication":med_map.get(d.medication_id,"Medication schedule"),"status":d.status,
                  "scheduled_local":local(d.scheduled_at,profile),"recorded_by":by_id.get(d.action_by,"Not attributed"),
                  "recorded_at":local(d.action_at,profile) if d.action_at else ""} for d in doses]
    counts = {
        status: db.query(Dose).filter(
            Dose.profile_id==profile.id, Dose.scheduled_at>=now-timedelta(days=14),
            Dose.scheduled_at<=now, Dose.status==status
        ).count()
        for status in ("taken","skipped","missed")
    }
    upcoming = db.query(Dose).filter(
        Dose.profile_id==profile.id,Dose.scheduled_at>=now,
        Dose.scheduled_at<=now+timedelta(days=7),Dose.status=="pending"
    ).order_by(Dose.scheduled_at).limit(40).all()
    upcoming_rows = [{"medication":med_map.get(d.medication_id,"Medication schedule"),
                      "scheduled_local":local(d.scheduled_at,profile)} for d in upcoming]
    tasks = db.query(CareTask).filter(
        CareTask.profile_id==profile.id,
        (CareTask.status=="open") | ((CareTask.status=="completed") & (CareTask.completed_at>=now-timedelta(days=7)))
    ).order_by(CareTask.status,CareTask.due_at,desc(CareTask.id)).limit(80).all()
    task_rows = [{"title":t.title,"description":t.description,"category":t.category,"status":t.status,
                  "assigned_to":by_id.get(t.assigned_to,"Unassigned"),
                  "due_local":local(t.due_at,profile) if t.due_at else "No due date",
                  "completed_by":by_id.get(t.completed_by,"Not recorded"),
                  "completed_at":local(t.completed_at,profile) if t.completed_at else ""} for t in tasks]
    activity = db.query(Audit).filter_by(profile_id=profile.id).order_by(desc(Audit.created_at)).limit(20).all()
    activity_rows = [{"actor":by_id.get(a.actor_id,"MitraCare system"),
                      "action":a.action.replace("_"," "),"detail":a.detail,"at":local(a.created_at,profile)}
                     for a in activity]
    db.add(Audit(profile_id=profile.id,actor_id=member.id,action="care_brief_prepared",
                 detail=f"Prepared a {data.kind} brief; patient permission confirmed."))
    db.commit()
    return {
        "kind":data.kind,"profile":profile.name,"timezone":profile.timezone,
        "prepared_at_local":local(now,profile),"prepared_by":member.name,
        "care_circle":[{"name":p.name,"role":p.role} for p in members if p.active],
        "medications":med_rows,"appointments":appt_rows,"checkins":dose_rows,
        "checkin_counts_14d":counts,"upcoming_doses":upcoming_rows,"tasks":task_rows,
        "recent_activity":activity_rows,
        "visit_questions":[
            "Please verify this user-entered medication list and schedule against the current prescription and packaging.",
            "What should the patient or caregiver do if a dose is late, missed or uncertain?",
            "Which changes or symptoms should prompt a call, and which contact should be used?",
            "Please clarify any changes to the plan and when updated instructions take effect."
        ],
        "data_note":("This is a user-entered coordination summary, not a medical record or clinical assessment. "
                     "A recorded 'taken' check-in is not proof of physical ingestion. Verify every medication "
                     "and instruction with the clinician or pharmacist.")
    }
