#!/usr/bin/env bash
# macOS 실행 스크립트. 사용법: bash run.sh [모드] [카메라 번호]
# 실제 PPT 입력(present)은 현재 Windows 전용이라 제공하지 않는다.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
    echo 'Run ./setup.sh first, or use Python 3.12 to run main.py --demo.' >&2
    exit 1
fi
MODE="${1:-demo}"
CAMERA="${2:-0}"
case "$MODE" in
    demo) ARGS=(--demo) ;;
    preview) ARGS=(--camera "$CAMERA") ;;
    check) ARGS=(--check-model) ;;
    desktop-demo) ARGS=(--desktop --demo) ;;
    desktop-preview) ARGS=(--desktop --camera "$CAMERA") ;;
    desktop) ARGS=(--desktop --camera "$CAMERA" --enable-input) ;;
    *) echo "Unknown mode: $MODE (demo, preview, check, desktop-demo, desktop-preview, desktop)" >&2; exit 2 ;;
esac
exec .venv/bin/python -X utf8 main.py "${ARGS[@]}"
