#!/usr/bin/env bash
# Start development server for cityservices.FacilityService

set -e
uvicorn main:app --reload --no-proxy-headers
