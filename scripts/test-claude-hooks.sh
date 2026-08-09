#!/usr/bin/env bash
# Project-owned compatibility runner for the protected Claude hook harness.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="$PROJECT_ROOT/.claude/hooks/tests"
RUNNER="$TEST_DIR/run-tests.sh"

grep -Fq "out = proc.stdout.decode('utf-8', 'replace')" "$RUNNER" || {
    echo "Claude hook runner contract changed; compatibility patch not applied." >&2
    exit 2
}

sed \
    -e "s|^SCRIPT_DIR=.*|SCRIPT_DIR=\"$TEST_DIR\"|" \
    -e "s/out = proc.stdout.decode('utf-8', 'replace')/out = (proc.stdout + proc.stderr).decode('utf-8', 'replace')/" \
    "$RUNNER" | bash
