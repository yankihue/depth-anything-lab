# Agent Quickstart

This is the shortest reliable path for a coding agent.

## 1. Pick An Asset Name

Use a lowercase slug:

```text
my-asset
```

The builder will create:

```text
public/data/my-asset-points.json
public/data/my-asset-depth.png
public/data/my-asset-source.jpg
public/data/my-asset.meta.json
```

## 2. Build

Generic image:

```bash
python3 tools/build_depth_asset.py \
  --input /absolute/path/to/source.jpg \
  --out public/data/my-asset \
  --crop 0,0,1,1 \
  --max-points 42000 \
  --mask-mode depth \
  --mode auto
```

High-contrast drawing or scan:

```bash
python3 tools/build_depth_asset.py \
  --input /absolute/path/to/source.jpg \
  --out public/data/my-asset \
  --crop 0,0,1,1 \
  --max-points 36000 \
  --mask-mode luma \
  --mode auto
```

Full rectangular sheet:

```bash
python3 tools/build_depth_asset.py \
  --input /absolute/path/to/source.jpg \
  --out public/data/my-asset \
  --crop 0,0,1,1 \
  --max-points 52000 \
  --mask-mode none \
  --mode auto
```

## 3. Preview

```bash
npm run serve
```

Open:

```text
http://localhost:8061/?asset=my-asset
```

Inspect:

- Depth scale: does the image read as a relief or a blown-out wall?
- Scatter: does the mask hold up when points separate?
- Point size: are details legible without becoming a texture sheet?
- Depth tint: does `depths` carry useful near/far structure?

## 4. Integrate

Copy the generated files needed by the target project. Usually that is only:

```text
public/data/my-asset-points.json
public/data/my-asset.meta.json
```

For visual debugging or UI previews, also copy:

```text
public/data/my-asset-depth.png
public/data/my-asset-source.jpg
```

## 5. Minimal Three.js Loader

```js
const payload = await fetch("/data/my-asset-points.json").then((r) => r.json());

const geometry = new THREE.BufferGeometry();
geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(payload.positions), 3));
geometry.setAttribute("color", new THREE.BufferAttribute(new Float32Array(payload.colors), 3));
geometry.setAttribute("size", new THREE.BufferAttribute(new Float32Array(payload.sizes), 1));
geometry.setAttribute("depth", new THREE.BufferAttribute(new Float32Array(payload.depths), 1));
geometry.setAttribute("seed", new THREE.BufferAttribute(new Float32Array(payload.seeds), 1));
```

In the shader, multiply `position.z` by a depth scale and use `depth` for tint, reveal, scatter, fog, or ordering.
