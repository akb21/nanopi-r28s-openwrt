# NanoPi R28S OpenWrt 25.12.5 private build

Private/test-only build for FriendlyElec NanoPi R28S (RK3528A).

## Build target

- OpenWrt: 25.12.5
- Linux base: OpenWrt 25.12.5 / Linux 6.12
- R28S DT: Linux upstream R28S v6 series from 2026-09-14
- U-Boot package: overridden to U-Boot 2026.07
- U-Boot variant used for the first hardware test: `nanopi-zero2-rk3528`
- Second Ethernet: `kmod-r8169`
- Wi-Fi/Bluetooth: intentionally not included

## Images

Both root filesystem types are enabled at the same time. OpenWrt's image framework iterates over the selected filesystem list when building each device image, so the Rockchip `sysupgrade.img.gz` recipe produces both filesystem variants.

Expected files:

- `openwrt-...-friendlyarm_nanopi-r28s-squashfs-sysupgrade.img.gz`
- `openwrt-...-friendlyarm_nanopi-r28s-ext4-sysupgrade.img.gz`

The Rockchip image recipe creates the boot partition, root partition and embeds the Rockchip U-Boot image at the standard sector offset used by this target.

## Build

On a Linux host:

```bash
./scripts/build.sh
```

The final images are copied to `output/`.

## GitHub Actions

Push the repository to GitHub and run:

`Actions -> Build NanoPi R28S OpenWrt 25.12.5 -> Run workflow`

The workflow installs the U-Boot/OpenWrt host dependencies, validates the project, builds OpenWrt, and uploads every artifact from `output/`.

## Important U-Boot note

OpenWrt 25.12.5 itself packages U-Boot 2025.10. This private project overrides the Rockchip U-Boot package to 2026.07 because that release contains `nanopi-zero2-rk3528_defconfig`.

The Linux R28S v6 author reports testing the board with a board-specific R28S U-Boot target that releases the RGMII PHY reset before Linux starts. Generic RK3528 U-Boot has been shown to leave the R28S PHY in reset. The first image therefore deliberately uses the known NanoPi RK3528 board target as an experiment. If the real board fails to bring up the RTL8211F GMAC, the next step is to carry the exact R28S-specific U-Boot target from Jonas Karlman's development tree into this private repository; do not add the old Linux MDIO reset workaround.

## Sources

- OpenWrt 25.12.5: https://github.com/openwrt/openwrt/releases/tag/v25.12.5
- Rockchip image framework: https://raw.githubusercontent.com/openwrt/openwrt/v25.12.5/target/linux/rockchip/image/Makefile
- Rockchip U-Boot package: https://raw.githubusercontent.com/openwrt/openwrt/v25.12.5/package/boot/uboot-rockchip/Makefile
- U-Boot 2026.07 NanoPi Zero2 RK3528 defconfig: https://raw.githubusercontent.com/u-boot/u-boot/v2026.07/configs/nanopi-zero2-rk3528_defconfig
- Linux R28S v6: https://patchew.org/linux/20260914-r28s-upstream-v6-0-ea9edd75c126%40proton.me/
- R28S v6 test report: https://lists.openwall.net/linux-kernel/2026/09/14/1977
- FriendlyElec R28S: https://wiki.friendlyelec.com/wiki/index.php/NanoPi_R28S
