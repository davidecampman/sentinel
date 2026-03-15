#!/bin/bash
set -e

echo "====================SEARXNG2 START===================="


# clone SearXNG repo
git clone "https://github.com/searxng/searxng" \
                   "/usr/local/searxng/searxng-src"

echo "====================SEARXNG2 VENV===================="

# create virtualenv:
python3.13 -m venv "/usr/local/searxng/searx-pyenv"

# make it default
echo ". /usr/local/searxng/searx-pyenv/bin/activate" \
                   >>  "/usr/local/searxng/.profile"

# activate venv
source "/usr/local/searxng/searx-pyenv/bin/activate"

echo "====================SEARXNG2 INST===================="

# update pip's boilerplate
pip install --no-cache-dir -U pip setuptools wheel pyyaml lxml msgspec typing_extensions

# jump to SearXNG's working tree and install SearXNG into virtualenv
cd "/usr/local/searxng/searxng-src"
# pip install --no-cache-dir --use-pep517 --no-build-isolation -e .
pip install --no-cache-dir --use-pep517 --no-build-isolation .

# Pin patched versions over whatever SearXNG pulled in as transitive deps:
# cryptography 41.x: CVE-2023-50782 (8.7H), CVE-2026-26007 (8.2H), CVE-2024-26130 (7.5H) → fixed in 42.0.4+
# Pillow <12.1.1:     CVE-2026-25990 (8.9H) → fixed in 12.1.1+
# setuptools <78.1.1: CVE-2025-47273 (7.7H) → fixed in 78.1.1+
# PyJWT 2.7.0:        CVE-2026-32597 (7.5H) → fixed in 2.9.0+
pip install --no-cache-dir -U \
    "cryptography>=42.0.4" \
    "Pillow>=12.1.1" \
    "setuptools>=78.1.1" \
    "PyJWT>=2.9.0"

# cleanup cache
pip cache purge

echo "====================SEARXNG2 END===================="