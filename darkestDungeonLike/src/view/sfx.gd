class_name Sfx
extends Node
## 音效播放（M43）。
##
## 和 `UnitArt` / `UiSkin` 同一条原则：**按名字找文件，找不到就静音**。
## 缺音不是错误——占位期本来就该有一半是空的。
##
## ## 槽位
##
## ```
## res://assets/audio/<name>.wav     （或 .ogg / .mp3，Godot 都吃）
## ```
##
## 换音效只要替换同名文件，代码一行不改。
##
## ## 两级素材
##
## 同一个槽位可以同时存在两种文件：
##   `<name>.ogg`  从 DD1 的 bank 里解的（FMOD FADPCM → vgmstream → ffmpeg），
##                 **不进版本库**（版权），只在本地有
##   `<name>.wav`  M43 程序化合成的占位，原创、可入库
##
## 查找顺序是 **.ogg 优先**，所以：有原版就用原版，没有就退回占位，
## 换一台没有原版素材的机器上照样有声音。
## 这个顺序不是随便定的——反过来（.wav 优先）的话，本地的原版永远用不上，
## 因为占位 wav 一直在。

const DIR: String = "res://assets/audio/"
## 同时可播的声道数。战斗里一轮可能同时有攻击/受击/死亡三个音，
## 2 个声道会把前一个掐掉。
const VOICES: int = 8

## 动作名（`attack_` 之后那段）-> 命中音。
##
## DD1 的 impact 只有 13 种（刀/剑/矛/斧？/箭/枪/钝击/盾/鞭/杖/酸/气/液），
## 没有「斧」「锤」「爪」这些细分——所以几个近似的都归到同一格。
## 归类的依据是**谁在用什么**：`chop` 是麻风病人的巨斧（→ sword），
## `hook` 是赏金猎人的钩链（→ whip），`high` 是恶女的战戟（→ spear）。
const ANIM_IMPACT: Dictionary = {
	"sword": "sword", "hew": "sword", "chop": "sword", "axe": "sword", "slice": "sword",
	"dagger": "knife", "dirk": "knife", "pick": "knife", "sickle": "knife", "throw": "knife",
	"charge": "spear", "lunge": "spear", "leap": "spear", "high": "spear", "low": "spear",
	"bow": "arrow", "artillery": "arrow", "hipshot": "arrow",
	"pistol": "gun",
	"shield": "shield", "guard": "shield",
	"chain": "whip", "hook": "whip",
	"censer": "staff", "scroll": "staff", "lectionary": "staff", "lute": "staff",
	"banner": "staff", "miracle": "staff", "kneel": "staff",
	"skull": "magic_dark",
	"barf": "gas", "blast": "gas", "grenade": "gas",
	"potion": "liquid",
	"club": "general", "mace": "general", "stun": "general", "punch": "general",
	"claw": "general", "horns": "general", "rush": "general", "sickem": "general",
	"melee": "general", "ranged": "general",
}

var enabled: bool = true
var volume_db: float = -7.0
## 每次播放的随机音高浮动，避免同一种声音连响时像机器
var pitch_var: float = 0.06

var _streams: Dictionary = {}     # name -> AudioStream（缺文件缓存 null）
var _players: Array = []
var _next: int = 0
## 播放计数（`--dev` 用来验证接线，不参与玩法）
var played: int = 0


func _ready() -> void:
	for i in VOICES:
		var p := AudioStreamPlayer.new()
		p.name = "voice%d" % i
		add_child(p)
		_players.append(p)


func stream(name: String) -> AudioStream:
	var key: String = str(name)
	if _streams.has(key):
		return _streams[key]
	var st: AudioStream = null
	# 三种扩展名都试：占位是 wav，将来换成 ogg 不用改代码
	# .ogg 在前：原版优先，合成占位兜底（见文件头）
	for ext in [".ogg", ".wav", ".mp3"]:
		var path: String = DIR + key + ext
		if ResourceLoader.exists(path):
			st = ResourceLoader.load(path) as AudioStream
			break
	_streams[key] = st
	return st


func play(name: String, pitch_scale: float = 1.0, db_offset: float = 0.0) -> void:
	if not enabled or _players.is_empty():
		return
	var st: AudioStream = stream(name)
	if st == null:
		return
	var p: AudioStreamPlayer = _players[_next]
	_next = (_next + 1) % VOICES
	p.stream = st
	p.pitch_scale = maxf(0.2, pitch_scale * (1.0 + randf_range(-pitch_var, pitch_var)))
	p.volume_db = volume_db + db_offset
	p.play()
	played += 1


## 一次性播一串（升级、胜利那种）。间隔用秒算，不进 await——调用点是绘制逻辑，
## 不能挂起。用 Timer 排队。
func play_seq(names: Array, gap: float = 0.12) -> void:
	if not enabled:
		return
	var t: float = 0.0
	for n in names:
		var nm: String = str(n)
		if t <= 0.0:
			play(nm)
		else:
			var timer := get_tree().create_timer(t, false)
			timer.timeout.connect(func() -> void: play(nm))
		t += gap


## 某个槽位有没有素材。用于「有就用专门的，没有退回通用」这种两级选择。
func has_slot(name: String) -> bool:
	return stream(name) != null


## 同名多份变体（`<base>_1` … `<base>_count`），随机挑一份播。
##
## 敌人语音用这个：每只怪每种叫声有 2 份录音，随机挑 + 已有的随机音高，
## 连挨两下不会听起来像同一段在重复。
##
## 存在的份数**第一次调用时探明并缓存**——每帧去试 ResourceLoader.exists
## 会变成每帧几十次文件查询。
func play_variant(base: String, count: int = 2, pitch: float = 1.0, db: float = 0.0) -> bool:
	var names: Array = _variant_list(base, count)
	if names.is_empty():
		return false
	play(str(names[randi() % names.size()]), pitch, db)
	return true


var _variants: Dictionary = {}      # base -> Array[String]


func _variant_list(base: String, count: int) -> Array:
	var key: String = "%s#%d" % [base, count]
	if _variants.has(key):
		return _variants[key]
	var out: Array = []
	for i in range(1, count + 1):
		var nm: String = "%s_%d" % [base, i]
		if stream(nm) != null:
			out.append(nm)
	_variants[key] = out
	return out


## 动作名 -> impact 槽位（`imp_<kind>`）。未知动作给 `general`：
## 宁可听一声「闷响」，也不要因为素材不全而静音——静音会让人以为音效坏了。
static func impact_slot(anim: String) -> String:
	var a: String = str(anim)
	if a.begins_with("attack_"):
		a = a.substr(7)
	return "imp_" + str(ANIM_IMPACT.get(a, "general"))
