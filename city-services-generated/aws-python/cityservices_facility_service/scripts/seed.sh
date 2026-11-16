#!/usr/bin/env bash
# Load seed data for cityservices.FacilityService

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
python -m cityservices_facility_service.persistence.seed_runner "$@"
