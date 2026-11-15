check:
	uv run ruff check src/ bin/
	uv run ruff format --check src/ bin/

test:
	uv run pytest tests/ -q

migrate:
	uv run alembic upgrade head

migrate-create:
	uv run alembic revision --autogenerate -m "$(name)"

run:
	uv run python -m bin.api
