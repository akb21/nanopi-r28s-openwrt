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

def replace_once(s, old, new, label):
    if old not in s:
        raise RuntimeError(f"{label}: expected text not found")
    return s.replace(old, new, 1)

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

if __name__ == "__main__":
    main()
