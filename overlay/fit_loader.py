from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import fitdecode
except ImportError as exc:  # pragma: no cover - exercised by users without deps
    fitdecode = None
    FITDECODE_IMPORT_ERROR = exc
else:
    FITDECODE_IMPORT_ERROR = None


FIELDNAMES = [
    "timestamp",
    "elapsed",
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


@dataclass
class FitData:
    rows: List[Dict[str, Any]]
    start_time: datetime

    @property
    def duration(self) -> float:
        if not self.rows:
            return 0.0
        return float(self.rows[-1].get("elapsed") or 0.0)

    @property
    def available_fields(self) -> set[str]:
        fields: set[str] = set()
        for row in self.rows:
            for key, value in row.items():
                if key in {"timestamp", "elapsed"}:
                    continue
                if value is not None:
                    fields.add(key)
        return fields


def semicircles_to_degrees(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value) * (180.0 / 2**31)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_present(fields: Dict[str, Any], *names: str) -> Any:
    for name in names:
        value = fields.get(name)
        if value is not None:
            return value
    return None


def _normalize_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        # FIT timestamps are UTC by definition. Some libraries expose them as
        # naive datetimes, so pinning UTC avoids local-time drift in offsets.
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _field_map(message: Any) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    for field in message.fields:
        name = getattr(field, "name", None)
        if name:
            fields[name] = field.value
    return fields


def load_fit(path: str) -> FitData:
    if fitdecode is None:
        raise RuntimeError(
            "fitdecode is not installed. Install dependencies with: pip install -r requirements.txt"
        ) from FITDECODE_IMPORT_ERROR

    fit_path = Path(path)
    if not fit_path.exists():
        raise FileNotFoundError(f"FIT file not found: {fit_path}")

    rows: List[Dict[str, Any]] = []
    with fitdecode.FitReader(str(fit_path)) as fit_file:
        for frame in fit_file:
            if not isinstance(frame, fitdecode.records.FitDataMessage):
                continue
            if frame.name != "record":
                continue
            fields = _field_map(frame)
            timestamp = _normalize_timestamp(fields.get("timestamp"))
            if timestamp is None:
                continue

            lat_raw = fields.get("position_lat")
            lon_raw = fields.get("position_long")
            row: Dict[str, Any] = {
                "timestamp": timestamp,
                "latitude": semicircles_to_degrees(lat_raw),
                "longitude": semicircles_to_degrees(lon_raw),
                "speed": _as_float(_first_present(fields, "enhanced_speed", "speed")),
                "altitude": _as_float(_first_present(fields, "enhanced_altitude", "altitude")),
                "distance": _as_float(fields.get("distance")),
                "heart_rate": _as_float(fields.get("heart_rate")),
                "cadence": _as_float(fields.get("cadence")),
                "power": _as_float(fields.get("power")),
                "temperature": _as_float(fields.get("temperature")),
            }
            rows.append(row)

    if not rows:
        raise ValueError(f"No record messages with timestamps found in {fit_path}")

    rows.sort(key=lambda item: item["timestamp"])
    start_time = rows[0]["timestamp"]
    for row in rows:
        row["elapsed"] = (row["timestamp"] - start_time).total_seconds()

    return FitData(rows=rows, start_time=start_time)


def write_csv(rows: Iterable[Dict[str, Any]], path: str) -> None:
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            out = {key: row.get(key) for key in FIELDNAMES}
            timestamp = out.get("timestamp")
            if isinstance(timestamp, datetime):
                out["timestamp"] = timestamp.isoformat()
            writer.writerow(out)
