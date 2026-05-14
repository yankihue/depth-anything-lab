# Payload Schema

`*-points.json` is intentionally plain JSON so agents can copy, inspect, transform, or load it without generated client code.

## Shape

```json
{
  "positions": [0, 0, 0],
  "colors": [1, 0, 0],
  "sizes": [1],
  "depths": [0.5],
  "seeds": [0.12345],
  "mode": "heuristic",
  "maskMode": "depth"
}
```

Every point uses the same index across arrays.

```text
point i:
  x = positions[i * 3 + 0]
  y = positions[i * 3 + 1]
  z = positions[i * 3 + 2]
  r = colors[i * 3 + 0]
  g = colors[i * 3 + 1]
  b = colors[i * 3 + 2]
  size = sizes[i]
  depth = depths[i]
  seed = seeds[i]
```

## Fields

`positions`

Local point positions. `x` and `y` are normalized around the cropped image. `z` is centered depth, usually around `-1` to `1`.

`colors`

Linear-ish RGB values in `0..1`, lifted slightly for browser visibility.

`sizes`

Relative point sizes. Use as a multiplier in shader point sizing.

`depths`

Normalized depth values in `0..1`. Use this for visual logic even if you change `positions.z`.

`seeds`

Stable random values in `0..1`. Use for scatter, shimmer, stochastic reveal, per-point delays, and animation offsets.

`mode`

Depth generation path:

- `heuristic`
- `da-v2`

`maskMode`

Pixel-selection strategy:

- `depth`
- `luma`
- `none`
- `oracle`

## Meta File

`<asset>.meta.json` contains the source path, crop, sample size, point count, depth range, depth mode, mask mode, and a short note.

Treat the meta file as provenance and debugging context. The runtime renderer should only need `*-points.json`.
