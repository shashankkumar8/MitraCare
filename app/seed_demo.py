"""Create a clearly synthetic local demo care circle. Run: python -m app.seed_demo"""
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .database import Base, make_database
from .models import Profile, Member, Medication, Appointment
from .security import hash_secret
from .engine import materialize_doses

engine, SessionLocal = make_database()
Base.metadata.create_all(engine)
db = SessionLocal()
try:
    if db.query(Profile).filter_by(code="MTDEMO26").first():
        print("Demo already exists: profile MTDEMO26 / PIN 246810 (patient), 135790 (caregiver)")
    else:
        profile = Profile(code="MTDEMO26", name="Meera Sharma", timezone="Asia/Kolkata")
        db.add(profile); db.flush()
        patient = Member(profile_id=profile.id, name="Meera Sharma", email="", role="patient", pin_hash=hash_secret("246810"))
        caregiver = Member(profile_id=profile.id, name="Ananya Sharma", email="", role="caregiver", pin_hash=hash_secret("135790"))
        db.add_all([patient, caregiver]); db.flush()
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        med1 = Medication(profile_id=profile.id, name="Example medicine A", strength="As on prescription", instructions="Demo schedule only — replace with the person's verified prescription", route="Oral", times_json=json.dumps(["08:00", "20:00"]), start_date=now.date().isoformat(), end_date="", prescriber="Demo clinician", active=True, created_by=patient.id)
        med2 = Medication(profile_id=profile.id, name="Example medicine B", strength="As on prescription", instructions="Demo schedule only — verify with clinician", route="Oral", times_json=json.dumps(["13:00"]), start_date=now.date().isoformat(), end_date="", prescriber="Demo clinician", active=True, created_by=patient.id)
        db.add_all([med1, med2])
        appointment = Appointment(profile_id=profile.id, clinician="Dr. Rao (demo)", location="Community clinic (demo)", starts_at=(now+timedelta(days=2)).astimezone(timezone.utc), notes="Synthetic appointment; not a real booking", created_by=patient.id)
        db.add(appointment); db.flush(); materialize_doses(db, profile); db.commit()
        print("Demo ready: profile MTDEMO26 / PIN 246810 (patient), 135790 (caregiver)")
finally:
    db.close()
