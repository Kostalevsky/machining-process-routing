PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
BACKEND_DIR := backend

.PHONY: install-dev lint format test e2e pre-commit-install up down logs

install-dev:
	cd $(BACKEND_DIR) && $(PIP) install -r requirements.txt

lint:
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff check .

format:
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff check . --fix
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff format .

test:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest

e2e:
	cd $(BACKEND_DIR) && $(PYTHON) scripts/run_e2e_checks.py

pre-commit-install:
	$(PYTHON) -m pre_commit install

up:
	cd $(BACKEND_DIR) && docker-compose up --build -d

down:
	cd $(BACKEND_DIR) && docker-compose down

logs:
	cd $(BACKEND_DIR) && docker-compose logs -f api
