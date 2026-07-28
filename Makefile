.PHONY: setup up down migrate seed test lint format logs clean

setup:
	@test -f .env || cp .env.example .env
	npm install
	python -m pip install -e packages/config/python -e "apps/api[dev]" -e "apps/worker[dev]"

up:
	docker compose up --build

down:
	docker compose down

migrate:
	docker compose run --rm api alembic upgrade head

seed:
	@echo "Seed data will be introduced with the first domain models in Phase 2."

test:
	python -m pytest apps/api/tests apps/worker/tests packages/config/python/tests
	npm test

lint:
	python -m ruff check apps/api apps/worker packages/config/python
	npm run lint
	npm run typecheck

format:
	python -m ruff format apps/api apps/worker packages/config/python
	npm run format --workspace=@geoflow/web

logs:
	docker compose logs -f

clean:
	docker compose down --remove-orphans

