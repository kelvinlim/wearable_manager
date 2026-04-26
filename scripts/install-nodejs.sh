#!/usr/bin/env bash
# Install Node.js 24 (npm 11) from the RHEL 9 AppStream module stream.
# Run as: sudo bash scripts/install-nodejs.sh
#
# Uses the `common` profile (runtime + npm). For native-module builds, swap
# to `nodejs:24/development` and add gcc/make/python3.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "must run as root: sudo bash $0" >&2
  exit 1
fi

STREAM=nodejs:24/common

echo "[1/3] Installing $STREAM"
dnf module install -y "$STREAM"

echo "[2/3] Verifying"
node --version
npm --version

echo "[3/3] Done."
