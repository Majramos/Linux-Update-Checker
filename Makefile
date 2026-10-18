.RECIPEPREFIX := $() $()

.PHONY: install fmt lint style test verify clean notify setup-pre-commit

install:
    uv sync

fmt:
    uv run ruff format .

lint:
    uv run ruff check .

style:
    uv run mypy src tests

test:
    uv run pytest

verify: lint style test

clean:
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type d -name "*.pyc" -delete
    rm -rf .pytest_cache .ruff_cache .mypy_cache

notify:
    uv run --env-file .env linux-update-checker

setup-pre-commit:
    uv run pre-commit install
    uv run pre-commit install --hook-type commit-msg
