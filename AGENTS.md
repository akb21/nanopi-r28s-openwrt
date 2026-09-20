# AGENTS.md

给在本仓库工作的 AI/人类协作者的说明。先读这一页，再读 `README.md`。

## 项目是什么

这不是 OpenWrt 源码树，也不含任何 OpenWrt 代码。它是一个**构建包装层**：
在构建时把 FriendlyElec NanoPi R28S（RK3528A）的支持注入到一份未修改的
OpenWrt v25.12.5 检出里，然后编译出可刷写的 sysupgrade 镜像。

所有对 OpenWrt 的改动都在构建时由脚本施加，不落盘到仓库，因此：
**不要往仓库里提交 OpenWrt 源码、DTS、补丁文件或 `.config` 的生成结果。**
仓库里只有「怎么注入」的脚本和一份配置片段。

## 目录结构

```
config/r28s.config          目标 .config 片段（rockchip/armv8 + 设备 + LuCI + 文件系统）
scripts/build.sh            完整构建入口：clone → 注入 → feeds → 编译 → 只收集 SD 卡镜像
scripts/import-r28s-dts.py  从 patchew 拉 Linux R28S v6 补丁，抽出两个 DTS 写入 OpenWrt 树
scripts/patch-openwrt.py    改 armv8.mk（加设备）和 uboot-rockchip/Makefile（升 U-Boot、加板级 target）
scripts/validate-project.py 静态校验：脚本语法 + config 必选项 + feeds 步骤 + OpenWrt 版本钉死
.github/workflows/build.yml GitHub Actions：仅手动触发，构建后把两张镜像发到 release
VERSION                     一行人类可读的版本描述
```

`.work/`（OpenWrt 检出）、`output/`（产物）和 `release/`（发版用的改名副本）
都被 `.gitignore` 忽略。

## 常用命令

```bash
# 静态校验，秒级，改动后先跑这个
python3 scripts/validate-project.py

# 单独跑某个注入脚本（需要一个 OpenWrt 检出目录作参数）
python3 scripts/patch-openwrt.py   .work/openwrt
python3 scripts/import-r28s-dts.py .work/openwrt

# 完整构建，需要 Linux 主机 + OpenWrt 全部编译依赖，小时级
./scripts/build.sh
```

本机是 macOS 时不要尝试完整构建，用 `validate-project.py` 做正确性检查，
真正的构建交给 GitHub Actions 或 Linux 机器。

## 包集从哪里来

`config/r28s.config` 只管目标、设备、文件系统和几个显式包，镜像里绝大多数
包来自两个地方：目标 profile 的 `DEFAULT_PACKAGES`（`include/target.mk`：
base-files、dropbear、netifd、uci… 加上 `DEVICE_TYPE` 对应的一组），以及
**feeds 里的包**。

所以 `scripts/feeds update -a` + `install -a` 不能省：

- LuCI 整个栈都在 `luci` feed 里。不装 feeds 就选不到，镜像里根本没有网页。
- `scripts/feeds update` 会生成 `feeds/<name>.index`，`scripts/feeds` 的
  `feed_config()` 据此产出带 `default y` 的 `config FEED_<name>` 符号。
  `/etc/apk/repositories.d/distfeeds.list` 是按这些符号逐条 feed 生成的，
  没有它们就只剩 core 和 base 两条（`include/feeds.mk` 的
  `FeedSourcesAppendAPK`）。

对照基线是官方同一个 target/subtarget 的 radxa E20C 镜像——它和 R28S 的
`DEVICE_PACKAGES` 完全一样（都只有 `kmod-r8169`），所以两者的差别只在
LuCI 栈。参考文件：

- `https://downloads.openwrt.org/releases/25.12.5/targets/rockchip/armv8/openwrt-25.12.5-rockchip-armv8.manifest`
- 同目录的 `config.buildinfo`（官方构建用的配置摘要）

**官方 E20C 镜像里没有 `kmod-nf-conntrack-netlink`**，R28S 配置里那一条是
额外要求，不是对齐 E20C 的一部分。官方镜像里的
`luci-app-attendedsysupgrade` / `owut` / `attendedsysupgrade-common` 也**没有**
照搬：attended sysupgrade 要查 `sysupgrade.openwrt.org`，而
`friendlyarm_nanopi-r28s` 不在官方构建里，装了也用不了。

## CI 构建时间与缓存

一次冷构建里，前面约 50 分钟几乎全花在编译上（clone 18 秒、download 约
1 分钟，其余是 host tools ~14 分钟 + 交叉工具链 ~21 分钟 + 目标包）。所以
优化点在缓存这两段，而不是下载。

workflow 里有三层缓存：

1. **host tools + 交叉工具链**（`openwrt-buildstate-*`，稳定 key，
   key 含 `config/r28s.config` 的 hash）。缓存
   `staging_dir/{host,toolchain-*}` 与 `build_dir/{host,toolchain-*}`。
   **三个 stamp 位置缺一不可**：OpenWrt 的依赖链是
   `.configured` → `.built` → `_installed`，前两个在 `build_dir/`，只有
   `_installed` 在 `staging_dir/`。少缓存 `build_dir/toolchain-*` 的话，
   `make` 会照旧从 configure 开始重建工具链，缓存等于白做。
2. **feeds 检出**（`openwrt-feeds-*`，key 只含 `scripts/build.sh`）。
   `scripts/feeds update -a` 每次都要克隆 4 个 feed 仓库，而它与包配置
   无关，只与 `build.sh` 里钉的 tag 有关，所以单独用一把稳定的 key。
3. **ccache**（`ccache-*`，滚动 key）。`config/r28s.config` 里的
   `CONFIG_CCACHE=y` 同时作用于目标编译和 host 编译（`rules.mk:347`）。

`dl/` **故意不缓存**：GitHub runner 的网络让 `make download` 只花约
1 分钟，缓存 1.5 GB 的收益抵不过恢复时间。

`CONFIG_DEVEL=y` 必须和 `CONFIG_CCACHE=y` 一起出现。`CONFIG_CCACHE` 的
prompt 是 `bool "Use ccache" if DEVEL`，DEVEL 关闭时它是不可见符号，
`make defconfig` 会**静默丢掉**这个值，ccache 就变成静默无效。
OpenWrt 官方 CI 同样先写 `CONFIG_DEVEL=y`。

`build.sh` 会在重新 clone 前把 `CACHED_BUILD_STATE`（`staging_dir`、
`build_dir`、`dl`、`feeds`）挪到一边再挪回来。**不要删掉这段逻辑**：缓存
恢复进来的目录里没有 `.git`，不做保全的话 `rm -rf "${OW}"` 会顺手把
35 分钟的构建产物和 feed 检出全删掉，缓存就永远命中不了。

改 `config/r28s.config` 会换掉 buildstate 的 key（触发一次冷编译），改
`scripts/build.sh` 会换掉 feeds 的 key。要强制重建时删缓存：

```bash
gh cache delete --all --repo akb21/nanopi-r28s-openwrt
```

## 核心不变量

改动脚本时，下面这些值是被相互约束的，改一处要同步改其余：

| 量 | 值 | 出现位置 |
|---|---|---|
| OpenWrt tag | `v25.12.5` | `build.sh` 的 `TAG`、`validate-project.py` 的断言、workflow 名称 |
| U-Boot 版本 | `2026.07` | `patch-openwrt.py` 的 `UBOOT_VERSION`、`VERSION`、`README.md` |
| U-Boot 源码 hash | `78e8bfc3…1243e` | `patch-openwrt.py` 的 `UBOOT_HASH` |
| U-Boot 板级 target | `nanopi-zero2-rk3528` | `patch-openwrt.py` 的 `UBOOT_TARGET`、设备定义里的 `UBOOT_DEVICE_NAME` |
| 设备名 | `friendlyarm_nanopi-r28s` | `config/r28s.config`、`patch-openwrt.py`、`validate-project.py`、`build.sh` 的产物校验 |
| DTS 名 | `rk3528-nanopi-r28s` | `patch-openwrt.py` 的 `DEVICE_DTS`、`import-r28s-dts.py` 的目标文件名 |
| U-Boot 补丁集 | 保留 4 个、删除 12 个 | `patch-openwrt.py` 的 `KEPT_UBOOT_PATCHES` / `REDUNDANT_UBOOT_PATCHES` |

U-Boot 之所以被单独覆盖：OpenWrt 25.12.5 自带 U-Boot 2025.10，而
`nanopi-zero2-rk3528_defconfig` 只在 2026.07 里才有（2025.10 / 2026.01 /
2026.04 均为 404，已实测）。换版本就必须同时换 `PKG_HASH`，否则
`make download` 阶段 hash 校验失败。

**U-Boot 版本和补丁集必须成对看待。** OpenWrt 25.12.5 的
`package/boot/uboot-rockchip/patches/` 里 16 个补丁是针对 2025.10 写的；
2026.07 已把它们全部合入上游，直接应用会被 `patch(1)` 判为
"previously applied (or reversed)" 并中断构建。所以 `patch-openwrt.py`
在改完版本后会把 12 个冗余补丁删掉，只留 4 个仍能打上的。
换 OpenWrt tag 或换 U-Boot 版本时，这两个清单都要重新实测，脚本末尾的
集合比对会在大声失败。

**不要**给 GMAC/PHY 加旧的 Linux MDIO reset workaround。README 里说明了原因：
R28S 的 RTL8211F 复位应该在 U-Boot 阶段完成，若首个镜像起不来网口，
正确方向是把 Jonas Karlman 树里的 R28S 专用 U-Boot target 移植进来。

## 脚本风格约定

`patch-openwrt.py` 已经建立了一套值得沿用的模式：

- **精确锚点 + 大声失败**：`replace_once()` 在找不到目标文本时直接
  `RuntimeError`，不会静默跳过。上游 OpenWrt 改动导致锚点失效时，
  构建应该立刻炸掉，而不是产出一个没打上补丁的镜像。新增补丁请复用这个函数。
- **幂等保护用存在性判断**：追加式的改动（设备定义、U-Boot target、
  target 列表项）都先 `if ... not in s` 再写，避免重复注入。
- **补丁内容写成模块级字符串常量**（`DEVICE`、`UBOOT_TARGET`），
  不要散落在 `main()` 里。
- shell 脚本用 `set -euo pipefail`，Python 用标准库，**不引入第三方依赖**
  （CI 只装了 apt 里的系统包，pip 依赖会直接挂）。

## 已知陷阱

**`build.sh` 不是幂等的。** 它只在 `.work/openwrt/.git` 不存在时才 clone，
但每次都会重跑 `patch-openwrt.py`，而该脚本对 `PKG_VERSION:=2025.10` 和
原始 `PKG_HASH` 的替换没有存在性保护。所以在已经有 `.work/openwrt` 的情况下
第二次执行 `build.sh`，会在 `U-Boot version: expected text not found` 处失败。
重新构建前先 `rm -rf .work/openwrt`，或者把这两处替换也改成幂等写法。

**DTS 来源是网络而且在构建时才抓。** `import-r28s-dts.py` 直接访问
patchew.org 的 mbox 并解析 MIME/quoted-printable，没有 hash 校验，
也没有离线回退。URL 里的 message-id 实际充当了版本钉死，但上游列表一旦
不可达，构建就会失败在下载而不是编译阶段。这个脚本靠
`diff --git` / `@@ -0,0 +` 文本匹配抽文件，对补丁格式变化很敏感。

**`validate-project.py` 覆盖范围有限。** 它只做 AST 语法检查和 config
字符串匹配，不校验 U-Boot 版本与 hash 是否配套，也不校验设备名在各文件间
是否一致。上表里的跨文件一致性目前靠人工维护。

**CI 没有测试。** `validate-project.py` 是唯一的自动化检查，它不做真实
构建。`timeout-minutes: 240` 是为冷构建留的余量；缓存命中时远用不到。

## 提交规范

遵循 Conventional Commits：`<type>(<scope>): <subject>`，
type 取 `feat|fix|docs|style|refactor|perf|test|build|ci|chore|...`，
subject 不超过 50 字符、结尾无句号。本仓库常用的 scope：
`build`（build.sh）、`patch`（patch-openwrt.py）、`dts`（import-r28s-dts.py）、
`config`、`ci`。一次提交只放一类相关改动。

## 改动前自检

1. `python3 scripts/validate-project.py` 通过。
2. 若改了设备名 / DTS 名 / U-Boot target，上面「核心不变量」表里的
   每一处都已同步。
3. 若动了 `patch-openwrt.py` 的锚点字符串，确认它们仍存在于
   OpenWrt v25.12.5 的对应文件里（对照 README 的 Sources 链接）。
4. 若改了产物名或数量，`build.sh` 末尾的两个 `if (( ${#...} != 1 ))`
   校验需要同步调整。
5. 若换了 OpenWrt tag 或 U-Boot 版本，重新实测
   `package/boot/uboot-rockchip/patches/` 里哪些补丁还打得上，
   并同步 `KEPT_UBOOT_PATCHES` / `REDUNDANT_UBOOT_PATCHES`。
