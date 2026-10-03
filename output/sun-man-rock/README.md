# Sun / water glints / man / rock frame – 4K PNG + layered SVG

- `frame-transparent.svg` / `frame-transparent_4K.png` – poora frame, transparent background (2144×3840)
- `frame-on-black_4K.png` – black par preview; `compare_reference-vs-result.png` – reference | result
- `assets/` – har asset alag SVG + 4K PNG (full-frame canvas, position same); `assets-cropped/` – tight crop

Assets (z-order): sun, water-glow, rock, walking-stick, man.

Notes
- Sun = exact vector semicircle. Rock / man / stick = soft silhouettes (blurred mask) + gradient-band colour fill, kyunki reference mein ye out-of-focus hain.
- water-glow (green/white streaks) alpha-mask se bana hai: dark hissa transparent hota hai, isliye white background par halka dikhta hai.
- Man ek hi piece hai (head/torso/legs reference mein blur ho kar jude hain). Dark kapde ki wajah se white bg par silhouette dark dikhta hai.
- SVG ke blur/mask filters Chromium/Inkscape jaise renderers mein sahi dikhte hain; PNG Chromium se render hue.
