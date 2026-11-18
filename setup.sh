#!/usr/bin/env bash
# macOS 설치 스크립트. Windows는 setup.ps1을 사용한다.
# requirements.lock.txt는 Windows에서 만든 목록이라 맥 의존성(pyobjc 등)이 빠져 있어
# 맥에서는 requirements.txt로 설치한다.
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3.12}"
if [ ! -x .venv/bin/python ]; then
    "$PYTHON" -c "import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8, 'Install Python 3.12 64-bit first'"
    "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
if [ "${1:-}" != "--skip-model" ]; then
    .venv/bin/python -X utf8 main.py --download-model
fi
.venv/bin/python -X utf8 main.py --check-env
echo 'Setup complete. Run: ./run.sh demo'
