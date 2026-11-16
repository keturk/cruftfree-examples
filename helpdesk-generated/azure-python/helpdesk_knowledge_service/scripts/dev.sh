#!/usr/bin/env bash
# Start development server for helpdesk.KnowledgeService

set -e
uvicorn main:app --reload --no-proxy-headers
