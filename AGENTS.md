# AGENTS.md

Operating rules for coding agents working in this repo. For project overview, read [README.md](./README.md).

## What you produce

One asset = four files under `public/data/<slug>`:

```
<slug>-points.json   <- the payload (ship this)
<slug>-depth.png     <- inspection only
<slug>-source.jpg    <- inspection only
<slug>.meta.json     <- provenance
```

Slug is lowercase, `[a-z0-9_-]` only (the viewer strips anything else).

## Decision tree

**Mode:**
- Default to `--mode auto`. It tries DA-V2 if `--model-dir` + `--checkpoint` (or the `DEPTH_ANYTHING_V2_*` env vars) are set, otherwise heuristic.
- Use `--mode da-v2` only when the user has explicitly provided model paths and wants the build to fail if DA-V2 isn't usable.
- Do not pretend heuristic depth is real depth. If you fall back, say so.

**Mask:**
- `depth` — start here for photos, paintings, anything with broad tonal range.
- `luma` — line art, scans, manuscripts, monochrome drawings.
- `none` — only when the user wants a rectangular depth sheet.
- `oracle` — only for the bundled `oracle.jpg` or near-identical red/blue/gold ritual art. It is not a generic mode.

**Crop:** start with `0,0,1,1`. Tighten only if the subject leaves obvious dead space, since `--sample-size` letterboxes to a square.

**Points:** 42000–52000 is the working range. Below 20000 looks sparse; above 80000 the JSON gets unwieldy for the static viewer.

## Don't

- Commit model checkpoints, the Depth-Anything-V2 checkout, venvs, or `node_modules`.
- Write assets outside `public/data/` unless the user asked for a different export path.
- Add a server, MCP wrapper, or background process. The contract is files + a CLI.
- Edit the bundled sample command in `package.json` to point at a different image.

## Verify before handing off

1. The CLI printed `wrote N points using <mode>: <prefix>`. Note N and the mode.
2. All four files exist at the expected paths.
3. `npm run serve` and open `/?asset=<slug>`. Confirm the subject reads as a relief, not a flat rectangle (unless `--mask-mode none` was intentional).
4. Open `<slug>.meta.json`. Confirm `mode`, `mask_mode`, `point_count`, and that `depth_min`/`depth_max` aren't both pinned to 0 or 1.

## Integration contract

Other projects (e.g. hue-slash) consume `<slug>-points.json` directly. The schema is stable; treat it as a public API.

```json
{
  "positions": [...],   // Float32, length = N*3, (x,y,z); z is centered and pre-amplified
  "colors":    [...],   // Float32, length = N*3, RGB in [0,1]
  "sizes":     [...],   // Float32, length = N
  "depths":    [...],   // Float32, length = N, raw normalized depth in [0,1]
  "seeds":     [...],   // Float32, length = N, stable random in [0,1]
  "mode":      "da-v2" | "heuristic",
  "maskMode":  "depth" | "luma" | "none" | "oracle"
}
```

Mapping to Three.js attributes:

| field       | itemSize | use                                                        |
|-------------|----------|------------------------------------------------------------|
| `positions` | 3        | `position`. Multiply z by your own `uDepthScale` in vertex shader. |
| `colors`    | 3        | `color`. Already lifted slightly for browser visibility.   |
| `sizes`     | 1        | per-point size multiplier.                                 |
| `depths`    | 1        | raw `[0,1]` depth. Use for tint, fog, reveal order, displacement. |
| `seeds`     | 1        | per-point stable random. Use for scatter, shimmer, delays. |

`positions.z` is already passed through `(z_raw - 0.5) * 2.0` plus small jitter, with the xy plane scaled by `8.4`. If your scene expects normalized `[-1,1]` depth coordinates, you're already there. If you want flat-then-extrude, ignore `positions.z` and drive geometry from `depths` instead.

`meta.json` is debugging context, not a runtime dependency. The renderer should need only `-points.json`.
