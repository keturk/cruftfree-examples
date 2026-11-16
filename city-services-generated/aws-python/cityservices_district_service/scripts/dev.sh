#!/usr/bin/env bash
# Start development server for cityservices.DistrictService

set -e
uvicorn main:app --reload --no-proxy-headers
