#!/usr/bin/env bash
# Lint helpdesk.KnowledgeService

set -e
ruff check .
mypy .
