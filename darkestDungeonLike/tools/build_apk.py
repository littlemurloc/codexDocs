"""打安卓包（M97）。

一次做三件事，都是「多个 APK 分不清 / 装不上」的直接原因：

1. **versionCode 自动 +1**。
   Android 靠 `version/code` 判断新包能不能覆盖旧包。之前它一直是 1，
   于是第二次打包在手机上会被拒装，只能先卸载——数据全丢。
2. **文件名带版本号和构建时间**：`DarkestLike_v0.9+3_20261116-1438.apk`。
   `build/` 里堆几个包时，光看 `DarkestLike.apk` 谁也分不清哪个新。
3. **保留固定的 `DarkestLike.apk`**，安装时直接用它，不用记时间戳。

用法：
    python tools/build_apk.py            # 正式打包
    python tools/build_apk.py --dry-run  # 只算版本号并打印，不打包
    python tools/build_apk.py --debug    # 打 debug 包（排查用，体积大、性能差）

Godot 路径可用环境变量 GODOT 覆盖。
"""
import datetime
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "export_presets.cfg")
PRESET = "Android"
GODOT = os.environ.get(
    "GODOT", r"D:/XT/godot/Godot_v4.7.2-stable_win64_console.exe")


def read_version(cfg_text):
    """从 export_presets.cfg 里取 (version_name, version_code)。"""
    name = re.search(r'^version/name="([^"]*)"', cfg_text, re.M)
    code = re.search(r'^version/code=(\d+)', cfg_text, re.M)
    return (name.group(1) if name else "0.0", int(code.group(1)) if code else 0)


def main():
    dry = "--dry-run" in sys.argv
    debug = "--debug" in sys.argv

    with open(CFG, encoding="utf-8") as f:
        cfg = f.read()

    vname, vcode = read_version(cfg)
    new_code = vcode + 1
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    out_name = "DarkestLike_v%s+%d_%s.apk" % (vname, new_code, stamp)
    out_path = os.path.join(ROOT, "build", out_name)

    print("版本 %s · versionCode %d → %d" % (vname, vcode, new_code))
    print("输出 build/%s" % out_name)
    if dry:
        print("（--dry-run：不写配置、不打包）")
        return 0

    # 先写回 versionCode 再导出：导出读的是文件里的值，顺序反了这次就没生效
    cfg = re.sub(r"^version/code=\d+", "version/code=%d" % new_code, cfg, flags=re.M)
    with open(CFG, "w", encoding="utf-8") as f:
        f.write(cfg)

    mode = "--export-debug" if debug else "--export-release"
    cmd = [GODOT, "--headless", "--path", ROOT, mode, PRESET]
    print("运行：%s" % " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print("打包失败（退出码 %d）" % r.returncode)
        print("注意：失败的导出可能已经把 build/DarkestLike.apk 写坏，"
              "需要重跑一次恢复。")
        return r.returncode

    fixed = os.path.join(ROOT, "build", "DarkestLike.apk")
    if not os.path.exists(fixed):
        print("没找到 %s，导出没产出？" % fixed)
        return 1
    shutil.copy2(fixed, out_path)
    size_mb = os.path.getsize(out_path) / (1024.0 * 1024.0)
    print("完成：build/%s（%.0f MB）" % (out_name, size_mb))
    print("固定名仍保留在 build/DarkestLike.apk，装机直接用它。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
