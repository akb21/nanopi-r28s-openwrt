#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${ROOT}/.work"
OW="${WORK}/openwrt"
OUT="${ROOT}/output"
TAG="v25.12.5"

mkdir -p "${WORK}" "${OUT}"

# Build state that a warm CI cache may have restored. It must survive the
# re-clone below, otherwise every run would throw away the host tools, the
# cross toolchain and the feed checkouts and rebuild or re-download them.
# The workflow caches staging_dir/{host,toolchain-*}, build_dir/{host,toolchain-*}
# and feeds/; dl/ is not cached but is cheap to keep locally.
CACHED_BUILD_STATE=(staging_dir build_dir dl feeds)

reclone_openwrt() {
  local stash="${WORK}/.stash" d
  rm -rf "${stash}"
  mkdir -p "${stash}"
  for d in "${CACHED_BUILD_STATE[@]}"; do
    if [[ -e "${OW}/${d}" ]]; then
      mkdir -p "${stash}/$(dirname "${d}")"
      mv "${OW}/${d}" "${stash}/${d}"
    fi
  done
  rm -rf "${OW}"
  git clone --depth 1 --branch "${TAG}" https://github.com/openwrt/openwrt.git "${OW}"
  for d in "${CACHED_BUILD_STATE[@]}"; do
    if [[ -e "${stash}/${d}" ]]; then
      mkdir -p "${OW}/$(dirname "${d}")"
      mv "${stash}/${d}" "${OW}/${d}"
    fi
  done
  rm -rf "${stash}"
}

if [[ ! -d "${OW}/.git" ]]; then
  reclone_openwrt
fi

python3 "${ROOT}/scripts/import-r28s-dts.py" "${OW}"
python3 "${ROOT}/scripts/patch-openwrt.py" "${OW}"

cd "${OW}"

# LuCI and most userland packages live in feeds, not in the OpenWrt tree, and
# the feeds are not fetched by the clone. Without this step nothing from the
# luci/packages/routing/telephony feeds can be selected, so the image gets no
# LuCI at all. scripts/feeds is also what installs feeds/<name>.index, which in
# turn gives the generated FEED_<name> symbols their `default y` and is what
# makes /etc/apk/repositories.d/distfeeds.list list the per-feed entries instead
# of just core and base.
./scripts/feeds update -a
./scripts/feeds install -a

cp "${ROOT}/config/r28s.config" "${OW}/.config"

# rules.mk derives CCACHE_DIR from CONFIG_CCACHE_DIR and exports it, so an
# environment variable alone is not enough. Point it at a caller-chosen path
# (outside .work/openwrt/) when one is given.
if [[ -n "${CCACHE_DIR:-}" ]]; then
  if ! command -v ccache >/dev/null 2>&1; then
    echo "ERROR: CCACHE_DIR is set but ccache is not installed" >&2
    exit 2
  fi
  printf 'CONFIG_CCACHE_DIR="%s"\n' "${CCACHE_DIR}" >> "${OW}/.config"
fi

make defconfig
make download -j"$(nproc)"
make -j"$(nproc)" V=s

# The only deliverable is the flashable SD-card image. The rockchip target also
# emits kernel, rootfs tarballs, profiles.json, buildinfo and sha256sums, but
# those are build plumbing, not something you write to a card.
shopt -s nullglob
sq=( bin/targets/rockchip/armv8/*friendlyarm_nanopi-r28s-squashfs-sysupgrade.img.gz )
ex=( bin/targets/rockchip/armv8/*friendlyarm_nanopi-r28s-ext4-sysupgrade.img.gz )

if (( ${#sq[@]} != 1 )); then
  echo "ERROR: squashfs sysupgrade image was not produced" >&2
  exit 2
fi
if (( ${#ex[@]} != 1 )); then
  echo "ERROR: ext4 sysupgrade image was not produced" >&2
  exit 2
fi

rm -rf "${OUT:?}"/*
cp -v "${sq[@]}" "${ex[@]}" "${OUT}/"

echo
echo "Build complete:"
printf '  %s\n' "${OUT}/${sq[0]##*/}" "${OUT}/${ex[0]##*/}"
