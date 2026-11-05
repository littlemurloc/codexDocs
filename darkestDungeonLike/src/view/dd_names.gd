class_name DdNames
extends RefCounted
## id → 中文名的全部映射表（M31 从 dd_theme.gd 拆出来的）。
##
## 为什么单独一个文件：这些表有 700 多行、占了原主题文件的 85%，
## 而它们回答的是「这个东西叫什么」，和「界面用什么颜色、多大字号」
## 是两个完全不同的问题。混在一起时，改一个色板要在一堆怪物名里翻。
##
## 约定：**所有查表函数都在这里**，DdTheme 只管视觉令牌。
## 查不到时一律回退 `pretty()`——宁可显示 Cultist Brawler，
## 也不要显示空字符串或 "unknown"。

## 从 id 造可读文本：cultist_brawler_B → Cultist Brawler，zealous_accusation → Zealous Accusation
static func pretty(id: String) -> String:
	var clean: String = id.replace("_A", "").replace("_B", "").replace("_C", "").replace("_D", "")
	var parts: Array = []
	for p in clean.split("_"):
		var s: String = str(p)
		if s.length() > 0:
			parts.append(s.substr(0, 1).to_upper() + s.substr(1))
	return " ".join(parts)


## 四个区域的中文名与一句定位（M20）。
##
## 数据里 `dungeons.json` 的 encounters / maps / props 全是按区域分开的，
## 但 M7~M19 一直硬编码 `weald`，另外三个区域的内容从没露出来过。
## 这里的「定位」一句是从各自的遭遇表归纳的，不是原版文案。
const DUNGEON_NAMES: Dictionary = {
	"weald": "荒野",
	"crypts": "墓穴",
	"warrens": "猪人巢穴",
	"cove": "海湾",
	"darkestdungeon": "至暗之地",
}

const DUNGEON_TAGS: Dictionary = {
	"weald": "野兽与土匪 · 硬碰硬",
	"crypts": "骷髅与死灵 · 抗性高",
	"warrens": "肮脏拥挤 · 数量多",
	"cove": "鱼人与深海 · 控制多",
	"darkestdungeon": "终局",
}


static func dungeon_name(id: String) -> String:
	return str(DUNGEON_NAMES.get(id, pretty(id)))


static func dungeon_tag(id: String) -> String:
	return str(DUNGEON_TAGS.get(id, ""))


## 英雄中文名（M21）。15 个全给——名册里只有 5 个，但 M20 之后随时会换人上场，
## 而英文名在中文 UI 里读起来就是「这游戏没做完」。
const HERO_NAMES: Dictionary = {
	"crusader": "十字军",
	"highwayman": "强盗",
	"vestal": "修女",
	"plague_doctor": "瘟疫医生",
	"man_at_arms": "战争老兵",
	"abomination": "憎恶",
	"antiquarian": "古董商",
	"arbalest": "弩手",
	"bounty_hunter": "赏金猎人",
	"grave_robber": "盗墓贼",
	"hellion": "蛮女",
	"houndmaster": "驯犬师",
	"jester": "小丑",
	"leper": "麻风病人",
	"occultist": "神秘学者",
}

## 怪物中文名（M21）。
##
## **key 是不带难度后缀的基础 id**：同一个怪在 A/B/C 三档只是数值不同，
## 名字该一样。所以查表前先把 `_A/_B/_C/_D` 去掉。
##
## 只覆盖「四个区域的遭遇池里真的会出现的」58 个基础怪 + 21 个首领
## （其中 8 个两者都算）。没收录的回退 `pretty()`——
## 宁可显示英文，也不要为了凑数编一个错的名字。
const MONSTER_NAMES: Dictionary = {
	"bloated_corpse": "臃肿腐尸",
	"brigand_blood": "血匪",
	"brigand_cutthroat": "土匪刀客",
	"brigand_fusilier": "土匪火枪手",
	"brigand_hunter": "土匪猎手",
	"brigand_raider": "土匪劫掠者",
	"carrion_eater": "食腐兽",
	"carrion_eater_big": "巨食腐兽",
	"carrion_eater_large": "大型食腐兽",
	"shambler": "蹒跚者",
	"collector": "收藏家",
	"crone": "干瘪老妪",
	"cultist_brawler": "邪教打手",
	"cultist_witch": "邪教女巫",
	"drowned_pirate": "溺亡海盗",
	"ectoplasm": "灵质",
	"ectoplasm_large": "大型灵质",
	"fishman_crabby": "蟹甲鱼人",
	"fishman_harpoon": "鱼叉鱼人",
	"fishman_shaman": "鱼人萨满",
	"fungal_artillery": "菌人炮手",
	"fungal_bloat": "菌人胀者",
	"gargoyle": "石像鬼",
	"ghoul": "食尸鬼",
	"jellyfish": "水母",
	"madman": "疯汉",
	"maggot": "蛆虫",
	"octotank": "巨型章鱼",
	"rabid_dog": "疯狗",
	"skeleton_arbalist": "骷髅弩手",
	"skeleton_bearer": "骷髅抬棺者",
	"skeleton_captain": "骷髅队长",
	"skeleton_common": "骷髅兵",
	"skeleton_courtier": "骷髅廷臣",
	"skeleton_defender": "骷髅盾卫",
	"skeleton_militia": "骷髅民兵",
	"skeleton_spear": "骷髅矛手",
	"snail_urchin": "海胆蜗牛",
	"spider_spitter": "喷毒蜘蛛",
	"spider_webber": "结网蜘蛛",
	"swine_drummer": "猪人鼓手",
	"swine_reaver": "猪人劫掠者",
	"swine_skiver": "猪人剥皮者",
	"swine_slasher": "猪人砍杀者",
	"swine_wretch": "猪人贱种",
	"swinetaur": "猪人半人马",
	"unclean_giant": "不洁巨汉",
	"virago_hateful": "怨毒悍妇",
	# —— 首领 ——
	"brigand_cannon": "土匪炮车",
	"brigand_fuseman": "土匪火铳手",
	"cauldron_empty": "空坩埚",
	"crow": "乌鸦",
	"drowned_captain": "溺亡船长",
	"formless_guard": "无定形·守卫",
	"formless_melee": "无定形·斗士",
	"formless_ranged": "无定形·射手",
	"formless_weak": "无定形·幼体",
	"hag": "沼泽老妪",
	"necromancer": "死灵法师",
	"nest": "巢",
	"pew_small": "小长椅",
	"pew_medium": "中长椅",
	"pew_large": "大长椅",
	"prophet": "先知",
	"siren": "海妖",
	"swine_piglet": "猪人仔",
	"swine_prince": "猪人王子",
}


## 去掉难度后缀。`cultist_brawler_B` → `cultist_brawler`。
static func monster_base(id: String) -> String:
	for suf in ["_A", "_B", "_C", "_D"]:
		if id.ends_with(suf):
			return id.substr(0, id.length() - 2)
	return id


static func monster_name(id: String) -> String:
	return str(MONSTER_NAMES.get(monster_base(id), pretty(id)))


static func hero_name(hid: String) -> String:
	return str(HERO_NAMES.get(hid, pretty(hid)))


## 战斗/日志里要显示「这是谁」时统一的入口：先认英雄，再认怪物，都不认识才回退。
static func unit_name(id: String) -> String:
	if HERO_NAMES.has(id):
		return str(HERO_NAMES[id])
	var b: String = monster_base(id)
	if MONSTER_NAMES.has(b):
		return str(MONSTER_NAMES[b])
	return pretty(id)


## 战斗技能中文名（M19）。
##
## 只覆盖当前名册里的 5 个职业（35 个技能）；其余 10 个职业回退 `pretty()`。
## 不一次翻完 105 个，是因为还没上场的职业翻了也没法验对——
## M20 开新英雄时照这张表补，回退分支保证「没翻也能显示」。
const SKILL_NAMES: Dictionary = {
	"smite": "惩击",
	"zealous_accusation": "狂热指控",
	"stunning_blow": "眩晕重击",
	"bulwark_of_faith": "信仰壁垒",
	"battle_heal": "战地治疗",
	"holy_lance": "圣枪",
	"inspiring_cry": "鼓舞呐喊",
	"wicked_slice": "邪恶斩击",
	"pistol_shot": "手枪射击",
	"point_blank_shot": "抵近射击",
	"grape_shot_blast": "霰弹轰击",
	"take_aim": "瞄准",
	"duelist_advance": "决斗突进",
	"opened_vein": "割开血管",
	"mace_bash": "钉锤猛击",
	"judgement": "审判",
	"dazzling_light": "炫目圣光",
	"divine_grace": "神圣恩典",
	"gods_comfort": "神之抚慰",
	"gods_illumination": "神启",
	"gods_hand": "神之手",
	"noxious_blast": "毒气喷发",
	"plague_grenade": "瘟疫手雷",
	"blinding_gas": "致盲瓦斯",
	"incision": "切开",
	"battlefield_medicine": "战地医术",
	"emboldening_vapours": "鼓舞蒸气",
	"disorienting_blast": "迷乱冲击",
	"crush": "碾压",
	"rampart": "壁垒",
	"bellow": "怒吼",
	"defender": "守护",
	"retribution": "反击",
	"command": "号令",
	"bolster": "振奋",
	# —— 以下 10 个职业是 M31 补的 ——
	# 原来这张表只有最初 5 个职业的 35 个技能，另外 70 个一直回退成英文。
	# M19 建公会屏时名册还只有 5 个人，所以看不见；M27 名册能招到 15 个职业之后，
	# 招进第 6 个职业就会在技能组里看到 `+ Manacles` 这种英文。
	"transform": "变身",
	"manacles": "镣铐",
	"vomit": "呕血",
	"absolution": "赦罪",
	"rake": "撕抓",
	"rage": "狂怒",
	"slam": "猛击",
	"kris_stab": "短剑突刺",
	"festering_vapours": "腐臭蒸气",
	"cower": "畏缩",
	"flashpowder": "闪光粉",
	"fortifying_vapours": "坚壁蒸气",
	"invigorating_vapours": "提神蒸气",
	"protect_me": "护着我",
	"sniper_shot": "狙击射击",
	"suppressing_fire": "压制射击",
	"sniper_mark": "狙击标记",
	"bola": "绊索",
	"blindfire": "盲射",
	"battlefield_bandage": "战地绷带",
	"flare": "照明弹",
	"collect_bounty": "收取赏金",
	"target_tag": "标记目标",
	"come_hither": "过来",
	"uppercut": "上勾拳",
	"flashbang": "闪光弹",
	"finish_him": "了结他",
	"hook_and_slice": "钩爪切割",
	"pick": "刺脸",
	"lunge": "突进",
	"flashing_daggers": "飞刀连闪",
	"shadow_fade": "隐匿",
	"thrown_dagger": "投掷匕首",
	"poison_dart": "毒镖",
	"toxin_trickery": "淬毒诡计",
	"wicked_hack": "凶蛮劈砍",
	"iron_swan": "铁天鹅",
	"barbaric_yawp": "蛮嚎",
	"if_it_bleeds": "见血追击",
	"breakthru": "突穿",
	"adrenaline_rush": "肾上腺素",
	"bleed_out": "放血",
	"hounds_rush": "纵犬突袭",
	"hounds_harry": "纵犬骚扰",
	"whistle": "口哨",
	"howl": "嚎叫",
	"guard_dog": "护主犬",
	"lick_wounds": "舔舐伤口",
	"blackjack": "闷棍",
	"dirk_stab": "短匕突刺",
	"harvest": "收割",
	"heroic_end": "英雄谢幕",
	"solo": "独奏",
	"slice_off": "断筋",
	"battle_ballad": "战斗叙事诗",
	"inspiring_tune": "鼓舞曲",
	"chop": "劈砍",
	"hew": "削斫",
	"focus": "凝神",
	"revenge": "复仇",
	"withstand": "忍耐",
	"solemnity": "庄严",
	"intimidate": "恐吓",
	"bloodlet": "放血",
	"abyssal_artillery": "深渊炮击",
	"weakening_curse": "虚弱诅咒",
	"wyrd_reconstruction": "诡异重建",
	"disruptive_curse": "扰乱诅咒",
	"hands_from_abyss": "深渊之手",
	"daemons_pull": "恶魔牵引",
}


static func skill_name(sid: String) -> String:
	return str(SKILL_NAMES.get(sid, pretty(sid)))


## 奇物中文名。
##
## data 里只有英文名（Locked Strongbox），而这一屏全是中文——混排会让
## 「要不要碰这东西」这个判断多一层翻译成本。表按 id 平铺，不用翻译接口：
## 60 条固定内容，比引一层 i18n 便宜。缺项回退到 pretty()，不会显示成空白。
const CURIO_NAMES: Dictionary = {
	"alchemy_table": "炼金台",
	"altar_of_light": "光之祭坛",
	"ancestors_knapsack": "先祖的背包",
	"ancient_coffin": "古老棺木",
	"bandits_trapped_chest": "强盗的陷阱箱",
	"barnacle_crusted_chest": "覆满藤壶的箱子",
	"bas_relief": "浅浮雕",
	"beast_carcass": "野兽尸体",
	"bookshelf": "书架",
	"brackish_tidepool": "咸水潮池",
	"confession_booth": "告解室",
	"cosmic_spiderweb": "宇宙蛛网",
	"crate": "板条箱",
	"decorative_urn": "装饰瓮",
	"dinner_cart": "餐车",
	"discarded_pack": "丢弃的背包",
	"eerie_coral": "怪异的珊瑚",
	"eldritch_altar": "邪秽祭坛",
	"fish_idol": "鱼神像",
	"giant_fish_carcass": "巨鱼尸体",
	"giant_oyster": "巨牡蛎",
	"goal_strongbox": "任务保险箱",
	"heirloom_chest": "传家宝箱",
	"holy_fountain": "神圣喷泉",
	"incursion_knapsack": "入侵者背包",
	"iron_maiden": "铁处女",
	"knife_rack": "刀架",
	"locked_display_cabinet": "上锁的陈列柜",
	"locked_sarcophagus": "上锁的石棺",
	"locked_strongbox": "上锁的保险箱",
	"lost_luggage": "遗失的行李",
	"makeshift_dining_table": "临时餐桌",
	"moonshine_barrel": "私酿酒桶",
	"mummified_remains": "木乃伊遗骸",
	"occult_scrawlings": "神秘涂鸦",
	"old_tree": "老树",
	"open_grave": "敞开的坟墓",
	"pile_of_bones": "骸骨堆",
	"pile_of_scrolls": "卷轴堆",
	"pristine_fountain": "清澈的喷泉",
	"sack": "麻袋",
	"sacrificial_stone": "献祭石",
	"sarcophagus": "石棺",
	"sconce": "壁灯",
	"secret_stash": "秘密藏匿处",
	"shallow_grave": "浅坟",
	"shamblers_altar": "蹒跚者祭坛",
	"ships_figurehead": "船首像",
	"skull_altar": "头骨祭坛",
	"stack_of_books": "书堆",
	"suit_of_armor": "盔甲",
	"thanks_chest": "谢礼箱",
	"travellers_tent": "旅行者帐篷",
	"travellers_tent_tutorial": "旅行者帐篷",
	"troubling_effigy": "令人不安的雕像",
	"tutorial_food": "口粮",
	"tutorial_holy": "圣水",
	"tutorial_key": "钥匙",
	"tutorial_shovel": "铲子",
	"unlocked_strongbox": "未上锁的保险箱",
}

## 补给道具中文名。奇物交互与拾取提示都用它。
const SUPPLY_NAMES: Dictionary = {
	"shovel": "铲子", "torch": "火把", "bandage": "绷带",
	"antivenom": "解毒剂", "medicinal_herbs": "药草",
	"skeleton_key": "骷髅钥匙", "holy_water": "圣水",
	"dog_treats": "狗饼干", "laudanum": "鸦片酊", "firewood": "柴火",
}

## 任务物品（M35）。和补给分开放：这些不能买、不能卖、用完就没了。
##
## 有些任务物品**本身就是补给**（圣水、解毒剂），所以查名字时先看这张表，
## 查不到再退回 `SUPPLY_NAMES`——两边都有的话以任务物品为准，
## 因为屏幕上这个位置说的就是「任务物品」。
const QUEST_ITEM_NAMES: Dictionary = {
	"pickaxe": "镐", "eldritch_lantern": "邪光提灯", "beacon_light": "信标之光",
	"holy_relic": "圣髑", "grain_sack": "粮袋", "medicines": "药材",
	"ancestors_crate": "先祖木箱",
}


static func quest_item_name(id: String) -> String:
	if QUEST_ITEM_NAMES.has(id):
		return str(QUEST_ITEM_NAMES[id])
	return supply_name(id)


const HEIRLOOM_NAMES: Dictionary = {
	"bust": "半身像", "portrait": "画像", "crest": "纹章", "deed": "地契",
}


static func curio_name(id: String) -> String:
	return str(CURIO_NAMES.get(id, pretty(id)))


static func supply_name(id: String) -> String:
	return str(SUPPLY_NAMES.get(id, pretty(id)))


static func heirloom_name(id: String) -> String:
	return str(HEIRLOOM_NAMES.get(id, pretty(id)))


## 怪癖中文名（170 条）。
##
## 全部覆盖、不依赖回退：`quirk_name()` 找不到会退回 pretty()，那是英文
## ——一屏中文里混进一个 "night blindness" 比不显示更难看。
## 所以 test_quirk 里有一条断言要求「170 个 id 全部有中文名」，
## 以后换数据包加了新怪癖，那条断言会先红，而不是让界面默默变英文。
const QUIRK_NAMES: Dictionary = {
	# —— 体格 / 属性 ——
	"tough": "强韧",
	"fragile": "脆弱",
	"hard_skinned": "皮糙肉厚",
	"soft": "皮肉松软",
	"quick_reflexes": "反应敏捷",
	"slow_reflexes": "反应迟钝",
	"quickdraw": "出手敏捷",
	"slowdraw": "出手迟缓",
	"natural_swing": "天生挥砍",
	"the_yips": "手抖",
	"natural_eye": "天生准头",
	"lazy_eye": "眼神不济",
	"evasive": "灵巧闪避",
	"clumsy": "笨手笨脚",
	"slugger": "重击手",
	"torn_rotator_cuff": "肩袖撕裂",
	"unerring": "百发百中",
	"scattering": "射术散乱",
	"accurate": "精准",
	"inaccurate": "失准",
	"precision_striker": "精准打击",
	"weak_grip": "握力不足",
	"eagle_eye": "鹰眼",
	"flawed_release": "脱手过早",
	"nervous": "神经紧张",
	"steady": "沉稳",
	"resilient": "坚韧",
	"ruminator": "反刍思虑",
	"thin_blooded": "血薄",
	"thick_blooded": "血浓",
	"sickly": "体弱多病",
	"robust": "强健",
	"anemic": "贫血",
	"clotter": "凝血异常",
	"fated": "天命所归",
	"hard_noggin": "脑袋硬",
	"shocker": "抗电体质",
	"mercurial": "性情多变",
	"irrepressible": "不屈不挠",
	"unyielding": "宁折不弯",
	"suicidal": "自毁倾向",
	"stout": "魁梧",
	"fast_healer": "愈合迅速",
	"gift_of_the_healer": "医者恩赐",
	"improved_balance": "身法稳健",

	# —— 昼夜 / 光照 ——
	"early_riser": "早起",
	"night_owl": "夜猫子",
	"nocturnal": "夜行性",
	"diurnal": "昼行性",
	"night_blindness": "夜盲症",
	"sensitive_to_light": "畏光",
	"warrior_of_light": "光之战士",
	"lurker": "潜伏者",
	"photomania": "恋光癖",
	"lygophobia": "惧暗",
	"phengophobia": "惧光",

	# —— 战况应激 ——
	"second_wind": "背水一战",
	"tuckered_out": "容易力竭",
	"last_gasp": "垂死挣扎",
	"winded": "气短",
	"on_guard": "严阵以待",
	"off_guard": "疏于防备",
	"clutch_hitter": "逆境强击",
	"dud_hitter": "顺境虚强",
	"stress_faster": "压力易积",
	"stress_eater": "压力贪食",

	# —— 恐惧 / 憎恨 / 杀手 ——
	"zoophobia": "惧兽",
	"thanatophobia": "惧死",
	"satanophobia": "惧魔",
	"automatonophobia": "惧人偶",
	"back_tracker": "爱走回头路",
	"claustrophobia": "幽闭恐惧",
	"fear_of_eldritch": "惧异形",
	"fear_of_unholy": "惧邪秽",
	"fear_of_man": "惧人类",
	"fear_of_beast": "惧野兽",
	"hatred_of_eldritch": "憎异形",
	"hatred_of_unholy": "憎邪秽",
	"hatred_of_man": "憎人类",
	"hatred_of_beast": "憎野兽",
	"slayer_of_eldritch": "异形克星",
	"slayer_of_unholy": "邪秽克星",
	"slayer_of_man": "人类克星",
	"slayer_of_beast": "野兽克星",

	# —— 疾病 ——
	"bad_humours": "体液失调",
	"creeping_cough": "久咳不止",
	"hemophilia": "血友病",
	"the_runs": "腹泻",
	"wasting_sickness": "虚损之症",
	"tetanus": "破伤风",
	"rabies": "狂犬病",
	"syphilis": "梅毒",
	"stomach_cramp": "胃痉挛",
	"bulimic": "暴食症",
	"lethargy": "嗜睡症",
	"spotted_fever": "斑疹热",
	"vertigo": "眩晕症",
	"vampiric_spirits": "嗜血精魂",
	"ennui": "倦怠",
	"the_ague": "疟疾",
	"hysterical_blindness": "癔症性失明",
	"scurvy": "坏血病",
	"the_worries": "忧思成疾",
	"the_fits": "抽搐",
	"tapeworm": "绦虫",
	"the_red_plague": "红瘟",
	"the_black_plague": "黑瘟",

	# —— 奇物癖（mania 系，与奇物标签联动）——
	"dark_temptation": "黑暗诱惑",
	"guilty_conscience": "良心不安",
	"kleptomaniac": "盗窃癖",
	"bloodthirsty": "嗜血",
	"hieromania": "圣物癖",
	"curious": "好奇心重",
	"ablutomania": "洁癖",
	"dacnomania": "撕咬癖",
	"egomania": "自恋",
	"hylomania": "恋物癖",
	"sitiomania": "贪食",
	"plutomania": "贪婪",
	"necromania": "恋尸癖",
	"dipsomania": "嗜酒",
	"paranormania": "灵异癖",
	"demonomania": "魔物癖",
	"hagiomania": "圣徒癖",
	"compulsive": "强迫症",
	"nymphomania": "色欲",

	# —— 乌鸦商队 ——
	"corvids_curiosity": "鸦之好奇",
	"corvids_appetite": "鸦之食欲",
	"corvids_blindness": "鸦之盲目",
	"corvids_grace": "鸦之优雅",
	"corvids_eye": "鸦之锐眼",
	"corvids_resilience": "鸦之坚韧",

	# —— 城镇 / 营地 ——
	"alcoholism": "酗酒",
	"gambler": "赌徒",
	"bad_gambler": "赌运不济",
	"skilled_gambler": "赌术精湛",
	"love_interest": "情之所钟",
	"enlightened": "开悟",
	"god_fearing": "敬神",
	"flagellant": "苦修",
	"resolution": "意志坚定",
	"known_cheat": "出千老手",
	"deviant_tastes": "异癖",
	"unquiet_mind": "心绪不宁",
	"witness": "目睹者",
	"faithless": "不信神",
	"meditator": "冥想者",
	"calm": "沉着冷静",
	"weapons_haggler": "武器砍价",
	"armor_haggler": "护甲砍价",

	# —— 地牢专精 ——
	"ruins_explorer": "废墟探索者",
	"warren_explorer": "巢穴探索者",
	"weald_explorer": "荒野探索者",
	"cove_explorer": "海湾探索者",
	"ruins_adventurer": "废墟老手",
	"warren_adventurer": "巢穴老手",
	"weald_adventurer": "荒野老手",
	"cove_adventurer": "海湾老手",
	"ruins_scrounger": "废墟搜刮者",
	"warren_scrounger": "巢穴搜刮者",
	"weald_scrounger": "荒野搜刮者",
	"cove_scrounger": "海湾搜刮者",
	"ruins_tactician": "废墟战术家",
	"warren_tactician": "巢穴战术家",
	"weald_tactician": "荒野战术家",
	"cove_tactician": "海湾战术家",
	"ruins_phobe": "废墟恐惧",
	"warren_phobe": "巢穴恐惧",
	"weald_phobe": "荒野恐惧",
	"cove_phobe": "海湾恐惧",
}


static func quirk_name(id: String) -> String:
	return str(QUIRK_NAMES.get(id, pretty(id)))


## 饰品名（490 件）没有可用的显示名。
##
## `trinkets.json` 只有 id / rarity / price / limit / buffs，
## `_raw/all_records.json` 里也没有 localization——**原游戏的饰品名没被抽出来**。
## 所以这里按 id 的词根拼中文：`swift_cloak` → 迅捷 + 斗篷。
## 英文 id 恰好是「形容词 名词」，与中文同序，拼出来能读。
##
## 只覆盖**可掉落的 196 件**用到的词根；294 件 kickstarter 永远不会出现在
## 游戏里，不值得为它们造译名。词根以外的 id 回退 `pretty()`（英文 id），
## 并在 `trinket_name_coverage()` 里报出未覆盖率——宁可显示英文，
## 也不要出现「未知饰品」这种把数据问题藏起来的占位符。
const TRINKET_ROOTS: Dictionary = {
	"accuracy": "准度",
	"agile": "灵敏",
	"agility": "灵巧",
	"amulet": "项链",
	"ancestors": "先祖",
	"antiq": "古物",
	"archers": "弓手",
	"armlet": "臂环",
	"ball": "弹丸",
	"bandana": "头巾",
	"beast": "野兽",
	"berserk": "狂怒",
	"blasphemous": "亵渎",
	"bleed": "流血",
	"bleeding": "流血",
	"blight": "枯萎",
	"blood": "血",
	"bloodied": "血污",
	"bloodthirst": "嗜血",
	"bloody": "血染",
	"book": "书",
	"boots": "长靴",
	"boss": "首领",
	"bottle": "瓶子",
	"bracer": "护腕",
	"brawlers": "斗殴者",
	"bright": "明光",
	"buckle": "扣环",
	"bulls": "公牛",
	"calming": "安抚",
	"camouflage": "伪装",
	"campers": "露营者",
	"candle": "蜡烛",
	"cannon": "加农炮",
	"cap": "帽",
	"cauldron": "坩埚",
	"caution": "谨慎",
	"censer": "香炉",
	"chalice": "圣杯",
	"charm": "护符",
	"chirurgeons": "外科医",
	"cleansing": "净化",
	"cloak": "斗篷",
	"coat": "外套",
	"collar": "项圈",
	"collector": "收藏家",
	"commanders": "指挥官",
	"constitution": "体质",
	"cream": "药膏",
	"crest": "纹章",
	"crew": "船员",
	"critical": "致命",
	"crow": "乌鸦",
	"crown": "王冠",
	"crucifix": "十字架",
	"crystal": "水晶",
	"cudgel": "短棒",
	"cursed": "被诅咒",
	"damage": "伤害",
	"dark": "暗黑",
	"dazzling": "炫目",
	"dd": "至暗",
	"debuff": "削弱",
	"defenders": "防卫者",
	"demons": "恶魔",
	"deteriorating": "衰败",
	"dice": "骰子",
	"disease": "疾病",
	"diseased": "病染",
	"dodge": "闪避",
	"dodgy": "闪避",
	"double": "双重",
	"draw": "拔枪",
	"drifters": "漂泊者",
	"edged": "开刃",
	"eldritch": "邪秽",
	"ethereal": "空灵",
	"evasion": "闪避",
	"eye": "之眼",
	"eyepatch": "眼罩",
	"fasting": "斋戒",
	"feather": "羽毛",
	"fetish": "崇拜物",
	"flashfire": "闪火",
	"flesh": "血肉",
	"focus": "专注",
	"fortifying": "加固",
	"fortunate": "幸运",
	"gamblers": "赌徒",
	"garlic": "大蒜",
	"glove": "手套",
	"gloves": "手套",
	"goblet": "酒杯",
	"greaves": "胫甲",
	"guardians": "守卫",
	"guide": "指南",
	"gunpowder": "火药",
	"hag": "老巫",
	"hairpin": "发簪",
	"handkerchief": "手帕",
	"haste": "迅捷",
	"healing": "治疗",
	"health": "生命",
	"heavens": "天界",
	"heavy": "沉重",
	"hells": "地狱",
	"helmet": "头盔",
	"herb": "药草",
	"heros": "英雄",
	"holiness": "圣德",
	"holy": "神圣",
	"hunters": "猎手",
	"idol": "神像",
	"immunity": "免疫",
	"incense": "熏香",
	"intuition": "直觉",
	"killing": "杀戮",
	"knights": "骑士",
	"lantern": "提灯",
	"legendary": "传说",
	"life": "生命",
	"longevity": "长寿",
	"lucky": "幸运",
	"madman": "疯汉",
	"man": "人",
	"map": "地图",
	"martyrs": "殉道者",
	"mask": "面具",
	"medics": "医者",
	"moon": "月亮",
	"moustache": "胡须",
	"move": "移动",
	"musket": "火枪",
	"necromancer": "死灵法师",
	"oil": "油",
	"orders": "命令",
	"padlock": "挂锁",
	"paralyzers": "麻痹者",
	"pen": "笔",
	"pendant": "吊坠",
	"pistol": "手枪",
	"poisoned": "中毒",
	"poisoning": "淬毒",
	"portrait": "画像",
	"profane": "凡俗",
	"prophet": "先知",
	"protection": "护佑",
	"protective": "护佑",
	"quick": "迅捷",
	"quickening": "加速",
	"rage": "愤怒",
	"raiders": "劫掠者",
	"rampart": "壁垒",
	"reckless": "鲁莽",
	"recovery": "复原",
	"relaxation": "松弛",
	"ring": "指环",
	"rotgut": "劣酒",
	"sacred": "圣洁",
	"sacrificial": "献祭",
	"sanity": "理智",
	"satchel": "挎包",
	"scouting": "侦察",
	"scroll": "卷轴",
	"seal": "印章",
	"seer": "先知",
	"seers": "先知",
	"selfish": "自私",
	"sharpening": "磨刃",
	"sheath": "刀鞘",
	"shield": "盾",
	"shimmering": "微光",
	"signet": "印戒",
	"siren": "塞壬",
	"slayers": "屠戮者",
	"slippery": "滑溜",
	"sly": "狡黠",
	"snake": "蛇",
	"snipers": "狙击手",
	"solar": "日轮",
	"speed": "速度",
	"spiked": "带刺",
	"steady": "沉稳",
	"stone": "石",
	"stun": "眩晕",
	"stunning": "眩晕",
	"sturdy": "坚固",
	"sun": "太阳",
	"surgical": "手术",
	"survival": "生存",
	"swift": "迅捷",
	"swordsmans": "剑客",
	"tailfeather": "尾羽",
	"talisman": "护身符",
	"talon": "爪",
	"tambourine": "铃鼓",
	"tassle": "流苏",
	"tempting": "诱惑",
	"tenacity": "坚毅",
	"tentacle": "触须",
	"tough": "坚韧",
	"trinket": "饰品",
	"unholy": "不洁",
	"unmovable": "不移",
	"vengeful": "复仇",
	"vial": "小瓶",
	"warriors": "战士",
	"weight": "负重",
	"whistle": "哨子",
	"wilbur": "威尔伯",
	"wingfeather": "翼羽",
	"witchs": "女巫",
	"worrystone": "忘忧石",
	"wounding": "致伤",
	"wrathful": "暴怒",
	"youth": "青春",
}


## 把 id 按词根拼成中文。任一词根不认识就整件回退英文 id——
## 半中半英（「迅捷cloak」）比全英文更难读。
static func trinket_name(id: String) -> String:
	if id.is_empty():
		return ""
	var parts: PackedStringArray = id.split("_", false)
	var out: String = ""
	for p in parts:
		var key: String = str(p).to_lower()
		# `of` / `the` 是英文虚词，中文里不出现；纯数字是 `collector_1` 这类
		# 同族编号（数据用它区分三件同名的收藏家饰品），译名里也不需要。
		if key == "of" or key == "the" or key.is_valid_int():
			continue
		if not TRINKET_ROOTS.has(key):
			return pretty(id)
		out += str(TRINKET_ROOTS[key])
	if out.is_empty():
		return pretty(id)
	return out


## 覆盖率自检：给一批 id，返回其中「能拼出中文」的比例。
## 界面上不显示它，但测试拿它当断言——以后换数据包加了新词根，
## 这条会先红，而不是让界面默默退化成英文。
static func trinket_name_coverage(ids: Array) -> float:
	if ids.is_empty():
		return 1.0
	var ok: int = 0
	for id in ids:
		if trinket_name(str(id)) != pretty(str(id)):
			ok += 1
	return float(ok) / float(ids.size())

