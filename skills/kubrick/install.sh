#!/usr/bin/env bash
# Kubrick — Hermes Skill Installer
# Usage:
#   ./install.sh                 # installs to ~/.hermes/skills/kubrick
#   ./install.sh creative        # installs to ~/.hermes/skills/creative/kubrick

set -e

TARGET_BASE="${HOME}/.hermes/skills"
SUBDIR=""

if [[ "$1" == "creative" || "$1" == "categorized" ]]; then
    SUBDIR="creative/"
fi

DEST="${TARGET_BASE}/${SUBDIR}kubrick"

echo "Installing Kubrick to: ${DEST}"
mkdir -p "$(dirname "${DEST}")"

if [ -d "${DEST}" ]; then
    echo "Existing installation found. Backing up to ${DEST}.bak"
    rm -rf "${DEST}.bak"
    mv "${DEST}" "${DEST}.bak"
fi

cp -R . "${DEST}"

# Make scripts executable
chmod +x "${DEST}/scripts/"*.py 2>/dev/null || true

echo ""
echo "✅ Kubrick installed successfully."
echo ""
echo "Location: ${DEST}"
echo ""
echo "Next steps:"
echo "  1. Restart Hermes or reload skills."
echo "  2. Try triggers like: 'develop screenplay', 'kubrick style', 'symbolic narrative'"
echo ""
echo "The skill works completely standalone inside Hermes."
echo "Optional: pair it with the hermes-continuity-forge skill for full production handoff."
