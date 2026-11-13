class_name BgMusic
extends Node

## 背景音乐（M49）。
##
## 曲目来自 DD1 的 `audio/secondary_banks/music.bank`：
## 那是个 RIFF/FEV 容器，里面嵌了一层 FSB5，编码是 **FMOD FADPCM 4-bit ADPCM**
## （不是 MPEG、也不是 Vorbis——按 MPEG 帧扫和按 Vorbis 头解都解不出来）。
## 用 vgmstream 解成 wav，再用 ffmpeg 转 ogg q4。详见 M49_MUSIC.md。
##
## 和音效层（`Sfx`）分开的两条理由：
##   1. 音乐要循环、要淡入淡出、同一时刻只该有一首；音效是多声道叠播
##   2. 音乐的音量基准比音效低一档，混在一起调会把问题搅乱

const DIR: String = "res://assets/audio/music/"
## 淡入淡出时长。0.8 秒够把"切屏时突然换歌"抹平，再长会显得反应慢。
const FADE_TIME: float = 0.8

## 音乐基准音量，由主音量设置推出来（见 ExpeditionScene._apply_volume）。
## 默认值只在没有设置时用。
var base_db: float = -14.0
var enabled: bool = true

var _player: AudioStreamPlayer
var _current: String = ""
## 0..1 的淡入程度；跟 `_fade_dir` 一起决定音量。
var _fade: float = 0.0
var _fade_dir: float = 0.0
var _cache: Dictionary = {}


func _ready() -> void:
	_player = AudioStreamPlayer.new()
	_player.bus = "Master"
	_player.volume_db = -80.0
	add_child(_player)
	set_process(true)


## 切一首。同一首正在播时什么都不做，避免每帧重设 stream 把播放位置打回 0。
func play(id: String) -> void:
	if not enabled or id.is_empty():
		return
	if id == _current and _player.playing:
		return
	var path: String = DIR + id + ".ogg"
	if not ResourceLoader.exists(path):
		# 缺曲目 = 安静，不报错。和 `UnitArt` / `Sfx` 同一条原则：
		# 资源缺失是正常状态（原创曲目还没写），不该让游戏中断。
		stop()
		return
	var st: AudioStream = _cache.get(id, null)
	if st == null:
		st = ResourceLoader.load(path) as AudioStream
		if st == null:
			stop()
			return
		# 循环必须在运行时设：导入设置里的 loop 是给编辑器预览用的，
		# 而这几首是「按场景循环」的 BGM，把 loop 写在资源上反而限制了别处复用。
		if st is AudioStreamOggVorbis:
			(st as AudioStreamOggVorbis).loop = true
		_cache[id] = st
	_current = id
	_player.stream = st
	_player.volume_db = -60.0
	_player.play()
	_fade = 0.0
	_fade_dir = 1.0


func stop() -> void:
	_current = ""
	_fade_dir = -1.0


func _process(delta: float) -> void:
	if _player == null:
		return
	if _fade_dir != 0.0:
		_fade = clampf(_fade + _fade_dir * delta / FADE_TIME, 0.0, 1.0)
		if _fade <= 0.0 and _fade_dir < 0.0:
			_fade_dir = 0.0
			_player.stop()
		elif _fade >= 1.0:
			_fade_dir = 0.0
	_player.volume_db = lerpf(-40.0, base_db, _fade) if _fade > 0.001 else -80.0
