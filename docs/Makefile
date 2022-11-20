.phony: all
all: build

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
