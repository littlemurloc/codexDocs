# -*- coding: utf-8 -*-
"""H5 版本地试玩：起一个静态服务器并自动打开浏览器。

为什么需要它：Godot 的 Web 版是 wasm，浏览器不允许从 file:// 加载，
**双击 index.html 一定白屏**。必须走 http。

端口从 8123 起往上试 —— 8080/8000 这类常被别的软件占着，
直接写死会在 bind 那步抛 WinError 10013/10048，看起来像权限问题。
"""
import http.server
import os
import socket
import socketserver
import subprocess
import sys
import threading
import urllib.request
import webbrowser

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "build", "web")


def lan_ip() -> str:
    """本机在局域网里的地址。手机要连的就是它。

    用 UDP「连」一个不可达地址只是为了问内核「你会从哪块网卡出去」——
    connect 一个 UDP socket 不发任何包，所以不会产生流量，也不依赖外网。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


MARK = "SHEEP COUNTER"      # 我们自己导出的 index.html 里一定有这串品牌字


def find_running(start: int, tries: int) -> int:
    """已经在跑的同一个试玩服务占着哪个端口（0 = 没找到）。

    为什么要找：包是同一个、目录也是同一个，再起一个只是多占一个端口、
    多留一个窗口，还把手机地址换掉。达叔实测连点五次，屏幕上堆了五个服务。
    """
    for p in range(start, start + tries):
        # 先探端口再验内容：只看端口会把这个范围内别的软件误认成我们的服务。
        # create_connection 被拒绝是立刻返回的（RST），不会一个个等超时。
        try:
            socket.create_connection(("127.0.0.1", p), 0.2).close()
        except OSError:
            continue
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:%d/index.html" % p, timeout=1.5) as r:
                body = r.read(8192).decode("utf-8", "ignore")
        except Exception:
            continue
        if MARK in body:
            return p
    return 0


def make_server(host: str, start: int, tries: int, handler):
    """从 start 起挨个真绑一次，第一个绑上的就用它。

    ⚠ 以前这里是「先 free_port() 探一下，再交给 TCPServer 绑」，而 free_port 里
    设了 SO_REUSEADDR —— **Windows 上这个选项的语义和 Linux 不同**：
    它允许两个 socket 绑同一个端口。于是「探测说空闲 → 真绑时 WinError 10048」
    必然发生（已达叔实测踩到）。
    正确做法是别探，直接绑：绑定成功本身就是唯一的判据，也顺手消掉了
    「探完到绑上」这段空窗期的竞态。
    """
    last: Exception | None = None
    for p in range(start, start + tries):
        try:
            return socketserver.ThreadingTCPServer((host, p), handler), p
        except OSError as e:      # 10048 = 已被占用，10013 = 权限不够
            last = e
            continue
    raise SystemExit(
        "端口 %d-%d 都绑不上（最后一个错误：%s）\n"
        "多半是有另一个试玩窗口开着，关掉它再双击一次。"
        % (start, start + tries - 1, last))


def open_page(url: str) -> bool:
    """把页面丢给默认浏览器，返回有没有成功。

    顺序是反的：**先**用 Windows 的 `start`，再退到 webbrowser。
    原因实测过：这台机器上 webbrowser.open() 返回 True 却什么都没打开 ——
    它只代表「把请求发出去了」，不代表浏览器收下了。而 `start` 是资源管理器
    自己处理协议关联，也就等于用户在地址栏里回车。
    """
    if os.name == "nt":
        # os.startfile 走 ShellExecute，和「在资源管理器里双击一个网址」同一条路，
        # 比 webbrowser（它只是尽量猜一个浏览器）更接近用户想要的行为。
        try:
            os.startfile(url)
            return True
        except OSError:
            pass
        try:
            subprocess.Popen(["cmd", "/c", "start", "", url],
                             creationflags=0x08000000)
            return True
        except OSError:
            pass
    try:
        return bool(webbrowser.open(url))
    except Exception:
        pass
    print()
    print("  ⚠ 没自动打开浏览器的话，请手动复制上面那条地址。")
    return False


def main() -> None:
    if not os.path.isfile(os.path.join(ROOT, "index.html")):
        raise SystemExit("没找到网页版：%s\n先导出一次（README「分发时：导出 H5」）" % ROOT)

    os.chdir(ROOT)

    # 想强制绕开浏览器缓存时，换个端口比按 Ctrl+F5 可靠 ——
    # 缓存是按 URL 存的，换端口就是新 URL，谁也拦不住。
    start = 8123
    for i, a in enumerate(sys.argv):
        if a == "--port" and i + 1 < len(sys.argv):
            start = int(sys.argv[i + 1])

    # 已经有一个在跑就别再起一个 —— 直接报它的地址。
    # 注意必须在 start 解析完之后：放前面会 UnboundLocalError（改这行时踩过）。
    if "--force" not in sys.argv:
        running = find_running(start, 8)
        if running:
            url = "http://127.0.0.1:%d" % running
            print("已经有一个在跑，直接打开它：")
            print("  " + url)
            print("  手机（同一 WiFi）： http://%s:%d" % (lan_ip(), running))
            print()
            print("  手机打不开的话，说明那个窗口是单机模式：关掉它，再双击本文件。")
            print("  确实要另起一个：加 --force（或 --port 8130）")
            print()
            # 这一支原来只打印不打开 —— 用户双击后看到窗口一闪、什么都没发生。
            # 「已经有服务」和「新起服务」对双击的人应该是同一个结果：页面开出来。
            if "--no-browser" not in sys.argv:
                open_page(url)
            return

    # 默认只绑本机回环。加 --lan 才绑 0.0.0.0 ——
    # 移动版的手势（长按拿起、双指滚、点牌追加）只有真手机能验，
    # 绑 127.0.0.1 的话手机连不上，等于没有验。
    host = "127.0.0.1"
    if "--lan" in sys.argv:
        host = "0.0.0.0"

    class Q(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # 绝不缓存：pck 换了以后浏览器还捧着旧的，表现是「改完了还是老样子」，
            # 而 http.server 的默认头会让浏览器按启发式规则缓存好一阵。
            # 试玩用的服务端不图省这点流量。
            self.send_header("Cache-Control", "no-store, must-revalidate")
            super().end_headers()

        def log_message(self, fmt, *args):      # 别刷屏，只留出错
            if not str(args[1] if len(args) > 1 else "").startswith("2"):
                sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    httpd, port = make_server(host, start, 30, Q)
    httpd.daemon_threads = True
    url = "http://127.0.0.1:%d" % port

    print("Sheep Counter H5")
    print("  " + url)
    if host == "0.0.0.0":
        print("  手机（同一 WiFi）打开： http://%s:%d" % (lan_ip(), port))
    else:
        print("  想让手机也能开：加 --lan 再跑一次")
    print("  关掉这个窗口 = 停止服务器")
    print()
    if "--no-browser" not in sys.argv:
        # 延 0.8 秒：serve_forever 还没进循环，浏览器就来请求会撞上「连接被拒」
        threading.Timer(0.8, lambda: open_page(url)).start()


    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
