#!/usr/bin/env bash
# Lint helpdesk.EmailMock

set -e
ruff check .
mypy .
