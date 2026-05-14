# Depth Anything Lab

Standalone browser lab for turning single images into depth-backed 2.5D/3D assets.

The first target is the `hue-slash` oracle image, but this repo is intentionally separate so it can become a reusable asset pipeline for other visual projects.

## What It Does

- Builds a depth asset pack from an input image:
  - `*-depth.png`: normalized grayscale depth map
  - `*-points.json`: point cloud payload for the browser viewer
  - `*.meta.json`: provenance, crop, mode, and generation settings
- Uses Depth Anything V2 when a local checkout and checkpoint are provided.
- Falls back to a deterministic heuristic depth pass so the lab works immediately without ML dependencies.
- Serves a Three.js viewer for point-cloud orbiting, depth scaling, scattering, color/depth inspection, and export-oriented iteration.

## Quick Start

Copy a source image into `assets/source/oracle.jpg`, then run:

```bash
npm run build:oracle
npm run serve
```

Open:

```text
http://localhost:8061
```

## Using the Hue Slash Oracle Image

From this repo root:

```bash
cp /Users/yanki/Desktop/personal/hue-slash/assets/oracle.jpg assets/source/oracle.jpg
npm run build:oracle
npm run serve
```

## Real Depth Anything V2 Mode

The default `auto` mode uses Depth Anything V2 only when all required local pieces exist. Otherwise it falls back to `heuristic`.

Example:

```bash
python3 tools/build_depth_asset.py \
  --input assets/source/oracle.jpg \
  --out public/data/oracle \
  --crop 0.18,0.10,0.82,0.92 \
  --mode da-v2 \
  --model-dir /path/to/Depth-Anything-V2 \
  --checkpoint /path/to/depth_anything_v2_vits.pth \
  --encoder vits
```

Expected Depth Anything V2 dependencies are the repo dependencies: `torch`, `opencv-python`, `torchvision`, and friends. This lab does not vendor those packages.

## Why This Exists

The useful thing is not a displayed depth map. The useful thing is a repeatable asset pipeline:

```text
image -> depth -> normals/points -> web scene -> reusable art primitive
```

For `hue-slash`, the point payload can replace the current dome/redness pseudo-depth in `main.js` with a real depth-displaced oracle figure. For fresco/manuscript projects, the same output can drive relief panels, parallax cards, and physical-feeling image layers.
