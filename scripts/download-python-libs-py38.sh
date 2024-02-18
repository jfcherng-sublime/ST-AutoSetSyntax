#!/usr/bin/env bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

pushd "${SCRIPT_DIR}" || exit 1

PY_VERSION=3.8 ./download-python-libs.sh

popd || exit 1
