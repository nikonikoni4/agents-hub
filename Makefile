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
	@echo "  make cov     - pytest with coverage report"
	@echo "  make clean   - remove caches"

check:
	$(CONDA) bash -c "set -e; \
	  echo '>>> ruff check'        && ruff check $(PKG) && \
	  echo '>>> ruff format check' && ruff format --check $(PKG) && \
	  echo '>>> mypy'              && mypy && \
	  echo '>>> pytest'            && pytest"

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

cov:
	$(CONDA) pytest --cov=$(PKG) --cov-report=term-missing

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
