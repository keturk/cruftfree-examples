#!/usr/bin/env bash
# Pull the latest cruftfree-examples changes into this clone.
# Thin twin of pull.ps1: the work is done by lib/pull.py.
#
# Usage: pull.sh [--rebase] [--no-summary] [--message-source auto|local|claude]
#        [--local-hosts HOSTS] [--local-model MODEL] [--claude-model MODEL] [--claude-timeout-ms N] [--self-test]
# Exit codes: 0 up to date or updated, 1 stopped (local changes, diverged branch, conflict), 2 git or Python could not run.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        PYTHONIOENCODING=utf-8 exec "$candidate" "$here/lib/pull.py" "$@"
    fi
done
echo "Error: Python 3.11 or newer was not found (tried python3, python)." >&2
exit 2
