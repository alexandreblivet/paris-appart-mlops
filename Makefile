.PHONY: install setup-db test lint format clean

install:
	uv sync

setup-db:
	uv run python scripts/setup_db.py

test:
	uv run pytest -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
