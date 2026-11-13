class_name EnemyVoice
extends RefCounted
## 敌人语音的槽位与映射（M51）。
##
## ## 为什么需要一张表
##
## DD1 的语音样本按**它自己的分组名**命名（`char_en_vo_skel_hurt_01`），
## 而本作的单位 id 是目录名（`skeleton_common_A`）。两边对不上，
## 也不存在能直接读的映射——DD1 走 FMOD event，样本名只在 bank 内部使用，
## `.darkest` / `.fx.darkest` 里没有任何引用（M51 查过）。
##
## 所以这张表是**按名字推的**，不是读出来的。推断依据有两条：
##   1. 分组名的语义（`skel` / `swine` / `fish` / `brig` 一眼能对）
##   2. 分组所在的 bank 就是那个区域的敌人包（`en_crypts` / `en_weald` / …）
##
## **对不上的宁可留空，不要瞎填。** 骷髅发出猪叫，比没有声音糟得多。

## 每个语音种类保留几份变体（`_1` / `_2`）。播放时随机挑一份。
## 只有一份的话，同一只怪连着挨两下会听起来像卡带。
const TAKES: int = 2

## family（id 去掉 `_A`/`_B` 这种变体后缀）-> 语音分组。
## 没列出的 family 一律静音。
const FAMILY_GROUP: Dictionary = {
	# —— 墓穴 ——
	"skeleton_common": "skel",
	"skeleton_militia": "skel",
	"skeleton_spear": "skel",
	"skeleton_defender": "skel",
	"skeleton_arbalist": "skel",
	"skeleton_courtier": "skel",
	"skeleton_captain": "sklcap",
	"skeleton_bearer": "skelbearer",
	"necromancer": "nec",
	"prophet": "prophet",

	# —— 荒野：邪教徒、老妇、巨人 ——
	"cultist_witch": "cultist_f",
	"cultist_harpy": "cultist_f",
	"cultist_brawler": "cultist_m",
	"cultist_warlord": "cultist_m",
	"cultist_orgiastic": "cultist_orgiastic",
	"cultist_shrouded": "cultistshrouded",
	"crone": "crone",
	"hag": "hag",
	"virago_hateful": "virago",
	"virago_shroom": "viragoshroom",
	"unclean_giant": "uncgi",
	"crow": "crow",
	"nest": "nest",

	# —— 荒野 / 海湾共用的「腐肉」「狗」「石像鬼」 ——
	"carrion_eater": "carrionsmall",
	"carrion_eater_big": "carrionlarge",
	"ghoul": "carrionsmall",
	"rabid_dog": "rbdog",
	"gargoyle": "garg",
	"collector": "collector",
	"collector_battle": "collector",
	"collector_protect": "collector",
	"collector_shaman": "collector",

	# —— 土匪 ——
	"brigand_raider": "brig_1",
	"brigand_cutthroat": "brig_1",
	"brigand_blood": "brig_1",
	"brigand_hunter": "brig_2",
	"brigand_sapper": "brig_2",
	"brigand_fuseman": "brig_2",
	"brigand_fusilier": "brig_2",
	"brigand_cannon": "brigcannon",

	# —— 巢穴：猪人 ——
	"swine_wretch": "swine_1",
	"swine_piglet": "swine_1",
	"swine_slasher": "swine_2",
	"swine_reaver": "swine_2",
	"swine_skiver": "swine_2",
	"swine_drummer": "swine_2",
	"swine_prince": "swine_3",
	"swinetaur": "swine_3",
	"formless_weak": "form",
	"formless_melee": "form",
	"formless_ranged": "form",
	"formless_guard": "form",
	"madman": "madman",

	# —— 海湾：鱼人、溺亡者、海妖 ——
	"fishman_harpoon": "fish_1",
	"fishman_shaman": "fish_1",
	"fishman_crabby": "fish_2",
	"drowned_captain": "drowncap",
	"drowned_pirate": "zombie_2",
	"drowned_anchor": "zombie_2",
	"drowned_anchored": "zombie_2",
	"siren": "siren",
	"bloated_corpse": "zombie_1",

	# —— 软体 / 虫类（分组名对不上，按叫声类型就近归类） ——
	"ectoplasm": "slime_1",
	"ectoplasm_large": "slime_2",
	"fungal_bloat": "slime_1",
	"fungal_artillery": "slime_2",
	"maggot": "bug_2",
	"spider_spitter": "bug_1",
	"spider_webber": "bug_1",
	"snail_urchin": "bug_2",
	"octotank": "bug_2",
	"jellyfish": "bug_2",

	# —— 至暗 / 特殊 ——
	"shambler": "shambler",
	"shambler_tentacle": "shamtent",
	"templar_melee": "templar",
	"templar_melee_mb": "templar",
	"templar_ranged": "templar",
	"templar_ranged_mb": "templar",
	"errant_flesh_bat": "fleshbat",
	"errant_flesh_dog": "fleshdog",
	"ancestor_heart": "ancestor_heart",
	"ancestor_pod": "ancestor_pod",
}


## `skeleton_common_A` -> `skeleton_common`。
## 变体后缀固定是一个大写字母（`_A`–`_E`），不是任意末段——
## 用「去掉最后一个下划线段」会把 `carrion_eater_big_A` 削成 `carrion_eater`。
static func family_of(def_id: String) -> String:
	var s: String = str(def_id)
	var cut: int = s.rfind("_")
	if cut > 0 and s.length() - cut == 2:
		var tail: String = s.substr(cut + 1, 1)
		if tail >= "A" and tail <= "Z":
			return s.substr(0, cut)
	return s


## 这个单位该用哪个语音组；没有就返回空串（= 静音）。
static func group_of(def_id: String) -> String:
	return str(FAMILY_GROUP.get(family_of(def_id), ""))


## 槽位名（不含扩展名）：`voice/skel_hurt`。播放端再拼 `_1` / `_2` 挑变体。
## 没有对应分组时返回空串。
static func slot(def_id: String, kind: String) -> String:
	var g: String = group_of(def_id)
	if g.is_empty():
		return ""
	return "voice/%s_%s" % [g, kind]


## 有几个分组只录了某几种叫声（`cultist_orgiastic` 只有 aggro、`viragoshroom` 只有 hurt）。
## 缺某种时退到这里的「补位分组」，而不是让那一击彻底没声——
## 一只怪被打时安静、死时却叫，听起来像 bug。
const FALLBACK: Dictionary = {
	"cultist_orgiastic": "cultist_m",
	"viragoshroom": "virago",
	"brigcannon": "brig_2",
	"shamtent": "shambler",
	"madman": "cultist_m",
}


## 主分组缺这一种叫声时用的备用槽位；没有就返回空串。
static func fallback_slot(def_id: String, kind: String) -> String:
	var alt: String = str(FALLBACK.get(group_of(def_id), ""))
	if alt.is_empty():
		return ""
	return "voice/%s_%s" % [alt, kind]


## 怪物攻击声的变体数（M52）。
## 每个组导出最多 3 个「像打人」的动作，随机播——比固定一个动作有变化。
const ATTACK_TAKES: int = 3


## 这组怪物的攻击声槽位：`atk/<family>`。
##
## 按 **family** 而不是语音分组：攻击声的素材是按 DD1 的怪物组录的
## （`char_en_sklcom_cudgel`），和语音那套分组名不是一回事。
## 没有素材的组（道具、尸体）不特判——`play_variant` 找不到文件会返回 false，
## 调用方退到通用 impact。这样加素材是纯数据操作，不用改代码。
static func attack_slot(def_id: String) -> String:
	return "atk/" + family_of(def_id)
