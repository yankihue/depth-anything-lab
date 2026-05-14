# Depth Anything Lab

Agent-friendly tools for turning ordinary images into browser-ready depth assets.

This repo is intentionally small: a Python asset builder, a static Three.js viewer, and documentation that makes it easy for coding agents to generate, inspect, and reuse 2.5D/3D image assets in other projects.

The bundled sample comes from the oracle image used in [hue-slash](https://hue-slash.vercel.app/), but the lab is general. Bring any image, build a depth-backed point payload, preview it locally, then copy the generated files into a website, game, installation, or visual experiment.

## What It Produces

For an input image, the builder writes:

- `public/data/<asset>-points.json`: compact point-cloud payload for WebGL.
- `public/data/<asset>-depth.png`: normalized grayscale depth map.
- `public/data/<asset>-source.jpg`: resized source preview used for inspection.
- `public/data/<asset>.meta.json`: generation settings, mode, crop, and provenance.

The point payload is designed to be easy for agents to consume in Three.js, custom shaders, canvas renderers, or conversion scripts.

## Fast Start

```bash
npm run build:sample
npm run serve
```

Open [http://localhost:8061](http://localhost:8061).

The viewer defaults to `oracle`. To inspect another generated asset:

```text
http://localhost:8061/?asset=my-asset
```

## Build Your Own Asset

Put an image anywhere, then run:

```bash
python3 tools/build_depth_asset.py \
  --input /path/to/image.jpg \
  --out public/data/my-asset \
  --crop 0,0,1,1 \
  --max-points 42000 \
  --mask-mode depth \
  --mode auto
```

Then preview:

```bash
npm run serve
```

```text
http://localhost:8061/?asset=my-asset
```

## Agent Workflow

For coding agents, the smooth path is:

1. Read [AGENTS.md](./AGENTS.md).
2. Build one asset with `tools/build_depth_asset.py`.
3. Open the static viewer and inspect depth scale, scatter, point size, and tint.
4. Copy only the needed generated files into the target project.
5. In the target project, load `<asset>-points.json` and map `positions`, `colors`, `sizes`, `depths`, and `seeds` to renderer attributes.

Use [docs/agent-quickstart.md](./docs/agent-quickstart.md) for exact commands and [docs/payload-schema.md](./docs/payload-schema.md) for the JSON contract.

## Mask Modes

`--mask-mode` controls which pixels become particles:

- `depth`: generic default. Keeps pixels with useful depth/color contrast and skips padded black background.
- `luma`: useful for drawings, documents, engravings, and high-contrast images.
- `none`: exports the full crop as a rectangular field.
- `oracle`: tuned for the bundled hue-slash sample, where red/blue/gold/dark regions carry the figure.

If an output looks too rectangular, avoid `none`. If the subject is sparse, try `luma`. If the source is painterly or photographic, start with `depth`.

## Depth Anything V2 Mode

The default `auto` mode uses Depth Anything V2 when you provide a local checkout and checkpoint. Otherwise it falls back to deterministic heuristic depth so the repo works on a clean machine.

```bash
python3 tools/build_depth_asset.py \
  --input /path/to/image.jpg \
  --out public/data/my-asset \
  --mode da-v2 \
  --model-dir /path/to/Depth-Anything-V2 \
  --checkpoint /path/to/depth_anything_v2_vits.pth \
  --encoder vits
```

You can also set:

```bash
export DEPTH_ANYTHING_V2_DIR=/path/to/Depth-Anything-V2
export DEPTH_ANYTHING_V2_CHECKPOINT=/path/to/depth_anything_v2_vits.pth
export DEPTH_ANYTHING_V2_ENCODER=vits
```

This repo does not vendor Depth Anything V2 or model weights.

## Why Not MCP?

MCP would be useful if this needed to be a long-running service, expose remote model execution, or manage a library of assets across tools. For this lab, files plus clear commands are smoother: coding agents can run the builder, inspect outputs, and copy artifacts without extra server state.

## Example Use

The sample oracle asset is meant to prove the workflow:

```text
source image -> depth map -> point payload -> browser scene -> reusable art primitive
```

In [hue-slash](https://hue-slash.vercel.app/), the same kind of payload can drive scroll-based reveal, depth amplification, glyph morphs, parallax, and particle disassembly. In other projects it can become relief panels, haunted portraits, product depth cards, stage backdrops, or asset-heavy interactive scenes.
