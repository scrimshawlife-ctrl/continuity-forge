#!/usr/bin/env bash
# Profile-aware embedded Kubrick installer. Plan by default; --apply installs.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "${PYTHON:-python3}" "${SCRIPT_DIR}/scripts/install_skill.py" "$@"
