# Rural maintenance, interruption and continuing activity

This qualification forked the continuing individual's checkpoint at tick 11123.
The branch continued normally until it had a self-set unfinished familiar-activity
goal. The environment then reduced reserve to 0.03 and set recovery rate to zero.
These are explicitly attributed test interventions; the brain was not told the
physical cause or given a recovery goal.

Across forty actual rural ticks, the creature attempted rest three times, issued
one grounded recovery-help request, conserved through thirty-three held ticks,
and made four later recovery probes. Its body did not move during the fault.
The request referenced actual zero-gain experiences and retained uncertainty
about the cause. The original activity goal remained active.

At tick 11167 the environment restored the recovery rate to 0.5 while preserving
reserve at 0.03. This repair did not grant energy or directly resolve the goal.
The creature had to observe recovery through its own subsequent rest actions.
It resumed and completed the original familiar-activity goal at tick 11213.
During the 256 ticks following repair, it made 125 approach actions, 16 practice
interactions, 97 exploration actions, ten ordinary rest actions, one recovery
probe and seven conserving holds. A new process then loaded its checkpoint and
continued twenty ticks; its complete resulting checkpoint exactly matched the
uninterrupted branch.

The source object and full pre-branch history were preserved. No fault, repair,
request, or test outcome was merged into the live companion. No production code
or live service changed during this qualification.

## Actual lived history audit

A separate read-only audit covered 1,024 real experiences from ticks 10194–11217.
It recorded 919 movement outcomes, 64 activations, twenty rests and twenty-one
holds. All observed rest gains were 0.5 within floating-point precision. This
window spans implementation updates and multiple decision-producing components;
it is not a controlled version comparison. Its mostly travel-and-familiar-play
routine is limited evidence of ordinary activity, not proof of rich companionship.

## Evidence and reproduction

Run examples/persistent_individual/world_recovery_probe.py with the project
virtualenv and PYTHONPATH=src:examples/persistent_individual. It reads the current
live checkpoint through HabitatStore and refuses to overwrite its evidence
directory. A future live checkpoint is a different starting condition.

validation/world-recovery/ contains the before-failure checkpoint, portable
restart-before and restart-after checkpoints, source SHA, actual probe log,
summary, lived audit and post-run live-state readback. The live individual was
still running without error on V18 at the final readback.

This qualifies one imposed fault and externally supplied repair in the rural
body. The creature selected conserving, probing, assistance and resumption, but
did not diagnose or repair executable recovery code. Sensor recognition,
broader autonomous activity, general repair and sustained owner-perceived
companionship remain unfinished.
