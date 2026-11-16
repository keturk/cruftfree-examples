#!/usr/bin/env bash
# Lint cityservices.SmsMock

set -e
ruff check .
mypy .
