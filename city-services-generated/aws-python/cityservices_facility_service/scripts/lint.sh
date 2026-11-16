#!/usr/bin/env bash
# Lint cityservices.FacilityService

set -e
ruff check .
mypy .
