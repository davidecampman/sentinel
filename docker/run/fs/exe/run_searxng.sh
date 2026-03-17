#!/bin/bash

# start webapp
cd /usr/local/searxng/searxng-src
export SEARXNG_SETTINGS_PATH="/etc/searxng/settings.yml"

# Apply TLS settings written by Agent Zero (CA bundle / verify mode).
# This file is created/updated by python/helpers/tls.py apply_env_vars().
[ -f /a0/usr/tls.env ] && source /a0/usr/tls.env

# activate venv
source "/usr/local/searxng/searx-pyenv/bin/activate"

# When TLS verification is disabled (A0_TLS_VERIFY=0), prepend the directory
# containing our sitecustomize.py to PYTHONPATH.  Python automatically imports
# sitecustomize at startup (before any user code), which patches ssl so that
# all new SSL contexts skip certificate verification.
if [ -d /a0/usr/searxng_site ] && [ "$A0_TLS_VERIFY" = "0" ]; then
    export PYTHONPATH="/a0/usr/searxng_site${PYTHONPATH:+:$PYTHONPATH}"
fi

exec python /usr/local/searxng/searxng-src/searx/webapp.py
