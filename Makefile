.PHONY: setup up down migrate seed test lint format logs clean

setup:
	@test -f .env || cp .env.example .env
	npm install
	python -m pip install -e packages/config/python -e "apps/api[dev]" -e "apps/worker[dev]"

up:
	@docker compose --progress quiet up --detach --build --quiet-pull --wait
	@echo ""
	@echo "GeoFlow is running:"
	@echo "  Web app:   http://localhost:3000"
	@echo "  API docs:  http://localhost:8000/docs"
	@echo "  API health: http://localhost:8000/api/v1/health/ready"
	@echo ""
	@echo "Run 'make logs' to view service logs."

down:
	docker compose down

migrate:
	docker compose run --rm api alembic upgrade head

seed:
	@echo "Phase 2 requires no seed data; create users through the registration page."

test:
	docker compose run --rm --no-deps api python -m pytest tests /workspace/packages/config/python/tests
	docker compose run --rm --no-deps worker python -m pytest tests
	docker compose run --rm --no-deps web npm test

lint:
	docker compose run --rm --no-deps api python -m ruff check /workspace/apps/api /workspace/packages/config/python
	docker compose run --rm --no-deps worker python -m ruff check /workspace/apps/worker
	docker compose run --rm --no-deps web npm run lint
	docker compose run --rm --no-deps web npm run typecheck

format:
	docker compose run --rm --no-deps api python -m ruff format /workspace/apps/api /workspace/packages/config/python
	docker compose run --rm --no-deps worker python -m ruff format /workspace/apps/worker
	docker compose run --rm --no-deps web npm run format

logs:
	docker compose logs -f

clean:
	docker compose down --remove-orphans
