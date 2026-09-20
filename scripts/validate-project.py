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
    "CONFIG_PACKAGE_luci=y",
    "CONFIG_PACKAGE_kmod-nf-conntrack-netlink=y",
]
missing = [x for x in required if x not in cfg]
if missing:
    raise SystemExit("Missing config entries: " + ", ".join(missing))

build = (root / "scripts" / "build.sh").read_text()
if "v25.12.5" not in build:
    raise SystemExit("OpenWrt is not pinned to v25.12.5")

# Feeds carry LuCI and most userland packages. Without them the image silently
# loses LuCI and distfeeds.list loses its per-feed entries.
for step in ("scripts/feeds update -a", "scripts/feeds install -a"):
    if step not in build:
        raise SystemExit(f"build.sh does not run '{step}'")

print("Project structure/config validation: PASS")
