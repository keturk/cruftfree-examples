#!/usr/bin/env bash
# Lint cityservices.DistrictService

set -e
ruff check .
mypy .
