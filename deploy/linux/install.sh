#!/usr/bin/env bash
# Bare-metal Continuity Forge install helper (Debian/Ubuntu-oriented).
# Run as root. Idempotent where practical.
#
# Usage:
#   sudo bash deploy/linux/install.sh
#   sudo CF_REPO=/path/to/clone bash deploy/linux/install.sh
#
# Does NOT install Postgres/MinIO/Temporal packages by default — see docs/LINUX.md.

set -euo pipefail

CF_REPO="${CF_REPO:-/opt/continuity-forge}"
CF_USER="${CF_USER:-continuity-forge}"
CF_DATA="${CF_DATA:-/var/lib/continuity-forge}"
CF_ETC="${CF_ETC:-/etc/continuity-forge}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

echo "==> Continuity Forge bare-metal install"
echo "    repo:  ${CF_REPO}"
echo "    user:  ${CF_USER}"
echo "    data:  ${CF_DATA}"
echo "    etc:   ${CF_ETC}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "ERROR: ${PYTHON_BIN} not found. Install Python 3.12+ first." >&2
  echo "  Debian/Ubuntu: sudo apt install python3.12 python3.12-venv python3-pip git" >&2
  exit 1
fi

if [[ ! -d "${CF_REPO}" ]]; then
  echo "ERROR: ${CF_REPO} does not exist." >&2
  echo "  Clone the repo first, e.g.:" >&2
  echo "    sudo git clone https://github.com/scrimshawlife-ctrl/continuity-forge.git ${CF_REPO}" >&2
  exit 1
fi

if ! id -u "${CF_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${CF_DATA}" --shell /usr/sbin/nologin "${CF_USER}"
  echo "    created system user ${CF_USER}"
fi

install -d -o "${CF_USER}" -g "${CF_USER}" -m 0750 "${CF_DATA}"
install -d -o root -g "${CF_USER}" -m 0750 "${CF_ETC}"

if [[ ! -f "${CF_ETC}/continuity-forge.env" ]]; then
  install -o root -g "${CF_USER}" -m 0640 \
    "${CF_REPO}/deploy/linux/continuity-forge.env.example" \
    "${CF_ETC}/continuity-forge.env"
  # Point store root at CF_DATA if still default
  if grep -q '^CF_STORE_ROOT=' "${CF_ETC}/continuity-forge.env"; then
    sed -i "s|^CF_STORE_ROOT=.*|CF_STORE_ROOT=${CF_DATA}|" "${CF_ETC}/continuity-forge.env"
  fi
  echo "    wrote ${CF_ETC}/continuity-forge.env — EDIT SECRETS before enabling auth"
else
  echo "    keeping existing ${CF_ETC}/continuity-forge.env"
fi

echo "==> Virtualenv + package install"
if [[ ! -x "${CF_REPO}/.venv/bin/python" ]]; then
  sudo -u "${CF_USER}" "${PYTHON_BIN}" -m venv "${CF_REPO}/.venv"
fi
# shellcheck disable=SC1091
source "${CF_REPO}/.venv/bin/activate"
python -m pip install -U pip
# Owner of tree should be continuity-forge for venv writes
chown -R "${CF_USER}:${CF_USER}" "${CF_REPO}/.venv" || true
sudo -u "${CF_USER}" bash -c "
  source '${CF_REPO}/.venv/bin/activate'
  cd '${CF_REPO}'
  python -m pip install -e '.[dev]'
"

echo "==> systemd units"
install -m 0644 "${CF_REPO}/deploy/linux/continuity-forge-api.service" \
  /etc/systemd/system/continuity-forge-api.service
install -m 0644 "${CF_REPO}/deploy/linux/continuity-forge-worker.service" \
  /etc/systemd/system/continuity-forge-worker.service
systemctl daemon-reload

echo "==> Done (service not started automatically)"
echo
echo "Next:"
echo "  1. Edit env:  sudo nano ${CF_ETC}/continuity-forge.env"
echo "  2. Validate:  sudo -u ${CF_USER} ${CF_REPO}/.venv/bin/python ${CF_REPO}/scripts/validate_m0.py"
echo "  3. Start API: sudo systemctl enable --now continuity-forge-api"
echo "  4. Health:    curl -s http://127.0.0.1:8080/health"
echo "  5. UI:        http://127.0.0.1:8080/"
echo
echo "Optional Temporal worker (needs Temporal host + .[production]):"
echo "  sudo systemctl enable --now continuity-forge-worker"
echo
echo "Full guide: ${CF_REPO}/docs/LINUX.md"
