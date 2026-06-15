from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from overlay.config import load_config  # noqa: E402
from overlay.render import render_frame  # noqa: E402


def main() -> int:
    frame_count = 300
    current_frame = 186
    t = np.linspace(0.0, 1.0, frame_count)

    timeline = {
        "fps": 30.0,
        "duration": 10.0,
        "time_scale": 1.0,
        "frame_count": frame_count,
        "video_times": np.arange(frame_count, dtype=float) / 30.0,
        "fit_times": np.arange(frame_count, dtype=float) / 30.0,
        "fields": {
            "speed": (24.0 + 8.0 * np.sin(t * np.pi * 1.25)) / 3.6,
            "distance": 1400.0 + 4300.0 * t,
            "altitude": 415.0 + 88.0 * np.sin(t * np.pi * 0.9) + 34.0 * t,
            "heart_rate": 134.0 + 18.0 * np.sin(t * np.pi * 1.7),
            "cadence": np.full(frame_count, np.nan),
            "power": 184.0 + 58.0 * np.sin(t * np.pi * 2.1),
            "temperature": 22.0 + 2.0 * np.sin(t * np.pi * 0.5),
            "latitude": 0.006 * np.sin(t * np.pi * 1.4),
            "longitude": 0.008 * np.cos(t * np.pi * 1.9),
        },
    }

    image = render_frame(1280, 720, current_frame, timeline, load_config(None))
    output_path = ROOT / "examples" / "example-overlay.png"
    image.save(output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
