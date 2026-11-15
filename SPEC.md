# Product specification — MitraCare

## Product thesis

Medication management at home is a shared coordination problem, but many reminder apps assume one technically confident user with one phone. MitraCare provides one patient-controlled source of truth with per-person access and clear responsibility records, while preserving the patient's role in decisions.

## Primary actors

- Patient: owns the profile, creates the PIN, invites members, manages their care information.
- Caregiver: invited by the patient; may add/pause verified schedules, appointments and record check-ins.
- Family: invited by the patient; can view schedules, appointments, reminder history and activity but cannot mutate data.

## Core journey and acceptance criteria

1. Patient creates profile → receives a unique profile code → session is created securely → code must be saved for future login.
2. Patient invites a named caregiver/family member → receives a one-use random invitation code → the code expires in 24 hours → invitee sets their own PIN.
3. Patient/caregiver adds medication with name, strength, route, schedule times, start/end dates and optional prescription-transcribed instructions → server validates dates/times → dose events materialize in the profile timezone.
4. At 15 minutes before dose time, reminder outbox receives one upcoming event per recipient. At 60 minutes after scheduled time, if still pending, event becomes `missed` (meaning no check-in was recorded) and one escalation is queued per recipient.
5. Patient/caregiver records `taken` or `skipped` once. The action is attributed to that member. A second mutation returns HTTP 409 rather than silently overwriting history.
6. Patient/caregiver adds appointment with clinician/date/location/notes. Appointment reminders queue at approximately 24 hours and 1 hour before start.
7. Each critical mutation writes an audit record. Family has GET-only access to these features and is blocked from mutations by role checks.
8. CareLoop analyzes only recorded history, shows the period/sample/threshold behind a signal and never recommends medication changes.

## Non-functional requirements

- Patient-first language; large touch targets and readable typography.
- All schedule times anchored to profile timezone and converted to UTC for storage.
- Unique event keys prevent duplicate dose rows; unique notification keys prevent duplicate reminder rows.
- PIN secrets and invitation codes are never stored in plaintext; session token stored as SHA-256 digest.
- Login brute-force throttle: five failed attempts for a profile-code/IP key trigger a 10-minute lockout.
- Cookies are HTTP-only, SameSite=Strict, 12-hour expiry; HTTPS deployments set Secure.
- Mutating APIs enforce patient/caregiver roles; family role is read-only.
- No uncontrolled clinical inference, LLM-based dosage interpretation or unverified medication content.

## Explicit exclusions

Diagnosis, prescribing, drug interaction checking, dose calculations, missed-dose instructions, refill ordering, remote monitoring, emergency dispatch, EMR integrations, pharmacy fulfillment, OCR of labels, predictive clinical risk scores.

## Definition of done for this challenge build

- App loads, API starts, synthetic demo can sign in.
- One patient profile, caregiver invite, family read-only permission, medication and appointment forms work.
- Dose-state transitions and notification idempotency have automated tests.
- README documents setup, limits and deployment prerequisites.
- Public repository and deployed URL are still a user-side submission step; no hosting account is assumed.
