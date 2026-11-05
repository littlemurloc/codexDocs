extends Node
## 程序化音效 —— 项目里没有一张音频文件，全部现场合成。
##
## 和「舞台没有一张位图」是同一个取舍：零素材、随时可调、体积为零。
## 更实际的原因是 **音高必须能跟着 COMBO 走** —— 越到后面每一步越高半个音，
## 这是「跑得越来越快」这件事唯一能被耳朵听见的形式。素材包里翻不出这种东西。
##
## 六种声音构成一次「运行」的听觉骨架：
##   click  每一步（很轻、像节拍器）—— COMBO 靠它连成鼓点
##   wood   动木牌（COPYTO / COPYFROM / BUMP*）
##   out    推一只羊过栅栏 —— **音高随「今天第几只」上行**，数满就是一串音阶
##   err    绊倒（下行两音）
##   win    过关（上行四音）
##   ding   刷了自己的记录（叠在 win 后面，让「我更快了」有自己的声音）
##
## 为什么用 8 路 player 池：一个 player 播新 stream 会把上一条掐掉。
## 高速时 click 间隔只有 75ms，池子不够就会听见「漏拍」—— 那正好是 COMBO 该有的反效果。

const RATE := 22050          # 音效上限 11kHz，够用；采样率减半，生成快一倍
const POOL := 8

## 每种音的基础音量（dB）。click 压得很低是有意的：
## 它一秒要响十几次，响度一高就盖掉 out 那条「数到第几只」的旋律。
const BASE_DB := {
	"click": -17.0,
	"wood": -14.0,
	"out": -8.0,
	"err": -5.0,
	"win": -7.0,
	"ding": -9.0,
}

var master_volume: float = 0.8     # 0..1，设置浮层改这个

var _cache: Dictionary = {}
var _pool: Array[AudioStreamPlayer] = []
var _next: int = 0


func _ready() -> void:
	for i in POOL:
		var p := AudioStreamPlayer.new()
		p.bus = "Master"
		add_child(p)
		_pool.append(p)
	apply_volume()


## 播一个音。semitone 是「比原调高几个半音」—— 同一个流用 pitch_scale 变调，
## 不必为每个音高重新合成一遍（那会在高速时卡帧）。
func play(kind: String, semitone: float = 0.0, db_offset: float = 0.0) -> void:
	if _pool.is_empty():
		return
	var st: AudioStreamWAV = _stream(kind)
	if st == null:
		return
	var p: AudioStreamPlayer = _pool[_next]
	_next = (_next + 1) % _pool.size()
	p.stream = st
	p.pitch_scale = pow(2.0, semitone / 12.0)
	p.volume_db = float(BASE_DB.get(kind, -10.0)) + db_offset
	p.play()


func set_master_volume(v: float) -> void:
	master_volume = clampf(v, 0.0, 1.0)
	apply_volume()


func apply_volume() -> void:
	var bus: int = AudioServer.get_bus_index("Master")
	if bus < 0:
		return
	var v: float = clampf(master_volume, 0.0, 1.0)
	AudioServer.set_bus_mute(bus, v <= 0.001)
	AudioServer.set_bus_volume_db(bus, linear_to_db(maxf(v, 0.001)))


# ---------------------------------------------------------------- 合成

func _stream(kind: String) -> AudioStreamWAV:
	if _cache.has(kind):
		return _cache[kind]
	var w: AudioStreamWAV = null
	match kind:
		"click":
			w = _note(680.0, 0.036, 1.0, 0.0)
		"wood":
			# 300 + 900 的 1:3 叠加 = 木头的「空腔」感；纯正弦听起来像电子滴
			w = _note(300.0, 0.070, 1.0, 0.42, 3.0)
		"out":
			w = _note(523.25, 0.130, 1.0, 0.28, 2.0)
		"err":
			w = _sweep(370.0, 196.0, 0.170)
		"win":
			w = _arp([523.25, 659.25, 783.99, 1046.5], 0.095)
		"ding":
			w = _note(1568.0, 0.280, 1.0, 0.22, 2.0)
		_:
			return null
	_cache[kind] = w
	return w


## 一个音：正弦（可选叠一条泛音）+ 指数衰减包络。
## 起音给 4ms 而不是 0 —— 直接从满幅开始会「啪」一声，那是爆音不是音效。
func _note(freq: float, dur: float, gain: float, harm: float = 0.0, hmul: float = 2.0) -> AudioStreamWAV:
	var n: int = int(RATE * dur)
	var buf := PackedByteArray()
	buf.resize(n * 2)
	var w: float = TAU * freq / float(RATE)
	var wh: float = w * hmul
	for i in n:
		var t: float = float(i) / float(RATE)
		var s: float = sin(w * float(i))
		if harm > 0.0:
			s += harm * sin(wh * float(i))
		var env: float = minf(t / 0.004, 1.0) * pow(maxf(1.0 - t / dur, 0.0), 2.4)
		buf.encode_s16(i * 2, int(clampf(s * env * gain * 0.62, -1.0, 1.0) * 32000.0))
	return _wrap(buf)


## 频率往下滑：绊倒就是「哎——」往下的那两音，比两个分开的音更连贯
func _sweep(f1: float, f2: float, dur: float) -> AudioStreamWAV:
	var n: int = int(RATE * dur)
	var buf := PackedByteArray()
	buf.resize(n * 2)
	var acc: float = 0.0
	for i in n:
		var u: float = float(i) / float(n)
		var f: float = lerpf(f1, f2, u * u)
		acc += TAU * f / float(RATE)
		var env: float = minf(u / 0.03, 1.0) * pow(maxf(1.0 - u, 0.0), 1.8)
		buf.encode_s16(i * 2, int(clampf(sin(acc) * env * 0.60, -1.0, 1.0) * 32000.0))
	return _wrap(buf)


## 几个音依次排开（过关的「叮-咚-叮」）。每个音自带衰减，接缝处自然归零，不用交叉淡化
func _arp(freqs: Array, step: float) -> AudioStreamWAV:
	var per: int = int(RATE * step)
	var n: int = per * freqs.size()
	var buf := PackedByteArray()
	buf.resize(n * 2)
	for k in freqs.size():
		var f: float = float(freqs[k])
		var w: float = TAU * f / float(RATE)
		for i in per:
			var t: float = float(i) / float(RATE)
			var env: float = minf(t / 0.004, 1.0) * pow(maxf(1.0 - float(i) / float(per), 0.0), 1.6)
			var s: float = sin(w * float(i)) + 0.25 * sin(2.0 * w * float(i))
			buf.encode_s16((k * per + i) * 2,
				int(clampf(s * env * 0.55, -1.0, 1.0) * 32000.0))
	return _wrap(buf)


func _wrap(buf: PackedByteArray) -> AudioStreamWAV:
	var s := AudioStreamWAV.new()
	s.format = AudioStreamWAV.FORMAT_16_BITS
	s.mix_rate = RATE
	s.stereo = false
	s.data = buf
	return s
