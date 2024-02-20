.phony: all
all: build

.PHONY: install
install: pip-compile
	uv pip install -r requirements.txt

.PHONY: pip-compile
pip-compile:
	uv pip compile --upgrade requirements.in -o requirements.txt

.phony: serve
serve:
	mkdocs serve

.phony: build
build: clean
	mkdocs build

.phony: deploy
deploy:
	mkdocs gh-deploy --force

.phony: clean
clean:
	rm -rf site/
