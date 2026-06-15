from __future__ import annotations

from typing import Any, Dict, Iterable, List

import numpy as np


NUMERIC_FIELDS = [
    "latitude",
    "longitude",
    "speed",
    "altitude",
    "distance",
    "heart_rate",
    "cadence",
    "power",
    "temperature",
]


def _series(rows: Iterable[Dict[str, Any]], field: str) -> tuple[np.ndarray, np.ndarray]:
    times: List[float] = []
    values: List[float] = []
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(numeric):
            times.append(float(row["elapsed"]))
            values.append(numeric)
    if not times:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)

    pairs = sorted(zip(times, values), key=lambda item: item[0])
    deduped_times: List[float] = []
    deduped_values: List[float] = []
    for sample_time, sample_value in pairs:
        if deduped_times and sample_time == deduped_times[-1]:
            deduped_values[-1] = sample_value
        else:
            deduped_times.append(sample_time)
            deduped_values.append(sample_value)
    return np.asarray(deduped_times, dtype=float), np.asarray(deduped_values, dtype=float)


def _interpolate_field(target_times: np.ndarray, sample_times: np.ndarray, sample_values: np.ndarray) -> np.ndarray:
    output = np.full_like(target_times, np.nan, dtype=float)
    if len(sample_times) == 0:
        return output
    if len(sample_times) == 1:
        output[np.isclose(target_times, sample_times[0], atol=0.5)] = sample_values[0]
        return output
    valid = (target_times >= sample_times[0]) & (target_times <= sample_times[-1])
    output[valid] = np.interp(target_times[valid], sample_times, sample_values)
    return output


def _rolling_average(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1 or len(values) == 0:
        return values
    window = min(window, len(values))
    valid = np.isfinite(values)
    filled = np.where(valid, values, 0.0)
    weights = valid.astype(float)
    kernel = np.ones(window, dtype=float)
    total = np.convolve(filled, kernel, mode="same")
    count = np.convolve(weights, kernel, mode="same")
    smoothed = np.divide(total, count, out=np.full_like(values, np.nan), where=count > 0)
    return smoothed


def build_timeline(
    rows: List[Dict[str, Any]],
    duration: float,
    fps: float,
    offset: float = 0.0,
    time_scale: float = 1.0,
    smoothing_seconds: float = 0.0,
) -> Dict[str, Any]:
    if duration <= 0:
        raise ValueError("duration must be greater than zero")
    if fps <= 0:
        raise ValueError("fps must be greater than zero")
    if time_scale <= 0:
        raise ValueError("time_scale must be greater than zero")

    frame_count = int(np.ceil(duration * fps))
    video_times = np.arange(frame_count, dtype=float) / fps
    # Offset is video-relative before speed scaling: +3.2 means telemetry starts
    # 3.2 video seconds after video start. time_scale maps timelapse video time
    # to real FIT time, e.g. 10 means one video second equals ten FIT seconds.
    fit_times = (video_times - float(offset)) * float(time_scale)

    fields: Dict[str, np.ndarray] = {}
    smoothing_window = int(round(smoothing_seconds * fps)) if smoothing_seconds > 0 else 0
    for field in NUMERIC_FIELDS:
        sample_times, sample_values = _series(rows, field)
        values = _interpolate_field(fit_times, sample_times, sample_values)
        if field in {"speed", "altitude", "power"}:
            values = _rolling_average(values, smoothing_window)
        fields[field] = values

    return {
        "fps": fps,
        "duration": duration,
        "time_scale": time_scale,
        "frame_count": frame_count,
        "video_times": video_times,
        "fit_times": fit_times,
        "fields": fields,
    }
