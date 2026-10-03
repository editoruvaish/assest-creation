# Stairs frame (697x1263 source)

- `frame-full.svg` / `frame-full_4K.png` (2119x3840): full frame with background.
- `frame-transparent.svg` / `frame-transparent_4K.png`: steps + glow + text + orb on a transparent canvas.
- `assets/` (each SVG + 4K PNG, long side 3840 px, transparent, tight crop):
  `steps/step-01..10` (full slab rectangles, incl. the parts that run off-frame), `step-01-corner-glow`,
  `text-one-step-closer`, `orb`, `background-flat`, `back-panel`.
- All steps share one gradient (`step-gradient`), every step is its own named group; text is outlined (Open Sans shapes).
