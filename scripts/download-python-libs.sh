#!/usr/bin/env bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."

# should matches Sublime Text's Python API environment
PY_IMPLEMENTATION=${PY_IMPLEMENTATION:-"cp"}
PY_VERSION=${PY_VERSION:-"3.14"}

PY_VERSION_NO_DOT=${PY_VERSION//./}

UV="${UV:-uv}"
PIP="${UV} run pip"
REQUIREMENTS_TXT="${SCRIPT_DIR}/requirements.txt"

"${UV}" venv --clear --python="${PY_IMPLEMENTATION}${PY_VERSION_NO_DOT}"

declare -A PIP_PLATFORM_ARCHS=(
    ["linux_arm64"]="manylinux_2_28_aarch64,manylinux2014_aarch64,any"
    ["linux_x64"]="manylinux_2_28_x86_64,manylinux2014_x86_64,any"
    ["osx_arm64"]="macosx_14_0_arm64,macosx_13_0_arm64,macosx_11_0_arm64,macosx_11_0_universal2,any"
    ["osx_x64"]="macosx_13_0_x86_64,macosx_11_0_x86_64,macosx_11_0_universal2,any"
    ["windows_x32"]="win32,any"
    ["windows_x64"]="win_amd64,any"
)

download_for_st_platform_arch() {
    local platform_arch=$1
    local platform_arch_flags=${PIP_PLATFORM_ARCHS[${platform_arch}]}

    echo "[INFO] Collect packages for platform/arch: ${platform_arch}"

    local platform_libs_dir="${PROJECT_DIR}/libs-py${PY_VERSION_NO_DOT}@${platform_arch}"
    rm -rf "${platform_libs_dir}" "${platform_libs_dir}."*
    mkdir -p "${platform_libs_dir}"

    local pip_flags=(
        "--implementation=${PY_IMPLEMENTATION}"
        "--python-version=${PY_VERSION}"
        "--only-binary=:all:"
        "--dest=${platform_libs_dir}"
    )
    for pip_platform in $(tr "," "\n" <<<"${platform_arch_flags}"); do
        pip_flags+=("--platform=${pip_platform}")
    done

    ${PIP} download -r "${REQUIREMENTS_TXT}" "${pip_flags[@]}"
    if ! [ $? -eq 0 ]; then
        echo "[ERROR] Failed to download packages for platform/arch: ${platform_arch}"
        return 1
    fi

    (
        cd "${platform_libs_dir}" || exit 1
        while IFS= read -r -d '' lib; do
            mv "${lib}" "${lib}.zip" # sometimes ".zip" extension is required for "unzip"
            unzip -q "${lib}.zip" && rm -f "${lib}.zip"
        done < <(find . -name "*.whl" -print0)
        "${UV}" pip freeze --path . | tr -d "\r" >"requirements.txt"
        cat "requirements.txt"
        cd ..

        libs_dir=$(basename "${platform_libs_dir}")
        libs_tarball="${libs_dir}.tar.xz"
        XZ_OPT=-e9 tar cJf "${libs_tarball}" "${libs_dir}" && rm -rf "${libs_dir}"
        sha256sum "${libs_tarball}" | awk '{ printf "%s",$1 }' >"${libs_tarball}.sha256"
    )
}

# ensure "uv" is available
if ! command -v "${UV}" &>/dev/null; then
    echo "[ERROR] \"${UV}\" command not found. Please install \"uv\" first."
    exit 1
fi

for st_platform_arch in "${!PIP_PLATFORM_ARCHS[@]}"; do
    if [[ ${PY_VERSION} == "3.14" ]]; then
        if [[ ${st_platform_arch} == "windows_x32" ]] || [[ ${st_platform_arch} == "osx_x64" ]]; then
            echo "[INFO] Skipping ${st_platform_arch} for Python ${PY_VERSION} as it's not supported."
            continue
        fi
    fi
    download_for_st_platform_arch "${st_platform_arch}"
done
