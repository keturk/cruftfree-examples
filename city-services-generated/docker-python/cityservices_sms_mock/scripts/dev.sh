#!/usr/bin/env bash
# Start development server for cityservices.SmsMock

set -e
uvicorn main:app --reload --no-proxy-headers
