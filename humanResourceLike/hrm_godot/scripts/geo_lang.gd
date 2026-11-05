extends Node
## 用 IP 归属决定「第一次打开该说哪门语言」。
##
## 三条线依次试，任一条回了就停；全失败就发一个空串，由调用方退回系统语言。
## 为什么自己写而不用现成的地理服务：这东西一辈子只跑一次，失败**完全无所谓**，
## 所以宁可要「几个免费源互相兜底」，也不要一个需要注册 key 的。
##
## 两条纪律：
##   1. **不许挡住启动。** 界面先按系统语言出来，探测结果晚到了再静默换掉。
##   2. **玩家自己选过就不再探。** 这条判据在 main 里（`manual` 存档位），
##      不在这儿 —— 这里只负责「这个 IP 属于哪」。
##
## 走的都是明文/公开 JSON 接口，不发任何本地信息，只发一个 HTTP GET。

signal located(country: String)      # 两位国家码（大写）；"" = 三条线都没探到

## 超时给 3 秒：慢到 3 秒还没回，说明这个源在本地网络里不通，
## 与其等它不如换下一个 —— 玩家这时已经在玩了。
const TIMEOUT := 3.0

## 顺序是有讲究的：先 https 的（能过大多数公司代理），再退明文。
## 每个源只取一个字段，字段名各不相同（各家 JSON 不一样），所以写在表里。
const SOURCES: Array = [
	{"url": "https://ipwho.is/", "key": "country_code"},
	{"url": "https://ipapi.co/json/", "key": "country_code"},
	{"url": "https://api.myip.com", "key": "cc"},
	{"url": "http://ip-api.com/json/?fields=countryCode", "key": "countryCode"},
]

var _done: bool = false


## 探测。结果通过 `located` 发一次，之后不再发。
func probe() -> void:
	if _done:
		return
	_done = true
	for src in SOURCES:
		var cc: String = await _ask(src)
		if cc.length() == 2:
			located.emit(cc.to_upper())
			return
	located.emit("")


func _ask(src: Dictionary) -> String:
	var req := HTTPRequest.new()
	req.timeout = TIMEOUT
	# 有的服务（ipwho.is）不带 UA 会直接 403，带一个最省事。
	add_child(req)
	var err: int = req.request(String(src["url"]), ["User-Agent: SheepCounter/1.0"])
	if err != OK:
		req.queue_free()
		return ""
	var res: Array = await req.request_completed
	req.queue_free()
	if int(res[1]) != 200:
		return ""
	var body: PackedByteArray = res[3]
	var data: Variant = JSON.parse_string(body.get_string_from_utf8())
	if not (data is Dictionary):
		return ""
	var v: Variant = data.get(String(src["key"]), "")
	if not (v is String):
		return ""
	var cc: String = String(v).strip_edges()
	# 「成功但国家未知」这种要当失败处理，别把 XX 当地址用
	return "" if cc == "" or cc.to_upper() == "XX" else cc
