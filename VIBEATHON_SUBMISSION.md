# MitraCare — PromptWars × Echo Engineers AI VIBEATHON 2026

## Project name
MitraCare — patient-controlled care coordination

## One-line pitch
MitraCare connects patient, caregiver and family around one patient-owned care plan—turning medication check-ins, appointments and practical follow-ups into an accountable workflow, with an optional privacy-bounded AI Task Coach.

## Problem
At-home care is often coordinated across separate reminders, calls, calendars and messages. A reminder may fire, but it does not assign someone to arrange transport, prepare for a visit, check supplies or record completion. Shared accounts can obscure who changed a plan.

## Solution
- Patient-owned profile and individual accounts.
- Patient, caregiver and view-only family permissions.
- Medication schedules transcribed from a current prescription and converted to dated events.
- Taken/skipped/no-check-in states with actor attribution.
- Deterministic upcoming, missed-check-in and appointment reminders.
- Assignable practical follow-ups with due dates and completion attribution.
- Patient-controlled revocation of invited access.
- Generic AI Task Coach for non-clinical coordination checklists.

## AI component
Task Coach uses a fixed category (appointment, transport, supplies, follow-up or other) and requires explicit consent. If a server-side Gemini API key is configured, only that category enum is sent to the Gemini Developer API. The user's task title, description, profile code, member identity, email addresses, medication names, prescription instructions and health details are not included.

The model is instructed to produce four concise non-clinical checklist items. Output is filtered for clinical terms and limited to four short items. The user reviews each idea before adding it as a shared task. If Gemini is not configured or fails, local templates are returned and labelled as templates, not AI. No key is exposed in frontend code.

## Why AI here
AI helps with generic task decomposition. Dose timing and check-in states remain deterministic software rules; AI does not decide whether someone should take, skip, repeat, start or stop medication.

## Honest differentiation
Medication reminders, caregiver alerts and shared records already exist in Medisafe, Hero, Birdie and CareClinic. MitraCare's prototype angle is a lightweight, patient-owned circle combining role-based identities, attributed check-ins, assignable follow-ups, revocable access and a privacy-bounded category-only task coach. This is a positioning hypothesis, not a market-first claim.

## Technical implementation
Python, FastAPI, Pydantic v2, SQLAlchemy 2; PostgreSQL hosted / SQLite for tests; vanilla JavaScript/HTML/CSS; deterministic CareLoop; optional server-side Gemini REST integration; pytest, GitHub Actions and Render.

## Judge walkthrough (6–8 minutes)
1. Explain the coordination gap at home.
2. Create a fictional patient profile; invite caregiver and family accounts.
3. Add a synthetic schedule; record a check-in and show member attribution.
4. Create Arrange clinic transport, assign it to caregiver and complete it.
5. Open Task Coach; show the category input and explicit consent. State whether Gemini or local template mode is running.
6. Add one suggestion as a follow-up.
7. Revoke synthetic family access and show login rejection.
8. Close with safety and hosting limits.

## Evaluation fit

| Dimension in current Unstop listing | Evidence to demonstrate |
|---|---|
| Innovation | Reminder-to-task workflow and category-only AI coach |
| Technical feasibility | Working FastAPI/PostgreSQL app, role permissions, persistent tasks, regression tests |
| Scalability | Profile-scoped data model; disclose current single-process reminder worker limitation |
| Problem fit and impact | Patient → caregiver → family coordination story |
| Resilience | Deterministic reminder rules, database dedupe, template fallback |
| Presentation | End-to-end demonstration with live app, source and honest boundaries |

## Verified links
- Live app: https://mitracare-api-shashank-k8r3-cfr0.onrender.com
- API health: https://mitracare-api-shashank-k8r3-cfr0.onrender.com/api/health
- Swagger: https://mitracare-api-shashank-k8r3-cfr0.onrender.com/docs
- GitHub: https://github.com/shashankkumar8/MitraCare
- Product strategy: PRODUCT_STRATEGY.md

## Event date and prize discrepancies — check your registered Team Dashboard

The participant-page text previously supplied in this conversation described a 25–28 November timeline (registration closing 25 November, submission 25–26 November, offline finale 28 November) and prize rows totalling ₹50,000. The current Unstop listing for AI Vibeathon 1.0 instead shows registration ending 17 December 2026 at 9:00 PM IST, online evaluation on 17 December, and an eight-hour offline finale on 19 December 2026, 9:00 AM–5:00 PM IST in Delhi. Unstop's listing also contains conflicting prize summaries in different sections. Confirm the exact round, submission portal, dates and prizes in your Team Dashboard and organizer updates; do not assume the older pasted timeline is current.

## Safety and limitations
- Synthetic data only for hackathon demos.
- Not a medical device, not clinically validated and not production-ready.
- No diagnosis, treatment advice, prescription interpretation, dose calculation, interaction checking or emergency dispatch.
- SMTP is not configured on hosted deployment; do not claim live email delivery.
- Gemini Task Coach stays in template mode unless the operator sets a server-side key.
- Current Render free service may sleep; hosted free database is temporary and scheduled to expire 15 December 2026.
