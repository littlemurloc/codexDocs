# -*- coding: utf-8 -*-
"""导出后跑：把 Godot 默认加载页换成游戏的深蓝牧场风。
只动 <title> 和 <style>，启动逻辑里的 id（status / status-splash / status-progress /
status-notice）一个不改 —— 那是引擎启动器认的。
用法：python tools/patch_web_html.py   （在 hrm_godot 目录下）"""
import io

P = "build/web/index.html"
s = io.open(P, encoding="utf-8").read()

OLD_STYLE_HEAD = "\t\t<style>"
NEW_CSS = """\t\t<style>
html, body, #canvas {
	margin: 0;
	padding: 0;
	border: 0;
}

body {
	color: white;
	background-color: #05223f;          /* 游戏页底色：深蓝夜空 */
	overflow: hidden;
	touch-action: none;
}

#canvas {
	display: block;
}

#canvas:focus {
	outline: none;
}

#status, #status-splash, #status-progress {
	position: absolute;
	left: 0;
	right: 0;
}

#status, #status-splash {
	top: 0;
	bottom: 0;
}

#status {
	background-color: #05223f;
	display: flex;
	flex-direction: column;
	justify-content: center;
	align-items: center;
	visibility: hidden;
}

#status-splash {
	width: 220px;                       /* 羊图标：小而居中，别铺满 */
	max-height: 46%;
	max-width: 60%;
	margin: 0 auto;
	object-fit: contain;
	border-radius: 18%;
	box-shadow: 0 14px 40px rgba(0, 0, 0, 0.45);
}

#status-splash.show-image--false {
	display: none;
}

#status-splash.use-filter--false {
	image-rendering: pixelated;
}

#status-progress, #status-notice {
	display: none;
}

#status-progress {
	appearance: none;
	-webkit-appearance: none;
	border: 0;
	bottom: 18%;
	width: 300px;
	height: 10px;
	margin: 0 auto;
	border-radius: 5px;
	background: #0e5a96;                /* 面板蓝做槽 */
	overflow: hidden;
}

#status-progress::-webkit-progress-bar {
	background: #0e5a96;
	border-radius: 5px;
}

#status-progress::-webkit-progress-value {
	background: #f2b544;                /* 琥珀做填充，和游戏里的进度条同色 */
	border-radius: 5px;
}

#status-progress::-moz-progress-bar {
	background: #f2b544;
	border-radius: 5px;
}

#status-loadtext {
	font-family: 'Segoe UI', 'Noto Sans', 'Microsoft YaHei', sans-serif;
	font-size: 14px;
	letter-spacing: 0.12em;
	color: #9cc3e8;
	margin-top: 22px;
	text-align: center;
}

#status-notice {
	background-color: #0e3a63;
	border-radius: 0.5rem;
	border: 1px solid #1470b4;
	color: #dceaf7;
	font-family: 'Segoe UI', 'Noto Sans', 'Microsoft YaHei', sans-serif;
	line-height: 1.4;
	margin: 0 2rem;
	max-width: 30rem;
	overflow: hidden;
	padding: 1rem;
	text-align: center;
	z-index: 1;
}

#status-brand {
	position: absolute;
	bottom: 26px;
	left: 0;
	right: 0;
	text-align: center;
	font-family: 'Segoe UI', 'Noto Sans', 'Microsoft YaHei', sans-serif;
	font-size: 12px;
	letter-spacing: 0.28em;
	color: #3f6a96;
	user-select: none;
}
		</style>
"""

# 1) 整段替换默认 <style>
a = s.index(OLD_STYLE_HEAD)
b = s.index("</style>", a) + len("</style>")
s = s[:a] + NEW_CSS + s[b:]

# 2) splash 后面加一行加载文案；品牌小字放遮罩**里面**——放外面的话引擎起来
#    遮罩被删、它还留在页面上，会叠在游戏画面底部（真踩过）
s = s.replace(
    '<img id="status-splash" class="show-image--true fullsize--true use-filter--true" src="index.png" alt="">',
    '<img id="status-splash" class="show-image--true fullsize--true use-filter--true" src="index.png" alt="">\n'
    '\t\t\t<div id="status-loadtext">LOADING · 加载中</div>\n'
    '\t\t\t<div id="status-brand">SHEEP COUNTER</div>',
)

io.open(P, "w", encoding="utf-8").write(s)
print("patched", P)
