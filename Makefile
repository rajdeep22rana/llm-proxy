.PHONY: test-lint test lint fmt

# Run formatting, linting, and tests with coverage
test-lint: fmt lint test

# Auto-format code
fmt:
	black .

# Lint code
lint:
	flake8

# Run tests with coverage
test:
	pytest --cov=app --cov-report=term-missing
