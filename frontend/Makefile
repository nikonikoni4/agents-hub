.PHONY: check fix lint format type test clean help

help:
	@echo "Targets:"
	@echo "  make check   - run format + lint + type + test (local CI)"
	@echo "  make fix     - auto-fix format + lint"
	@echo "  make lint    - eslint check"
	@echo "  make format  - prettier auto-fix"
	@echo "  make type    - typescript type check"
	@echo "  make test    - vitest"

check:
	npm run format && npm run lint && npm run type-check && npm run test run

fix:
	npm run format && npm run lint:fix

lint:
	npm run lint

format:
	npm run format

type:
	npm run type-check

test:
	npm run test run

clean:
	rm -rf node_modules/.vite dist coverage
