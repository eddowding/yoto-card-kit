#!/bin/bash
# Transcribe a long audiobook in fixed chunks and emit absolute-timestamped lines.
# Chunked deliberately: whisper base.en falls into repetition loops on long runs,
# and a loop silently poisons everything after it.
#   transcribe.sh <norm.m4a> <outdir> [chunk_seconds]
set -eu
if [ $# -lt 2 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  echo "usage: transcribe.sh <source-audio> <outdir> [chunk_seconds]" >&2
  exit 1
fi
SRC="$1"; OUT="$2"; CHUNK="${3:-600}"

# Model lives somewhere permanent. Override with WHISPER_MODEL if you keep it
# elsewhere. It is ~148MB, so it wants a real home, not a temp directory.
MODEL="${WHISPER_MODEL:-$HOME/.local/share/whisper/ggml-base.en.bin}"
if [ ! -s "$MODEL" ]; then
  echo "whisper model not found at: $MODEL" >&2
  echo "  mkdir -p \"$(dirname "$MODEL")\"" >&2
  echo "  curl -sL -o \"$MODEL\" https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin" >&2
  exit 1
fi
command -v whisper-cli >/dev/null || { echo "whisper-cli not found: brew install whisper-cpp" >&2; exit 1; }

mkdir -p "$OUT/chunks"

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC" | cut -d. -f1)
N=$(( (DUR + CHUNK - 1) / CHUNK ))
echo "duration=${DUR}s  chunks=$N x ${CHUNK}s"

: > "$OUT/transcript.txt"
for ((i=0; i<N; i++)); do
  OFF=$(( i * CHUNK ))
  wav="$OUT/chunks/c$(printf %03d "$i").wav"
  [ -s "$wav" ] || ffmpeg -nostdin -y -hide_banner -loglevel error \
      -ss "$OFF" -t "$CHUNK" -i "$SRC" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$wav"
  whisper-cli -m "$MODEL" -f "$wav" --no-prints -oj -of "${wav%.wav}" >/dev/null 2>&1
  python3 - "$OUT/chunks/c$(printf %03d "$i").json" "$OFF" >> "$OUT/transcript.txt" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
off = int(sys.argv[2])
for seg in data.get("transcription", []):
    t = seg["offsets"]["from"] / 1000.0 + off       # ms -> s, shifted to absolute
    print(f"{t:9.2f}\t{seg['text'].strip()}")
PY
  echo "  chunk $i / $N done" >&2
done
echo "wrote $OUT/transcript.txt"
