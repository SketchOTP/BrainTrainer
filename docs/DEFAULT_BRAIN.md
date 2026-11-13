# Default creature brain: integration boundary

`DefaultBrain` is the genome-driven neural kernel, available without loading a
world, pet, body, or action executor. It is a native-informed research reference,
not a claim of complete Docking Station or biological equivalence. Each creature
owns its own brain instance and its own checkpoint. The same kernel can be
connected to different bodies by adapting their signals; the supplied program's
lobe meanings, category indexes, chemical indexes, and decision mappings remain
part of that program's contract and must not be treated as universally identical.

```python
from creature_brain import DefaultBrain

brain = DefaultBrain.from_file('/absolute/path/to/owner-supplied-program.json',
                               seed=7, age_stage=3, sex='female')
# The host maps its own sensors and body to the chosen program's neuron indexes.
chemicals = [0.0] * 256
output = brain.tick({'driv': {2: 0.6}, 'visn': {3: 0.5}}, chemicals)
print(output.attention, output.decision, output.action, output.tick)
checkpoint = brain.to_dict()
restored = DefaultBrain.from_dict(checkpoint)
```

`DefaultBrain` and `GenomeBrain` refer to the same implementation. A host must
provide a supported `dna3` genome or normalized brain-program JSON; no game genome
is bundled with this API. The current program decoder supports a bounded subset of
format records and construction-time age/sex expression, rejects unsupported
nonzero variants, and does not implement live development. Supply an owner-owned
program appropriate for the intended use.

## What the host owns

- **Perception and body:** Map real sensor and body measurements to the lobe and
  neuron indexes of the selected program. `tick` accepts sparse index/value maps
  or complete lobe vectors. Values must be finite and normalized to -1..1.
  Specify 256 finite chemical concentrations in 0..1; omitting `chemicals`
  retains the last vector. Do not silently invent measurements or treat a
  missing sensor as a known zero.
- **Time:** The host calls `tick` on its own schedule. A tick is one brain
  update, not a guaranteed wall-clock duration. Match the real system's timing
  and validate it for the intended embodiment.
- **Action:** `decision` is a neuron index and `attention` is a category index.
  `action` uses this reference's Docking Station decision-to-action mapping.
  A host maps these outputs to available actions and enforces its own physical
  constraints. A numeric attention or decision value alone does not establish
  that a target is present, reachable, or safe. The brain neither executes
  actions nor proves an action occurred.
- **Learning feedback:** The host can use `route_sensory_adjustment` to route an
  already decoded outcome through the recovered source, life-state, action and
  target gates. It must supply the program's ordered tracked-chemical list and
  the actual attribution facts; a decision index alone is not an engine script
  or proof of an action or target. An `unresolved` result requires missing facts;
  it is not evidence that learning was rejected. The route returns the requested
  chemical adjustment separately, including when training is rejected. The host
  applies chemistry and supplies resulting concentrations to `tick`.
- **Persistence:** `to_dict` and `from_dict` retain program identity, neurons,
  dendrites, helper state, RNG, inputs, and rehearsal state. The host owns file
  storage, versioning, protection, and lifecycle. A brain checkpoint is not a
  complete body, environment, clock, or native-game world save.

Input validation precedes a tick's first mutation. A successful tick returns a
`BrainOutput`; an invalid frame raises a `NeuralError`. Each host should test
sensors, actions, feedback, and checkpoint recovery as one system. A small JSON
stream adapter is provided at [examples/default_brain/stream.py](../examples/default_brain/stream.py).

For example, after the host has decoded a stimulus and obtained the source and
life-state facts, it can queue each eligible adjustment independently:

```python
from creature_brain import route_sensory_adjustment

route = route_sensory_adjustment(
    chemical=150, adjustment=-0.25, tracked_chemicals=[148, 149, 150, 151],
    training=True, source_valid=True, life_state=1, synchronous_learning=0)
# Apply route.adjustment to host chemistry, even if route.status is not routed.
brain.queue_inputs(route.brain_inputs())
# Repeat for other events, then brain.tick(..., chemicals=host_chemicals).
```

The tracked list here is an example; the host must obtain the correct list for
its program. `queue_inputs` adds each normalized event to the pending input
buffer, so multiple events can accumulate beyond -1..1 before a tick. The
pending buffer is included in the brain checkpoint. A missing lobe or invalid
neuron index raises an error; for example, some programs do not have `prox`.
The host decides how to handle such a program rather than silently assuming
the input was consumed. This function does not decode stimulus flags or own
the action, body, chemical dynamics, timing, or world.

A controlled reconstruction test also checkpoints while both response inputs
and a weak-dendrite queue are pending. After restore, the next full brain tick
selects the same two migrations and produces the same complete checkpoint as
the uninterrupted brain. This verifies the reference checkpoint boundary; it
does not establish that a native engine checkpoint has identical hidden state.

## Qualification

The kernel runs the supplied genome's rule programs and native-informed lobe,
tract, instinct and learning machinery. Python numeric behavior, update-order
ties, exceptional values, native timing, all native credit-assignment paths,
and whole-engine parity remain unqualified. The static migration selection has
been corrected to the recovered finite-value top-N rule; live differential
qualification remains open. The native experiments in
[brain-connections-20261106](../research/docking-station-20261103/brain-connections-20261106/)
show selected pathways and limitations, not general creature competence.

The sensory regression reads the retained native `DMPN` buffers for stimulus 79:
the agent-sourced, synchronous-learning-off run matches response inputs 1 and 3,
and a null-source run matches the all-zero response buffer. A synchronous-on
capture was also all zero, but did not capture enough information to identify
which gate failed. Self/pointer exceptions and the other-life-state branch are
source-derived and have not been independently observed at runtime. A separate
brain integration test checks the captured stimulus 77 value reaching the drive
lobe after a checkpoint. A subsequent partial-state replay starts with the
captured response inputs and the available native neuron and learning-tract
states, then runs the reconstructed response-to-drive and drive-to-combination
components. In two original-engine captures, the resulting drive and all 80
learning-tract records matched within 1e-6, including the two migrated
connections. The replay infers the weak queue and initializes unobserved
intermediate tract state; it does not establish full native-brain state parity.
In a later isolated, debugger-instrumented engine run, a synchronized native
memory observation supplied the actual weak queue for the same bounded replay.
The response-to-drive pathway, all 80 tract records, and the rebuilt weak queue
matched the captured native step within 1e-6; other hidden state still was not
captured. In one separate native PRAY creature export/import experiment, the
visible tract dump remained byte-identical while the live weak queue changed
from `[4,5,6,7,8]` to `[0,1,2,3,4]`. A separate isolated world save/reload
also preserved the sampled tract dump but changed its queue from `[3,4,5,6,7]`
to `[0,1,2,3,4]`. These were single controlled observations; consequences for
later choices require separate testing. In a controlled native follow-up with
matching sampled state and equal response inputs, the pre-save and post-reload
queues migrated different records: one branch preserved two existing weighted
connections and the other replaced them. Several controlled choice probes
showed different combination-neuron activity but the same motor choice. Other
hidden state was not matched, so this does not establish a natural choice effect
or prove the queue was the only differing state. The
portable default-brain checkpoint preserves its actual queue; it is not a
native creature archive. See [the runtime report](../research/docking-station-20261103/brain-connections-20261106/queue-runtime/REPORT.md).
See [the replay](../research/docking-station-20261103/brain-connections-20261106/partial-tract-replay/compare.py)
and [weak-queue analysis](../research/docking-station-20261103/brain-connections-20261106/component-differential/WEAK-QUEUE.md).
Raw captures and context are in
[the native findings](../research/docking-station-20261103/brain-connections-20261106/FINDINGS.md)
and [touch report](../research/docking-station-20261103/brain-connections-20261106/touch-investigation/REPORT.md).
