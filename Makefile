.PHONY: install setup-db download-dvf ingest-dvf test lint format clean

install:
	uv sync

setup-db:
	uv run python scripts/setup_db.py

download-dvf:
	uv run python scripts/download_dvf.py

ingest-dvf: download-dvf
	uv run python scripts/ingest_dvf.py

test:
	uv run pytest -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
