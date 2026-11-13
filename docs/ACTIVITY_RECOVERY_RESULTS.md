# Familiar activity failure and recovery

Candidate v27 extends activity opportunities with experience-based retry spacing.
A completed, zero-effect familiar attempt records its actual last-trial world tick.
Repeated failed goals wait 128, 256, 512, then at most 1024 world ticks before a
new recheck. No elapsed time is invented for pre-adoption goals lacking that tick.
A due recheck may take the next free activity opportunity; it cannot interrupt an
active activity or bypass maintenance. The interval rule is authored, not learned
or self-modified. Failure history determines its applied interval.

When all recent effects are zero, a recheck is justified by historical actual
effects and explicitly marked current-effect-unknown. A successful goal resets
consecutive failures. Opportunity evidence stores the last selected and latest
opportunity event plus skipped count, instead of copying an ever-growing list.

Qualification history:
- Original opportunity candidate failed the changed-outcome preference test.
- Retry spacing repaired all four familiar regressions (32.223 seconds).
- Initial recovery run passed six discovered tests in 72.696 seconds: nine failed
  interactions over 640 moments, then repair recovered after 553 moments, with
  twelve exact restored ticks. Four familiar tests were unintentionally discovered
  again through a class import; the import was changed to a module to avoid that.
- Six related world-commitment and investigation-feedback checks passed in 49.780
  seconds before the final due-recheck priority adjustment.
- Rural spacing-only candidate failed recovery: six inert trials over 512 moments,
  but no new lantern trial across 1536 repaired moments. Eligibility alone did not
  win a new activity opportunity. This failed evidence is retained under rural/.
- Final priority-adjusted qualification is recorded separately under
  validation/activity-recovery/rural-priority and final-tests.log.

These tests distinguish changing the test environment from the creature's own
activity decisions. The main habitat has not received test faults or test memories.
See the final appended results before considering live adoption.


## Final qualification

The final six focused tests passed (see final-tests.log). In the rural branch,
512 inert moments produced twelve failed interactions in two bounded six-trial
attempts. After repair, the creature made five interactions and demonstrated the
restored effect at world tick 20707, 267 moments after repair. Twelve further
restored ticks and full snapshots matched. This repairs the spacing-only rural
failure without importing any branch experience into the main individual.

The intervals intentionally trade recovery latency for fewer ineffective attempts.
Neither these examples nor the fixed interval rule establish an optimal tradeoff
or self-authored learning policy. Controlled qualification is sufficient for the
specific change; sustained companionship and broad adaptive competence remain open.

## Live adoption

Adopted at tick 20977; owned migration verified full prior event prefix,
identity, branch and host state preservation, and installed checkpoint readback.
The transient user service definition was collected on stop, so the initial
start failed after successful adoption. Its same command, working directory,
PYTHONPATH and private proxy configuration were recreated with systemd-run.
The prior running intent was restored. Failure log and before-images are retained.

Live state at tick 21014 is running without error, same identity and branch,
with the existing two rehearsals and one retained practice-code revision. Browser
QA showed resumed movement and intact town art (live-resumed.png). The live
creature has received no simulated breakage or branch learning. Its new ordinary
activity choices remain to be observed over sustained use.

### Unprompted live follow-up

At tick 21349, the same live v27 individual had completed a voluntary return
to workshop-lantern in five trials with one visible effect, then a successful
berry-1 return. No new teaching, device change, or action command was issued for
these returns. Evidence is validation/live-activity-opportunities/latest-state.json
and qualified-goals.json. This confirms actual use of the retained skill after
adoption; it does not by itself establish long-term balanced activity.
