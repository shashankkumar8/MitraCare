# 100-second judge demo — MitraCare

**Use only the synthetic demo workspace. Do not enter real patient information.**

### 0:00–0:12 — The real gap
“Medication reminders usually stop at an alarm. But an older adult’s routine involves the person, a caregiver, and family members who need visibility without taking away the patient’s control. MitraCare makes that workflow shared and accountable.”

### 0:12–0:30 — Shared access
“Here is the patient workspace. The patient can invite a caregiver or family member using a single-use code. Each person gets their own PIN. The caregiver can manage the plan; family access is read-only.”

Show Care circle and the three role descriptions. (In a fresh demo, generate an invite and show the code; optionally open a second private browser for the joined role.)

### 0:30–0:50 — A working medication loop
“Schedules are entered from a clinician-verified prescription. CareLoop materializes dose events in the patient’s local timezone. A check-in can be recorded as taken or skipped. A second attempt cannot overwrite the first record.”

Open Medication check-ins, record one synthetic event, and show that the dashboard/activity updates.

### 0:50–1:08 — What makes it more than CRUD
“CareLoop queues one reminder before the scheduled time. If no check-in is recorded inside the grace window, the event is flagged as a missed check-in and escalated. A database uniqueness constraint prevents duplicate reminders when the worker runs again. SMTP delivery has bounded retries and a visible history.”

Show Reminder centre and explain configured vs unconfigured email. Do not claim email is working until a real mailbox has received the test message.

### 1:08–1:22 — Explainable insight, not unsafe AI
“The routine signal looks for repeated unconfirmed check-ins by time of day. It shows the sample size and exact rule. It suggests asking the patient about reminder friction; it never diagnoses or recommends changing a medicine. We deliberately keep clinical decisions out of an LLM.”

Show CareLoop signal and its method/evidence.

### 1:22–1:40 — Reliability and close
“We tested role boundaries, failed PINs and lockout, schedule validation, duplicate actions, reminder idempotency, missed-check-in transitions and appointment validation. The prototype is synthetic-data only and needs field usability testing and clinical review before real-world use.”

**Close:** “MitraCare turns isolated medication alarms into a patient-controlled care loop — with trusted access, clear check-ins, and a traceable handoff.”
