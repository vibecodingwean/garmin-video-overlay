from __future__ import annotations

from math import isfinite
from typing import Any, Dict, Tuple

import numpy as np
from PIL import ImageDraw, ImageFont

from .config import layout_scale, resolve_box


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def finite(value: Any) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def scaled_theme(theme: Dict[str, Any], scale: float) -> Dict[str, Any]:
    result = dict(theme)
    for key in ("font_size", "small_font_size", "label_font_size", "panel_radius", "gap", "margin"):
        result[key] = max(1, int(round(float(theme[key]) * scale)))
    return result


def panel(draw: ImageDraw.ImageDraw, box: Tuple[int, int, int, int], theme: Dict[str, Any]) -> None:
    x, y, w, h = box
    radius = int(theme["panel_radius"])
    draw.rounded_rectangle(
        [x, y, x + w, y + h],
        radius=radius,
        fill=tuple(theme["panel_fill"]),
        outline=tuple(theme["panel_outline"]),
        width=1,
    )


def draw_icon(
    draw: ImageDraw.ImageDraw,
    name: str,
    x: int,
    y: int,
    size: int,
    theme: Dict[str, Any],
) -> None:
    accent = tuple(theme["accent_fill"])
    muted = tuple(theme["muted_fill"])
    warning = tuple(theme["warning_fill"])
    stroke = max(1, size // 9)
    x2 = x + size
    y2 = y + size

    if name == "speed":
        draw.arc([x + 2, y + 3, x2 - 2, y2 - 2], start=200, end=340, fill=accent, width=stroke)
        center = (x + size // 2, y + int(size * 0.68))
        draw.line([center, (x + int(size * 0.72), y + int(size * 0.42))], fill=accent, width=stroke)
        draw.ellipse(
            [center[0] - stroke, center[1] - stroke, center[0] + stroke, center[1] + stroke],
            fill=accent,
        )
    elif name == "distance":
        draw.ellipse([x + int(size * 0.28), y + 1, x + int(size * 0.72), y + int(size * 0.44)], outline=accent, width=stroke)
        draw.line(
            [
                (x + int(size * 0.50), y + int(size * 0.44)),
                (x + int(size * 0.50), y + int(size * 0.92)),
            ],
            fill=accent,
            width=stroke,
        )
        draw.ellipse([x + int(size * 0.42), y + int(size * 0.14), x + int(size * 0.58), y + int(size * 0.30)], fill=accent)
    elif name == "altitude":
        points = [
            (x + int(size * 0.08), y + int(size * 0.78)),
            (x + int(size * 0.35), y + int(size * 0.30)),
            (x + int(size * 0.52), y + int(size * 0.58)),
            (x + int(size * 0.66), y + int(size * 0.40)),
            (x + int(size * 0.92), y + int(size * 0.78)),
        ]
        draw.line(points, fill=accent, width=stroke, joint="curve")
    elif name == "heart":
        points = [
            (x + int(size * 0.50), y + int(size * 0.86)),
            (x + int(size * 0.18), y + int(size * 0.50)),
            (x + int(size * 0.22), y + int(size * 0.26)),
            (x + int(size * 0.40), y + int(size * 0.22)),
            (x + int(size * 0.50), y + int(size * 0.36)),
            (x + int(size * 0.60), y + int(size * 0.22)),
            (x + int(size * 0.78), y + int(size * 0.26)),
            (x + int(size * 0.82), y + int(size * 0.50)),
            (x + int(size * 0.50), y + int(size * 0.86)),
        ]
        draw.line(points, fill=warning, width=stroke, joint="curve")
    elif name == "power":
        points = [
            (x + int(size * 0.60), y + int(size * 0.05)),
            (x + int(size * 0.20), y + int(size * 0.56)),
            (x + int(size * 0.48), y + int(size * 0.56)),
            (x + int(size * 0.36), y + int(size * 0.95)),
            (x + int(size * 0.80), y + int(size * 0.42)),
            (x + int(size * 0.52), y + int(size * 0.42)),
        ]
        draw.polygon(points, fill=accent)
    elif name == "temperature":
        stem_x = x + int(size * 0.52)
        draw.line([(stem_x, y + int(size * 0.12)), (stem_x, y + int(size * 0.62))], fill=accent, width=stroke)
        draw.rounded_rectangle(
            [stem_x - stroke * 2, y + 1, stem_x + stroke * 2, y + int(size * 0.67)],
            radius=stroke * 2,
            outline=accent,
            width=stroke,
        )
        draw.ellipse(
            [x + int(size * 0.30), y + int(size * 0.58), x + int(size * 0.72), y + int(size * 0.98)],
            fill=accent,
        )
    elif name == "profile":
        draw.line(
            [
                (x + int(size * 0.08), y + int(size * 0.75)),
                (x + int(size * 0.30), y + int(size * 0.48)),
                (x + int(size * 0.48), y + int(size * 0.60)),
                (x + int(size * 0.72), y + int(size * 0.30)),
                (x + int(size * 0.94), y + int(size * 0.75)),
            ],
            fill=accent,
            width=stroke,
            joint="curve",
        )
    elif name == "track":
        points = [
            (x + int(size * 0.18), y + int(size * 0.18)),
            (x + int(size * 0.42), y + int(size * 0.38)),
            (x + int(size * 0.34), y + int(size * 0.66)),
            (x + int(size * 0.72), y + int(size * 0.84)),
        ]
        draw.line(points, fill=muted, width=stroke, joint="curve")
        for px, py in (points[0], points[-1]):
            draw.ellipse([px - stroke * 2, py - stroke * 2, px + stroke * 2, py + stroke * 2], fill=accent)


def draw_title(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    icon_name: str,
    theme: Dict[str, Any],
    label_font: ImageFont.ImageFont,
) -> None:
    icon_size = max(10, int(theme["label_font_size"] * 1.08))
    draw_icon(draw, icon_name, x, y + max(0, icon_size // 10), icon_size, theme)
    draw.text(
        (x + icon_size + max(5, icon_size // 3), y - max(0, icon_size // 20)),
        label.upper(),
        fill=tuple(theme["muted_fill"]),
        font=label_font,
    )


def text_widget(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    label: str,
    icon_name: str,
    value: float,
    unit: str,
    theme: Dict[str, Any],
    font: ImageFont.ImageFont,
    label_font: ImageFont.ImageFont,
    unit_font: ImageFont.ImageFont,
    decimals: int = 0,
) -> None:
    if not finite(value):
        return
    panel(draw, box, theme)
    x, y, w, h = box
    pad_x = max(10, int(round(12 * h / 78)))
    title_y = y + max(7, int(round(8 * h / 78)))
    draw_title(draw, x + pad_x, title_y, label, icon_name, theme, label_font)

    value_text = f"{float(value):.{decimals}f}"
    bbox = draw.textbbox((0, 0), value_text, font=font)
    value_h = bbox[3] - bbox[1]
    value_y = y + h - value_h - max(7, int(round(9 * h / 78))) - bbox[1]
    draw.text((x + pad_x, value_y), value_text, fill=tuple(theme["text_fill"]), font=font)
    value_w = bbox[2] - bbox[0]
    unit_bbox = draw.textbbox((0, 0), unit, font=unit_font)
    unit_h = unit_bbox[3] - unit_bbox[1]
    unit_x = x + pad_x + value_w + max(5, int(round(7 * h / 78)))
    unit_y = value_y + value_h - unit_h - max(1, int(round(2 * h / 78))) - unit_bbox[1]
    if unit_x + unit_bbox[2] - unit_bbox[0] <= x + w - pad_x:
        draw.text((unit_x, unit_y), unit, fill=tuple(theme["muted_fill"]), font=unit_font)


def elevation_profile(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    altitude: np.ndarray,
    current_index: int,
    theme: Dict[str, Any],
    label_font: ImageFont.ImageFont,
) -> None:
    valid = np.isfinite(altitude)
    if valid.sum() < 3:
        return
    panel(draw, box, theme)
    x, y, w, h = box
    pad = max(12, int(round(16 * h / 128)))
    title_y = y + max(8, int(round(9 * h / 128)))
    draw_title(draw, x + pad, title_y, "Profile", "profile", theme, label_font)
    graph_top = y + pad + int(theme["label_font_size"]) + max(10, int(round(10 * h / 128)))
    graph_bottom = y + h - pad
    values = altitude.copy()
    values[~valid] = np.nan
    min_alt = float(np.nanmin(values))
    max_alt = float(np.nanmax(values))
    if max_alt - min_alt < 1:
        max_alt = min_alt + 1
    xs = np.linspace(x + pad, x + w - pad, len(values))
    ys = graph_bottom - ((values - min_alt) / (max_alt - min_alt)) * max(1, graph_bottom - graph_top)
    points = [(float(px), float(py)) for px, py, ok in zip(xs, ys, valid) if ok]
    if len(points) >= 2:
        draw.line(points, fill=tuple(theme["accent_fill"]), width=max(2, int(round(2.4 * h / 128))), joint="curve")
    if 0 <= current_index < len(xs) and valid[current_index]:
        cx = float(xs[current_index])
        cy = float(ys[current_index])
        dot = max(4, int(round(4.5 * h / 128)))
        draw.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill=tuple(theme["warning_fill"]))


def track_map(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    current_index: int,
    theme: Dict[str, Any],
    label_font: ImageFont.ImageFont,
) -> None:
    valid = np.isfinite(latitudes) & np.isfinite(longitudes)
    if valid.sum() < 3:
        return
    panel(draw, box, theme)
    x, y, w, h = box
    pad = max(12, int(round(15 * h / 184)))
    title_y = y + max(8, int(round(9 * h / 184)))
    draw_title(draw, x + pad, title_y, "Track", "track", theme, label_font)
    graph_top = y + pad + int(theme["label_font_size"]) + max(10, int(round(10 * h / 184)))
    graph_bottom = y + h - pad
    lat = latitudes[valid]
    lon = longitudes[valid]
    min_lat, max_lat = float(np.min(lat)), float(np.max(lat))
    min_lon, max_lon = float(np.min(lon)), float(np.max(lon))
    if max_lat - min_lat < 1e-8 or max_lon - min_lon < 1e-8:
        return

    all_x = x + pad + ((longitudes - min_lon) / (max_lon - min_lon)) * (w - 2 * pad)
    all_y = graph_bottom - ((latitudes - min_lat) / (max_lat - min_lat)) * max(1, graph_bottom - graph_top)
    points = [(float(px), float(py)) for px, py, ok in zip(all_x, all_y, valid) if ok]
    if len(points) >= 2:
        draw.line(points, fill=tuple(theme["track_fill"]), width=max(2, int(round(2.4 * h / 184))), joint="curve")
    if 0 <= current_index < len(all_x) and valid[current_index]:
        cx = float(all_x[current_index])
        cy = float(all_y[current_index])
        dot = max(4, int(round(4.5 * h / 184)))
        draw.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill=tuple(theme["warning_fill"]))


def draw_widgets(draw: ImageDraw.ImageDraw, frame_index: int, timeline: Dict[str, Any], config: Dict[str, Any], width: int, height: int) -> None:
    scale = layout_scale(width, height)
    theme = scaled_theme(config["theme"], scale)
    widgets = config["widgets"]
    fields = timeline["fields"]

    font = load_font(int(theme["font_size"]), bold=True)
    small_font = load_font(int(theme["small_font_size"]), bold=True)
    label_font = load_font(int(theme["label_font_size"]), bold=True)
    unit_font = load_font(int(theme["label_font_size"]), bold=False)

    def value(name: str) -> float:
        series = fields.get(name)
        if series is None or frame_index >= len(series):
            return float("nan")
        return float(series[frame_index])

    specs = [
        ("speed", "speed", "Speed", "speed", value("speed") * 3.6, "km/h", font, 1),
        ("distance", "distance", "Dist", "distance", value("distance") / 1000.0, "km", font, 2),
        ("altitude", "altitude", "Alt", "altitude", value("altitude"), "m", small_font, 0),
        ("heart_rate", "heart_rate", "Heart", "heart", value("heart_rate"), "bpm", small_font, 0),
        ("power", "power", "Power", "power", value("power"), "W", small_font, 0),
        ("temperature", "temperature", "Temp", "temperature", value("temperature"), "C", small_font, 0),
    ]

    for widget_name, field_name, label, icon_name, widget_value, unit, widget_font, decimals in specs:
        widget = widgets.get(widget_name, {})
        if not widget.get("enabled", True):
            continue
        if not finite(value(field_name)):
            continue
        text_widget(
            draw,
            resolve_box(widget, width, height, scale),
            label,
            icon_name,
            widget_value,
            unit,
            theme,
            widget_font,
            label_font,
            unit_font,
            decimals,
        )

    profile_widget = widgets.get("elevation_profile", {})
    if profile_widget.get("enabled", True):
        elevation_profile(
            draw,
            resolve_box(profile_widget, width, height, scale),
            fields["altitude"],
            frame_index,
            theme,
            label_font,
        )

    track_widget = widgets.get("track_map", {})
    if track_widget.get("enabled", True):
        track_map(
            draw,
            resolve_box(track_widget, width, height, scale),
            fields["latitude"],
            fields["longitude"],
            frame_index,
            theme,
            label_font,
        )
