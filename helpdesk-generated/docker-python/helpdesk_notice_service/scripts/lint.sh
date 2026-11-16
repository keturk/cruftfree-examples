#!/usr/bin/env bash
# Lint helpdesk.NoticeService

set -e
ruff check .
mypy .
