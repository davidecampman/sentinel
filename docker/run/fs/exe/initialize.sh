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

# Restore custom CA certificate into all system trust stores.
# tls.env is written by apply_env_vars() when TLS settings are saved; SSL_CERT_FILE
# holds the path to the user-configured CA bundle.  Installing it here ensures
# every TLS-speaking component — Python (ssl.create_default_context), aiohttp,
# botocore/Bedrock, and Chromium/Playwright (NSS) — trusts the corporate CA
# from the very first connection, before the Python app calls apply_env_vars().
if [ -f /a0/usr/tls.env ]; then
    CERT_PATH=$(grep '^export SSL_CERT_FILE=' /a0/usr/tls.env | cut -d= -f2-)
    if [ -n "$CERT_PATH" ] && [ -f "$CERT_PATH" ]; then
        # 1. OpenSSL system trust store (Python ssl, requests, httpx, botocore…)
        cp "$CERT_PATH" /usr/local/share/ca-certificates/sentinel-ca.crt
        update-ca-certificates 2>/dev/null || true

        # 2. NSS trust store (Chromium / Playwright on Linux)
        for NSS_DB in sql:/etc/pki/nssdb sql:/root/.pki/nssdb; do
            DB_DIR="${NSS_DB#sql:}"
            if [ -d "$DB_DIR" ]; then
                certutil -D -d "$NSS_DB" -n "sentinel-ca" 2>/dev/null || true
                certutil -A -d "$NSS_DB" -n "sentinel-ca" -t "CT,," -i "$CERT_PATH" 2>/dev/null || true
            fi
        done

        echo "Custom CA certificate installed from $CERT_PATH"
    fi
fi

# update package list to save time later
apt-get update > /dev/null 2>&1 &

# let supervisord handle the services
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
