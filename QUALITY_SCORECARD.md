# MitraCare — product and engineering scorecard

**Assessment date:** 25 November 2026  
**Assessment type:** Internal evidence-based product review. This is not an independent security audit, clinical validation, customer study, or market benchmark.

## Executive judgement

MitraCare is best positioned as a **patient-owned household care-operations workspace**: it connects the daily routine to named responsibilities, appointment preparation, and continuity handovers. The differentiator is the connected workflow and patient-controlled care circle—not the presence of a chatbot.

**Current internal maturity estimate: 3.2 / 5.0.** The core workflow is demonstrable and automated tests cover important role and safety boundaries. The score is deliberately held back by the absence of independent security review, older-adult usability testing, durable production job infrastructure, account recovery, billing, and validated customer demand. It is not a clinical quality score.

## Product capabilities added in this release

| Capability | Working behaviour | Evidence / boundary |
|---|---|---|
| Visit Ready Kit | A future appointment can generate four practical tasks: confirm details, gather requested records, arrange transport/companion, and prepare questions | Tasks are assigned to the acting patient/caregiver; repeat requests return the existing kit instead of duplicating it |
| CareOps Pulse | Calculates manual check-in recording, task ownership, 30-day task completion, overdue follow-ups and visit-preparation coverage | Computed from one authenticated care profile; empty denominators show “—” rather than fabricated 0% |
| 7-day operating trend | Shows scheduled events versus person-recorded outcomes by local calendar day | Counts taken/skipped actions; does not assert that a dose was physically ingested |
| Existing continuity workflow | Medication schedules, shared tasks, appointments, reminders, local companion, clinician visit brief, family handover and activity attribution | User-entered coordination records; not a medical record or clinical decision support |

## Internal quality rating

| Dimension | Rating / 5 | Why | Next proof required |
|---|---:|---|---|
| Core workflow completeness | 4.0 | Authentication, patient-controlled invitations/revocation, schedules, check-ins, tasks, appointments, reminders and handovers are implemented | Observe complete household workflows with real pilot users using synthetic data |
| Workflow integration | 3.7 | Visit preparation now creates work in the same task queue; CareOps Pulse measures the same operating loop | Track kit completion and interview patients/caregivers about usefulness |
| Reliability and QA | 3.2 | Automated API tests, role checks and CI syntax checks cover key paths | Browser E2E, accessibility automation, load/soak tests, backup/restore exercise and alerting |
| Security and privacy | 2.8 | PIN hashing, HttpOnly session cookie, role-scoped queries, expiring single-use invites and security headers exist | Independent threat model and penetration test; MFA/recovery; retention/deletion controls; production secrets and backups |
| UX and accessibility | 3.0 | Responsive interface, focus states and role-specific controls exist | Older-adult and caregiver usability studies; screen-reader and WCAG audit; test at large text sizes |
| Clinical safety boundaries | 3.7 | No diagnosis, treatment, dosage or interaction recommendations; exports are consent-gated | Clinician/pharmacist review of copy and workflows; formal clinical safety assessment before any regulated claims |
| Commercial readiness | 1.8 | A coherent household workflow and pricing hypotheses exist | Paid pilot, willingness-to-pay interviews, retention cohorts, support cost and unit economics |

The weighted estimate uses the dimensions above with emphasis on security, core workflow and reliability. Scores are judgement calls, not certified benchmarks.

## Live household metrics

The authenticated `GET /api/scorecard` endpoint is designed for the current care profile. It is **not** an organisation-wide analytics or telemetry system.

| Metric | Definition | Interpretation guardrail |
|---|---|---|
| Human-recorded check-ins · 7 days | Scheduled dose events in the past 7 days with an explicit taken/skipped action, divided by all non-superseded scheduled events in that period | A record is not proof of ingestion or treatment adherence |
| Open task ownership | Open coordination tasks assigned to an active patient/caregiver, divided by all open tasks | High ownership means a person is named; it does not prove the work happened |
| Follow-up completion · 30 days | Tasks created in the past 30 days and marked completed, divided by tasks created in that period | Completion is a workflow status, not an outcome measure |
| Visit prep coverage | Upcoming appointments in the next 30 days with at least one Visit Ready Kit task, divided by upcoming appointments | A kit being created does not mean it has been completed |
| Visit prep task completion | Completed preparation tasks for upcoming visits divided by all such tasks | This is a household logistics measure only |
| Overdue follow-ups | Open tasks whose due time has passed | Review and reassign; this is not a medical urgency classification |

Where a denominator is zero, the API returns `null` and the interface displays “—”. The 7-day series uses the profile's configured timezone.

## Pilot KPI hypotheses — targets, not achieved results

These are proposed experiment thresholds. MitraCare has not yet demonstrated these outcomes with a representative user cohort.

| Pilot KPI | Initial target | How to validate |
|---|---:|---|
| New household activation | ≥70% add one routine and invite one care-circle member within 48 hours | Instrument consented onboarding events; interview drop-offs |
| Open follow-up ownership | ≥90% | Review household scorecards weekly |
| 30-day follow-up completion | ≥75% | Cohort analysis, not a single demo profile |
| Visit prep coverage | ≥80% of eligible upcoming visits | Measure generated kits across a pilot |
| Visit prep task completion | ≥70% before the appointment | Compare task completion timestamps with visit start |
| 30-day household retention | ≥35% | Cohort-based active household definition, agreed before launch |
| Shared-handoff usefulness | ≥4.3 / 5 average rating | Short patient and caregiver survey after a handover |

Do not use check-in percentages as a proxy for medication effectiveness, patient safety, or clinical adherence. Avoid gamification or pressure based on a missed check-in.

## Release gates before real patient data

1. Move reminders from an in-process web worker to a durable queue/worker with retry, monitoring and idempotent delivery across restarts.
2. Confirm production database lifecycle, scheduled backups and a tested restore. The current demo infrastructure may sleep and is not an uptime commitment.
3. Add account recovery and review session expiry, throttling, CSRF posture and invitation abuse controls with a security reviewer.
4. Implement explicit data export/deletion, retention policy and privacy notices; complete a data-flow and threat review.
5. Run accessibility and usability tests with older adults and caregivers; validate plain-language copy.
6. Obtain clinician/pharmacist review of all health-adjacent labels and the visit brief before any clinical-safety claims.
7. Validate demand and pricing through interviews and a paid pilot before claiming product-market fit or revenue.

## Positioning statement

**MitraCare keeps a household's care responsibilities visible and owned—from routine check-ins to visit preparation and family handover—while the patient remains in control.**

The product complements clinicians and caregivers. It is not an emergency-response service, medical record, diagnostic tool, medication decision engine, or substitute for professional care.
