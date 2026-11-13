# V24: review remembered relief when outcomes stop supporting it

The prior recency-weighted positive expectation approached zero asymptotically
when food repeatedly produced no hunger relief. Since selection required only a
positive expectation, the continuing-history fault experiment consumed twelve
berries in twenty-four moments while hunger remained 0.8.

V24 retains up to three recent zero-relief evidence references when the creature
was actually hungry and the resource previously had positive expected relief.
After three such outcomes, that memory stops proposing the resource until a
bounded recheck time. A successful later outcome clears the suspension. Fullness,
missing need observations, and unmatched outcomes do not establish this failure.
The old expectation is retained rather than silently erased. Rechecks explicitly
carry failure evidence and uncertainty instead of claiming current effectiveness.

The rule is owned by the outcome-memory projection and is reconstructed from the
recorded implementation and experience history. V23 and earlier histories keep
their earlier behavior. The authored thresholds are three observed failures and
a sixteen-moment retry interval; this is not learned timing or general causal
diagnosis. It reviews hunger relief, not every possible nutritional benefit.

For the qualification, an attributed body configuration changed stored berries'
hunger relief to zero, then restored it. Inventory expenditure, actual body
hunger, pending feedback, and appearance remained real simulation consequences.
The body configuration is persistent and validated. The continuing live body's
normal effectiveness was not changed by these test interventions.

## Evidence and tradeoff

`validation/changed-food-effect/` retains the baseline and initial 64-moment
candidate. In that first candidate, 24 failure moments consumed six berries
instead of twelve, but relief was detected 48 moments after repair versus two
for the original. That latency motivated the final shorter interval. The
initial candidate was not deployed.

The final tests cover failure suspension, bounded rechecking, successful recovery,
fullness/missing/unmatched evidence, old behavior, recall and priority semantics,
actual stored-food consumption and persistence. Fourteen final checks passed in
9.450 seconds. Six garden, adoption, and upgrade regressions passed in 13.131
seconds. Paired runtime results and exact restoration evidence are under `final/`.

This capability does not diagnose why food failed, guarantee an optimal retry
interval, or provide a general nutrition plan. Other needs, replanning across
resource exhaustion, and general self-directed implementation growth remain
unfinished. Full end-goal acceptance remains unproven.

## Final comparison and visual qualification

With the sixteen-moment interval, V24 consumed seven ineffective berries during twenty-four failure moments, versus twelve in V23. Both remained at hunger 0.8 until effectiveness was restored at the same world tick. First subsequent relief occurred six moments after restoration for V24 versus two for V23; both consumed four effective berries and reduced hunger to floating-point zero. Thus the tested benefit is lower repeated waste with a four-moment recovery delay, not faster recovery. A twelve-tick continuation from a suspended-memory test branch matched exactly after restoration. The UI was visually inspected on a separate recorded test branch: it says “Checking whether remembered relief has returned”, without claiming the food currently works. Screenshot: validation/changed-food-effect/recheck-ui.png.

Live adoption at tick 16557 preserved the full prior history, identity, branch and body through the owned-store migration. The same individual resumed and advanced to tick 16577 with no reported error. Default food effectiveness remains unchanged; test fault configurations and experiences were not merged. The temporary adoption hook was removed and preview server stopped.
