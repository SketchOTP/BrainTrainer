# Full creature runtime and qualification

The standalone simulator closes the perception → genome controller → action → body/world → measured feedback loop. Every request originates in the genome decision lobe. `core.Brain` is a separate earlier experiment and is not invoked by this runtime.

The optional interactive pet habitat also has an original host-side curiosity adapter. It selects visible goals using novelty, distance and body needs, then supplies internal noun/verb sensory cues with pauses between goals. Hunger or low Energy34 can prioritize available food. The genome brain still chooses its own attention and action each tick, and a person's cue takes priority. This goal-selection adapter is not part of the recovered native brain or evidence of native cognition. Its current intention and memory are checkpointed; ordinary benchmark worlds do not enable it.

The pet now defaults to `learned` mode rather than this scripted adapter. Its original host-side experience memory keeps up to 96 recent episodes (including location and body context) and bounded category/action associations. It updates effect estimates from observed intake, stimulation and toxin, can favor familiar object-specific outcomes, and values those effects against current needs when recalling them. A separate survival-affordance adapter can point the genome brain toward visible food, water, shelter, or an available companion when corresponding body signals are high. It supplies a target and noun/verb cue only; it does not issue motors or create resources. This is an authored digital-world mapping, not a recovered native ability or self-chosen goal system. Learned recall offers noun/verb cues; it does not substitute a motor decision. `observe` mode records experience with no internal goals or recall cues, and `scripted` retains the older curiosity adapter. The reward weights and memory model are authored adaptations, and category-level transfer cannot identify an unseen object's toxicity before experience. Delayed biochemical effects are not attributed to the current action without an eligibility mechanism.

Learned mode also has authored sensory reflexes: a previously experienced toxic intake or physically attributed contact injury can elicit a temporary retreat cue, and a sustained repeated interaction can elicit a temporary look cue (or a move-away cue after prolonged looking). The genome remains responsible for every motor output; these are not recovered native circuits. Object-specific hazard memories survive the rolling episode window and may be cleared after repeated safe experiences of the same action. Optional object `percepts` are explicit simulator-provided labels, not visual recognition. A shared label can support a cautious response to a different object only after harmful experiences with two distinct objects bearing it. That can also create false alarms for harmless lookalikes, and a completely unknown cue provides no advance knowledge of toxicity.

## Neural anatomy and execution

The supplied Chichi definition at life stage3 (youth) expresses these fifteen lobes:

| Token | Neurons | Role |
|---|---:|---|
| driv | 20 | Physiological drives |
| decn | 13 | Decision winners |
| attn | 40 | Category attention |
| visn | 40 | Vision |
| move | 40 | Category movement history |
| comb | 440 | Category/action combinations |
| stim | 40 | Stimulus integration |
| noun | 40 | Category word input |
| verb | 13 | Action word input |
| detl | 16 | Selected-target details |
| situ | 16 | Body/situation input |
| resp | 20 | Signed drive response |
| smel | 40 | Smell |
| forf | 36 | Friends and Foe |
| mood | 1 | Mood integration |

All 29 tracts participate in the same 44-component priority schedule as the lobes. The recovered connection constructor produces 2,639 dendrites in this reference implementation, including 440 combination→attention links, 440 combination→decision links, and eighty initial drive→combination links. Initialization, update programs, persistent eight-variable states, reinforcement chemistry and weak-connection migration execute rather than being replaced by score heuristics. The trusted hot path shares one interpreter with the atomic public VM.

The thirteen decision cells map to external actions `look, push, get, drop, eat, pull, approach, hit, retreat, express, rest, left, right`. The catalogue also defines deactivate for a fourteenth decision index, absent in the supplied 13-cell lobe.

Native `SetInput` adds to an external per-neuron buffer consumed during its lobe update. Instinct tissue IDs use raw byte minus one, then match the configured lobe tissue field; attention becomes noun and decision becomes verb during rehearsal. Reinforcement byte decoding uses the native codon folding and signed level. The demo begins with a declared pre-embodiment instinct warmup with REM chemical213 enabled, then clears activity. Sleep rehearses remaining inherited instincts, then cycles drive/category knowledge probes. This does not yet implement the rest of the game's language/knowledge query system.

## Body, sensory and action adapters

`GenomePhysiology` replaces the earlier simplified body in default runs. `Biochemistry` owns the source genome, construction-time expression and immutable compiled programs. The supplied genome declares 101 reactions, 199 receptors, 43 emitters, 25 initial-concentration genes, 256 half-life entries, one neuroemitter and 58 stimulus recipes. Active counts differ by sex/age: the stage3 female currently admits 100 reactions, 191 receptors and 42 emitters across 22 organs including the native unencoded default; the male admits 100/191/40 across 21 organs.

Chemical kinetics use the recovered 2.2-based rate formula, substrate-limited stoichiometry, sequential organ/reaction order and chemical0 as an absent-reagent sentinel. Half-lives, receptor thresholds/gains/nominals, emitter inversion/digital/clear flags, strict emitter phase thresholds, neuroemitter products, ATP35→ADP36 costs, starvation injury, organ repair and life-force changes execute from genes/native rules. Organ2/3 loci remain scoped to their owner; mode-dependent body locus aliases are explicit. An age receptor and muscular-activity emitter with the same displayed triple are different native pointers and are kept separate.

The twenty drives are latched `(1,5,index)` receptor outputs, not inverse nutrient stores. Health display follows native chemical4 (Glycogen); chemical35 is ATP. Zero displayed health alone does not cause death. Death latches from the recovered `(1,3,0)` life-death receptor. Per-organ health and Life125 are reported independently. Direct raw nutrient dosing is available for experiments but does not invent hunger relief or generic reward.

Actual installed CAOS scripts select food stimuli77/78/79, toy97 and social pat/slap2/4. The expressed stimulus genes specify signed chemical changes, including nutrients AND appetite relief. The world applies those recipes in proportion to consumed food or contact duration; it does not add legacy macronutrient profiles on top. Raw ingredient dosing and genomic meal recipes are mutually exclusive. Stimulus per-channel learning flags are retained in receipts; exact native source-agent/action gating is not reproduced by the body's counterfactual adapter.

Vision and smell aggregate forty categories. Nearest visible category representatives resolve attention into actual targets. Detail/situation encoding, distance falloff, the temperature gradient, movement, approach scripts, carrying, resource regeneration and action duration remain explicit world rules. Food quantities are conserved except configured regeneration; held/depleted targets are rechecked at actuation.

Each step perceives/decides for every creature, then applies requests and consequences. Neural chemical receptors write through the native tissue/cell/variable mapping; emitter/neuroemitter reads use snapshots of the same brain. Duplicate tissue IDs select the last matching lobe for native locus access, with no leaked cells from earlier larger lobes. Deferred snapshot/write phases are a host adaptation rather than full native pointer-alias interleaving.

Native biochemical Update has no elapsed-time argument. The default nominal profile maps one update to 0.2 simulated seconds and preserves fractional ticks: the installed engine initializes a 50 ms world ticker and runs a creature’s faculties once per four world ticks. An isolated game experiment measured approximately five callbacks per second under its particular conditions; fast-tick mode and workload can change actual timing. See [calibration](CALIBRATION.md) for the measurement and its limits. The legacy profile and old checkpoints retain a one-second update. Physical temperature/threat/air/crowding inputs, continuous muscle activity and stage timings remain declared model choices. NREM/REM restores through the genes' asleep input and explicitly selected REM chemistry; motor inhibition and the stage scheduler are host-owned. Brain-organ metadata is retained: no coupling was found in the inspected owning brain update/read routines, and a complete native brain-organ energy path is not claimed.

After the host scheduler ends a sleep cycle, its automatic sleep trigger waits 60 simulated seconds before triggering again. A brain-requested sleep can still occur during that interval. This is a simulator adaptation to avoid an observed immediate automatic wake/sleep loop; it is not a measured native sleep rule, and it does not change genome chemistry.

Genomic feedback uses a persistent, checkpointed 64-second body-only counterfactual. It excludes this creature's own action consequences, receives external incoming contact/harm, stays at the window's origin and advances through the same chemical phases. Changes in actual-minus-control drive differences reach `resp`; constant differences are not rewarded repeatedly. Thus a single bite's delayed receptor change can be observed after the creature switches actions. The original genome's eligibility state controls neural allocation. This is an explicit temporal-credit adaptation, not a full counterfactual world/brain or exact native sensory-training algorithm; effects beyond the finite window can still be missed. The legacy simplified body retains its earlier one-step comparison for reproducible comparison.

## Social identity

The 36-cell Friends and Foe lobe has 35 tracked identity slots; the last cell is reserved. Native seen flags use variable5, novelty uses variable7, and acting-upon-me uses variable3. Native opinion outputs are variables0 and2. Reused slots clear old neural state, then use an explicit unrelated-identity initialization; native kinship-dependent initialization remains unqualified.

Genomic bodily reactions to positive/negative contact use the expressed pat/slap stimuli. `SocialMemory` separately learns bounded identity-specific familiarity, affinity, threat and separation distress. These are original model dynamics and never overwrite the brain's learned opinion variables. Trace records display both. Actual signed interaction events identify their actor and recipient; neutral proximity supplies familiarity without inventing social reward. Threat/separation feed the explicit physical exposure adapter. There is no reproduction, pedigree, language conversation or full social-agent script system.

## Persistence and observability

Full checkpoints include the normalized genome definition, source digest, every neuron and dendrite state, endpoints, migration queues, tract helper configuration, shared native-style LCG state, rehearsal cursors, chemistry, body and sleep clocks, every organ/chemical/phase, the persistent causal control and origin, identity memories, queued teacher commands, world positions/resources/carriers, timestep and counters. Schema3 checkpoints retain source identity and matching expression; old schema2 simplified-body checkpoints remain readable. Invalid states are rejected. JSON round-trip continuation is tested frame-for-frame and final-state-for-final-state.

The CLI writes complete step traces, compact scenario summaries, a full checkpoint and a standalone HTML replay with a scrubber, positions, selected actions and live need meters. Replays are recorded observations, not an independent browser controller. The Python simulation is the owner of behavior.

## Evidence boundary

Genome rules, anatomy, action mappings, arithmetic dispatch, constructor connectivity and many update paths come from the installed artifact and preserved REA/Ghidra Evidence. This implementation makes these additional choices:

- Python finite double arithmetic in place of native x87 evaluation; unsupported ambiguous VM cases fail explicitly.
- Stable insertion order for components with equal priority, whose native tie order remains unqualified.
- Migration ranks sources by descending value, preserves source-vector order on finite equal values, and selects at most the original weak-queue length before checking existing connections. These rules follow the [native assembly investigation](../research/docking-station-20261103/brain-connections-20261106/FINDINGS.md); exceptional floating-point cases and live migration parity remain unqualified.
- A zero-initialized shared scratch bank; its original process initialization is not fully qualified.
- Fixed age-stage expression at construction, physical exposure/world/motor adapters, sleep stage timing and identity replacement policy. Live development/reproduction and the full native CAOS environment remain outside this model.

Tests establish internal contracts, exercised genome pathways and deterministic simulation behavior. They do not establish live native-engine parity, animal-level cognition, robust lifetime survival, generalized social competence or biological realism. See `full_creature_receipt.json` for measured scenario results and source-bound hashes.


## Genomic physiology and survival evidence

See `genome_physiology_receipt.json` and `runs/genome-biochemistry-verification/` for current tests and actual long-run outcomes. Earlier `runs/verification/` recordings used the former simplified body and remain historical evidence. Longer autonomous trials record deaths as outcomes, preserve failures, compare original versus restored continuation, and label horizon survivors as censored observations. No rescue actions or teacher inputs are permitted in these trials.


## ATP-starvation and gene-expression corrections

The [corrected matched trials](../runs/atp-investigation/final/REPORT.md) trace ATP regeneration to gene-driven breakdown of internal fuel and observe both depleted creatures die through the Energy34 receptor. ATP35 remains above its own death threshold at those events. Fed controls survive beyond the later event. The later [nominal timing trials](../runs/nominal-survival/REPORT.md) and isolated native chemistry comparison provide additional evidence; full live-game parity remains unqualified.

Native evidence also required two fixes: a paid organ update triggers life-force decay even when no chemical operation was active; sex-inactive organ genes do not prevent their active child genes from attaching to the preceding active organ. The previous male counts and physiology were therefore superseded. Sex flags that admit both sexes and native organ age bypass are handled by the shared expression owner.
