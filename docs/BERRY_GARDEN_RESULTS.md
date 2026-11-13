# Consequential native berry garden

The six previously decorative rural plots now optionally exist as persistent
world objects. Each ripe plant exposes an interaction; an actual contact harvest
changes it to a regrowing plant and adds one berry of its species to the basket.
Harvest counts and inventory are conserved and checked during restoration.
Depleted plants do not advertise harvesting. Each regrows after eighty world
ticks, with ripening recorded separately as an environmental change. Paused or
restored creatures gain no growth time. This does not simulate real-world botany.

The existing curriculum notices unfamiliar affordances, approaches the plots,
sets practice goals, and retains evidence of harvest effects. No per-harvest
command or plant-specific goal was prescribed to the brain. Native Oran/Pecha
sprite-sheet frames show ripe versus regrowing states; generic object props are
suppressed for those plots. The basket displays the actual stored inventory.
Walkability is unchanged: plots remain traversable and pond cells remain blocked.

Garden adoption is an attributed implementation event. It preserves the previous
host, original objects, lineage, and event history while adding six fixed native
plots and an empty inventory. Restore rejects unrecorded garden adoption, altered
plot locations, invalid growth clocks, and inventory inconsistent with harvests.
The owner of garden creation normalizes object iteration to checkpoint ordering;
a first long-run restore comparison exposed divergence before this fix. That
failed receipt is retained, and a dedicated visible-original-object regression
now verifies identical perception and future behavior after restoration.

## Evidence

`validation/berry-garden/` contains the test logs, branch records, and screenshots.
Eight initial tests passed; nine final garden, adoption, and rural-body tests
passed in 17.328 seconds. These include exact preservation and idempotent offline
adoption, exclusive-writer rejection, autonomous harvest, actual regrowth,
restore continuity, invalid-state rejection, and existing farm/pond/door checks.

An explicit branch of the continuing individual ran 400 real world ticks and
performed fourteen autonomous harvests across all six plots, including repeated
harvests of every plot. It retained six Oran and eight Pecha berries and recorded
thirteen ripening events. At least one berry practice goal reached demonstrated
visible effect. Twelve further uninterrupted/restored ticks matched exactly;
those extra ticks produced another Pecha, so the later preview shows 6/9 rather
than the 400-tick result of 6/8. The source individual was unchanged.

The branch was served separately and visually inspected at close view and town
overview. The native plant frames, inventory, full roofs, and tree borders were
visible. This is desktop browser QA, not physical-phone acceptance. The preview
server was stopped after inspection.

## Limits

The basket is persistent collected inventory, not yet food consumption, crafting,
planting, watering, or a general resource economy. Plant availability is authored
world information; the creature has not demonstrated a general concept of
agriculture or learned regrowth timing. No test inventory or experience is merged
into the continuing individual. Full end-goal acceptance remains unfinished.

Live adoption at tick 14630 preserved the prior individual and began with an empty basket. The same live creature autonomously initiated berry practice and harvested fruit. At tick 14729, the inventory was {'oran': 3, 'pecha': 3}, running was true, and no error was reported. A fresh Tailscale browser inspection showed the live inventory, native plots, and corrected “Harvesting berries” activity wording. The migration hook was removed; `live-adoption/` retains before-images and the receipt.
