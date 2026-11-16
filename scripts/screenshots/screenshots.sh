#!/usr/bin/env bash
# Capture the UI screenshots of an example from its running local stack.
# Thin twin of screenshots.ps1: the work is done by lib/capture.py.
#
# Usage: screenshots.sh --domain NAME [--site NAME] [--user EMAIL] [--markdown] [--self-test]
# The sign-in password is read from $CRUFTFREE_SCREENSHOT_PASSWORD (the user may also come from
# $CRUFTFREE_SCREENSHOT_USER); $CRUFTFREE_BROWSER_EXE names a browser to use instead of Playwright's.
# Needs Python 3.11+ with playwright and pillow: pip install playwright pillow && playwright install chromium
# Exit codes: 0 captured cleanly, 1 captured with problems, 2 could not run.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys, playwright, PIL; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        PYTHONIOENCODING=utf-8 exec "$candidate" "$here/lib/capture.py" "$@"
    fi
done
echo "Error: no Python 3.11+ with playwright and pillow was found (tried python3, python)." >&2
echo "Install them: pip install playwright pillow && playwright install chromium" >&2
exit 2
