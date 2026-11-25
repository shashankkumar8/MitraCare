# MitraCare

### Patient-first elderly-care coordination · Medication routines · Shared family visibility

[![CI](https://github.com/shashankkumar8/MitraCare/actions/workflows/tests.yml/badge.svg)](https://github.com/shashankkumar8/MitraCare/actions/workflows/tests.yml)
[![Live demo](https://img.shields.io/badge/Live%20Demo-Render-2E6D4B)](https://mitracare-api-shashank-k8r3-cfr0.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1)](https://www.postgresql.org/)

**Shared care. Safer routines. The patient stays in control.**

MitraCare is a shared medication and appointment workspace for older adults and the people they trust. It connects a patient, invited caregivers and family members around one care profile—with individual sign-in, role-specific permissions, medication schedules, dose check-ins, appointment planning, reminder history and an attributed activity record.

It is designed around a practical care workflow, not a chatbot: the schedule is explicit, reminder transitions are deterministic, repeated notifications are deduplicated, and every recorded action has an identifiable member behind it.

> **Product principle:** technology should make it easier for an older adult to coordinate care—not quietly take decisions away from them.

---

## Live application

| Resource | Link |
|---|---|
| **MitraCare web app** | [Open the live application](https://mitracare-api-shashank-k8r3-cfr0.onrender.com) |
| **API health** | [Check service health](https://mitracare-api-shashank-k8r3-cfr0.onrender.com/api/health) |
| **Interactive API reference** | [Open Swagger UI](https://mitracare-api-shashank-k8r3-cfr0.onrender.com/docs) |
| **Source repository** | [GitHub — shashankkumar8/MitraCare](https://github.com/shashankkumar8/MitraCare) |
| **Automated checks** | [GitHub Actions](https://github.com/shashankkumar8/MitraCare/actions) |

**Hosted environment:** Render web service in Singapore, backed by managed PostgreSQL 18. The service is configured for HTTPS cookies and has been verified live with successful application-root and API health responses.

**First visit:** the hosted environment does not contain shared demo credentials. Create a new patient profile from the welcome screen, then invite test caregiver/family members from the Care circle.

**Deployment note:** this is a hackathon demonstration on Render's free tier. The web service may sleep after inactivity, and the current free PostgreSQL instance is scheduled to expire on **15 December 2026**. Do not enter real patient or sensitive health information.

---

## Product at a glance

| Area | What MitraCare provides |
|---|---|
| **Patient profile** | A patient-owned care profile with a unique profile code and timezone |
| **Shared access** | Separate PIN-based accounts for the patient, caregivers and family |
| **Medication plan** | Add, edit and pause schedules transcribed from a current verified prescription |
| **Dose check-ins** | Record taken or skipped events; overdue events become missed check-ins |
| **Appointments** | Shared clinician, date, time, location and preparation notes |
| **CareLoop reminders** | Upcoming dose, missed-check-in and appointment reminder events |
| **Reminder history** | In-app notification records and visible email delivery states |
| **CareLoop Insight** | Explainable time-of-day routine signals based on recorded check-ins |
| **Shared care tasks** | Assign transport, appointment preparation, supplies and non-clinical follow-ups with ownership |\n| **AI task coach** | Optional Gemini checklist from a fixed category only; local templates work without an API key |\n| **Activity log** | Recent member-attributed changes across the care profile |

### Why it is different

Most reminder utilities stop at a notification. MitraCare connects the surrounding workflow:

1. **A shared source of context:** the patient, caregiver and family see the same care plan through their own accounts.
2. **A deterministic event engine:** medication schedules become dated dose events with explicit states and bounded reminder rules.
3. **A patient-controlled care circle:** the patient chooses who joins and whether they receive caregiver or view-only family access.
4. **An explainable signal, not a black box:** the routine insight shows its sample, time window and threshold. It does not diagnose or recommend treatment.
5. **A traceable record:** medication changes, check-ins, invitations, tasks and appointments are attributed to a member in the activity history.\n6. **A reminder is not the whole workflow:** assign transport, supplies and appointment-preparation tasks to a named patient or caregiver, then record completion.\n7. **AI with a narrow privacy boundary:** the optional Task Coach sends only a fixed category label to Gemini—not task titles, notes, identity, medication or health details. Without a server-side key, it returns a clearly labelled local template.

---

## Workspace modules

The browser application is organized into seven focused work areas.

### 1. Overview

A shared snapshot of the care routine: upcoming dose events, appointment schedule, descriptive adherence records, recent reminders and care-circle members. The adherence figure remains empty until there are recorded check-ins; it is not presented as proof that a medicine was physically taken.

### 2. Medication plan

Create, edit and pause medication schedules with:

- Medication name, strength/form and route.
- Instructions transcribed from the current prescription.
- One or more scheduled times in 24-hour format (up to eight per day).
- Start date, optional end date and prescriber/clinic.
- A dated event for each scheduled dose in the patient's timezone.

Editing a schedule supersedes future pending events that no longer match. Pausing a schedule preserves the historical record and supersedes future pending events rather than deleting the medication history.

### 3. Appointments

Add and view doctor or clinician appointments with date/time, location and optional preparation notes. Appointment times are stored in UTC and displayed in the patient's configured timezone.

### 4. Care circle

The patient controls invitations and access. Patient owners can revoke an active caregiver or family member; revocation deactivates the member and removes active sessions.\n\nThe patient controls invitations:

| Role | Access |
|---|---|
| **Patient** | Owns the profile, invites members, manages the plan and records check-ins |
| **Caregiver** | Can manage medication schedules and appointments and record check-ins |
| **Family** | Can view the shared plan, appointments and activity; cannot mutate records |

Invitations are single-use, expire after 24 hours and are stored as hashes. Each invited person creates an individual 6–8 digit PIN.

### 5. Shared care tasks\n\nCreate a follow-up such as arranging transport, preparing for an appointment, checking supplies or coordinating a general callback. Patient and caregiver members can assign it to an active patient/caregiver, set a due time in the profile timezone, complete it or reopen it. The actor is recorded in the activity log. Family remains view-only. These tasks coordinate logistics; they are not medical instructions.\n\n### 6. Activity log

A recent, member-attributed history of profile creation, invitations, medication changes, dose actions and appointment creation. The log helps the care circle understand what was recorded and by whom; it is an operational activity history, not a certified tamper-proof medical record.

### 7. Reminder centre

A consolidated view of reminder records, their type and current delivery state. It also makes the configured dose lead time, missed-check-in grace period and appointment lead times visible.

---

## CareLoop — deterministic reminder and check-in engine

CareLoop converts a recurring medication schedule into dated events in the patient's timezone. The application worker checks profiles on a 60-second cycle and creates reminder records using unique deduplication keys.

~~~mermaid
flowchart TD
    A["Verified medication schedule"] --> B["Materialize dated dose events"]
    B --> C["Pending event in patient timezone"]
    C --> D["Upcoming reminder: 15 minutes before"]
    C --> E{"Check-in recorded?"}
    E -->|"Taken"| F["Taken — attributed to member"]
    E -->|"Skipped"| G["Skipped — attributed to member"]
    E -->|"No check-in after 60 minutes"| H["Missed check-in"]
    H --> I["Missed-check-in follow-up reminder"]
    B --> J["Schedule edited or paused"]
    J --> K["Obsolete future events superseded"]
~~~

### Reminder rules

| Event | Rule |
|---|---|
| Upcoming medication | Queue a reminder approximately **15 minutes before** the scheduled time |
| Missed check-in | After the **60-minute grace window**, mark the event missed and queue a follow-up |
| Appointment | Queue reminders approximately **24 hours** and **1 hour** before the appointment |
| Duplicate prevention | A unique notification key prevents repeated worker cycles from creating the same reminder again |
| Email retry | SMTP failures are retried with a maximum of **three total attempts**; exhausted attempts are marked failed |

A check-in can be recorded as **taken** or **skipped**. Once an event is recorded, a second action is rejected so the history is not silently overwritten. A “taken” status means a member recorded that status—it does not verify ingestion.

### CareLoop Insight

CareLoop Insight is a transparent, rules-based summary of check-in patterns over the last 14 days.

- Events are grouped into morning, afternoon, evening and night.
- A time-period signal is considered only when there are at least **four recorded events** in that period.
- A signal appears when at least **40%** of those events were not marked taken.
- The interface exposes the event count, window, threshold and suggested human follow-up.
- When the sample is too small or the threshold is not met, the app says that no clear pattern is available.

It is descriptive routine support—not a clinical prediction, adherence diagnosis or medication recommendation.

---

## System architecture

~~~mermaid
flowchart LR
    subgraph People
      P["Patient"]
      C["Caregiver"]
      F["Family"]
    end
    UI["Accessible browser UI"] --> API["FastAPI application"]
    P --> UI
    C --> UI
    F --> UI
    API --> AUTH["PIN sessions + role authorization"]
    AUTH --> DB[("SQLite local / PostgreSQL hosted")]
    API --> PLAN["Medication + appointment services"]
    PLAN --> ENGINE["CareLoop event materializer"]
    ENGINE --> OUTBOX["Deduplicated notification outbox"]
    OUTBOX --> SMTP["Optional SMTP delivery"]
    API --> AUDIT["Member-attributed activity log"]
    API --> INSIGHT["Explainable routine signal"]
    INSIGHT --> DB
~~~

### Key implementation decisions

- **Timezone-aware scheduling:** local schedule times are converted to UTC event timestamps and rendered back in the patient's timezone.
- **Explicit event records:** scheduled doses are persisted as individual events, protected by a uniqueness constraint on medication and scheduled time.
- **Idempotent reminders:** notification deduplication is enforced in the database, not only in the browser.
- **Patient-scoped data:** every care-plan query is filtered by the active profile.
- **Human authority:** the application records schedules and check-ins; it does not decide what medicine a person should take.

---

## Security, privacy and accessibility

### Access and session controls

- Individual 6–8 digit PINs; PIN hashes use **scrypt**.
- Random session tokens are stored as SHA-256 digests, not as raw tokens.
- HTTP-only, SameSite=Strict session cookie; hosted deployment enables the Secure cookie flag.
- Sessions expire after 12 hours.
- Patient-created invitations are hashed, single-use and expire after 24 hours.
- Failed login attempts are rate-limited; five failed attempts trigger a 10-minute lockout for the profile/IP key.
- Role authorization and profile scoping are enforced by the API, not just hidden UI controls.
- Security response headers are applied by the FastAPI middleware.

### Accessible interaction

- Large, readable form controls and clear action labels.
- Keyboard-visible focus states and a skip-to-main-content link.
- Responsive desktop and mobile navigation.
- Reduced-motion support.
- High-contrast status labels for upcoming, due, taken, skipped and missed events.

The project has not undergone formal WCAG certification or an assistive-technology audit. Accessibility features are implemented, but certification is not claimed.

---

## Technology stack

| Layer | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Validation | Pydantic v2 |
| Persistence | SQLAlchemy 2 |
| Hosted database | PostgreSQL 18 |
| Local database | SQLite |
| Frontend | HTML5, CSS, vanilla JavaScript |
| Reminder delivery | In-process worker, database outbox, optional SMTP |
| Tests | pytest, FastAPI TestClient, isolated SQLite fixtures |
| CI | GitHub Actions |
| Hosting | Render web service + managed PostgreSQL |

**No generative-AI wrapper is used.** The medication and reminder path is deterministic Python logic. The routine insight is a small, inspectable rules-based aggregation; no external LLM or third-party AI API receives care-profile data.

---

## Run locally

### Requirements

- Python 3.11 or newer.
- Git.
- A modern browser.

### 1. Clone the repository

~~~bash
git clone https://github.com/shashankkumar8/MitraCare.git
cd MitraCare
~~~

### 2. Create a virtual environment

**Windows PowerShell**

~~~powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
~~~

**macOS / Linux**

~~~bash
python3 -m venv .venv
source .venv/bin/activate
~~~

### 3. Install dependencies

~~~bash
python -m pip install -r requirements.txt
~~~

### 4. Seed the local synthetic demo

~~~bash
python -m app.seed_demo
~~~

### 5. Start the application

**Windows PowerShell**

~~~powershell
$env:COOKIE_SECURE = "false"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

**macOS / Linux**

~~~bash
COOKIE_SECURE=false python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

Open **http://127.0.0.1:8000**.

### Local-only synthetic demo accounts

| Role | Profile code | PIN |
|---|---|---|
| Patient | MTDEMO26 | 246810 |
| Caregiver | MTDEMO26 | 135790 |

These credentials are created only by running the local seed command. They are **not present on the public hosted service**. The example schedules and appointment are synthetic and must never be treated as prescriptions or real bookings.

---

## Test and quality checks

Run the backend suite and frontend syntax check:

~~~bash
pytest -q
node --check static/app.js
~~~

The current suite contains **25 tests** covering:

- Profile creation, login, logout, invalid PINs and timezone validation.
- Login lockout and single-use invitation expiry/replay protection.
- Patient, caregiver and read-only family permissions.
- Cross-profile data isolation.
- Medication creation, editing, pausing and superseding obsolete future events.
- Taken/skipped check-ins and rejection of duplicate actions.
- Upcoming and missed reminder idempotency.
- Appointment validation.
- CareLoop Insight minimum-sample behavior.
- SMTP retry and dead-letter behavior using a mocked mail server.
- PostgreSQL URL normalization to the installed psycopg 3 driver.\n- Reminder fan-out idempotency and in-app fallback when members have email addresses.\n- Shared-task assignment, completion attribution and family read-only access.\n- Patient-controlled member revocation and session invalidation.\n- Task Coach consent, category-only local fallback and mocked Gemini Interactions API request with `store: false`.\n- Digit-only login PIN validation and duplicate schedule-time rejection.
- Frontend entry point and static asset delivery.

GitHub Actions runs pytest and the JavaScript syntax check on pushes and pull requests. Automated tests validate software behavior with synthetic fixtures; they are not clinical trials, field testing or proof of email deliverability.

---

## API surface

The complete interactive reference is available at **[Swagger UI](https://mitracare-api-shashank-k8r3-cfr0.onrender.com/docs)**.

| Group | Method | Endpoint | Purpose |
|---|---|---|---|
| Identity | POST | /api/profiles | Create patient profile and start a session |
| Identity | POST | /api/auth/login | Sign in with profile code and PIN |
| Identity | POST | /api/auth/join | Join with a single-use invitation |
| Identity | POST | /api/auth/logout | Revoke current session |
| Identity | GET | /api/me | Read current member and profile |
| Care circle | POST | /api/invites | Patient creates a caregiver/family invite |
| Care circle | GET | /api/members | List active care-circle members |\n| Care circle | DELETE | /api/members/{member_id} | Patient revokes caregiver/family access |\n| Care tasks | GET / POST | /api/tasks | List or create assigned follow-ups |\n| Care tasks | POST | /api/tasks/{task_id}/complete | Complete a follow-up |\n| Care tasks | POST | /api/tasks/{task_id}/reopen | Reopen a follow-up |\n| Task Coach | GET / POST | /api/task-coach | Read AI status or generate a consented category-only checklist |
| Medication | GET / POST | /api/medications | List or create medication schedules |
| Medication | PUT | /api/medications/{med_id} | Update a schedule |
| Medication | PATCH | /api/medications/{med_id}/deactivate | Pause a schedule |
| Dose events | GET | /api/dashboard | Read dashboard, upcoming events and reminders |
| Dose events | POST | /api/doses/{dose_id}/mark | Record a taken or skipped check-in |
| Appointments | GET / POST | /api/appointments | List or create appointments |
| Insights | GET | /api/insights | Read explainable routine signals |
| Reminders | GET | /api/notifications | Read reminder history and delivery states |
| Reminders | GET | /api/settings/reminders | Read reminder configuration |
| Activity | GET | /api/activity | Read recent activity events |
| System | GET | /api/health | Health probe |

---

## Research-informed design

MitraCare's product choices are informed by research on medication adherence and caregiver involvement. The evidence does **not** establish that this prototype improves adherence or clinical outcomes.

| Research | Design implication |
|---|---|
| [Systematic review of medication-adherence strategies in older adults (2026)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12911538/) | Medication support should be multi-component; reminder-only impact should not be overstated |
| [Cochrane review CD012419 — older adults taking multiple medicines](https://www.cochrane.org/evidence/CD012419_interventions-helping-older-adults-prescribed-multiple-medications-use-and-take-their-medications) | Record check-ins descriptively and communicate uncertainty |
| [Caregiver-based medication safety review (2018)](https://pubmed.ncbi.nlm.nih.gov/30136714/) | Include caregivers while preserving the older adult's control and explicit access boundaries |
| [Medication reminder technologies review (2026)](https://pubmed.ncbi.nlm.nih.gov/41642177/) | Treat reminders as one part of a care workflow, not a guarantee of adherence or better outcomes |

See [RESEARCH.md](RESEARCH.md) for the study details and the research-to-feature mapping.

---

## Safety and operational boundaries

MitraCare is a **care coordination and record-keeping prototype**. It does not:

- Diagnose conditions, prescribe medicines or calculate doses.
- Interpret prescriptions, check drug interactions or contraindications.
- Recommend what to do after a missed or uncertain dose.
- Verify that a medicine was physically taken, or that an email was read.
- Connect to an EMR, pharmacy, hospital, insurer or live clinical system.
- Send SMS/WhatsApp notifications or act as an emergency alert service.

Medication details and schedules must be transcribed from a current prescription and checked with the patient's clinician or pharmacist. A reminder is not medical advice; never double a dose because of an app notification.

**Live deployment status:** SMTP credentials and a verified sender have not been configured on the hosted demo, so real email delivery is not enabled. In-app reminders remain available; the email outbox is not evidence of delivery.\n\n**AI configuration:** Task Coach runs in local template mode unless a server-side GEMINI_API_KEY is configured. If configured, the Gemini request contains only one fixed category enum; no task title, notes, profile, member identity, medication or health data is sent. Do not enable external AI in a real-care deployment without reviewing provider terms, the privacy notice and applicable data-protection obligations.

**Before real-world use:** conduct older-adult and caregiver usability testing, clinical workflow review, security and privacy assessment, formal accessibility testing, database migrations and backups, and move reminder processing to a durable monitored worker. The current free-tier demo is not suitable for real patient data or production care.

---

## Judge walkthrough

A focused demonstration can show the complete collaboration loop:

1. Create a synthetic patient profile and sign in.
2. Add a clearly labelled test medication schedule using non-clinical example data.
3. Invite a caregiver and join with a separate PIN.
4. Invite a family member and verify the read-only boundary.
5. Record a dose as taken or skipped and show the member-attributed activity event.
6. Open the reminder centre and explain the 15-minute / 60-minute CareLoop rules.
7. Add a synthetic appointment and show the shared appointment view.
8. Open CareLoop Insight and explain its sample threshold and evidence.\n9. Create “Arrange clinic transport”, assign it to the caregiver, complete it and show who recorded the completion.\n10. Open Task Coach, confirm consent, choose Transport, generate a generic checklist, and add one suggestion as a follow-up. Explain whether Gemini or local template mode ran.\n11. As the patient, revoke a synthetic family member and show that their next login is rejected.

Use synthetic data only during public demonstrations.

---

## Repository structure

~~~text
MitraCare/
├── app/
│   ├── main.py          # FastAPI routes, middleware and reminder worker
│   ├── models.py        # SQLAlchemy data models
│   ├── schemas.py       # Pydantic request contracts
│   ├── database.py      # SQLite / PostgreSQL engine configuration
│   ├── engine.py        # CareLoop, reminders, outbox and routine insight
│   ├── security.py      # PIN hashing, sessions and authorization helpers
│   └── seed_demo.py     # Local synthetic demo data only
├── static/
│   ├── index.html       # Accessible application entry point
│   ├── app.js           # Browser UI and client interactions
│   └── styles.css       # Responsive visual system
├── tests/
│   └── test_core.py     # Backend and workflow tests
├── .github/workflows/
│   └── tests.yml        # CI quality checks
├── render.yaml          # Render web service + PostgreSQL blueprint
├── requirements.txt
├── ARCHITECTURE.md
├── RESEARCH.md
├── DEMO_SCRIPT.md
└── README.md
~~~

---

## Project

**MitraCare** — built for the Catalyst Solo AI Hackathon, challenge: *Elderly Care & Medication Management Platform*.

- **Repository:** [github.com/shashankkumar8/MitraCare](https://github.com/shashankkumar8/MitraCare)
- **Live demo:** [mitracare-api-shashank-k8r3-cfr0.onrender.com](https://mitracare-api-shashank-k8r3-cfr0.onrender.com)
- **API docs:** [Swagger UI](https://mitracare-api-shashank-k8r3-cfr0.onrender.com/docs)



## AI VIBEATHON positioning

MitraCare is a patient-controlled home-care coordination workflow—not the first medication reminder app, a clinical AI assistant or a hardware dispenser. Its AI-enabled component is deliberately narrow: generic task planning from a fixed category. See PRODUCT_STRATEGY.md for competitor analysis and VIBEATHON_SUBMISSION.md for the judge pitch and walkthrough.


## Mitra Companion and continuity packs

A floating **Ask Mitra** companion is available after sign-in. It is a private, deterministic care-coordination guide that works without Gemini or an API key. It uses records available to the signed-in role, does not save chat message text, and cannot diagnose or make medication decisions.

It supports task, appointment, care-circle and reminder questions, plus patient-permission-acknowledged **Clinician Visit Brief** and **Family Care Handover** packs. Review each pack before sharing. The patient or caregiver can create a pack; family remains view-only. Copy, download and print are performed locally in the browser. See [COMPANION_GUIDE.md](COMPANION_GUIDE.md).

Care Tasks with due times also create deduplicated in-app due-soon and overdue notifications. This is a coordination reminder, not an emergency alert. Actual email delivery still depends on verified SMTP configuration.


## Product and engineering scorecard

The internal quality review, measurable household operating metrics, pilot KPI hypotheses and launch gates are documented in [QUALITY_SCORECARD.md](QUALITY_SCORECARD.md). The live app's CareOps Pulse is generated from the active care profile; its percentages are workflow measures, not clinical outcomes.
