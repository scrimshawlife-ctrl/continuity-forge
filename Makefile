.PHONY: install validate test lint format typecheck

install:
	python -m pip install -e '.[dev]'

validate:
	python scripts/validate_m0.py

test:
	python -m pytest

lint:
	python -m ruff check .

format:
	python -m ruff format --check .

typecheck:
	python -m mypy packages apps scripts
