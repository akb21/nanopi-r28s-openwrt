#!/usr/bin/env python3
import pathlib
import sys

UBOOT_VERSION = "2026.07"
UBOOT_HASH = "78e8bfc382fe388f9b55aa1daf8c563522a037779b5d4c349d1415e381f1243e"

DEVICE = r'''
define Device/friendlyarm_nanopi-r28s
  $(Device/rk3528)
  DEVICE_VENDOR := FriendlyARM
  DEVICE_MODEL := NanoPi R28S
  DEVICE_DTS := rk3528-nanopi-r28s
  UBOOT_DEVICE_NAME := nanopi-zero2-rk3528
  DEVICE_PACKAGES := kmod-r8169
  SUPPORTED_DEVICES := friendlyarm,nanopi-r28s
endef
TARGET_DEVICES += friendlyarm_nanopi-r28s
'''

UBOOT_TARGET = r'''
define U-Boot/nanopi-zero2-rk3528
  $(U-Boot/rk3528/Default)
  NAME:=NanoPi Zero2 RK3528 (NanoPi R28S test)
  BUILD_DEVICES:= \
    friendlyarm_nanopi-r28s
endef
'''

# OpenWrt 25.12.5 ships its uboot-rockchip patches authored against U-Boot
# 2025.10. U-Boot 2026.07 already carries every change below, so patch(1)
# rejects them with "previously applied (or reversed)" and aborts the package
# build. Verified against the upstream 2026.07 tarball: each entry is either
# entirely upstream or touches only boards this target does not build.
REDUNDANT_UBOOT_PATCHES = (
    "001-spi-rockchip_sfc-Support-sclk_x2-version.patch",
    "002-rockchip-spl-Add-a-read_brom_bootsource_id-helper.patch",
    "004-rockchip-rk3576-Add-SPI-Flash-boot-support.patch",
    "005-board-rockchip-Add-Radxa-ROCK-4D.patch",
    "006-arm64-dts-rockchip-Add-Radxa-ROCK-2A-2F.patch",
    "007-board-rockchip-Add-Radxa-ROCK-2A-2F.patch",
    "008-board-rockchip-add-Lunzn-FastRhino-R66S.patch",
    "009-mmc-rockchip_sdhci-Set-xx_TAP_VALUE-for-RK3528.patch",
    "102-rockchip-Add-initial-RK3582-support.patch",
    "103-rockchip-rk3588-generic-Enable-support-for-RK3582.patch",
    "104-rockchip-rk3588s-rock-5c-Add-support-for-ROCK-5C-Lit.patch",
    "105-1-arm64-dts-rockchip-add-LinkEase-EasePi-R1.patch",
)

# Still applicable to 2026.07; applied by the normal OpenWrt patch step.
KEPT_UBOOT_PATCHES = (
    "003-rockchip-rk3528-Implement-read_brom_bootsource_id.patch",
    "101-nanopc-t4-fix-memory-unstability.patch",
    "105-2-board-rockchip-add-LinkEase-EasePi-R1.patch",
    "107-board-rockchip-add-HINLINK-H28K.patch",
)

def replace_once(s, old, new, label):
    if old not in s:
        raise RuntimeError(f"{label}: expected text not found")
    return s.replace(old, new, 1)

def prune_uboot_patches(ow):
    patch_dir = ow / "package/boot/uboot-rockchip/patches"
    if not patch_dir.is_dir():
        raise RuntimeError(f"uboot-rockchip patch directory not found: {patch_dir}")

    for name in REDUNDANT_UBOOT_PATCHES:
        p = patch_dir / name
        if not p.is_file():
            raise RuntimeError(f"uboot-rockchip patch missing: {name}")
        p.unlink()

    remaining = {p.name for p in patch_dir.iterdir() if p.is_file() and p.suffix == ".patch"}
    if remaining != set(KEPT_UBOOT_PATCHES):
        raise RuntimeError(
            "uboot-rockchip patch set differs from what U-Boot "
            f"{UBOOT_VERSION} expects; kept {sorted(remaining)}, "
            f"expected {sorted(KEPT_UBOOT_PATCHES)}"
        )
    print(f"Pruned {len(REDUNDANT_UBOOT_PATCHES)} U-Boot {UBOOT_VERSION} "
          f"patches already upstream; kept {len(KEPT_UBOOT_PATCHES)}")

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-openwrt.py OPENWRT_DIR")
    ow = pathlib.Path(sys.argv[1]).resolve()

    armv8 = ow / "target/linux/rockchip/image/armv8.mk"
    s = armv8.read_text()
    if "friendlyarm_nanopi-r28s" not in s:
        armv8.write_text(s.rstrip() + "\n\n" + DEVICE)

    ub = ow / "package/boot/uboot-rockchip/Makefile"
    s = ub.read_text()

    s = replace_once(
        s, "PKG_VERSION:=2025.10",
        f"PKG_VERSION:={UBOOT_VERSION}", "U-Boot version"
    )
    s = replace_once(
        s,
        "PKG_HASH:=b4f032848e56cc8f213ad59f9132c084dbbb632bc29176d024e58220e0efdf4a",
        f"PKG_HASH:={UBOOT_HASH}",
        "U-Boot hash",
    )

    if "define U-Boot/nanopi-zero2-rk3528" not in s:
        s = replace_once(
            s,
            "define U-Boot/hinlink-h28k-rk3528",
            UBOOT_TARGET + "\n" + "define U-Boot/hinlink-h28k-rk3528",
            "U-Boot target insertion",
        )

    if "  nanopi-zero2-rk3528 \\" not in s:
        s = replace_once(
            s,
            "  hinlink-h28k-rk3528 \\\n",
            "  hinlink-h28k-rk3528 \\\n  nanopi-zero2-rk3528 \\\n",
            "U-Boot target list",
        )

    ub.write_text(s)

    prune_uboot_patches(ow)

if __name__ == "__main__":
    main()
