#!/bin/bash
set -e

echo "====================PYTHON START===================="

echo "====================PYTHON 3.13===================="

apt clean && apt-get update && apt-get -y upgrade

# Ubuntu 25.10 (questing) ships Python 3.13 natively; no PPA needed
# install python 3.13 globally
apt-get install -y --no-install-recommends \
    python3.13 python3.13-venv
    #python3.13-dev


echo "====================PYTHON 3.13 VENV===================="

# create and activate default venv
python3.13 -m venv /opt/venv
source /opt/venv/bin/activate

# upgrade pip and install static packages; CVE-2025-8869 affects pip 24.0, fixed in 25.0+
pip install --no-cache-dir "pip>=25.0" pipx ipython requests

echo "====================PYTHON PYVENV===================="

# Install build dependencies (needed by uv, torch, and other downstream packages).
apt-get install -y --no-install-recommends \
    make build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev \
    libxmlsec1-dev libffi-dev liblzma-dev

# Install Python 3.12 directly from the Ubuntu 25.10 universe repo instead of via pyenv.
#
# pyenv uses #!/usr/bin/env shebang scripts (pyenv init --path, shims, etc.). Under QEMU
# (linux/arm64 buildx cross-compilation) Node.js 22's process-name security check fires
# for any #!/usr/bin/env <name> invocation where the resolved executable path doesn't
# match the requested utility name, exiting with code 1.
# Ubuntu 25.10 ships python3.12 alongside the default python3.13 in the universe repo,
# so we can install it directly without pyenv.
apt-get install -y --no-install-recommends python3.12 python3.12-venv

echo "====================PYTHON 3.12 VENV===================="

python3.12 -m venv /opt/venv-a0
source /opt/venv-a0/bin/activate

# upgrade pip; CVE-2025-8869 affects pip 24.0, fixed in 25.0+
pip install --no-cache-dir "pip>=25.0"

# Install some packages in specific variants
# torch 2.4.0 had CVE-2024-48063 and CVE-2025-32434 (RCE via torch.load); fixed in 2.6.0
pip install --no-cache-dir \
    torch==2.6.0 \
    torchvision==0.21.0 \
    --index-url https://download.pytorch.org/whl/cpu

echo "====================PYTHON UV ===================="

curl -Ls https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh

# clean up pip cache
pip cache purge

# Security: CVE-2026-23949 in jaraco.context <6.1.0 (path traversal via tarball()); fixed in 6.1.0
# Ubuntu 25.10 ships 6.0.1 as a system package; upgrade it with --break-system-packages
# to patch the system Python installation (venv installations are already covered by requirements.txt)
pip3 install --break-system-packages "jaraco.context>=6.1.0"

echo "====================PYTHON END===================="
