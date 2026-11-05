class_name DdRng
extends RefCounted
## 确定性伪随机数发生器：xorshift32 + 乘法散列输出。
##
## 为什么不直接用 RandomNumberGenerator：本项目要用「两套独立实现互相印证」
## 的方式验证伤害公式（GDScript 一份、Python 一份），所以随机序列必须能被
## 逐位复现，不能依赖引擎内部实现。周期 2^32-1，测试用途足够。
##
## 与 tools/ref_impl.py 中的 PythonDdRng 必须保持完全一致。

const MASK32: int = 0xFFFFFFFF
const DEFAULT_SEED: int = 0x9E3779B9
const HASH_FLOAT: int = 2654435761
const HASH_INT: int = 2246822519

var _state: int = DEFAULT_SEED
var draw_count: int = 0


func _init(seed_value: int = DEFAULT_SEED) -> void:
	reseed(seed_value)


func reseed(seed_value: int) -> void:
	_state = seed_value & MASK32
	if _state == 0:
		_state = DEFAULT_SEED
	draw_count = 0


## 32 位截断乘法。拆成 16 位半字相乘，避免 int64 溢出影响低 32 位。
static func _mul32(a: int, b: int) -> int:
	var al: int = a & 0xFFFF
	var ah: int = (a >> 16) & 0xFFFF
	var bl: int = b & 0xFFFF
	var bh: int = (b >> 16) & 0xFFFF
	return (al * bl + (((ah * bl + al * bh) & 0xFFFF) << 16)) & MASK32


func next_u32() -> int:
	var x: int = _state
	x = x ^ ((x << 13) & MASK32)
	x = x ^ (x >> 17)
	x = x ^ ((x << 5) & MASK32)
	_state = x
	draw_count += 1
	return x


## [0, 1)
func next_float() -> float:
	return float(_mul32(next_u32(), HASH_FLOAT)) / 4294967296.0


## [0, n)
func next_int(n: int) -> int:
	if n <= 0:
		return 0
	return _mul32(next_u32(), HASH_INT) % n


## [lo, hi] 含两端
func next_int_range(lo: int, hi: int) -> int:
	if hi <= lo:
		return lo
	return lo + next_int(hi - lo + 1)


func chance(p: float) -> bool:
	if p <= 0.0:
		return false
	if p >= 1.0:
		return true
	return next_float() < p
