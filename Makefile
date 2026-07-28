.PHONY: install validate test lint format typecheck proof

install:
	python -m pip install -e '.[dev]'

validate:
	python scripts/validate_m0.py

proof:
	python -m continuity_forge_compiler.cli proof tests/golden/fixtures/continuity.fountain --out out

test:
	python -m pytest

lint:
	python -m ruff check .

format:
	python -m ruff format --check .

typecheck:
	python -m mypy packages apps scripts
