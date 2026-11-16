#!/usr/bin/env bash
# Start development server for cityservices.GeocoderMock

set -e
uvicorn main:app --reload --no-proxy-headers
