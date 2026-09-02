.PHONY: up down logs test test-unit test-integration test-external test-web e2e lint contracts contracts-check

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api worker web

test: lint contracts-check test-unit test-web

test-unit:
	.venv/bin/python -m pytest -q apps/api/tests/unit

test-integration:
	docker compose --profile test run --rm integration-test

test-external:
	.venv/bin/python -m pytest -q -m external tests/integration/test_external_qwen.py

test-web:
	cd apps/web && npm test && npm run build

e2e:
	cd apps/web && npm run e2e

lint:
	.venv/bin/ruff check apps/api scripts tests
	.venv/bin/python -m mypy apps/api/camcat

contracts:
	PYTHONPATH=apps/api .venv/bin/python scripts/generate_openapi_contracts.py

contracts-check:
	PYTHONPATH=apps/api .venv/bin/python scripts/generate_openapi_contracts.py --check
