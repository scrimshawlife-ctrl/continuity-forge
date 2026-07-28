.PHONY: install install-prod validate test lint format typecheck proof ui mcp

install:
	python -m pip install -e '.[dev]'

install-prod:
	python -m pip install -e '.[production]'

validate:
	python scripts/validate_m0.py

proof:
	python -m continuity_forge_compiler.cli proof tests/golden/fixtures/continuity.fountain --out out

ui:
	uvicorn continuity_forge_api.main:app --reload --port 8080

mcp:
	continuity-forge-mcp

test:
	python -m pytest

lint:
	python -m ruff check .

format:
	python -m ruff format --check .

typecheck:
	python -m mypy packages apps scripts
