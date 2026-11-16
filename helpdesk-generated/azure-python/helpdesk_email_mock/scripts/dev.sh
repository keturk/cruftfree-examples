#!/usr/bin/env bash
# Start development server for helpdesk.EmailMock

set -e
uvicorn main:app --reload --no-proxy-headers
