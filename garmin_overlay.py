from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

from overlay.config import load_config
from overlay.fit_loader import load_fit, write_csv
from overlay.interpolate import build_timeline
from overlay.render import RenderError, probe_video, render_composite_nvenc, render_composite_x264, render_overlay


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a transparent Garmin FIT telemetry overlay for DaVinci Resolve."
    )
    parser.add_argument("--fit", required=True, help="Path to Garmin .fit file")
    parser.add_argument("--video", help="Optional source video used only for duration, size and FPS probing")
    parser.add_argument("--output", required=True, help="Output .mov path or PNG sequence directory")
    parser.add_argument("--csv", help="Optional CSV export for checking parsed FIT data")
    parser.add_argument("--config", help="Optional JSON config for widget positions/theme")
    parser.add_argument("--music", help="Optional music file for composite output")
    parser.add_argument("--duration", type=positive_float, help="Overlay duration in seconds")
    parser.add_argument("--width", type=positive_int, help="Overlay width, e.g. 3840")
    parser.add_argument("--height", type=positive_int, help="Overlay height, e.g. 2160")
    parser.add_argument("--fps", type=positive_float, help="Overlay framerate, e.g. 30")
    parser.add_argument(
        "--offset",
        type=float,
        default=0.0,
        help="Seconds to shift FIT data relative to video. Positive means telemetry starts after video.",
    )
    parser.add_argument(
        "--time-scale",
        type=positive_float,
        default=1.0,
        help="FIT seconds per video second. Use 10 for a video recorded/playbacked at 10x speed.",
    )
    parser.add_argument(
        "--smooth",
        type=float,
        default=None,
        help="Rolling average window in seconds for speed/altitude/power. Defaults to config value.",
    )
    parser.add_argument(
        "--format",
        choices=["auto", "prores", "png", "nvenc-preview", "composite-nvenc", "composite-x264"],
        default="auto",
        help="auto uses ProRes 4444 when ffmpeg is available, otherwise PNG sequence. nvenc-preview/composite-nvenc/composite-x264 outputs do not preserve alpha.",
    )
    parser.add_argument("--no-profile", action="store_true", help="Disable elevation profile widget")
    parser.add_argument("--no-track", action="store_true", help="Disable track map widget")
    parser.add_argument(
        "--theme",
        default="default",
        help="Reserved for future theme presets. The current version ships one default theme.",
    )
    return parser.parse_args()


def resolve_video_settings(args: argparse.Namespace) -> Dict[str, Any]:
    settings: Dict[str, Any] = {
        "width": args.width,
        "height": args.height,
        "duration": args.duration,
        "fps": args.fps,
    }
    if args.video:
        probed = probe_video(args.video)
        for key in settings:
            if settings[key] is None:
                settings[key] = probed.get(key)

    missing = [key for key, value in settings.items() if value is None]
    if missing:
        raise RenderError(
            "Missing video settings: "
            + ", ".join(missing)
            + ". Provide --video or set --duration, --width, --height and --fps."
        )
    return settings


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if args.no_profile:
        config["widgets"]["elevation_profile"]["enabled"] = False
    if args.no_track:
        config["widgets"]["track_map"]["enabled"] = False
    if args.smooth is not None:
        config["render"]["smoothing_seconds"] = max(0.0, float(args.smooth))

    try:
        fit_data = load_fit(args.fit)
        if args.csv:
            write_csv(fit_data.rows, args.csv)

        settings = resolve_video_settings(args)
        timeline = build_timeline(
            fit_data.rows,
            duration=float(settings["duration"]),
            fps=float(settings["fps"]),
            offset=float(args.offset),
            time_scale=float(args.time_scale),
            smoothing_seconds=float(config["render"].get("smoothing_seconds", 0.0)),
        )
        if args.format in {"composite-nvenc", "composite-x264"}:
            if not args.video:
                raise RenderError(f"--format {args.format} requires --video")
            composite_renderer = render_composite_nvenc if args.format == "composite-nvenc" else render_composite_x264
            output = composite_renderer(
                args.output,
                source_video=args.video,
                music_path=args.music,
                width=int(settings["width"]),
                height=int(settings["height"]),
                fps=float(settings["fps"]),
                duration=float(settings["duration"]),
                timeline=timeline,
                config=config,
            )
        else:
            output = render_overlay(
                args.output,
                width=int(settings["width"]),
                height=int(settings["height"]),
                fps=float(settings["fps"]),
                timeline=timeline,
                config=config,
                output_format=args.format,
            )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    fields = ", ".join(sorted(fit_data.available_fields)) or "none"
    print(f"FIT start: {fit_data.start_time.isoformat()}")
    print(f"FIT duration: {fit_data.duration:.1f} s")
    print(f"Available fields: {fields}")
    if args.csv:
        print(f"CSV written: {Path(args.csv)}")
    print(f"Overlay written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
