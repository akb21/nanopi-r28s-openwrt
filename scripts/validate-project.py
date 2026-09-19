#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]

for p in (root / "scripts").glob("*.py"):
    ast.parse(p.read_text(), filename=str(p))

cfg = (root / "config" / "r28s.config").read_text()
required = [
    "CONFIG_TARGET_rockchip=y",
    "CONFIG_TARGET_rockchip_armv8=y",
    "CONFIG_TARGET_rockchip_armv8_DEVICE_friendlyarm_nanopi-r28s=y",
    "CONFIG_TARGET_ROOTFS_SQUASHFS=y",
    "CONFIG_TARGET_ROOTFS_EXT4FS=y",
    "CONFIG_TARGET_IMAGES_GZIP=y",
    "CONFIG_PACKAGE_kmod-r8169=y",
]
missing = [x for x in required if x not in cfg]
if missing:
    raise SystemExit("Missing config entries: " + ", ".join(missing))

if "v25.12.5" not in (root / "scripts" / "build.sh").read_text():
    raise SystemExit("OpenWrt is not pinned to v25.12.5")

print("Project structure/config validation: PASS")
