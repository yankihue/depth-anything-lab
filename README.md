# depth-anything-lab

Turn a single image into a depth map and a point-cloud JSON you can drop into a Three.js scene.

Two pieces:

- `tools/build_depth_asset.py` — Python CLI. Input: one image. Output: four files in `public/data/`.
- `public/` — a static Three.js viewer (importmap + CDN, no bundler) for eyeballing what the CLI produced.

The viewer is for inspection. It is not a production renderer. The point payload is what you ship.

## Quick check

```bash
npm run build:sample   # builds the bundled oracle.jpg sample
npm run serve          # python3 -m http.server 8061 --directory public
```

Open `http://localhost:8061/`. To inspect a different asset: `?asset=<name>`.

## Build an asset

```bash
python3 tools/build_depth_asset.py \
  --input /abs/path/to/image.jpg \
  --out public/data/my-asset \
  --mask-mode depth \
  --mode auto
```

Writes:

```
public/data/my-asset-points.json   # the payload you actually use
public/data/my-asset-depth.png     # normalized grayscale depth, for inspection
public/data/my-asset-source.jpg    # resized + letterboxed source, for inspection
public/data/my-asset.meta.json     # crop, mode, point count, depth range, source path
```

Other flags worth knowing: `--crop x0,y0,x1,y1` (normalized), `--max-points` (default 52000), `--sample-size` (default 640, also the letterbox canvas size), `--seed`.

## Depth source

Two modes. Default is `auto`, which tries Depth Anything V2 and falls back to a heuristic if the model isn't wired up.

**Depth Anything V2.** Not vendored. You install it yourself and point the CLI at it:

```bash
python3 tools/build_depth_asset.py \
  --input image.jpg --out public/data/my-asset \
  --mode da-v2 \
  --model-dir /path/to/Depth-Anything-V2 \
  --checkpoint /path/to/depth_anything_v2_vits.pth \
  --encoder vits
```

Or set `DEPTH_ANYTHING_V2_DIR`, `DEPTH_ANYTHING_V2_CHECKPOINT`, `DEPTH_ANYTHING_V2_ENCODER` and use `--mode auto`. Requires `torch` and `opencv-python`. Uses CUDA / MPS / CPU in that order.

**Heuristic.** A deterministic mix of luminance, color, edge gradient, and a centered dome (`heuristic_depth` in the CLI). It's a fallback so the repo runs on a clean machine — not real monocular depth. Plausible-looking, geometrically wrong. Use it for placeholders and tests, not for shipping anything that claims spatial accuracy.

## Mask modes

`--mask-mode` decides which pixels become particles. The candidate-keep weighting is in `candidate_weight()`.

- `depth` — general default. Drops near-black background, weights by depth contrast and saturation.
- `luma` — for line art, scans, manuscripts, engravings. Weights by saturation and mid-luma.
- `none` — keep everything in the crop. Produces a rectangular sheet.
- `oracle` — hardcoded HSV ranges (red/blue/gold/dark) tuned for the bundled `oracle.jpg` from [hue-slash](https://hue-slash.vercel.app/). Don't use this on anything else — it will throw most of your image away.

If the output looks like a flat rectangle and you didn't ask for `none`, the mask kept too much background. If it looks sparse, try `luma` or widen the crop.

## Using the payload elsewhere

See [docs/payload-schema.md](./docs/payload-schema.md) for the JSON shape, and [docs/agent-quickstart.md](./docs/agent-quickstart.md) for a minimal Three.js loader. The integration contract lives in [AGENTS.md](./AGENTS.md).

`positions.z` is already centered around 0 and depth-amplified (`scale = 8.4` in `build_points`). Multiply by your own depth scale in the vertex shader. The raw `[0,1]` scalar is in `depths` — use that for tint, fog, reveal ordering, displacement, anything where you want depth as a signal rather than a coordinate.

## Limits

- One image in, one asset out. No batching, no video, no temporal coherence.
- The viewer is a single orbit camera with four sliders. It's for sanity checks.
- DA-V2 quality depends entirely on the encoder and checkpoint you bring. `vits` is fast and rough; `vitl`/`vitg` are slow and better.
- Output is letterboxed to a square (`--sample-size`). Non-square inputs get black padding before depth runs.
