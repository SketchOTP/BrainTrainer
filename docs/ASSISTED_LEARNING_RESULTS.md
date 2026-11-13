# Assistance and retained teaching

Four prospective seeds (91–94) passed the [frozen protocol](ASSISTED_LEARNING_PROTOCOL.md).
Each asked for help after three actual attempts with no visible effect. The request
included its observations and uncertainty; no implementation defect was inferred.
An attributed suggestion to try five more times remained unverified until real
activity produced evidence. It advanced no world time by itself.

| Condition | Observed outcome in all four seeds |
|---|---|
| Four-press device, five additional attempts | Two visible changes; advice supported in this context |
| New identity, same type, retained lesson | Verified effect on fourth attempt |
| Same transfer with only practice lesson removed | Stopped after three attempts without an effect |
| Inert device, identical advice | Stopped after eight total attempts; advice unsupported |

The successful lesson retains its teacher, advice event, real outcome event and
observed practice requirement. It changes later independent practice; it does not
change executable source. Unsuccessful advice creates no successful lesson and
cannot be repeatedly reapplied to the same goal. Existing harmful-result stops
still take precedence over extra practice allowance.

Evidence: `validation/assisted-learning-v1/` contains requests, resulting ordinary
checkpoints, controlled experiment traces, raw outcomes, runner and results.
Transfer-ablation artifacts use a distinct experimental wrapper: normal restore
reconstructs retained knowledge from history, so reproducing ablation requires
reapplying its recorded control. They are not ordinary continuing checkpoints.
The runner was updated after execution to label those artifacts explicitly;
experimental outcomes and original embedded snapshot digests were preserved.

The integrated suite passed 49 tests, including six assistance tests, executable
revision, learning, dreams/goal revision, recall, continuity and body/lifecycle
regressions. After the final capacity-reservation edit, all 17 assistance, executable
revision and continuity checks passed again. Assistance tests include real process restart during guided practice,
CLI teaching, rejecting invalid advice without mutation and later independent
use of retained learning. See `validation/v5-integrated-tests.log`.

This is bounded teaching with a causal behavioral memory. Teacher identity is
supplied metadata; it is not recognition. It does not establish attachment,
trust, person-specific voluntary interaction or a sustained relationship. The
interface currently accepts only bounded extra practice in response to a real
request, not arbitrary natural-language lessons. A visible integrated companion
and the broader end goal remain incomplete.
