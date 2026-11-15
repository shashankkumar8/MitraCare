# Catalyst submission checklist

The selected challenge is **Elderly Care & Medication Management Platform**.

## Verified project links

- **Public GitHub repository:** https://github.com/shashankkumar8/MitraCare
- **Live application:** https://mitracare-api-shashank-k8r3-cfr0.onrender.com
- **API health:** https://mitracare-api-shashank-k8r3-cfr0.onrender.com/api/health
- **Interactive API docs:** https://mitracare-api-shashank-k8r3-cfr0.onrender.com/docs

## Deployment status

The app is deployed as one FastAPI service on Render, backed by managed PostgreSQL 18 in Singapore. The deployment reports `live`, and Render health checks have returned HTTP 200 from `/api/health`.

The hosted service does **not** seed public demo credentials. Create a new patient profile from the welcome screen, then use patient-controlled one-time invitations to add caregiver/family test members.

**Email is not configured yet.** The application supports SMTP when valid sender credentials are supplied, but do not claim that real email reminders are delivered until SMTP is configured and an end-to-end mailbox test succeeds. In-app reminders are available.

**Free-tier warning:** the Render free web service may sleep after inactivity. The free PostgreSQL database is scheduled to expire on **15 December 2026**. This deployment is a hackathon demonstration only. Do not enter real patient data or rely on it for care. For sustained use, upgrade to durable hosting/database, configure backups, secrets and monitoring, and complete security, privacy, usability and clinical validation.

## Final Unstop/Hack2Skill fields

1. **Challenge:** select `Elderly Care & Medication Management Platform`.
2. **Public GitHub Repository Link:** paste the public repository URL above.
3. **Deployed Link (Cloud Run URL):** the event form wording says Cloud Run, but this project is deployed on Render. Paste the actual live Render URL above only if the submission form accepts any deployed HTTPS URL. Do not represent it as a Cloud Run URL. If the form strictly validates a `*.run.app` URL, a separate Cloud Run deployment is required.
4. **LinkedIn Post:** publish the draft below after replacing any placeholders with the verified links, then paste the actual public post URL into Unstop.

## Judge demo flow

1. Open the live application and create a new synthetic patient profile.
2. Save the generated profile code and sign in with the patient PIN.
3. Add a clearly labelled test medication schedule using non-clinical synthetic details.
4. Create one caregiver invitation; join from a separate browser/session with a separate PIN.
5. Create one family invitation and verify that the family role is read-only.
6. Record a dose as taken or skipped; verify the activity log and shared view update.
7. Add a synthetic doctor appointment and inspect appointment reminders.
8. Show the reminder centre and the CareLoop explanation.

Use only synthetic data. Do not use a real person's prescription, health history, email address, or personal data in a public demonstration.

## LinkedIn post draft

```text
Built MitraCare for Catalyst — a patient-first shared care platform for elderly medication and appointment coordination.

The core idea: a medication reminder should not stop at an alarm. MitraCare connects the patient, invited caregivers and family members through individual PIN-based access, role-specific permissions, dose check-ins, appointment reminders and a traceable activity log.

What I focused on:
• A deterministic CareLoop engine for upcoming and missed check-in reminders, with deduplicated notifications.
• Patient-controlled invitations and separate patient / caregiver / family permissions.
• An explainable routine-friction signal that shows its evidence and never gives clinical advice.
• Security, accessibility, edge-case testing and clear operational limits instead of a chatbot wrapper.

This is a synthetic-data hackathon prototype, not a clinically validated product. The hosted demo uses a temporary free-tier database; email delivery is not configured. Real-world use would require older-adult usability testing, clinician review, security/privacy assessment and reliable production infrastructure.

Repository: https://github.com/shashankkumar8/MitraCare
Live demo: https://mitracare-api-shashank-k8r3-cfr0.onrender.com

#Catalyst #MakersNeedMore #Hackathon #HealthTech #AIEngineering #Accessibility #ElderlyCare
```

Do not claim clinical validation, production readiness, successful email delivery, or a Cloud Run deployment. The project is a working hackathon prototype with the limitations above.
