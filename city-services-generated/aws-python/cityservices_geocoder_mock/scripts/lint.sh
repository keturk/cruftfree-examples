#!/usr/bin/env bash
# Lint cityservices.GeocoderMock

set -e
ruff check .
mypy .
