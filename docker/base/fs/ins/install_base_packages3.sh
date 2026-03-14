#!/bin/bash
set -e

echo "====================BASE PACKAGES3 START===================="

# Use NodeSource to install the latest Node.js 22.x LTS instead of the potentially
# outdated distro package. This fixes CVEs in Node 22.14.0 (CVE-2025-55130,
# CVE-2025-59465/59466, CVE-2025-23166, CVE-2026-21637, CVE-2025-55131) and ensures
# bundled packages (undici, tar, minimatch, etc.) are at patched versions.
apt-get install -y --no-install-recommends ca-certificates curl gnupg
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y --no-install-recommends nodejs

echo "====================BASE PACKAGES3 NPM===================="

# Update npm to latest to pick up fixes for bundled deps:
# tar (CVE-2026-23950/24842/29786/23745/31802/26960), minimatch (CVE-2026-26996/27903/27904),
# @babel/traverse (CVE-2023-45133), flatted (CVE-2026-32141), glob (CVE-2025-64756),
# http-cache-semantics (CVE-2022-25881), serialize-javascript (GHSA-5c6j-r48x-rmvq)
npm install -g npm@latest

# we shall not install npx separately, it's discontinued and some versions are broken
# npm i -g npx
echo "====================BASE PACKAGES3 END===================="
