# Research notes — design choices for MitraCare

This is a focused evidence scan to inform product design, not a systematic review conducted by this project. The studies below support a patient-centred, multi-component approach but do **not** prove that this prototype improves clinical outcomes.

## 1. Medication adherence interventions in older adults

**Scotti et al., “Enhancing Medication Adherence in Older Adults: A Systematic Review of Evidence-Based Strategies,” Journal of the American Geriatrics Society, 2026 issue (published online 30 Dec 2025), DOI: 10.1111/jgs.70257.** The review included 128 studies (96 RCTs, 16 pre–post, 9 non-RCT and 7 longitudinal evaluations). It reports that most interventions improved adherence, but the evidence was heterogeneous and effectiveness was often limited to short or medium term. It also notes that many studies focus on single diseases rather than patient-centred management across multimorbidity/polypharmacy.

**Product implication:** do not stop at a single alarm. Provide a shared care routine, patient/caregiver participation, activity history, appointment coordination and a gentle follow-up workflow. Do not claim a quantified clinical benefit from a reminder feature alone.

Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC12911538/

## 2. Multiple-medication routines and certainty of evidence

**Cochrane Review CD012419, “Interventions for helping older adults prescribed multiple medications to use and take their medications.”** The review identified 50 studies involving 14,269 participants. Intervention types varied (education, behavioural reminders/packaging, and mixed approaches); study methods and outcome measurement varied substantially, and overall certainty was low to very low for many outcomes.

**Product implication:** provide a configurable, clinician-transcribed routine, explicit check-in states and an accessible interface, while presenting adherence metrics as descriptive records rather than proof of medication ingestion or treatment success.

Source: https://www.cochrane.org/evidence/CD012419_interventions-helping-older-adults-prescribed-multiple-medications-use-and-take-their-medications

## 3. Caregiver-focused medication safety

**“Caregiver-Based Interventions to Optimize Medication Safety in Vulnerable Elderly Adults: A Systematic Evidence-Based Review,” PMID 30136714 (2018).** The review found only eight studies meeting its inclusion criteria, with varied interventions and mixed measured effects. It discusses education and collaborative case-management approaches, but the evidence base is limited.

**Product implication:** a caregiver should be part of the process without silently displacing the older adult. MitraCare uses patient-owned invitations, named actions and a role-based view rather than giving every family member unrestricted edit rights.

Source: https://pubmed.ncbi.nlm.nih.gov/30136714/

## 4. Reminder technologies in home-dwelling older adults

**“Effects of using medication reminder technologies by home-dwelling older citizens: a systematic review,” Age and Ageing, 2026, DOI 10.1093/ageing/afag007.** This review considered 23 original studies and nine systematic reviews (43 original studies in the included evidence synthesis). It reports moderate evidence for some clinical health outcomes, but did not find significant effects on patient/carer experiences or cost-effectiveness and notes that more high-quality research is needed.

**Product implication:** reminders are one part of an ecosystem, not a guarantee of adherence or improved health. Offer reminders plus shared context, but keep clear delivery-state labels and avoid claiming that an email has been read or that a dose was physically taken.

Source: https://pubmed.ncbi.nlm.nih.gov/41642177/

## Research-to-build translation

| Evidence-informed concern | Implemented response |
|---|---|
| Older adults may need support without loss of agency | Patient is profile owner and controls invitations |
| Medication management is shared and burdensome | Caregiver role, family view-only role, shared schedule |
| Reminder-only interventions have uncertain/heterogeneous effects | Add check-in state, audit history, appointment prompts and human follow-up cues |
| A reminder does not prove ingestion | UI says “recorded check-in”; metrics are descriptive |
| Medication decisions are high stakes | No diagnosis, dose interpretation, interaction checker or missed-dose recommendation |
| Communication can fail | Notification outbox, idempotency key, bounded retries, visible pending/failed status |

## Unresolved research questions

A real pilot should evaluate usability with older adults with varied vision, dexterity, health/digital literacy, language and cognitive needs; caregiver burden; reminder fatigue; email reach/delivery; accessibility with assistive technology; and privacy expectations. A clinical partner must review medication workflows and escalation language. None of those field studies has been performed for this hackathon prototype.
