# Mitra Companion and continuity packs

## What it is

The Mitra Companion is a local, deterministic care-coordination guide. It works without a Gemini API key, makes no external AI request, and does not persist chat message text. A usage-only audit event is stored without the message or response. Chat is authenticated and limited to 40 requests per member per 10-minute window.

It answers supported questions using records already available to the signed-in member: priorities, open tasks, appointments, medication schedules entered in MitraCare, care-circle roles and reminder rules. It is not a general-purpose AI assistant.

## Continuity packs

**Clinician visit brief** assembles active user-entered medication schedules, recent check-ins, appointments and neutral questions to verify with a clinician or pharmacist.

**Family handover** assembles open and recently completed tasks, task owners, appointments, upcoming scheduled check-ins, recent activity and active care-circle roles.

The patient or caregiver must acknowledge that the patient has permitted the brief to be prepared/shared. Family members retain view-only access and cannot generate an export. Review every entry before sharing. Copy/download/print happens in the browser; reports are not automatically emailed.

## Safety and privacy

- Never use the companion to diagnose, interpret symptoms, recommend treatment, change prescriptions, calculate doses, assess drug interactions or advise after a missed/late dose.
- For medicine decisions, contact the prescribing clinician or pharmacist and follow the current prescription. For emergencies, contact local emergency services; MitraCare cannot triage or dispatch.
- Chat text and replies are not persisted. A usage-only audit event is recorded.
- Reports contain sensitive care-related details. Use synthetic data in public demos and share only with the patient's permission.
- A recorded “taken” check-in is not proof of physical ingestion. Medication details are user-entered and must be verified against the current prescription and packaging.

## API

| Method | Route | Purpose |
|---|---|---|
| POST | /api/companion/chat | Authenticated local response to one question |
| POST | /api/companion/brief | Prepare a visit or handover dataset after permission acknowledgement |

Chat body:

~~~json
{"message":"What needs attention today?"}
~~~

Brief body:

~~~json
{"kind":"visit","consent":true}
~~~

The brief endpoint returns structured profile data for the browser's copy/download/print renderer. It does not send data to an LLM.
