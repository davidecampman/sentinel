#!/bin/bash

# start webapp
cd /usr/local/searxng/searxng-src
export SEARXNG_SETTINGS_PATH="/etc/searxng/settings.yml"

# Apply TLS settings written by Agent Zero (CA bundle / verify mode).
# This file is created/updated by python/helpers/tls.py apply_env_vars().
[ -f /a0/usr/tls.env ] && source /a0/usr/tls.env

# activate venv
source "/usr/local/searxng/searx-pyenv/bin/activate"

exec python /usr/local/searxng/searxng-src/searx/webapp.py
