extends RefCounted
## 多语言。三套语言：`zh_Hans`（原文 / 恒等）、`zh_Hant`、`en`。
##
## 三个决定，都不太显然：
##
## 1. **原文就是 key。** 源码和关卡数据里写的是简中原文，英文表按「原文字面量」查。
##    这样漏翻不会崩、只会退回中文（最坏情况是玩家看到一句中文），而且能被
##    `tools/scan_strings.py --check` 一条条抓出来 —— 比「缺 key 就显示 error_17」
##    那种半崩状态好查得多。
##
## 2. **繁体不另写一份。** 简 → 繁走三趟：先词表（程序→程式），再逐字（数→數），
##    最后台湾用词表（内存→記憶體）。表由 `tools/gen_hant.py` 从 OpenCC 字典烘焙进
##    `data/i18n.json`，运行时不联网、不带 1MB 的原始词库。
##    代价是生僻词组要靠词表补，好处是**新增文案只翻一遍**（只翻英文）。
##
## 3. **`zh_Hans` 是原文语，恒等。** 测试和开发用它，不受转换表影响；
##    以后真要做简体版，加一个按钮指向它就行，文案一行都不用补。

const TABLE_PATH := "res://data/i18n.json"
const DEFAULT_SETTINGS_PATH := "user://settings.cfg"
const LOCALES: Array = ["zh_Hans", "zh_Hant", "en"]

## 会默认给中文的区域。只有一个字判断，随时改这一个常量就行。
## 说明：大中华区（陆/台/港/澳）算中文区；新加坡、马来西亚英语是工作语言，
## 这里的默认给英文 —— 要改就把 "SG" 加进来。
const ZH_REGIONS: Array = ["CN", "TW", "HK", "MO"]

const KEY_LANG := "lang"
const KEY_MANUAL := "lang_manual"

static var locale: String = "zh_Hans"
## 关掉它，`main._ready` 就不会去读设置、也不会探 IP（测试与截图用）。
static var auto_detect: bool = true
static var settings_path: String = DEFAULT_SETTINGS_PATH

static var _loaded: bool = false
static var _en: Dictionary = {}
static var _pre: Dictionary = {}      # 简→繁 词（一只→一隻）
static var _char: Dictionary = {}     # 简→繁 字
static var _post: Dictionary = {}     # 繁→台 词（内存→記憶體）
static var _twchar: Dictionary = {}   # 台湾字形（裏→裡）
static var _pre_max: int = 1
static var _post_max: int = 1
## 查不到英文时记一笔。游戏里不显示，调试与自检用（tools/scan_strings.py 也会查）。
static var misses: Dictionary = {}


# ---------------------------------------------------------------- 表

static func _load() -> void:
	if _loaded:
		return
	_loaded = true
	if not FileAccess.file_exists(TABLE_PATH):
		return
	var f := FileAccess.open(TABLE_PATH, FileAccess.READ)
	if f == null:
		return
	var data: Variant = JSON.parse_string(f.get_as_text())
	if not (data is Dictionary):
		return
	_en = data.get("en", {})
	_pre = data.get("hant_pre", {})
	_post = data.get("hant_post", {})
	_char = data.get("hant_char", {})
	_twchar = data.get("hant_twchar", {})
	_pre_max = 1
	for k in _pre.keys():
		_pre_max = maxi(_pre_max, String(k).length())
	_post_max = 1
	for k in _post.keys():
		_post_max = maxi(_post_max, String(k).length())


## 表里有几条（测试用；0 说明 data/i18n.json 没打进包）
static func table_size() -> int:
	_load()
	return _en.size()


# ---------------------------------------------------------------- 查询

## 翻一句。非中文字面量（数字、`INBOX`、`★`）原样返回，所以可以无脑套。
static func t(s: String) -> String:
	if s.is_empty():
		return s
	match locale:
		"en":
			_load()
			if _en.has(s):
				return String(_en[s])
			misses[s] = true
			return s
		"zh_Hant":
			return to_hant(s)
		_:
			return s


## 带格式参数的：先翻，再 `%`。参数顺序在两套语言里必须一致 —— 英文句子因此
## 宁可写被动句，也不要拆成两段拼接（拼接一定有一门语言读起来是倒的）。
static func tf(s: String, args: Array) -> String:
	return t(s) % args


## 关名。英文版本来就叫 `name`（First Sheep），中文版叫 `cn`（第一只羊）。
## 英文环境下再挂一个中文括号是废话，所以只给一个。
static func level_name(level: Dictionary) -> String:
	if locale == "en":
		return String(level.get("name", ""))
	return t(String(level.get("cn", "")))


# ---------------------------------------------------------------- 繁简

## 简 → 繁（台湾正体）。四趟：词 → 字 → 台湾用词 → 台湾字形。
##
## 顺序不是随便排的，跟 OpenCC 的 s2twp 流水线一致：
##   「一只」得在逐字转换**之前**认出来（转完就只剩「一隻」，认不出是量词）；
##   「内存 → 記憶體」得在逐字转换**之后**才认得出（轉完之前它是「內存」）。
static func to_hant(s: String) -> String:
	_load()
	if _char.is_empty() and _pre.is_empty():
		return s
	var out := _phrases(s, _pre, _pre_max)
	out = _chars(out, _char)
	out = _phrases(out, _post, _post_max)
	return _chars(out, _twchar)


## 贪心最长匹配：先试最长的词，命不中就挪一个字。
## 顺序很重要 ——「一下」不能被拆成「一」+「下」，「程序」更不能被拆着转。
static func _phrases(s: String, tbl: Dictionary, maxlen: int) -> String:
	if maxlen <= 1 or tbl.is_empty():
		return s
	var out := ""
	var i := 0
	var n := s.length()
	while i < n:
		var hit := ""
		var step := 1
		var lim: int = mini(maxlen, n - i)
		for l in range(lim, 1, -1):
			var cand := s.substr(i, l)
			if tbl.has(cand):
				hit = String(tbl[cand])
				step = l
				break
		out += (hit if hit != "" else s.substr(i, 1))
		i += step
	return out


static func _chars(s: String, tbl: Dictionary) -> String:
	if tbl.is_empty():
		return s
	var out := ""
	for i in s.length():
		var ch := s.substr(i, 1)
		out += String(tbl.get(ch, ch))
	return out


# ---------------------------------------------------------------- 区域 → 语言

## 一个国家的代码说了算。想加区域只改 ZH_REGIONS。
static func locale_for_country(cc: String) -> String:
	return "zh_Hant" if ZH_REGIONS.has(cc.to_upper()) else "en"


## IP 探测失败 / 离线时的兜底：看系统语言。zh_* 一律算中文区。
static func locale_for_os() -> String:
	return "zh_Hant" if OS.get_locale().begins_with("zh") else "en"


# ---------------------------------------------------------------- 存档

## 玩家自己选过就以他为准，永远不再自动改。返回 {lang, manual}
static func read_saved() -> Dictionary:
	var cf := ConfigFile.new()
	if cf.load(settings_path) != OK:
		return {}
	return {
		"lang": String(cf.get_value("i18n", KEY_LANG, "")),
		"manual": bool(cf.get_value("i18n", KEY_MANUAL, false)),
	}


static func save_locale(l: String, manual: bool) -> void:
	if not LOCALES.has(l):
		return
	var cf := ConfigFile.new()
	cf.load(settings_path)          # 先读：别把别处写的设置（音量之类）冲掉
	cf.set_value("i18n", KEY_LANG, l)
	cf.set_value("i18n", KEY_MANUAL, manual)
	cf.save(settings_path)


## 切换语言（不落盘）。界面重建由 main 负责 —— 静态类不该知道有界面。
static func set_locale(l: String) -> bool:
	if not LOCALES.has(l) or l == locale:
		return false
	locale = l
	misses.clear()
	return true


## 界面上可选的两种语言（原文语是内部用的，不给玩家看）
static func ui_locales() -> Array:
	return ["zh_Hant", "en"]


static func other_locale() -> String:
	return "en" if locale != "en" else "zh_Hant"


## 按钮上显示的字：名字写「切过去的那门语言」，玩家一看就知道按了会发生什么。
static func locale_label(l: String) -> String:
	match l:
		"en":
			return "EN"
		"zh_Hant":
			return "繁中"
		_:
			return "简中"


## 语言的全名（说明书 / 提示里用）
static func locale_full_name(l: String) -> String:
	match l:
		"en":
			return "English"
		"zh_Hant":
			return "繁體中文"
		_:
			return "简体中文"
