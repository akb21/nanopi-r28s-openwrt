# NanoPi R28S OpenWrt 25.12.5 private build

Private/test-only build for FriendlyElec NanoPi R28S (RK3528A).

## Disclaimer / 免责声明

**English**

This is an unofficial, private, test-only build. It is not affiliated with,
endorsed by or supported by the OpenWrt project, FriendlyElec or Radxa. The
images are assembled from upstream sources plus local modifications and have
been tested on one board by the author and nobody else.

Flashing firmware can leave a device unbootable, and writing an image to the
wrong device destroys everything on it. Everything here is provided "as is",
without warranty of any kind, express or implied. The author accepts no
liability for bricked hardware, lost data or any other damage arising from
its use.

Proceed entirely at your own risk, and confirm the target device before
writing anything to it.

**中文**

本项目是非官方的私有测试构建，与 OpenWrt 项目、FriendlyElec、Radxa 均无
隶属关系，也未获得其认可或支持。镜像由上游源码加本地修改拼装而成，只在
作者的一块板子上验证过，没有第二个人复现。

刷写固件可能导致设备无法启动；把镜像写到错误的设备上会毁掉该设备上的
全部数据。本项目按"现状"提供，不附带任何形式的明示或默示担保。因使用
本项目而造成的设备变砖、数据丢失或其他任何损害，作者不承担责任。

请自行承担全部风险，写入前务必确认目标设备。

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

Both are complete disk images: write either one straight to the card with no unpacking beyond gunzip. Flash the `squashfs` one unless you specifically want a writable root filesystem; squashfs keeps the root filesystem read-only with an overlay, which survives power loss on an SD card far better than ext4.

```bash
gunzip -c openwrt-...-friendlyarm_nanopi-r28s-squashfs-sysupgrade.img.gz |
  sudo dd of=/dev/sdX bs=4M conv=fsync status=progress
```

The build collects only these two images into `output/`. The Rockchip target also produces a kernel, rootfs tarballs, `profiles.json`, buildinfo and `sha256sums`, but those are build plumbing and are left in `bin/targets/rockchip/armv8/`.

If you only ever flash one of the two filesystem variants, drop the other from `config/r28s.config` (`CONFIG_TARGET_ROOTFS_SQUASHFS` or `CONFIG_TARGET_ROOTFS_EXT4FS`) and the matching entry in `scripts/build.sh`.

## Build

On a Linux host:

```bash
./scripts/build.sh
```

The final images are copied to `output/`.

## GitHub Actions

The workflow is manual-only; pushing does not start a build.

`Actions -> Build NanoPi R28S OpenWrt 25.12.5 -> Run workflow`

It installs the host dependencies, validates the project, builds OpenWrt, and
publishes the two sysupgrade images as separate assets of a GitHub release
tagged with the build date, e.g. `25.12.5-20260920`:

- `openwrt-...-friendlyarm_nanopi-r28s-squashfs-sysupgrade-20260920.img.gz`
- `openwrt-...-friendlyarm_nanopi-r28s-ext4-sysupgrade-20260920.img.gz`

Each image is downloadable on its own. A second build on the same day replaces
that day's assets.

## Packages

The image carries the same package set as the stock OpenWrt image for the Radxa
E20C, which shares this target, subtarget and `DEVICE_PACKAGES`. That means the
full LuCI web interface plus the standard router packages. It additionally
includes `kmod-nf-conntrack-netlink`, which the stock image does not.

Because the feeds are installed and enabled, `distfeeds.list` inside the image
points at the official rockchip/armv8 package repositories, so `apk`/`opkg` and
the LuCI package manager can install further packages from
`downloads.openwrt.org`.

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
