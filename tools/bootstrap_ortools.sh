#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
venv="$root/.tools/ortools-venv"
python="${PYTHON:-python3}"

target="$("$python" - <<'PY'
import platform
import sys

print(
    f"{sys.version_info.major}.{sys.version_info.minor} "
    f"{platform.system()} {platform.machine()}"
)
PY
)"

case "$target" in
  "3.9 Darwin arm64")
    lock="$root/tools/ortools-requirements.lock"
    ;;
  "3.11 Linux x86_64")
    lock="$root/tools/ortools-ci-requirements.lock"
    ;;
  *)
    printf 'unsupported OR-Tools lock target: %s\n' "$target" >&2
    exit 2
    ;;
esac

"$python" -m venv "$venv"
"$venv/bin/python" -m pip install \
  --require-hashes \
  --no-deps \
  -r "$lock"
