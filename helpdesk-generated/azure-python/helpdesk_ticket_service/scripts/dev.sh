#!/usr/bin/env bash
# Start development server for helpdesk.TicketService

set -e
uvicorn main:app --reload --no-proxy-headers
