PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

.PHONY: install-dev lint format test e2e pre-commit-install up down logs

install-dev:
	$(PIP) install -r requirements.txt

lint:
	docker-compose exec -T api ruff check .

format:
	docker-compose exec -T api ruff check . --fix
	docker-compose exec -T api ruff format .

test:
	docker-compose exec -T api pytest -q

e2e:
	$(PYTHON) scripts/run_e2e_checks.py

pre-commit-install:
	$(PYTHON) -m pre_commit install

up:
	docker-compose up --build -d

down:
	docker-compose down

logs:
	docker-compose logs -f api
