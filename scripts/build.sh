#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${ROOT}/.work"
OW="${WORK}/openwrt"
OUT="${ROOT}/output"
TAG="v25.12.5"

mkdir -p "${WORK}" "${OUT}"

if [[ ! -d "${OW}/.git" ]]; then
  rm -rf "${OW}"
  git clone --depth 1 --branch "${TAG}" https://github.com/openwrt/openwrt.git "${OW}"
fi

python3 "${ROOT}/scripts/import-r28s-dts.py" "${OW}"
python3 "${ROOT}/scripts/patch-openwrt.py" "${OW}"

cp "${ROOT}/config/r28s.config" "${OW}/.config"

cd "${OW}"
make defconfig
make download -j"$(nproc)"
make -j"$(nproc)" V=s

rm -rf "${OUT:?}"/*
find bin/targets/rockchip/armv8 -maxdepth 1 -type f -print0 |
while IFS= read -r -d '' f; do
  cp -v "$f" "${OUT}/"
done

shopt -s nullglob
sq=( "${OUT}"/*friendlyarm_nanopi-r28s-squashfs-sysupgrade.img.gz )
ex=( "${OUT}"/*friendlyarm_nanopi-r28s-ext4-sysupgrade.img.gz )

if (( ${#sq[@]} != 1 )); then
  echo "ERROR: squashfs sysupgrade image was not produced" >&2
  exit 2
fi
if (( ${#ex[@]} != 1 )); then
  echo "ERROR: ext4 sysupgrade image was not produced" >&2
  exit 2
fi

echo
echo "Build complete:"
printf '  %s\n' "${sq[0]}" "${ex[0]}"
