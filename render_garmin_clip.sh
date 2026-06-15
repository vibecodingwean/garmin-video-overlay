#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
VIDEO=""
FIT=""
OUTPUT=""
WIDTH="1920"
HEIGHT="1080"
OFFSET="0"
TIME_SCALE="auto"
FORMAT="composite-x264"
PREVIEW_SECONDS=""
START_SECONDS=""
MUSIC=""
KEEP_TEMP="0"

usage() {
  cat <<'USAGE'
Usage:
  ./render_garmin_clip.sh --video input.mp4 --fit ride.fit --output output.mp4
  ./render_garmin_clip.sh --video input.mp4 --fit ride.fit --preview 5 --output preview.mp4

Options:
  --video PATH          Source video.
  --fit PATH            Garmin FIT file.
  --output PATH         Output video path. Defaults to ~/Downloads/<video>_overlay_1080p.mp4.
  --width PX            Output width. Default: 1920.
  --height PX           Output height. Default: 1080.
  --offset SECONDS      Manual sync offset in video seconds. Default: 0.
  --time-scale VALUE    FIT seconds per video second, or auto. Default: auto.
  --preview SECONDS     Render only a preview clip. If --start is omitted, uses the video middle.
  --start SECONDS       Preview start time in the source video.
  --music PATH          Optional music file for composite output.
  --format FORMAT       garmin_overlay.py output format. Default: composite-x264.
  --keep-temp           Keep temporary preview source clip.
  -h, --help            Show this help.

Offset rule:
  If telemetry appears too early, increase --offset, e.g. --offset 0.5.
  If telemetry appears too late, decrease --offset, e.g. --offset -0.5.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --video) VIDEO="${2:-}"; shift 2 ;;
    --fit) FIT="${2:-}"; shift 2 ;;
    --output) OUTPUT="${2:-}"; shift 2 ;;
    --width) WIDTH="${2:-}"; shift 2 ;;
    --height) HEIGHT="${2:-}"; shift 2 ;;
    --offset) OFFSET="${2:-}"; shift 2 ;;
    --time-scale) TIME_SCALE="${2:-}"; shift 2 ;;
    --preview) PREVIEW_SECONDS="${2:-}"; shift 2 ;;
    --start) START_SECONDS="${2:-}"; shift 2 ;;
    --music) MUSIC="${2:-}"; shift 2 ;;
    --format) FORMAT="${2:-}"; shift 2 ;;
    --keep-temp) KEEP_TEMP="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$VIDEO" || -z "$FIT" ]]; then
  echo "Error: --video and --fit are required." >&2
  usage >&2
  exit 2
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "Error: Python venv not found at $PYTHON. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

if ! command -v ffprobe >/dev/null || ! command -v ffmpeg >/dev/null; then
  echo "Error: ffmpeg and ffprobe are required." >&2
  exit 1
fi

if [[ -z "$OUTPUT" ]]; then
  video_name="$(basename "$VIDEO")"
  video_stem="${video_name%.*}"
  suffix="overlay_${WIDTH}x${HEIGHT}"
  if [[ -n "$PREVIEW_SECONDS" ]]; then
    suffix="preview_${PREVIEW_SECONDS}s_${WIDTH}x${HEIGHT}"
  fi
  OUTPUT="$HOME/Downloads/${video_stem}_${suffix}.mp4"
fi

VIDEO_DURATION="$(ffprobe -hide_banner -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VIDEO")"
FIT_DURATION="$(PYTHONPATH="$ROOT_DIR" FIT_PATH="$FIT" "$PYTHON" - <<'PY'
import os
from overlay.fit_loader import load_fit
print(load_fit(os.environ["FIT_PATH"]).duration)
PY
)"

if [[ "$TIME_SCALE" == "auto" ]]; then
  TIME_SCALE="$(awk -v fit="$FIT_DURATION" -v video="$VIDEO_DURATION" 'BEGIN { printf "%.9f", fit / video }')"
fi

SOURCE_VIDEO="$VIDEO"
SCRIPT_OFFSET="$OFFSET"
TEMP_DIR=""

if [[ -n "$PREVIEW_SECONDS" ]]; then
  if [[ -z "$START_SECONDS" ]]; then
    START_SECONDS="$(awk -v dur="$VIDEO_DURATION" -v preview="$PREVIEW_SECONDS" 'BEGIN { start = dur / 2 - preview / 2; if (start < 0) start = 0; printf "%.6f", start }')"
  fi
  SCRIPT_OFFSET="$(awk -v offset="$OFFSET" -v start="$START_SECONDS" 'BEGIN { printf "%.6f", offset - start }')"
  TEMP_DIR="$(mktemp -d /tmp/garmin-overlay-preview.XXXXXX)"
  SOURCE_VIDEO="$TEMP_DIR/preview_source.mp4"
  ffmpeg -y -hide_banner -loglevel error \
    -ss "$START_SECONDS" \
    -i "$VIDEO" \
    -t "$PREVIEW_SECONDS" \
    -map 0:v:0 \
    -map 0:a? \
    -vf "scale=${WIDTH}:${HEIGHT}:flags=lanczos" \
    -c:v libx264 \
    -preset veryfast \
    -crf 20 \
    -pix_fmt yuv420p \
    -c:a aac \
    -b:a 128k \
    "$SOURCE_VIDEO"
fi

echo "video:      $VIDEO"
echo "fit:        $FIT"
echo "output:     $OUTPUT"
echo "duration:   video=${VIDEO_DURATION}s fit=${FIT_DURATION}s"
echo "time-scale: $TIME_SCALE"
echo "offset:     $OFFSET"
if [[ -n "$PREVIEW_SECONDS" ]]; then
  echo "preview:    ${PREVIEW_SECONDS}s from source second ${START_SECONDS}"
  echo "segment offset passed to renderer: $SCRIPT_OFFSET"
fi

COMMAND=(
  "$PYTHON" "$ROOT_DIR/garmin_overlay.py"
  --fit "$FIT"
  --video "$SOURCE_VIDEO"
  --output "$OUTPUT"
  --width "$WIDTH"
  --height "$HEIGHT"
  --time-scale "$TIME_SCALE"
  --offset "$SCRIPT_OFFSET"
  --format "$FORMAT"
)

if [[ -n "$MUSIC" ]]; then
  COMMAND+=(--music "$MUSIC")
fi

"${COMMAND[@]}"

ffprobe -hide_banner -v error \
  -show_entries format=duration,size:stream=index,codec_name,codec_type,width,height,avg_frame_rate,duration \
  -of default=noprint_wrappers=1 \
  "$OUTPUT"

if [[ -n "$TEMP_DIR" && "$KEEP_TEMP" != "1" ]]; then
  rm -rf "$TEMP_DIR"
elif [[ -n "$TEMP_DIR" ]]; then
  echo "temporary preview source kept at: $TEMP_DIR"
fi
