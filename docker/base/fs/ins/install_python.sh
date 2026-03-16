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

# Build Python 3.12.4 from source.
#
# python3.12 is NOT in the Ubuntu 25.10 (questing) repos — the distro ships only 3.13.
# pyenv was the previous approach, but its scripts use #!/usr/bin/env shebangs that
# trigger a Node.js 22 security check under QEMU arm64 cross-compilation.
# Building from source uses only standard UNIX tools (wget, ./configure, make) which
# have no such shebang issues.
# --enable-optimizations is intentionally omitted: it runs the full test suite via
# QEMU which is extremely slow and unreliable in a cross-build environment.
PYTHON_VERSION=3.12.4
mkdir -p /tmp/python-src
cd /tmp/python-src
wget -q "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
tar xzf "Python-${PYTHON_VERSION}.tgz"
cd "Python-${PYTHON_VERSION}"
./configure \
    --prefix=/usr/local \
    --enable-shared \
    --with-ensurepip=install \
    LDFLAGS="-Wl,-rpath /usr/local/lib"
make -j"$(nproc)"
make altinstall
cd /
rm -rf /tmp/python-src

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
