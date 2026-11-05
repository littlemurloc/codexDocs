extends SceneTree
## 临时探针：确认六种音都能合成、时长合理、没有爆音（首尾样本接近 0）。

const Sfx = preload("res://scripts/sfx.gd")

func _init() -> void:
	var n := Sfx.new()
	root.add_child(n)
	await process_frame
	var t0: int = Time.get_ticks_msec()
	for k in ["click", "wood", "out", "err", "win", "ding"]:
		var s: AudioStreamWAV = n._stream(k)
		if s == null:
			print("FAIL 合成失败 ", k)
			continue
		var d: PackedByteArray = s.data
		var cnt: int = d.size() / 2
		var first: int = d.decode_s16(0)
		var last: int = d.decode_s16((cnt - 1) * 2)
		var peak: int = 0
		for i in range(0, cnt, 7):
			peak = maxi(peak, absi(d.decode_s16(i * 2)))
		print("%-6s %5.0fms  %5d 样本  首 %6d  尾 %5d  峰 %6d"
			% [k, s.get_length() * 1000.0, cnt, first, last, peak])
	print("合成总耗时 %d ms" % (Time.get_ticks_msec() - t0))
	print("Master bus %d  音量 %.2f" % [AudioServer.get_bus_index("Master"), n.master_volume])
	quit()
