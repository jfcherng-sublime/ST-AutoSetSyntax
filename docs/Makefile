.phony: all
all: build

.phony: install
install:
	python -m pip install --upgrade pip
	python -m pip install --upgrade -r requirements.txt

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
