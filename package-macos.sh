#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
if [ ! -d .venv ]; then "$PYTHON" -m venv .venv; fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --windowed --name PromptFlow \
  --icon assets/promptflow.icns \
  --add-data "assets/promptflow.png:assets" main.py
echo "Application created at dist/PromptFlow.app"
echo "Build architecture: $(python -c 'import platform; print(platform.machine())')"
