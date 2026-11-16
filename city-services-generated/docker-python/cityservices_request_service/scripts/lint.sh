#!/usr/bin/env bash
# Lint cityservices.RequestService

set -e
ruff check .
mypy .
