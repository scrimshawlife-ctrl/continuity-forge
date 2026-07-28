.PHONY: install install-prod validate validate-repo test lint format typecheck coverage-floors proof ui mcp

install:
	python -m pip install -e '.[dev]'

install-prod:
	python -m pip install -e '.[production]'

# Fast/local merge gate (ruff + mypy + pytest + critical coverage floors)
validate:
	python scripts/validate_m0.py

# Durable Phase 2+ gate (same suite; explicit name for production CI docs)
validate-repo:
	python scripts/validate_repo.py

# Per-path critical coverage floors only (requires prior pytest --cov / .coverage)
coverage-floors:
	python scripts/validate_repo.py --floors-only

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
