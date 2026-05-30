.PHONY: check lint format type test clean help

PKG := agents_hub
TESTS := tests

help:
	@echo "Targets:"
	@echo "  make check   - run lint + type + test (local CI)"
	@echo "  make lint    - ruff check + format check"
	@echo "  make format  - ruff format + ruff --fix (auto-fix)"
	@echo "  make type    - mypy type check"
	@echo "  make test    - pytest"
	@echo "  make clean   - remove caches"

check: lint type test

lint:
	ruff check $(PKG)
	ruff format --check $(PKG)

format:
	ruff format $(PKG)
	ruff check --fix $(PKG)

type:
	mypy

test:
	pytest

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
