.PHONY: all
all:

.PHONY: download
download: download-py38 download-py314

.PHONY: download-py38
download-py38:
	bash scripts/download-python-libs-py38.sh

.PHONY: download-py314
download-py314:
	bash scripts/download-python-libs-py314.sh
