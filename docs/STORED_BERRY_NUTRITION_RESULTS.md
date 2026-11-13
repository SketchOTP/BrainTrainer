# V23: stored food and learned need relief

Collected berries can now be adopted as carried food. Perception exposes only
available stored quantities, as distinct targets from the rooted plants. The
existing eat lifecycle requires contact/consumption stages, and spending one
berry increases its species' consumed count. Inventory plus consumed berries
must equal actual harvests. Carried food works independently of the current room;
no duplicate world objects or distant food teleports are created.

Consumption changes hunger by at most 0.2 and energy by at most 0.05, within the
existing body bounds. Outcome credit reports the actual change, including zero
hunger relief when already full. The feedback is queued through the same body
credit path as other food. The nutrition values are authored body behavior; they
are not supplied as facts to the creature's memory.

The first continuing-history experiment exposed that world exploration overrode
the substrate's recalled food action after a successful taste. V23 explicitly
selects an available resource with experienced positive relief when hunger is
present, approaches it if needed, and attaches the memory evidence and expected
relief to the decision. Maintenance retains precedence. Unknown foods and a full
creature do not receive this learned-relief priority. Curiosity can still sample
an unfamiliar food at fullness; the result then teaches zero relief in that
context. This is not a complete nutrition or satiety model.

## Evidence

`validation/stored-berry-nutrition/` retains the initial failure and final evidence.
The initial probe also incorrectly searched returned host events for the ledger's
separate intention field. The final paired probe instead checks actual executive
choices and their referenced completed relief events.

Two explicit branches of the same tick-15244 history ran 160 moments with stored
food enabled. V22 ate once, leaving hunger at 0.6, and made no learned-relief
choices. V23 ate six berries, made six learned-relief choices, reached zero hunger,
and continued exploration/practice/rest. Of the six eaten berries, some were
curiosity samples rather than needed hunger relief. Every learned-relief choice
referenced an actual prior negative hunger adjustment. The V23 continuation
matched restoration exactly for twelve more ticks. Test histories were not merged.

The first run executed twelve checks (including four duplicate garden tests from
an imported test class). The duplicate collection was removed. Six final stored
food/adoption/upgrade tests passed in 11.249 seconds; fourteen priority, recall,
and developmental regressions passed in 8.552 seconds. Checks cover conserved
counts, no repeated spend after exhaustion, zero actual relief at fullness,
restoration during the eating lifecycle and pending feedback, invalid adoption,
need/distance/maintenance arbitration, and prior recall/development behavior.

The prototype browser check uses a separately served test branch with an explicit
external hunger-setting event for repeatable display inspection. It is not the
continuing individual. Body, brain, and nutrition adoption each retain attributed
history; the prior inventory is preserved rather than replenished.

General nutrition planning, replenishment goals driven by inventory forecasts,
crafting, learned regrowth timing, and full companion acceptance remain unfinished.

Live adoption at tick 15505 separately recorded V22 → V23 and nutrition enablement. Before resuming, inventory (11 Oran / 12 Pecha), hunger (0.8), energy, identity, branch, and prior history were verified preserved. At tick 15532, actual live consumption was {'oran': 2, 'pecha': 0}, hunger was 0.4000000000000001, running was true, and no error was reported. The one-time hook was removed. The prototype UI showed a remembered eating action and the basket falling by one; its preview server was stopped.
