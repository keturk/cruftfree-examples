#!/usr/bin/env bash
# Lint helpdesk.TicketService

set -e
ruff check .
mypy .
