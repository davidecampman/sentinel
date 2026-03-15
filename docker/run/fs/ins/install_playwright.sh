#!/bin/bash
set -e

# activate venv
. "/ins/setup_venv.sh" "$@"

# install playwright if not installed (should be from requirements.txt)
uv pip install playwright

# set PW installation path to /a0/tmp/playwright
export PLAYWRIGHT_BROWSERS_PATH=/a0/tmp/playwright

# install chromium with dependencies
# libnss3-tools provides certutil, needed to inject custom CA certs into the
# NSS trust store that Chromium reads on Linux.
apt-get install -y fonts-unifont libnss3 libnss3-tools libnspr4 libatk1.0-0 libatspi2.0-0 libxcomposite1 libxdamage1 libatk-bridge2.0-0 libcups2
playwright install chromium --only-shell

# Initialise NSS certificate databases so certutil can add/remove certs at
# runtime without needing to re-run certutil -N interactively.
# /etc/pki/nssdb  – system-wide DB checked by Chromium
# /root/.pki/nssdb – per-user DB for the root account (container default user)
mkdir -p /etc/pki/nssdb /root/.pki/nssdb
# certutil -f requires a non-empty file; a file containing only a newline
# is treated as an empty (blank) password by NSS.
NSS_PASS=$(mktemp)
echo > "$NSS_PASS"
certutil -N -f "$NSS_PASS" -d sql:/etc/pki/nssdb
certutil -N -f "$NSS_PASS" -d sql:/root/.pki/nssdb
rm -f "$NSS_PASS"
