# Rejected activity-recency candidate

A candidate v27 ranked eligible familiar activities by last selection event,
then retained visible-effect preference and distance. It preserved prior model
behavior behind a version gate. Its source is retained only under
validation/activity-recency/rejected-*.py; production source was reverted to v26.
No live migration or service restart occurred.

From the same saved history used for changed-workshop qualification, the candidate
made zero lantern trials during 256 inert-device moments and zero during 256
repaired-device moments. Twelve subsequent restored ticks matched exactly.
Restoration passed, but the behavioral objective failed. Ten focused/regression
tests ran: nine passed and history-dependent voluntary preference failed, because
recency overrode the expected preference. The baseline preference test was rerun
after reversion; its result is in reverted-preference.log.

The candidate's final 512 event records include 248 familiar-activity approach
moments and seven familiar interactions. This rules out claiming that all the
berry activity was initial discovery. Ranking alone did not solve opportunity
coverage. Next investigation must trace active-goal creation, eligibility and
completion at each selection opportunity, including whether depleted plots keep
an active goal blocking new choices. That explanation remains a hypothesis.

Evidence: validation/activity-recency/probe.log, changed.json, recovered.json,
after.json, regressions.log and the preserved rejected source. The branch lineage
explicitly identifies the candidate test. Do not load its v27 checkpoint into the
v26 live service. The full companion goal remains incomplete.
