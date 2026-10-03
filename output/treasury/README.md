# Treasury certificate frame (706x1258 source, 9:16)

- `frame-full.svg` / `frame-full_4K.png` (2155x3840): full frame incl. dark grid background.
- `frame-transparent.svg` / `frame-transparent_4K.png`: same, background removed (transparent canvas).
- `assets/`: every element as its own SVG + 4K PNG (long side 3840 px, transparent, tight crop):
  background-gradient, grid-lines, text-simple, bracket-*, card-paper, text-us-treasury, text-amount,
  text-ownership-certificate, text-lines-all, `lines/text-line-1..8`, `seal` and `seal-parts/*`.
- SVG layers are named groups/ids (`layer-background`, `layer-corner-brackets`, `layer-certificate`, `seal`, ...).
- All text is outlined (Liberation Serif / Montserrat shapes), so no fonts are needed.
