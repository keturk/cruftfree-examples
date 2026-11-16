#!/usr/bin/env bash
# Commit every change in the cruftfree-examples repository and push it.
# Thin twin of commit-and-push.ps1: the work is done by lib/commit_and_push.py.
#
# Usage: commit-and-push.sh [--message TEXT] [--dry-run] [--no-push]
#        [--message-source auto|local|claude] [--local-hosts HOSTS] [--local-model MODEL]
#        [--claude-model MODEL] [--claude-timeout-ms N] [--self-test]
# Exit codes: 0 done or nothing to do, 1 stopped by a check or a rejected push, 2 git or Python could not run.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        PYTHONIOENCODING=utf-8 exec "$candidate" "$here/lib/commit_and_push.py" "$@"
    fi
done
echo "Error: Python 3.11 or newer was not found (tried python3, python)." >&2
exit 2
