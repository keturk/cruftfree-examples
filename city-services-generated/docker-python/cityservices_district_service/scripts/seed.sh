#!/usr/bin/env bash
# Load seed data for cityservices.DistrictService

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
python -m cityservices_district_service.persistence.seed_runner "$@"
