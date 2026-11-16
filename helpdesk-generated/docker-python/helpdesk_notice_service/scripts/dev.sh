#!/usr/bin/env bash
# Start development server for helpdesk.NoticeService

set -e
uvicorn main:app --reload --no-proxy-headers
