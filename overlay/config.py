from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "theme": {
        "font_size": 44,
        "small_font_size": 30,
        "label_font_size": 16,
        "panel_fill": [4, 8, 12, 132],
        "panel_outline": [255, 255, 255, 34],
        "text_fill": [255, 255, 255, 245],
        "muted_fill": [220, 228, 235, 195],
        "accent_fill": [35, 180, 255, 235],
        "warning_fill": [255, 210, 70, 235],
        "track_fill": [255, 255, 255, 210],
        "panel_radius": 7,
        "margin": 28,
        "gap": 12,
    },
    "widgets": {
        "speed": {"enabled": True, "x": 28, "y": 28, "w": 210, "h": 78},
        "distance": {"enabled": True, "x": 250, "y": 28, "w": 190, "h": 78},
        "altitude": {"enabled": True, "x": 452, "y": 28, "w": 144, "h": 78},
        "heart_rate": {"enabled": True, "x": 608, "y": 28, "w": 150, "h": 78},
        "cadence": {"enabled": False, "x": 770, "y": 28, "w": 144, "h": 78},
        "power": {"enabled": True, "x": 770, "y": 28, "w": 144, "h": 78},
        "temperature": {"enabled": True, "x": 926, "y": 28, "w": 132, "h": 78},
        "elevation_profile": {"enabled": True, "x": 28, "y": -28, "w": 520, "h": 128},
        "track_map": {"enabled": True, "x": -28, "y": -28, "w": 236, "h": 184},
    },
    "render": {
        "show_panel_for_missing": False,
        "smoothing_seconds": 1.5,
        "png_pattern": "frame_%06d.png",
    },
}


def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | None) -> Dict[str, Any]:
    if not path:
        return deepcopy(DEFAULT_CONFIG)

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        user_config = json.load(handle)
    return _deep_merge(DEFAULT_CONFIG, user_config)


def layout_scale(width: int, height: int) -> float:
    return min(width / 1280.0, height / 720.0)


def resolve_box(widget: Dict[str, Any], width: int, height: int, scale: float | None = None) -> tuple[int, int, int, int]:
    scale = layout_scale(width, height) if scale is None else scale
    raw_x = float(widget["x"])
    raw_y = float(widget["y"])
    w = int(round(float(widget["w"]) * scale))
    h = int(round(float(widget["h"]) * scale))
    if raw_x < 0:
        x = int(round(width + raw_x * scale - w))
    else:
        x = int(round(raw_x * scale))
    if raw_y < 0:
        y = int(round(height + raw_y * scale - h))
    else:
        y = int(round(raw_y * scale))
    return x, y, w, h
