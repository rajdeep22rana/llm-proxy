#!/usr/bin/env bash
set -euo pipefail

# Run formatting, linting, and tests with coverage
black .
flake8
pytest --cov=app --cov-report=term-missing
