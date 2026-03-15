#!/bin/bash

echo "Running initialization script..."

# branch from parameter
if [ -z "$1" ]; then
    echo "Error: Branch parameter is empty. Please provide a valid branch name."
    exit 1
fi
BRANCH="$1"

# Copy all contents from persistent /per to root directory (/) without overwriting
cp -r --no-preserve=ownership,mode /per/* /

# allow execution of /root/.bashrc and /root/.profile
chmod 444 /root/.bashrc
chmod 444 /root/.profile

# Restore custom CA certificate into the system trust store.
# tls.env is written by apply_env_vars() when TLS settings are saved; SSL_CERT_FILE
# holds the path to the user-configured CA bundle.  Installing it here ensures
# ssl.create_default_context() — used by aiohttp, botocore/Bedrock, and others —
# trusts the corporate CA from the very first connection, before the Python app
# has had a chance to call apply_env_vars() itself.
if [ -f /a0/usr/tls.env ]; then
    CERT_PATH=$(grep '^export SSL_CERT_FILE=' /a0/usr/tls.env | cut -d= -f2-)
    if [ -n "$CERT_PATH" ] && [ -f "$CERT_PATH" ]; then
        cp "$CERT_PATH" /usr/local/share/ca-certificates/sentinel-ca.crt
        update-ca-certificates 2>/dev/null || true
        echo "Custom CA certificate installed from $CERT_PATH"
    fi
fi

# update package list to save time later
apt-get update > /dev/null 2>&1 &

# let supervisord handle the services
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
