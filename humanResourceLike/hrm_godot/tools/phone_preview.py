# -*- coding: utf-8 -*-
"""手机模拟窗口：不用按 F12，直接开一个 390×844、带触摸的浏览器看竖屏版。

为什么需要它：
  ① 笔记本的 F 键常被 Fn 锁成媒体键，F12 按下去根本没到浏览器；
  ② 有些公司机器（云管 Chrome）会让 DevTools 快捷键失灵；
  ③ Chrome 自带的设备模拟要按快捷键再挑机型，这个脚本一步到位。

它跑的是 Playwright 自带的 Chromium，不碰你日常那个 Chrome ——
企业策略、扩展、书签都不影响，看到的就是干净的手机环境。
"""
import glob
import os
import socket
import subprocess
import sys
import time

DEFAULT_URL = "http://127.0.0.1:8123/index.html"


def find_live_url(start: int = 8123, tries: int = 8) -> str:
    """在 8123 往上找一个能连的本地服务。

    端口会漂：8123 被占时 serve_web.py 会自动退到 8124、8125……
    这里写死 8123 的话，一漂开窗就报「打不开」，而用户并不知道该改成几。
    """
    for p in range(start, start + tries):
        try:
            socket.create_connection(("127.0.0.1", p), 0.2).close()
        except OSError:
            continue
        return "http://127.0.0.1:%d/index.html" % p
    return ""

# 三档机型：iPhone 13 / iPhone SE / 安卓中端。最窄的那个最容易暴露排版问题。
DEVICES = [
    ("iPhone 13", 390, 844, 3),
    ("iPhone SE", 375, 667, 2),
    ("Android", 360, 800, 3),
]


def _load_playwright():
    """拿到 sync_playwright。当前解释器没装就换一个装了重跑自己。

    坑：这台机器上有三个 Python（系统 3.14、WorkBuddy 内置 3.13、可能还有别的），
    `python` 指向哪个取决于 PATH。playwright 只装在其中一个里，
    所以不能假定「双击 bat 时 import 得到」。
    """
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        pass

    roots = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Python"),
        r"C:\Python314", r"C:\Python313",
    ]
    cands = []
    for r in roots:
        if not r:
            continue
        cands += glob.glob(os.path.join(r, "python.exe"))
        cands += glob.glob(os.path.join(r, "*", "python.exe"))
    for exe in cands:
        if os.path.normcase(exe) == os.path.normcase(sys.executable):
            continue
        try:
            r = subprocess.run([exe, "-c", "import playwright"],
                               capture_output=True, timeout=25)
        except Exception:
            continue
        if r.returncode == 0:
            # 换成它重新跑自己。
            # 用 subprocess 而不是 os.execv：Windows 上 os.execv 是模拟实现，
            # 实测会把子进程的输出和退出码都吞掉（双击 bat 时表现为「黑窗一闪就关」）。
            rc = subprocess.call([exe, "-u", os.path.abspath(__file__)] + sys.argv[1:])
            raise SystemExit(rc)

    raise SystemExit(
        "这台机器上没有装了 playwright 的 Python。装一次就好：\n"
        "  python -m pip install playwright\n"
        "  python -m playwright install chromium")


def main() -> None:
    sync_playwright = _load_playwright()

    url = ""
    idx = 0
    for i, a in enumerate(sys.argv):
        if a.startswith("http"):
            url = a
        if a == "--device" and i + 1 < len(sys.argv):
            idx = int(sys.argv[i + 1]) % len(DEVICES)
    if not url:
        url = find_live_url() or DEFAULT_URL

    name, w, h, dpr = DEVICES[idx]
    print("手机模拟：%s  %d×%d  @%dx" % (name, w, h, dpr))
    print("  " + url)
    print("  鼠标左键 = 手指点击；按住 0.32 秒再拖 = 拿起行卡")
    print("  关掉这个窗口 = 结束")
    print()

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                args=["--enable-unsafe-swiftshader", "--use-gl=angle"])
        except Exception as e:
            raise SystemExit("浏览器起不来：%s" % e)

        ctx = browser.new_context(
            viewport={"width": w, "height": h},
            device_scale_factor=dpr,
            is_mobile=True,
            has_touch=True,
        )
        page = ctx.new_page()
        page.on("pageerror", lambda e: print("[page error] %s" % e))
        try:
            page.goto(url, wait_until="commit", timeout=20000)
        except Exception:
            browser.close()
            raise SystemExit("打不开 %s\n先把服务起起来：双击 play_h5.bat" % url)

        # 等加载遮罩撤掉。判断只用来决定「什么时候打印提示」，
        # 不当作打开成功与否的依据 —— 窗口已经开了，玩家看到什么就是什么。
        # 注意：遮罩不是靠 display:none 消失的，所以这里要同时看几种迹象，
        # 只看 display 会永远等不到（实测 20 秒还在等，而画面早就进游戏了）。
        for _ in range(40):
            time.sleep(0.5)
            try:
                gone = page.evaluate("""() => {
                    const s = document.getElementById('status');
                    if (!s) return true;
                    const cs = getComputedStyle(s);
                    return cs.display === 'none' || cs.visibility === 'hidden'
                        || Number(cs.opacity) === 0 || s.offsetParent === null;
                }""")
                if gone:
                    break
            except Exception:
                pass
        print("窗口已就绪。关掉它就是退出。")

        try:
            # Browser 的关闭事件叫 disconnected（"close" 是 Page 的）
            browser.wait_for_event("disconnected", timeout=0)
        except Exception:
            pass


if __name__ == "__main__":
    main()
