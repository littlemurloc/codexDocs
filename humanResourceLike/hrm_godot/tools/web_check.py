# -*- coding: utf-8 -*-
"""打开本地 Web 版，等引擎起来后截图。用真实时间，不玩虚拟时钟。"""
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8099/index.html"
out = sys.argv[2] if len(sys.argv) > 2 else "_shots/_web_pw.png"
wait_s = int(sys.argv[3]) if len(sys.argv) > 3 else 40

with sync_playwright() as p:
    b = p.chromium.launch(args=["--enable-unsafe-swiftshader", "--use-gl=angle"])
    pg = b.new_page(viewport={"width": 1280, "height": 800})
    errors = []
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    import time

    def _throttle(route):          # 让加载页多停留几秒，方便截图
        time.sleep(4)
        route.continue_()

    if wait_s < 0:                 # 负数 = 抓「加载页还在」的最早时刻
        pg.goto(url)
        for _ in range(200):
            if pg.evaluate("!!document.getElementById('status')"):
                pg.wait_for_timeout(400)
                break
            pg.wait_for_timeout(20)
    else:
        pg.route("**/index.wasm", _throttle)
        pg.goto(url)
        pg.wait_for_timeout(wait_s * 1000)
    info = pg.evaluate("""() => {
        const st = document.getElementById('status');
        return {
            status_exists: !!st,
            visibility: st ? getComputedStyle(st).visibility : null,
            img_loaded: (() => { const i = document.getElementById('status-splash');
                return i ? (i.complete + ' natural=' + i.naturalWidth) : 'gone'; })(),
            progress_display: (() => { const p = document.getElementById('status-progress');
                return p ? getComputedStyle(p).display + ' val=' + p.value + '/' + p.max : 'gone'; })(),
        };
    }""")
    print("dom:", info)
    pg.screenshot(path=out)
    print("console errors:", len(errors))
    for e in errors[:5]:
        print("  ", e[:200])
    b.close()
print("saved", out)
