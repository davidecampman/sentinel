#!/usr/bin/env bash
# Run Agent Zero Corporate Edition security test suite
# Uses the system python with lightweight conftest stubs

set -e
COLOR_GREEN="\033[0;32m"
COLOR_RED="\033[0;31m"
COLOR_RESET="\033[0m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${COLOR_GREEN}Running Agent Zero security tests...${COLOR_RESET}"

python -m pytest \
    tests/test_tls_helper.py \
    tests/test_fasta2a_client.py \
    -v "$@"

echo -e "${COLOR_GREEN}All Agent Zero security tests passed!${COLOR_RESET}"
