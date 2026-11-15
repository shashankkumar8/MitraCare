# Catalyst submission checklist

The required challenge is **Elderly Care & Medication Management Platform**.

## Required Unstop/Hack2Skill fields

1. **Challenge:** select `Elderly Care & Medication Management Platform`.
2. **Public GitHub Repository Link:** push this `mitracare` folder to a public GitHub repository and paste its HTTPS URL. Do not submit a private repo.
3. **Deployed Link (Cloud Run URL):** deploy using `README.md` and paste the actual HTTPS `*.run.app` URL. Do not paste localhost or a guessed URL.
4. **LinkedIn Post:** publish a post and paste its public HTTPS URL. A draft is below.

## Publish repository

From this folder after reviewing `.gitignore` and confirming no `.env` or database file is present:

```bash
git init -b main
git add .
git status
git commit -m "Build MitraCare shared elderly care platform"
# Create an empty PUBLIC repository named mitracare on GitHub, then:
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/mitracare.git
git push -u origin main
```

Verify the repository opens in a private/incognito browser window. Confirm the README, source files and test files are visible. Check that `.env`, `*.db`, SMTP passwords and real health data are not committed.

## Publish the demo

Follow the Cloud Run steps in `README.md`. Create Cloud SQL/PostgreSQL and SMTP credentials first. Verify sign-in, caregiver invite, family read-only access, medication creation, check-in, appointment and at least one delivered test email. Copy only the actual Cloud Run URL from the deployment output.

## LinkedIn post draft

```text
Built MitraCare for Catalyst — a patient-first shared care platform for elderly medication and appointment coordination.

The core idea: a medication reminder should not stop at an alarm. MitraCare connects the patient, invited caregivers and family members through individual PIN-based access, role-specific permissions, dose check-ins, appointment reminders and a traceable activity log.

What I focused on:
• A deterministic CareLoop engine for upcoming and missed check-in reminders, with deduplicated notifications.
• Patient-controlled invitations and separate patient / caregiver / family permissions.
• An explainable routine-friction signal that shows its evidence and never gives clinical advice.
• Security, accessibility, edge-case testing and clear operational limits instead of a chatbot wrapper.

This is a synthetic-data hackathon prototype, not a clinically validated product. Real-world use would require older-adult usability testing, clinician review, security/privacy assessment and reliable production notification infrastructure.

Repository: [PASTE PUBLIC GITHUB URL]
Live demo: [PASTE VERIFIED CLOUD RUN URL]

#Catalyst #MakersNeedMore #Hackathon #HealthTech #AIEngineering #Accessibility #ElderlyCare
```

Only publish after replacing both placeholders with verified URLs and confirming the app/demo works. Do not claim that it is deployed, clinically validated, or sent real emails unless those checks have actually succeeded.
