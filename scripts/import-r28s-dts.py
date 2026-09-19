#!/usr/bin/env python3
import pathlib, sys, urllib.request, quopri

URL = "https://patchew.org/linux/20260914-r28s-upstream-v6-0-ea9edd75c126@proton.me/mbox"

def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8", "replace")

def get_message(mbox, n):
    marker = f"Subject: [PATCH v6 {n}/3]"
    start = mbox.find(marker)
    if start < 0:
        raise RuntimeError(f"missing patch {n}")
    end = mbox.find("\nSubject: [PATCH v6 ", start + len(marker))
    if end < 0:
        end = len(mbox)
    return mbox[start:end]

def extract_added_file(msg, path):
    decoded = quopri.decodestring(msg.encode()).decode("utf-8", "replace")
    needle = f"diff --git a/{path} b/{path}"
    p = decoded.find(needle)
    if p < 0:
        raise RuntimeError(f"missing {path}")
    p = decoded.find("\n@@ -0,0 +", p)
    if p < 0:
        raise RuntimeError(f"missing new-file hunk for {path}")
    p = decoded.find("\n", p + 1) + 1
    out = []
    for line in decoded[p:].splitlines():
        if line.startswith("diff --git ") or line == "-- " or line.startswith("-- "):
            break
        if line.startswith("+"):
            out.append(line[1:])
        elif line.startswith(" "):
            out.append(line[1:])
        elif line.startswith("\\"):
            continue
        else:
            break
    if not out:
        raise RuntimeError(f"empty extraction for {path}")
    return "\n".join(out) + "\n"

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: import-r28s-dts.py OPENWRT_DIR")
    ow = pathlib.Path(sys.argv[1]).resolve()
    mbox = get(URL)
    common = extract_added_file(
        get_message(mbox, 2),
        "arch/arm64/boot/dts/rockchip/rk3528-nanopi.dtsi",
    )
    r28s = extract_added_file(
        get_message(mbox, 3),
        "arch/arm64/boot/dts/rockchip/rk3528-nanopi-r28s.dts",
    )
    dst = ow / "target/linux/rockchip/files-6.12/arch/arm64/boot/dts/rockchip"
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "rk3528-nanopi.dtsi").write_text(common)
    (dst / "rk3528-nanopi-r28s.dts").write_text(r28s)
    print("Imported upstream R28S v6 DTS files into", dst)

if __name__ == "__main__":
    main()
