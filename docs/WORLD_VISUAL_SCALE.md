# Overworld visual scale and prop pass

Owner feedback: the creature was too large and visually disconnected from the
town, and the interactive box did not belong in the environment.

The world renderer now draws the creature in a 28x28 world-pixel cell instead of
40x40 (30% smaller). Each source frame is reduced once into a cached display
texture, mapped to a compact lavender/charcoal/brass/amber palette, and given
solid pixel edges. The world canvas enlarges those pixels with smoothing off.
Positions and feet are snapped to world pixels so fractional walking positions
do not continually resample fine source detail. The contact shadow uses small
pixel rows rather than a large antialiased ellipse. Original PNGs are untouched.

The generic purple box is replaced by a 12x16 code-native lantern, using muted
brass, gray-green glass and dark outlines. Its glass becomes warm gold only when
the actual object state is on. Counter/inert devices use a rounded stone sprite;
food uses a small berry/morsel and bowl. These are existing procedural canvas
props refined into pixel grids, not new imported raster assets.

The update affects only display. The server and continuing creature were not
restarted or migrated. The same object identities, actions and outcomes remain
the basis of animation and prop state.

Verification: JavaScript syntax passed; all three prop grids have valid 12x16
bounds and palette symbols. The deployed browser showed the smaller creature
and lantern with no console errors. A 412x915 viewport was checked during the
scale pass; final palette pass was checked in the desktop browser. The initial
nearest-neighbor reduction looked jagged and was replaced by cached high-quality
reduction followed by explicit pixel-palette rendering. Visual acceptance still
belongs to the owner.

Before renderer and final screenshot:
`validation/world-style-pass/renderer-before.js`, `live-after.png`.
The intermediate `phone-after.png` predates the final palette adjustment.
