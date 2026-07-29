.PHONY: install install-prod validate validate-repo test lint format typecheck coverage-floors proof handoff connector-smoke ui mcp breakdown

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

# Handoff path: paste/import → shot breakdown + continuity (kernel + API + CLI)
handoff:
	python scripts/handoff_harness.py

breakdown:
	python -m continuity_forge_compiler.cli breakdown tests/golden/fixtures/continuity.fountain --out out

# Live API connector smoke (server must be running: make ui)
connector-smoke:
	bash scripts/connector_smoke.sh

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
