#!/usr/bin/env bash
# Load seed data for helpdesk.KnowledgeService

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
python -m helpdesk_knowledge_service.persistence.seed_runner "$@"
