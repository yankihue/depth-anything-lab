#!/usr/bin/env python3
"""Build browser-ready depth assets from a single image.

The script can use Depth Anything V2 when a local model checkout and checkpoint
are supplied. Without those dependencies it falls back to a deterministic image
heuristic so the lab remains runnable on a clean machine.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter


@dataclass
class BuildMeta:
    source: str
    mode: str
    crop: Tuple[float, float, float, float]
    sample_size: int
    max_points: int
    point_count: int
    depth_min: float
    depth_max: float
    note: str


MODEL_CONFIGS = {
    "vits": {"encoder": "vits", "features": 64, "out_channels": [48, 96, 192, 384]},
    "vitb": {"encoder": "vitb", "features": 128, "out_channels": [96, 192, 384, 768]},
    "vitl": {"encoder": "vitl", "features": 256, "out_channels": [256, 512, 1024, 1024]},
    "vitg": {"encoder": "vitg", "features": 384, "out_channels": [1536, 1536, 1536, 1536]},
}


def parse_crop(value: str) -> Tuple[float, float, float, float]:
    parts = [float(x.strip()) for x in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("crop must be x0,y0,x1,y1")
    x0, y0, x1, y1 = parts
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise argparse.ArgumentTypeError("crop values must be normalized and ordered")
    return x0, y0, x1, y1


def normalize_depth(depth: np.ndarray) -> np.ndarray:
    depth = np.asarray(depth, dtype=np.float32)
    finite = np.isfinite(depth)
    if not finite.any():
        return np.zeros_like(depth, dtype=np.float32)
    lo, hi = np.percentile(depth[finite], [2, 98])
    if hi <= lo:
        lo, hi = float(depth[finite].min()), float(depth[finite].max())
    if hi <= lo:
        return np.zeros_like(depth, dtype=np.float32)
    out = (depth - lo) / (hi - lo)
    return np.clip(out, 0, 1).astype(np.float32)


def heuristic_depth(rgb: np.ndarray) -> Tuple[np.ndarray, str]:
    luminance = (
        rgb[..., 0].astype(np.float32) * 0.299
        + rgb[..., 1].astype(np.float32) * 0.587
        + rgb[..., 2].astype(np.float32) * 0.114
    ) / 255.0
    red = rgb[..., 0].astype(np.float32) / 255.0
    green = rgb[..., 1].astype(np.float32) / 255.0
    blue = rgb[..., 2].astype(np.float32) / 255.0
    saturation = np.max(rgb, axis=2).astype(np.float32) / 255.0 - np.min(rgb, axis=2).astype(np.float32) / 255.0

    gy, gx = np.gradient(luminance)
    edge = normalize_depth(np.sqrt(gx * gx + gy * gy))
    h, w = luminance.shape
    yy, xx = np.mgrid[0:h, 0:w]
    nx = (xx / max(1, w - 1) - 0.5) * 2.0
    ny = (yy / max(1, h - 1) - 0.5) * 2.0
    dome = np.sqrt(np.clip(1.0 - (nx * nx * 0.58 + ny * ny * 0.46), 0, 1))

    red_push = np.clip(red - (green + blue) * 0.42, 0, 1)
    cobalt_cut = np.clip(blue - red * 0.45, 0, 1)
    dark_recede = 1.0 - np.clip(luminance * 1.55, 0, 1)

    depth = (
        dome * 0.42
        + red_push * 0.34
        + edge * 0.16
        + saturation * 0.1
        - cobalt_cut * 0.12
        - dark_recede * 0.08
    )
    image_depth = Image.fromarray((normalize_depth(depth) * 255).astype(np.uint8))
    image_depth = image_depth.filter(ImageFilter.GaussianBlur(radius=1.2))
    return np.asarray(image_depth, dtype=np.float32) / 255.0, "heuristic luminance/color/edge depth"


def depth_anything_v2_depth(
    image_path: Path,
    model_dir: Path,
    checkpoint: Path,
    encoder: str,
    input_size: int,
) -> Tuple[np.ndarray, str]:
    try:
        import cv2  # type: ignore
        import torch  # type: ignore
    except Exception as exc:
        raise RuntimeError("Depth Anything V2 mode requires torch and opencv-python") from exc

    sys.path.insert(0, str(model_dir))
    try:
        from depth_anything_v2.dpt import DepthAnythingV2  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"could not import DepthAnythingV2 from {model_dir}") from exc

    if encoder not in MODEL_CONFIGS:
        raise RuntimeError(f"unknown encoder {encoder}; expected one of {sorted(MODEL_CONFIGS)}")
    if not checkpoint.exists():
        raise RuntimeError(f"checkpoint not found: {checkpoint}")

    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    model = DepthAnythingV2(**MODEL_CONFIGS[encoder])
    model.load_state_dict(torch.load(str(checkpoint), map_location="cpu"))
    model = model.to(device).eval()

    raw = cv2.imread(str(image_path))
    if raw is None:
        raise RuntimeError(f"could not read image with cv2: {image_path}")
    with torch.no_grad():
        depth = model.infer_image(raw, input_size)
    return normalize_depth(depth), f"Depth Anything V2 {encoder} on {device}"


def choose_depth(args: argparse.Namespace, image_path: Path, rgb_full: np.ndarray) -> Tuple[np.ndarray, str, str]:
    requested = args.mode
    if requested in {"auto", "da-v2"} and args.model_dir and args.checkpoint:
        try:
            depth, note = depth_anything_v2_depth(
                image_path=image_path,
                model_dir=Path(args.model_dir).expanduser(),
                checkpoint=Path(args.checkpoint).expanduser(),
                encoder=args.encoder,
                input_size=args.input_size,
            )
            return depth, "da-v2", note
        except Exception:
            if requested == "da-v2":
                raise
            print("Depth Anything V2 unavailable; falling back to heuristic.", file=sys.stderr)

    depth, note = heuristic_depth(rgb_full)
    return depth, "heuristic", note


def rgb_to_hsv(r: float, g: float, b: float) -> Tuple[float, float, float]:
    mx = max(r, g, b)
    mn = min(r, g, b)
    delta = mx - mn
    if delta == 0:
        h = 0.0
    elif mx == r:
        h = ((g - b) / delta) % 6
    elif mx == g:
        h = (b - r) / delta + 2
    else:
        h = (r - g) / delta + 4
    h *= 60.0
    s = 0.0 if mx == 0 else delta / mx
    return h, s, mx


def candidate_weight(r: float, g: float, b: float) -> float:
    h, s, v = rgb_to_hsv(r, g, b)
    weight = 0.0
    if (h < 30 or h > 330) and s > 0.35 and 0.18 < v < 0.82:
        weight += 1.0
    if v < 0.16:
        weight += 0.7
    if 200 < h < 245 and s > 0.38 and 0.22 < v < 0.62:
        weight += 0.48
    if 30 < h < 55 and s > 0.55 and v > 0.58:
        weight += 0.18
    if s < 0.16 and v > 0.72:
        weight *= 0.08
    if 35 < h < 55 and s > 0.72 and v > 0.72:
        weight *= 0.08
    return weight


def build_points(
    rgb: np.ndarray,
    depth: np.ndarray,
    crop: Tuple[float, float, float, float],
    max_points: int,
    seed: int,
) -> dict:
    rng = random.Random(seed)
    h, w, _ = rgb.shape
    x0 = int(crop[0] * w)
    y0 = int(crop[1] * h)
    x1 = int(crop[2] * w)
    y1 = int(crop[3] * h)
    crop_w = max(1, x1 - x0)
    crop_h = max(1, y1 - y0)
    aspect = crop_w / crop_h

    candidates = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = [float(v) / 255.0 for v in rgb[y, x]]
            weight = candidate_weight(r, g, b)
            if weight > 0.05:
                candidates.append((x, y, r, g, b, float(depth[y, x]), weight))

    if not candidates:
        raise RuntimeError("no candidate pixels found; adjust crop or input image")

    rng.shuffle(candidates)
    keep_prob = min(1.0, (max_points / len(candidates)) * 1.7)
    chosen = []
    for item in candidates:
        if len(chosen) >= max_points:
            break
        if rng.random() < item[6] * keep_prob:
            chosen.append(item)
    while len(chosen) < min(max_points, len(candidates)):
        chosen.append(candidates[rng.randrange(len(candidates))])

    positions = []
    colors = []
    sizes = []
    depths = []
    seeds = []
    scale = 8.4
    for x, y, r, g, b, z_raw, _weight in chosen:
        u = (x - x0) / crop_w
        v = (y - y0) / crop_h
        wx = (u - 0.5) * scale * aspect
        wy = -(v - 0.5) * scale
        z = (z_raw - 0.5) * 2.0
        z += (rng.random() - 0.5) * 0.035
        lum = (r + g + b) / 3.0
        figure_color = (r - 0.4 * (g + b)) > 0.08
        size = (0.95 if figure_color else 0.58) * (0.62 + rng.random() * 0.78)
        if lum < 0.16:
            size *= 0.82

        positions.extend([round(wx, 4), round(wy, 4), round(z, 4)])
        colors.extend([round(min(1.0, r * 1.12), 4), round(min(1.0, g * 1.07), 4), round(min(1.0, b * 1.07), 4)])
        sizes.append(round(size, 4))
        depths.append(round(float(z_raw), 4))
        seeds.append(round(rng.random(), 5))

    return {
        "positions": positions,
        "colors": colors,
        "sizes": sizes,
        "depths": depths,
        "seeds": seeds,
    }


def write_depth_png(depth: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray((normalize_depth(depth) * 255).astype(np.uint8), mode="L")
    img.save(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="source image path")
    parser.add_argument("--out", required=True, help="output prefix, e.g. public/data/oracle")
    parser.add_argument("--crop", type=parse_crop, default=(0.0, 0.0, 1.0, 1.0))
    parser.add_argument("--sample-size", type=int, default=640)
    parser.add_argument("--max-points", type=int, default=52000)
    parser.add_argument("--seed", type=int, default=4107)
    parser.add_argument("--mode", choices=["auto", "heuristic", "da-v2"], default="auto")
    parser.add_argument("--model-dir", default=os.environ.get("DEPTH_ANYTHING_V2_DIR"))
    parser.add_argument("--checkpoint", default=os.environ.get("DEPTH_ANYTHING_V2_CHECKPOINT"))
    parser.add_argument("--encoder", choices=sorted(MODEL_CONFIGS), default=os.environ.get("DEPTH_ANYTHING_V2_ENCODER", "vits"))
    parser.add_argument("--input-size", type=int, default=int(os.environ.get("DEPTH_ANYTHING_V2_INPUT_SIZE", "518")))
    args = parser.parse_args()

    image_path = Path(args.input).expanduser()
    out_prefix = Path(args.out)
    if not image_path.exists():
        raise SystemExit(f"input not found: {image_path}")

    src = Image.open(image_path).convert("RGB")
    src.thumbnail((args.sample_size, args.sample_size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (args.sample_size, args.sample_size), (0, 0, 0))
    canvas.paste(src, ((args.sample_size - src.width) // 2, (args.sample_size - src.height) // 2))
    rgb = np.asarray(canvas, dtype=np.uint8)

    depth, mode, note = choose_depth(args, image_path, rgb)
    if depth.shape[:2] != rgb.shape[:2]:
        depth_img = Image.fromarray((normalize_depth(depth) * 255).astype(np.uint8), mode="L")
        depth_img = depth_img.resize((args.sample_size, args.sample_size), Image.Resampling.BICUBIC)
        depth = np.asarray(depth_img, dtype=np.float32) / 255.0

    points = build_points(rgb, depth, args.crop, args.max_points, args.seed)
    point_count = len(points["sizes"])
    points["mode"] = mode

    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    with open(out_prefix.with_name(out_prefix.name + "-points.json"), "w", encoding="utf-8") as fh:
        json.dump(points, fh, separators=(",", ":"))

    write_depth_png(depth, out_prefix.with_name(out_prefix.name + "-depth.png"))
    canvas.save(out_prefix.with_name(out_prefix.name + "-source.jpg"), quality=92)

    meta = BuildMeta(
        source=str(image_path),
        mode=mode,
        crop=args.crop,
        sample_size=args.sample_size,
        max_points=args.max_points,
        point_count=point_count,
        depth_min=float(np.min(depth)),
        depth_max=float(np.max(depth)),
        note=note,
    )
    with open(out_prefix.with_name(out_prefix.name + ".meta.json"), "w", encoding="utf-8") as fh:
        json.dump(asdict(meta), fh, indent=2)

    print(f"wrote {point_count} points using {mode}: {out_prefix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
