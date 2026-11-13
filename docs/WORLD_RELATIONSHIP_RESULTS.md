# Rural relationship behavior on continuing-history test branches

This qualification used the continuing individual's current saved history as a
read-only source. It forked a test branch, supplied reported availability, and
waited for the creature to issue its own invitation during actual rural activity.
The invitation referenced retained successful teaching: its guidance record was
supplied information and its teaching outcome was a real experience record.
No new lesson or activity goal was prescribed by this probe.

At tick 9873, the offered invitation was forked into three explicit test branches.
The only response difference was join, decline, or quiet. Join and decline
branches received repeated reported availability every thirty ticks; quiet did
not. These are simulated reports in test context, not claims that the person
actually participated.

| Response | Outcome over 160 actual body ticks |
| --- | --- |
| Join | Activity completed with reported participation. Later invitations at 9919 and 9981. |
| Decline | Refusal retained; activity completed independently. Next invitation at 10001, respecting the 128-tick cooldown. |
| Quiet | Offered invitation closed; activity completed independently; no later invitations. |

All three branches restored and continued for eight additional ticks with exact
event and checkpoint equality. This continuation comparison used an in-process
restore, not a separate-process restart. Their 160-tick actual body traces were
identical, while later invitation timing differed. Thus the response affected
communication without stopping or redirecting independent activity in this case.
The initial state and history of the source object remained unchanged. No test
experiences were merged into the continuing live individual.

## Reproduction and retained evidence

Run examples/persistent_individual/world_relationship_probe.py with PYTHONPATH
including src and examples/persistent_individual, using the project virtualenv.
The probe reads runs/habitat-visual-qualification/current.json through HabitatStore
and refuses to overwrite an existing validation/world-relationship directory.
It qualifies the checkpoint read at execution time; a later live checkpoint is a
different starting condition. The invitation checkpoint retained in invited.json
pins this run's branch point. Each response receipt retains its lineage, actual
test events, goal, invitations and checkpoint hash. summary.json and
paired-comparison.json retain the asserted outcomes. source-sha256.json pins the
probe source; probe.log records the executed cases.

## Meaning and limits

This extends earlier relationship evidence into the actual rural body using the
continuing individual's teaching history. It establishes grounded voluntary
invitations, response-dependent timing, and respecting quiet in these three
branches. It does not establish sensory recognition, understanding the person's
real availability, long-term routine learning, or broad social understanding.
Availability and responses use one explicitly reported companion channel. The
cooldown is an authored mechanism, not a learned general model of the person.
There is no partner selection.

No runtime implementation or live service was changed for this qualification.
The full companionship and self-development end goal remains unfinished.
