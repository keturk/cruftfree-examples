#!/usr/bin/env bash
# Start development server for cityservices.RequestService

set -e
uvicorn main:app --reload --no-proxy-headers
