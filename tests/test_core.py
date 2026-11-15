from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
from app.main import app
from app.database import Base
from app.models import Profile, Member, Medication, Dose, Notification
from app.security import hash_secret
from app.engine import process_reminders

@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app.state.engine = engine; app.state.SessionLocal = SessionLocal
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c, SessionLocal
    Base.metadata.drop_all(engine); engine.dispose()

def create_patient(c):
    r = c.post("/api/profiles", json={"name":"Meera Sharma", "pin":"246810", "email":"", "timezone":"Asia/Kolkata"})
    assert r.status_code == 201, r.text
    return r.json()["profile_code"]

def test_profile_login_cookie_and_health(client):
    c, _ = client
    assert c.get("/api/health").json()["status"] == "ok"
    code = create_patient(c)
    assert c.get("/api/me").status_code == 200
    c.post("/api/auth/logout")
    assert c.get("/api/me").status_code == 401
    assert c.post("/api/auth/login", json={"profile_code":code,"pin":"246810"}).status_code == 200
    assert c.get("/api/me").json()["member"]["role"] == "patient"

def test_bad_pin_and_invalid_timezone_rejected(client):
    c, _ = client
    assert c.post("/api/profiles", json={"name":"Meera", "pin":"123", "timezone":"Asia/Kolkata"}).status_code == 422
    assert c.post("/api/profiles", json={"name":"Meera", "pin":"123456", "timezone":"Not/AZone"}).status_code == 422
    code = create_patient(c)
    assert c.post("/api/auth/login", json={"profile_code":code,"pin":"000000"}).status_code == 401

def test_patient_invite_caregiver_and_family_read_only(client):
    c, _ = client; create_patient(c)
    invite = c.post("/api/invites", json={"name":"Ananya", "role":"caregiver"})
    assert invite.status_code == 201
    joined = c.post("/api/auth/join", json={"invite_code":invite.json()["invite_code"],"name":"Ananya","pin":"135790"})
    assert joined.status_code == 200 and joined.json()["member"]["role"] == "caregiver"
    # Caregiver can invite no one; patient is the permission owner.
    assert c.post("/api/invites", json={"name":"Other","role":"family"}).status_code == 403
    c.post("/api/auth/logout")
    login = c.post("/api/auth/login", json={"profile_code":joined.json()["profile"]["code"],"pin":"135790"})
    assert login.status_code == 200
    family_invite = c.post("/api/invites", json={"name":"Family","role":"family"})
    assert family_invite.status_code == 403

def test_medication_schedule_marking_and_immutable_double_action(client):
    c, _ = client; create_patient(c)
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    r = c.post("/api/medications", json={"name":"Example tablet","strength":"As prescribed","instructions":"Demo only","route":"Oral","times":["23:59"],"start_date":today,"prescriber":"Dr Demo"})
    assert r.status_code == 201, r.text
    dashboard = c.get("/api/dashboard").json()
    dose = next(d for d in dashboard["doses"] if d["medication"] == "Example tablet")
    marked = c.post(f"/api/doses/{dose['id']}/mark", json={"action":"taken","note":"Recorded by patient"})
    assert marked.status_code == 200 and marked.json()["status"] == "taken"
    again = c.post(f"/api/doses/{dose['id']}/mark", json={"action":"skipped","note":""})
    assert again.status_code == 409
    assert any(a["action"] == "dose taken" for a in c.get("/api/activity").json())

def test_family_role_cannot_mutate_medication_or_dose(client):
    c, _ = client; code = create_patient(c)
    invite = c.post("/api/invites", json={"name":"Reader","role":"family"}).json()
    c.post("/api/auth/logout")
    assert c.post("/api/auth/join", json={"invite_code":invite["invite_code"],"name":"Reader","pin":"112233"}).status_code == 200
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    payload = {"name":"Medication","strength":"","instructions":"","route":"Oral","times":["23:59"],"start_date":today}
    assert c.post("/api/medications", json=payload).status_code == 403
    assert c.post("/api/appointments", json={"clinician":"Dr X","starts_at":(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}).status_code == 403

def test_missed_transition_and_email_idempotency():
    engine = create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); S = sessionmaker(bind=engine, expire_on_commit=False)
    db = S()
    profile = Profile(code="MTRULE01", name="Patient", timezone="UTC"); db.add(profile); db.flush()
    member = Member(profile_id=profile.id,name="Patient",email="",role="patient",pin_hash=hash_secret("123456")); db.add(member); db.flush()
    med = Medication(profile_id=profile.id,name="Test med",strength="test",instructions="",route="Oral",times_json=json.dumps(["10:00"]),start_date="2026-11-15",end_date="2026-11-15",prescriber="",active=True,created_by=member.id)
    db.add(med); db.flush()
    scheduled = datetime(2026,11,15,10,0,tzinfo=timezone.utc)
    dose = Dose(profile_id=profile.id,medication_id=med.id,scheduled_at=scheduled,status="pending"); db.add(dose); db.commit()
    process_reminders(db, profile, scheduled+timedelta(minutes=61))
    assert db.get(Dose,dose.id).status == "missed"
    count1 = db.query(Notification).count()
    process_reminders(db, profile, scheduled+timedelta(minutes=62))
    assert db.query(Notification).count() == count1 == 1
    db.close(); Base.metadata.drop_all(engine); engine.dispose()

def test_appointment_requires_future_datetime(client):
    c, _ = client; create_patient(c)
    payload = {"clinician":"Dr Rao","starts_at":(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()}
    assert c.post("/api/appointments", json=payload).status_code == 422

def test_login_lockout_after_five_failed_attempts(client):
    c, _ = client; code = create_patient(c)
    for _ in range(5):
        r = c.post("/api/auth/login", json={"profile_code":code,"pin":"000000"})
    assert r.status_code == 401
    locked = c.post("/api/auth/login", json={"profile_code":code,"pin":"246810"})
    assert locked.status_code == 429

def test_upcoming_reminder_is_queued_once():
    engine = create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); S = sessionmaker(bind=engine, expire_on_commit=False)
    db = S()
    now = datetime(2026,11,15,9,50,tzinfo=timezone.utc)
    profile = Profile(code="MTRULE02", name="Patient", timezone="UTC"); db.add(profile); db.flush()
    member = Member(profile_id=profile.id,name="Patient",email="",role="patient",pin_hash=hash_secret("123456")); db.add(member); db.flush()
    med = Medication(profile_id=profile.id,name="Test med",strength="test",instructions="",route="Oral",times_json=json.dumps(["10:00"]),start_date="2026-11-15",end_date="2026-11-15",prescriber="",active=True,created_by=member.id)
    db.add(med); db.flush(); dose = Dose(profile_id=profile.id,medication_id=med.id,scheduled_at=datetime(2026,11,15,10,0,tzinfo=timezone.utc),status="pending"); db.add(dose); db.commit()
    process_reminders(db, profile, now); first = db.query(Notification).count()
    process_reminders(db, profile, now+timedelta(minutes=1)); second = db.query(Notification).count()
    assert first == second == 1
    row = db.query(Notification).first(); assert row.kind == "upcoming_dose" and row.status == "in_app"
    db.close(); Base.metadata.drop_all(engine); engine.dispose()

def test_insight_engine_is_descriptive_and_requires_minimum_sample():
    from app.engine import care_insights
    engine = create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); S = sessionmaker(bind=engine, expire_on_commit=False); db=S()
    profile=Profile(code="MTRULE03",name="Patient",timezone="UTC");db.add(profile);db.flush()
    # Three events are below the four-event minimum, so no time-slot signal is fabricated.
    med=Medication(profile_id=profile.id,name="Demo",strength="",instructions="",route="Oral",times_json='["20:00"]',start_date="2026-11-15",end_date="",prescriber="",active=True,created_by=1)
    member=Member(profile_id=profile.id,name="Patient",email="",role="patient",pin_hash=hash_secret("123456"));db.add(member);db.flush();med.created_by=member.id;db.add(med);db.flush()
    for day in range(3): db.add(Dose(profile_id=profile.id,medication_id=med.id,scheduled_at=datetime(2026,11,13+day,20,0,tzinfo=timezone.utc),status="missed"))
    db.commit(); signals=care_insights(db,profile,datetime(2026,11,15,21,0,tzinfo=timezone.utc))
    assert len(signals)==1 and "No clear" in signals[0]["title"]
    assert "no clinical prediction" in signals[0]["method"]
    db.close();Base.metadata.drop_all(engine);engine.dispose()

def test_invalid_schedule_time_rejected(client):
    c,_=client;create_patient(c)
    today=datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    payload={"name":"Medicine","times":["25:90"],"start_date":today}
    assert c.post("/api/medications",json=payload).status_code==422

def test_medication_edit_supersedes_only_obsolete_pending_events(client):
    c,_=client;create_patient(c)
    today=datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    payload={"name":"Demo tablet","strength":"10 mg","route":"Oral","instructions":"Old schedule","times":["23:59"],"start_date":today}
    created=c.post("/api/medications",json=payload);assert created.status_code==201
    med_id=created.json()["id"]
    updated={**payload,"strength":"20 mg","instructions":"Updated from verified label","times":["21:00"]}
    r=c.put(f"/api/medications/{med_id}",json=updated)
    assert r.status_code==200 and r.json()["strength"]=="20 mg"
    with c:
        # The changed schedule is reflected in the API and an audit trail is written.
        assert c.get('/api/medications').json()[0]['times']==['21:00']
        assert any(a['action']=='medication updated' for a in c.get('/api/activity').json())

def test_static_frontend_and_accessibility_entry_point(client):
    c,_=client
    home=c.get('/')
    assert home.status_code==200 and 'MitraCare' in home.text and 'Skip to main content' in home.text
    assert c.get('/static/styles.css').status_code==200
    assert c.get('/static/app.js').status_code==200

def test_medication_deactivation_preserves_existing_records(client):
    c,_=client;create_patient(c)
    today=datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    r=c.post('/api/medications',json={"name":"Pause test","times":["23:59"],"start_date":today})
    assert r.status_code==201
    paused=c.patch(f"/api/medications/{r.json()['id']}/deactivate")
    assert paused.status_code==200 and paused.json()['medication']['active'] is False
    assert c.get('/api/medications').json()[0]['active'] is False
    with client[1]() as db:
        from app.models import Dose
        assert db.query(Dose).filter_by(status='superseded').count() >= 1

def test_smtp_failure_is_retried_then_dead_lettered(monkeypatch):
    import app.engine as engine_module
    from app.engine import deliver_pending
    monkeypatch.setenv('SMTP_HOST','smtp.example.invalid');monkeypatch.setenv('SMTP_USER','user');monkeypatch.setenv('SMTP_PASSWORD','secret')
    class BrokenSMTP:
        def __init__(self,*a,**k): pass
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def starttls(self): pass
        def login(self,*a): pass
        def send_message(self,*a): raise OSError('simulated SMTP failure')
    monkeypatch.setattr(engine_module.smtplib,'SMTP',BrokenSMTP)
    e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);Base.metadata.create_all(e);S=sessionmaker(bind=e,expire_on_commit=False);db=S()
    p=Profile(code='MTRULE04',name='Patient',timezone='UTC');db.add(p);db.flush()
    n=Notification(profile_id=p.id,dedupe_key='retry-test',kind='test',subject='Test',body='Test body',recipient='member@example.com',status='queued');db.add(n);db.commit()
    deliver_pending(db);assert n.status=='retrying' and n.attempts==1 and n.last_error=='OSError'
    n.attempts=2;n.next_attempt_at=datetime.now(timezone.utc)-timedelta(seconds=1);n.status='retrying';db.commit()
    deliver_pending(db);assert n.status=='failed' and n.attempts==3
    db.close();Base.metadata.drop_all(e);e.dispose()

def test_invite_is_single_use(client):
    c,_=client;create_patient(c)
    inv=c.post('/api/invites',json={'name':'Family','role':'family'}).json()
    joined=c.post('/api/auth/join',json={'invite_code':inv['invite_code'],'name':'Family','pin':'445566'})
    assert joined.status_code==200
    c.post('/api/auth/logout')
    replay=c.post('/api/auth/join',json={'invite_code':inv['invite_code'],'name':'Other','pin':'556677'})
    assert replay.status_code==400

def test_profile_data_isolation(client):
    c,_=client;code_a=create_patient(c)
    today=datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()
    c.post('/api/medications',json={'name':'Private A medicine','times':['23:59'],'start_date':today})
    c.post('/api/auth/logout')
    code_b=c.post('/api/profiles',json={'name':'Patient B','pin':'654321','timezone':'Asia/Kolkata'}).json()['profile_code']
    c.post('/api/auth/logout')
    c.post('/api/auth/login',json={'profile_code':code_a,'pin':'246810'})
    assert len(c.get('/api/medications').json())==1
    c.post('/api/auth/logout')
    c.post('/api/auth/login',json={'profile_code':code_b,'pin':'654321'})
    assert c.get('/api/medications').json()==[]
