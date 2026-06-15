from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw

from .widgets import draw_widgets


class RenderError(RuntimeError):
    pass


def _rate_to_float(rate: str | None) -> Optional[float]:
    if not rate:
        return None
    if "/" in rate:
        num, den = rate.split("/", 1)
        try:
            denominator = float(den)
            if denominator == 0:
                return None
            return float(num) / denominator
        except ValueError:
            return None
    try:
        return float(rate)
    except ValueError:
        return None


def probe_video(path: str) -> Dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RenderError(
            "ffprobe was not found. Provide --duration, --width, --height and --fps manually, "
            "or install ffmpeg/ffprobe."
        )

    command = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,r_frame_rate,duration:format=duration",
        "-of",
        "json",
        path,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RenderError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    info = json.loads(result.stdout)
    streams = info.get("streams") or []
    if not streams:
        raise RenderError(f"No video stream found in {path}")
    stream = streams[0]
    duration = stream.get("duration") or (info.get("format") or {}).get("duration")
    fps = _rate_to_float(stream.get("avg_frame_rate")) or _rate_to_float(stream.get("r_frame_rate"))
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration": float(duration) if duration is not None else None,
        "fps": fps,
    }


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def render_frame(width: int, height: int, frame_index: int, timeline: Dict[str, Any], config: Dict[str, Any]) -> Image.Image:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    draw_widgets(draw, frame_index, timeline, config, width, height)
    return image


def render_png_sequence(
    output_dir: str,
    width: int,
    height: int,
    timeline: Dict[str, Any],
    config: Dict[str, Any],
    pattern: str | None = None,
) -> Path:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    filename_pattern = pattern or config["render"].get("png_pattern", "frame_%06d.png")
    for frame_index in range(timeline["frame_count"]):
        frame = render_frame(width, height, frame_index, timeline, config)
        frame.save(target / (filename_pattern % frame_index))
    return target


def render_prores4444(
    output_path: str,
    width: int,
    height: int,
    fps: float,
    timeline: Dict[str, Any],
    config: Dict[str, Any],
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError("ffmpeg was not found")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s:v",
        f"{width}x{height}",
        "-r",
        f"{fps}",
        "-i",
        "-",
        "-an",
        "-c:v",
        "prores_ks",
        "-profile:v",
        "4444",
        "-pix_fmt",
        "yuva444p10le",
        str(target),
    ]

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    try:
        for frame_index in range(timeline["frame_count"]):
            frame = render_frame(width, height, frame_index, timeline, config)
            process.stdin.write(frame.tobytes("raw", "RGBA"))
    except BaseException:
        process.kill()
        process.wait()
        raise
    finally:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()

    stderr = process.stderr.read() if process.stderr is not None else b""
    process.wait()
    if process.returncode != 0:
        message = stderr.decode("utf-8", errors="replace").strip()
        raise RenderError(f"ffmpeg ProRes 4444 export failed: {message}")
    return target


def render_nvenc_preview(
    output_path: str,
    width: int,
    height: int,
    fps: float,
    timeline: Dict[str, Any],
    config: Dict[str, Any],
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError("ffmpeg was not found")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s:v",
        f"{width}x{height}",
        "-r",
        f"{fps}",
        "-i",
        "-",
        "-an",
        # NVENC is useful for fast timing/layout previews. It does not preserve
        # alpha, so this path must not replace ProRes 4444 or PNG for Resolve.
        "-vf",
        "format=nv12",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p4",
        "-cq",
        "19",
        "-pix_fmt",
        "yuv420p",
        str(target),
    ]

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    try:
        for frame_index in range(timeline["frame_count"]):
            frame = render_frame(width, height, frame_index, timeline, config)
            process.stdin.write(frame.tobytes("raw", "RGBA"))
    except BaseException:
        process.kill()
        process.wait()
        raise
    finally:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()

    stderr = process.stderr.read() if process.stderr is not None else b""
    process.wait()
    if process.returncode != 0:
        message = stderr.decode("utf-8", errors="replace").strip()
        raise RenderError(f"ffmpeg NVENC preview export failed: {message}")
    return target


def render_composite_nvenc(
    output_path: str,
    source_video: str,
    music_path: str | None,
    width: int,
    height: int,
    fps: float,
    duration: float,
    timeline: Dict[str, Any],
    config: Dict[str, Any],
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError("ffmpeg was not found")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-thread_queue_size",
        "1024",
        "-i",
        source_video,
    ]
    if music_path:
        command.extend(["-stream_loop", "-1", "-i", music_path])
    command.extend(
        [
            "-thread_queue_size",
            "1024",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s:v",
            f"{width}x{height}",
            "-r",
            f"{fps}",
            "-i",
            "-",
            "-filter_complex",
            "[0:v][1:v]overlay=0:0:format=auto[v]" if not music_path else "[0:v][2:v]overlay=0:0:format=auto[v]",
            "-map",
            "[v]",
        ]
    )
    if music_path:
        command.extend(["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"])
    else:
        command.extend(["-map", "0:a?", "-c:a", "copy"])
    command.extend(
        [
            "-t",
            f"{duration}",
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p4",
            "-cq",
            "19",
            "-dn",
            "-map_metadata",
            "-1",
            "-write_tmcd",
            "0",
            "-shortest",
            str(target),
        ]
    )

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    try:
        for frame_index in range(timeline["frame_count"]):
            frame = render_frame(width, height, frame_index, timeline, config)
            process.stdin.write(frame.tobytes("raw", "RGBA"))
    except BaseException:
        process.kill()
        process.wait()
        raise
    finally:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()

    stderr = process.stderr.read() if process.stderr is not None else b""
    process.wait()
    if process.returncode != 0:
        message = stderr.decode("utf-8", errors="replace").strip()
        raise RenderError(f"ffmpeg composite NVENC export failed: {message}")
    return target


def render_composite_x264(
    output_path: str,
    source_video: str,
    music_path: str | None,
    width: int,
    height: int,
    fps: float,
    duration: float,
    timeline: Dict[str, Any],
    config: Dict[str, Any],
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError("ffmpeg was not found")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    raw_input_index = 2 if music_path else 1

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-thread_queue_size",
        "1024",
        "-i",
        source_video,
    ]
    if music_path:
        command.extend(["-stream_loop", "-1", "-i", music_path])
    command.extend(
        [
            "-thread_queue_size",
            "1024",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s:v",
            f"{width}x{height}",
            "-r",
            f"{fps}",
            "-i",
            "-",
            "-filter_complex",
            (
                f"[0:v]scale={width}:{height}:flags=lanczos,fps={fps},format=rgba[base];"
                f"[base][{raw_input_index}:v]overlay=0:0:format=auto[v]"
            ),
            "-map",
            "[v]",
        ]
    )
    if music_path:
        command.extend(["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"])
    else:
        command.extend(["-map", "0:a?", "-c:a", "copy"])
    command.extend(
        [
            "-t",
            f"{duration}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-dn",
            "-map_metadata",
            "-1",
            "-write_tmcd",
            "0",
            "-movflags",
            "+faststart",
            "-shortest",
            str(target),
        ]
    )

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    try:
        for frame_index in range(timeline["frame_count"]):
            frame = render_frame(width, height, frame_index, timeline, config)
            try:
                process.stdin.write(frame.tobytes("raw", "RGBA"))
            except BrokenPipeError:
                break
    except BaseException:
        process.kill()
        process.wait()
        raise
    finally:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()

    stderr = process.stderr.read() if process.stderr is not None else b""
    process.wait()
    if process.returncode != 0:
        message = stderr.decode("utf-8", errors="replace").strip()
        raise RenderError(f"ffmpeg composite x264 export failed: {message}")
    return target


def render_overlay(
    output: str,
    width: int,
    height: int,
    fps: float,
    timeline: Dict[str, Any],
    config: Dict[str, Any],
    output_format: str = "auto",
) -> Path:
    if output_format not in {"auto", "prores", "png", "nvenc-preview"}:
        raise ValueError("output_format must be one of: auto, prores, png, nvenc-preview")

    if output_format == "png":
        return render_png_sequence(output, width, height, timeline, config)

    if output_format == "nvenc-preview":
        return render_nvenc_preview(output, width, height, fps, timeline, config)

    if output_format in {"auto", "prores"} and ffmpeg_available():
        try:
            return render_prores4444(output, width, height, fps, timeline, config)
        except RenderError:
            if output_format == "prores":
                raise

    if output_format == "prores":
        raise RenderError("ffmpeg was not found, so ProRes 4444 cannot be rendered")

    png_dir = str(Path(output).with_suffix("")) + "_png"
    return render_png_sequence(png_dir, width, height, timeline, config)
