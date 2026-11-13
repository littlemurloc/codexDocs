#!/usr/bin/env python3
"""出一版 Android 包：文件名自带「编号 + 日期」，旧包先删干净。

    python tools/export_apk.py                 # 版本号 +1，导出
    python tools/export_apk.py --no-bump       # 版本号不变（同一版重出，调试用）
    python tools/export_apk.py --note=palette  # 追加短标签（可选）

产物：仓库根目录 `sheep-counter-v<编号>-<YYYYMMDD>[-note].apk`

为什么文件名要带编号：达叔手上会同时有好几个包，光看 `sheep-counter.apk`
永远不知道哪个是新的 —— 而 APK 内部又搜不出可读的版本证据（脚本是压缩过的
二进制），于是只能靠文件名说清楚。

顺序上**先导出成功、再删旧包**：反过来的话，导出失败一次就把能用的包删没了。
"""
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # hrm_godot/
REPO = ROOT.parent                                      # 仓库根目录
PRESET = ROOT / "export_presets.cfg"
PRESET_NAME = "Android"

CANDIDATES = [
    Path("D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe"),
    Path("D:/XT/godot/Godot_v4.7.2-stable_win64.exe"),
]


def find_godot() -> Path:
    for p in CANDIDATES:
        if p.exists():
            return p
    found = shutil.which("godot")
    if found:
        return Path(found)
    sys.exit("[ERROR] 找不到 Godot。装到 D:/XT/godot/ 或设 GODOT_BIN 环境变量。")


def read_version() -> tuple[int, str]:
    text = PRESET.read_text(encoding="utf-8")
    m = re.search(r"^version/code=(\d+)$", text, re.M)
    n = re.search(r'^version/name="(.*)"$', text, re.M)
    if not m:
        sys.exit("[ERROR] export_presets.cfg 里找不到 version/code，导出预设被改过？")
    return int(m.group(1)), (n.group(1) if n else "1.0")


def write_version(code: int, name: str) -> None:
    text = PRESET.read_text(encoding="utf-8")
    text = re.sub(r"^version/code=\d+$", f"version/code={code}", text, count=1, flags=re.M)
    text = re.sub(r'^version/name=".*"$', f'version/name="{name}"', text, count=1, flags=re.M)
    PRESET.write_text(text, encoding="utf-8", newline="\n")


def old_packages() -> list[Path]:
    """任何 sheep-counter*.apk / *.idsig —— 根目录和 build 目录都算，IDE 手动导出的也一并收掉。"""
    out = []
    for d in (REPO, ROOT / "build"):
        if d.is_dir():
            out += [p for p in d.glob("sheep-counter*.apk")]
            out += [p for p in d.glob("sheep-counter*.apk.idsig")]
    return sorted(set(out))


def main() -> int:
    args = sys.argv[1:]
    bump = "--no-bump" not in args
    note = ""
    for a in args:
        if a.startswith("--note="):
            note = a.split("=", 1)[1].strip()

    code, _ = read_version()
    if bump:
        code += 1
        write_version(code, f"1.{code}")

    day = date.today().strftime("%Y%m%d")
    stem = f"sheep-counter-v{code}-{day}" + (f"-{note}" if note else "")
    final = REPO / f"{stem}.apk"
    tmp = ROOT / "build" / "_export_tmp.apk"

    godot = find_godot()
    tmp.parent.mkdir(parents=True, exist_ok=True)
    if tmp.exists():
        tmp.unlink()

    print(f"导出 v{code} · {day} → {final.name}")
    cmd = [str(godot), "--headless", "--path", str(ROOT),
           "--export-debug", PRESET_NAME, str(tmp)]
    r = subprocess.run(cmd)
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 10 * 1024 * 1024:
        # 失败就保留旧包，别把能用的删掉
        print(f"[ERROR] 导出失败（返回码 {r.returncode}，产物 "
              f"{tmp.stat().st_size if tmp.exists() else 0} B）。旧包未动。")
        return 1

    # 新的成了，才删旧的
    for p in old_packages():
        p.unlink()
        print(f"  删除旧包 {p.relative_to(REPO)}")

    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tmp), str(final))
    idsig = Path(str(tmp) + ".idsig")
    if idsig.exists():
        idsig.unlink()

    size = final.stat().st_size / 1024 / 1024
    print(f"完成：{final.name}（{size:.1f} MB，版本 1.{code} / code {code}）")
    print("同签名可覆盖安装；手机「应用信息」里能看到版本号。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
