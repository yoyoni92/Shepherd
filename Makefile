SVC ?= libs
NAME ?=

.DEFAULT_GOAL := help

help:  ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

install:  ## install one package  (make install SVC=services/fleet-api)
	cd $(SVC) && poetry env use python3.12 >/dev/null 2>&1 || true
	cd $(SVC) && poetry install

test:  ## unit tests (fast, mocked) for one package  (make test SVC=services/fleet-api)
	cd $(SVC) && poetry run pytest -q

test-watch:  ## TDD watch loop for one package
	cd $(SVC) && poetry run ptw -- -q

lint:  ## ruff lint the whole repo (no install needed, via uvx)
	uvx ruff check .

fmt:  ## ruff format the whole repo
	uvx ruff format .

typecheck:  ## mypy one package
	cd $(SVC) && poetry run mypy .

up:  ## start the stack (build)
	docker compose up -d --build

down:  ## stop the stack
	docker compose down

logs:  ## tail compose logs
	docker compose logs -f

e2e:  ## cross-service e2e smoke (requires the stack up)
	cd tests/e2e && poetry run pytest -q

new-service:  ## scaffold a python service  (make new-service NAME=fleet-api)
	bash scripts/new_service.sh $(NAME)
