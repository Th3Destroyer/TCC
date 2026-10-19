#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/workspace/.cache/pip}"
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py bootstrap_desk
.venv/bin/python manage.py check
