# Agent Guide

This repo is designed to be operated by coding agents. Prefer simple file and CLI workflows over adding services.

## Goal

Turn input images into reusable depth-backed assets for browser projects.

The normal deliverable is a small asset pack:

- `public/data/<asset>-points.json`
- `public/data/<asset>-depth.png`
- `public/data/<asset>-source.jpg`
- `public/data/<asset>.meta.json`

## Common Commands

Build the bundled sample:

```bash
npm run build:sample
```

Build a generic asset:

```bash
python3 tools/build_depth_asset.py \
  --input /absolute/path/to/image.jpg \
  --out public/data/my-asset \
  --crop 0,0,1,1 \
  --max-points 42000 \
  --mask-mode depth \
  --mode auto
```

Serve the viewer:

```bash
npm run serve
```

Open:

```text
http://localhost:8061/?asset=my-asset
```

## Decision Rules

- Start with `--mode auto`; use `--mode da-v2` only when the user has provided a local Depth Anything V2 checkout and checkpoint.
- Start with `--mask-mode depth` for general images.
- Use `--mask-mode luma` for scans, drawings, manuscripts, and high-contrast art.
- Use `--mask-mode none` only when the target wants a full rectangular depth sheet.
- Use `--mask-mode oracle` only for the bundled hue-slash oracle sample or closely similar red/blue/gold ritual artwork.
- Keep generated assets in `public/data/` unless the user asks for a different export folder.
- Do not commit model checkpoints, downloaded repositories, virtual environments, or `node_modules`.

## Integration Contract

Load `<asset>-points.json` in the target project and map:

- `positions`: `Float32Array`, item size 3.
- `colors`: `Float32Array`, item size 3.
- `sizes`: `Float32Array`, item size 1.
- `depths`: `Float32Array`, item size 1.
- `seeds`: `Float32Array`, item size 1.

Use `positions.z *= depthScale` in the vertex shader or equivalent scene logic. Use `depths` for depth tint, fog, reveal ordering, displacement intensity, or layer-based animation.

## Verification Checklist

Before handing off an asset:

- Run the builder successfully and note the printed point count.
- Serve the viewer and inspect the asset at `/?asset=<asset>`.
- Check that the subject is not an accidental flat rectangle unless `--mask-mode none` was intentional.
- Check that the JSON, depth PNG, source JPG, and meta JSON exist.
- If integrating into another repo, copy only the generated asset files needed by that repo.
