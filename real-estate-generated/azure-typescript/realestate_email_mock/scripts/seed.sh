#!/usr/bin/env bash
# Load seed data for realestate.EmailMock

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
node dist/persistence/seed-runner.js "$@"
