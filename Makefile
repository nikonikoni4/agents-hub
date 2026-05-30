.PHONY: check lint format type test clean help

PKG := agents_hub
TESTS := tests
ENV := agentshub_dev_env
CONDA := conda run -n $(ENV) --no-capture-output

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
	$(CONDA) ruff check $(PKG)
	$(CONDA) ruff format --check $(PKG)

format:
	$(CONDA) ruff format $(PKG)
	$(CONDA) ruff check --fix $(PKG)

type:
	$(CONDA) mypy

test:
	$(CONDA) pytest

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
