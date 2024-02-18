#!/usr/bin/env bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."

PIP="${PIP:-pip}"
REQUIREMENTS_TXT="${SCRIPT_DIR}/requirements.txt"

declare -A PIP_PLATFORM_ARCHS=(
    ["linux_arm64"]="manylinux_2_27_aarch64,manylinux2014_aarch64,any"
    ["linux_x64"]="manylinux_2_27_x86_64,manylinux2014_x86_64,any"
    ["osx_arm64"]="macosx_11_0_arm64,macosx_11_0_universal2,any"
    ["osx_x64"]="macosx_11_0_x86_64,macosx_11_0_universal2,any"
    ["windows_x32"]="win32,any"
    ["windows_x64"]="win_amd64,any"
)

download_for_st_platform_arch() {
    local platform_arch=$1
    local platform_arch_flags=${PIP_PLATFORM_ARCHS[${platform_arch}]}

    echo "[INFO] Collect packages for platform/arch: ${platform_arch}"

    local platform_libs_dir="${PROJECT_DIR}/libs-py38@${platform_arch}"
    rm -rf "${platform_libs_dir}" "${platform_libs_dir}.zip"
    mkdir -p "${platform_libs_dir}"

    local pip_flags=(
        "--dest=${platform_libs_dir}"
        "--implementation=cp"
        "--only-binary=:all:"
        "--python-version=3.8"
    )
    for pip_platform in $(tr "," "\n" <<<"${platform_arch_flags}"); do
        pip_flags+=("--platform=${pip_platform}")
    done

    "${PIP}" download -r "${REQUIREMENTS_TXT}" "${pip_flags[@]}"

    (
        cd "${platform_libs_dir}" || exit 1
        while IFS= read -r -d '' lib; do
            mv "${lib}" "${lib}.zip" # sometime ".zip" extension is required for "unzip"
            unzip -q "${lib}.zip" && rm -f "${lib}.zip"
        done < <(find . -name "*.whl" -print0)
        libs_info=$("${PIP}" list --path . | tr -d "\r")
        echo "${libs_info}"
        cd ..

        libs_dir=$(basename "${platform_libs_dir}")
        zip -9ryqz "${libs_dir}.zip" "${libs_dir}" <<<"${libs_info}" && rm -rf "${libs_dir}"
        md5sum "${libs_dir}.zip" | awk '{ print $1 }' >"${libs_dir}.zip.md5"
    )
}

for st_platform_arch in "${!PIP_PLATFORM_ARCHS[@]}"; do
    download_for_st_platform_arch "${st_platform_arch}"
done
