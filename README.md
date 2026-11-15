# MitraCare — shared care, made calmer

**Catalyst — Solo AI Hackathon | Challenge: Elderly Care & Medication Management Platform**

MitraCare is a patient-first shared care space for medication routines, dose check-ins, doctor appointments, and trusted family/caregiver coordination. It is built around a real workflow rather than a chatbot wrapper: one patient-controlled profile, individually authenticated members, a deterministic reminder state machine, deduplicated alert delivery, and a traceable activity log.

> **Safety boundary:** MitraCare is a coordination and record-keeping prototype. It does not diagnose, prescribe, calculate doses, interpret drug labels, check interactions, determine whether a missed dose should be taken, or replace a clinician/pharmacist. Medication information must be entered from a current clinician-verified prescription. Never double a dose because of an app notification.

## The product in one minute

A patient creates a care profile and PIN, then invites a caregiver or family member with a one-time code. The invited person creates their own PIN. The patient and caregivers can manage verified schedules, record a dose as taken or skipped, and add appointments. Family members can see the shared plan but cannot change it. Every important change is attributed to a member in the activity log.

CareLoop creates dose events in the patient's timezone and tracks them through explicit states:

```text
scheduled → due → taken
                  ├→ skipped
                  └→ missed check-in (after a 60-minute grace window)
```

A reminder is queued 15 minutes before a scheduled dose. If no check-in is recorded within the 60-minute grace window, the event is marked as a missed check-in and a follow-up is queued. Appointment reminders are queued 24 hours and 1 hour before the visit. Each reminder has a database-enforced unique key, preventing repeated page refreshes or worker cycles from sending the same alert repeatedly. Email delivery gets up to three total attempts (the initial attempt plus two retries); delivery failures remain visible in the reminder history.

**CareLoop Insight** is a deliberately explainable, non-clinical routine signal. It looks for time-of-day periods where a sufficient number of check-ins were repeatedly not marked taken, shows the exact sample/window/threshold, and suggests a human conversation about reminder friction. It does not predict illness or recommend treatment. With too little data it explicitly says so.

## What is implemented

| Challenge requirement | MitraCare implementation |
|---|---|
| Shared healthcare profile | Patient-owned care profile with timezone and a unique profile code |
| Passcode-based access | 6–8 digit personal PIN; per-member sessions; invitation codes hashed at rest, single-use and 24-hour expiry |
| Patient/caregiver/family roles | Patient controls invitations; caregiver can manage; family is read-only |
| Add/edit/manage medication routine | Add, edit and pause a verified schedule, route, strength, instructions, prescriber, dates, and up to eight daily times |
| Adherence tracking | Event-level taken/skipped/missed check-ins; 7-day descriptive snapshot (blank until a check-in is recorded) |
| Appointment management | Add clinician, date/time, location and preparation notes |
| Proactive reminders | 15-minute dose prompt, 60-minute missed-check-in escalation, 24-hour/1-hour appointment alerts |
| Email reminders | SMTP delivery to member emails; persistent outbox, deduplication, retry and visible status; in-app-only mode when SMTP is absent |
| Collaboration | Shared care circle, member-specific identity, role boundaries, activity audit |
| Accessibility | Large readable controls, high contrast, keyboard focus, semantic labels, responsive layout, reduced-motion support |
| Privacy/security | Scrypt PIN hashes, HTTP-only cookie sessions, hashed session tokens, account/IP login throttling, role checks, security headers, no third-party AI/data calls |

## Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2
- **Database:** SQLite for local evaluation; PostgreSQL recommended for hosted use
- **Frontend:** HTML, CSS, vanilla JavaScript (no build step, no React dependency, no placeholder screens)
- **Reminder engine:** deterministic Python worker, database outbox, uniqueness constraints, SMTP with retries
- **Deployment target:** Render web service + managed PostgreSQL (configured in `render.yaml`)
- **Testing:** pytest + FastAPI TestClient + isolated in-memory SQLite databases

No external generative model is used in the medication path. The highest-risk actions are deterministic and auditable by design. The product's intelligence is an explainable pattern signal; it is not marketed as clinical AI.

## Run locally (Windows / macOS / Linux)

Python 3.11 or newer is recommended.

```bash
# 1. Extract the project and open the mitracare folder
cd mitracare

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Create the synthetic demo workspace (once)
python -m app.seed_demo

# 5. Start the app
# Windows PowerShell:
$env:COOKIE_SECURE="false"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# macOS/Linux:
# COOKIE_SECURE=false python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>.

### Demo access (synthetic data only)

| Role | Profile code | PIN |
|---|---|---|
| Patient | `MTDEMO26` | `246810` |
| Caregiver | `MTDEMO26` | `135790` |

The local synthetic demo (created only when you run `python -m app.seed_demo`) includes example medications and a clearly labelled demo appointment. It is not seeded on the public hosted service. These are not real prescriptions or a clinical schedule. You can create a new profile from the welcome screen.

## Configure real email delivery

Without SMTP configuration the app still records in-app reminders and explicitly displays that email is not connected. For actual email delivery, copy `.env.example` to `.env` and export the values in your terminal or configure them as service environment variables. Never commit secrets.

Required variables:

```text
SMTP_HOST
SMTP_PORT=587
SMTP_USER
SMTP_PASSWORD
SMTP_FROM
COOKIE_SECURE=true   # true on HTTPS deployment; false only for localhost HTTP
DATABASE_URL         # optional locally; hosted app should use PostgreSQL
```

Each patient/caregiver/family member must provide their own email address when creating or joining the circle. Only then can alerts be delivered to that member. Use a transactional SMTP provider; do not put personal email passwords into the repository. Failed delivery gets up to three total attempts (initial attempt plus two retries) and is then shown as failed. The app must not be used as an emergency alert channel.

## Test and verify

```bash
pytest -q
node --check static/app.js
```

The included tests cover profile creation/login/logout, invalid PIN and timezone handling, login lockout, single-use caregiver/family invitations, role and cross-profile isolation, medication creation/edit/pause, pending-event supersession, dose check-ins and duplicate-action rejection, audit history, missed-check-in and upcoming-reminder idempotency, routine-insight sample thresholds, invalid schedule times, future appointment validation, frontend asset delivery, and mocked SMTP retry/dead-letter behavior.

**Last local verification in this build:** `17 passed` under pytest; `node --check static/app.js` completed without syntax errors. These are automated local tests with synthetic fixtures, not field trials with real older adults or live SMTP. Re-run them on your machine and test in a real browser before claiming deployment readiness.

## Live demo

**Application:** https://mitracare-api-shashank-k8r3-cfr0.onrender.com

**API health:** https://mitracare-api-shashank-k8r3-cfr0.onrender.com/api/health

**Interactive API docs:** https://mitracare-api-shashank-k8r3-cfr0.onrender.com/docs

The application is deployed on Render in Singapore with a managed PostgreSQL 18 database. The deployment was verified as `live` and Render's `/api/health` health checks returned HTTP 200 after startup.

For the hosted instance, create a new patient profile from the welcome screen. The local synthetic demo accounts listed above are not seeded into the public service. Email delivery is not enabled until valid SMTP credentials and a verified sender are configured; in-app reminders remain available.

**Free-tier limitations:** the web service can spin down after inactivity, causing a cold-start delay. The free PostgreSQL database is scheduled to expire on **15 December 2026**. Do not use this temporary hackathon deployment for real patient or other sensitive health data; move to a paid persistent database, configure backups and secrets, and complete security and clinical validation before any real-world use.

## API overview

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/profiles` | Create patient profile and sign in |
| POST | `/api/auth/login` | Sign in with profile code + personal PIN |
| POST | `/api/auth/join` | Accept a single-use invite and set a personal PIN |
| POST | `/api/auth/logout` | Revoke current session |
| GET | `/api/me` | Current member/profile |
| POST | `/api/invites` | Patient invites caregiver or family |
| GET | `/api/members` | List active care-circle members |
| POST / GET | `/api/medications` | Add/list medication schedules |
| PUT | `/api/medications/{id}` | Edit a verified schedule and supersede obsolete pending events |
| PATCH | `/api/medications/{id}/deactivate` | Pause a schedule without deleting history |
| GET | `/api/dashboard` | Upcoming doses, appointments, adherence snapshot and reminders |
| POST | `/api/doses/{id}/mark` | Record taken or skipped check-in (one transition only) |
| POST / GET | `/api/appointments` | Add/list doctor appointments |
| GET | `/api/insights` | Explainable, descriptive routine signals |
| GET | `/api/activity` | Recent audit events |
| GET | `/api/notifications` | Reminder/outbox history |
| GET | `/api/settings/reminders` | Reminder configuration summary |
| GET | `/api/health` | Health probe |

Interactive API documentation is available at `/docs` while the service is running.

## Known limitations — stated honestly

- No real-world field testing with elderly participants has been conducted. The automated tests validate software behavior, not clinical safety or usability in the home.
- Email delivery requires valid SMTP credentials, verified sender configuration and member email addresses. A queue record alone is not proof an email reached an inbox.
- SQLite is for local evaluation only; use PostgreSQL for hosted use. This prototype uses `create_all`; production needs versioned migrations, backups and recovery tests.
- The embedded reminder worker is suitable for a single-instance prototype. Production should use a separate durable scheduler/worker, distributed locking, monitoring and dead-letter handling.
- There is no clinician/EMR integration, pharmacy integration, refill management, SMS/WhatsApp channel, offline sync, caregiver identity verification, or push notification support.
- The app does not check drug-drug interactions, duplicate ingredients, contraindications, renal adjustments, missed-dose actions, or dosage correctness.
- No regulatory, privacy, penetration, accessibility certification or clinical validation is claimed. Do not enter real health information into a public hackathon deployment.

## Submission positioning

**One-liner:** *MitraCare turns isolated medication reminders into a patient-controlled care loop: verified schedules, individual caregiver access, event-level check-ins and deduplicated escalation — with every change visible to the right people.*

**What judges should see:** create a patient profile → invite caregiver → add a clinician-verified demo schedule → mark a dose taken → switch to the caregiver and see the same state → view the audit event → show the reminder queue and CareLoop evidence. This demonstrates the core workflow and the engineering mechanism, not just a set of dashboard screens.
