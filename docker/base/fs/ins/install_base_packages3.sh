#!/bin/bash
set -e

echo "====================BASE PACKAGES3 START===================="

# Use NodeSource to install the latest Node.js 22.x LTS instead of the potentially
# outdated distro package. This fixes CVEs in Node 22.14.0 (CVE-2025-55130,
# CVE-2025-59465/59466, CVE-2025-23166, CVE-2026-21637, CVE-2025-55131) and ensures
# bundled packages (undici, tar, minimatch, etc.) are at patched versions.
#
# We use the 'nodistro' target instead of the auto-detect setup_22.x script because
# Ubuntu 25.10 (Questing Quokka) is not yet recognised by the NodeSource distro
# detection logic, causing the setup script to exit with code 1 (especially under
# QEMU for the linux/arm64 build).
NODE_MAJOR=22
apt-get install -y --no-install-recommends ca-certificates curl gnupg
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
    | tee /etc/apt/sources.list.d/nodesource.list
apt-get update
apt-get install -y --no-install-recommends nodejs

echo "====================BASE PACKAGES3 NPM===================="

# NOTE: do NOT run 'npm install -g npm@latest' or 'npm update -g' here.
# Node.js 22 has a security check that validates the shebang utility name matches
# the executable name. Under QEMU (linux/arm64 cross-build) this check fails for
# npm's #!/usr/bin/env node shebang, producing:
#   "Security violation: Requested utility `env` does not match executable name"
# Node 22.22.1 already ships with a sufficiently recent npm (10.x) that includes
# all relevant CVE fixes, so the extra update step is not needed.
echo "====================BASE PACKAGES3 END===================="
