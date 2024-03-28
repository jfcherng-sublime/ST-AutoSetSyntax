UV_INSTALL_FLAGS :=

.PHONY: all
all:

.PHONY: install
install: install-dev install-docs

.PHONY: install-dev
install-dev:
	uv pip install $(UV_INSTALL_FLAGS) -r requirements-dev.txt

.PHONY: install-docs
install-docs:
	uv pip install $(UV_INSTALL_FLAGS) -r requirements-docs.txt

.PHONY: pip-compile
pip-compile:
	uv pip compile --upgrade requirements-dev.in -o requirements-dev.txt
	uv pip compile --upgrade requirements-docs.in -o requirements-docs.txt

.PHONY: ci-check
ci-check:
	@echo "========== check: mypy =========="
	mypy -p plugin
	@echo "========== check: ruff (lint) =========="
	ruff check --diff .
	@echo "========== check: ruff (format) =========="
	ruff format --diff .

.PHONY: ci-fix
ci-fix:
	@echo "========== fix: ruff (lint) =========="
	ruff check --fix .
	@echo "========== fix: ruff (format) =========="
	ruff format .

.PHONY: docs-serve
docs-serve:
	cd "docs/" && mkdocs serve

.PHONY: docs-build
docs-build: docs-clean
	cd "docs/" && mkdocs build

.PHONY: docs-deploy
docs-deploy:
	cd "docs/" && mkdocs gh-deploy --force

.PHONY: docs-clean
docs-clean:
	cd "docs/" && rm -rf site/
