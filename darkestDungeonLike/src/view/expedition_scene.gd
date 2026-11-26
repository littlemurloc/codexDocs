extends Control
## 可玩的远征循环：出发 → 地图 → 战斗 → 结算。
##
## 为什么要有这一层：M1/M2/M3 都是「测量」，能证明规则对、数值成立，
## 但证明不了「有没有人愿意再打一趟」。那件事只能让人真的玩一次才知道。
##
## 设计约束（刻意的）：
##   1. 全程自绘，不用任何外部素材 —— 换美术时不需要重写布局
##   2. 不做地图生成、不做城镇、不做饰品 —— 只做「一趟远征」的最小闭环
##   3. 所有规则都来自 src/core，这里一格判定都不写
##
## 操作：
##   鼠标点按钮 / 点敌人 = 选技能与目标
##   空格 = 自动代打一回合（调试用）   F = 点火把   C = 休整   Esc = 撤退
##
## 自检用参数：
##   --auto            让 AI 一路代打，用于截图与冒烟
##   --shot=<路径>     第 --shot-at 秒截图后退出

## 状态号只追加不插队（M46）：`S_VICTORY` 放在末尾而不是「逻辑上该在 S_RESULT 后面」的位置。
## 中间插入会让后面所有的编号 +1，而编号被写进了 `--dev` 的打印和若干自检断言里，
## 换一次状态就得跟着改一遍。追加是唯一不产生连带改动的改法。
enum { S_TOWN, S_MAP, S_BATTLE, S_RESULT, S_TRINKET, S_PREP, S_SHOP, S_GUILD, S_BUILDING, S_VICTORY, S_MENU, S_SETTINGS, S_GATE, S_ROSTER, S_BATTLE_END, S_ROOM, S_PARTY }

## 一步的间隔（M65：0.34 → 0.38）。
##
## 它必须**大于**出招姿势时长（POSE_TIME 0.34）。原来 0.34 对 0.42，
## 下一个单位开始行动时上一个的挥击还没播完 —— 多人回合里每一下动作
## 都被切掉尾巴。没有拉到 0.44：一场战斗每轮 7 个单位，多 0.1 秒
## 就是每轮多 0.7 秒，手感会从「利落」变成「拖」。
const STEP_DELAY: float = 0.38
const LOG_MAX: int = 200

# —— 可选场景 ——
var _dungeon: String = "weald"
var _size: String = "short"
var _level: int = 1
var _preset: String = "standard"

# —— 运行时 ——
var db: DdDb
var exp: Expedition
var _state: int = S_TOWN
## 城镇饰品界面里「正在挑的那一件」。空 = 没选中。
## 有选中时点英雄的空槽＝装上去，否则点槽＝卸下来。
var _sel_trinket: String = ""

## —— 出发准备（M16）——
## 选好的补给。键是 Shop 的 id（食物用 `food`），值是份数。
## 默认给的是「保底包」，和 M13 之前硬编码的默认完全一致——
## 所以第一趟（没钱）的体验和以前一模一样。
var _prep_pack: Dictionary = {}
## 商店分页（M66）：0 饰品 / 1 补给。
## 原来这一屏只有饰品，而玩家对这一屏的期待是「城镇的商店」。
var _shop_tab: int = 0
var _prep_size: String = "short"
var _prep_level: int = 1
## 这次出发带谁。空 = 用 `campaign.default_party()`（名册前 4 个活人）。
var _prep_party: Array = []

## 公会屏当前选中的英雄（M19）。空 = 进屏时自动取名册第一个活人。
var _guild_hero: String = ""
## 准备屏当前的任务类型（M20）：explore / kill_boss。
var _prep_quest: String = "explore"

## —— 城镇建筑（M22）——
##
## 原版八座。前四座是「换个入口」——逻辑 M5/M13/M15/M16/M19 就有了，
## 只是按钮原来散落在英雄卡和右下角；后四座是这一期新写的规则。
##
## `act` 是进屏后右侧给出的动作 id，空表示「进去只有展示或子入口」。
const BUILDINGS: Array = [
	["coach", "马车", "招募"],
	["smith", "铁匠铺", "升级装备"],
	["guild", "公会", "技能组"],
	["sanitarium", "疗养院", "治病 · 清怪癖"],
	["abbey", "修道院", "减压 40"],
	["tavern", "酒馆", "减压 70"],
	["wagon", "商队", "饰品 · 补给"],
	["graveyard", "墓园", "阵亡记录"],
]

## 城镇场景里的 8 座建筑（M64）。
##
## 坐标直接来自布局编辑器导出的 JSON：`[id, x, 底边 y, 显示高度, 水平镜像, 是否在前景层之上]`。
## 坐标是**布局画布**（750×1334）里的绝对像素，画布顶端 = 物理屏顶端。
## 屏幕坐标 = 画布坐标 − 实际 `_safe_top`（不是写死的 80）—— 见 `_town_canvas_rect()`。
## 想重排不要改这里 —— 用 docs/town_layout_editor.html 摆完把 JSON 发过来。
const TOWN_SLOTS: Array = [
	["guild",       18,  638, 303, false, false],
	["abbey",      284,  639, 243, true,  false],
	["sanitarium", 498,  660, 363, false, false],
	["graveyard",  110,  737, 140, false, true],
	["coach",      321,  869, 158, false, true],
	["tavern",     538,  902, 328, false, true],
	["smith",      -46, 1064, 250, false, false],
	["wagon",      429, 1183, 245, false, true],
]
## 各建筑需要完成多少个任务才开放（M123）。
##
## 数值照抄原版 `campaign/town/buildings/*/*.building.json` 里的
## `requirements.number_of_quests_finished`：
##   马车/墓园/商队 0、修道院/酒馆 2、铁匠/公会 3、疗养院 4。
##
## 开局只开三个是原版的设计意图 —— 第一趟必须硬扛着打完，
## 回来才有减压的地方。这不是「漏做」，是难度曲线的一部分。
const BLD_UNLOCK: Dictionary = {
	"coach": 0, "graveyard": 0, "wagon": 0,
	"abbey": 2, "tavern": 2,
	"smith": 3, "guild": 3,
	"sanitarium": 4,
}

## 布局画布的高度（编辑器导出的坐标都以它为准）
const TOWN_CANVAS_H: float = 1334.0

## 底部 dock 的尺寸（M67：从全宽大栏改成**居中窄栏**）。
##
## 原来 188 高、三颗圆 92/118，横贯整个屏幕宽度 —— 按钮确实醒目，
## 但它把铁匠铺、商队、酒馆的下半截全挡住了，而城镇这一屏的主要内容
## 就是那八栋楼。所以这次反过来：栏宽收到 264（约屏幕 1/3），
## 圆缩到 26/32，高度降到 128，两侧露出场景。
##
## 教训：dock 是「导航」，不该和「内容」抢面积。上一轮放大按钮方向没错，
## 错在把它做成了通栏。
const DOCK_H: float = 128.0
const DOCK_W: float = 344.0

## 实际生效的布局（M64）。默认用上面的常量，`--layout=xxx.json` 会覆盖它。
##
## 读取的是布局编辑器导出的那份 JSON，字段一一对应，
## 所以「摆位置」这件事不需要改代码、也不需要重新编译。
var _town_slots: Array = TOWN_SLOTS.duplicate(true)
## `--layout=docs/town_layout.json`：相对路径按项目根解析。
var _want_town_layout: String = ""

var _building: String = ""       ## 当前进的建筑 id
var _building_hero: String = ""  ## 建筑屏里选中的英雄
## 待确认解雇的 hid（M28）。非空时马车上的按钮变成「再点一次确认」。
##
## 自绘 UI 没有弹窗，而解雇是**不可逆且清空投入**的操作——
## 一个按钮点错就把练了十趟的人删了。所以用「点两次」代替确认框：
## 第一次不执行任何事，第二次才真的删。
var _fire_pending: String = ""

## —— 自动代打的走路策略（M18）——
##
## 默认 False = **直奔目标的最短路径**。这条路径是自检的基线，
## 也是「最少步数能走到哪」，但它**不代表玩家**——玩家会绕路拿东西。
##
## 打开之后优先走没去过的、且不增加「到目标距离」的邻居（侧向支线），
## 走完了再回最短路径。用来回答「绕路到底有没有回报」。
var _explore: bool = false
var _seen_rooms: Dictionary = {}
var _battle: Battle = null
var _ev_pos: int = 0
var _exp_ev_pos: int = 0
var _step_timer: float = 0.0
var _options: Array = []
var _pending: Dictionary = {}
## 撤退上膛（M65）：战斗里撤退等于丢掉整趟，必须按两下。
## 和名册删除的 `_fire_pending` 是同一套做法——第一次只是「举起来」，
## 任何别的操作都会把它放下。
var _retreat_arm: bool = false
## 正在看详情的单位（M65 续）。-1 = 没打开。
## 非瞄准态点单位打开，点同一单位或空白关闭。
var _info_uid: int = -1
## 房间叙事（M74）：奇物房间进门先停一张卡，点「走进去」才结算。
var _room_step: Dictionary = {}
var _room_kind: String = ""
var _room_room: int = 0
var _room_phase: int = 0          # 0 = 抵达，1 = 结果
var _room_lines: Array = []
## 地图横幅（M75）：走廊陷阱 / 路障 / 空房间的提示条。
##
## 为什么不弹卡：这些东西一路上会遇到好多次，每次都要点一下「继续」，
## 探索就变成了点按钮。横幅 1.7 秒自动淡出，不拦操作。
var _map_banner_t: float = 0.0
var _map_banner_title: String = ""
var _map_banner_sub: String = ""
var _map_banner_col: Color = Color("#8b8a84")
## 横幅的纵向位置（M76）。原来贴着网格顶，网格挪到下半屏之后会盖住第一行房间；
## 现在压在**日志条**的位置 —— 消息本来就该出现在那里，1.7 秒后日志自己回来。
var _map_banner_y: float = 966.0
## 事件弹窗（M194）。和横幅的区别是**要玩家点一下才走**。
##
## 用户原话：「类似这样的事件提示，能不能也做成一个弹窗的提示，
## 需要玩家点击下【确定】按钮来表达知道这件事了。类似的遭遇战也一样，
## 碰到了先给个弹窗描述提示，玩家点【确定】后才会进入战斗。」
##
## 分工：**有代价或有收获的**（奇物、陷阱、路障、遭遇）走弹窗 ——
## 玩家必须真的看见，不然后面掉血、捡到东西都不知道为什么。
## **纯叙事没后果的**（空房间）继续用横幅，1.7 秒自己淡出，不打断节奏。
var _dlg_open: bool = false
var _dlg_title: String = ""
var _dlg_body: String = ""
var _dlg_sub: String = ""
var _dlg_col: Color = Color("#8b8a84")
## 点完「确定」之后要做的事。空 = 什么都不做（纯提示）。
## 用 Callable 而不是字符串动作名：遭遇战要带着已经建好的 `_battle` 往下走，
## 字符串得再绕一圈存参数，容易存丢。
var _dlg_next: Callable = Callable()
var _dlg_btn: Rect2 = Rect2()
## 截屏用（M194）：进地图后立刻弹一个事件框，用来验样式和位移。
## 真实事件要走到奇物/陷阱才会触发，那一步的随机性太大，验收截图等不起。
var _dlg_demo: bool = false
var _dlg_demo_done: bool = false
## 截屏用（M201）：直接把一张英雄卡的长按浮层钉在屏幕上。
## 长按要按住 0.45 秒，命令行没法模拟"按住不动"，只能这样验样式。
var _hold_demo: bool = false
var _hold_demo_done: bool = false
## 地图平移（M78）。格子固定 120 之后内容会超出面板，靠拖拽看。
var _map_pan: Vector2 = Vector2.ZERO
## true = 下次绘制时把当前房间居中（进新房间时重置）。
## 玩家一拖就关掉，直到下一间房——不然「我想多看两眼这边」会被强行拉回去。
var _map_pan_auto: bool = true
var _map_drag: bool = false
var _map_drag_pos0: Vector2 = Vector2.ZERO
var _map_drag_pan0: Vector2 = Vector2.ZERO
var _map_drag_moved: bool = false
var _map_bounds: Vector2i = Vector2i(1, 1)
var _map_rect: Rect2 = Rect2()
var _map_pan_lock: bool = false
var _map_layer: Control = null
var _card_layer: Control = null
## 当前绘制目标（M80）。地图画在独立子节点上（为了 clip），
## 但绘制辅助函数（_text/_panel/_hit_overlay/_edge_badge）都是按 self 写的。
## 这里用一个「当前目标」把它们统一指过去：默认 self，进地图层时临时改。
var _draw_target: CanvasItem = null


## 绘制目标：进了地图层就画它，否则画自己。
func _dci() -> CanvasItem:
	return _draw_target if _draw_target != null else self
## 行动序（M65）：规则层每轮 emit 一次 `order`，这里存本轮的 uid 顺序。
## `_order_cur` 是「轮到第几个」，由 `turn` 事件推进。
var _order_ids: Array = []
## 守护表现（M200）：守护者 uid → {toward: 被守护者 uid, t: 剩余秒}；
## 被守护者 uid → {blocked: true, t}。只影响绘制，规则层不知道它的存在。
var _guard_fx: Dictionary = {}
var _order_cur: int = -1
## 战斗结算卡（M65）：打赢之后先停一屏，把这一场拿到了什么摆出来。
## 以前是 0.45 秒后直接切回地图，正反馈只剩日志里一行滚过去的字。
var _be_data: Dictionary = {}
var _be_timer: float = 0.0
## 遭遇横幅（M65）：进战斗后 1.4 秒内显示「遇见了谁」。
var _banner_t: float = 0.0
var _move_mode: bool = false       # 技能面板切到「选落点」状态
var _show_move_demo: bool = false  # 截屏用：一进战斗就展开落点列表
var _show_guard_demo: bool = false # 截屏用：让守护者守一次后冻住画面
## 截屏用（M192）：强制当前房间显示「互动」标签。
## 呼吸缩放是**逐帧变化**的，静态截图看不出来，必须能稳定复现同一屏
## 再按不同 `--shot-at` 各截一张对比。靠真实走位很难停在门口：
## 地图每次出发都重新生成，房间号随机，`--click=room:N` 会直接进去。
var _show_interact: bool = false
var _guard_demo_done: bool = false
var _move_checked: bool = false    # 自检：站位调整路径是否已跑过
var moved_ok: bool = false         # 自检：那次调整是否真的改变了 rank
var _guard_checked: bool = false   # 自检：守护路径是否已跑过
var guarded_ok: bool = false       # 自检：那次守护是否真的建立了关系
## 自检：整趟里由技能造成的位移 / 洗位次数（M11）。
## 和守护不同，这一项玩家控制不了——怪物推不推人取决于遭遇里有没有带
## 位移技能的怪，所以它只报数，不参与 PASS/FAIL 判定。
var forced_moves: int = 0
var shuffle_moves: int = 0
var move_resists: int = 0
## 自检：整趟里的召唤次数（M12）。同位移，只报数不判 PASS——
## 路上有没有召唤怪由地图决定，不是玩家能选的。
var summons: int = 0
var summon_fails: int = 0
var _font: Font
var _mouse: Vector2 = Vector2.ZERO
var _log: Array = []           # {text, color}
var _floaters: Array = []
var _buttons: Array = []       # {rect, id, enabled, label}
var _slots: Array = []         # {rect, uid, side}

## 单位贴图（M36）。槽位与规格见 `unit_art.gd` 头部。
var _art: UnitArt = UnitArt.new()
## 界面贴图槽位（M40）。`--no-skin` 会把它整个关掉，退回自绘。
var _skin: UiSkin = UiSkin.new()
## 光照的可见范围层（M44）。`--no-light` 关掉，用于对照。
var _light: LightLayer = LightLayer.new()
## 战斗背景（M45）。`--no-bg` 关掉，回到纯色，用来判断某个「看不清」是不是背景造成的。
var _bg: BattleBg = BattleBg.new()
## 背景音乐（M49）。
var _music: BgMusic = null
## 上一帧请求的曲目。用来做「状态变了才切歌」，而不是每帧重设 stream。
var _music_want: String = ""
## 画面上**当前**的光照值，朝 `exp.light` 平滑跟随。
##
## 直接读 exp.light 的话，点火把是「瞬间从 30 跳到 90」——画面闪一下，
## 玩家读到的是一次 UI 刷新，而不是「火把烧起来了」。
## 用 1 秒左右的跟随，那一下才有重量。
var _light_vis: float = 100.0
## 音效（M43）。`--mute` 关掉。别的不管——音频和视觉完全解耦，
## 不会因为它晚接而返工。
var _sfx: Sfx = null
## 受击抖动剩余时间：uid -> 秒。补间的输入之一，由伤害飘字触发。
var _hit_t: Dictionary = {}
const HIT_TIME: float = 0.22

# —— 战斗站位（M38：站桩）——
#
# rank 换算成 x，阵营决定站在哪条地面线上。
# 目标位置由 `_battle_slot_x` 给，实际 x 由 `_slot_anim` 插值——
# 位移才有「滑过去」的过程。
## M58 竖屏：敌方在上、我方在下，两条地面线之间留 90 给中缝。
## 竖屏的纵向空间比横屏多得多，所以人物可以放大到 210（横屏只能给 180）。
const GROUND_ENEMY: float = 348.0
## 我方地面线（M69：652→690，M70：690→716）。
##
## 血条搬到头顶之后，我方那排状态块离敌方立绘底太近，读起来像
## 「上面那排怪的属性」延伸下来。下移之后两军之间空出 72px：
## 一半给分隔，一半给战斗信息条（轮数 / 光照 / 操作提示）。
## 代价是战场纵向矮了 64px，但下方那块（我方脚底 ~ 日志条）本来就空着。
const GROUND_PARTY: float = 716.0
## **全局导航栏**高度（M163）。和城镇里那个 `DOCK_H`（建筑入口，128）
## 是两回事：那个是「去酒馆/铁匠铺/商队」，这个是「去名册/队伍/商店」。
## 导航栏贴屏幕最底，建筑 dock 整体上移 NAV_H 让出位置。
const NAV_H: float = 64.0
const SPRITE_H: float = 240.0     # 人物本体的显示高度（不含举起的武器）
const BASE_H: float = 400.0       # 导出基准：人物本体高（脚底到头顶）
const SLOT_W: float = 175.0       # 4 列 × 175 = 700，750 宽刚好
## uid -> 当前显示的 x。每帧朝目标插值。
var _slot_anim: Dictionary = {}
## `_slot_anim` 属于哪一场战斗；换战斗就清空，避免上一场的坐标漏过来。
var _slot_anim_battle: Battle = null
## uid -> {anim, t, dur}：出招时的姿势帧 + 补间进度，t 秒后回到 combat（M38/M39）。
var _pose: Dictionary = {}
## 一次出招的表现时长。DD1 的攻击骨架里没有分帧动画，只有「整张图的位移/旋转」，
## 所以我们用这个时长自己补出前冲和收势。
##
## M65：0.42 → 0.34。它原来比 STEP_DELAY 还长，等于每个动作都被下一手打断。
## 缩动作比拉长间隔好：0.34 秒仍然看得出「前冲—回位」两段，而拉长间隔
## 会让整场节奏变拖（每轮 7 个单位，多 0.08 秒就是每轮多半秒）。
const POSE_TIME: float = 0.34
## 守护探身的时长（M200）。0.5 秒和一次出招（0.34）差不多长，
## 但比 `STEP_DELAY` 短 —— 探身要在下一次结算前收回来，否则会叠在别人的动作上。
const GUARD_FX_TIME: float = 0.5

# —— 技能特效（M57）——
#
# 素材是 DD1 的 Spine 特效，离线导成帧序列（`assets/art/fx/<名字>/000.webp`），
# 映射直接读数据里的 `skills[].art.fx` / `.targchestfx`。
# 这一层只负责「播」，不参与任何规则计算——所以 `--no-fx` 关掉它，
# 战斗逻辑和数值一个字节都不变。
var _fx: FxArt = FxArt.new()
## 正在播的特效：{name, uid, enemy, t, dur, delay}
var _fx_active: Array = []
var _fx_on: bool = true
## 屏幕级叠加（M57 续）：命中/暴击时全屏溅血。{name, t, dur, flip}
##
## 和普通特效分开存：它不跟任何单位走，钉在屏幕上、铺满高度，
## 而且必须画在 UI 面板**之前**——否则会盖住技能按钮，点不着。
var _fx_overlay: Array = []
## 加法混合层（M57 修）：刀光/火花/光晕走 additive，溅血与烟雾走普通 alpha。
var _fx_add: FxAddLayer = null
## `--fx-overlay=hit|crit`：把溅血层钉在屏幕上，用于验收（M57 续）。
var _fx_overlay_preview: String = ""
## `--fx-pose=attack_sword`：把主角钉在某个出招姿势的**最大前冲点**（M57 修）。
##
## 验收需要它：特效的落点要跟「已经冲出去的角色」对上，
## 但正常战斗里那 0.21 秒太难截。钉住之后一次截图就能看出贴不贴。
var _fx_pose: String = ""
## `--fx-preview=名字`：把某个特效固定在主角脚上，用来验收锚点/缩放（M57）。
## 不跑战斗也能截到图——否则「特效播没播对」只能靠手速。
var _fx_preview: String = ""
var _fx_preview_t: float = 0.45
var _fx_preview_anch: String = "feet"
## `--fx-check`：无头验收（M57）。
##
## 为什么不用 `--selftest` 顺带断言：那个模式要跑完整趟远征（几分钟），
## 而「特效映射对不对」是纯查表，两秒就能答。分开之后改特效不用等整趟。
## 结果同时写 `user://fx_check.log`——Windows 上脚本的 print 有时抓不到。
var _fx_check: bool = false
## `--fx-debug`：把特效的贴图矩形和锚点画出来（M57 验收用）。
var _fx_debug: bool = false
## 顶部安全区高度（M58）：刘海 / 状态栏占掉的那条。
##
## 做法是**把整个 Control 往下挪、高度相应地少一截**（`offset_top`），
## 这样所有按 `size.y` 算的贴底布局会自动让出这块，不用逐屏改。
## 刘海本身盖一块纯黑底板。
var _safe_top: float = 0.0
## `--safe-top=80`：模拟刘海（桌面端没有真机安全区，验收只能靠它）。
var _want_safe_top: float = 0.0
## 底部安全区高度（M63）：手势条 / 圆角下巴占掉的那条。
##
## 和顶部同一套做法，方向相反：`offset_bottom` 收回来，贴底的东西（战斗技能区、
## 各屏返回键、城镇「休整一周」）自动上移。
## 不处理会怎样：安卓全面屏的手势条正好压在最底下那排按钮上，
## 按钮画得出来、点不到 —— 屏幕上看起来是完全正常的。
var _safe_bottom: float = 0.0
## `--safe-bottom=48`：模拟手势条。
var _want_safe_bottom: float = 0.0

## 战斗日志浮层是否展开（M58）。
##
## 竖屏底部是拇指热区，日志这种纯信息展示不能常驻占位，只留一行摘要；
## 完整记录点摘要条展开成半透明浮层，位置与技能区重叠但可以随时关。
var _log_open: bool = false
## 地牢内补给面板（M154）。玩家买了 9 种补给，进地牢后原来只有
## 「点火把 / 休整」两个动作会自己扣，其余的在背包里躺着看不到也用不了。
var _supply_open: bool = false
## 奇物「用哪件道具」的待确认项（M161）。
## 有内容时说明正停在一个需要玩家决定的奇物前，
## 形状：{"step": 房间步骤, "curio": 奇物 id, "item": 候选道具 id}
var _curio_ask: Dictionary = {}
## 结算屏「用仓库里哪一件换下这件」的待选状态（M168）。空 = 没在该模式。
var _swap_ask: String = ""
## 商店的「选中 → 确认」两步状态（M183）：{kind:"buy"/"sell", idx:int}
var _shop_sel: Dictionary = {}
## 商店确认弹窗：{kind, idx, name, price}，空 = 没弹
var _shop_ask: Dictionary = {}
## 队伍屏拖拽换位（M173）。形状：{id, from, pos, moved}
var _drag_card: Dictionary = {}
## 上一次鼠标位置命中的控件 id（M176）。用来判断「hover 有没有变、要不要重绘」。
var _hover_key: String = ""
## 队伍屏左侧卡片的位置（每帧重画时刷新），拖拽命中判定要用
var _party_rects: Array = []
## 地图底部队伍条的卡片位置（M176 拖拽换位用）
var _strip_rects: Array = []
## 同一次战斗里已经试过几次撤退（M155）：每次失败下一次成功率 +5%。
var _retreat_tries: int = 0

## —— 横向滚动区（M58）——
##
## 竖屏只有 750 宽，名册 15 人、建筑 8 个都排不进一行。做成「单行 + 横向滑动」，
## **高度就定死了**：人数从 4 变到 15，下面所有区域的 y 一个像素都不动。
## 多行网格做不到这一点 —— 每多一人就整体下移一格。
var _hscroll: Dictionary = {}          # key -> 当前偏移（px）
var _hscroll_zone_meta: Dictionary = {} # key -> {rect, step, max, count}
var _drag_zone: String = ""            # 正在拖的区
var _drag_x0: float = 0.0
var _drag_off0: float = 0.0
var _drag_moved: bool = false
## —— 界面皮肤（M59）——
##
## 素材在 `assets/art/ui/skin/`，全部程序化生成：
## `panel` 是九宫格边框（中间透明），`grain`/`stain` 是可平铺的颗粒与污渍，
## 按钮三态各一张。**中间透明**是关键：底色仍由 `_panel(r, bg)` 决定，
## 皮肤只负责「边框 + 材质」，所以换主题色不用重画贴图。
##
## 缺图时全部退回原来的纯色绘制（`--no-skin` 也走这条路）。
var _sk_panel: Texture2D = null
## 轻量面板（小卡片用）：无角饰、内阴影更浅。
var _sk_card: Texture2D = null
var _sk_grain: Texture2D = null
var _sk_stain: Texture2D = null
var _sk_btn: Texture2D = null
## 标题横幅（横向九宫格）与分隔线。
var _sk_banner: Texture2D = null
var _sk_divider: Texture2D = null
## 四角雕花（出图工具生成、抠图后的独立贴图）。
var _sk_orn: Texture2D = null

## 城镇名册里点开的那张卡（M58）。空 = 抽屉关着。
##
## 名册卡原来只展示、不可点，但它和建筑卡是同一套外观，
## 玩家一定会去点。现在点开一块底部抽屉看这个人的完整状态。
var _roster_open: String = ""
## 待确认卖出的仓库下标（M141）：-1 表示没有。
## 商店里点一下就卖太危险 —— 饰品是限定掉落，卖错了买不回来。
## 抽屉内的可点区域。抽屉打开时它接管全部点击：
## 命中这里 → 执行；命中别处 → 关闭（点遮罩关浮层）。
var _sheet_hits: Array = []

## 正在按住的控件 id（M58 反馈）。
##
## 之前是「按下即触发」，所以「按住」这一帧在视觉上根本不存在 ——
## 手指落下去，界面已经切走了。现在改成按下只记录、抬手才触发，
## 中间这段时间用它把控件画成按下态，让玩家确认「我按到的是这个」。
var _press_id: String = ""
## 长按看详情（M183）：按下多久、按的是哪张卡、现在有没有弹出来。
## 手机没有 hover，技能/饰品的完整数值只能靠长按看。
var _hold_t: float = 0.0
var _hold_id: String = ""
var _hold_shown: String = ""
## `--press=<id>`：把某个控件钉在按下态（验收用）。
##
## 真机上「按住」这一帧没法用命令行模拟（`--shot` 只截一帧、不会保持按下），
## 但「按下态画得对不对」必须能验 —— 找到该控件的矩形，
## 把 `_press_id` 和 `_mouse` 都钉上去，等价于手指一直压在那儿。
var _want_press: String = ""
## `--mouse=x,y`：把指针钉在某个坐标，用来验收悬停态。
var _want_mouse: Vector2 = Vector2(-1.0, -1.0)
## 命中区裁剪：滚动区绘制期间，`_add_hit` 要把矩形裁到这个范围内，
## 否则「滚出去一半的卡片」在面板外也能点到。
var _hit_clip_on: bool = false
var _hit_clip: Rect2 = Rect2()
## 一个特效的显示缩放：素材按 DD1 像素导出，人物本体高 400，
## 我们屏幕上的本体高是 SPRITE_H。两边的比值就是它。
## 再除掉导出时的 `scale`（manifest 里记的），免得改导出比例就要改代码。
func _fx_draw_scale(d: Dictionary) -> float:
	var k: float = SPRITE_H / BASE_H
	var s: float = float(d.get("scale", 1.0))
	if s <= 0.01:
		s = 1.0
	return k / s


## 某个单位应该站在哪个 x（M38）。纯函数，不读动画状态。
## 一格有多宽。站位和光源位置都从这里取——两处各算一遍必然算歪（M44 就歪过：
## 按「屏幕中心」放光源，但队伍只占左侧 40%，光落在十字军身上，瘟疫医生在暗处）。
func _battle_slot_w() -> float:
	# M58：横屏是 8 格并排（7 格宽摊开），竖屏改成 4 格 —— 上下各 4 人。
	return clampf((size.x - 48.0) / 4.0, 120.0, 176.0)


## 我方四个人在画面上的水平中心（光源就放这儿）。
func _party_focus_x() -> float:
	return size.x * 0.5


func _battle_slot_x(u: Combatant, is_enemy: bool) -> float:
	# 每格宽度跟着视口走（M41）。
	#
	# 写死 170 的话，1280 宽下正好（右边缘 1250），但 1080 宽下敌方第 4 格
	# 会跑到 x=1180——**直接出屏**，而且因为敌人常是 3 只，平时看不出来。
	# 这一条是靠 `--w=1080` 才测出来的。
	# M58 竖屏：两队**共用同一组 4 列**，只是站在上下两条地面线上。
	# 横屏那套「我方占左半、敌方占右半、前锋在中间相接」是 8 格并排才成立的，
	# 竖屏 750 宽放不下 8 格，继续用会让敌方整排跑到屏幕外。
	var slot: float = _battle_slot_w()
	var x0: float = (size.x - slot * 4.0) * 0.5
	var rk: int = clampi(u.rank, 0, 3)
	# 面对面：我方 rank 1 在右、敌方 rank 1 在左，两队前锋隔着中缝相对
	if is_enemy:
		return x0 + float(rk) * slot + slot * 0.5
	return x0 + float(3 - rk) * slot + slot * 0.5


## 当前显示的 x（带插值）。第一次出现时直接落在目标位。
func _anim_x(u: Combatant, is_enemy: bool) -> float:
	var target: float = _battle_slot_x(u, is_enemy)
	return float(_slot_anim.get(u.uid, target)) + float(_hit_shake(u.uid)) \
		+ _guard_shift(u)


## 守护探身（M200）：朝被守护者方向平移最多 16px，0.5 秒内去而复返。
##
## 为什么是「探身」而不是「站过去」：战场按 rank 槽位绘制，真的换位会和
## `_slot_anim` 的位移补间、rank 重排打架，画面上也会读成「他换了位置」。
## 探身只改绘制、不动 `rank`，规则层完全不受影响。
func _guard_shift(u: Combatant) -> float:
	var gd: Dictionary = _guard_fx.get(u.uid, {})
	if gd.is_empty() or not gd.has("toward"):
		return 0.0
	var other: Combatant = _unit_by_uid(int(gd["toward"]))
	if other == null:
		return 0.0
	var me_x: float = _battle_slot_x(u, not u.is_hero)
	var ot_x: float = _battle_slot_x(other, not other.is_hero)
	var dir: float = 1.0 if ot_x > me_x else -1.0
	var prog: float = clampf(1.0 - float(gd.get("t", 0.0)) / GUARD_FX_TIME, 0.0, 1.0)
	return dir * 16.0 * sin(prog * PI)


func _hit_shake(uid: int) -> float:
	var ht: float = float(_hit_t.get(uid, 0.0))
	if ht <= 0.0:
		return 0.0
	return sin(ht * 80.0) * 3.2 * (ht / HIT_TIME)
var _room_hits: Array = []     # {rect, id}：地图上能走过去的房间
var _hover_uid: int = -1
var _flash: String = ""
var _flash_life: float = 0.0

# —— 元层 ——
var campaign: Campaign
var _save_path: String = Campaign.DEFAULT_PATH
var _settle_gain: Dictionary = {}
var _settled: bool = false

# —— 自检 ——
var _auto: bool = false
var _auto_map_only: bool = false
var _skip_battles: bool = false   # 调试：战斗瞬间结算，让镜头一直停在地图上
var _step_delay: float = STEP_DELAY
var _auto_start: bool = false
var _to_result: bool = false
var _selftest: bool = false
var _reveal_all: bool = false
var _auto_timer: float = 0.0
var _shot_path: String = ""
var _shot_at: float = 3.0
## 截图/冒烟用：启动后直接停在出发准备屏（`--prep`）。
## 加它是因为「准备屏的布局与门槛」以前只能靠手点验证，改一次要人肉看一次。
var _boot_prep: bool = false
## `--resume-demo`（M117）：即使带了截图参数也走「自动继续远征」。
## 正常情况下 `--shot` 会关掉自动恢复（否则所有城镇截图都会变成地图），
## 这个参数专门用来验收恢复路径。
var _boot_resume: bool = false
## `--quests=N`（M123）：把「已完成任务数」设成 N，用来验收建筑解锁 ——
## 否则新档只有三个建筑，截不到后面那些。
var _boot_quests: int = -1
## 技能图标缓存（M133）：hid|sid → Texture2D（取不到时存 null）
var _skill_icon_cache: Dictionary = {}
## `--skill-lv=N`（M126）：把全名册的技能等级都设成 N，用来验收
## 「每技能等级」这条路走没走通 —— 看技能卡上的伤害/命中数字变没变。
var _boot_skill_lv: int = -1
## `--resolve=N`（M126）：把全名册的决心等级设成 N，用来验收技能等级上限。
var _boot_resolve: int = -1
## 同上：启动后直接停在公会屏（`--guild`），用于截图验证技能组界面。
var _boot_guild: bool = false
## 启动时的任务类型（`--quest=kill_boss`），给自检和截图用。
var _boot_quest: String = "explore"
## 启动后直接进某座建筑（`--bld=sanitarium`），给截图用。
var _boot_building: String = ""
## 截图用：直接进建筑、并把解雇按钮置成「待确认」（`--pending-fire`）。
## 「点两次才删」这个交互没法靠静态截图验证，所以给它一个入口。
var _boot_pending_fire: bool = false
## 开发信息开关（M31）：`--dev` 打开。
##
## 界面上有一部分字只有做这个项目的人需要看——存档路径、内部 id、诊断数字。
## 它们以前一直在屏幕上，和玩家真正需要的「我能不能出发」混在同一层，
## 于是玩家要先学会忽略一半的字。默认关掉，`--dev` 才显示。
var _dev_ui: bool = false
## 截图用：`--start --battle` 出发后直接拉一场战斗（M36）。
var _boot_battle: bool = false
## `--w=N`：排版验收用的目标窗口宽度（M41）。0 表示用真实视口宽。
var _want_w: int = 0
## `--bosses=N`：把前 N 个区域标成已讨伐（M46，验收用）。-1 表示不干预。
var _want_bosses: int = -1
## `--victory`：直接显示胜利屏（M46，验收用）。
var _show_victory: bool = false
## `--be-demo`：直接显示战斗结算卡（M65，验收用）。
## 真实流程要先打赢一场才看得到，截图时没法卡在那个时间点。
var _show_battle_end: bool = false
## `--trinkets` / `--shop`：直接进饰品仓库 / 商店（M66，验收用）。
## 这两屏要先进城镇再点建筑，截图和排版验收都不方便。
var _boot_trinkets: bool = false
var _boot_shop: bool = false
## `--aim=N`：进战斗后自动选中第 N 个技能，停在瞄准态（M65，验收用）。
## 瞄准态只存在于两次点击之间，命令行截不到 —— 而这次改的正是瞄准态的样子
## （合法目标加粗绿环、血条右侧显示命中率）。
var _boot_aim: int = -1
## `--retreat-demo`：进战斗后立刻走一次「战斗中撤退」（M65，验收用）。
## 这条路径以前根本不存在（ESC 只在地图屏生效），
## 它要动到 `finish_battle` 的落盘，不实际跑一遍不敢说通。
var _retreat_demo: bool = false
## `--corpse-demo`（M73）：进战斗后立刻杀掉 1 号敌人，留一具残骸给截图看。
var _corpse_demo: bool = false
## `--corpse-demo` 的配套：已经为哪一场战斗做过（按 Battle 实例 id）。
var _corpse_done_for: int = 0
## `--room-demo` / `--room-demo=1`（M74）：直接打开房间卡。
## 0 = 抵达页，1 = 结果页（自动结算一次）。跑一趟撞奇物太靠运气。
var _room_demo: int = -1
## `--banner-demo`（M75）：进地图后立刻弹一条「陷阱」横幅，方便截图。
var _banner_demo: bool = false
## `--pick-demo=N`（M89）：进玩家回合后自动选中第 N 个技能，用来截目标面板。
var _pick_demo: int = -1
## `--busy-demo=N`（M94）：把前 N 个活人标成「在建筑里，还剩 2 周」。
## 名册的「忙 / 可出征」区分不造数据就截不到。
var _busy_demo: int = 0
## `--hire-demo`（M98）：强制摆两个招募候选，马车卡片不造数据截不到
## （新存档第一周常常是空的）。
var _hire_demo: bool = false
## `--phone=482x1080`（M99）：桌面试跑按手机屏幕比例跑。
## 0 表示不模拟（桌面正常窗口）。
var _phone_size: Vector2i = Vector2i.ZERO
## 本次远征打到第几场（M101）。召唤物补位和「新的一场」长得太像，
## 标题里没有场次的话，玩家分不清刚才那一串是不是同一场。
var _battle_no: int = 0
## 这一场是从走廊打起来的吗（M102）。横幅要用它区分「走廊遭遇 / 房间遭遇」——
## 两种在画面上长得一模一样，而玩家最困惑的正是「为什么突然又打起来」。
var _battle_corridor: bool = false
## 本场召唤出来的单位 uid（M102）。给它们挂「召」角标用。
var _summoned_uids: Dictionary = {}
## 这场战斗是从房间卡上点「探索」打起来的（M103）。
## 决定打完回哪儿：回房间卡弹结果，而不是直接回地图。
var _room_battle: bool = false
## 队伍屏当前选中的人（M106）。
var _party_hero: String = ""
## `--store-demo`（M107）：往仓库塞 6 件饰品。
## 干净存档里一件都没有，队伍屏的仓库列表根本截不到。
var _store_demo: bool = false
## `--info=N`：进战斗后打开第 N 个单位的状态详情（M65 续，验收用）。
## 顺带塞几条典型状态（命中、伤害、流血、标记）——不然「有 buff 时长什么样」
## 只能靠打几轮撞运气，那种验收不可复现。
var _boot_info: int = -1
## `--dump-hits`：打印当前界面的可点元素（M55，触屏验收用）。
##
## 桌面端看不出「手机上点不到」——按钮在不在屏幕里、够不够大，
## 都要靠数字。这个开关把每一屏的热区按「贴底 / 过小」两类打出来。
var _dump_hits: bool = false
var _dump_key: String = ""
## `--sfx-demo`：音效试听（M50）。在菜单上逐个播放全部槽位并标出名字。
##
## 存在的理由很实际：正常玩一趟听不全——`death` 要有人死、`click` 要手动点、
## `miss` 看运气。调音效时没法只靠「打一趟」判断好坏。
var _sfx_demo: bool = false
var _sfx_demo_i: int = 0
var _sfx_demo_t: float = 0.0
## 试听顺序：短促的在前，长的在后，方便连续听时分辨
const SFX_DEMO_LIST: Array = [
	# 界面与通用（M50）
	"click", "hit", "crit", "miss", "heal", "stress", "death", "door", "torch", "victory",
	# 分类命中（M51）：按武器分，同一招不可能再听成「都是一把剑」
	"imp_sword", "imp_knife", "imp_spear", "imp_arrow", "imp_gun", "imp_shield",
	"imp_whip", "imp_staff", "imp_magic_dark", "imp_gas", "imp_liquid", "imp_slime",
	"imp_general",
	# 敌人语音（M51）：带 `/` 的是变体槽位，播放时随机挑 `_1` / `_2`
	"voice/skel_hurt", "voice/swine_1_hurt", "voice/fish_1_hurt", "voice/brig_1_hurt",
	"voice/cultist_f_hurt", "voice/crone_hurt", "voice/rbdog_hurt", "voice/bug_1_hurt",
	"voice/skel_death", "voice/swine_2_death", "voice/cultist_f_crit", "voice/skel_aggro",
	# 怪物攻击声（M52）：每组 1–3 个变体
	"atk/skeleton_common", "atk/swine_reaver", "atk/fishman_harpoon",
	"atk/brigand_cutthroat", "atk/cultist_witch", "atk/hag",
]
## 有任何一个「进游戏」类参数时不显示主菜单（M47）。
##
## 判据是「这次运行是不是人手动打开的」：截图、自检、自动跑、指定存档路径
## 全都是脚本调用，弹一个菜单让它们等点击等于把整条自动化链掐断。
var _skip_menu: bool = false
## 存档槽位数（M47）。三个够用：比 1 个能开多档，比 10 个不需要翻页。
const SAVE_SLOTS: int = 3
## 正在等待「确认删除」的槽位（M48）。-1 表示没有。
var _del_slot: int = -1

## 设置文件（M47）。和存档分开：设置是「这台机器」的，存档是「这一档」的，
## 混在一起会出现「换个槽音量就变了」。
const SETTINGS_PATH: String = "user://settings.json"
## 主音量 0–100（0 = 静音）。默认 70：
## 之前写死 -7dB，在笔电外放上偏吵、在耳机上偏轻，两边都不合适。
var _volume: int = 70
## 光照层开关（M44）。关掉之后光影完全不存在，用来判断某个「看不清」是光造成的还是布局造成的。
var _light_on: bool = true
## 战斗背景开关（M45）。
var _bg_on: bool = true
## `--light=N` 强行固定的光照值（M44）。-1 表示不干预。
var _want_light: float = -1.0
## `--dev` 下打印跟随曲线的节流计时（M44）。
var _light_log_t: float = 0.0
## `--dev` 下「上次打印过的背景」标记，避免每帧刷屏（M45）。
var _bg_log_key: String = ""
## `--mute`：全程静音（M43）。
var _mute: bool = true   # 默认静音（M138）：玩家明确要求，也不打扰别人

## 截图/回归用：启动后模拟点一次这个按钮 id（`--click=bld:coach`）。
## 和 `--bld=` 的区别是它走 `_activate`，能测出「状态没切换」这类断线。
var _boot_click: String = ""
## `--tap=x,y`（M140）：按**屏幕坐标**点一下，走真实命中层（`_on_click`）。
## `--click=` 直接调 `_activate`，绕过了 `_hit_id_at` —— 遮挡/穿透这类
## 「点哪儿算谁」的问题只有 `--tap` 测得到。
var _boot_tap: Vector2 = Vector2(-1, -1)
## 截图用：指定建筑屏选中的人（`--bld-hero=<hid>`）。
## 默认选第一个活人，所以「墓园里的死人」那半屏永远截不到。
var _boot_building_hero: String = ""
var _elapsed: float = 0.0


## 建 Campaign 并读档（M47 从 `_ready` 里抽出来）。
##
## 抽出来的原因很实际：主菜单要先让玩家选槽，选完才知道读哪个文件，
## 而这段初始化原来写死在 `_ready` 里，没有「稍后再调一次」的入口。
func _boot_campaign(save_path: String) -> void:
	_save_path = save_path
	campaign = Campaign.new()
	campaign.setup_from_cfg(db.campaign_cfg, _save_path)
	# 元层要判「升级打折」类怪癖，但它不该自己去读一份 88 KB 的表
	campaign.quirk_lib = db.quirk_lib
	# 新英雄自带 1–2 正 + 1–2 负（heroes.json 的 generation 段）。
	# 这是原版怪癖的主要来源，M14 第一版漏了它，导致整期功能几乎不可见。
	campaign.start_quirk_gen = db.hero_quirk_generation()
	# 饰品库：仓库/装备要判职业限制与同名上限，但它同样不该自己去读表。
	campaign.trinket_lib = db.trinket_lib
	# 商店：价格表与上架规则都在 Shop 里，元层只管钱。
	# **必须在 load_or_new 之前**：开新档时要立刻掷一批货架。
	campaign.shop = db.shop
	# 技能组：每个英雄能带 4 个（heroes.json 的 skill_selection，M19 才接上）。
	# **必须在 load_or_new 之前**：读档时要按它校验存档里的技能列表。
	campaign.skill_table = db.hero_skill_table()
	# 招新的候选池（M27）：名册上限 = 职业总数，所以元层得知道有哪些职业。
	# **必须在 load_or_new 之前**：读档时要用它校验存档里的名册组成。
	campaign.known_heroes = db.hero_ids()
	var had_save: bool = campaign.load_or_new()
	if not had_save:
		campaign.save()
	# 启动时对齐「选中的区域」和「读档时那个区域」（M32）：
	# 命令行 `--dungeon=` 或者存档里记的区域都算数，两者不一致时以场景为准，
	# 因为城镇上那排按钮高亮的正是 `_dungeon`。
	campaign.select_board_region(_dungeon)
	print("城镇：金币 %d，名册 %d 人，远征 %d 趟%s" % [
		campaign.gold, campaign.alive_ids().size(), campaign.expeditions,
		"（读档）" if had_save else "（新档）"])



## 桌面窗口适配（M71）。
##
## 项目逻辑分辨率是竖屏 750×1334。桌面上 1:1 开窗时，1334 已经超过
## 大多数 1080 高屏幕的**可用高度** —— 窗口底部被显示器/任务栏截掉，
## 而「贴底」的那排按钮（准备屏的出发、地图屏的三颗、战斗的技能区）
## 手机显示模式的缩放设置（M99）。
##
## Android 和桌面 `--phone=` 共用这一份，**模拟必须和真机走同一段代码**，
## 否则桌面上看着没问题、装到手机上还是断层。
##
## `win_size == ZERO` 表示真机（窗口就是屏幕，不要改尺寸）。
func _apply_mobile_scale(win_size: Vector2i) -> void:
	var win: Window = get_window()
	win.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
	win.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_KEEP
	win.content_scale_size = Vector2i(750, 1334)
	if win_size.x > 0:
		win.size = win_size
		win.position = Vector2i(40, 40)


## 正好全在那一块，看起来就像界面元素互相压在一起。
##
## 修法是锁逻辑尺寸、缩窗口：内容永远按 750×1334 排，玩家看到的是一整张
## 等比缩小的画面，不缺底也不留黑边（窗口本身按 750:1334 开）。
##
## 三种情况**不**这么做：
##   · `--w=` 排版验收 —— 它依赖「窗口多宽、布局就多宽」（M41，踩过坑）
##   · `--shot=` 截图 —— 要输出 750×1334 原尺寸，否则验收图全是缩过的
##   · headless / Android —— 各自已有处理
func _fit_desktop_window() -> void:
	if not _shot_path.is_empty() or OS.has_feature("headless") \
			or OS.has_feature("android") or _phone_size.x > 0:
		return
	var win: Window = get_window()
	win.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
	win.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_KEEP
	win.content_scale_size = Vector2i(750, 1334)
	var scr: Rect2i = DisplayServer.screen_get_usable_rect()
	if scr.size.x <= 0 or scr.size.y <= 0:
		return
	# 0.96：可用区通常不含标题栏，留 4% 给它，别让窗口顶着任务栏
	var k: float = minf(float(scr.size.x) / 750.0, float(scr.size.y) / 1334.0) * 0.96
	if k >= 1.0:
		return      # 屏幕够大就保持 1:1；放大只会糊
	var sz := Vector2i(int(750.0 * k), int(1334.0 * k))
	win.size = sz
	win.position = scr.position + (scr.size - sz) / 2
	print("窗口：%dx%d（屏幕可用 %dx%d，缩放 %.2f）" % [
		sz.x, sz.y, scr.size.x, scr.size.y, k])


## 切后台 / 被系统回收前把该落的盘都落了（M114）。
##
## 手机上「按 Home 键」不是暂停，系统随时可能把进程杀掉。Godot 在
## Android 上会先发 `NOTIFICATION_APPLICATION_PAUSED`，这是唯一的预警窗口。
## 原来完全没处理：名单、补给包这些只活在内存里的东西，回来就没了。
func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		# 安卓返回键（M134）。
		#
		# 这是「游戏自己退回桌面」的真凶：`SceneTree.quit_on_go_back`
		# **默认是 true**，而我们从没关过它。全面屏手机的返回手势是从屏幕
		# 边缘往里滑 —— 在战斗里点最边上的按钮、或者手指带一下，就会触发
		# 「返回」，游戏直接退出，玩家看到的是「它自己跳回桌面了」。
		#
		# 而且 `NOTIFICATION_WM_GO_BACK_REQUEST` 到达时我们只写了存档、
		# 没拦住退出，所以存档写完了人也出去了。
		_on_back_pressed()
		return
	if what == NOTIFICATION_APPLICATION_PAUSED \
			or what == NOTIFICATION_WM_CLOSE_REQUEST:
		_party_persist()
		_exp_persist()


## 返回键：先关弹窗，再回上一屏，最后才退出（M134）。
##
## 一按就退的话，玩家在战斗里误触一下就丢了这一趟 —— 而这场仗可能打了五分钟。
func _on_back_pressed() -> void:
	# 任何浮层先关掉
	if not _roster_open.is_empty():
		_roster_open = ""
		queue_redraw()
		return
	if _state == S_BATTLE and _info_uid >= 0:
		_info_uid = -1
		queue_redraw()
		return
	# 子屏回城镇
	match _state:
		S_BUILDING, S_GUILD, S_ROSTER, S_TRINKET, S_SHOP, S_GATE, S_PREP, S_PARTY, S_SETTINGS:
			_party_persist()
			_exp_persist()
			_state = S_TOWN
			queue_redraw()
			return
		S_MAP:
			# 远征途中不退出：直接回城镇等于放弃这一趟，太狠
			_flash_msg("在地牢里，退出请走「撤退」")
			queue_redraw()
			return
		S_BATTLE:
			_flash_msg("战斗中不能退出")
			queue_redraw()
			return
	# 城镇再按一次才退出
	_party_persist()
	_exp_persist()
	get_tree().quit()


func _ready() -> void:
	# **必须关**（M134）：默认 true 时安卓返回键会直接退出应用，
	# 而全面屏手势的「返回」是从屏幕边缘往内滑 —— 点边上的按钮就会误触。
	get_tree().quit_on_go_back = false
	# Android 端把逻辑分辨率锁成 1280×760 再按屏幕缩放（M54）。
	#
	# 桌面端**故意不动**：`--w=1080` 那套排版验收依赖「窗口多宽、布局就多宽」。
	# 一旦开了 canvas_items，1080 宽会被缩回 1280 逻辑宽，验收就测了个假的
	# ——M41 已经在这一类「以为测到了」上栽过一次。
	#
	# keep 而不是 expand（M96，真机反馈改回来）。
	#
	# 原先用 expand，注释里写的理由是「手机比 16:9 高，多出来的高度给界面用」。
	# 实际效果是**断层**：视口变 750×1680，但
	#   · 城镇画布 `_town_canvas_rect()` 按 `size.x * 1334/750` 算 → 只有 1334 高；
	#   · 地图屏的网格/面板用的是写死的 156/716 等坐标 → 也停在 1334 附近；
	#   · 而底部按钮用 `size.y - 44 - 204` → 跑到 1432。
	# 上下两套坐标系，中间空出 346 逻辑像素（≈222 屏幕像素），
	# 看起来就是「内容画到一半断了，按钮悬在下面」。
	#
	# expand 要能真的用起来，得让**所有**纵向布局都跟着 size.y 走
	# （画布、建筑槽位、地图网格、每个面板的 y）。在做到那一步之前，
	# keep 是唯一不会骗人的选择：内容按 750×1334 完整显示、居中，
	# 比例不符的机型上下留一点边——边比断层好。
	if OS.has_feature("android"):
		_apply_mobile_scale(Vector2i.ZERO)
	elif _phone_size.x > 0:
		_apply_mobile_scale(_phone_size)

	_font = ThemeDB.fallback_font
	# 地图层（M80）：单独一个 Control 子节点 + `clip_contents`。
	# `_draw()` 画的东西没法裁剪，格子一旦超出面板就会画到面板外面去
	# （半截房间浮在背景上）；子节点自带裁剪，这是唯一干净的解法。
	_map_layer = Control.new()
	_map_layer.name = "MapLayer"
	_map_layer.clip_contents = true
	_map_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_map_layer.draw.connect(_draw_map_layer)
	add_child(_map_layer)

	# 卡片层（M80）：房间卡要浮在地图层之上，而子节点的层级是固定的，
	# 所以只能再加一层。它铺满全屏、坐标和屏幕一致，命中区不用换算。
	_card_layer = Control.new()
	_card_layer.name = "CardLayer"
	_card_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_card_layer.draw.connect(_draw_card_layer)
	add_child(_card_layer)
	for a in OS.get_cmdline_user_args():
		if a == "--auto":
			_auto = true
		elif a == "--selftest":
			_selftest = true
		elif a == "--show-move":
			_show_move_demo = true
		elif a == "--show-guard":
			_show_guard_demo = true
		elif a == "--reveal":
			_reveal_all = true
		elif a == "--to-result":
			_to_result = true
		elif a == "--explore":
			_explore = true
		elif a == "--fast":
			_step_delay = 0.02
		elif a == "--auto-map":
			_auto = true
			_auto_map_only = true
			_skip_battles = true
		elif a.begins_with("--shot="):
			_shot_path = a.substr(7)
			# M58：截图窗口跟基准分辨率走，不写死 ——
			# 原来写死 1280×760，改成竖屏之后截出来的还是横屏，白等一轮。
			DisplayServer.window_set_size(Vector2i(
				int(ProjectSettings.get_setting("display/window/size/viewport_width")),
				int(ProjectSettings.get_setting("display/window/size/viewport_height"))))
		elif a.begins_with("--shot-at="):
			_shot_at = float(a.substr(10))
		elif a.begins_with("--size="):
			_size = a.substr(7)
		elif a.begins_with("--dungeon="):
			_dungeon = a.substr(10)
		elif a.begins_with("--quest="):
			_boot_quest = a.substr(8)
		elif a.begins_with("--bld="):
			_boot_building = a.substr(6)
		elif a == "--pending-fire":
			_boot_pending_fire = true
		elif a.begins_with("--bld-hero="):
			_boot_building_hero = a.substr(11)
		elif a.begins_with("--tap="):
			var xy: PackedStringArray = a.substr(6).split(",")
			if xy.size() == 2:
				_boot_tap = Vector2(float(xy[0]), float(xy[1]))
		elif a.begins_with("--click="):
			_boot_click = a.substr(8)
		elif a == "--dev":
			_dev_ui = true
		elif a == "--no-skin":
			_skin.enabled = false
		elif a == "--no-light":
			_light_on = false
		elif a == "--no-bg":
			_bg_on = false
		elif a.begins_with("--bosses="):
			# 验收用（M46）：直接把前 N 个区域标成已讨伐。
			# 没有它，想看「首领 3/4 的城镇」得真的打三场首领。
			_want_bosses = int(a.substr(9))
		elif a == "--victory":
			_show_victory = true
		elif a == "--be-demo":
			_show_battle_end = true
		elif a == "--trinkets":
			_boot_trinkets = true
		elif a == "--shop":
			_boot_shop = true
		elif a.begins_with("--shop="):
			_boot_shop = true
			_shop_tab = int(a.substr(7))
		elif a.begins_with("--aim="):
			_boot_aim = int(a.substr(6))
		elif a == "--retreat-demo":
			_retreat_demo = true
		elif a == "--corpse-demo":
			_corpse_demo = true
		elif a == "--room-demo":
			_room_demo = 0
		elif a.begins_with("--room-demo="):
			_room_demo = int(a.substr(12))
		elif a.begins_with("--phone="):
			# 两种写法：`--phone` 用 20:9 默认值，`--phone=482x1080` 指定尺寸
			var pv3: PackedStringArray = a.substr(8).split("x")
			if pv3.size() == 2 and pv3[0].is_valid_int() and pv3[1].is_valid_int():
				_phone_size = Vector2i(int(pv3[0]), int(pv3[1]))
			else:
				_phone_size = Vector2i(482, 1080)
		elif a.begins_with("--resolve="):
			_boot_resolve = int(a.substr(10))
		elif a.begins_with("--skill-lv="):
			_boot_skill_lv = int(a.substr(11))
		elif a.begins_with("--quests="):
			_boot_quests = int(a.substr(9))
		elif a == "--resume-demo":
			_boot_resume = true
		elif a == "--store-demo":
			_store_demo = true
		elif a == "--hire-demo":
			_hire_demo = true
		elif a == "--banner-demo":
			_banner_demo = true
		elif a.begins_with("--busy-demo="):
			_busy_demo = int(a.substr(12))
		elif a.begins_with("--pick-demo="):
			_pick_demo = int(a.substr(12))
		elif a.begins_with("--map-pan="):
			# 验收用（M78）：把地图平移钉在指定值，验证「拖动之后画得对不对」。
			# 鼠标拖拽没法用命令行模拟，但偏移之后的绘制路径可以。
			var pv2: PackedStringArray = a.substr(10).split(",")
			if pv2.size() == 2:
				_map_pan = Vector2(float(pv2[0]), float(pv2[1]))
				_map_pan_auto = false
				_map_pan_lock = true
		elif a.begins_with("--info="):
			_boot_info = int(a.substr(7))
		elif a == "--sfx-demo":
			_sfx_demo = true
		elif a == "--dump-hits":
			_dump_hits = true
		elif a.begins_with("--light="):
			# 固定光照值（M44）。没有它，想截一张「昏暗」只能靠点火把/走路碰运气，
			# 光照四档里只有 100 是能稳定复现的。
			_want_light = float(a.substr(8))
		elif a == "--mute":
			_mute = true
		elif a.begins_with("--w="):
			# 排版验收用（M41）：把窗口改成指定宽度，逼布局真正重排。
			# `--resolution` 在这里没用——项目把 viewport 定成 1280，
			# 内容尺寸不跟窗口走，截出来还是 1280 宽，等于没测。
			_want_w = int(a.substr(4))
		elif a == "--battle":
			_boot_battle = true
		elif a.begins_with("--level="):
			_level = int(a.substr(8))
		elif a.begins_with("--preset="):
			_preset = a.substr(9)
		elif a == "--start":
			_auto_start = true
		elif a == "--prep":
			_boot_prep = true
		elif a == "--show-interact":
			_show_interact = true
		elif a == "--dlg-demo":
			_dlg_demo = true
		elif a == "--hold-demo":
			_hold_demo = true
		elif a == "--guild":
			_boot_guild = true
		elif a.begins_with("--save="):
			_save_path = a.substr(7)
		elif a == "--no-fx":
			_fx_on = false
		elif a.begins_with("--fx-preview="):
			_fx_preview = a.substr(13)
		elif a.begins_with("--fx-t="):
			_fx_preview_t = float(a.substr(7))
		elif a.begins_with("--fx-anchor="):
			_fx_preview_anch = a.substr(12)
		elif a == "--fx-check":
			_fx_check = true
		elif a.begins_with("--safe-top="):
			_want_safe_top = float(a.substr(11))
		elif a.begins_with("--safe-bottom="):
			_want_safe_bottom = float(a.substr(14))
		elif a.begins_with("--layout="):
			_want_town_layout = a.substr(9)
		elif a.begins_with("--press="):
			_want_press = a.substr(8)
		elif a.begins_with("--mouse="):
			var mv: PackedStringArray = a.substr(8).split(",")
			if mv.size() == 2:
				_want_mouse = Vector2(float(mv[0]), float(mv[1]))
		elif a.begins_with("--scroll="):
			# 验收用：把某个滚动区钉在指定偏移（`--scroll=roster:150`）。
			# 拖动本身没法用命令行模拟，但「偏移之后的绘制是否正确」可以这样验。
			var sp: PackedStringArray = a.substr(9).split(":")
			if sp.size() == 2:
				_hscroll[sp[0]] = float(sp[1])
		elif a == "--fx-debug":
			_fx_debug = true
		elif a.begins_with("--fx-overlay="):
			_fx_overlay_preview = a.substr(13)
		elif a.begins_with("--fx-pose="):
			_fx_pose = a.substr(10)
	# 任何「直接进游戏 / 指定路径」的参数都跳过主菜单。
	# 逐条列出而不是「有参数就跳过」：`--w` / `--dev` / `--mute` 这些纯调试开关
	# 不影响流程，加了它们也该看到主菜单。
	if (_auto_start or _to_result or _selftest or _auto or _boot_prep
			or _boot_guild or _boot_building != "" or _show_victory
			or _save_path != Campaign.DEFAULT_PATH):
		_skip_menu = true

	db = DdDb.shared()
	if db == null or db.heroes.is_empty():
		push_error("数据未加载")
		return
	# 「技能 → 动作帧」映射建一次（M38）。数据里现成，不用手工维护。
	_art.build_attack_map(db)
	# 「技能 → 特效」映射（M57）。同样是数据里现成的，缺资源就只是不播。
	_fx.load_manifest()
	_fx.build_map(db)
	# 加法层必须真挂一个子节点：Control 的 _draw() 没法逐项换混合模式。
	_fx_add = FxAddLayer.new()
	_fx_add.host = self
	add_child(_fx_add)
	if _fx_check:
		_run_fx_check()
		return

	_load_settings()
	_sfx = Sfx.new()
	_sfx.enabled = not _mute
	add_child(_sfx)
	_apply_volume()

	_music = BgMusic.new()
	add_child(_music)
	# 试听模式下不放音乐：BGM 会把音效盖住，而这个模式唯一的目的就是听音效
	_music.enabled = not _mute and not _sfx_demo
	if _sfx_demo:
		# 立刻播第一个，不等 2 秒——否则窗口开出来一片安静，像没生效
		_demo_play(str(SFX_DEMO_LIST[0]))

	# —— 主菜单分流（M47）——
	#
	# 主菜单之前不存在：启动直接进城镇，换档只能靠命令行 `--save=`。
	# 现在没有「进游戏」类参数时先停在这里，等玩家选一个槽。
	#
	# 注意这里**还没读任何存档**：选槽之前不知道读哪个文件。
	# 所以 `campaign` 在这一刻是 null，绘制主菜单的分支不能碰它。
	# 窗口宽度要在菜单分支**之前**应用（M47）：
	# 原来在 `_boot_campaign` 之后，于是 `--w=1080` 进主菜单时根本没生效，
	# 截出来还是 1280——正是 M41 踩过的那个坑（测了个假的）。
	if _want_w > 400:
		get_window().size = Vector2i(_want_w, int(get_window().size.y))
	else:
		_fit_desktop_window()

	if not _skip_menu:
		_state = S_MENU
		# 验收用：`--boot-click=slot:0` 要能在菜单状态下生效，
		# 否则「从菜单点进某个槽」这条链路永远测不到（会先在菜单处 return）。
		if not _boot_click.is_empty():
			var boot_id: String = _boot_click
			_boot_click = ""
			_activate(boot_id)
		queue_redraw()
		return

	_boot_campaign(_save_path)
	if _boot_quests >= 0 and campaign != null:
		campaign.quests_done = _boot_quests
	if _boot_resolve >= 0 and campaign != null:
		for hid in campaign.roster.keys():
			(campaign.roster[str(hid)] as Dictionary)["resolve"] = _boot_resolve
	if _boot_skill_lv >= 0 and campaign != null:
		for hid in campaign.roster.keys():
			var lv: Dictionary = {}
			for sid in campaign.equipped_skills(str(hid)):
				lv[str(sid)] = clampi(_boot_skill_lv, 0, Campaign.SKILL_MAX_LEVEL)
			(campaign.roster[str(hid)] as Dictionary)["skill_levels"] = lv

	set_process(true)
	if _want_bosses >= 0 and campaign != null:
		for i in mini(_want_bosses, Campaign.BOARD_REGIONS.size()):
			campaign.boss_cleared[Campaign.BOARD_REGIONS[i]] = true
		campaign.save()
	if _show_victory:
		# 胜利屏上的数字要和状态自洽：不打这一行的话，画面上会写着
		# 「战役完成」而「首领讨伐 0 / 4」——看起来像 bug。
		for r in Campaign.BOARD_REGIONS:
			campaign.boss_cleared[str(r)] = true
		campaign.save()
		_state = S_VICTORY
	# 截图/冒烟用：直接进地图，不必先点按钮
	if _store_demo and campaign != null and campaign.trinket_lib != null \
			and campaign.trinket_lib.is_loaded():
		var tn: int = 0
		for tid2 in (campaign.trinket_lib.entries as Dictionary).keys():
			if tn >= 6:
				break
			campaign.trinket_store.append(str(tid2))
			tn += 1
		if not campaign.trinket_store.is_empty():
			_sel_trinket = str(campaign.trinket_store[0])
	if _hire_demo and campaign != null:
		campaign.recruit_candidates = ["leper", "vestal"]
		campaign.gold = 2500      # 让卡片处于「可招」状态，才看得出正常长什么样
	if _busy_demo > 0 and campaign != null:
		var bn: int = 0
		for bhid in campaign.alive_ids():
			if bn >= _busy_demo:
				break
			(campaign.roster[str(bhid)] as Dictionary)["busy"] = 2
			bn += 1
	if _boot_guild and not campaign.alive_ids().is_empty():
		_guild_hero = str(campaign.alive_ids()[0])
		_state = S_GUILD
	elif not _boot_building.is_empty() and not campaign.alive_ids().is_empty():
		_building = _boot_building
		# 默认选第一个活人；`--bld-hero` 可以指定（截图要看死人那半屏）
		_building_hero = str(campaign.alive_ids()[0])
		if campaign.roster.has(_boot_building_hero):
			_building_hero = _boot_building_hero
		if _boot_pending_fire:
			_fire_pending = _building_hero
		_state = S_BUILDING
	elif _boot_prep and not campaign.alive_ids().is_empty():
		# 和点难度卡进准备屏走同一套初始化，否则截出来的不是玩家看到的那一屏
		_prep_size = _size
		_prep_level = _level
		_prep_pack = _restore_prep_pack()
		_prep_party = _party_restore(_prep_level)
		_state = S_PREP
	elif _boot_trinkets and not campaign.alive_ids().is_empty():
		_sel_trinket = ""
		_state = S_TRINKET
	elif _boot_shop and not campaign.alive_ids().is_empty():
		_state = S_SHOP
	elif _auto_start:
		_start_expedition(_size, _level, {}, [], _boot_quest)
		# 截图用：出发后立刻拉一场战斗，不必等自动走到战斗房（M36）
		if _boot_battle:
			_boot_into_battle()
		if _room_demo >= 0 and exp != null:
			_room_demo_open()
		if _banner_demo and exp != null:
			# 验收用（M75）：直接弹一条横幅，不必等走到陷阱
			_map_banner("陷阱！", "脚下的地砖陷了下去。", DdTheme.HP)
		if _reveal_all and exp != null:
			exp.debug_reveal_all()
	elif _to_result:
		# 一次性跑完一整趟再展示结算：给截图和冒烟测试用，
		# 免得为了看结算屏等上几分钟战斗动画。
		#
		# 不能调 exp.run_auto()：那是线性路线的驱动器，图模式的待结算队列
		# 它不会消化，于是「推进 1/9 步」就被判定完成——截图上完全看不出来。
		_start_expedition(_size, _level)
		if exp != null:
			# 战斗也走「秒结算」，否则循环会停在战斗屏等玩家点击
			_skip_battles = true
			var guard: int = 0
			while not exp.ended and guard < 400:
				guard += 1
				_selftest_move()
			_sync_exp_events()
			_enter_result()
	elif _selftest:
		_selftest_run()
	# 截图/回归用：走**真正的那条点击路径**（按钮 id → _activate），
	# 而不是像 `--bld=` 那样直接赋状态。
	#
	# 为什么需要它：`--bld=` 绕过了点击分发，所以「点了没反应」这类 bug
	# 截图全绿也看不见——M30 修的那个漏赋 `_state` 就是这么活下来的。
	# 支持逗号分隔的连续点击（`--click=roster_page,hero_info:crusader`）：
	# 「先进名册页、再点开一个人」这类两步流程，一次点击验不到。
	if not _boot_click.is_empty():
		for step in _boot_click.split(","):
			var one: String = step.strip_edges()
			if one.is_empty():
				continue
			print("模拟点击：%s → 状态 %d" % [one, _state])
			_activate(one)
		print("点击后状态：%d（S_TOWN=%d S_BUILDING=%d S_GUILD=%d S_ROSTER=%d）" % [
			_state, S_TOWN, S_BUILDING, S_GUILD, S_ROSTER])
	if _boot_tap.x >= 0.0:
		print("坐标点击：%s → 命中 %s" % [str(_boot_tap), _hit_id_at(_boot_tap)])
		_on_click(_boot_tap)
		print("坐标点击后浮层: '%s'" % _roster_open)
	_sk_panel = _skin.texture("skin", "panel")
	_sk_card = _skin.texture("skin", "card")
	_sk_grain = _skin.texture("skin", "grain")
	_sk_stain = _skin.texture("skin", "stain")
	_sk_btn = _skin.texture("skin", "btn")
	_sk_banner = _skin.texture("skin", "banner")
	_sk_divider = _skin.texture("skin", "divider")
	_sk_orn = _skin.texture("skin", "orn")
	# dock 图标在这里预热：等到第一次 `_draw()` 才 load 的话，
	# 那一帧画出来的是一块纯白，玩家会看到闪一下。
	for _k in ["town", "gate", "shop"]:
		_dock_icon(_k)
	_apply_safe_area()
	if not _want_town_layout.is_empty():
		_load_town_layout(_want_town_layout)
	# 有没打完的远征就直接接着打（M117）。
	#
	# 原来要玩家回城镇、再点一次右下角的「继续远征」——那不叫继续，那叫重新进入。
	# 玩家按 Home 回个消息、回来应该站在原地，而不是被送回城门口。
	# 验收参数（`--shot=` / `--click=` / `--bld=` 等）一律不自动恢复：
	# 那些场景要的是可预测的初始状态，自动跳进远征会让截图全是地图。
	if campaign != null and not campaign.expedition_run.is_empty() \
			and (_boot_resume or (_shot_path.is_empty() and _boot_click.is_empty() \
			and _boot_building.is_empty() and not _auto and not _selftest \
			and not _boot_prep and _phone_size.x <= 0)):
		_resume_expedition()
	# 出征名单在**这里**统一初始化一次（M176）。
	# 原来每个屏各初始化各自的（名册/队伍/出征屏各一处），
	# 于是没进过那几屏就直接开公会的玩家，看到的全是「空闲」——
	# 而实际上默认名单是有人的。
	if campaign != null and _prep_party.is_empty():
		_prep_party = _party_restore(_prep_level)
	queue_redraw()


## 让出顶部 / 底部安全区（M58 顶部，M63 补底部）。
##
## 真机上取 `DisplayServer.get_display_safe_area()`，桌面端没有这个概念，
## 靠 `--safe-top=` / `--safe-bottom=` 模拟。
##
## 做法是改根 Control 的 `offset_top` / `offset_bottom`：内容整体内缩、`size.y` 同步变短，
## 所有「贴底」的布局（战斗底部三段、地图按钮、各屏返回键、城镇休整键）会自动跟着上移，
## 不用逐屏改坐标。让出来的那两条用纯黑 ColorRect 盖住 —— 它比窗口的清屏色更深，
## 视觉上和手机边框连成一片。
##
## 底部这块不能省：安卓全面屏的手势条就压在最底那排按钮上，
## 按钮照画、照显示，只是点不到 —— 截图验收永远发现不了。
func _apply_safe_area() -> void:
	var vh: float = float(ProjectSettings.get_setting("display/window/size/viewport_height"))
	if OS.has_feature("android"):
		var wh: float = float(DisplayServer.window_get_size().y)
		var safe: Rect2i = DisplayServer.get_display_safe_area()
		if wh > 0.0 and safe.size.y > 0:
			var k: float = vh / wh
			if safe.position.y > 0:
				_safe_top = float(safe.position.y) * k
			# 底部内缩 = 窗口高 -（安全区顶 + 安全区高），含手势条与圆角下巴
			var ins: float = wh - float(safe.position.y + safe.size.y)
			if ins > 0.0:
				_safe_bottom = ins * k
	if _want_safe_top > 0.0:
		_safe_top = _want_safe_top
	if _want_safe_bottom > 0.0:
		_safe_bottom = _want_safe_bottom
	_safe_top = clampf(_safe_top, 0.0, 160.0)
	_safe_bottom = clampf(_safe_bottom, 0.0, 160.0)
	if _safe_top < 1.0 and _safe_bottom < 1.0:
		return
	offset_top = _safe_top
	offset_bottom = -_safe_bottom
	if _safe_top >= 1.0:
		_safe_mask(true)
	if _safe_bottom >= 1.0:
		_safe_mask(false)


## 安全区黑底板。用锚点定位而不是写死矩形 —— 窗口尺寸一变它自己跟着走。
func _safe_mask(is_top: bool) -> void:
	var mask := ColorRect.new()
	mask.color = Color(0.0, 0.0, 0.0, 1.0)
	mask.mouse_filter = Control.MOUSE_FILTER_IGNORE
	# 横向铺满父 Control
	mask.anchor_left = 0.0
	mask.anchor_right = 1.0
	mask.offset_left = 0.0
	mask.offset_right = 0.0
	if is_top:
		# 父 Control 的顶边已经下移了 _safe_top，往上画回去
		mask.anchor_top = 0.0
		mask.anchor_bottom = 0.0
		mask.offset_top = -_safe_top
		mask.offset_bottom = 1.0
	else:
		# 父 Control 的底边已经上移了 _safe_bottom，往下画出去
		mask.anchor_top = 1.0
		mask.anchor_bottom = 1.0
		mask.offset_top = 0.0
		mask.offset_bottom = _safe_bottom + 1.0
	add_child(mask)


## 截图/回归用：出发后直接拉一场战斗（`--start --battle`）。
##
## 为什么需要它：战斗屏这一屏的变化（单位图形、补间）只能靠截图验证，
## 而靠 `--auto` 走到第一场遭遇，时间点不确定，截十次有八次落在别的屏上。
##
## 优先取图里现成的战斗房；图上没有就按遭遇表现抽一场——
## 后者保证任何种子都能截到战斗屏。
func _boot_into_battle() -> void:
	if exp == null or exp.ended:
		return
	var step: Dictionary = {}
	if exp.map_mode and not exp.map.is_empty():
		for id in (exp.map["room_ids"] as Array):
			var st: Dictionary = ((exp.map["rooms"][int(id)] as Dictionary).get("step", {}) as Dictionary)
			if str(st.get("kind", "")) == "battle":
				step = st.duplicate(true)
				break
	if step.is_empty():
		step = RouteGen.encounter_block(db, _dungeon, _level)
	if step.is_empty():
		return
	_battle = exp.start_battle(step)
	if _battle == null:
		return
	_battle_corridor = bool(step.get("corridor", false))
	_summoned_uids.clear()
	_battle.decision_provider = func(_b: Battle, _a: Combatant) -> Dictionary: return {}
	_ev_pos = 0
	_options = []
	_pending = {}
	# 和正常进战斗同一套界面初始化（M65）：验收路径不能比玩家路径少东西，
	# 否则「截图里没有行动序条」到底是没画还是没跑到，分不清。
	_order_ids = []
	_order_cur = -1
	_retreat_arm = false
	_info_uid = -1
	_banner_t = 1.7
	_state = S_BATTLE
	# `--be-demo`（M65）：把结算卡钉在屏幕上。伪造一份掉落，
	# 好让「金币 + 祖传物 + 饰品」三种行都能一次看全。
	if _show_battle_end:
		_be_data = {"rounds": 7, "gain": {"gold": 87,
			"heirlooms": {"crest": 2, "bust": 1}, "trinkets": 1}}
		_be_timer = 0.0
		_state = S_BATTLE_END
	elif _retreat_demo:
		# 直接走第二下（第一下只是上膛，验收里不必演两遍）
		_do_retreat()
	elif _corpse_demo:
		# 交给 `_begin_player_turn` 处理：在那里 `_battle` 一定是 UI 正在画的那个
		# 实例（`--start --battle` 这条链路会 start 两次战斗，在 `_boot_into_battle`
		# 里杀了另一场的敌人，界面上什么都看不到）。
		pass


## 自检专用：当前可选技能里第一个守护技的下标，没有返回 -1。
##
## 不写死索引（defender 在第 4 个）是为了换职业/换数据时自检不会假装通过：
## 找不到就不测，而不是拿错技能去点。
func _find_guard_option() -> int:
	for i in _options.size():
		var op: Dictionary = _options[i]
		# M65：`_options` 现在包含「站位不符」的招，跳过它们。
		# 不跳的话，自检会选中一个用不了的守护技，然后 guarded_ok 永远是 false——
		# 报的却是「守护关系没建立」，查半天发现是选项列表换了语义。
		if not bool(op.get("usable", true)):
			continue
		if bool((op.get("action", {}) as Dictionary).get("is_guard", false)):
			return i
	return -1


## 自检专用：第一个真正能用的技能下标（M65）。
##
## `_options` 换成 `all_options` 之后，0 号技能有可能因为站位不符而不存在。
## 自检若还是死点 `skill:0`，会「点了没反应」并继续循环 —— 表现出来是跑到
## 预算上限停在战斗屏，而不是一条能看懂的报错。
func _first_usable_option() -> int:
	for i in _options.size():
		if bool((_options[i] as Dictionary).get("usable", true)):
			return i
	return -1


## 端到端自检：不改一行规则，只走界面自己的那条路
## （出发 → 地图 → 战斗 → 选技能 → 选目标 → 结算），
## 用来验证「界面接线」有没有断开。这类断裂不会让规则测试变红，
## 只会让玩家点了没反应。
## 自检专用：朝出口走一步。到了出口就离开。
func _selftest_move() -> void:
	if exp == null or exp.ended:
		_enter_result()
		return
	# 到了出口还要看任务达没达成（M32）：清剿任务走到出口但还有仗没清时，
	# 现在离开只能是「未完成」——AI 应该把剩下的仗打完，而不是照旧走人。
	# 对探索任务这一条不改变任何行为（at_goal ⇒ quest_met）。
	if exp.at_goal() and exp.quest_met():
		_leave_dungeon()
		return
	var nxt: int = _pick_step()
	if nxt < 0:
		_leave_dungeon()
		return
	_travel_to(nxt)


## 下一步往哪走。默认朝出口；任务有明确目标时先去做目标。
##
## M32 只处理清剿（战斗房），M33 加上收集/激活（指定奇物）。
## 三种目标共用同一条「找最近的目标 → 朝它走」的骨架，
## 差别只在「目标是什么」——所以分别写成一个返回房间号的函数。
func _pick_step() -> int:
	if exp == null:
		return -1
	if exp.quest_met():
		return _step_toward_goal()
	var kind: String = str(exp.quest_goal.get("kind", ""))
	var target: int = -1
	match kind:
		QuestGoal.KIND_BATTLE:
			target = _nearest_uncleared_battle()
		QuestGoal.KIND_GATHER, QuestGoal.KIND_ACTIVATE:
			target = _nearest_quest_target()
	if target >= 0 and target != exp.current_room:
		var st: int = _step_toward_room(target)
		if st >= 0:
			return st
	# 已经到了出口、又没有别的目标可做：走人。结算会把它判成「未完成」，
	# 那是合法结果（和清剿没清完就走是同一种），不是失败。
	if exp.at_goal():
		return -1
	return _step_toward_goal()


## 离得最近的任务目标奇物所在房间（M33）。
##
## 房间里的目标奇物直接就是候选；走廊里的要取两端——奇物挂在边上，
## 走到任意一端都会触发。取两端里更近的那个，AI 才不会绕远路。
func _nearest_quest_target() -> int:
	var cid: String = str(exp.quest_goal.get("curio", ""))
	if cid.is_empty() or exp.map.is_empty():
		return -1
	var m: Dictionary = exp.map
	var rooms: Dictionary = m["rooms"]
	var ids: Array = m["room_ids"]
	var n: int = ids.size()
	var pairs: Array = []
	for e in (m["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var adj: Dictionary = MapGen.adjacency_rooms(n, pairs)
	var dist: Array = MapGen.bfs(n, adj, exp.current_room)
	var best: int = -1
	var best_d: int = 1 << 30
	for id in ids:
		var rid: int = int(id)
		var r: Dictionary = rooms[rid]
		var st: Dictionary = r.get("step", {})
		if str(st.get("curio", "")) != cid:
			continue
		if bool(r.get("visited", false)):
			continue
		var d: int = int(dist[rid])
		if d >= 0 and d < best_d:
			best_d = d
			best = rid
	for e2 in (m["edges"] as Array):
		if bool((e2 as Dictionary).get("walked", false)):
			continue
		var steps: Array = (e2 as Dictionary).get("steps", [])
		if steps.is_empty() or str((steps[0] as Dictionary).get("curio", "")) != cid:
			continue
		for endp in [int(e2.a), int(e2.b)]:
			var d2: int = int(dist[endp])
			if d2 >= 0 and d2 < best_d:
				best_d = d2
				best = endp
	return best


## 离得最近的、还没打过的战斗房。
##
## 「还没打过」用 `visited` 判：房间的 step 只在第一次进门时触发，
## 所以到过就等于清过（同地图屏那个变暗标记，两处必须同一条判据）。
func _nearest_uncleared_battle() -> int:
	var m: Dictionary = exp.map
	if m.is_empty():
		return -1
	var rooms: Dictionary = m["rooms"]
	var ids: Array = m["room_ids"]
	var n: int = ids.size()
	var pairs: Array = []
	for e in (m["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var adj: Dictionary = MapGen.adjacency_rooms(n, pairs)
	# 以**当前房间**为源做一次 BFS：这样能往回走，而不是只会朝出口方向搜。
	var dist: Array = MapGen.bfs(n, adj, exp.current_room)
	var best: int = -1
	var best_d: int = 1 << 30
	for id in ids:
		var rid: int = int(id)
		var r: Dictionary = rooms[rid]
		var k: String = str(r.get("kind", ""))
		if k != MapGen.K_BATTLE and k != MapGen.K_BOSS:
			continue
		if bool(r.get("visited", false)):
			continue
		var d: int = int(dist[rid])
		if d >= 0 and d < best_d:
			best_d = d
			best = rid
	return best


## 朝某个房间走一步：以目标为源做 BFS，选距离更小的邻居。
##
## 不能复用 `_dist_table()`——那张表是「到出口的距离」，
## 目标不是出口时会把人往反方向带（而且不报错，只是越走越远）。
func _step_toward_room(target: int) -> int:
	var m: Dictionary = exp.map
	var n: int = (m["room_ids"] as Array).size()
	var pairs: Array = []
	for e in (m["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var adj: Dictionary = MapGen.adjacency_rooms(n, pairs)
	var dist: Array = MapGen.bfs(n, adj, target)
	var cur_d: int = int(dist[exp.current_room])
	var nbs: Array = exp.adjacent()
	for nb in nbs:
		var rid: int = int(nb.room)
		if int(dist[rid]) == cur_d - 1:
			return rid
	return int((nbs[0] as Dictionary).room) if not nbs.is_empty() else -1


func _step_toward_goal() -> int:
	if _explore:
		return _step_explore()
	var dist: Array = _dist_table()
	var cur: int = exp.current_room
	for nb in exp.adjacent():
		var rid: int = int(nb.room)
		if int(dist[rid]) == int(dist[cur]) - 1:
			return rid
	var nbs: Array = exp.adjacent()
	return int((nbs[0] as Dictionary).room) if not nbs.is_empty() else -1


## 探索策略：先走「没去过且不后退」的邻居，没有就走最短路径。
##
## 为什么要限制「不后退」：允许回头的话会在死胡同里来回走，
## 把预算烧光却什么都拿不到。`<= cur` 这个条件保证每一步都在朝目标
## 或者横向移动，不会离目标更远。
##
## 走完侧支线之后自动回到最短路径——因为下一步就没有未访问的邻居了。
func _step_explore() -> int:
	var dist: Array = _dist_table()
	var cur: int = exp.current_room
	var cur_d: int = int(dist[cur])
	var side: Array = []
	var forward: Array = []
	var nbs: Array = exp.adjacent()
	for nb in nbs:
		var rid: int = int(nb.room)
		var d: int = int(dist[rid])
		if not _seen_rooms.has(rid) and d <= cur_d:
			side.append(rid)
		if d == cur_d - 1:
			forward.append(rid)
	if not side.is_empty():
		return int(side[0])
	if not forward.is_empty():
		return int(forward[0])
	return int((nbs[0] as Dictionary).room) if not nbs.is_empty() else -1


## 到目标的 BFS 距离**表**（按房间 id 索引）。
##
## 注意别和 `_dist_to_goal()` 混：那个返回「自己离出口还有几步」，
## 是个标量，界面用来显示提示；这个是每个房间到出口的距离，走路决策要用。
## M18 一开始就撞了名，撞出的报错是「不能把 int 赋给 Array」。
func _dist_table() -> Array:
	var m: Dictionary = exp.map
	var n: int = (m["room_ids"] as Array).size()
	var pairs: Array = []
	for e in (m["edges"] as Array):
		pairs.append(Vector2i(int(e.a), int(e.b)))
	var adj: Dictionary = MapGen.adjacency_rooms(n, pairs)
	return MapGen.bfs(n, adj, int(m["goal"]))


func _selftest_run() -> void:
	# 上一趟全灭又没钱时，玩家会去点「免费征召」。自检也照做，
	# 否则第二次跑就会停在城镇里，看起来像失败，其实是没模拟那一步操作。
	# 注意要**补满**而不是补一个：单人出门必死，只补一个等于把死循环演一遍。
	if campaign.alive_ids().is_empty():
		var n: int = 0
		for hid in campaign.hero_ids():
			if campaign.can_recruit(hid):
				campaign.recruit(hid)
				n += 1
		if n > 0:
			campaign.save()
			print("SELFTEST 名册为空，免费征召 %d 人" % n)
	_start_expedition(_size, _level, {}, [], _boot_quest)
	_seen_rooms = {}
	if exp != null:
		_seen_rooms[int(exp.current_room)] = true
	var guard: int = 0
	var acted: int = 0
	var battles: int = 0
	_move_checked = false
	moved_ok = false
	_guard_checked = false
	guarded_ok = false
	forced_moves = 0
	shuffle_moves = 0
	move_resists = 0
	summons = 0
	summon_fails = 0
	# 循环预算：每轮处理一个动作（一次点击/一回合推进/一步移动）。
	# 600 在 M16 之前够用，M17 把奇物密度从 0.6 提到 3.5 个/趟之后不够了——
	# 奇物交互要占轮次，而且它们带来的掉血/加压让战斗回合变长。
	# 超预算的表现是停在 S_BATTLE（state=2），看起来像「没走到结算屏」。
	while guard < 1200:
		guard += 1
		if _state == S_RESULT:
			break
		if _state == S_MAP:
			_selftest_move()
			continue
		if _state == S_BATTLE and _battle != null:
			if _battle.awaiting_input != null:
				# 自检也要走一次「调整站位」——M9 之前站位是静态的，
				# 这条路径（按钮 → submit_move → perform_move）没有任何测试覆盖，
				# 而它正是玩家手里唯一能改阵型的入口。
				var who: Combatant = _battle.awaiting_input
				if not _move_checked and not _battle.move_options(who).is_empty():
					_move_checked = true
					var spots: Array = _battle.move_options(who)
					var before_rank: int = who.rank
					_move_mode = true
					_activate("goto:%d" % int(spots[0]))
					moved_ok = moved_ok or (who.rank != before_rank)
					continue
				# 自检也要走一次「守护」：点技能 → 点队友 → 关系建立。
				# 规则层对了不代表这条路径通——按钮的 rect、目标池、_pending 的状态机
				# 任何一环断了，玩家只会看到「点了守护，什么也没发生」。
				if not _guard_checked:
					var gi: int = _find_guard_option()
					if gi >= 0:
						var opt: Dictionary = _options[gi]
						_guard_checked = true
						_activate("skill:%d" % gi)
						if not _pending.is_empty():
							var mates: Array = _pending.get("targets", [])
							if not mates.is_empty():
								_pick_target(int((mates[0] as Combatant).uid))
								guarded_ok = _battle.guard_target_of(who.uid) != null
								acted += 1
								continue
				if _options.is_empty():
					_submit({}, [])
				else:
					var si: int = _first_usable_option()
					if si < 0:
						_submit({}, [])
					else:
						_activate("skill:%d" % si)
						if not _pending.is_empty():
							var pool: Array = _pending.get("targets", [])
							if pool.is_empty():
								_submit({}, [])
							else:
								_pick_target(int((pool[0] as Combatant).uid))
					acted += 1
				if int(_battle.round_index) == 1 and acted == 1:
					battles += 1
			else:
				_battle_step()
			continue
		break

	var s: Dictionary = exp.summary() if exp != null else {}
	print("SELFTEST 状态=%d 推进=%d/%d 玩家出手=%d 结束原因=%s" % [
		_state, int(s.get("steps_done", 0)), int(s.get("steps_total", 0)),
		acted, str(s.get("end_reason", "?"))])

	# —— 元层闭环：入账 → 存档 → 重新读档 → 数值必须一致 ——
	var gold_after: int = campaign.gold
	var alive_after: int = campaign.alive_ids().size()
	# 入账**不判 PASS**，只报数。
	#
	# 试过两版判据，都不成立：
	#   1.0 `end_reason == "wipe"` 才允许零收入 → 「一场没打就撤退」被误判。
	#   2.0 `battles > 0` 就该有钱 → 遇到 `loot: NONE` 的怪组照样零收入。
	#      （`monsters.json` 里 17 只怪的 loot 就是 NONE，那是数据事实。）
	# 真正能判的是「存档往返一致」，那条已经在下面硬判。
	# 收入是遭遇决定的，和位移/召唤一样，不该由玩家行为保证。
	var fight_n: int = int(s.get("battles", 0))
	var loot_ok: bool = true
	var probe := Campaign.new()
	probe.setup_from_cfg(db.campaign_cfg, _save_path)
	var reloaded: bool = probe.load_or_new()
	var save_ok: bool = reloaded and probe.gold == gold_after \
		and probe.alive_ids().size() == alive_after \
		and probe.expeditions == campaign.expeditions
	print("SELFTEST 战利品 金币=%d 传家宝=%d 战斗=%d 结束=%s 入账=%s" % [
		gold_after, campaign.heirloom_total(), fight_n, str(s.get("end_reason", "?")),
		"OK" if loot_ok else "FAIL"])
	print("SELFTEST 存档往返 %s（远征 %d 趟，存活 %d 人）" % [
		"OK" if save_ok else "FAIL", probe.expeditions, probe.alive_ids().size()])

	print("SELFTEST 站位调整 %s" % (
		"OK" if moved_ok else ("未触发（这场没有可挪的单位）" if not _move_checked else "FAIL 选择了移动但 rank 没变")))
	print("SELFTEST 守护 %s" % (
		"OK" if guarded_ok else ("未触发（队伍里没人能守护）" if not _guard_checked else "FAIL 点了守护但关系没建立")))
	# 位移只报数：它取决于这趟路线里有没有带位移技能的怪，
	# 不像守护那样由玩家自己点，所以不能拿它判 PASS。
	if forced_moves > 0 or shuffle_moves > 0:
		print("SELFTEST 位移 推拉=%d 洗位=%d 抵抗=%d" % [forced_moves, shuffle_moves, move_resists])
	else:
		print("SELFTEST 位移 未触发（本趟没有带位移技能的敌人）")
	# 召唤同理：由遭遇决定，不能拿它判 PASS。
	if summons > 0:
		print("SELFTEST 召唤 成功=%d 失败=%d" % [summons, summon_fails])
	else:
		print("SELFTEST 召唤 未触发（本趟没有会召唤的敌人，或它们没选这个技能）")
	# 怪癖：同样只报数。默认名册开局没有怪癖，能不能拿到全靠这趟碰了什么奇物，
	# 拿它判 PASS 等于要求「这趟必须踩到坑」。
	var q_gain: int = int(s.get("quirks_gained", 0))
	var q_have: int = int(s.get("quirks_total", 0))
	if q_gain > 0 or q_have > 0:
		print("SELFTEST 怪癖 获得=%d 在手=%d 染病=%d 抗病=%d 清负面=%d" % [
			q_gain, q_have, int(s.get("diseases_contracted", 0)),
			int(s.get("diseases_resisted", 0)), int(s.get("quirks_purged", 0))])
	else:
		print("SELFTEST 怪癖 未触发（本趟奇物 %d 次，其中没有给怪癖的分支）" % int(s.get("curios", 0)))
	# 饰品：这趟谁戴了、掉了什么、进没进仓库。
	# 这里只报数不判 PASS——「这趟没掉饰品」不是失败，
	# 拿它当断言等于要求每次都得开箱出货。
	var worn: int = int(s.get("trinkets_equipped", 0))
	var drops: int = int(s.get("trinkets", 0))
	var got_ids: Array = (s.get("trinket_ids", []) as Array)
	if worn > 0 or drops > 0:
		print("SELFTEST 饰品 佩戴=%d 掉落=%d 有id=%d 样例=%s" % [
			worn, drops, got_ids.size(), str(got_ids.slice(0, 3))])
	else:
		print("SELFTEST 饰品 未触发（这趟没人戴、也没掉到；仓库 %d 件）" % campaign.trinket_store.size())

	# 循环是怎么退出的？预算用完 vs 正常走到结算屏，是两种完全不同的病：
	# 前者说明「这一趟真的需要更多动作」，后者说明「卡在一个不推进的状态里」。
	# 不打印这个数就只能靠猜——M18 这里连挂两次才想到要加。
	if _state != S_RESULT:
		var bt: Battle = _battle
		print("SELFTEST 诊断 循环用了 %d/%d 轮  state=%d  战斗轮=%d  待输入=%s  待结算=%s" % [
			guard, 1200, _state,
			(bt.round_index if bt != null else -1),
			(bt.awaiting_input != null if bt != null else false),
			(exp.has_pending() if exp != null else false)])

	# 内容密度：地图上**有**多少 vs 这一趟**遇到**多少。
	# 两个数差很多——玩家只走一条路，图上的奇物大半碰不到。
	# M13 说「奇物几乎不出现」，M17 调密度，靠的就是这一栏。
	print("SELFTEST 内容 奇物=%d 陷阱=%d 障碍=%d 饥饿=%d 房间=%d 步数=%d" % [
		int(s.get("curios", 0)), int(s.get("traps", 0)), int(s.get("obstacles", 0)),
		int(s.get("hunger_checks", 0)), int(s.get("rooms_visited", 0)), int(exp.step_index)])
	# 首领任务（M20）：任务是 kill_boss 时，终点房间必须真的有一场首领战。
	# 「地图生成了 boss 房」和「这一趟打到了 boss」是两件事——
	# 走不到终点、或者中途团灭，击杀就是 false，这栏要把这两种情况分开报。
	if exp.quest_type == "kill_boss":
		print("SELFTEST 首领 任务=%s 打到=%s 击杀=%s 结果=%s" % [
			exp.quest_type, str(bool(s.get("boss_fought", false))),
			str(bool(s.get("boss_killed", false))), exp.end_reason])

	# 任务目标（M32 / M33）：类型、目标、达成与否、各类进度。
	# 自检走最短路径，所以清剿/收集「走到出口但没做完」是**正常结果**——
	# 这一行要把这种情况和「机制坏了」区分开。
	print("SELFTEST 任务 类型=%s 目标=%s 达成=%s 奇物=%s 战斗房=%d/%d 收集=%d 激活=%d 物品用=%d 缺=%d" % [
		exp.quest_type, str(exp.quest_goal.get("kind", "")), str(exp.quest_met()),
		str(exp.quest_goal.get("curio", "")),
		int(exp.stats.get("quest_battles_cleared", 0)), int(exp.stats.get("quest_battles_total", 0)),
		int(exp.stats.get("quest_gathered", 0)), int(exp.stats.get("quest_activated", 0)),
		int(exp.stats.get("quest_items_used", 0)), int(exp.stats.get("quest_items_missing", 0))])

	# 失败时要说清是哪一项挂了。之前只打一个 FAIL，
	# 遇到偶发（跑五次过一次）根本没法查——那等于自己给自己出难题。
	var bad: Array = []
	# 短图偶尔整张没有战斗房（随机地图），那时候「没出手」不是接线问题。
	# 判据要看「图上到底有没有战斗房」，不是看有没有出手——
	# 否则每跑几次就会假警报一次，而假警报比没警报更伤人。
	var rooms_battle: int = 0
	if exp != null and exp.map_mode and not exp.map.is_empty():
		for rid in (exp.map["room_ids"] as Array):
			var st: Dictionary = ((exp.map["rooms"][int(rid)] as Dictionary).get("step", {}) as Dictionary)
			if str(st.get("kind", "")) == "battle":
				rooms_battle += 1
	if acted <= 0 and rooms_battle > 0:
		bad.append("玩家一次都没出手")
	# 胜利屏也算走完（M46）：打完第四个首领的那一趟不会停在结算屏。
	if _state != S_RESULT and _state != S_VICTORY:
		bad.append("没走到结算屏（state=%d）" % _state)
	if not loot_ok:
		bad.append("战利品入账可疑（金币 %d，结束原因 %s）" % [
			gold_after, str(s.get("end_reason", "?"))])
	if not save_ok:
		bad.append("存档往返不一致（档内金币 %d / 内存 %d，档内活人 %d / 内存 %d）" % [
			probe.gold, gold_after, probe.alive_ids().size(), alive_after])
	if _move_checked and not moved_ok:
		bad.append("站位调整失败")
	if _guard_checked and not guarded_ok:
		bad.append("守护关系没建立")
	# 「结算说完成了」和「任务目标达成了」必须是同一件事（M32）。
	# 清剿的自检走最短路径，所以经常走到出口却没清完——那是**合法的未完成**，
	# 不是失败。真正要抓的是反过来的情况：判据坏了，什么都没清也算完成。
	if exp != null and exp.end_reason == "complete" and not exp.quest_met():
		bad.append("结算写了完成，但任务目标没达成")
	var pass_all: bool = bad.is_empty()
	print("SELFTEST %s%s" % ["PASS" if pass_all else "FAIL",
		"" if pass_all else "： " + "；".join(bad)])
	get_tree().quit(0 if pass_all else 1)


# ============================================================
# 开局
# ============================================================

## `pack` 是出发前买的补给。**默认空 = 不覆盖**：自动代打、bench、
## 以及「钱不够按保底包出发」都走这条，所以历史行为逐位不变。
func _start_expedition(size_name: String, level: int, pack: Dictionary = {},
		picked: Array = [], quest: String = "explore") -> void:
	# 名册现在有 5 人、出战上限 4 人。**必须在这里夹住**——
	# 战斗层的 rank 只有 0–3，多一个人会站到第 5 位，目标掩码选不中他，
	# 表现是「队伍里有个永远不被打也不会被治疗的人」。
	var party: Array = picked.duplicate() if not picked.is_empty() \
		else _party_for(level)
	if party.size() > Campaign.PARTY_MAX:
		party = party.slice(0, Campaign.PARTY_MAX)
	if party.is_empty():
		_flash_msg("名册里没有可出发的英雄")
		return

	_size = size_name
	_level = level
	_battle_no = 0
	match quest:
		"kill_boss":
			_flash_msg("首领任务：终点房间必有一战")
		"cleanse":
			# 压到 16 字（M204）：原来 23 字，34 号要折两行，第二行会压住房间面板标题。
			# 完整的判据在房间面板的「任务」那一行里（带进度），这里只说结论。
			_flash_msg("清剿任务：全图战斗打完才算完成")
		"inventory_activate":
			_flash_msg("仪式任务：带着任务物品去激活，用完就没了")
		_:
			pass
	var m: Dictionary = MapGen.build(db, _dungeon, _size, _level, DdRng.new(randi()), quest)
	if m.is_empty():
		_flash_msg("地图生成失败")
		return

	# 装备阶来自城镇（花钱升的），不是路线白送的
	var gear: Dictionary = {}
	var skill: Dictionary = {}
	for hid in party:
		gear[hid] = campaign.gear_of(hid)
		# 每个技能各自的等级（M126）
		skill[hid] = campaign.skill_levels_map([hid]).get(str(hid), {})

	exp = Expedition.new()
	# 等级惩罚（M25 / M29）：低一级，进本 +20 压力，之后每次受压 +25%。
	# 进本压力**必须在 setup 之前赋**——队伍状态是在 setup 里建的，晚一步就白赋；
	# 受压倍率是每场战斗开始时读的，晚一点赋没关系，但放一起更清楚。
	var js: Dictionary = {}
	var js_mult: Dictionary = {}
	for hid_j in party:
		js[str(hid_j)] = campaign.entry_stress(str(hid_j), _level)
		js_mult[str(hid_j)] = campaign.stress_mult_for(str(hid_j), _level)
	exp.join_stress = js
	exp.join_stress_mult = js_mult
	# 名册实例 id → 职业 id（M34）。`party` 里装的是实例（可能是 `crusader#2`），
	# 而数值表、技能表、饰品职业限制全都按职业查，所以这张映射必须一起递下去。
	var defs: Dictionary = {}
	for hid_d in party:
		defs[str(hid_d)] = campaign.def_of(str(hid_d))
	exp.setup(db, party, [], db.expedition_cfg.preset(_preset), randi(), _preset,
		_loot_cfg(), gear, defs)
	exp.hero_skill = skill
	# 技能组（M19）：只传这四个人带的 4 个技能，没上路的人不影响战斗。
	exp.hero_loadout = campaign.loadout_map(party)
	# 怪癖跟人走：把这趟出发的四个人身上的怪癖灌进去。
	# 没上路的人不会在别处中招，所以只传 party 而不是整个名册。
	exp.seed_quirks(campaign.quirk_map_for(party))
	# 装备同理：只带这四个人身上的，仓库里的留在城里。
	exp.set_hero_trinkets(campaign.equipped_map())
	# 补给：买了就按买的带，没买（或钱不够）就走默认包。
	exp.set_start_supplies(pack)
	exp.set_location(_dungeon, _size, _level, quest)
	exp.enter_map(m)

	_log.clear()
	_exp_ev_pos = 0
	_settled = false
	_settle_gain = {}
	_sync_exp_events()
	_battle = null
	_state = S_MAP
	# 出发就落一次盘（M116）：这样「只要出发过，就一定有得恢复」，
	# 不必等到打完第一场才第一次写。切后台丢整趟的洞从这里堵上。
	_exp_persist()
	var goal_word: String = "首领" if quest == "kill_boss" else "出口"
	_add_log("出发：%s %s · %d 间房 · 入口到%s约 %d 步 · 队伍 %d 人" % [
		DdNames.dungeon_name(_dungeon), _size_name_of(_size),
		(m["room_ids"] as Array).size(), goal_word, int(m["shortest"]), party.size()],
		DdTheme.TEXT)
	queue_redraw()


func _loot_cfg() -> Dictionary:
	var lc: Dictionary = (campaign.cfg.get("loot", {}) as Dictionary).duplicate(true)
	lc["heirloom_names"] = campaign.cfg.get("heirlooms", [])
	return lc


## 进结算屏：把战利品入账、英雄状态落盘、存档。只做一次。
## 这一步要不要停下来放房间卡（M74）。
##
## 拦「房间里的战斗和奇物」（M103）。
##
## 原来只拦奇物：战斗房是**进房直接开打**，中间没有任何停顿，
## 于是「走廊刚打完、画面一闪、又在打」——玩家分不清这是同一场还是新一场，
## 也看不出自己刚进了房间。
##
## 现在战斗房也要先弹卡：卡上写「这里有什么动静」，点「探索」才开打。
## 打完回到同一张卡上弹结果，再点「继续赶路」回地图。
##
## 仍然不拦：
##   · 走廊步骤带 `corridor: true`，一路走一路停会把节奏拖死；
##   · 空房间没有 step，本来就不会进这里。
func _room_should_pause(step: Dictionary) -> bool:
	if _selftest or _auto or _skip_battles:
		return false
	if bool(step.get("corridor", false)):
		return false
	var k: String = str(step.get("kind", ""))
	return k == "curio" or k == "battle"


func _room_open(step: Dictionary) -> void:
	_room_step = step
	_room_kind = str(step.get("kind", ""))
	_room_room = int(step.get("room", exp.current_room))
	_room_phase = 0
	_room_lines = []
	_state = S_ROOM
	queue_redraw()


## 房间卡上的那颗按钮：第一下结算，第二下回地图继续走。
func _room_go() -> void:
	if _room_phase == 0:
		_room_phase = 1
		# 结算前记日志长度，结果卡直接用**刚写进去的那几行**。
		# 另维护一套文案迟早会和日志对不上（日志说掉血、卡片说没事）。
		var before: int = _log.size()
		match _room_kind:
			"battle":
				# 从卡片上开战（M103）。这一段和地图步进里的开战逻辑必须一致
				# （决策 provider、事件游标、行动序、瞄准态都要重置），
				# 否则会带着上一场的残留进新战斗。
				var nb: Battle = exp.start_battle(_room_step)
				if nb == null:
					_room_phase = 1
					_room_lines = ["这里已经没有东西了。"]
					queue_redraw()
					return
				_room_battle = true
				_battle = nb
				_battle_no += 1
				_battle_corridor = false
				_summoned_uids.clear()
				_battle.decision_provider = func(_b: Battle, _a: Combatant) -> Dictionary: return {}
				_ev_pos = 0
				_options = []
				_pending = {}
				_order_ids = []
				_order_cur = -1
				_step_timer = 0.20
				_state = S_BATTLE
				queue_redraw()
				return
			"curio":
				# 有可用道具就先问（M161）。原来 `curio_auto_item_enabled`
				# 会**自动**挑背包里第一件能用的扣掉 —— 玩家买了一背包补给，
				# 走着走着没了，完全不知道花在哪。现在停一下问一句。
				var ask_id: String = str(_room_step.get("curio", ""))
				var cand: String = _curio_candidate(ask_id)
				if not cand.is_empty():
					_curio_ask = {"step": _room_step.duplicate(true),
						"curio": ask_id, "item": cand}
					_room_step = {}
					_room_phase = 2
					queue_redraw()
					return
				exp.resolve_curio(_room_step)
			"trap":
				exp.resolve_trap(_room_step)
			"obstacle":
				exp.resolve_obstacle()
		_room_step = {}
		_fill_room_lines(before)
		return
	_state = S_MAP
	_room_step = {}
	_room_lines = []
	_drain_queue()


## 房间环境描述（M74）。每种房间三句，用**房间编号**选一句 —— 不碰随机源。
const ROOM_FLAVOR: Dictionary = {
	"curio": [
		"空气里有旧木头和铁锈混在一起的味道。",
		"墙角堆着东西，看上去有人比你先到过。",
		"火把只照到一半，剩下的地方得走近了才看得清。",
	],
	"trap": [
		"地砖的缝隙比别处宽，边缘有细碎的划痕。",
		"头顶的影子不太对劲，像是有什么被吊着。",
		"脚下的地面比周围软，踩上去有一声轻响。",
	],
	"obstacle": [
		"通道被塌下来的碎石堵了大半。",
		"一扇门卡在门框里，后面的路看不太清。",
		"横梁斜插在地上，得挪开才能过去。",
	],
	"empty": [
		"这里除了灰，什么也没留下。",
		"墙上有一道干涸的痕迹，说不上是什么。",
		"空房间。但总觉得不该这么安静。",
	],
}


## 房间卡（M74）。
##
## 探索的平淡感来自「点房间 → 瞬间结算 → 人还站在原地」：
## 玩家从没看见过自己走进的那间屋子长什么样，也没看见自己做了什么。
## 这张卡分两页：先描述屋子（类型 + 环境 + 里面那件东西叫什么），
## 再把结算结果摆出来。
## 一行结果文字里最主要的那个资源，返回图标 key（M141）。
##
## 只认四种纹章 + 金币：饰品没有稳定的通用图标，
## 与其上一张对不上的图，不如只上能认出来的。
## 在 (x, y-18) 画奖励行的行首图标，返回**文字该从哪开始**（M147）。
##
## 房间卡片是整句、胜利屏是分栏，两边的排版没法合并，
## 但「行首那个图标」是同一样东西 —— 抽出来之后，
## 加新资源类型只要改 `_line_icon_name` 一处，两个界面同时生效。
func _reward_icon_x(x: float, y: float, text: String) -> float:
	var ic: String = _line_icon_name(text)
	if ic.is_empty():
		return x
	var t: Texture2D = _ico(ic)
	if t == null:
		return x
	draw_texture_rect(t, Rect2(x + 2.0, y - 18.0, 22.0, 22.0), false)
	return x + 30.0


func _line_icon_name(line: String) -> String:
	if line.contains("金币") or line.contains("金 "):
		return "icon_gold"
	# 四种纹章共用「地契」那张图标 —— 图集里没有分种类，
	# 上一张能认的比上一张错的好（M141）。
	for k in ["地契", "纹章", "雕像", "头像", "徽记", "传家宝"]:
		if line.contains(k):
			return "icon_deed"
	# 补给（M199）：药草/绷带/解毒剂这些原来**没有行首图标** ——
	# 而它们在奖励里出现得比传家宝还频繁（奇物多半给补给）。
	# 补给面板和准备屏早就有整套 `supply_*` 图标，这里只是没接上。
	for sid in SUPPLY_ICONS.keys():
		var nm: String = DdNames.supply_name(str(sid))
		if not nm.is_empty() and line.contains(nm):
			return str(SUPPLY_ICONS[sid])
	return ""


## 这件奇物有没有「背包里正好有」的可用道具（M161）。空 = 直接结算。
func _curio_candidate(cid: String) -> String:
	if cid.is_empty() or exp == null or exp.db == null:
		return ""
	var cl: CurioLib = exp.db.curio_lib
	if cl == null or not cl.is_loaded():
		return ""
	for it in cl.items_for(cid):
		if exp.supply_count(str(it)) > 0:
			return str(it)
	return ""


## 奇物询问卡（M161）：把「要不要用这件道具」摆出来，等玩家点。
func _draw_curio_ask() -> void:
	if _curio_ask.is_empty():
		return
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.0, 0.0, 0.64))
	var w: float = minf(520.0, size.x - 60.0)
	var h: float = 350.0
	var r := Rect2((size.x - w) * 0.5, (size.y - h) * 0.5, w, h)
	_panel(r, DdTheme.PANEL_DEEP)
	draw_rect(r, DdTheme.PANEL_EDGE, false, 2.0)
	var cid: String = str(_curio_ask.get("curio", ""))
	var it: String = str(_curio_ask.get("item", ""))
	_text(Vector2(r.position.x + 20.0, r.position.y + 40.0), "你看见了：%s" % DdNames.curio_name(cid),
		DdTheme.FONT_H1, DdTheme.TEXT, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 40.0)
	_text(Vector2(r.position.x + 20.0, r.position.y + 76.0),
		"背包里有「%s」× %d" % [DdNames.supply_name(it), exp.supply_count(it)],
		DdTheme.FONT_BD, DdTheme.STAT, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 40.0)
	_text(Vector2(r.position.x + 20.0, r.position.y + 112.0),
		"用对应道具通常能开出更好的东西，但道具会被消耗掉。",
		DdTheme.FONT_SM, DdTheme.DIM, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 40.0)
	_text(Vector2(r.position.x + 20.0, r.position.y + 138.0),
		"（空手翻也可能撞上坏结果）",
		DdTheme.FONT_SM, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 40.0)

	var ico: Texture2D = _supply_icon(it)
	if ico != null:
		draw_texture_rect(ico, Rect2(r.position.x + 20.0, r.position.y + 160.0, 40.0, 40.0), false)

	var bw: float = (r.size.x - 56.0) * 0.5
	_add_button(Rect2(r.position.x + 20.0, r.end.y - 108.0, bw, 44.0),
		"curio_use", "用「%s」" % DdNames.supply_name(it), true)
	_add_button(Rect2(r.position.x + 36.0 + bw, r.end.y - 108.0, bw, 44.0),
		"curio_skip", "空手翻", true)
	_text(Vector2(r.position.x + 20.0, r.end.y - 24.0),
		"点空白处 = 空手翻", DdTheme.FONT_TAG, DdTheme.FAINT,
		HORIZONTAL_ALIGNMENT_CENTER, r.size.x - 40.0)


## 结算完一件事之后，把「这一趟」列表重填（M161）。
##
## 原来这段在 `_drain_room` 和奇物询问两处各写一遍 —— 一处改了另一处就漏。
func _fill_room_lines(before: int) -> void:
	_sync_exp_events()
	_room_lines = []
	for i in range(mini(before, _log.size()), _log.size()):
		_room_lines.append(str((_log[i] as Dictionary).get("text", "")))
	if _room_lines.is_empty():
		_room_lines.append("翻了一遍，没有值得带走的东西。")
	queue_redraw()


func _draw_room_card() -> void:
	if exp == null:
		return
	if not _curio_ask.is_empty():
		_draw_curio_ask()
		return
	# 先画地图垫底（M74）：卡背后一片纯黑的话，玩家会忘了自己在图上哪一间。
	# 画完把地图的按钮清掉 —— 卡片是模态的，只该有它自己那颗按钮。
	var rooms: Dictionary = exp.map.get("rooms", {})
	var rr: Dictionary = rooms.get(_room_room, {})
	var rkind: String = str(rr.get("kind", MapGen.K_EMPTY))
	if _room_demo >= 0:
		rkind = MapGen.K_CURIO      # 验收时当前房间是入口，卡片该演示的是奇物房
	var w: float = 640.0
	# 高度跟着内容走（M74）：结果可能只有一行（半身像 ×2），也可能五六行。
	# 固定 560 会让「只拿到一件」的卡下面空掉三分之一。
	var h: float = 430.0
	if _room_phase == 1:
		h = clampf(360.0 + float(mini(_room_lines.size(), 6)) * 30.0, 400.0, 620.0)
	var r := Rect2((size.x - w) * 0.5, (size.y - h) * 0.5 - 40.0, w, h)

	# 把地图压暗但不盖死：玩家还得记得自己在图上的哪个位置
	_dci().draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.0, 0.0, 0.66))
	_panel(r, DdTheme.PANEL_DEEP)
	_dci().draw_rect(Rect2(r.position, Vector2(r.size.x, 3.0)),
		DdTheme.STAT if rkind == MapGen.K_CURIO else DdTheme.WARN)

	var ico: Texture2D = _room_icon(rkind)
	if ico != null:
		var isz: float = 130.0
		_dci().draw_texture_rect(ico, Rect2(r.position.x + (r.size.x - isz) * 0.5,
			r.position.y + 26.0, isz, isz), false)

	_text(Vector2(r.position.x, r.position.y + 200.0),
		"%d 号房 · %s" % [_room_room, _room_kind_name(rkind)],
		DdTheme.FONT_H1, DdTheme.TEXT, HORIZONTAL_ALIGNMENT_CENTER, r.size.x)

	var y: float = r.position.y + 240.0
	if _room_phase == 0:
		var lines: Array = ROOM_FLAVOR.get("curio", [])
		var flavor: String = "这里比走廊里更安静。"
		if not lines.is_empty():
			flavor = str(lines[_room_room % lines.size()])
		_text(Vector2(r.position.x + 40.0, y), flavor, DdTheme.FONT_BD, DdTheme.TEXT,
			HORIZONTAL_ALIGNMENT_CENTER, r.size.x - 80.0)
		# 具体是什么东西一定要写出来：玩家才学得会「祭坛要带圣水」
		var cid: String = str(_room_step.get("curio", ""))
		if not cid.is_empty():
			_text(Vector2(r.position.x + 40.0, y + 46.0),
				"你看见了：%s" % DdNames.curio_name(cid),
				DdTheme.FONT_LG, DdTheme.STAT, HORIZONTAL_ALIGNMENT_CENTER, r.size.x - 80.0)
	else:
		_text(Vector2(r.position.x + 40.0, y - 2.0), "这一趟：", DdTheme.FONT_MD, DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_CENTER, r.size.x - 80.0)
		var ly: float = y + 28.0
		var shown: int = mini(_room_lines.size(), 6)
		for i in shown:
			var line_txt: String = _strip_log_tag(str(_room_lines[i]))
			# 行首图标（M141）：这一行里只要有金币/纹章，前面就盖一个对应图标。
			# 光靠文字读「金币 750、地契 ×2」得逐字看，图标是扫一眼就认得的。
			var tx3: float = _reward_icon_x(r.position.x + 40.0, ly, line_txt)
			var wtxt: float = r.size.x - 80.0 - (tx3 - (r.position.x + 40.0))
			_text(Vector2(tx3, ly), line_txt,
				DdTheme.FONT_BD, DdTheme.TEXT, HORIZONTAL_ALIGNMENT_LEFT, wtxt)
			ly += 30.0
		if _room_lines.size() > shown:
			_text(Vector2(r.position.x + 40.0, ly),
				"……还有 %d 条（见右侧日志）" % (_room_lines.size() - shown),
				DdTheme.FONT_TAG, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, r.size.x - 80.0)

	_add_button(Rect2(r.position.x + 40.0, r.end.y - 76.0, r.size.x - 80.0, 56.0),
		"room_go", "走进去" if _room_phase == 0 else "继续赶路")


## 作弊：金币和四种纹章各 +10000（M104，数值 M125 上调）。
##
## 只为开发期少跑几趟远征。**不动名册**——加人不该是按钮，
## 那会绕开「名册上限 / 忙 / 死亡」一整套规则，出事很难查。
func _cheat_resources() -> void:
	if campaign == null:
		return
	campaign.gold += 10000
	for k in (campaign.cfg.get("heirlooms", []) as Array):
		var key: String = str(k)
		campaign.heirlooms[key] = int(campaign.heirlooms.get(key, 0)) + 10000
	campaign.save()
	_flash_msg("金币 +10000 · 纹章各 +10000")
	queue_redraw()


## 队伍屏左侧的名册卡（M106）。和名册页的卡同构，但多一个「上阵」状态。
func _party_card(hid: String, r: Rect2) -> void:
	var row: Dictionary = campaign.hero(hid)
	var alive: bool = bool(row.get("alive", true))
	var on: bool = _prep_party.has(hid)
	var st: int = _hit_state(r, "party_sel:" + hid)
	var base: int = TILE_ACTIVE if hid == _party_hero else st
	_tile(r, base)
	var pr := Rect2(r.position.x + 7.0, r.position.y + 8.0, 42.0, 42.0)
	_draw_hero_badge(hid, pr, alive)
	var tx: float = pr.end.x + 10.0
	_text(Vector2(tx, r.position.y + 22.0), _hero_label(hid), DdTheme.FONT_BD,
		DdTheme.TEXT if alive else DdTheme.FAINT)
	_text(Vector2(tx, r.position.y + 40.0),
		"Lv%d · 装备 %d 阶" % [campaign.resolve_of(hid), campaign.gear_of(hid)],
		DdTheme.FONT_TAG, DdTheme.DIM)
	# 右侧状态（M171）：名册屏合并进来之后，它那套「上阵/修养/病/阵亡」
	# 的优先级也照搬 —— 一目了然「这人这周能不能用」。
	# 原来这里只有「上阵 / — / 阵亡」三档，看不出「在建筑里躺着」和「病了」。
	var ptag: String = "—"
	var ptag_c: Color = DdTheme.DIM
	if not alive:
		ptag = "阵亡"
		ptag_c = DdTheme.CRIT
	elif on:
		ptag = "上阵"
		ptag_c = DdTheme.OK
	elif campaign.busy_of(hid) > 0:
		ptag = "修养 %d 周" % campaign.busy_of(hid)
		ptag_c = DdTheme.PARTY
	elif campaign.diseases_of(hid).size() > 0:
		ptag = "病 %d" % campaign.diseases_of(hid).size()
		ptag_c = DdTheme.WARN
	else:
		# 「空闲」这一档漏了（M174）：名册屏原来有，搬过来时只搬了
		# 修养和病，剩下的人全掉进「—」，等于没状态。
		ptag = "空闲"
		ptag_c = DdTheme.DIM
	_text(Vector2(r.end.x - 78.0, r.position.y + 22.0), ptag,
		DdTheme.FONT_TAG, ptag_c, HORIZONTAL_ALIGNMENT_RIGHT, 70.0)
	_add_hit(r, "party_sel:" + hid)


## 这个技能在「第几号位」能不能放（M175）。
##
## 判据和战斗里 `Battle._can_use()` 同一条：`launch_mask` 的位掩码。
## `mask == 0` 表示数据没限位次，任何位置都能放。
func _skill_ok_at(hid: String, sid: String, rank: int) -> bool:
	# 注意：是**视图层的 `db`**，不是 `campaign.db` ——
	# Campaign 上没有 `db` 字段（M175 第一次就写错了，运行时报
	# 「Invalid access to property or key 'db' on Campaign」）。
	if rank < 0 or db == null:
		return true
	var h: Dictionary = (db.heroes.get(campaign.def_of(hid), {}) as Dictionary)
	for s in (h.get("skills", []) as Array):
		if not (s is Dictionary) or str((s as Dictionary).get("id", "")) != sid:
			continue
		var lv_list: Array = (s as Dictionary).get("levels", [])
		if lv_list.is_empty():
			return true
		var m: Dictionary = Combatant._parse_rank_mask(
			str((lv_list[0] as Dictionary).get("launch", "")))
		var mask: int = int(m["mask"])
		return mask == 0 or (mask & (1 << rank)) != 0
	return true


## 队伍屏右侧：选中角色的装备与技能（M106）。
func _draw_party_detail(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	var hid: String = _party_hero
	var row: Dictionary = campaign.hero(hid)
	var alive: bool = bool(row.get("alive", true))
	var on: bool = _prep_party.has(hid)

	_text(Vector2(r.position.x + 16.0, r.position.y + 32.0), _hero_label(hid),
		DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(r.position.x + 16.0, r.position.y + 54.0),
		"Lv%d · 装备 %d 阶 · 压力 %.0f" % [campaign.resolve_of(hid),
			campaign.gear_of(hid), float(row.get("stress", 0.0))],
		DdTheme.FONT_SM, DdTheme.DIM)
	# 上阵开关 / 买活（M173）
	#
	# 阵亡的人原来这里的按钮是**灰的**，只在下面写一句「阵亡的人不能上阵」——
	# 玩家知道不能上，但不知道**怎么才能再上**。
	# 既然旁边已经有「改技能（去公会）」这种跳转键，这里也该有个动作键：
	# 直接掏钱把人捞回来（和马车征召同一个价，走 `campaign.recruit`）。
	var tog := Rect2(r.end.x - 156.0, r.position.y + 14.0, 140.0, 42.0)
	if alive:
		_add_button(tog, "party_toggle:" + hid, "下阵" if on else "上阵", true)
	else:
		var rcost: int = int((campaign.effective_recruit_cost(hid) as Dictionary).get("gold", 0))
		var can_rv: bool = campaign.can_recruit(hid)
		_add_button(tog, "party_revive:" + hid, "复活 %d 金" % rcost, can_rv)
		# 说明再往下 14px（M173）：`tog.end.y + 4` 正好贴着按钮下沿，
		# 视觉上挤成一行。也给位置不够时留出「金币不够」这档更长的文案。
		_text(Vector2(tog.position.x - 96.0, tog.end.y + 18.0),
			"复活后可直接上阵" if can_rv else "金币不够（要 %d）" % rcost,
			DdTheme.FONT_TAG, DdTheme.FAINT if can_rv else DdTheme.CRIT,
			HORIZONTAL_ALIGNMENT_RIGHT, 236.0)
	# 站位（M166）：上阵顺序就是号位，1 号在最前面吃伤害。
	# 原来这个顺序**没法调**，只能靠「先点谁」决定 —— 而玩家根本不知道这件事。
	if on:
		var idx: int = _prep_party.find(hid)
		var last: int = _prep_party.size() - 1
		# 文字和按钮要错开 24 以上（M166）：`_text` 的 y 是**基线**，
		# 文字往上占 18px、往下占 4px；上一版只隔 6，直接叠上了。
		# 放按钮**下面**、左对齐（M166 第二版）：右对齐到 140 宽的右端时，
		# 文字正好压在「↓ 后移」那颗按钮的右半边上。
		# 宽度只能给 140（= 两颗按钮的总宽）：面板右边界就在那儿，
		# 上一版给 200 直接把「吃伤害」三个字画到面板外了（M166 第三版）。
		_text(Vector2(tog.position.x, tog.end.y + 74.0), "第 %d 号位" % (idx + 1),
			DdTheme.FONT_SM, DdTheme.PARTY, HORIZONTAL_ALIGNMENT_LEFT, 140.0)
		# 不再给「前移/后移」按钮（M173）：两个小按钮点一次挪一格，
		# 把 4 号位换到 1 号位要点三次。改成**拖左侧卡片**。
		_text(Vector2(tog.position.x - 60.0, tog.end.y + 30.0),
			"拖左侧卡片可换位", DdTheme.FONT_TAG, DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_RIGHT, 200.0)
		var _unused_last: int = last

	# —— 装备 ——
	var y: float = r.position.y + 144.0
	_text(Vector2(r.position.x + 16.0, y), "饰品", DdTheme.FONT_MD, DdTheme.DIM)
	y += 12.0
	var eq: Array = campaign.equipped_of(hid)
	for si in campaign.equip_slots:
		var sr := Rect2(r.position.x + 16.0, y + 6.0 + float(si) * 66.0,
			r.size.x - 32.0, 60.0)
		var cur: String = str(eq[si]) if si < eq.size() else ""
		_panel(sr, DdTheme.PANEL_DEEP if cur.is_empty() else DdTheme.PANEL_HI)
		_hit_overlay(sr, "tk_slot:%s:%d" % [hid, si])
		_add_hit(sr, "tk_slot:%s:%d" % [hid, si])
		if cur.is_empty():
			_text(Vector2(sr.position.x + 16.0, sr.position.y + 36.0),
				"空槽 · 点下面仓库里的一件，再点这里", DdTheme.FONT_MD,
				DdTheme.FAINT)
		else:
			var ico: Texture2D = _trinket_icon(cur)
			var tx2: float = sr.position.x + 16.0
			if ico != null:
				draw_texture_rect(ico, Rect2(sr.position.x + 10.0,
					sr.position.y + 13.0, 34.0, 34.0), false)
				tx2 = sr.position.x + 52.0
			# 名字用**品质色**、下面补一行效果（M139）。
			# 原来只有灰白名字 —— 装了什么东西、这东西什么品质，
			# 得点开别的地方才知道，而这一行右边全是空的。
			var rar: String = ""
			if campaign.trinket_lib != null:
				rar = campaign.trinket_lib.rarity_of(cur)
			_text(Vector2(tx2, sr.position.y + 24.0), DdNames.trinket_name(cur),
				DdTheme.FONT_MD, _rarity_col(rar), HORIZONTAL_ALIGNMENT_LEFT,
				sr.end.x - tx2 - 46.0)
			_text(Vector2(tx2, sr.position.y + 46.0),
				DdTheme.ellipsis(_trinket_summary(cur), _font,
					sr.end.x - tx2 - 46.0, DdTheme.FONT_TAG),
				DdTheme.FONT_TAG, DdTheme.DIM, HORIZONTAL_ALIGNMENT_LEFT,
				sr.end.x - tx2 - 46.0)
			_text(Vector2(sr.end.x - 46.0, sr.position.y + 26.0), "卸",
				DdTheme.FONT_SM, DdTheme.WARN)

	# —— 技能：这一版只读，改技能仍在公会 ——
	var sy: float = y + 6.0 + float(campaign.equip_slots) * 66.0 + 20.0
	_divider(r.position.x + 16.0, sy, r.size.x - 48.0)
	var ski: Array = campaign.equipped_skills(hid)
	# 站在几号位决定「这几个技能里哪几个真能放」（M175）。
	# 用户看到的困惑：「技能 4/4，可战斗里只有 2 个」——
	# 4/4 是**装备了几个**，战斗里只列**当前站位能放的**，
	# 这个差别原来界面上一个字都没写。
	var my_rank: int = _prep_party.find(hid)
	var ok_n: int = 0
	for sk_t in ski:
		if _skill_ok_at(hid, str(sk_t), my_rank):
			ok_n += 1
	var sk_head: String = "技能　%d / %d" % [ski.size(), campaign.skill_slot_max(hid)]
	if my_rank >= 0 and ok_n < ski.size():
		sk_head += "　·　%d 位于可用 %d 个" % [my_rank + 1, ok_n]
	_text(Vector2(r.position.x + 16.0, sy + 26.0), sk_head,
		DdTheme.FONT_MD, DdTheme.DIM)
	for i in ski.size():
		var col: int = i % 2
		var line: int = i / 2
		var sid_s: String = str(ski[i])
		var ok_here: bool = _skill_ok_at(hid, sid_s, my_rank)
		# 行高 24 → 30（M143）：字号提到 18 之后 24 会上下叠，
		# 「眩晕重击」和下一行的「鼓舞呐喊」压在一起。
		_text(Vector2(r.position.x + 16.0 + float(col) * 300.0,
			sy + 52.0 + float(line) * 30.0),
			"· " + DdNames.skill_name(sid_s) + ("" if ok_here else "（此位不可用）"),
			DdTheme.FONT_SM, DdTheme.TEXT if ok_here else DdTheme.FAINT)
	# 公会没解锁就不给这个入口（M152）：原来它无条件可点，
	# 点了会跳到一个本该锁着的界面 —— 解锁的前置任务白设计了。
	var can_guild: bool = _bld_unlocked("guild")
	_add_button(Rect2(r.position.x + 16.0, sy + 52.0 + float((ski.size() + 1) / 2) * 30.0 + 8.0,
		r.size.x - 32.0, 44.0), "goto:guild",
		"改技能（去公会）" if can_guild else "改技能（公会未解锁 · 还差 %d 次任务）" % _bld_need("guild"),
		can_guild)

	# —— 仓库（M107）——
	#
	# 空槽原来写着「去饰品仓库挑一件」，而队伍屏里根本没有那个地方 ——
	# 玩家点空槽只会收到一句「先在左边挑一件饰品」，左边是名册，没饰品。
	# 现在把仓库直接摆在这一屏：点一件选中，再点上面的空槽装上。
	var wy: float = sy + 52.0 + float((ski.size() + 1) / 2) * 30.0 + 62.0
	_divider(r.position.x + 16.0, wy, r.size.x - 48.0)
	_text(Vector2(r.position.x + 16.0, wy + 24.0), "仓库饰品", DdTheme.FONT_MD,
		DdTheme.DIM)
	_text(Vector2(r.position.x + 120.0, wy + 24.0), "点一件选中 → 再点上面空槽",
		DdTheme.FONT_TAG, DdTheme.FAINT)
	# 选中后给**全量**效果（M111）：列表里只放得下两条摘要，
	# 而判断一件饰品值不值得戴，往往就差第三条。
	var sel_top: float = wy + 34.0
	if not _sel_trinket.is_empty():
		var all_bits: Array = _trinket_stat_bits(_sel_trinket, 0)
		var rar2: String = campaign.trinket_lib.rarity_of(_sel_trinket)
		_text(Vector2(r.position.x + 16.0, wy + 44.0),
			"%s · %s" % [DdNames.trinket_name(_sel_trinket),
				_trinket_rarity_name(rar2)], DdTheme.FONT_SM,
			_rarity_col(rar2))
		# 谁戴着：同一件不能给两个人，只说「已被占用」等于让玩家自己去找
		var wearer: String = _who_wears(_sel_trinket)
		_text(Vector2(r.position.x + 200.0, wy + 44.0),
			("已装备于 " + _hero_label(wearer)) if not wearer.is_empty() else "未装备",
			DdTheme.FONT_TAG, DdTheme.WARN if not wearer.is_empty() else DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 220.0)
		_text(Vector2(r.position.x + 16.0, wy + 62.0),
			DdTheme.ellipsis(" · ".join(all_bits) if not all_bits.is_empty()
				else "无属性加成", _font, r.size.x - 56.0, DdTheme.FONT_TAG),
			DdTheme.FONT_TAG, DdTheme.TEXT, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 56.0)
		sel_top = wy + 74.0
	var store: Array = campaign.trinket_store
	var room: int = int((r.end.y - (wy + 46.0)) / 52.0) * 2
	if store.is_empty():
		_text(Vector2(r.position.x + 16.0, wy + 52.0), "仓库里没有饰品。",
			DdTheme.FONT_SM, DdTheme.FAINT)
	else:
		# 每件两行（M108）：名字 + 效果摘要。
		# 原来只有名字 —— 两条「乌鸦肩羽」摆在一起，玩家没有任何依据选哪个。
		# 原版饰品界面至少给「图标 + 稀有度色 + 效果列表」，这里先补前两样加一条摘要。
		var cw2: float = (r.size.x - 40.0) * 0.5
		var row_h2: float = minf(52.0, maxf(34.0,
			(r.end.y - (wy + 40.0) - 16.0) / maxf(1.0, ceil(float(store.size()) * 0.5))))
		for i in mini(store.size(), maxi(2, room)):
			var tid: String = str(store[i])
			var col2: int = i % 2
			var line2: int = i / 2
			var rr := Rect2(r.position.x + 16.0 + float(col2) * cw2,
				sel_top + 6.0 + float(line2) * row_h2, cw2 - 8.0, row_h2 - 4.0)
			var sel: bool = _sel_trinket == tid
			draw_rect(rr, DdTheme.PANEL_HI if sel else DdTheme.BTN)
			draw_rect(rr, DdTheme.CRIT if sel else DdTheme.PANEL_EDGE, false, 1.0)
			_add_hit(rr, "party_tk:" + tid)
			# 图标 24：行高只有 40 出头，再大就把两行字挤掉了
			var tico: Texture2D = _trinket_icon(tid)
			var ntx: float = rr.position.x + 8.0
			if tico != null:
				draw_texture_rect(tico, Rect2(rr.position.x + 6.0,
					rr.position.y + (rr.size.y - 26.0) * 0.5, 26.0, 26.0), false)
				ntx = rr.position.x + 36.0
			# 职业限制**在这里就标**（M143）：原来要点了才弹「这个职业戴不了」，
			# 而玩家挑装备时正是要一眼看出「谁能用」。
			# 判断用 `fits_class` 而不是 `can_equip` —— 后者还会把「槽满」也算成不能装，
			# 而槽满跟这件饰品本身无关。
			var fits: bool = true
			if campaign.trinket_lib != null and not _party_hero.is_empty():
				fits = campaign.trinket_lib.fits_class(tid, campaign.def_of(_party_hero))
			if not fits:
				draw_rect(rr, Color(0.0, 0.0, 0.0, 0.45))
			_text(Vector2(ntx, rr.position.y + 18.0),
				DdNames.trinket_name(tid), DdTheme.FONT_SM,
				DdTheme.TEXT if sel else _rarity_col(
					campaign.trinket_lib.rarity_of(tid)),
				HORIZONTAL_ALIGNMENT_LEFT, rr.end.x - ntx - 6.0)
			if not fits:
				_text(Vector2(rr.end.x - 74.0, rr.position.y + 18.0), "戴不了",
					DdTheme.FONT_TAG, DdTheme.WARN, HORIZONTAL_ALIGNMENT_RIGHT, 68.0)
			_text(Vector2(ntx, rr.position.y + 36.0),
				DdTheme.ellipsis(_trinket_summary(tid), _font,
					rr.end.x - ntx - 6.0, DdTheme.FONT_TAG),
				DdTheme.FONT_TAG, DdTheme.FAINT,
				HORIZONTAL_ALIGNMENT_LEFT, rr.end.x - ntx - 6.0)
		if store.size() > maxi(2, room):
			_text(Vector2(r.position.x + 16.0, r.end.y - 10.0),
				"……还有 %d 件（去饰品仓库看全部）" % (store.size() - maxi(2, room)),
				DdTheme.FONT_TAG, DdTheme.FAINT)


## 队伍（M106）：装备、技能、上阵。
func _draw_party() -> void:
	# 文案压到 20 字以内（M171）：`_header` 右栏只占 46% 宽（约 345px），
	# 原来那句话 28 个字，末尾「决定谁跟你下去」直接被切在面板边上。
	# 说清楚「这一屏改的是哪一趟」（M179）。
	# 用户报过：「队伍里瘟疫医生明明是 4 号位，战斗里怎么变 1 号位了」——
	# 因为他**这一趟已经出发了**，地牢里的站位存在 `exp.hero_ids`，
	# 是出发那一刻定下的快照；这一屏改的是 `_prep_party`，只影响**下一趟**。
	# 两个数字都对，只是作用于不同的趟。不写出来，看起来就是「系统搞错了」。
	var _on_run: bool = exp != null and not exp.ended
	_header("队伍", "改的是下一趟" + ("　·　这趟的站位请在地图上拖队伍条" if _on_run else ""))
	if campaign == null:
		return
	# 进来第一件事是把出战名单初始化好（M114）。
	#
	# 这一屏原来直接用 `_prep_party`，而它只**准备屏**会初始化 ——
	# 直接从城镇进队伍屏时它是空的，整列显示成「—」，
	# 玩家点一下「上阵」就变成「一个人的出征队伍」，还会被存进档案。
	if _prep_party.is_empty():
		_prep_party = _party_restore(_prep_level)
	# 用 `hero_ids_deployed_first()` 而不是 `hero_ids()`（M171）：
	# 名册屏被合并进这一屏之后，它的「上阵优先、阵亡排末尾」也要带过来 ——
	# 否则 15 个人里找一个阵亡的战友要往下翻。
	# **列表顺序必须跟着站位走**（M174）：原来这里直接用 `hero_ids_deployed_first()`，
	# 它是按名册 `_order` 排的，和 `_prep_party` 两套顺序互不相干 ——
	# 拖完卡片，「第 N 号位」变了、列表纹丝不动，看起来像拖拽没生效。
	var alive: Array = []
	for h_on in _prep_party:
		if campaign.hero_ids().has(str(h_on)):
			alive.append(str(h_on))
	for h_rest in campaign.hero_ids_deployed_first():
		if not alive.has(str(h_rest)):
			alive.append(str(h_rest))
	if alive.is_empty():
		_text(Vector2(28, 120), "名册是空的。", DdTheme.FONT_BD, DdTheme.WARN)
		_add_button(Rect2(24.0, size.y - 100.0 - NAV_H, size.x - 48.0, 56.0), "party_back", "返回城镇")
		return
	if _party_hero.is_empty() or not alive.has(_party_hero):
		_party_hero = str(alive[0])
	# —— 左：名册 ——
	var btn_y: float = size.y - 44.0 - 56.0 - NAV_H
	var span: float = btn_y - 24.0 - 100.0
	var step: float = minf(78.0, span / float(maxi(1, alive.size())))
	_text(Vector2(24, 88), "名册 %d 人" % alive.size(), DdTheme.FONT_BD, DdTheme.TEXT)
	_party_rects = []
	for i in alive.size():
		var cr := Rect2(24.0, 100.0 + float(i) * step, 212.0, step - 8.0)
		_party_card(str(alive[i]), cr)
		_party_rects.append({"id": str(alive[i]), "rect": cr})
	# 拖拽中的浮动卡片（M173）：不给视觉反馈的话，手指底下的卡片
	# 还是留在原位，玩家会以为「没抓住」。
	if not _drag_card.is_empty() and bool(_drag_card.get("moved", false)):
		var cp: Vector2 = _drag_card.get("cur", _mouse)
		var dr := Rect2(cp.x - 106.0, cp.y - 30.0, 212.0, 60.0)
		draw_rect(dr, Color(0.07, 0.07, 0.09, 0.94))
		draw_rect(dr, DdTheme.CRIT, false, 2.0)
		_text(Vector2(dr.position.x + 12.0, dr.position.y + 34.0),
			_hero_label(str(_drag_card.get("id", ""))), DdTheme.FONT_BD,
			DdTheme.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 188.0)
	# —— 右 ——
	_draw_party_detail(Rect2(248.0, 88.0, size.x - 272.0, btn_y - 88.0 - 34.0))
	_text(Vector2(DdTheme.MARGIN, btn_y - 16.0), _building_hint("guild"),
		DdTheme.FONT_MD, DdTheme.FAINT)
	_add_button(Rect2(24.0, btn_y, size.x - 48.0, 56.0), "party_back", "返回城镇")


## 弹一条地图横幅（M75）。
func _map_banner(title: String, sub: String, col: Color) -> void:
	if _selftest or _auto:
		return      # 自动化不看这个，也免得在验收截图上乱入
	_map_banner_title = title
	_map_banner_sub = sub
	_map_banner_col = col
	_map_banner_t = 1.7


## 弹一个事件框（M194）：玩家点「确定」才继续。
##
## `next` 是关掉之后要做的事 —— 遭遇战靠它把「先看提示再开打」串起来。
## 自动模式下**不弹**，直接执行 `next`：自动化不会点按钮，弹出来就是卡死。
func _event_dialog(title: String, body: String, col: Color,
		sub: String = "", next: Callable = Callable()) -> void:
	if _auto or _selftest:
		if next.is_valid():
			next.call()
		return
	_dlg_open = true
	_dlg_title = title
	_dlg_body = body
	_dlg_sub = sub
	_dlg_col = col
	_dlg_next = next
	# 弹窗一开，底下的横幅就没必要再抢位置了
	_map_banner_t = 0.0
	queue_redraw()


func _dlg_close() -> void:
	if not _dlg_open:
		return
	_dlg_open = false
	var f: Callable = _dlg_next
	_dlg_next = Callable()
	# 先关再执行：`next` 里可能立刻弹出下一个框（连着两个事件），
	# 反过来的话会被这里的赋值清掉。
	if f.is_valid():
		f.call()
	queue_redraw()


## 事件弹窗。画在 `_draw_map()` 最后，**并且清掉底下的按钮**——
## 不清的话点空白照样能命中「撤退」「补给」，玩家想确认事件却退了队。
func _draw_event_dialog() -> void:
	if not _dlg_open:
		return
	_buttons.clear()
	var m: float = DdTheme.MARGIN
	var w: float = minf(size.x - m * 2.0, 520.0)
	var h: float = 232.0
	var x: float = (size.x - w) * 0.5
	var y: float = (size.y - h) * 0.5 - 36.0
	var r := Rect2(x, y, w, h)
	# 遮罩：0.62 够暗，还能看见底下是哪一屏 —— 完全黑掉会让人以为切场景了
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.0, 0.0, 0.62))
	draw_rect(r, Color(0.055, 0.06, 0.072, 0.985))
	draw_rect(r, Color(_dlg_col.r, _dlg_col.g, _dlg_col.b, 0.55), false, 1.5)
	draw_rect(Rect2(x, y, w, 3.0), _dlg_col)
	_text(Vector2(x + 24.0, y + 44.0), _dlg_title, DdTheme.FONT_BD, _dlg_col,
		HORIZONTAL_ALIGNMENT_LEFT, w - 48.0)
	_text(Vector2(x + 24.0, y + 78.0), _dlg_body, DdTheme.FONT_MD, DdTheme.TEXT,
		HORIZONTAL_ALIGNMENT_LEFT, w - 48.0)
	if not _dlg_sub.is_empty():
		_text(Vector2(x + 24.0, y + 104.0), _dlg_sub, DdTheme.FONT_TAG, DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_LEFT, w - 48.0)
	_dlg_btn = Rect2(x + 24.0, y + h - 62.0, w - 48.0, 46.0)
	_add_button(_dlg_btn, "dlg_ok", "确定", true, false, true)


## 地图横幅（M75）。放在网格区顶部：那是「你刚走到的地方」，
## 眼睛本来就在这儿；放屏幕底部会落在日志条上。
func _draw_map_banner() -> void:
	if _map_banner_t <= 0.0 or _state != S_MAP:
		return
	var a: float = clampf(_map_banner_t / 0.5, 0.0, 1.0)
	var w: float = 520.0
	var r := Rect2((size.x - w) * 0.5, _map_banner_y, w, 64.0)
	draw_rect(r, Color(0.02, 0.02, 0.025, 0.88 * a))
	var edge := Color(_map_banner_col.r, _map_banner_col.g, _map_banner_col.b, a)
	draw_rect(Rect2(r.position, Vector2(3.0, r.size.y)), edge)
	draw_rect(Rect2(r.end.x - 3.0, r.position.y, 3.0, r.size.y), edge)
	_text(Vector2(r.position.x, r.position.y + 26.0), _map_banner_title,
		DdTheme.FONT_BD, edge, HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
	_text(Vector2(r.position.x, r.position.y + 50.0), _map_banner_sub,
		DdTheme.FONT_MD,
		Color(DdTheme.TEXT.r, DdTheme.TEXT.g, DdTheme.TEXT.b, a * 0.9),
		HORIZONTAL_ALIGNMENT_CENTER, r.size.x)


## 去掉日志行的「【奇物】」前缀（M74）：卡片上那行本来就写在房间语境里，
## 再带一个方括号像在念后台日志。日志里保留前缀，那边要能扫得快。
## 奇物交互的**专用动词**（M195）。返回空 = 这道具没有专用说法，
## 退回「对〈奇物〉用了〈道具〉」—— 这句话对任何组合都通顺。
##
## 为什么需要它：素材里的交互只表示「这道具对这件东西有效」，
## 统一写成「用 X 打开 Y」会出病句（「用解毒剂打开遗失的行囊」）。
## 只有真正意义上的"打开"才配这个词：钥匙、撬锁工具。
static func _curio_verb(item: String) -> String:
	match item:
		"skeleton_key", "key":
			return "打开了"
		"shovel":
			return "铲开了"
		"torch":
			return "点着了"
		_:
			return ""


func _strip_log_tag(t: String) -> String:
	if t.begins_with("【"):
		var close: int = t.find("】")
		if close > 0:
			return t.substr(close + 1).strip_edges()
	return t


func _room_kind_name(kind: String) -> String:
	match kind:
		MapGen.K_CURIO:
			return "奇物"
		MapGen.K_EMPTY:
			return "空房间"
		MapGen.K_BATTLE:
			return "战斗房"
		MapGen.K_BOSS:
			return "首领房"
		MapGen.K_GOAL:
			return "出口"
		MapGen.K_START:
			return "入口"
	return "房间"


## 打开房间卡（M74，验收用）。
##
## 奇物房间要不要出现取决于地图生成，跑一趟撞不到就截不到图；
## 这里直接伪造一个「房间奇物」步骤，把卡钉在屏幕上。
func _room_demo_open() -> void:
	var cid: String = ""
	var lib = db.curio_lib
	if lib != null and lib.is_loaded() and not lib.curios.is_empty():
		cid = str(lib.curios.keys()[0])
	_room_kind = "curio"
	_room_room = int(exp.current_room)
	_room_step = {"kind": "curio", "curio": cid, "room": _room_room}
	_room_phase = 0
	_room_lines = []
	_state = S_ROOM
	if _room_demo >= 1:
		# 结果页：真结算一次，拿到的日志行就是卡片内容
		_room_go()
	queue_redraw()


func _enter_result() -> void:
	if not _settled and exp != null and campaign != null:
		_settled = true
		_settle_gain = campaign.settle(exp)
		if _dev_ui:
			# 经济量级（M46）：补上任务奖励之后，一趟到底赚多少只能靠打印看。
			# 结算屏上显示的是总数，不区分「捡的」和「交差拿的」。
			print("[econ] 结束=%s  战利品 %d + 任务奖励 %d = %d 金；任务传家宝 %s；首领 %d/%d" % [
				str(exp.end_reason),
				int(exp.loot_gold), int(_settle_gain.get("quest_gold", 0)),
				int(_settle_gain.get("gold", 0)),
				str(_settle_gain.get("quest_heirlooms", {})),
				int(_settle_gain.get("bosses_total", 0)), 4])
		campaign.save()
	_state = S_RESULT
	# 终局（M46）：打完第四个区域首领，这一趟直接进胜利屏，不再走结算。
	# 判定放在 settle 之后、且由界面消费掉 `victory_pending`——
	# 规则层只负责「记下这件事发生了」，切不切界面是界面的事。
	if campaign != null and campaign.victory_pending:
		campaign.victory_pending = false
		campaign.save()
		_state = S_VICTORY


func _sync_exp_events() -> void:
	if exp == null:
		return
	while _exp_ev_pos < exp.events.size():
		_consume_exp_event(exp.events[_exp_ev_pos])
		_exp_ev_pos += 1


func _consume_exp_event(e: Dictionary) -> void:
	var t: String = str(e.get("t", ""))
	match t:
		"light":
			pass    # 光照变化不进流水，顶栏实时显示，写日志会刷屏
		"torch_used":
			_add_log("【火把】光照 %.0f（剩 %d 根）" % [float(e["light"]), int(e["left"])], DdTheme.LIGHT)
		"hallway_stress":
			_add_log("走过走廊：%s 压力 +%.0f" % [
				_hero_label(str(e.get("hero", ""))), float(e.get("amount", 0.0))], DdTheme.DIM)
		"hunger":
			if bool(e["fed"]):
				_add_log("【饥饿】吃了口粮（剩 %d 份），全队略回血" % int(e["food"]), DdTheme.FOOD)
			else:
				_add_log("【饥饿】断粮！全员加压并掉血", DdTheme.WARN)
		"battle_start":
			_add_log("【遭遇】%s" % ", ".join(_monster_list(e.get("monsters", []))), DdTheme.TEXT)
			if not str(e.get("surprised", "")).is_empty():
				_add_log("　惊袭：%s 第一轮不行动" % ("我方" if str(e["surprised"]) == "party" else "敌方"), DdTheme.CRIT)
		"battle_end":
			# 四种收场要分开写（M65）：原来只有「我方胜 / 战败」两种，
			# 于是撤退和僵持（winner="none"）都被写成「战败」——
			# 玩家明明是自己走出去的，日志却说输了。
			var wn: String = str(e["winner"])
			var word: String = "我方胜" if wn == "party" else (
				"撤退" if wn == "retreat" else ("僵持" if wn == "none" else "战败"))
			_add_log("【战果】%s（%d 轮）" % [word, int(e["rounds"])], DdTheme.DIM)
		"loot":
			var bits: Array = []
			if int(e.get("gold", 0)) > 0:
				bits.append("金币 %d" % int(e["gold"]))
			for k in (e.get("heirlooms", {}) as Dictionary).keys():
				bits.append("%s ×%d" % [DdNames.heirloom_name(str(k)), int(e["heirlooms"][k])])
			for k in (e.get("supplies", {}) as Dictionary).keys():
				bits.append("%s ×%d" % [DdNames.supply_name(str(k)), int(e["supplies"][k])])
			for k in (e.get("gems", {}) as Dictionary).keys():
				bits.append("%s ×%d" % [DdNames.heirloom_name(str(k)), int(e["gems"][k])])
			if not bits.is_empty():
				_add_log("【%s】%s" % ["结算" if bool(e.get("complete", false)) else "拾取",
					"、".join(bits)], DdTheme.CRIT)
		"curio":
			# 奇物必须报出来。不报的话玩家只看到金币涨了，永远学不会
			# 「这个祭坛该带圣水」——那正是这一层唯一的意义。
			var cname: String = DdNames.curio_name(str(e.get("curio", "")))
			var used: String = str(e.get("item", ""))
			var outcome: String = str(e.get("outcome", ""))
			var tail: Array = []
			if int(e.get("gold", 0)) > 0:
				tail.append("金币 %d" % int(e["gold"]))
			for k2 in (e.get("heirlooms", {}) as Dictionary).keys():
				tail.append("%s ×%d" % [DdNames.heirloom_name(str(k2)), int(e["heirlooms"][k2])])
			for k3 in (e.get("supplies", {}) as Dictionary).keys():
				tail.append("%s ×%d" % [DdNames.supply_name(str(k3)), int(e["supplies"][k3])])
			if float(e.get("stress", 0.0)) > 0.0:
				tail.append("全员压力 +%.0f" % float(e["stress"]))
			if float(e.get("hp_lost", 0.0)) > 0.0:
				tail.append("全员掉血 %.0f%%" % (float(e["hp_lost"]) * 100.0))
			# 怪癖与疾病必须点名报到人：这是玩家唯一能看见的获得渠道，
			# 只写「获得了负面怪癖」等于让人不知道自己被坑在哪。
			var who: String = _hero_label(str(e.get("quirk_target", "")))
			if not str(e.get("quirk", "")).is_empty():
				tail.append("%s 获得「%s」" % [who, DdNames.quirk_name(str(e["quirk"]))])
			if not str(e.get("disease", "")).is_empty():
				tail.append("%s 染上「%s」" % [who, DdNames.quirk_name(str(e["disease"]))])
			if not str(e.get("quirk_lost", "")).is_empty():
				tail.append("清除了「%s」" % DdNames.quirk_name(str(e["quirk_lost"])))
			if not (e.get("unsupported", []) as Array).is_empty():
				tail.append("（效果未实装）")
			var verb: String = "空手而归"
			if not tail.is_empty():
				verb = "、".join(tail)
			elif outcome == "nothing":
				verb = "什么也没有"
			# 文案（M195）：原来一律写「用「X」打开 Y」，于是出现
			# 「用解毒剂打开遗失的行囊」—— 玩家第一反应是"凭什么"。
			#
			# 数据里的交互只表示「这道具对这件东西有效」，**不等于"打开"**：
			# 钥匙是打开，铁锹是铲，火把是烧，药剂是处理。所以动词按道具分，
			# 没有专用动词的退回「对〈奇物〉用了〈道具〉」—— 这句话对任何组合都通顺。
			var head: String = "【奇物】%s" % cname
			if not used.is_empty():
				var iname: String = DdNames.supply_name(used)
				var cv: String = _curio_verb(used)
				if cv.is_empty():
					head = "【奇物】对「%s」用了%s" % [cname, iname]
				else:
					head = "【奇物】用%s%s「%s」" % [iname, cv, cname]
			_add_log("%s → %s" % [head, verb],
				DdTheme.WARN if float(e.get("stress", 0.0)) > 0.0 or float(e.get("hp_lost", 0.0)) > 0.0 else DdTheme.TEXT)
		"affliction":
			_add_log("【崩溃】%s 陷入 %s" % [_hero_label(str(e.get("hero", ""))), str(e.get("kind", ""))], DdTheme.WARN)
			_flash_msg("崩溃！")
		"virtue":
			_add_log("【美德】%s 觉醒（%s）" % [_hero_label(str(e.get("hero", ""))), str(e.get("kind", ""))], DdTheme.CRIT)
			_flash_msg("美德觉醒")
		"heart_attack":
			_add_log("【心脏骤停】%s" % _hero_label(str(e.get("hero", ""))), DdTheme.WARN)
			_flash_msg("心脏骤停")
		"deaths_door":
			_add_log("【死门】%s" % _hero_label(str(e.get("hero", ""))), DdTheme.WARN)
		"death":
			_add_log("【阵亡】%s（%s）" % [_hero_label(str(e.get("hero", ""))), str(e.get("cause", ""))], DdTheme.WARN)
		"act_out":
			_add_log("　%s 崩溃发作，本回合不行动" % _hero_label(str(e.get("hero", ""))), DdTheme.WARN)
		"camp":
			_add_log("【休整】回血减压，光照 %.0f" % float(e["light"]), DdTheme.HEAL)
		"camp_ambush":
			_add_log("【休整】营地被偷袭！", DdTheme.WARN)
		"scout":
			if exp != null and exp.map_mode:
				_add_log("【侦察】看清一间房（已探明 %d/%d，成功率 %.0f%%）" % [
					int(e["revealed"]), int(e["total"]), float(e["chance"]) * 100.0], DdTheme.OK)
			else:
				_add_log("【侦察】看清前方第 %d 个节点（成功率 %.0f%%）" % [
					int(e["revealed"]), float(e["chance"]) * 100.0], DdTheme.OK)
		"scout_edge":
			_add_log("【侦察】看清前方走廊：%s（解除率 +%.0f%%）" % [
				_hazard_name(str(e.get("kind", ""))),
				db.rules.trap_scout_disarm_bonus * 100.0], DdTheme.OK)
		"trap":
			# 文案原来拼成「没察觉，队伍避开了（40%）」——
			# 「没察觉」和「避开」看着自相矛盾，其实说的是两件事：
			#   前半 = **有没有提前侦察到**；后半 = **踩上去那一下有没有躲过**。
			# 拼成一句就成了病句（用户报的原文）。拆成四种组合各写一句。
			var seen: bool = bool(e.get("scouted", false))
			var pct: float = float(e["chance"]) * 100.0
			if bool(e.get("dodged", false)):
				if seen:
					_add_log("【陷阱】提前发现了，绕了过去（躲开率 %.0f%%）" % pct, DdTheme.OK)
				else:
					_add_log("【陷阱】没看见，踩上去的瞬间躲开了（躲开率 %.0f%%）" % pct, DdTheme.OK)
			else:
				if seen:
					_add_log("【陷阱】发现了，但没拆成 —— 全队掉血加压", DdTheme.WARN)
				else:
					_add_log("【陷阱】没察觉，全队掉血加压（躲开率 %.0f%%）" % pct, DdTheme.WARN)
				_flash_msg("踩中陷阱")
		"obstacle":
			if bool(e.get("cleared", false)):
				_add_log("【障碍】用掉 1 把铁锹凿开（剩 %d）" % int(e["shovel"]), DdTheme.FOOD)
			else:
				_add_log("【障碍】没有铁锹，只能硬挖——全队掉血加压", DdTheme.WARN)
				_flash_msg("没有铁锹")
		"retreat":
			_add_log("【撤退】全员加压 %.0f" % db.rules.retreat_stress, DdTheme.DIM)
		"exp_end":
			_add_log("【结束】%s" % str(e["reason"]), DdTheme.TEXT)


func _add_log(text: String, col: Color = DdTheme.TEXT) -> void:
	_log.append({"text": text, "color": col})
	if _log.size() > LOG_MAX:
		_log = _log.slice(_log.size() - LOG_MAX)


## 最近一条日志的正文（M194）。弹窗用它当「结果」那一行 ——
## 玩家点开奇物最想知道的是「拿到了什么」，而不是「你翻了一下」。
func _last_log_text() -> String:
	if _log.is_empty():
		return ""
	return _strip_log_tag(str((_log[_log.size() - 1] as Dictionary).get("text", "")))


func _flash_msg(text: String) -> void:
	_flash = text
	_flash_life = 3.2   # 1.8 → 3.2（M155）：遭遇战那种一行字，1.8 秒根本读不完


# ============================================================
# 地图阶段的动作
# ============================================================

## 走向相邻房间。真正的内容结算交给 _drain_queue ——
## 一次移动可能同时包含「走廊事件」和「房间内容」，不能只处理第一个。
func _travel_to(room: int) -> void:
	if exp == null or exp.ended:
		return
	# 点的是自己脚下这间、而且它还有内容没触发 → 那就是「进去」（M144）。
	# 走廊遭遇战打完人已经站在门口，房间里的战斗/奇物等他点这一下才开。
	if room == exp.current_room and exp.has_pending_room():
		exp.enter_room()
		_sync_exp_events()
		_drain_queue()
		return
	if exp.has_pending_room():
		# 门口那间还没进去（M145）：说清楚卡在哪，别让玩家以为是路径问题
		_flash_msg("先进这间房 —— 点脚下这一格")
		return
	if not exp.travel(room):
		_flash_msg("走不到那间房")
		return
	_seen_rooms[room] = true
	# 换房间就把镜头拉回自己身上（M78）：拖远了之后走到下一间，
	# 不重置的话玩家会在满屏格子里找「我在哪」。
	_map_pan_auto = true
	# 空房间也要有一句话（M75）：它没有 step，`_drain_queue` 里什么都不会发生，
	# 玩家看到的就是「点了一下，什么都没变」。先弹一条，后面若有陷阱/奇物
	# 会把这条覆盖掉 —— 后发生的更重要。
	if exp.map_mode:
		var rooms_d: Dictionary = exp.map.get("rooms", {})
		if rooms_d.has(room):
			var rk: String = str((rooms_d[room] as Dictionary).get("kind", ""))
			if rk == MapGen.K_EMPTY:
				var fl: Array = ROOM_FLAVOR.get("empty", [])
				_map_banner("%d 号房 · 空房间" % room,
					str(fl[room % fl.size()]) if not fl.is_empty()
						else "这里除了灰，什么也没有。",
					DdTheme.DIM)
	_sync_exp_events()
	_drain_queue()


## 消化「已决定但还没结算」的步骤：走廊内容 → 房间内容。
## 碰到战斗就切到战斗屏，剩下的步骤等打完再继续。
func _drain_queue() -> void:
	var guard: int = 0
	while exp != null and not exp.ended and exp.has_pending() and guard < 32:
		guard += 1
		# 房间叙事（M74）：走进「有奇物的房间」时先停一下，让玩家看见这是什么地方，
		# 点「走进去」才结算。原来这一步是瞬间发生的 —— 点房间、日志多一行、
		# 人就还站在原地，整个探索过程没有任何画面。
		#
		# 只拦房间里的奇物，不拦走廊（走廊每走一步都停会把人逼疯），
		# 自动化模式也一律跳过：它们不会点按钮，停下来就是卡死。
		var peek: Dictionary = exp.peek_step()
		if not peek.is_empty() and _room_should_pause(peek):
			_room_open(exp.take_step())
			return
		var step: Dictionary = exp.take_step()
		_sync_exp_events()
		if step.is_empty():
			break
		match str(step.get("kind", "walk")):
			"hunger":
				exp.resolve_hunger()
				_sync_exp_events()
			"curio":
				exp.resolve_curio(step)
				_sync_exp_events()
				# 走到这里的只可能是走廊奇物（房间里的被 `_room_should_pause` 拦住了）
				if bool(step.get("corridor", false)):
					# 弹窗而不是横幅（M194）：奇物是有收获的，玩家得真的看见
					_event_dialog("走廊奇物", "路边有件东西，你们顺手翻了一下。",
						DdTheme.STAT, _last_log_text(), Callable(self, "_drain_queue"))
					return
			"trap":
				exp.resolve_trap(step)
				_sync_exp_events()
				_event_dialog("陷阱！", "脚下的地砖陷了下去。", DdTheme.HP,
					_last_log_text(), Callable(self, "_drain_queue"))
				return
			"obstacle":
				exp.resolve_obstacle()
				_sync_exp_events()
				_event_dialog("路障", "挡路的碎石，你们挪开了。", DdTheme.WARN,
					_last_log_text(), Callable(self, "_drain_queue"))
				return
			"walk":
				pass
			_:
				_battle = exp.start_battle(step)
				_battle_no += 1
				_battle_corridor = bool(step.get("corridor", false))
				_summoned_uids.clear()
				_sync_exp_events()
				if _battle == null:
					continue
				# 让规则层知道「英雄的决策由外部给」——它只认这个标志，不认识界面
				_battle.decision_provider = func(_b: Battle, _a: Combatant) -> Dictionary: return {}
				_ev_pos = 0
				_options = []
				_pending = {}
				if _skip_battles:
					# 调试用：不切战斗屏，直接按 AI 打完，镜头留在地图上
					exp._play_out(_battle)
					_battle = null
					_sync_exp_events()
					continue
				# 遭遇弹窗（M194）：**只在走廊遭遇弹**。
				#
				# 房间战斗前面已经有一张房间卡片（「7 号房·战斗房」→ 点「走进去」
				# 才走到这里），再弹一次等于连点四次才开打。走廊遭遇不一样：
				# 它是走一步就撞上的，之前没有任何一屏告诉玩家「撞上了什么」。
				if _battle_corridor:
					_event_dialog("走廊遭遇", "有东西挡住了路。", DdTheme.CRIT,
						", ".join(_monster_list(step.get("monsters", []))),
						Callable(self, "_begin_encounter"))
					return
				_begin_encounter()
				return
	if exp != null and exp.ended:
		_enter_result()


## 遭遇弹窗点了「确定」（M194）：这才真的切到战斗屏。
##
## 里面这几行原来直接写在 `_drain_queue` 的分支尾部。抽出来的原因不是美观：
## 弹窗要先 `return` 等玩家点，中间隔着一次回调，状态初始化必须跟着一起搬到这里，
## 否则玩家在弹窗停留的这几秒里，上一场战斗的 `_order_ids` / `_pending` 还留着。
func _begin_encounter() -> void:
	if _battle == null or exp == null or exp.ended:
		return
	_step_timer = 0.20
	# 新战斗的界面状态（M65）：行动序、瞄准、撤退上膛都不能带上一场的。
	_order_ids = []
	_order_cur = -1
	_pending = {}
	_retreat_arm = false
	_info_uid = -1
	_banner_t = 1.7
	_state = S_BATTLE


func _leave_dungeon() -> void:
	if exp == null or exp.ended:
		return
	exp.leave_dungeon()
	_sync_exp_events()
	_enter_result()


func _use_torch() -> void:
	if exp == null or exp.ended:
		return
	if exp.use_torch():
		_sync_exp_events()


func _do_camp() -> void:
	if exp == null or exp.ended:
		return
	if exp.camp():
		_sync_exp_events()
		if exp.ended:
			_enter_result()
		elif _battle != null:
			_state = S_BATTLE


func _do_retreat() -> void:
	if exp == null or exp.ended:
		return
	# 战斗中撤退**不是百分百**（M155）。查 DD1 的 `shared/rules.json`：
	#   combat_retreat_chance = 0.70
	#   combat_retreat_bonus_chance_per_attempt = 0.05
	#   combat_retreat_stress = 20
	# 也就是说原版里撤退是一**次掷骰**，失败要再吃一轮伤害。
	# 我们原来是无条件成功 —— 那等于「打不过就跑、一分代价不付」，
	# 战斗的资源压力全没了。
	if _battle != null:
		var ch: float = clampf(float(db.rules.retreat_chance)
			+ float(_retreat_tries) * float(db.rules.retreat_chance_step), 0.0, 0.95)
		_retreat_tries += 1
		if randf() > ch:
			# 失败：压力照扣（原版也扣），这一回合算白费
			for hk in exp.state.keys():
				var st: Dictionary = exp.state[hk]
				if bool(st.get("dead", false)):
					continue
				st["stress"] = clampf(float(st.get("stress", 0.0))
					+ float(db.rules.retreat_stress), 0.0, 200.0)
			_add_log("【撤退】失败（%.0f%% 成功）全队 +%.0f 压力" % [
				ch * 100.0, float(db.rules.retreat_stress)], DdTheme.WARN)
			_flash_msg("撤退失败！(%.0f%%)" % (ch * 100.0))
			_battle.step_turn()
			_drain_battle_events()
			queue_redraw()
			return
		_retreat_tries = 0
		_flash_msg("撤退成功")
	else:
		_retreat_tries = 0
	# 战斗中途撤退（M65）：先把这一场造成的伤害与压力落盘，再走。
	# 原来直接 `exp.retreat()` 就把 `_battle` 丢掉了，那场里掉的血清零——
	# 撤退等于免费重置，资源层立刻失去意义。`aborted` 让 finish_battle
	# 照常存状态，但不记清剿、不掉落（战利品只认「打赢」）。
	if _battle != null:
		_battle.aborted = true
		exp.finish_battle(_battle)
		_battle = null
		_pending = {}
		_options = []
		_sync_exp_events()
	_step_timer = 0.0
	if exp.ended:
		_enter_result()
		return
	exp.retreat()
	_sync_exp_events()
	_enter_result()


# ============================================================
# 战斗阶段
# ============================================================

func _process(delta: float) -> void:
	# 长按计时（M183）：手机上没有鼠标悬停，技能/饰品的完整数值
	# 只能靠「按住不放」来看。0.45 秒 —— 短了会和点击混淆，
	# 长了玩家以为没反应。
	if not _hold_id.is_empty() and _hold_shown.is_empty():
		_hold_t += delta
		if _hold_t >= 0.45:
			_hold_shown = _hold_id
			queue_redraw()
	_elapsed += delta
	_flash_life = maxf(0.0, _flash_life - delta)

	# 验收开关（M58）：把指针/按下态钉住。`_buttons` 是上一帧填好的，
	# 所以第一帧找不到、第二帧起生效 —— 截图在 1 秒以后，早就稳定。
	if _want_mouse.x >= 0.0:
		_mouse = _want_mouse
	if not _want_press.is_empty():
		for b in _buttons:
			if str(b["id"]) == _want_press:
				_press_id = _want_press
				_mouse = (b["rect"] as Rect2).get_center()
				break

	# 音效试听（M50）：每 2 秒换一个，循环播。
	if _sfx_demo and _sfx != null:
		_sfx_demo_t += delta
		if _sfx_demo_t >= 1.6:
			_sfx_demo_t = 0.0
			_sfx_demo_i = (_sfx_demo_i + 1) % SFX_DEMO_LIST.size()
			_demo_play(str(SFX_DEMO_LIST[_sfx_demo_i]))
			queue_redraw()

	# 背景音乐（M49）：改成「状态变了才切」，而不是每个状态切换点都各写一行。
	# 界面状态有 12 个，逐个挂钩会漏；而曲目本来就只由状态决定。
	if _music != null:
		var want: String = _music_for_state()
		if want != _music_want:
			_music_want = want
			if _dev_ui:
				# 曲目切换只能靠打印确认：截图看不见、耳机里也只能听出「有没有」。
				print("[music] -> %s" % want)
			_music.play(want)

	# 光照视觉值跟随（M44）。用指数趋近而不是线性，否则点一次火把会匀速变亮一秒，
	# 看起来像进度条而不是火焰。
	if _want_light >= 0.0 and exp != null:
		exp.light = _want_light
	if exp != null:
		_light_vis = lerpf(_light_vis, exp.light, 1.0 - pow(0.02, delta))
	else:
		_light_vis = lerpf(_light_vis, 100.0, 1.0 - pow(0.02, delta))
	if _dev_ui:
		# 跟随曲线是可以被看见的（M44）：没有这两行，「渐亮」只能靠肉眼猜，
		# 而静态截图完全无法区分「瞬变」和「1 秒渐变」。
		_light_log_t += delta
		if _light_log_t >= 0.25:
			_light_log_t = 0.0
			print("[light] vis=%.1f  target=%.1f" % [_light_vis, exp.light if exp != null else 100.0])

	# 受击抖动计时（M36）
	for k in _hit_t.keys():
		var left: float = float(_hit_t[k]) - delta
		if left <= 0.0:
			_hit_t.erase(k)
		else:
			_hit_t[k] = left

	# 守护探身计时（M200）：和受击抖动同一套写法 —— 到点就删，
	# 留着 0 秒的条目会让 `_guard_shift` 一直算出 0 偏移、白白遍历。
	for k in _guard_fx.keys():
		var gleft: float = float((_guard_fx[k] as Dictionary).get("t", 0.0)) - delta
		if gleft <= 0.0:
			_guard_fx.erase(k)
		else:
			(_guard_fx[k] as Dictionary)["t"] = gleft

	# 站位补间（M37/M38）：立绘朝「rank 该在的位置」滑动。
	# 这是位移技能能被看懂的关键——没有插值的话，rank 一变就是瞬移，
	# 玩家只能从日志里猜「谁换了位置」。
	# **每帧无条件重绘是这里最贵的开销**（M150）：整屏 750×1334
	# 有几十张纹理 + 上百段文字，hover 一下就是一次全量重画。
	# 改成「只在真的有东西在动的时候重绘」，其余靠输入事件触发。
	if _battle != null and _state == S_BATTLE:
		if _slot_anim_battle != _battle:
			_slot_anim.clear()
			_pose.clear()
			# 咆哮是「登场台词」，换一场就该重新来过（M51）
			_aggro_done.clear()
			_voice_at.clear()
			_slot_anim_battle = _battle
		var k_lerp: float = 1.0 - pow(0.0015, delta)
		for u in _battle.all_units():
			var goal: float = _battle_slot_x(u, not u.is_hero)
			var cur: float = float(_slot_anim.get(u.uid, goal))
			_slot_anim[u.uid] = lerpf(cur, goal, k_lerp)
		# 出招姿势的计时（M38）：时间一到自动回到 combat 帧
		for k in _pose.keys():
			var pd: Dictionary = _pose[k]
			var left: float = float(pd.get("t", 0.0)) - delta
			if left <= 0.0:
				_pose.erase(k)
			else:
				pd["t"] = left
		# 特效计时（M57）：跟姿势同一段生命周期，播完自己消失
		_fx_tick(delta)
	elif _state != S_BATTLE:
		_slot_anim_battle = null
		_pose.clear()
		_fx_active.clear()
		_fx_overlay.clear()

	if not _shot_path.is_empty() and _elapsed >= _shot_at:
		var img: Image = get_viewport().get_texture().get_image()
		img.save_png(_shot_path)
		print("截图已保存：%s（布局宽 %.0f）" % [_shot_path, size.x])
		get_tree().quit()
		return

	var i: int = 0
	while i < _floaters.size():
		_floaters[i].life -= delta
		_floaters[i].pos.y -= 26.0 * delta
		if _floaters[i].life <= 0.0:
			_floaters.remove_at(i)
		else:
			i += 1

	if _banner_t > 0.0:
		_banner_t = maxf(0.0, _banner_t - delta)
	if _map_banner_t > 0.0:
		_map_banner_t = maxf(0.0, _map_banner_t - delta)
	if _state == S_BATTLE_END:
		# 结算卡是「等玩家看」的一屏，不是过场：兜底时间给得长一点，
		# 防止玩家没注意到按钮时卡在这里。
		# 自动模式（`--auto` / `--selftest`）例外——那里没人会点按钮，
		# 12 秒一张卡会把整趟自检拖到超时。注意 `--selftest` 不设 `_auto`，
		# 两个标志都要判。
		_be_timer += delta
		if _be_timer > (0.7 if (_auto or _selftest) else 12.0):
			_continue_after_battle()
	elif _state == S_BATTLE and _battle != null:
		if _battle.awaiting_input != null:
			if _auto and not _auto_map_only:
				_auto_timer += delta
				if _auto_timer > 0.25:
					_auto_timer = 0.0
					_auto_submit()
		else:
			_step_timer -= delta
			if _step_timer <= 0.0:
				_battle_step()
	elif _state == S_MAP and exp != null and exp.has_pending_room() \
			and _map_layer != null and _map_layer.visible:
		# 「互动」标签在呼吸（M190）：动画要动就必须每帧重画地图层。
		# 只在**真的有 pending 房间**时才这么做 —— 平时地图是静止的，
		# 每帧重画几十个格子会把这一屏拖回「很卡」的老路（M183 刚修过）。
		_map_layer.queue_redraw()
	elif _state == S_MAP and _auto:
		_auto_timer += delta
		if _auto_timer > 0.7:
			_auto_timer = 0.0
			_selftest_move()
	elif _state == S_TOWN and _auto:
		_auto_timer += delta
		if _auto_timer > 0.3:
			_auto_timer = 0.0
			_start_expedition(_size, _level)

	# 事件弹窗样张（M194，仅 --dlg-demo）。放在 if-elif 链**之后**：
	# 插在中间会把后面那个 `elif _state == S_MAP and _auto` 抢过来，
	# 自动跑图就再也不动了（而且语法合法、不报错）。
	if _dlg_demo and not _dlg_demo_done and _state == S_MAP:
		_dlg_demo_done = true
		_dlg_open = true
		_dlg_title = "走廊奇物"
		_dlg_body = "路边有件东西，你们顺手翻了一下。"
		_dlg_sub = "用「解毒剂」打开 遗失的行囊 → 金币 1000、药草 ×1"
		_dlg_col = DdTheme.STAT
		queue_redraw()

	# 长按浮层样张（M201，仅 --hold-demo）：顺手把第一个人的恢复期打开，
	# 否则截图只能看到「生命 / 压力」两行，最想看的那段看不到。
	if _hold_demo and not _hold_demo_done and _state == S_MAP and exp != null \
			and not exp.hero_ids.is_empty():
		_hold_demo_done = true
		var hid_d: String = str(exp.hero_ids[0])
		(exp.state[hid_d] as Dictionary)["recovering"] = true
		_hold_shown = "hero_stat:" + hid_d
		queue_redraw()

	# 只有「还在动」的东西才需要下一帧（M150）。
	#
	# 原来这里是**无条件** `queue_redraw()` —— 每秒 60 次整屏重画，
	# 而整屏有几十张纹理、上百段文字。表现是「鼠标划过技能卡会卡」，
	# 但那不是 hover 的问题，是一直在重画。
	# 鼠标 hover 现在由 `_input` 里的移动事件触发。
	var moving: bool = not _floaters.is_empty() \
		or _banner_t > 0.0 or _map_banner_t > 0.0 or _flash_life > 0.0 \
		or _step_timer > 0.0 or _pose.size() > 0 or not _fx_active.is_empty() \
		or (_state == S_BATTLE and _battle != null) \
		or not _shot_path.is_empty()
	if exp != null and absf(_light_vis - exp.light) > 0.3:
		moving = true
	if moving:
		queue_redraw()


func _battle_step() -> void:
	if _battle == null:
		return
	if _battle.is_over():
		_step_timer = 0.45
		_end_battle_ui()
		return
	if not _battle.round_open():
		_battle.begin_round()
		_ev_pos = 0
		_drain_battle_events()
		_step_timer = _step_delay
		return

	_battle.step_turn()
	_drain_battle_events()
	if _battle.awaiting_input != null:
		_begin_player_turn()
	_step_timer = _step_delay


func _end_battle_ui() -> void:
	if exp == null or _battle == null:
		return
	# 先拍一张战利品快照：掉落是在 finish_battle 里累进 exp 的，
	# 结算卡要显示的是「这一场拿到了什么」，不是整趟累计。
	var before: Dictionary = _loot_snapshot()
	var b: Battle = _battle
	exp.finish_battle(b)
	_battle = null
	_sync_exp_events()
	if exp.ended:
		_enter_result()
		return
	# 只有打赢才停一屏。僵持/撤退各有去向，不该套一张「胜利卡」。
	if str(b.winner()) == "party":
		_be_data = {"rounds": b.round_index, "gain": _loot_diff(before)}
		_be_timer = 0.0
		_state = S_BATTLE_END
		return
	_continue_after_battle()


## 结算卡之后的收尾。点「继续」和超时兜底共用这一段。
func _continue_after_battle() -> void:
	if exp == null:
		return
	_be_data = {}
	exp.after_step(false)
	_sync_exp_events()
	if exp.ended:
		_enter_result()
		return
	_options = []
	_pending = {}
	_retreat_arm = false
	_exp_persist()
	# 从房间卡打起来的（M103）：回到那张卡上弹结果，而不是直接回地图。
	# 「打完连口气都不喘就继续走」正是原来那个突兀感的来源。
	if _room_battle:
		_room_battle = false
		_room_phase = 1
		_room_lines = ["这一间已经清干净了。"]
		_state = S_ROOM
		queue_redraw()
		return
	_state = S_MAP
	# 战斗可能发生在走廊里，房间里还有内容没结算
	_drain_queue()


## 本场掉落的差值。掉落是在 finish_battle 里累加的，
## 所以只能靠「打完 - 打前」，不能直接读总数——
## 直接读会把前面几场捡的也算进这一张卡。
func _loot_snapshot() -> Dictionary:
	if exp == null:
		return {"gold": 0, "heirlooms": {}, "trinkets": 0}
	return {"gold": exp.loot_gold,
		"heirlooms": (exp.loot_heirlooms as Dictionary).duplicate(),
		"trinkets": exp.loot_trinkets}


func _loot_diff(before: Dictionary) -> Dictionary:
	var out: Dictionary = {"gold": 0, "heirlooms": {}, "trinkets": 0}
	if exp == null:
		return out
	out["gold"] = maxi(0, int(exp.loot_gold) - int(before.get("gold", 0)))
	out["trinkets"] = maxi(0, exp.loot_trinkets - int(before.get("trinkets", 0)))
	var prev: Dictionary = before.get("heirlooms", {})
	for k in (exp.loot_heirlooms as Dictionary).keys():
		var d: int = int(exp.loot_heirlooms[k]) - int(prev.get(k, 0))
		if d > 0:
			(out["heirlooms"] as Dictionary)[str(k)] = d
	return out


func _begin_player_turn() -> void:
	# 每回合开头存一次战斗快照（M118）。
	#
	# 只在这个点存，是为了让「快照 = 这一回合的开头」成立：
	# 切后台时若正打到一半，恢复回来从回合开头重来，
	# 血量/buff 和快照完全一致，不会出现「血恢复了但技能已经放掉」。
	_exp_persist()
	# 用 `all_options` 而不是 `player_options`（M65）：后者会把站位不符的招滤掉，
	# 面板上直接少一格，玩家看不出「为什么少了一招」。
	_options = _battle.all_options(_battle.awaiting_input)
	_pending = {}
	_retreat_arm = false
	# 换人了就把详情关掉：上一手看的那个单位可能已经死了，
	# 留着一张尸体的卡挡在屏幕中间没有意义。
	_info_uid = -1
	_auto_timer = 0.0
	if _boot_aim >= 0:
		var ai: int = _boot_aim
		_boot_aim = -1
		_activate("skill:%d" % ai)
	if _pick_demo >= 0:
		var pd: int = _pick_demo
		_pick_demo = -1
		_activate_id("skill:%d" % pd)
	if _corpse_demo and _battle != null and not _battle.enemies.is_empty() \
			and _corpse_done_for != _battle.get_instance_id():
		# 每场战斗只做一次（按实例 id 记）：`--start --battle` 会先起一场队列战斗，
		# 再被 `_boot_into_battle` 顶掉，只按「第一次」记会杀到上一场的敌人。
		_corpse_done_for = _battle.get_instance_id()
		var victim: Combatant = _battle.enemies[0] as Combatant
		victim.take_damage(99999)
		victim.corpse_hp = 2
		queue_redraw()
	if _boot_info >= 0:
		var all_u: Array = _battle.all_units()
		if _boot_info < all_u.size():
			var tu := all_u[_boot_info] as Combatant
			# 验收用：四类状态各来一条，正好把「buff / dot / status」三条通道
			# 都铺在屏幕上。数值本身没有意义，别拿它当平衡依据。
			tu.add_ad_hoc_buff("demo_hit", "combat_stat_add", "attack_rating", 0.10, 3)
			tu.add_ad_hoc_buff("demo_dmg", "combat_stat_multiply", "damage_low", 0.15, 2)
			tu.add_dot("bleed", 3, 4)
			tu.add_status("tagged", 1)
			_info_uid = tu.uid
		_boot_info = -1


func _auto_submit() -> void:
	if _battle == null or _battle.awaiting_input == null:
		return
	# 截图用：让第一个能守护的人真的守一次，然后把画面冻住——
	# 守护是一项「持续状态」，不冻住的话截图永远落在它已经过期之后。
	if _show_guard_demo:
		if _guard_demo_done:
			return
		var gi: int = _find_guard_option()
		if gi < 0:
			# 这一回合不是守护者发起的：照常代打，等轮到他
			var c0: Dictionary = _battle.choose_action(_battle.awaiting_input)
			_submit(c0.get("action", {}), c0.get("targets", []))
			return
		_guard_demo_done = true
		_activate("skill:%d" % gi)
		var mates: Array = _pending.get("targets", [])
		if not mates.is_empty():
			_pick_target(int((mates[0] as Combatant).uid))
		return
	var c: Dictionary = _battle.choose_action(_battle.awaiting_input)
	_submit(c.get("action", {}), c.get("targets", []))


func _submit(action: Dictionary, targets: Array) -> void:
	if _battle == null:
		return
	_battle.submit_choice(action, targets)
	_drain_battle_events()
	_options = []
	_pending = {}
	_move_mode = false
	_info_uid = -1
	_step_timer = _step_delay


# ============================================================
# 输入
# ============================================================

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		_mouse = (event as InputEventMouseMotion).position
		if not _drag_card.is_empty():
			if (_mouse - (_drag_card["pos"] as Vector2)).length() > 12.0:
				_drag_card["moved"] = true
			_drag_card["cur"] = _mouse
			queue_redraw()
		# **只有 hover 目标变了才重绘**（M176）。原来每个 motion 事件都整屏重画，
		# 公会屏右侧是 7 张技能卡（图标 + 4 段文字 + 底条），
		# 鼠标在名单上划一下就把它们全画一遍 —— 玩家感受到的就是「这界面很卡」。
		var hk: String = _hit_id_at(_mouse)
		if hk != _hover_key:
			_hover_key = hk
			queue_redraw()
		if _map_drag:
			var dm: Vector2 = _mouse - _map_drag_pos0
			if not _map_drag_moved and dm.length() > 10.0:
				_map_drag_moved = true
			if _map_drag_moved:
				_map_pan = _map_drag_pan0 + dm
				_map_clamp_pan(_map_rect)
		var prev_uid: int = _hover_uid
		_hover_uid = -1
		for s in _slots:
			if (s.rect as Rect2).has_point(_mouse):
				_hover_uid = int(s.uid)
		# **这一行原来是无条件的 `queue_redraw()`**（M183）——
		# 于是上面刚做的「hover 目标变了才重绘」被它整个盖掉，
		# 鼠标每动一像素就整屏重画一次。公会屏右侧 7 张技能卡 × 每张
		# 图标 + 4 段文字 + 底条，玩家感受到的就是「这界面非常卡」。
		# 只有**真的需要**重绘时才重绘：
		#   1. 悬停的血条换了（`_hover_uid` 变化）
		#   2. 正在拖动滚动条
		#   3. 地图正在被拖（`_map_pan` 变了）
		if _hover_uid != prev_uid or _map_drag_moved:
			queue_redraw()
		if not _drag_zone.is_empty():
			_hscroll_drag_to(_mouse.x)
	elif event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index != MOUSE_BUTTON_LEFT:
			return
		if mb.pressed:
			_press_begin(mb.position)
		else:
			_press_end(mb.position)
	elif event is InputEventScreenTouch:
		# 触摸没有 motion 事件：不在这里更新 `_mouse`，手机上所有 hover
		#（以及按下态要看的那次 `has_point`）都会恒假。
		var st := event as InputEventScreenTouch
		_mouse = st.position
		if st.pressed:
			_press_begin(st.position)
		else:
			_press_end(st.position)
			# 触摸没有「鼠标停在哪」这回事：抬手后不清掉，最后按到的
			# 那张卡会一直亮着 hover，看起来像选中了又没选中。
			_mouse = Vector2(-9999.0, -9999.0)
			_hover_uid = -1
			queue_redraw()
	elif event is InputEventScreenDrag:
		var sd := event as InputEventScreenDrag
		_mouse = sd.position
		if not _drag_card.is_empty():
			if (_mouse - (_drag_card["pos"] as Vector2)).length() > 12.0:
				_drag_card["moved"] = true
			_drag_card["cur"] = _mouse
			queue_redraw()
		if _drag_zone.is_empty() and _press_id.is_empty():
			_press_begin(sd.position)
		_hscroll_drag_to(sd.position.x)


func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not (event as InputEventKey).pressed:
		return
	match (event as InputEventKey).keycode:
		KEY_ESCAPE:
			# 抽屉是最上一层，ESC 先关它，再考虑撤退
			if not _roster_open.is_empty():
				_roster_open = ""
				queue_redraw()
			elif _state == S_MAP:
				_do_retreat()
		KEY_SPACE:
			if _state == S_BATTLE and _battle != null and _battle.awaiting_input != null:
				_auto_submit()
		KEY_F:
			if _state == S_MAP:
				_use_torch()
		KEY_C:
			if _state == S_MAP:
				_do_camp()


func _on_click(pos: Vector2) -> void:
	# 弹窗是模态的（M194）：除了「确定」，点哪儿都不响应。
	# 这里必须**先于** `_hit_id_at` 判断 —— 那个函数会遍历整屏按钮，
	# 而弹窗只是把它们从绘制里清掉了，命中区还在。
	if _dlg_open:
		if _dlg_btn.has_point(pos):
			_activate("dlg_ok")
		return
	var id: String = _hit_id_at(pos)
	if id.is_empty():
		# 点空白（M65）：退出瞄准态 / 放下撤退上膛。
		# 以前这里什么都不做——选了技能之后除了点另一个技能没有别的退路。
		if _log_open:
			_log_open = false
		elif _info_uid >= 0:
			_info_uid = -1
		elif _state == S_BATTLE and not _pending.is_empty():
			_pending = {}
			_retreat_arm = false
		queue_redraw()
		return
	_activate_id(id)


func _pick_target(uid: int) -> void:
	if _pending.is_empty():
		return
	var pool: Array = _pending.get("targets", [])
	var action: Dictionary = _pending.get("action", {})
	for t in pool:
		if int(t.uid) == uid:
			# AOE 点谁都是「打全体」（M65）：传整池，不是点中的那一个。
			# 这里是规则层 `for t in targets` 的语义决定的——
			# 只传一个的话，全体技能会真的只打一个人。
			if bool(action.get("target_aoe", false)):
				_submit(action, pool)
			else:
				_submit(action, [t])
			return


func _activate(id: String) -> void:
	if _sfx != null and not id.begins_with("skill:") and not id.begins_with("goto:"):
		_sfx.play("click", 1.0, -12.0)
	if id == "dlg_ok":
		_dlg_close()
		return
	# 中间那颗「进去看看」（M194）。走的是和点房间同一条路 ——
	# `enter_room()` 之后必须 `_drain_queue()`，否则房间里的奇物/战斗
	# 只是标了已访问，内容永远不结算。
	if id == "enter_room":
		if exp != null and exp.has_pending_room():
			exp.enter_room()
			_sync_exp_events()
			_drain_queue()
			queue_redraw()
		return
	if id == "curio_use":
		var st_c: Dictionary = (_curio_ask.get("step", {}) as Dictionary).duplicate(true)
		var it_c: String = str(_curio_ask.get("item", ""))
		_curio_ask = {}
		_room_phase = 1
		var before_c: int = _log.size()
		exp.resolve_curio(st_c, it_c)
		_fill_room_lines(before_c)
		return
	if id == "curio_skip":
		var st_s: Dictionary = (_curio_ask.get("step", {}) as Dictionary).duplicate(true)
		_curio_ask = {}
		_room_phase = 1
		var before_s: int = _log.size()
		exp.resolve_curio(st_s, "__none__")
		_fill_room_lines(before_s)
		return
	if id.begins_with("tk_swap:"):
		_swap_ask = id.substr(8)
		queue_redraw()
		return
	if id == "tk_swapcancel":
		_swap_ask = ""
		queue_redraw()
		return
	if id.begins_with("tk_swapsell:"):
		var si: int = int(id.substr(11))
		var want: String = _swap_ask
		_swap_ask = ""
		if si < 0 or si >= campaign.trinket_store.size() or want.is_empty():
			queue_redraw()
			return
		var got_money: int = campaign.shop.trinket_sell_price(str(campaign.trinket_store[si])) if campaign.shop != null else 0
		var why2: String = campaign.sell_trinket(si)
		if not why2.is_empty():
			_flash_msg("卖不掉（%s）" % why2)
			queue_redraw()
			return
		var why3: String = campaign.add_trinket(want)
		if not why3.is_empty():
			_flash_msg("还是放不下（%s），已折价 +%d 金" % [why3, got_money])
		else:
			_flash_msg("已换入「%s」，卖了 +%d 金" % [DdNames.trinket_name(want), got_money])
			# 从结算面板的待换列表里摘掉
			var left: Array = []
			for rr2 in (_settle_gain.get("trinket_refused", []) as Array):
				if str((rr2 as Dictionary).get("id", "")) != want:
					left.append(rr2)
			_settle_gain["trinket_refused"] = left
		campaign.save()
		queue_redraw()
		return
	if id.begins_with("party_revive:"):
		var rv_h: String = id.substr(13)
		var rv_cost: int = int((campaign.effective_recruit_cost(rv_h) as Dictionary).get("gold", 0))
		if not campaign.can_recruit(rv_h):
			_flash_msg("复活要 %d 金（或这人还活着）" % rv_cost)
			return
		if campaign.recruit(rv_h):
			# 捞回来直接放进出征名单：玩家的意图就是「我要用他」，
			# 再让他自己去点一次「上阵」是多余的一步。
			if not _prep_party.has(rv_h) and _prep_party.size() < Campaign.PARTY_MAX:
				_prep_party.append(rv_h)
				_party_persist()
			campaign.save()
			_flash_msg("%s 复活了（-%d 金）" % [_hero_label(rv_h), rv_cost])
			queue_redraw()
		return
	if id.begins_with("party_up:") or id.begins_with("party_down:"):
		var up: bool = id.begins_with("party_up:")
		var hid_p: String = id.substr(11 if up else 13)
		var i1: int = _prep_party.find(hid_p)
		if i1 >= 0:
			var j1: int = i1 - 1 if up else i1 + 1
			if j1 >= 0 and j1 < _prep_party.size():
				_prep_party.remove_at(i1)
				_prep_party.insert(j1, hid_p)
				_party_persist()
				queue_redraw()
		return
	if id.begins_with("party_up:") or id.begins_with("party_down:"):
		var up: bool = id.begins_with("party_up:")
		var hid_p: String = id.substr(11 if up else 13)
		var i1: int = _prep_party.find(hid_p)
		if i1 >= 0:
			var j1: int = i1 - 1 if up else i1 + 1
			if j1 >= 0 and j1 < _prep_party.size():
				_prep_party.remove_at(i1)
				_prep_party.insert(j1, hid_p)
				_party_persist()
				queue_redraw()
		return
	if id.begins_with("dock:"):
		match id.substr(5):
			"prep":
				# 「出征」先进**选关屏**（M197）。
				#
				# 原来这里直接 `S_PREP`，等于跳过了选区域/选难度这一整屏 ——
				# 而那一屏（`_draw_gate`）是玩家决定「去哪、打多难」的唯一地方。
				# 用户报「点出征没有选关界面了」就是这个：跳转没删，是被绕过。
				if campaign.alive_ids().is_empty():
					_flash_msg("名册里没有活人")
					return
				_state = S_GATE
			"town":
				_state = S_TOWN
			"roster":
				# 同上：这个 tab 已经从导航栏删掉，留着只是防别处还发这个 id
				_state = S_PARTY
			"party":
				if campaign.alive_ids().is_empty():
					_flash_msg("名册里没有活人")
					return
				_state = S_PARTY
			"shop":
				_state = S_SHOP
			"guild":
				if not _bld_unlocked("guild"):
					_flash_msg("公会还没解锁（还差 %d 次任务）" % _bld_need("guild"))
					return
				_state = S_GUILD
		_roster_open = ""
		_sel_trinket = ""
		queue_redraw()
		return
	if id == "supply_open":
		_supply_open = true
		queue_redraw()
		return
	if id == "supply_close":
		_supply_open = false
		queue_redraw()
		return
	if id.begins_with("supply_noop:"):
		_flash_msg("这一项要在「%s」用" % str(SUPPLY_USE_HINT.get(id.substr(13), "对应场合")))
		return
	if id.begins_with("supply_use:"):
		var su: String = id.substr(11)
		var msg: String = ""
		if su == "torch":
			if exp.torch <= 0:
				_flash_msg("没有火把了")
				return
			exp.torch -= 1
			exp.light = clampf(exp.light + 40.0, 0.0, 100.0)
			_want_light = exp.light
			msg = "点了一支火把"
		elif su == Shop.FOOD_KEY:
			# 每间房只能随手吃一次（M188）：不限次的话，1 份口粮换 12% 血、
			# 没有任何风险，而「休整」（2 份、+30~35%、还带减压和光照）
			# 每趟只有 1 次、还有 33% 被偷袭 —— 玩家当然一直点吃口粮，
			# 休整就彻底没用了。限制之后两者的取舍才成立。
			if int(exp.food) <= 0:
				_flash_msg("没有口粮了")
				return
			if int(exp.food_room_uses) >= 1:
				_flash_msg("这间房已经吃过一次了 —— 还想补就用「休整」")
				return
			exp.food -= 1
			exp.food_room_uses += 1
			for hk in exp.state.keys():
				var st5: Dictionary = exp.state[hk]
				if bool(st5.get("dead", false)):
					continue
				st5["hp_ratio"] = clampf(float(st5.get("hp_ratio", 1.0)) + 0.12, 0.0, 1.0)
			msg = "全队吃了点东西（+12% 生命）"
		elif su == "laudanum":
			if exp.supply_count("laudanum") <= 0:
				_flash_msg("没有鸦片酊了")
				return
			exp.supplies["laudanum"] = exp.supply_count("laudanum") - 1
			for hk2 in exp.state.keys():
				var st6: Dictionary = exp.state[hk2]
				if bool(st6.get("dead", false)):
					continue
				st6["stress"] = maxf(0.0, float(st6.get("stress", 0.0)) - 15.0)
			msg = "全队用了鸦片酊（压力 -15）"
		else:
			_flash_msg("这一项要在对应场合用")
			return
		_add_log("【补给】%s" % msg)
		_flash_msg(msg)
		queue_redraw()
		return
	if id.begins_with("revive:"):
		var rv: String = id.substr(7)
		var rcost2: int = int((campaign.effective_recruit_cost(rv) as Dictionary).get("gold", 0))
		if not campaign.can_recruit(rv):
			_flash_msg("复活要 %d 金，或者这个人还活着" % rcost2)
			return
		if campaign.recruit(rv):
			campaign.save()
			_flash_msg("%s 复活了（-%d 金）" % [_hero_label(rv), rcost2])
			queue_redraw()
		return
	if id.begins_with("hero_info:"):
		_roster_open = id.substr(10)
		queue_redraw()
		return
	if id == "sheet_close":
		_roster_open = ""
		queue_redraw()
		return
	# 作弊按钮（M104）。两套分发（`_activate` / `_activate_id`）都要挂：
	# 真实点击走后者，`--click=` 验收走前者，只挂一边会出现
	# 「手点有效、脚本验收无效」这种最难查的分裂。
	if id == "cheat_res":
		_cheat_resources()
		return
	if id.begins_with("del:"):
		_del_slot = int(id.substr(4))
		queue_redraw()
		return
	if id.begins_with("delno:"):
		_del_slot = -1
		queue_redraw()
		return
	if id.begins_with("delok:"):
		_delete_slot(int(id.substr(6)))
		return
	if id.begins_with("vol:"):
		_volume = clampi(int(id.substr(4)), 0, 100)
		_apply_volume()
		_save_settings()
		if _sfx != null:
			# 立刻试听：调音量时听不到声音等于盲调
			_sfx.play("click", 1.0, 0.0)
		queue_redraw()
		return
	if id.begins_with("slot:"):
		_enter_slot(int(id.substr(5)))
		return
	if id.begins_with("upgrade:"):
		var hid_u: String = id.substr(8)
		if campaign.upgrade(hid_u):
			campaign.save()
			_flash_msg("%s 升到 %d 阶" % [_hero_label(hid_u), campaign.gear_of(hid_u)])
		return
	if id.begins_with("recruit:"):
		var hid_r: String = id.substr(8)
		if campaign.recruit(hid_r):
			campaign.save()
			_flash_msg("%s 归队" % _hero_label(hid_r))
		return
	if id == "goto:guild":
		if not _bld_unlocked("guild"):
			_flash_msg("公会还没解锁（还差 %d 次任务）" % _bld_need("guild"))
			return
		# 「改技能（去公会）」的按钮（M143）。原来它落到下面 `goto:<数字>`
		# 那条战斗换位分支上：`int("guild")` 是 0，而队伍屏没有战斗，
		# 于是什么都不发生 —— 玩家点了没反应。
		var gav: Array = campaign.alive_ids()
		if gav.is_empty():
			_flash_msg("名册里没有活人")
			return
		_guild_hero = _party_hero if not _party_hero.is_empty() \
			and gav.has(_party_hero) else str(gav[0])
		_state = S_GUILD
		queue_redraw()
		return
	if id.begins_with("goto:"):
		if _battle != null:
			_move_mode = false
			_battle.submit_move(int(id.substr(5)))
			_drain_battle_events()
			_options = []
			_pending = {}
			_step_timer = _step_delay
		return
	if id.begins_with("skill:"):
		var idx: int = int(id.substr(6))
		if idx < 0 or idx >= _options.size():
			return
		var opt: Dictionary = _options[idx]
		if not bool(opt.get("usable", true)):
			_flash_msg(str(opt.get("why", "这个位置用不了")))
			queue_redraw()
			return
		var action: Dictionary = opt.action
		_pending = opt
		_retreat_arm = false
		_info_uid = -1
		# AOE 也进瞄准态（M65）。原来「AOE 或只剩一个合法目标」是一点即发，
		# 于是同一块面板里有两种操作方式：点单体要选人，点全体直接放出去了。
		# 玩家点「全体」往往只是想看看会打到谁，代价是一整个回合。
		# 现在只有「唯一合法目标」还自动确认（那不会打错，也省一次点击）。
		if not bool(action.target_aoe) and (opt.targets as Array).size() == 1:
			_submit(action, opt.targets)
		return
	if id == "be_continue":
		_continue_after_battle()
		return
	if id == "room_go":
		_room_go()
		return
	if id == "info_close":
		_info_uid = -1
		queue_redraw()
		return
	if id == "retreat":
		# 战斗中撤退是「丢掉整趟」，必须两下。第二下才真的走——
		# 和名册删人的 `_fire_pending` 同一套：举起、再确认、中途任何别的操作都会放下。
		if not _retreat_arm:
			_retreat_arm = true
			_flash_msg("再点一次确认撤退（全队 +%.0f 压力）" % float(db.rules.retreat_stress))
			queue_redraw()
			return
		_retreat_arm = false
		_do_retreat()
		return
	# —— 出发准备 ——
	if id.begins_with("prep:"):
		# prep:<size>:<level>[:<quest>]
		var parts: PackedStringArray = id.split(":", false)
		if parts.size() >= 3:
			_prep_size = str(parts[1])
			_prep_level = int(parts[2])
			_prep_quest = str(parts[3]) if parts.size() > 3 else "explore"
			_prep_pack = _restore_prep_pack()
			# 默认名单按**这一趟的等级**筛（M25），不能直接取 Campaign.default_party()：
			# 那样会把等级太高的人排进去，玩家要按到「出发」才看到报错。
			_prep_party = _party_restore(_prep_level)
			_state = S_PREP
			queue_redraw()
		return
	if id.begins_with("prep_pick:"):
		_toggle_party(str(id.substr(10)))
		return
	if id.begins_with("prep_add:") or id.begins_with("prep_sub:"):
		var add: bool = id.begins_with("prep_add:")
		var sid: String = id.substr(9)
		_adjust_pack(sid, 1 if add else -1)
		return
	if id == "shop_my_trinkets":
		_sel_trinket = ""
		_state = S_TRINKET
		queue_redraw()
		return
	if id == "shop_tab:0" or id == "shop_tab:1":
		_shop_tab = int(id.substr(9))
		queue_redraw()
		return
	if id.begins_with("sup_buy:"):
		var sid_b: String = id.substr(8)
		var rb: Dictionary = campaign.buy_supply(sid_b, 1)
		if bool(rb.get("ok", false)):
			# 当场存盘：补给是花钱买的，崩溃丢掉最不可接受。
			campaign.save()
			_flash_msg("买下 %s（-%d 金）" % [DdNames.supply_name(sid_b),
				int(rb.get("cost", 0))])
		else:
			_flash_msg(_shop_reason(str(rb.get("reason", ""))))
		queue_redraw()
		return
	if id == "shop_no":
		_shop_ask = {}
		queue_redraw()
		return
	if id == "shop_yes":
		var kind: String = str(_shop_ask.get("kind", ""))
		var ai: int = int(_shop_ask.get("idx", -1))
		_shop_ask = {}
		if kind == "buy":
			var w1: String = campaign.buy_shop_trinket(ai)
			if w1.is_empty():
				_flash_msg("已买下")
				campaign.save()
			else:
				_flash_msg(_shop_reason(w1))
		elif kind == "sell":
			var sold1: String = str(campaign.trinket_store[ai]) if ai >= 0 \
				and ai < campaign.trinket_store.size() else ""
			var e1: String = campaign.sell_trinket(ai)
			if e1.is_empty():
				_flash_msg("卖掉 %s，+%d 金币" % [DdNames.trinket_name(sold1),
					campaign.shop.trinket_sell_price(sold1)])
				campaign.save()
			else:
				_flash_msg(_shop_reason(e1))
		queue_redraw()
		return
	if id.begins_with("shop_buy:"):
		# 两步走（M183）：第一下只**选中并高亮**，第二下弹确认框。
		# 原来点一下就直接扣钱 —— 饰品是限定掉落，买错了没法退；
		# 而且手机上误触的概率比鼠标高得多。
		var bi: int = int(id.substr(9))
		if str(_shop_sel.get("kind", "")) != "buy" or int(_shop_sel.get("idx", -1)) != bi:
			_shop_sel = {"kind": "buy", "idx": bi}
			queue_redraw()
			return
		var bid_s: String = str(campaign.shop_stock[bi]) if bi >= 0 \
			and bi < campaign.shop_stock.size() else ""
		_shop_ask = {"kind": "buy", "idx": bi, "name": DdNames.trinket_name(bid_s),
			"price": campaign.shop.trinket_buy_price(bid_s) if campaign.shop != null else 0}
		_shop_sel = {}
		queue_redraw()
		return
	if id.begins_with("shop_sell:"):
		var si: int = int(id.substr(10))
		if str(_shop_sel.get("kind", "")) != "sell" or int(_shop_sel.get("idx", -1)) != si:
			_shop_sel = {"kind": "sell", "idx": si}
			queue_redraw()
			return
		var sold_nm: String = str(campaign.trinket_store[si]) if si >= 0 \
			and si < campaign.trinket_store.size() else ""
		_shop_ask = {"kind": "sell", "idx": si, "name": DdNames.trinket_name(sold_nm),
			"price": campaign.shop.trinket_sell_price(sold_nm) if campaign.shop != null else 0}
		_shop_sel = {}
		queue_redraw()
		return
		var sold: String = str(campaign.trinket_store[si]) if si >= 0 \
			and si < campaign.trinket_store.size() else ""
		var err2: String = campaign.sell_trinket(si)
		if err2.is_empty():
			_flash_msg("卖掉 %s，+%d 金币" % [DdNames.trinket_name(sold),
				campaign.shop.trinket_sell_price(sold)])
			campaign.save()
		else:
			_flash_msg(_shop_reason(err2))
		queue_redraw()
		return
	if id.begins_with("tk_store:"):
		# 点仓库里的一件：选中/取消选中。真正装上去要等玩家点某个槽，
		# 因为「装给谁」是这一屏唯一的决策，替玩家决定就失去意义了。
		var sid: String = id.substr(9)
		_sel_trinket = "" if _sel_trinket == sid else sid
		queue_redraw()
		return
	if id.begins_with("tk_slot:"):
		# tk_slot:<hid>:<slot>
		var rest: String = id.substr(8)
		var cut: int = rest.rfind(":")
		if cut > 0:
			_toggle_slot(rest.substr(0, cut), int(rest.substr(cut + 1)))
		return
	if id.begins_with("bld:"):
		var bid: String = id.substr(4)
		# 公会和商队是「已有屏的入口」，不重复造一个只有两个按钮的中间屏
		if bid == "guild":
			var av2: Array = campaign.alive_ids()
			_guild_hero = str(av2[0]) if not av2.is_empty() else ""
			_state = S_GUILD
		elif bid == "coach":
			# 马车直接进商店（M182）。
			#
			# 原来点马车会进一张「目录屏」：标题 + 一句说明 + 两颗按钮
			# （饰品仓库 / 补给与饰品买卖），剩下**整屏都是空的** ——
			# 用户原话「这界面存在的意义是什么」。真正的内容本来就在那两颗按钮里。
			# 而且这句话上面那条注释早就写着「不重复造一个只有两个按钮的中间屏」，
			# 只是当时只给 guild 加了分支，马车漏了。
			_state = S_SHOP
			_shop_tab = 0
		else:
			_building = bid
			var av3: Array = campaign.alive_ids()
			_building_hero = str(av3[0]) if not av3.is_empty() else ""
			# M30 修正：这里一直漏了 `_state = S_BUILDING`。
			# 只赋值 `_building` 不改状态的话，点了等于什么都没发生——
			# 而公会那条分支改了状态，所以八座建筑里只有它能进。
			# 表现上完全一致（按钮都高亮、都有 hover），所以两年期都没人发现。
			_fire_pending = ""
			_state = S_BUILDING
		queue_redraw()
		return
	if id.begins_with("bld_hero:"):
		_building_hero = id.substr(9)
		_fire_pending = ""    # 换人就取消上膛，否则会误删下一个选中的人
		queue_redraw()
		return
	if id.begins_with("bld_act:"):
		_do_building_action(id.substr(8))
		return
	if id.begins_with("hire:"):
		_do_hire(id.substr(5))
		return
	if id.begins_with("fire:"):
		# 第一次点只是「上膛」，第二次才真的删（见 _fire_pending 的注释）
		_fire_pending = id.substr(5)
		queue_redraw()
		return
	if id.begins_with("fire2:"):
		_do_fire(id.substr(6))
		return
	if id == "bld_back":
		_state = S_TOWN
		queue_redraw()
		return
	if id == "roster_page":
		# 名册屏已经并进队伍屏（M171），但城镇名册条的**表头**还在发这个 id，
		# 于是「点表头」和「点导航栏」进的是两个完全不同的界面 —— 用户一眼就看出来了。
		_roster_open = ""
		if not _party_hero.is_empty():
			_state = S_PARTY
		else:
			var av_p: Array = campaign.hero_ids_deployed_first()
			if not av_p.is_empty():
				_party_hero = str(av_p[0])
			_state = S_PARTY
		queue_redraw()
		return
	if id == "roster_back":
		_state = S_TOWN
		queue_redraw()
		return
	if id == "roster_coach":
		var av0: Array = campaign.alive_ids()
		_building = "coach"
		_building_hero = str(av0[0]) if not av0.is_empty() else ""
		_fire_pending = ""
		_state = S_BUILDING
		queue_redraw()
		return
	if id.begins_with("dock:"):
		match id.substr(5):
			"town":
				_state = S_TOWN
			"gate":
				_state = S_GATE
			"shop":
				_state = S_SHOP
			"party":
				_state = S_PARTY
		queue_redraw()
		return
	if id == "gate_back":
		_state = S_TOWN
		queue_redraw()
		return
	if id.begins_with("dungeon:"):
		# 换区域不改难度：玩家常常「还是这张短图，换个地方打」。
		# M32：区域现在同时决定「看哪一块板子」——任务板长在区域上，
		# 不跟着切的话会出现「顶着海湾的标题挑 weald 的任务」。
		_dungeon = id.substr(8)
		campaign.select_board_region(_dungeon)
		queue_redraw()
		return
	if id.begins_with("guild_pick:"):
		_guild_hero = id.substr(11)
		queue_redraw()
		return
	if id.begins_with("guild_skill:"):
		_toggle_skill(id.substr(12))
		return
	match id:
		"prep_go":
			_launch_with_pack()
		"prep_back":
			_state = S_TOWN
			queue_redraw()
		"open_guild":
			var av: Array = campaign.alive_ids()
			_guild_hero = str(av[0]) if not av.is_empty() else ""
			_state = S_GUILD
			queue_redraw()
		"close_guild":
			_state = S_TOWN
			queue_redraw()
		"idle_week":
			var iw: String = campaign.idle_week()
			if iw.is_empty():
				campaign.save()
				_flash_msg("过了一周")
			else:
				_flash_msg(iw)
			queue_redraw()
		"open_shop":
			_sel_trinket = ""
			_state = S_SHOP
			queue_redraw()
		"close_shop":
			_state = S_TOWN
			queue_redraw()
		"open_trinkets":
			_sel_trinket = ""
			_state = S_TRINKET
			queue_redraw()
		"close_trinkets":
			_sel_trinket = ""
			_state = S_TOWN
			queue_redraw()
		"start_short":
			_start_expedition("short", 1)
		"start_medium":
			_start_expedition("medium", 3)
		"start_long":
			_start_expedition("long", 5)
		"torch":
			if _sfx != null:
				_sfx.play("torch")
			_use_torch()
		"camp":
			if _sfx != null:
				_sfx.play("heal", 0.85, -4.0)
			_do_camp()
		"retreat":
			if _sfx != null:
				_sfx.play("door", 0.9)
			_do_retreat()
		"leave":
			if _sfx != null:
				_sfx.play("victory")
			_leave_dungeon()
		"pass":
			_submit({}, [])
		"movemode":
			_move_mode = true
			queue_redraw()
		"movecancel":
			_move_mode = false
			queue_redraw()
		"log_toggle":
			_log_open = not _log_open
			queue_redraw()
		"restart":
			back_to_town()
		"menu_quit":
			get_tree().quit()
		"del_cancel":
			_del_slot = -1
			queue_redraw()
		"menu_settings":
			_state = S_SETTINGS
			queue_redraw()
		"settings_back":
			_save_settings()
			_state = S_MENU
			queue_redraw()
		"victory_continue":
			# 通关之后不锁档：本作没有多周目，锁档等于把玩家攒的东西全扔了。
			back_to_town()
		"victory_new":
			# 开新档 = 真的清档重来（会盖掉当前 save）。
			# 这是胜利屏上的明确操作，不做二次确认——玩家刚打完整个战役，
			# 点这个就是想要重开，再弹一个「确定吗」只是多一步。
			campaign.new_game()
			campaign.save()
			back_to_town()
		_:
			# 兜底（M114 的初衷）：`_activate` 与 `_activate_id` 是**两套并行分发**，
			# 真实点击走 `_on_click() → _activate_id()`，而 `--click=` 验收走这里。
			# 新加的 id（队伍屏、饰品、作弊）只挂在后者，于是「手点有效、脚本验收无效」。
			#
			# **必须写在 match 里面**（M134 修）。原来放在 match 外面，
			# 而 match 的分支里大部分**没有 return** —— 于是匹配成功的 id
			# 执行完分支之后照样往下走，撞进兜底 → `_activate_id` → 又回 `_activate`
			# → 无限递归、栈溢出。表现就是「点某个按钮，客户端直接崩」，
			# 而且崩的按钮是随机的：取决于那个 id 在 `_activate_id` 里有没有对应分支。
			#
			# 注释里原来写着「上面每条分支都 return 了」——那句话是错的，别信。
			_activate_id(id, true)

## 删掉一个槽的存档（M48）。
##
## 只删文件，不碰其它槽：`save_1/2/3` 是三个独立文件，删一个不影响另外两个。
## 删完立刻重绘——留在确认态会让玩家以为没成功。
func _delete_slot(idx: int) -> void:
	var fname: String = "save_%d.json" % (idx + 1)
	var dir := DirAccess.open("user://")
	if dir != null and dir.file_exists(fname):
		dir.remove(fname)
	_del_slot = -1
	_flash_msg("存档 %d 已删除" % (idx + 1))
	queue_redraw()


## 从主菜单进入一个槽（M47）。
##
## 空槽不走特判：`_boot_campaign` 里 `load_or_new()` 发现没有文件就会开新档并立刻存档，
## 所以「点空槽 = 新开一档」是免费得到的，不需要两条分支各写一遍。
func _enter_slot(idx: int) -> void:
	_boot_campaign(_slot_path(idx))
	# 读档之后要对齐到存档里记的那个区域（城镇那排按钮高亮的正是它）
	if campaign != null:
		campaign.select_board_region(_dungeon)
	_state = S_TOWN
	queue_redraw()


func back_to_town() -> void:
	_state = S_TOWN
	_sel_trinket = ""
	exp = null
	_battle = null
	_options = []
	_pending = {}
	_settled = false
	_log.clear()


# ============================================================
# 绘制
# ============================================================

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), DdTheme.BG)
	# Spine 试验是最外层：它不参与任何界面状态（M119）
	_buttons.clear()
	_slots.clear()
	_room_hits.clear()
	_sheet_hits.clear()
	# 子节点的层级是固定的（永远在 self 之上），所以显示/隐藏要自己管（M80）：
	#   S_MAP  —— 地图层正常显示
	#   S_ROOM —— 地图层调暗垫底（卡片在更高一层，见 `_card_layer`）
	#   其它   —— 两层都收起来
	if _map_layer != null:
		if _state == S_MAP:
			# 补给面板开着的时候要把地图层收起来（M180）。
			#
			# 子节点的层级**永远在 self 之上**，而补给面板是画在 self 上的
			# （`_draw_supply_panel` 里的 `draw_rect`）。于是面板背景是实心的
			# `#161920`，地图的房间图标和走廊金线照样从上面透过来 ——
			# 看起来像「面板是半透明的」，其实是画序压反了。
			if _supply_open or _dlg_open or _hold_shown.begins_with("hero_stat:"):
				# 事件弹窗 / 补给面板 / 英雄长按浮层都要收地图层（M194/M201）。
				# `_map_layer` 是**子节点**，永远画在 self 之上 —— 只画一层遮罩
				# 根本盖不住它，房间格子会直接压在浮层文字上（截图里那块石头就是）。
				_map_layer.hide()
			else:
				_map_layer.show()
				_map_layer.modulate = Color(1.0, 1.0, 1.0, 1.0)
		elif _state == S_ROOM:
			_map_layer.hide()
		else:
			_map_layer.hide()
	# 卡片层先不用（M80 试过，绘制回调里仍有裸 draw_ 落在 self 上会报错）。
	# 卡片回到 self 上画，S_ROOM 时地图层直接收起来。
	if _card_layer != null:
		_card_layer.hide()
	if db == null:
		return

	match _state:
		S_TOWN:
			_draw_town()
		S_MAP:
			_draw_map()
		S_BATTLE:
			_draw_battle()
		S_PARTY:
			_draw_party()
		S_BATTLE_END:
			_draw_battle_end()
		S_ROOM:
			_draw_room_card()
		S_RESULT:
			_draw_result()
		S_TRINKET:
			_draw_trinket()
		S_PREP:
			_draw_prep()
		S_SHOP:
			_draw_shop()
		S_VICTORY:
			_draw_victory()
		S_MENU:
			_draw_menu()
		S_SETTINGS:
			_draw_settings()
		S_GUILD:
			_draw_guild()
		S_GATE:
			_draw_gate()
		S_ROSTER:
			_draw_roster_page()
		S_BUILDING:
			_draw_building()

	_draw_buttons()
	_draw_nav_bar()
	# 长按详情画在最上层（M183）：盖住底下的界面，
	# 但**不挡点击** —— 抬手就收，不需要按钮。
	_draw_hold_tip()
	_draw_floaters()
	if _dump_hits:
		_dump_hit_report()

	if _flash_life > 0.0:
		var a: float = clampf(_flash_life, 0.0, 1.0)
		# 城镇里名册条压到 70~180，提示条写 96 会被盖住一半（M125 发现：
		# 点作弊按钮、「金币 +10000」只露出下半截）。其他屏往上一点不冲突。
		# 名册条从 92 开始、126 高 → 到 218。提示条压在 96 会被遮，
		# 压在 196 还是在条里。放到条下面 232，正好是建筑区的上沿。
		# 位置按屏分：城镇名册条到 218，公会/建筑屏标题在 88 也会被压，
		# 只有地图和战斗那种顶部空旷的可以用 96。
		var fy: float = 96.0
		if _state == S_MAP:
			# 地图屏顶部有一条资源条（光照 / 火把 / 口粮 …，基线 76），
			# 下面紧跟着房间面板（约 130 起）——中间只有 ~54px。
			# 136 会压住「入口房间」标题，96 会压住资源条。
			# 所以位置取 118，并且**字号也跟着降到 34**（见下），
			# 48 号字高就是 48，夹不进这条缝。
			fy = 118.0
		if _state == S_TOWN:
			fy = _roster_y() + 140.0
		elif _state == S_GUILD or _state == S_BUILDING or _state == S_ROSTER:
			# 放底部按钮上方：这些屏顶部全是内容（名册页第一张卡从 64 开始、
			# 公会屏标题在 88），150 会直接压在卡片上。
			# 建筑屏还要再往上让 62：那里新加了升级条（M131），
			# 否则提示正好压在「等级 0/3」上。
			fy = size.y - 44.0 - 56.0 - (82.0 if _state == S_BUILDING else 18.0)
		# 描边（M155）：深色背景上的红字几乎看不清 —— 遭遇战提示尤其明显。
		# `_text` 不支持描边，所以**先画一圈黑字再压上彩色字**：
		# 八个方向各偏移 2px，等于把描边做出来，比 Godot 的 outline 参数可控。
		#
		# 限宽 + 折行（M200）：长句会冲出屏幕、压住标题栏。
		# 字号只在**放不下时**降：「踩中陷阱」这类短提示保持原来的大字
		# —— 大正是它存在的理由；长句降到 34 再折行。
		var maxw: float = size.x - 40.0
		var fsz: int = DdTheme.FONT_HERO + 8
		# 地图屏额外降一档（M201）：那条缝只有 54px 高，48 号字塞不进去。
		if _state == S_MAP \
				or _font.get_string_size(_flash, HORIZONTAL_ALIGNMENT_LEFT, -1, fsz).x > maxw:
			fsz = 34
		var flines: Array = _wrap_lines(_flash, fsz, maxw)
		var fcol := Color(DdTheme.CRIT.r, DdTheme.CRIT.g, DdTheme.CRIT.b, a)
		var ocol := Color(0.0, 0.0, 0.0, a * 0.95)
		var lh: float = float(fsz) + 4.0
		for li in flines.size():
			var s: String = str(flines[li])
			var tw: float = _font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, fsz).x
			var tx0: float = (size.x - tw) * 0.5
			var ly: float = fy + float(li) * lh
			for dx in [-2.0, 0.0, 2.0]:
				for dy in [-2.0, 0.0, 2.0]:
					if dx == 0.0 and dy == 0.0:
						continue
					draw_string(_font, Vector2(tx0 + dx, ly + dy), s,
						HORIZONTAL_ALIGNMENT_LEFT, -1, fsz, ocol)
			draw_string(_font, Vector2(tx0, ly), s,
				HORIZONTAL_ALIGNMENT_LEFT, -1, fsz, fcol)


# —— 基础绘制工具 ——

func _text(pos: Vector2, s: String, fs: int, col: Color,
		align: int = HORIZONTAL_ALIGNMENT_LEFT, width: float = -1.0) -> void:
	# 描边（M83）：字压在立绘、砖墙、血迹上时，纯色文字经常糊成一片。
	# 先画一圈深色描边再画字，靠对比度把字「抠」出来。
	# 宽度跟着字号走：11px 的小字用 3px 描边会糊成一团黑块，34px 的飘字用 1px 又等于没有。
	var ow: int = int(clampf(roundf(float(fs) * 0.16), 1.0, 4.0))
	_dci().draw_string_outline(_font, pos, s, align, width, fs, ow,
		Color(0.02, 0.02, 0.03, 0.9 * col.a))
	_dci().draw_string(_font, pos, s, align, width, fs, col)


func _panel(r: Rect2, bg: Color = DdTheme.PANEL, edge: bool = true) -> void:
	_dci().draw_rect(r, bg)
	# 皮肤（M59）：底色仍由上面的 `_dci().draw_rect` 决定，皮肤只叠「材质 + 边框」。
	# 这样切主题色（暗/更暗/选中）不用重画任何贴图。
	if _sk_grain != null:
		# 污渍只在够大的面板上铺：小卡片铺 128×128 的斑块会显得像脏点，
		# 而且每多一层都是每帧的 fill rate
		if _sk_stain != null and r.size.x > 140.0 and r.size.y > 100.0:
			_dci().draw_texture_rect(_sk_stain, r, true)
		_dci().draw_texture_rect(_sk_grain, r, true)
	if edge:
		# 两级皮肤（M59）：小卡片用轻量版 —— 四张并排时每张都带金角
		# 会像挂了一墙相框。大面板才配角饰。
		if r.size.x >= 380.0 and r.size.y >= 180.0 and _sk_panel != null:
			_draw_nine(_sk_panel, r, 24.0)
			# 角花暂不启用：实测「面板边框 24px + 雕花臂长 76px」对不齐，
			# 画在内侧压头像、画在外侧像漂浮。要用得先把边框加厚到 40+。
			# `_draw_ornaments()` 和 `orn.png` 都留着，换厚边框设计时直接开。
		elif _sk_card != null:
			_draw_nine(_sk_card, r, 8.0)
		elif _sk_panel != null:
			_draw_nine(_sk_panel, r, 24.0)
		else:
			_dci().draw_rect(r, DdTheme.PANEL_EDGE, false, 1.0)


## 可点方块的统一外观（M31）。
##
## 之前每个调用点自己 _dci().draw_rect，于是「选中」有三种长相：
## 城镇区域按钮是 2px 蓝边、准备屏出战卡是 ✓ 前缀、建筑行只是 hover 提亮。
## 同一种状态三种表现，玩家每换一屏都要重新学一遍「我选了什么」。
enum { TILE_IDLE, TILE_HOVER, TILE_ACTIVE, TILE_OFF, TILE_DANGER, TILE_PRESS }


func _tile(r: Rect2, st: int, bg: Color = DdTheme.PANEL_DEEP) -> void:
	# 皮肤（M59）：只换「边框」，fill 仍由每个状态自己决定。
	# 这样同一张 btn.png 能用在普通按钮、区域卡、技能格上 ——
	# 它们的底色本来就不同（BTN / PANEL_DEEP / BTN_ACTIVE）。
	var fill: Color = bg
	match st:
		TILE_ACTIVE:
			fill = DdTheme.BTN_ACTIVE
		TILE_HOVER:
			fill = DdTheme.BTN_HOVER
		TILE_OFF:
			fill = DdTheme.BTN_OFF
		TILE_DANGER, TILE_PRESS:
			fill = DdTheme.BTN if st == TILE_DANGER else DdTheme.BTN_ACTIVE
		_:
			fill = bg
	draw_rect(r, fill)
	if _sk_btn != null:
		_draw_nine(_sk_btn, r, 12.0)
	else:
		# 无皮肤时保持原来的细边框
		match st:
			TILE_HOVER:
				draw_rect(r, DdTheme.DIM, false, 1.0)
			TILE_OFF:
				draw_rect(r, DdTheme.PANEL_EDGE, false, 1.0)
			TILE_PRESS:
				draw_rect(r, DdTheme.PANEL_DEEP, false, 2.0)
			TILE_DANGER:
				pass
			_:
				draw_rect(r, DdTheme.PANEL_EDGE, false, 1.0)
	# 选中 / 危险的外框永远画在最上面：它要压过皮肤边框
	match st:
		TILE_ACTIVE:
			draw_rect(r, DdTheme.PARTY, false, 2.0)
		TILE_DANGER:
			# M65：金色（CRIT）改成红（WARN）。金色在本作里是「你选中了/暴击了」，
			# 用在「撤退」「删人」这种按钮上，会把最该谨慎的那个画成最醒目的主按钮。
			draw_rect(r, DdTheme.WARN, false, 2.0)


func _bar(r: Rect2, ratio: float, fill: Color, track: Color) -> void:
	draw_rect(r, track)
	var w: float = clampf(ratio, 0.0, 1.0) * r.size.x
	if w > 0.5:
		draw_rect(Rect2(r.position, Vector2(w, r.size.y)), fill)


## 所有屏共用的表头：一条 56 高的横带，标题在左、提示在右。
##
## 高度、边距、字号都从令牌取——之前 52 是写死的，五处内容面板按 88 起排，
## 中间那 36px 的空白没有任何依据，改一次要试半天。
func _header(title: String, hint: String) -> void:
	# 皮肤（M59）：整条表头换成一块「铁牌」，左右端有折角和铆钉，
	# 中段是纵向渐变 —— 横向拉伸不会破坏它。
	if _sk_banner != null:
		_draw_nine_h(_sk_banner, Rect2(0.0, 0.0, size.x, float(DdTheme.HEADER_H)), 36.0)
	else:
		draw_rect(Rect2(0, 0, size.x, DdTheme.HEADER_H), DdTheme.PANEL)
		draw_line(Vector2(0, DdTheme.HEADER_H), Vector2(size.x, DdTheme.HEADER_H),
			DdTheme.PANEL_EDGE, 1.0)
	# 两栏分宽度（M165）：原来 hint 占 `size.x-620` 起的 592（= 整条 79%），
	# 长标题（「出发准备 · 荒野 · 短途 1 级」）横着压上去叠成一团。
	# 反过来把标题限到 110 又会把区域信息整个切掉。
	# 现在按 45% / 55% 分：标题降一档字号（H1→BD）才放得下完整的一句。
	var hint_w: float = size.x * 0.46
	_text(Vector2(DdTheme.MARGIN, 33), title, DdTheme.FONT_BD, DdTheme.TEXT,
		HORIZONTAL_ALIGNMENT_LEFT, size.x - hint_w - DdTheme.MARGIN - 12.0)
	_text(Vector2(size.x - hint_w - 12.0, 32), hint, DdTheme.FONT_MD, DdTheme.FAINT,
		HORIZONTAL_ALIGNMENT_RIGHT, hint_w)


## 名册抽屉是否正盖着屏幕（M147）。
##
## 这个判断原来在**两处各写一遍**：`_draw_buttons`（不画底下的按钮）
## 和 `_hit_id_at`（不响应底下的点击）。M140 那次只补了后者，
## 结果名册页的浮层能点穿 —— 而两份代码各写各的，靠人记着同步。
func _sheet_modal() -> bool:
	return (_state == S_TOWN or _state == S_ROSTER) and not _roster_open.is_empty()


## 底部导航栏（M163）：城镇类界面常驻，切屏不消失。
##
## 之前每个界面底部都有一颗「返回城镇」，等于把「回主界面」当成唯一的导航 ——
## 想看名册得先回城镇、再点名册，两跳。现在底部一条固定 tab，
## 和微信底部导航一个意思。
##
## **地牢内不显示**（用户明确）：探索和战斗时屏幕高度是稀缺资源，
## 而且那两块地方本来就不该有「去商店」这种出口。
## **顺序按玩家一局的动线排**（M194 用户指定）：城镇 → 公会 → 出征 → 队伍 → 商店。
##
## 原来是「出征 / 城镇 / 队伍 / 商店 / 公会」——出征排第一，因为它是主要出口；
## 但实际动线是「在城镇里招募、去公会接任务、配好队再出征」，
## 把最后一环放在第一个位置，每局都要往左跳。
const DOCK_TABS: Array = [
	["dock:town", "城镇", 0],
	["dock:guild", "公会", 7],
	# 出征 tab 落到**选关屏**（S_GATE=12），不是准备屏（S_PREP=5）——
	# 第三列只用来判高亮，实际跳转在 `dock:` 分支里。
	["dock:prep", "出征", 12],
	["dock:party", "队伍", 16],
	["dock:shop", "商店", 6],
]


func _dock_visible() -> bool:
	return _state == S_TOWN or _state == S_ROSTER or _state == S_PARTY \
		or _state == S_SHOP or _state == S_GUILD or _state == S_BUILDING \
		or _state == S_TRINKET or _state == S_PREP or _state == S_GATE


func _draw_nav_bar() -> void:
	if not _dock_visible():
		return
	var y: float = size.y - NAV_H
	draw_rect(Rect2(0.0, y, size.x, NAV_H), Color(0.018, 0.018, 0.024, 0.98))
	draw_line(Vector2(0.0, y), Vector2(size.x, y), DdTheme.PANEL_EDGE, 1.0)
	var tw: float = size.x / float(DOCK_TABS.size())
	for i in DOCK_TABS.size():
		var t: Array = DOCK_TABS[i]
		var r := Rect2(float(i) * tw, y, tw, NAV_H)
		var active: bool = _state == int(t[2])
		if active:
			draw_rect(r, DdTheme.PANEL_HI)
			draw_rect(Rect2(r.position.x, r.position.y, tw, 3.0), DdTheme.CRIT)
		elif r.has_point(_mouse):
			draw_rect(r, DdTheme.BTN_HOVER)
		_text(Vector2(r.position.x, r.position.y + 40.0), str(t[1]),
			DdTheme.FONT_BD, DdTheme.CRIT if active else DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_CENTER, tw)
		_add_hit(r, str(t[0]))


func _draw_buttons() -> void:
	# 名册抽屉是模态的（M58）：它在 `_draw_town()` 里画，而按钮统一在
	# `_draw()` 末尾画，所以不跳过的话，底下那排按钮会浮在抽屉上面 ——
	# 第一版就是这样，「休整一周」压在关闭按钮底下露出来。
	if _sheet_modal():
		return
	for b in _buttons:
		# 日志浮层铺了半屏（M202）：底下的技能 / 挪位 / 撤退照画，就会浮在浮层
		# **上面**被看见、被点到。只放行浮层自己的「关闭」。
		if _log_open and _state == S_BATTLE and str(b.get("id", "")) != "log_toggle":
			continue
		var r: Rect2 = b.rect
		var label: String = str(b.get("label", ""))
		if label.is_empty():
			continue
		var hover: bool = r.has_point(_mouse)
		var enabled: bool = bool(b.enabled)
		# 按下态（M58）：手指正压在这个按钮上。
		var pressed: bool = hover and not _press_id.is_empty() and str(b["id"]) == _press_id
		# 危险态（M28）：解雇的「再点一次确认」必须一眼看出和平常按钮不一样。
		# 只改文字不改样式没用——玩家连点两下时不会读字。
		var danger: bool = bool(b.get("danger", false))
		# 强调态（M142）：离开地牢这种「这一趟的目的地」按钮，
		# 和旁边的火把/休整长得一样不合适 —— 金底 + 金框。
		var accent: bool = bool(b.get("accent", false))
		var st: int = TILE_IDLE
		if not enabled:
			st = TILE_OFF
		elif pressed:
			# 按下优先于 danger：危险按钮按下去那一刻也要有「压住了」的反馈，
			# 否则「再点一次确认」的第一下完全没有触感。
			st = TILE_PRESS
		elif danger:
			st = TILE_DANGER
		elif hover:
			st = TILE_HOVER
		_tile(r, st, DdTheme.PANEL_HI if accent else DdTheme.BTN)
		if accent:
			draw_rect(r, DdTheme.CRIT, false, 2.0)
		# 文字跟着下沉 1px：只有底色变化时，49px 高的按钮在大屏上看不出「按进去」，
		# 位移 1px 比换颜色便宜，但手感差别很大。
		_text(Vector2(r.position.x, r.position.y + r.size.y * 0.5 + 5.0 + (1.0 if pressed else 0.0)),
			label, DdTheme.FONT_BD,
			DdTheme.FAINT if not enabled else (
				DdTheme.CRIT if (danger or accent) else DdTheme.TEXT),
			HORIZONTAL_ALIGNMENT_CENTER, r.size.x)


func _add_button(r: Rect2, id: String, label: String, enabled: bool = true,
		danger: bool = false, accent: bool = false) -> void:
	_buttons.append({"rect": r, "id": id, "label": label, "enabled": enabled,
		"danger": danger, "accent": accent})


## —— 横向滚动区（M58）——
##
## 一个区 = 一条定高的横向带子，卡片超出就滑动。三个要点：
##   1. 绘制用 `canvas_item_set_clip_rect` 裁剪，卡片不会画到面板外；
##   2. 按下先不触发点击，等抬手时看「有没有拖动超过 8px」再决定点还是滑；
##   3. 抬手吸附到整卡边界，不停在半张卡上。
## 按下（M58 反馈重构）。
##
## **只记录，不触发。** 这是这次改动的核心：原来按下瞬间就 `_on_click`，
## 于是「按住」这件事在屏幕上不存在 —— 手指落下、界面已经切走了，
## 玩家既看不到自己按中了什么，也没有反悔的机会。
##
## 滚动区要在按下时就接管（否则拖动会被判成点击），所以两者都记。
func _press_begin(pos: Vector2) -> void:
	_mouse = pos
	var hk0: String = _hit_id_at(pos)
	if hk0.begins_with("skill:") or hk0.begins_with("guild_skill:") \
			or hk0.begins_with("tk_store:"):
		_hold_id = hk0
		_hold_t = 0.0
	else:
		_hold_id = ""
		_hold_t = 0.0
	# 地图底部队伍条：按下 = 准备拖拽换位（M176）
	if _state == S_MAP and not _strip_rects.is_empty():
		for sr0 in _strip_rects:
			if (sr0["rect"] as Rect2).has_point(pos):
				_drag_card = {"id": str(sr0["id"]), "from": -1,
					"pos": pos, "moved": false, "strip": true}
				# 同一张卡也支持长按看状态（M201）：拖动和长按不冲突 ——
				# 拖拽要「移动超过阈值」才成立，长按是「按住不动 0.45 秒」。
				_hold_id = "hero_stat:%s" % str(sr0["id"])
				_hold_t = 0.0
				_press_id = ""
				queue_redraw()
				return
	# 队伍屏：按下左侧卡片 = 准备拖拽换位（M173）
	if _state == S_PARTY:
		for pr in _party_rects:
			if (pr["rect"] as Rect2).has_point(pos):
				_drag_card = {"id": str(pr["id"]), "from": _prep_party.find(str(pr["id"])),
					"pos": pos, "moved": false}
				_press_id = ""
				queue_redraw()
				return
	# 地图面板按下 = 准备拖拽（M78）。松手时位移不足 6px 才算点击，
	# 否则拖动地图会顺手把手指底下那间房点掉。
	if _state == S_MAP and _map_rect.has_point(pos):
		_map_drag = true
		_map_drag_pos0 = pos
		_map_drag_pan0 = _map_pan
		_map_drag_moved = false
		# 一按下就关掉自动居中：不关的话下一帧 `_draw_grid_map` 会把你
		# 刚拖出来的位置又拉回去，看起来像「拖不动」。
		_map_pan_auto = false
		_press_id = _hit_id_at(pos)
		queue_redraw()
		return
	for k in _hscroll_zone_meta.keys():
		var m: Dictionary = _hscroll_zone_meta[k]
		if (m["rect"] as Rect2).has_point(pos):
			_drag_zone = str(k)
			_drag_x0 = pos.x
			_drag_off0 = float(_hscroll.get(k, 0.0))
			_drag_moved = false
			# 滚动区里按下的那张卡也要亮：不然按住卡片毫无反应，
			# 玩家分不清「按到了卡」还是「按在空白处准备滑」
			_press_id = _hit_id_at(pos)
			queue_redraw()
			return
	_press_id = _hit_id_at(pos)
	if not _press_id.is_empty():
		queue_redraw()


## 抬手：位置没变才触发。
func _press_end(pos: Vector2) -> void:
	# 长按弹出来的详情，抬手就收（M183）
	if not _hold_shown.is_empty():
		_hold_shown = ""
		_hold_id = ""
		_hold_t = 0.0
		queue_redraw()
		return
	_hold_id = ""
	_hold_t = 0.0
	# 队伍屏拖拽结束（M173）：落在哪张卡上就换到那个位置。
	# 没移动 = 普通点击（选中），走原来的路径。
	if not _drag_card.is_empty():
		var moved: bool = bool(_drag_card.get("moved", false))
		var did: String = str(_drag_card.get("id", ""))
		# 地图队伍条（M176）：改的是 `exp.hero_ids` 的顺序 ——
		# 地牢里的站位就是它，换完下一场战斗立刻按新顺序排。
		if bool(_drag_card.get("strip", false)):
			_drag_card = {}
			# 真拖动了就不是长按（M201）：不清的话，松手后那张状态浮层还挂着，
			# 而玩家以为自己只是换了个站位。
			if moved:
				_hold_id = ""
				_hold_shown = ""
			if moved and exp != null:
				var to_i: int = -1
				for sr1 in _strip_rects:
					if (sr1["rect"] as Rect2).has_point(pos):
						to_i = exp.hero_ids.find(str(sr1["id"]))
						break
				var from_i: int = exp.hero_ids.find(did)
				if to_i >= 0 and from_i >= 0 and to_i != from_i:
					var who2: String = str(exp.hero_ids[from_i])
					exp.hero_ids.remove_at(from_i)
					exp.hero_ids.insert(to_i, who2)
					_exp_persist()
					_flash_msg("%s 换到第 %d 号位" % [_hero_label(who2), to_i + 1])
				queue_redraw()
			return
		_drag_card = {}
		if moved:
			var target: int = -1
			for pr2 in _party_rects:
				if (pr2["rect"] as Rect2).has_point(pos):
					target = _prep_party.find(str(pr2["id"]))
					break
			var from: int = _prep_party.find(did)
			if target >= 0 and from >= 0 and target != from:
				var who: String = _prep_party[from]
				_prep_party.remove_at(from)
				_prep_party.insert(target, who)
				_party_persist()
				_flash_msg("%s 换到第 %d 号位" % [_hero_label(who), target + 1])
			queue_redraw()
			return
		# 没拖动：当成普通点击继续往下走
		_party_hero = did if not did.is_empty() else _party_hero
	_mouse = pos
	if _map_drag:
		var moved_m: bool = _map_drag_moved
		var pressed_id: String = _press_id
		_map_drag = false
		_map_drag_moved = false
		_press_id = ""
		# 和下面那条一样的规则：抬手时还在同一个格子上才算点中。
		# 拖动地图时手指大概率会掠过别的房间，不判这个会顺手走进隔壁。
		if not moved_m and not pressed_id.is_empty() and _hit_id_at(pos) == pressed_id:
			_activate_id(pressed_id)
		queue_redraw()
		return
	if not _drag_zone.is_empty():
		var moved: bool = _drag_moved
		var zone: String = _drag_zone
		_drag_zone = ""
		_drag_moved = false
		_press_id = ""
		if moved:
			_hscroll_snap(zone)
		else:
			# 没拖动 = 就是点了一下卡片
			_activate_id(_hit_id_at(pos))
		queue_redraw()
		return
	var id: String = _press_id
	_press_id = ""
	queue_redraw()
	if id.is_empty():
		return
	# 抬手时还在同一个控件上才算数：按下后滑开 = 取消。
	# 触屏上这是唯一能反悔的动作，也是防误触的最后一道。
	if _hit_id_at(pos) == id:
		_activate_id(id)


## 某个热区当前该画成什么样（M58）。自定义热区统一走这个，
## 免得每处各写一套 hover 判断、还漏掉按下态。
func _hit_state(r: Rect2, id: String) -> int:
	if not _press_id.is_empty() and id == _press_id and r.has_point(_mouse):
		return TILE_PRESS
	if r.has_point(_mouse):
		return TILE_HOVER
	return TILE_IDLE


## 图集图标（M59 交付）：`assets/art/ui/skin/atlas/*.png`。
##
## 这些是出图方按图集交付、再由 `tools/slice_atlas.py` 切出来的单体图，
## 已经 trim + 居中 + 缩放到「显示尺寸 ×2」。缺图返回 null，调用方退回纯文字。
func _ico(name: String) -> Texture2D:
	return _skin.texture("skin/atlas", name)


## 在 (x, y) 处画一个图标，返回右边界。图标按正方形给，宽高都等于 sz。
func _draw_ico(name: String, pos: Vector2, sz: float, tint: Color = Color(1, 1, 1, 1)) -> float:
	var tex: Texture2D = _ico(name)
	if tex == null:
		return pos.x
	var k: float = sz / float(maxi(1, maxi(tex.get_width(), tex.get_height())))
	var w: float = float(tex.get_width()) * k
	var h: float = float(tex.get_height()) * k
	draw_texture_rect(tex, Rect2(pos.x + (sz - w) * 0.5, pos.y + (sz - h) * 0.5, w, h),
		false, tint)
	return pos.x + sz


## 九宫格：把一张 48×48 的边框贴图拉成任意尺寸（M59）。
##
## 四角固定、四边只沿一个方向拉伸、中间拉伸但不显示内容
## （边框贴图的中间是完全透明的，底下的底色和材质会透上来）。
## 这样一套 48×48 就能覆盖从 40×22 的小格子到 702×720 的抽屉。
func _draw_nine(tex: Texture2D, r: Rect2, m: float) -> void:
	var ts: Vector2 = tex.get_size()
	if r.size.x < m * 2.0 or r.size.y < m * 2.0:
		# 比九宫格还小的控件：整张缩下去，硬套九宫格会取到负宽度
		draw_texture_rect(tex, r, false)
		return
	var xs: Array = [[0.0, m, m], [m, ts.x - m, r.size.x - m * 2.0], [ts.x - m, ts.x, m]]
	var ys: Array = [[0.0, m, m], [m, ts.y - m, r.size.y - m * 2.0], [ts.y - m, ts.y, m]]
	for i in 3:
		for j in 3:
			var sx: float = float(xs[i][0])
			var sy: float = float(ys[j][0])
			var sw: float = float(xs[i][1]) - sx
			var sh: float = float(ys[j][1]) - sy
			var dw: float = float(xs[i][2])
			var dh: float = float(ys[j][2])
			if sw <= 0.0 or sh <= 0.0 or dw <= 0.0 or dh <= 0.0:
				continue
			var px: float = r.position.x + (0.0 if i == 0 else (m if i == 1 else r.size.x - m))
			var py: float = r.position.y + (0.0 if j == 0 else (m if j == 1 else r.size.y - m))
			draw_texture_rect_region(tex, Rect2(px, py, dw, dh), Rect2(sx, sy, sw, sh))


## 横向九宫格（M59）：左右端固定、中段拉伸、纵向整体不切。
##
## 横幅和分隔线都是「高度固定、宽度随屏幕变」的东西，
## 用 3×3 的话纵向中间区会被压成负高度，所以单独走这一条。
func _draw_nine_h(tex: Texture2D, r: Rect2, mx: float) -> void:
	var ts: Vector2 = tex.get_size()
	if r.size.x <= mx * 2.0:
		draw_texture_rect(tex, r, false)
		return
	draw_texture_rect_region(tex, Rect2(r.position.x, r.position.y, mx, r.size.y),
		Rect2(0.0, 0.0, mx, ts.y))
	draw_texture_rect_region(tex,
		Rect2(r.position.x + mx, r.position.y, r.size.x - mx * 2.0, r.size.y),
		Rect2(mx, 0.0, ts.x - mx * 2.0, ts.y))
	draw_texture_rect_region(tex,
		Rect2(r.position.x + r.size.x - mx, r.position.y, mx, r.size.y),
		Rect2(ts.x - mx, 0.0, mx, ts.y))


## 四角雕花（M59）。
##
## 用 `draw_set_transform` 做镜像：同一张贴图覆盖四个角，不用存四张。
## 注意每画完一个角必须复位 —— 不复位的话后面所有绘制都会跟着翻转。
func _draw_ornaments(r: Rect2, sz: float) -> void:
	if _sk_orn == null:
		return
	# 角花骑在边框上：向外偏 1/3，一半在面板外。
	# 全画在内侧会压住头像和标题 —— 面板边框只有 24px，装不下有细节的雕花。
	var o: float = sz * 0.34
	var corners: Array = [
		[Vector2(r.position.x - o, r.position.y - o), Vector2(1.0, 1.0)],
		[Vector2(r.position.x + r.size.x + o, r.position.y - o), Vector2(-1.0, 1.0)],
		[Vector2(r.position.x - o, r.position.y + r.size.y + o), Vector2(1.0, -1.0)],
		[Vector2(r.position.x + r.size.x + o, r.position.y + r.size.y + o), Vector2(-1.0, -1.0)],
	]
	for c in corners:
		draw_set_transform(c[0], 0.0, c[1])
		# 压暗一档：原图偏亮金，和冷灰边框放一起会「跳」出来
		draw_texture_rect(_sk_orn, Rect2(Vector2.ZERO, Vector2(sz, sz)), false,
			Color(0.86, 0.84, 0.82, 0.95))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


## 一条带中心纹章的分隔线（M59）。没有皮肤时退回一条细线。
func _divider(x: float, y: float, w: float) -> void:
	if _sk_divider != null:
		_draw_nine_h(_sk_divider, Rect2(x, y - 7.0, w, 14.0), 23.0)
	else:
		draw_line(Vector2(x, y), Vector2(x + w, y), DdTheme.PANEL_EDGE, 1.0)


## 命中反馈的通用覆盖层（M58）：悬停一档、按下一档。
##
## 用「白色半透明叠加」而不是替换底色：卡片底色各屏不同
## （`PANEL_DEEP` / `PANEL_HI` / `TILE_ACTIVE`），换底色得逐处对色阶，
## 叠加一层则对任何底色都成立，也不会盖掉「选中」那圈蓝框。
##
## 必须画在 `_panel()` 之后、选中边框之前 —— 画在最后会把选中框染白。
func _hit_overlay(r: Rect2, id: String, edge: bool = true) -> void:
	match _hit_state(r, id):
		TILE_PRESS:
			_dci().draw_rect(r, Color(1.0, 1.0, 1.0, 0.10))
			if edge:
				_dci().draw_rect(r.grow(-1.0), DdTheme.DIM, false, 2.0)
		TILE_HOVER:
			_dci().draw_rect(r, Color(1.0, 1.0, 1.0, 0.045))
			if edge:
				_dci().draw_rect(r, DdTheme.DIM, false, 1.0)


## 某个坐标会命中哪个控件（M58）。命中优先级和 `_on_click` 原来的一致：
## 地图房间 > 战斗目标 > 普通按钮。
##
## 抽出来是因为现在按下和抬手要**分别**回答一次「这是谁」，
## 两次答案相同才触发 —— 判定逻辑只能有一份。
func _hit_id_at(pos: Vector2) -> String:
	# 抽屉打开时它是模态的：只有抽屉里的东西能点，点别处就是关掉它。
	# 必须在所有其它判定之前 —— 否则会点到抽屉底下的名册卡/建筑卡。
	#
	# **必须和 `_draw_buttons` 的模态判断保持一致**（M140）：
	# 那边写的是 `S_TOWN or S_ROSTER`，这边原来只有 `S_TOWN`，
	# 于是名册页打开详情之后，点面板的空白处会穿透到背后的名册卡上
	# —— 面板看着盖住了，其实那一片还是「活的」。
	# 补给面板也是模态的（M154）。绘制那边 `_draw_map` 一开头就 return 了，
	# 命中这边不挡的话，点面板空白处会穿透到背后的房间格 ——
	# 和 M140 的浮层穿透是**同一个错**，这次先想到了。
	if _log_open and _state == S_BATTLE:
		# 日志浮层是模态的（M202）。它铺了半屏，底下的技能 / 挪位 / 撤退
		# 如果照常可点，玩家想关浮层却按到了「撤退」—— 那是丢掉整趟的动作。
		# 和 M140（名册抽屉）、M154（补给面板）同一个错，这是第三次。
		# **`_draw_buttons` 那边必须有同样的判断**，只拦一边就是「看着盖住了、其实能点」。
		for b in _buttons:
			if str(b["id"]) == "log_toggle" and (b["rect"] as Rect2).has_point(pos):
				return "log_toggle"
		return ""      # 点空白：`_on_click` 会当成「关掉浮层」
	if not _curio_ask.is_empty():
		for b in _buttons:
			if (b["rect"] as Rect2).has_point(pos):
				return str(b["id"])
		return "curio_skip"   # 点空白 = 空手翻
	if _supply_open:
		for b in _buttons:
			if (b["rect"] as Rect2).has_point(pos):
				return str(b["id"])
		return "supply_close"
	if _sheet_modal():
		for b in _sheet_hits:
			if (b["rect"] as Rect2).has_point(pos):
				return str(b["id"])
		return "sheet_close"
	if _state == S_MAP:
		for h in _room_hits:
			if (h.rect as Rect2).has_point(pos):
				return "room:%d" % int(h.id)
	if _state == S_BATTLE and _battle != null and _battle.awaiting_input != null \
			and not _pending.is_empty():
		for sl in _slots:
			if (sl.rect as Rect2).has_point(pos):
				return "tgt:%d" % int(sl.uid)
	# 非瞄准态点单位 = 看状态（M65 续）。和「瞄准态点目标 = 出手」不冲突：
	# 那两个状态本来就是互斥的，先用 pending 判断，走不到这里。
	# 但浮层打开时它是模态的：**先判它自己的关闭按钮**。
	# 不先判的话，「关闭」落在底下那个单位的 slot 矩形里（浮层盖在立绘上），
	# 点下去变成「切换到那个单位」，按钮永远按不动。
	if _state == S_BATTLE and _info_uid >= 0:
		for b0 in _buttons:
			if str(b0["id"]) == "info_close" and (b0["rect"] as Rect2).has_point(pos):
				return "info_close"
	if _state == S_BATTLE and _battle != null and _pending.is_empty():
		for sl2 in _slots:
			if (sl2.rect as Rect2).has_point(pos):
				return "info:%d" % int(sl2.uid)
	for b in _buttons:
		if not bool(b.get("enabled", true)):
			continue
		if (b["rect"] as Rect2).has_point(pos):
			return str(b["id"])
	return ""


## `from_activate`（M136）：标明这次是**从 `_activate` 兜底过来的**。
##
## 两个分发函数都要兜底对方（真实点击走这里、`--click` 走那边），
## 但两边都无条件回调就是死环 —— 只要 id 两边都不认识就会栈溢出。
## 带上来源标记之后，兜底只走**一个来回**：过来的人不再回头。
func _activate_id(id: String, from_activate: bool = false) -> void:
	if id.begins_with("room:"):
		_travel_to(int(id.substr(5)))
	elif id.begins_with("tgt:"):
		_pick_target(int(id.substr(4)))
	elif id.begins_with("atk:"):
		# 目标面板上的一行（M89）：走和点战场单位同一条路
		_pick_target(int(id.substr(4)))
	elif id == "cheat_res":
		_cheat_resources()
	elif id.begins_with("roster_deploy:"):
		_toggle_deploy(id.substr(14))
	elif id.begins_with("bld_up:"):
		var ub: String = id.substr(7)
		var uerr: String = campaign.upgrade_building(ub)
		if uerr.is_empty():
			campaign.save()
			_flash_msg("%s 升到 %d 级" % [str(_building_meta(ub)[1]),
				campaign.building_level(ub)])
		else:
			_flash_msg(uerr)
		queue_redraw()
	elif id.begins_with("guild_up:"):
		var us: String = id.substr(9)
		var err: String = campaign.upgrade_skill(_guild_hero, us)
		if err.is_empty():
			campaign.save()
			_flash_msg("%s 升到 %d 级" % [DdNames.skill_name(us),
				campaign.skill_level_of(_guild_hero, us) + 1])
		else:
			_flash_msg(err)
		queue_redraw()
	elif id.begins_with("bld_locked:"):
		var lb: String = id.substr(11)
		_flash_msg("「%s」还没开放 —— 再完成 %d 次任务" % [
			str(_building_meta(lb)[1]), _bld_need(lb)])
		queue_redraw()
	elif id == "party_back":
		_state = S_TOWN
		queue_redraw()
	elif id.begins_with("party_sel:"):
		_party_hero = id.substr(10)
		queue_redraw()
	elif id.begins_with("party_tk:"):
		var tk: String = id.substr(9)
		_sel_trinket = "" if _sel_trinket == tk else tk
		queue_redraw()
	elif id.begins_with("party_toggle:"):
		# 名单可能还没初始化（`--click=` 在第一次绘制之前就跑了）。
		# 不补这一句的话，点一下「上阵」会从一个空名单里 append，
		# 出征队伍直接变成一个人，而且会被存进档案。
		if _prep_party.is_empty():
			_prep_party = _party_restore(_prep_level)
		var ph: String = id.substr(13)
		if _prep_party.has(ph):
			if _prep_party.size() > 1:
				_prep_party.erase(ph)
		elif _prep_party.size() < Campaign.PARTY_MAX:
			_prep_party.append(ph)
		else:
			_flash_msg("出征最多 %d 人，先下阵一个" % Campaign.PARTY_MAX)
		_party_persist()
		queue_redraw()
	elif id == "cancel_pick":
		_pending = {}
		_retreat_arm = false
		queue_redraw()
	elif id.begins_with("info:"):
		var iu: int = int(id.substr(5))
		# 点同一个单位 = 关掉。否则玩家会去找「关闭」，而手指本来就在那个单位上。
		_info_uid = -1 if iu == _info_uid else iu
		_log_open = false      # 两个浮层同时开只会互相盖
		queue_redraw()
	else:
		if from_activate:
			# 两边都不认识：这是真的没有实现，不是要回头再问一遍。
			push_warning("未处理的按钮 id: " + id)
			return
		_activate(id)


func _hscroll_drag_to(x: float) -> void:
	var dx: float = x - _drag_x0
	# 8px 的死区：手指按下时几乎都会抖两像素，没有死区会把点击吃成拖动
	if not _drag_moved and absf(dx) < 8.0:
		return
	_drag_moved = true
	# 一旦判定成拖动，按下态就该消失：这张卡不是被点，是被滑动
	_press_id = ""
	var m: Dictionary = _hscroll_zone_meta.get(_drag_zone, {})
	if m.is_empty():
		return
	_hscroll[_drag_zone] = clampf(_drag_off0 - dx, 0.0, float(m["max"]))
	queue_redraw()


func _hscroll_snap(key: String) -> void:
	var m: Dictionary = _hscroll_zone_meta.get(key, {})
	if m.is_empty():
		return
	var step: float = maxf(1.0, float(m["step"]))
	var off: float = float(_hscroll.get(key, 0.0))
	_hscroll[key] = clampf(roundf(off / step) * step, 0.0, float(m["max"]))


## 画一条横向滚动带。`cb` 收到 (卡片矩形, 序号)，矩形已经算好偏移。
func _hscroll_zone(key: String, r: Rect2, count: int, cw: float, gap: float, cb: Callable) -> void:
	var step: float = cw + gap
	var content: float = float(count) * step - gap + 16.0
	var max_off: float = maxf(0.0, content - r.size.x)
	var off: float = clampf(float(_hscroll.get(key, 0.0)), 0.0, max_off)
	_hscroll[key] = off
	_hscroll_zone_meta[key] = {"rect": r, "step": step, "max": max_off, "count": count}

	_panel(r, DdTheme.PANEL_DEEP)
	_hit_clip_on = true
	_hit_clip = r
	for i in count:
		var cr := Rect2(r.position.x + 8.0 - off + float(i) * step,
			r.position.y + 8.0, cw, r.size.y - 16.0)
		if cr.end.x < r.position.x or cr.position.x > r.end.x:
			continue
		cb.call(cr, i)
	_hit_clip_on = false
	# 裁剪靠「背景色回涂」：Godot 的自绘 `_draw()` 没有 scissor API
	#（`canvas_item_set_clip_rect` 不存在，`clip_contents` 只管子节点）。
	# 滚动区左右是页边距，回涂不会伤到别的元素；最后把边框补回来。
	var lw: float = minf(off + 9.0, r.position.x)
	if lw > 0.0:
		draw_rect(Rect2(r.position.x - lw, r.position.y + 8.0, lw, r.size.y - 16.0), DdTheme.BG)
	var rw: float = minf(max_off - off + 9.0, size.x - r.end.x)
	if rw > 0.0:
		draw_rect(Rect2(r.end.x, r.position.y + 8.0, rw, r.size.y - 16.0), DdTheme.BG)
	draw_rect(r, DdTheme.PANEL_EDGE, false, 1.0)

	# 右侧渐隐 + 滑条：告诉玩家「后面还有」，否则会被当成只有 4 张
	if max_off > 1.0:
		var bar_w: float = maxf(24.0, r.size.x * (r.size.x / maxf(content, 1.0)))
		var t: float = off / max_off
		var bx: float = r.position.x + t * (r.size.x - bar_w)
		draw_rect(Rect2(bx, r.end.y - 5.0, bar_w, 3.0), DdTheme.DIM)


func _add_hit(r: Rect2, id: String) -> void:
	if _hit_clip_on:
		r = r.intersection(_hit_clip)
		if r.size.x < 2.0 or r.size.y < 2.0:
			return
	_buttons.append({"rect": r, "id": id, "label": "", "enabled": true})


## 触屏验收用的热区报告（M55）。
##
## 两类问题在桌面运行时**看不出来**：
##   1. 贴底：`y2` 落在最后 26 逻辑像素里 —— 手机的手势条/圆角会盖住，
##      点击会变成「返回桌面」而不是点按钮
##   2. 过小：高度 < 34 或宽度 < 44 —— 手指落点约 9mm，逻辑像素再乘 1.4 才到物理像素
##
## 同一屏只打一次（`size` 变了算另一屏），否则每帧刷屏。
func _dump_hit_report() -> void:
	# 前 2 秒不报：进屏第一帧往往还没建好单位/面板，那时打出来是空的
	# （第一次跑就是这么被自己骗了：战斗屏报 total=0）
	if _elapsed < 2.0:
		return
	var key: String = "%d@%.0fx%.0f#%d" % [_state, size.x, size.y, _buttons.size()]
	if key == _dump_key:
		return
	_dump_key = key
	var bottom_zone: float = 26.0
	var rows: Array = []
	var low: Array = []
	for b in _buttons:
		if not bool(b.get("enabled", true)):
			continue
		var r: Rect2 = b["rect"]
		var tag: String = str(b["id"])
		if r.position.y + r.size.y > size.y - bottom_zone:
			rows.append("    %-22s y=%3.0f..%3.0f  h=%2.0f" % [tag, r.position.y,
				r.position.y + r.size.y, r.size.y])
		if r.size.y < 34.0 or r.size.x < 44.0:
			low.append("    %-22s %3.0fx%-3.0f" % [tag, r.size.x, r.size.y])
	print("[hits] state=%d size=%.0fx%.0f total=%d options=%d" % [_state, size.x, size.y,
		_buttons.size(), _options.size()])
	print("[hits] 贴底 %d 个：%s" % [rows.size(), "" if rows.is_empty() else ""])
	for r in rows:
		print(r)
	print("[hits] 过小 %d 个：%s" % [low.size(), "" if low.is_empty() else ""])
	for r in low:
		print(r)
	# 重叠：两个可点区域相交 —— 轻则「点了没反应」，重则点到隔壁那个。
	# 这类问题在截图上未必看得出来（后画的会盖住先画的），必须按坐标算。
	var dup: Array = []
	var list: Array = []
	for b in _buttons:
		if bool(b.get("enabled", true)):
			list.append(b)
	for i in list.size():
		for j in range(i + 1, list.size()):
			var a: Rect2 = list[i]["rect"]
			var c: Rect2 = list[j]["rect"]
			var inter: Rect2 = a.intersection(c)
			if inter.size.x > 1.0 and inter.size.y > 1.0:
				dup.append("    %-18s x %-18s 重叠 %.0fx%.0f" % [str(list[i]["id"]),
					str(list[j]["id"]), inter.size.x, inter.size.y])
	print("[hits] 重叠 %d 对：%s" % [dup.size(), "" if dup.is_empty() else ""])
	for r in dup:
		print(r)


func _draw_floaters() -> void:
	# 飘字画在最顶层（`_draw()` 末尾），不分界面（M85）：
	# 战斗切到房间卡/结算卡的瞬间，还没飘完的数字会浮在卡片上继续飘。
	# 飘字只由战斗事件产生（`_consume_battle_event`），所以离开战斗屏就该收起来。
	if _state != S_BATTLE:
		return
	for f in _floaters:
		var col: Color = f.color
		col.a = clampf(f.life, 0.0, 1.0)
		# 字号（M83）：15/20 在 750 宽的战场上只有指甲盖大，
		# 叠在立绘上基本读不出数字。24/34 才对得上「伤害是这一屏最重要的信息」。
		_text(f.pos - Vector2(90, 0), str(f.text), 24 if not f.big else 34, col,
			HORIZONTAL_ALIGNMENT_CENTER, 180)


func _spawn_float(uid: int, text: String, col: Color, big: bool = false) -> void:
	# 掉血的飘字顺带触发受击抖动（M36）。用它当触发器而不是另开一个事件订阅：
	# 飘字本来就是「这一下打在这个人身上」的唯一统一出口，
	# 再拉一条并行的事件流，两条迟早对不上。
	if text.begins_with("-"):
		_hit_t[uid] = HIT_TIME
	var pos: Vector2 = _slot_center(uid)
	if pos == Vector2(-1, -1):
		return
	_floaters.append({"pos": pos + Vector2(randf_range(-12, 12), 0), "text": text,
		"color": col, "life": 1.1, "big": big})


func _slot_center(uid: int) -> Vector2:
	for s in _slots:
		if int(s.uid) == uid:
			var r: Rect2 = s.rect
			return Vector2(r.position.x + r.size.x * 0.5, r.position.y + r.size.y * 0.38)
	return Vector2(-1, -1)


# ============================================================
# 城镇屏（元层）
# ============================================================

## 城镇建筑（M22 入口 / M40 图形化 / M42 自适应）。
##
## 卡上放的是**这栋建筑里的人**（DD1 的 `<id>.character.png` 是执事、铁匠、
## 酒馆老板的半身像，不是建筑外观）。在窄卡里，半身像的辨识度远高于远景，
## 而且它替玩家回答了「进去会遇到谁」。
##
## 布局两套，按视口宽切换：
##   宽（>=1200）：8 列一行，竖排卡（图在上、字在下）
##   窄（<1200）： 4 列两行，横排卡（图在左、字在右）
## 1280 下 8 列每张 146 还够；1080 下只剩 119，名字加头像之后没有余量，必须换行。
##
## **返回建筑区底部的 y**，后面的区块靠它往下排。
## 上一版这些 y 是硬编码的（452/436/480/650），布局每改一次就要手算一遍
## （M40 一次、M41 一次），这次收口。
## 建筑入口（M58）：8 个建筑改成单行横向滚动，卡 190×178。
##
## 原来是 4 列 × 2 行网格 —— 横幅占掉 400 多像素，把出发区一路推到屏幕下半。
## 单行之后这块恒定 178，剩下的高度可以留给任务卡。
func _draw_town_buildings(top: float, h: float = 300.0) -> float:
	# 320 → 300：B 区改成左右两块之后要更多纵向空间，而 contain 之后
	# 图片区最高只用到 283，300 高的卡片已经够。
	# M63：h 改成参数 —— 底部安全区吃掉高度时由 `_draw_town` 统一压缩，
	# 立绘走 contain，压到 240 也不会出框。
	var r := Rect2(24.0, top, size.x - 48.0, h)
	_hscroll_zone("blds", r, BUILDINGS.size(), 190.0, 12.0,
		func(cr: Rect2, i: int) -> void:
			_draw_building_card((BUILDINGS[i] as Array), cr))
	return r.end.y


## 单个建筑卡：图在上、名字与副标题压底部条。
func _draw_building_card(b: Array, rb: Rect2) -> void:
	var bid: String = str(b[0])
	var hovered: bool = rb.has_point(_mouse)
	_tile(rb, _hit_state(rb, "bld:" + bid))
	var tex: Texture2D = _skin.building(bid)
	var tint: Color = Color(1, 1, 1, 1) if hovered else Color(0.82, 0.80, 0.78, 1)
	if tex == null:
		# 没图（--no-skin）：扁平字，位置和贴图版一致，方便对照
		_text(Vector2(rb.position.x, rb.position.y + rb.size.y * 0.5 - 8.0), str(b[1]),
			DdTheme.FONT_BD, DdTheme.TEXT, HORIZONTAL_ALIGNMENT_CENTER, rb.size.x)
		_text(Vector2(rb.position.x, rb.position.y + rb.size.y * 0.5 + 14.0), str(b[2]),
			DdTheme.FONT_TAG, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, rb.size.x)
	else:
		# 底部文字条：名字压在图上也读得清（M41 的教训）
		draw_rect(Rect2(rb.position.x, rb.end.y - 44.0, rb.size.x, 44.0),
			Color(0.055, 0.06, 0.065, 0.92))
		var ih: float = rb.size.y - 46.0
		# M58 修：原来只按**高度**贴合（`k = ih / 图高`），八张图有七张算出来
		# 比卡片还宽 —— smith 221×1.34=295、wagon 285×1.34=381，而卡片只有 190，
		# 于是立绘直接画到相邻卡片上，读起来像「这几个按钮互相盖住了」。
		# 改成 contain：宽高都不得越界，水平居中、底部贴着文字条对齐 ——
		# 底对齐而不是居中，是因为这几张都是「站在建筑里的人」，
		# 脚踩同一条线才不像浮空。
		var tw: float = float(maxi(1, tex.get_width()))
		var th: float = float(maxi(1, tex.get_height()))
		var k: float = minf((rb.size.x - 8.0) / tw, ih / th)
		var w: float = tw * k
		var h: float = th * k
		draw_texture_rect(tex, Rect2(rb.position.x + (rb.size.x - w) * 0.5,
			rb.position.y + 2.0 + (ih - h), w, h), false, tint)
		_text(Vector2(rb.position.x, rb.end.y - 26.0), str(b[1]), DdTheme.FONT_BD,
			DdTheme.TEXT, HORIZONTAL_ALIGNMENT_CENTER, rb.size.x)
		_text(Vector2(rb.position.x, rb.end.y - 8.0), str(b[2]), DdTheme.FONT_TAG,
			DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, rb.size.x)
	_add_hit(rb, "bld:" + bid)


## 一张难度卡（M58 竖屏）：右栏 470 宽 × 约 120 高。
##
## 它原来是 2×2 里的一张 339×210，五行字纵着排；搬到右栏之后变宽变矮，
## 所以改成「左边四行信息、右上角一个够格人数」的横向布局 ——
## 卡变矮之后纵排五行会挤成一条，横排反而更清楚。
## 按宽度切成若干行（M200），只做测量，不管绘制。
##
## 中文没有词边界，所以逐字加、超宽就断。抽出来是因为折行的需求散在几处
## （任务卡、飘字提示），各写一份必然有一处忘了按字宽量。
func _wrap_lines(s: String, fs: int, width: float) -> Array:
	var out: Array = []
	var line: String = ""
	for i in s.length():
		var ch: String = s.substr(i, 1)
		var test: String = line + ch
		if _font.get_string_size(test, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x > width \
				and not line.is_empty():
			out.append(line)
			line = ch
		else:
			line = test
	if not line.is_empty():
		out.append(line)
	return out if not out.is_empty() else [s]


## 按宽度折行画一段文字（M198），返回下一行的基线 y。
##
## `_text` 的 width 只影响对齐，**不换行**（`draw_string` 本身不会自动折）。
## 任务卡的说明是长句，窄卡上不折就是原来那种「尾巴被切掉」。
func _text_wrap(pos: Vector2, s: String, fs: int, col: Color,
		width: float, max_lines: int = 3) -> float:
	var lh: float = float(fs) + 6.0
	var lines: Array = _wrap_lines(s, fs, width)
	var n: int = mini(lines.size(), max_lines)
	for i in n:
		var line: String = str(lines[i])
		# 放不下的部分用省略号收在最后一行
		if i == n - 1 and lines.size() > max_lines:
			line = DdTheme.ellipsis(line + "……", _font, width, fs)
		_text(Vector2(pos.x, pos.y + float(i) * lh), line, fs, col,
			HORIZONTAL_ALIGNMENT_LEFT, width)
	return pos.y + float(n) * lh


## 任务卡（M198 改竖卡）。
##
## 原来是四张横排、每张 ~166 宽：标题和说明都放不下，
## 「清光全图战斗，支路」直接压到下一张卡上。改成窄竖卡 + 横向滚动区，
## 一张卡把「做什么 / 会碰到谁 / 够不够格 / 打过没有」四件事说完。
func _draw_board_card(row: Array, r: Rect2, alive: int) -> void:
	_panel(r)
	_hit_overlay(r, "prep:%s:%d:%s" % [str(row[0]), int(row[1]), str(row[4])])
	draw_rect(Rect2(r.position, Vector2(r.size.x, 3.0)), DdTheme.PARTY)
	# 难度徽章（M59）：1 枚 / 2 枚 / 3 枚铆钉，一眼看出这一档有多硬。
	var lv: int = int(row[1])
	var rk: String = "rank_apprentice"
	if lv >= 5:
		rk = "rank_champion"
	elif lv >= 3:
		rk = "rank_veteran"
	var tx2: float = r.position.x + 18.0
	if _ico(rk) != null:
		_draw_ico(rk, Vector2(r.position.x + 14.0, r.position.y + 8.0), 34.0,
			Color(1, 1, 1, 1) if alive > 0 else Color(0.55, 0.55, 0.55, 0.8))
		tx2 = r.position.x + 60.0
	# 标题要让出右上角「够格 N 人」那 150px（M153）：字号放大后
	# 「荒野 · 短途 · 1 级」正好压到「够格 4 人」上。
	_text(Vector2(tx2, r.position.y + 32.0), str(row[2]),
		DdTheme.FONT_BD, DdTheme.TEXT if alive > 0 else DdTheme.DIM,
		HORIZONTAL_ALIGNMENT_LEFT, r.size.x - (tx2 - r.position.x) - 152.0)
	_text(Vector2(tx2, r.position.y + 56.0), str(row[3]),
		DdTheme.FONT_SM, DdTheme.DIM)
	# 情报（M21）：这一档会遇到什么。玩家点进去之前唯一能看的信息。
	var info: Dictionary = db.encounter_outline(_dungeon, int(row[1]))
	var foes: String = _foe_brief(info, str(row[4]))
	if not foes.is_empty():
		_text(Vector2(tx2, r.position.y + 82.0), foes,
			DdTheme.FONT_SM, DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_LEFT, r.size.x - (tx2 - r.position.x) - 20.0)
	# 「够格几人」（M25）：它回答的是「我能不能打这一档」，不只是「有几个活人」。
	var fit: int = _fit_count(int(row[1]))
	var fit_col: Color = DdTheme.OK if fit >= Campaign.PARTY_MAX else DdTheme.WARN
	if fit <= 0:
		fit_col = DdTheme.CRIT
	_text(Vector2(r.position.x + r.size.x - 138.0, r.position.y + 32.0),
		"够格 %d 人" % fit, DdTheme.FONT_MD, fit_col,
		HORIZONTAL_ALIGNMENT_RIGHT, 120.0)
	if alive > 0 and fit <= 0:
		# 一个都不够格只有一种可能：**全员等级过高**（低等级永远能进）。
		# 空状态纹章（M61）：红字只说「不行」，纹章说「为什么不行」——
		# 一把锁住的盾，比七个字更早被看到。
		_draw_ico("emblem_blocked", Vector2(r.position.x + r.size.x - 64.0,
			r.position.y + 50.0), 50.0, Color(1, 1, 1, 0.94))
		_text(Vector2(r.position.x + 18.0, r.position.y + 104.0),
			"全员等级过高，这一档带不动", DdTheme.FONT_TAG, DdTheme.CRIT,
			HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 90.0)
	elif alive > 0 and fit < Campaign.PARTY_MAX:
		_text(Vector2(r.position.x + 18.0, r.position.y + 104.0),
			"还缺 %d 人才够满编" % (Campaign.PARTY_MAX - fit), DdTheme.FONT_TAG, DdTheme.WARN)
	if alive > 0 and fit > 0:
		# 点难度卡不直接出发，而是进「出发准备」——补给是出发前唯一能调的东西。
		_add_hit(r, "prep:%s:%d:%s" % [str(row[0]), int(row[1]), str(row[4])])


## 区域横幅（M42）。出发区背后铺一条该区域的图，让「要去哪」先有一个画面。
##
## 用的是 DD1 的 loading 图（1920×1080）裁出的横带，四张分别是
## 荒野 / 墓穴 / 巢穴 / 海湾，都是「入口」构图。
##
## 没有图就什么都不画——占位框比没有更难看。
func _draw_region_band(r: Rect2, did: String) -> void:
	var tex: Texture2D = _skin.region(did)
	if tex == null:
		return
	# cover：按短边放大到盖满，再居中裁切
	var tw: float = float(maxi(1, tex.get_width()))
	var th: float = float(maxi(1, tex.get_height()))
	var k: float = maxf(r.size.x / tw, r.size.y / th)
	var src := Rect2((tw - r.size.x / k) * 0.5, (th - r.size.y / k) * 0.5,
		r.size.x / k, r.size.y / k)
	draw_texture_rect_region(tex, r, src)
	# 压暗：上面要放标签和四个区域按钮，不压暗读不清
	draw_rect(r, Color(0.04, 0.045, 0.05, 0.52))
	draw_rect(r, Color(DdTheme.PANEL_EDGE.r, DdTheme.PANEL_EDGE.g, DdTheme.PANEL_EDGE.b, 0.5),
		false, 1.0)


# ============================================================
# 主菜单与存档槽（M47）
# ============================================================

## 读设置。文件不存在 / 读不出来就用默认值，不报错——
## 设置丢了的后果是「音量回到默认」，不是「游戏打不开」。
func _load_settings() -> void:
	if not FileAccess.file_exists(SETTINGS_PATH):
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(SETTINGS_PATH))
	if not (parsed is Dictionary):
		return
	_volume = clampi(int((parsed as Dictionary).get("volume", _volume)), 0, 100)


func _save_settings() -> void:
	var f := FileAccess.open(SETTINGS_PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({"version": 1, "volume": _volume}, "  "))
	f.close()


## 音量值 → dB。
##
## 不用「线性百分比直通 dB」：人对响度的感知是对数的，线性映射会让
## 0–70 这一段几乎没有变化、70–100 突然变响。
## 0 单独给 -80（等于静音），而不是 -36——-36dB 还能听见一点，那不叫关掉。
func _volume_db(v: int) -> float:
	if v <= 0:
		return -80.0
	return lerpf(-34.0, 0.0, float(v) / 100.0)


func _apply_volume() -> void:
	if _sfx != null:
		_sfx.volume_db = _volume_db(_volume)
	if _music != null:
		# 音乐比音效低 5dB：BGM 是背景，音效是要听见的反馈。
		# 两者同音量的话，战斗里听不清"打中了没有"。
		_music.base_db = _volume_db(_volume) - 5.0


func _slot_path(idx: int) -> String:
	return "user://save_%d.json" % (idx + 1)


## 读一个槽的摘要，给主菜单显示。
##
## 直接解析 JSON 而不是先 `setup` 再读：主菜单要同时显示三个档的情况，
## 而 `Campaign` 一次只能装一个。全文解析在这里不心疼——文件就几十 KB，
## 而且是玩家点开游戏才发生一次的事。
func _slot_summary(idx: int) -> Dictionary:
	var p: String = _slot_path(idx)
	if not FileAccess.file_exists(p):
		return {"empty": true}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(p))
	if not (parsed is Dictionary):
		# 文件在但读不出来：显示成「损坏」而不是「空」。
		# 显示成空会让玩家以为档没了，然后点进去被覆盖——那才是真的没了。
		return {"empty": false, "broken": true}
	var d: Dictionary = parsed
	var roster: Dictionary = d.get("roster", {})
	var alive: int = 0
	for k in roster.keys():
		if bool((roster[k] as Dictionary).get("alive", false)):
			alive += 1
	var bosses: int = 0
	for k in (d.get("boss_cleared", {}) as Dictionary).keys():
		if bool(d["boss_cleared"][k]):
			bosses += 1
	return {
		"empty": false, "broken": false,
		"week": int(d.get("week", 1)),
		"gold": int(d.get("gold", 0)),
		"roster": roster.size(),
		"alive": alive,
		"expeditions": int(d.get("expeditions", 0)),
		"bosses": bosses,
	}


## 设置屏（M47）。目前只有主音量——这是唯一一个「不改就真的影响体验」的项。
##
## 没做分辨率和全屏：项目把 viewport 定死 1280×760，改窗口只是缩放内容，
## 做出来会是三个不起作用的按钮，比没有更糟。
func _draw_settings() -> void:
	var bands2: int = 16
	for bi in bands2:
		var t: float = float(bi) / float(bands2)
		draw_rect(Rect2(0.0, size.y * t, size.x, size.y / float(bands2) + 1.0),
			Color(0.040, 0.042, 0.048).lerp(Color(0.014, 0.015, 0.018), t))

	_text(Vector2(0, 130), "设置", DdTheme.FONT_H1, DdTheme.TEXT,
		HORIZONTAL_ALIGNMENT_CENTER, size.x)

	var cx: float = size.x * 0.5
	var card := Rect2(cx - 260, 190, 520, 150)
	_panel(card, DdTheme.PANEL_DEEP)

	_text(Vector2(card.position.x + 28, card.position.y + 40), "主音量", DdTheme.FONT_BD, DdTheme.TEXT)
	_text(Vector2(card.position.x + 28, card.position.y + 66),
		"作用于全部音效；0 = 静音", DdTheme.FONT_SM, DdTheme.FAINT)

	# 数值：右端对齐（x 是文本框左边界，要减宽度）
	_text(Vector2(card.position.x + card.size.x - 148.0, card.position.y + 40),
		"%d" % _volume, DdTheme.FONT_BD, DdTheme.LIGHT, HORIZONTAL_ALIGNMENT_RIGHT, 40)

	# 音量条：10 格，点格子直接设到那一档
	var bx: float = card.position.x + 28.0
	var by: float = card.position.y + 96.0
	var seg_w: float = 40.0
	var seg_gap: float = 4.0
	for i in 10:
		var lvl: int = (i + 1) * 10
		var sr := Rect2(bx + float(i) * (seg_w + seg_gap), by, seg_w, 22)
		var on: bool = _volume >= lvl
		draw_rect(sr, Color(0.40, 0.33, 0.16) if on else Color(0.14, 0.14, 0.15))
		draw_rect(sr, DdTheme.PANEL_EDGE, false, 1.0)
		_hit_overlay(sr, "vol:%d" % lvl, false)
		_add_hit(sr, "vol:%d" % lvl)

	# 两个快捷按钮：静音 / 默认
	_add_button(Rect2(cx - 260, 370, 160, 36), "vol:0", "静音")
	_add_button(Rect2(cx - 80, 370, 160, 36), "vol:70", "恢复默认")
	_add_button(Rect2(cx + 100, 370, 160, 36), "settings_back", "返回")

	_text(Vector2(0, size.y - 40), "设置存在 settings.json，和存档分开", DdTheme.FONT_SM,
		DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, size.x)


## 主菜单背景（M48）：DD1 的 `title_bg`（红色光晕）+ `title_house`（庄园剪影）。
##
## 两张图是分开的，不是一张合成图：底图是纯气氛的红光，庄园是透明底剪影。
## 分开存的好处是换风格时只换其中一张——比如把庄园换成别的建筑。
##
## 庄园在提取时裁掉了底部实心黑：原图下半是 alpha=255 的纯黑，
## 叠在底图上会露出一条水平硬边，像贴了一张纸在画面上。
func _draw_menu_bg() -> bool:
	if not _skin.enabled:
		return false
	var bg: Texture2D = _skin.texture("menu", "bg")
	if bg == null:
		return false
	var bscale: float = maxf(size.x / bg.get_width(), size.y / bg.get_height())
	var bw: float = bg.get_width() * bscale
	var bh: float = bg.get_height() * bscale
	draw_texture_rect(bg, Rect2((size.x - bw) * 0.5, (size.y - bh) * 0.5, bw, bh), false)

	var house: Texture2D = _skin.texture("menu", "house")
	if house != null:
		# 庄园高度按视口高换算：760 基准下 470px，1080 宽（高度不变）时仍是 470。
		var hh: float = 470.0 * (size.y / 760.0)
		var hk: float = hh / house.get_height()
		var hw: float = house.get_width() * hk
		draw_texture_rect(house, Rect2((size.x - hw) * 0.5, 18.0 * (size.y / 760.0), hw, hh), false)

	# 顶部压暗：标题和副标题正好落在庄园的塔楼上，不压掉会读不清。
	# 12 段是因为这一段跨 220px，段数少了能看出台阶。
	# 指数曲线而不是线性：线性压暗到标题那一行只剩 0.3，庄园的塔楼还是穿字。
	# 前 60px 直接压到接近全黑，后面快速衰减——读者看到的是「标题浮在暗处」，
	# 而不是「标题和塔楼叠在一起」。
	# 分两段：0–160 直接压到接近全黑（标题和副标题都在这段里），
	# 160–240 再渐隐回背景。只用一个连续曲线的话，压到副标题那一行就衰减没了，
	# 结果字是清楚的、背后有碎石纹理穿过来。
	for i in 20:
		var y: float = 240.0 * float(i) / 20.0
		var a: float = 0.86 if y < 160.0 else 0.86 * (1.0 - (y - 160.0) / 80.0)
		draw_rect(Rect2(0.0, y, size.x, 240.0 / 20.0 + 1.0),
			Color(0.02, 0.021, 0.025, a))
	# 底部压暗：三个槽和按钮落在红光最亮的地方，不压会读不清
	for i in 10:
		var t2: float = float(i) / 10.0
		draw_rect(Rect2(0.0, size.y * 0.62 + (size.y * 0.38) * t2, size.x, size.y * 0.038 + 1.0),
			Color(0.02, 0.021, 0.025, 0.55 * t2))
	return true


## 音效试听面板（M50）。盖在主菜单上，列出全部槽位、高亮正在播的那个。
##
## 每行右侧标「来自哪」：`.ogg` 是原版、`.wav` 是合成占位。
## 这一栏不是装饰——调音效时最常问的就是「这个槽到底有没有换上真音」。
func _draw_sfx_demo() -> void:
	draw_rect(Rect2(0.0, 0.0, size.x, size.y), Color(0.022, 0.023, 0.027))
	var cx: float = size.x * 0.5
	_text(Vector2(0, 80), "音效试听", DdTheme.FONT_DISPLAY, DdTheme.LIGHT,
		HORIZONTAL_ALIGNMENT_CENTER, size.x)
	_text(Vector2(0, 112), "每 1.6 秒一个，循环播放 —— 左：界面与武器音　右：敌人语音与攻击声",
		DdTheme.FONT_MD, DdTheme.DIM, HORIZONTAL_ALIGNMENT_CENTER, size.x)

	var cur: String = str(SFX_DEMO_LIST[_sfx_demo_i])
	var rows: int = int(ceil(float(SFX_DEMO_LIST.size()) / 2.0))
	var col_w: float = 300.0
	for i in SFX_DEMO_LIST.size():
		var id: String = str(SFX_DEMO_LIST[i])
		var on: bool = id == cur
		var col: int = 0 if i < rows else 1
		var row: int = i if i < rows else i - rows
		var x: float = cx - col_w - 12.0 if col == 0 else cx + 12.0
		var y: float = 148.0 + float(row) * 26.0
		if on:
			draw_rect(Rect2(x - 8.0, y - 17.0, col_w + 16.0, 24.0),
				Color(0.35, 0.28, 0.12, 0.55))
		# 槽位名去掉 `voice/` 前缀再显示：列表里 12 行都带它就没信息量了
		var label: String = id.substr(6) if id.begins_with("voice/") else id
		_text(Vector2(x, y), label, DdTheme.FONT_BD, DdTheme.CRIT if on else DdTheme.DIM)
		var src: String = _demo_source(id)
		_text(Vector2(x + 168.0, y), src, DdTheme.FONT_TAG,
			DdTheme.OK if src == ".ogg" else DdTheme.FAINT)
		if on:
			_text(Vector2(x + 208.0, y), "← 播", DdTheme.FONT_TAG, DdTheme.CRIT)

	_text(Vector2(0, size.y - 34.0),
		"ogg = 原版　wav = 合成占位　缺 = 没素材（静音是正常状态，不是错误）",
		DdTheme.FONT_SM, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, size.x)


## 试听清单里某一项实际来自哪种文件（`.ogg` / `.wav` / 缺）。
## 变体槽位要看 `_1` 那一份，列表里显示的是「这个槽位有没有东西」。
func _demo_source(id: String) -> String:
	var base: String = id
	if id.contains("/"):
		var parts: PackedStringArray = id.split("/")
		base = "%s/%s_1" % [parts[0], parts[1]]
	for ext in [".ogg", ".wav"]:
		if ResourceLoader.exists("res://assets/audio/%s%s" % [base, ext]):
			return ext
	return "缺"


## 试听播放：变体槽位（`voice/skel_hurt`）要走 `play_variant`，
## 直接 `play` 会去找 `voice/skel_hurt.ogg`（不存在）然后静音。
func _demo_play(id: String) -> void:
	if _sfx == null:
		return
	if id.contains("/"):
		# 攻击声最多 3 个变体、语音 2 个，按前缀选，别拿错的份数去探
		var n: int = EnemyVoice.ATTACK_TAKES if id.begins_with("atk/") else EnemyVoice.TAKES
		_sfx.play_variant(id, n)
	else:
		_sfx.play(id)


## 当前界面该放哪首（M49）。
##
## 只有五首：竖屏菜单、城镇、战斗、荒野探索、其他区域探索。
## 曲目和界面是**多对一**的——经营相关的六屏共用城镇曲，否则每次点进商店都换歌。
func _music_for_state() -> String:
	match _state:
		S_BATTLE, S_BATTLE_END:
			return "combat"
		S_MAP:
			# 荒野有自己的曲子；其余三个区域共用「深层探索」。
			# 原版每个区域都有专属曲，但本作只有四张图，多导三首的收益不如先把循环跑通。
			return "weald" if (exp != null and str(exp.dungeon) == "weald") else "depths"
		S_MENU, S_SETTINGS, S_VICTORY:
			return "menu"
		_:
			# 城镇 + 所有建筑 + 准备 + 结算
			return "town"


func _draw_menu() -> void:
	# 试听模式独占整屏（M50）。
	#
	# 第一版是叠在菜单上、背景 alpha 0.86，结果存档卡和按钮全透上来，
	# 和列表文字糊在一起——半透明在这种「两层都有字」的场景里没有出路。
	if _sfx_demo:
		_draw_sfx_demo()
		return
	# 没有图就退回纯渐变：`--no-skin` 和「图没导入」都走这条路。
	# 退路必须存在——主菜单是第一屏，它挂了整局都进不去。
	if not _draw_menu_bg():
		var bands: int = 16
		var top_col := Color(0.040, 0.042, 0.048)
		var bot_col := Color(0.014, 0.015, 0.018)
		for bi in bands:
			var t: float = float(bi) / float(bands)
			draw_rect(Rect2(0.0, size.y * t, size.x, size.y / float(bands) + 1.0),
				top_col.lerp(bot_col, t))

	_text(Vector2(0, 128), "空 腔", DdTheme.FONT_DISPLAY, DdTheme.LIGHT,
		HORIZONTAL_ALIGNMENT_CENTER, size.x)
	_text(Vector2(0, 172), "带四个人下去，把能带的都带回来", DdTheme.FONT_MD, DdTheme.DIM,
		HORIZONTAL_ALIGNMENT_CENTER, size.x)

	var cw: float = 460.0
	var ch: float = 96.0
	var gap: float = 20.0
	var x0: float = (size.x - cw) * 0.5
	var y0: float = 224.0

	for i in SAVE_SLOTS:
		var r := Rect2(x0, y0 + float(i) * (ch + gap), cw, ch)
		var sum: Dictionary = _slot_summary(i)
		var confirming: bool = _del_slot == i
		# 确认删除时整张卡不接受点击（按钮接管），所以不显示悬停/按下
		_tile(r, TILE_IDLE if confirming else _hit_state(r, "slot:%d" % i))

		_text(Vector2(r.position.x + 24.0, r.position.y + 36.0), "存档 %d" % (i + 1),
			DdTheme.FONT_H1, DdTheme.TEXT)

		if confirming:
			# 二次确认（M48）。删除是不可逆的，而这一类操作最容易被误触——
			# 卡片本身就是「读档」的点击区，删除按钮就贴在上面。
			# 高度 28 而不是 18：按钮里的文字是垂直居中绘制的，
			# 18 高会把字压到边框上（第一版就是这样，看起来像裁切）。
			_text(Vector2(r.position.x + 24.0, r.position.y + 58.0),
				"删除后不可恢复 —— 这一档的全部进度会消失", DdTheme.FONT_MD, DdTheme.WARN)
			_add_button(Rect2(r.position.x + 24.0, r.position.y + 66.0, 150, 28),
				"delok:%d" % i, "确定删除", true, true)
			_add_button(Rect2(r.position.x + 186.0, r.position.y + 66.0, 120, 28),
				"delno:%d" % i, "取消")
			continue

		if bool(sum.get("empty", true)):
			_text(Vector2(r.position.x + 24.0, r.position.y + 66.0), "空 —— 点这里开始新的一档",
				DdTheme.FONT_MD, DdTheme.DIM)
		elif bool(sum.get("broken", false)):
			_text(Vector2(r.position.x + 24.0, r.position.y + 66.0), "这个存档读不出来（文件损坏）",
				DdTheme.FONT_MD, DdTheme.WARN)
		else:
			var line: String = "第 %d 周 · %d 趟 · 名册 %d 人（活 %d）" % [
				int(sum["week"]), int(sum["expeditions"]), int(sum["roster"]), int(sum["alive"])]
			_text(Vector2(r.position.x + 24.0, r.position.y + 64.0), line, DdTheme.FONT_MD, DdTheme.DIM)
			var tail: String = "金币 %d" % int(sum["gold"])
			if int(sum["bosses"]) > 0:
				tail += " · 首领 %d / 4" % int(sum["bosses"])
			_text(Vector2(r.position.x + 24.0, r.position.y + 84.0), tail, DdTheme.FONT_MD,
				DdTheme.LIGHT if int(sum["bosses"]) > 0 else DdTheme.FAINT)
			# 删除按钮要先加进 `_buttons`：`_on_click` 是按加入顺序匹配的，
			# 后加的会被整张卡的 hit 抢走（卡片就是「点这里读档」）。
			_add_button(Rect2(r.position.x + r.size.x - 84.0, r.position.y + 16.0, 64, 22),
				"del:%d" % i, "删除")

		_add_hit(r, "slot:%d" % i)

	var by2: float = y0 + float(SAVE_SLOTS) * (ch + gap) + 16.0
	_add_button(Rect2((size.x - 420.0) * 0.5, by2, 200, 38), "menu_settings", "设置")
	_add_button(Rect2((size.x - 420.0) * 0.5 + 220.0, by2, 200, 38), "menu_quit", "退出游戏")

	_text(Vector2(0, size.y - 26.0),
		"三个槽各自独立；进入后每次回城都会自动存档", DdTheme.FONT_SM, DdTheme.FAINT,
		HORIZONTAL_ALIGNMENT_CENTER, size.x)


## 城镇整屏背景（M59 交付）。cover 铺满，不变形。
##
## 素材原图是三段重复的——出图方把竖屏理解成了三联画。取中间那段
## 上下模糊延展成 750×1334，压到平均亮度 17%，退成氛围而不是画面。
func _draw_town_bg() -> void:
	var tex: Texture2D = _skin.texture("skin", "bg_town")
	if tex == null:
		return
	var k: float = maxf(size.x / tex.get_width(), size.y / tex.get_height())
	var w: float = tex.get_width() * k
	var h: float = tex.get_height() * k
	draw_texture_rect(tex, Rect2((size.x - w) * 0.5, (size.y - h) * 0.5, w, h), false)


func _draw_town() -> void:
	# 场景（三层底图 + 建筑）先画，后面的 header / 资源条 / 名册条 / dock 都压在它上面
	_draw_town_scene()
	# 作弊按钮（M104）：开发期调资源用。
	# 放在 dock 上方的空带里（城镇那一块本来就是背景），不压任何正式元素。
	# 正式发行前要删掉——这里没有开关，因为它就是给自己用的。
	# 位置（M104 第三版）：dock 右侧那条空带。
	# 前两版分别压住了「商队」标签和名册条右端的「全部 ›」。
	# dock 宽 264 居中，右边从 507 到 750 一直是空的。
	_add_button(Rect2(size.x - 190.0, size.y - 74.0, 172.0, 44.0),
		"cheat_res", "＋10000 资源")
	# 「继续远征」按钮已删除（M137）。
	#
	# 它原来靠 `campaign.expedition_run` 非空来判断「有没打完的一趟」，
	# 而 `settle()` **根本没清过这个字段** —— 打完最后一间房、结算发完奖励，
	# 快照里还留着「结束前那一帧的地图」。回城存档把它写进档，
	# 按钮就一直亮着：点一次回到最后一间房，再打一次、再结算一次，**刷奖励**。
	#
	# 切后台续玩这件事不需要按钮：M117 已经在启动时自动恢复（读同一个快照），
	# 玩家按 Home 回来会直接落在原来的屏幕上。
	# 副标题把「每周恢复多少」写出来：不写的话「休整一周」看起来只是浪费时间，
	# 玩家不会知道那 50 金买到了什么。
	var wk_relief: int = int((campaign.cfg.get("town_cycle", {}) as Dictionary).get(
		"weekly_stress_relief", 0))
	# 任务数写进副标题（M123）：建筑是按「完成任务数」开放的，
	# 但玩家看不到那个数字的话，只会觉得「这座城怎么越来越空」。
	# 差多少任务才开下一座（M123）：不写的话玩家只会觉得「城怎么这么空」。
	var nx_bid: String = ""
	var nx_need: int = 999
	for b in ["abbey", "tavern", "smith", "guild", "sanitarium"]:
		var need: int = int(BLD_UNLOCK.get(b, 0)) - campaign.quests_done
		if need > 0 and need < nx_need:
			nx_need = need
			nx_bid = b
	if not nx_bid.is_empty():
		_text(Vector2(28.0, size.y - NAV_H - DOCK_H - 26.0),
			"再完成 %d 次任务：「%s」开放" % [nx_need,
				str(_building_meta(nx_bid)[1]) if not _building_meta(nx_bid).is_empty() else nx_bid],
			DdTheme.FONT_MD, DdTheme.DIM)
	_header("城镇 · 第 %d 周" % campaign.week,
		"远征 %d 趟 · 完成任务 %d 次 · 每周恢复 %d 压力" % [
			campaign.expeditions, campaign.quests_done, wk_relief])

	# —— 资源 ——
	# 纵向重排（M31）：视口是 1280×760，而内容原来只排到 586，
	# 底下空了 174px——看起来像「这屏还没画完」。现在按 760 重新分配。
	var y: float = 76.0
	# 资源条（M59）：图标 + 数字，比「半身像 12」省一半横向空间。
	# 取不到图标时逐项退回文字，所以 --no-skin 下样子和以前一致。
	var cx: float = 28.0
	cx = _draw_ico("icon_gold", Vector2(cx, y - 17.0), 22.0) + 6.0
	var gold_s: String = str(campaign.gold)
	_text(Vector2(cx, y), gold_s, DdTheme.FONT_BD, DdTheme.CRIT)
	cx += _font.get_string_size(gold_s, HORIZONTAL_ALIGNMENT_LEFT, -1, DdTheme.FONT_BD).x + 20.0
	for k in campaign.heirlooms.keys():
		var kid: String = str(k)
		var n_s: String = str(int(campaign.heirlooms[k]))
		if _ico("icon_" + kid) != null:
			cx = _draw_ico("icon_" + kid, Vector2(cx, y - 17.0), 22.0) + 7.0
			_text(Vector2(cx, y), n_s, DdTheme.FONT_MD, DdTheme.DIM)
			cx += _font.get_string_size(n_s, HORIZONTAL_ALIGNMENT_LEFT, -1, DdTheme.FONT_MD).x + 24.0
		else:
			_text(Vector2(cx, y), "%s %s" % [DdNames.heirloom_name(kid), n_s],
				DdTheme.FONT_MD, DdTheme.DIM)
			cx += 110.0
	# 右侧原来是「最深推进」单独一项。加首领进度之后两项挤在一行，
	# 所以合成一句——单独占一行会在 1080 下压到名册卡上。
	var right_bits: Array = []
	var bc: int = campaign.bosses_cleared()
	if bc > 0:
		right_bits.append("首领讨伐 %d / 4" % bc)
	if campaign.best_steps > 0:
		right_bits.append("最深推进 %d 间房" % campaign.best_steps)
	if not right_bits.is_empty():
		# 右对齐时 `pos.x` 是**文本框左边界**，不是右边界——
		# 必须减去宽度，否则整段文字会画到屏幕外（这个坑在下面「侦察 %」那行一直存在）。
		var rb_w: float = 380.0
		_text(Vector2(size.x - 28.0 - rb_w, y), " · ".join(right_bits), DdTheme.FONT_MD,
			DdTheme.LIGHT if bc > 0 else DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_RIGHT, rb_w)

	# —— 场景：三层底图 + 8 座建筑 + 名牌（M64）——
	var ids: Array = campaign.hero_ids()
	var alive_n: int = campaign.alive_ids().size()
	_draw_town_labels()

	# —— 名册条：缩小居中，底部两角让给铁匠铺和马车 ——
	_draw_roster_strip(ids, alive_n)

	# 底部 dock 由 `_draw()` 统一画（M163），这里不再重复

	# 抽屉画在最后：它要盖住整屏（含上面那条「休整一周」）
	_draw_hero_sheet()


# ============================================================
# 城镇场景（M64）：三层底图 + 8 座建筑 + 名牌 + 名册条 + dock
# ============================================================

## 读布局编辑器导出的 JSON，覆盖 `_town_slots`（M64）。
##
## JSON 合同（和 `docs/town_layout_editor.html` 导出的一致）：
## `{canvas:{w,h}, items:[{id,x,y,h,flipH,front}]}`，其中 `y` 是**底边**、
## `h` 是显示高度，坐标都是 750×1334 的画布坐标（含顶部安全区）。
##
## 读失败不崩、不静默：打一条 warning 然后继续用内置坐标 ——
## 场景摆错只是不好看，但为此让游戏起不来是另一回事。
func _load_town_layout(path: String) -> void:
	var p: String = path.strip_edges()
	if p.is_empty():
		return
	# 命令行里写 `docs/town_layout.json` 这种相对路径就行，按项目根解析
	if not p.begins_with("res://") and not p.begins_with("user://") and not p.is_absolute_path():
		p = "res://" + p
	if not FileAccess.file_exists(p):
		push_warning("[layout] 读不到 %s —— 继续用内置坐标" % p)
		return
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(p))
	if typeof(data) != TYPE_DICTIONARY:
		push_warning("[layout] %s 不是合法 JSON 对象" % p)
		return
	var items: Array = (data as Dictionary).get("items", [])
	var out: Array = []
	for raw in items:
		if typeof(raw) != TYPE_DICTIONARY:
			continue
		var d: Dictionary = raw
		var bid: String = str(d.get("id", ""))
		if bid.is_empty():
			continue
		out.append([
			bid,
			int(d.get("x", 0)),
			int(d.get("y", 0)),
			maxi(1, int(d.get("h", 100))),
			bool(d.get("flipH", false)),
			bool(d.get("front", false)),
		])
	if out.is_empty():
		push_warning("[layout] %s 里没有可用条目 —— 继续用内置坐标" % p)
		return
	var canvas: Dictionary = (data as Dictionary).get("canvas", {}) as Dictionary
	if int(canvas.get("h", 1334)) != 1334:
		# 坐标是绝对像素，画布高度变了就整体错位，必须说清楚
		push_warning("[layout] 画布高 %s ≠ 1334，坐标会偏" % str(canvas.get("h", "?")))
	_town_slots = out
	_town_tex_cache.clear()
	print("[layout] 已加载 %s（%d 座）" % [p, out.size()])


var _town_tex_cache: Dictionary = {}


## 图层贴图（带缓存）。`flip` 会把图水平翻一次再存，避免每帧翻。
func _town_tex(kind: String, tex_name: String, flip: bool = false) -> Texture2D:
	var key: String = "%s/%s%s" % [kind, tex_name, "|f" if flip else ""]
	if _town_tex_cache.has(key):
		return _town_tex_cache[key]
	var tex: Texture2D = _skin.texture(kind, tex_name)
	if tex != null and flip:
		var img: Image = tex.get_image()
		if img != null:
			img.flip_x()
			tex = ImageTexture.create_from_image(img)
	_town_tex_cache[key] = tex
	return tex


## 建筑在屏幕上的矩形。`y` 存的是**画布坐标**（底边），
## 所以减的是实际 `_safe_top`，和底图用同一个平移量，两者才不会错开。
func _town_bld_rect(slot: Array) -> Rect2:
	var tex: Texture2D = _town_tex("town", "bld_" + str(slot[0]))
	if tex == null:
		return Rect2()
	var h: float = float(slot[3])
	var w: float = h * float(tex.get_width()) / float(maxi(1, tex.get_height()))
	return Rect2(float(slot[1]), float(slot[2]) - _safe_top - h, w, h)


## 交互态 → 提亮系数。可点的东西要「活着」，但常态不能太跳。
func _town_tint(st: int) -> Color:
	match st:
		TILE_HOVER:
			return Color(1.18, 1.14, 1.04, 1.0)
		TILE_PRESS:
			return Color(0.90, 0.88, 0.84, 1.0)
	return Color(1.0, 1.0, 1.0, 1.0)


## 场景画布在屏幕上的矩形（M64 修正）。
##
## **底图必须和建筑共用同一个 1334 坐标系。**
##
## 原来写的是 `Rect2(0,0,size.x,size.y)`：那会把 1334 高的画布压进 1202 的视口
##（上下各扣了安全区），纵向缩放 0.90；而建筑高度是按画布像素直接给的、没有缩放。
## 结果就是整排建筑比底图大 11%，而且**越靠上偏得越多**
##（底边 1064 处偏下 26px、638 处偏上 17px）——
## 表现就是「位置和比例都对不上」，但代码不会报任何错。
##
## 正确做法：底图也画在**画布坐标系**里，整体上移 `_safe_top`，
## 底部超出去的那一段由安全区裁掉，和真机一致。
##
## 平移量必须是**实际** `_safe_top`，不能写死 80：
## 桌面无安全区时它是 0，真机可能是 47/59 —— 写死的话
## 换一个设备建筑就整体偏掉同样的量，而底图不动。
## 这座建筑解锁了没有（M123）。
func _bld_unlocked(bid: String) -> bool:
	if campaign == null:
		return true
	return campaign.quests_done >= int(BLD_UNLOCK.get(bid, 0))


## 差多少个任务才开放（M123）。用于点击时的提示。
func _bld_need(bid: String) -> int:
	if campaign == null:
		return 0
	return maxi(0, int(BLD_UNLOCK.get(bid, 0)) - campaign.quests_done)


func _town_canvas_rect() -> Rect2:
	var h: float = size.x * TOWN_CANVAS_H / 750.0
	return Rect2(0.0, -_safe_top, size.x, h)


func _draw_town_scene() -> void:
	var cr: Rect2 = _town_canvas_rect()
	var far: Texture2D = _town_tex("town", "bg_far")
	if far != null:
		draw_texture_rect(far, cr, false)
	var mid: Texture2D = _town_tex("town", "bg_mid")
	if mid != null:
		draw_texture_rect(mid, cr, false)

	var back: Array = []
	var front: Array = []
	for slot in _town_slots:
		# 未解锁也画（M124）：整块地空着比画个暗的更怪 ——
		# 玩家会觉得「这里本来没东西」而不是「还没开放」。
		if bool((slot as Array)[5]):
			front.append(slot)
		else:
			back.append(slot)
	back.sort_custom(func(a: Array, b: Array) -> bool: return float(a[2]) < float(b[2]))
	front.sort_custom(func(a: Array, b: Array) -> bool: return float(a[2]) < float(b[2]))
	for slot in back:
		_draw_town_bld(slot)

	# 前景层压在建筑之上 —— 树、栅栏、木箱会自然挡住立在它们后面的楼
	var near: Texture2D = _town_tex("town", "bg_near")
	if near != null:
		draw_texture_rect(near, cr, false)
	for slot in front:
		_draw_town_bld(slot)


## 画一把锁（M124）。没有锁的素材，用两个基本图元拼 ——
## 在 1334 宽的画布上显示 22px 大小，够读。
func _draw_lock(c: Vector2, hot: bool) -> void:
	var col: Color = Color(0.94, 0.80, 0.46, 1.0) if hot else Color(0.78, 0.68, 0.48, 0.96)
	# 锁体 26×20：上一版 18×14 在 1334 宽画布上几乎看不见
	draw_rect(Rect2(c.x - 13.0, c.y - 1.5, 26.0, 20.0), col, true)
	# 锁梁（上半圆）
	draw_arc(c + Vector2(0.0, -1.5), 9.5, PI, TAU, 16, col, 3.2)
	# 钥匙孔
	draw_circle(c + Vector2(0.0, 7.0), 2.8, Color(0.10, 0.08, 0.06, 0.92))
	draw_rect(Rect2(c.x - 1.1, c.y + 7.0, 2.2, 5.0), Color(0.10, 0.08, 0.06, 0.92), true)


func _draw_town_bld(slot: Array) -> void:
	var bid: String = str(slot[0])
	var flip: bool = bool(slot[4])
	var r: Rect2 = _town_bld_rect(slot)
	if r.size.x <= 0.0:
		return
	var unlocked: bool = _bld_unlocked(bid)
	var st: int = _hit_state(r, "bld_locked:" + bid if not unlocked else "bld:" + bid)
	var tex: Texture2D = _town_tex("town", "bld_" + bid, flip)
	if not unlocked:
		# 未开放：压成暗灰剪影（保留轮廓，让人看出「这里有座楼」），
		# 中央盖一把锁。指上来稍微提亮一点，表示「能点，只是点不开」。
		if tex != null:
			var dim_k: float = 0.30 if st == TILE_IDLE else 0.42
			draw_texture_rect(tex, r, false, Color(dim_k, dim_k, dim_k * 1.04, 0.95))
		_draw_lock(r.position + r.size * 0.5, st != TILE_IDLE)
		_add_hit(r, "bld_locked:" + bid)
		return
	if tex != null:
		draw_texture_rect(tex, r, false, _town_tint(st))
	# 金色描边：常态 42%，指上来才全亮 —— 「这栋能点」要一眼看出来，
	# 但八栋全亮会盖掉场景本身。
	var rim: Texture2D = _town_tex("town/rim", "rim_" + bid, flip)
	if rim != null:
		var a: float = 0.95 if st != TILE_IDLE else 0.42
		draw_texture_rect(rim, r, false, Color(1.0, 0.78, 0.34, a))
	_add_hit(r, "bld:" + bid)


## 名牌。**逐个算位置**：统一挂底边会有两栋撞车（公会压墓园、疗养院压酒馆）。
##
## 候选顺序：下方 → 上方 → 建筑内底 → 右侧 → 左侧；取第一个既不越界、
## 又不压别的建筑、也不压 UI 条的。中心点先夹回画面内，否则右半出框的建筑
## （酒馆）所有候选都越界，牌子会被甩到屏幕中间，看着像别人的。
func _draw_town_labels() -> void:
	var rects: Array = []
	for slot in _town_slots:
		# 没解锁的建筑不挂名牌（M123），但**要占位**：
		# 下面按索引取 `rects[i]` 来对齐 `_town_slots`，直接 continue
		# 会让后面所有牌子错位到隔壁建筑头上。
		# 未解锁也要占位（索引对齐），但牌子的颜色另算

		var r: Rect2 = _town_bld_rect(slot)
		if r.size.x > 0.0:
			rects.append(r)
		else:
			rects.append(Rect2())
	# dock 只有中间一条（M67）：两侧不再有栏，名牌可以一直下到屏幕底部。
	# 这三块 UI 禁止区全部按「真实占据的矩形」算，不再用整宽。
	var dock_r := Rect2((size.x - DOCK_W) * 0.5, size.y - NAV_H - DOCK_H, DOCK_W, DOCK_H)
	var ui: Array = [
		Rect2(0, 0, size.x, 92.0),
		Rect2(size.x * 0.5 - 176.0, _roster_y(), 352.0, 126.0),
		dock_r,
	]
	# 已放好的名牌。**牌子之间也要互斥** ——
	# 商队和酒馆在横向重叠，只跟建筑比的话两块牌子会并排贴成一片，
	# 玩家分不清哪块是哪栋的。
	var placed: Array = []
	for i in _town_slots.size():
		var slot: Array = _town_slots[i]
		var own: Rect2 = rects[i] if i < rects.size() else Rect2()
		if own.size.x <= 0.0:
			continue
		var pw: float = clampf(own.size.x * 0.86, 84.0, 118.0)
		var cx: float = clampf(own.position.x + own.size.x * 0.5,
			14.0 + pw * 0.5, size.x - 14.0 - pw * 0.5)
		var base_y: float = own.end.y
		# 底边已经沉进 dock 的建筑（商队、马车）先试**挂建筑顶部**：
		# 它们底部的候选全在 dock 里，最后只会被夹回 dock 上方几十像素，
		# 牌子离建筑老远，看着像别人的。
		var over_dock: bool = own.end.x > dock_r.position.x \
			and own.position.x < dock_r.end.x
		var sunk: bool = over_dock and base_y > size.y - NAV_H - DOCK_H
		var cands: Array = []
		if sunk:
			# 放在**建筑内部靠顶**，不是顶部外面：
			# 顶部外面会和邻栋（酒馆）的牌子撞，撞掉之后只能回退到 dock 上方，
			# 那时牌子离自己那栋楼 150px，谁也不认它是谁的。
			cands.append(Vector2(cx - pw * 0.5, own.position.y + 16.0))
			# 居中版会压到名册条（名册条两端各伸出建筑中线 170px），
			# 再试贴着自己建筑的右上/左上角 —— 牌子仍在自己身上，只是不居中。
			cands.append(Vector2(minf(own.end.x - pw - 6.0, size.x - 14.0 - pw),
				own.position.y + 16.0))
			cands.append(Vector2(maxf(own.position.x + 6.0, 14.0),
				own.position.y + 16.0))
			cands.append(Vector2(cx - pw * 0.5, own.position.y - 34.0))
		cands.append(Vector2(cx - pw * 0.5, base_y + 6.0))
		cands.append(Vector2(cx - pw * 0.5, own.position.y - 34.0))
		cands.append(Vector2(cx - pw * 0.5, base_y - 30.0))
		cands.append(Vector2(own.end.x + 6.0, base_y - 30.0))
		cands.append(Vector2(own.position.x - pw - 6.0, base_y - 30.0))
		var pick: Vector2 = Vector2(cx - pw * 0.5, base_y - 30.0)
		for c in cands:
			var rr := Rect2(c.x, c.y, pw, 26.0)
			if rr.position.x < 14.0 or rr.end.x > size.x - 14.0:
				continue
			# 底部只保留 30px 的屏幕边距（M67）：原来这里留 170，
			# 是为「通栏 dock + 名册条」让位；两者一个收窄、一个搬去顶部之后，
			# 那条限制会把两侧建筑的名牌强行压在屏幕中间。
			if rr.position.y < 100.0 or rr.end.y > size.y - 30.0:
				continue
			var bad: bool = false
			for k in rects.size():
				if k != i and rr.intersects(rects[k]):
					bad = true
					break
			if not bad:
				for u in ui:
					if rr.intersects(u):
						bad = true
						break
			if not bad:
				for pr2 in placed:
					if rr.intersects(pr2):
						bad = true
						break
			if not bad:
				pick = c
				break
		# 最后一道保险：绝不让牌子落进 dock 区（商队那种底边沉在底栏里的，
		# 所有候选都被判越界，回退位置正好在 dock 后面 —— 等于没有名牌）。
		# M67：只对**横向与 dock 重叠**的牌子生效，两侧的可以到底。
		if pick.x + pw > dock_r.position.x and pick.x < dock_r.end.x:
			pick.y = minf(pick.y, size.y - NAV_H - DOCK_H - 34.0)
		else:
			pick.y = minf(pick.y, size.y - 34.0)
		var lr := Rect2(pick.x, pick.y, pw, 26.0)
		placed.append(lr)

		_panel(lr, Color(0.043, 0.039, 0.035), true)
		_text(Vector2(lr.position.x, lr.position.y + 18.0),
			str(_building_meta(str(slot[0]))[1]), DdTheme.FONT_BD, DdTheme.TEXT,
			HORIZONTAL_ALIGNMENT_CENTER, pw)


## 名册条的位置（M67：从底部搬到**顶部居中**）。
##
## 它原来压在屏幕下三分之一（在 dock 上方 192），和马车、墓碑、铁匠铺
## 抢同一块地方。搬到 header 下面之后，中下部整块还给了场景。
## 92 是「资源条基线 76 + 字高」之后的第一个安全位置。
func _roster_y() -> float:
	return 92.0


func _draw_roster_strip(ids: Array, alive_n: int) -> void:
	var w: float = 352.0
	var x0: float = size.x * 0.5 - w * 0.5
	var y0: float = _roster_y()
	_panel(Rect2(x0, y0, w, 126.0), DdTheme.PANEL_DEEP)
	draw_rect(Rect2(x0 + 2.0, y0 + 8.0, 3.0, 18.0), DdTheme.PARTY)
	# 整条标题可点 → 名册页（M64）。只让头像可点的话，
	# 玩家想「看全部人」得先猜到有这么一个入口。
	var head_r := Rect2(x0, y0, w, 32.0)
	_add_hit(head_r, "roster_page")
	_text(Vector2(x0 + 14.0, y0 + 25.0), "名册 %d 人" % ids.size(),
		DdTheme.FONT_LG, DdTheme.TEXT)
	# 「存活 5 · 上限 4」在字号提了两档之后会顶到右边的「全部 ›」（M72），
	# 缩成「活 5/4」——这一条本来就只是给「我这趟能带几个」看的。
	# 「活 5/4」这个写法本身就在制造误会（M94）：活着 5 个、上限 4 个，
	# 读起来像「系统不让我带满」。真正该看的是**能出征几个**——
	# 疗养院里的人活着，但这趟带不走。改成可出征数，一眼就对上。
	# 只读展示，**不改** `_prep_party`：这一条是「本趟阵容」的镜子，
	# 不该在这里决定了出征名单。
	# 名单为空（还没选过）时退到「能出征的前 4 个」——
	# 直接调 `_party_for` 会被课题等级过滤（高等级英雄进不了低级本），
	# 结果整条显示成 4 个空槽（M127 第一版就是这样）。
	# 名册条要**过滤死人和忙人**（M191）。
	# 原来直接 `_prep_party.duplicate()`，而阵亡的人还留在出征名单里
	# （解雇才移除，死亡不移除）—— 于是队伍已经死伤大半，
	# 城镇这条名册还在显示「上阵 4/4」四个正常人。
	# 用户原话：「我明明战死 2 个了，这里还是显示 4 个正常人」。
	var show_ids: Array = []
	if campaign != null:
		for h_show in _prep_party:
			var r_show: Dictionary = campaign.hero(str(h_show))
			if bool(r_show.get("alive", false)) and campaign.busy_of(str(h_show)) <= 0:
				show_ids.append(str(h_show))
	if show_ids.is_empty() and campaign != null:
		# 其次是**存档里的名单**（M114 存的那份）：刚启动/切后台回来时
		# 内存里的 `_prep_party` 还是空的，但玩家的选择在档里。
		show_ids = campaign.party_ids.duplicate()
	if show_ids.is_empty() and campaign != null:
		show_ids = campaign.selectable_ids().slice(0, Campaign.PARTY_MAX)
	var can_go: int = campaign.selectable_ids().size()
	# 标题右侧原本写「可出征 N/4」，但名册条画的是**上阵的 4 个格子**，
	# 两个数字对不上会让人以为系统不让他带满。现在直接报「上阵 N/4」。
	_text(Vector2(x0 + 152.0, y0 + 25.0),
		"上阵 %d/%d" % [mini(show_ids.size(), Campaign.PARTY_MAX), Campaign.PARTY_MAX],
		DdTheme.FONT_TAG,
		DdTheme.DIM if can_go >= Campaign.PARTY_MAX else DdTheme.WARN)
	# 用 TEXT 不用 PARTY：皮肤主色偏冷灰，压在深底上几乎看不见，
	# 而这个入口是「怎么看全部人」的唯一线索，必须能看见。
	_text(Vector2(x0 + w - 62.0, y0 + 25.0), "全部 ›", DdTheme.FONT_BD,
		DdTheme.TEXT if head_r.has_point(_mouse) else DdTheme.DIM,
		HORIZONTAL_ALIGNMENT_RIGHT, 50.0)
	# 这条显示的是**上阵的 4 个人**（M127），不是名册前 5 个。
	# 原来照着名册顺序排，玩家看不出「这周到底带谁下去」——
	# 而这一条就在城镇正中，是每周看的第一眼。
	var n: int = Campaign.PARTY_MAX
	for i in n:
		var hid: String = str(show_ids[i]) if i < show_ids.size() else ""
		if hid.is_empty():
			# 空位：虚线感的空槽 + 一个「空」字。名册里还有人也不补 ——
			# 这 4 个格子表达的是「本趟阵容」，不是「我有哪些人」。
			var er := Rect2(x0 + 14.0 + float(i) * 67.0, y0 + 38.0, 56.0, 56.0)
			draw_rect(er, DdTheme.PANEL_EDGE, false, 1.0)
			_text(Vector2(er.position.x, er.end.y - 18.0), "空", DdTheme.FONT_TAG,
				DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, 56.0)
			continue
		var pr := Rect2(x0 + 14.0 + float(i) * 67.0, y0 + 38.0, 56.0, 56.0)
		var tex: Texture2D = _art.texture_of(campaign.def_of(hid))
		# 在建筑里的人整张头像压暗（M94）：这条名册条原来完全看不出
		# 「他这周不能用」，玩家的第一反应就是「我的人怎么不见了」。
		var bz: int = campaign.busy_of(hid)
		var tint: Color = Color(0.42, 0.42, 0.48, 1.0) if bz > 0 else Color(1, 1, 1, 1)
		if tex != null:
			draw_texture_rect(tex, pr, false, tint)
		draw_rect(pr, DdTheme.PANEL_EDGE, false, 1.0)
		_text(Vector2(pr.position.x, pr.end.y + 16.0), _hero_label(hid),
			DdTheme.FONT_TAG, DdTheme.FAINT if bz > 0 else DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_CENTER, 56.0)
		_add_hit(pr, "hero_info:" + hid)


## 当前所在的 dock 页签。城镇的子页（名册）也算「城镇」。
func _dock_cur() -> String:
	match _state:
		S_GATE:
			return "gate"
		S_SHOP:
			return "shop"
	return "town"


## 底部 dock（M64 第九轮重做）。
##
## 原来是一个圆圈套一个单字 + 一行小字。干净，但和这套皮肤完全不搭：
## 冷灰色的圆环压在暖色墨线场景上，读起来像贴了三个系统控件。
##
## 现在改成「金属托 + 图集图标 + 文字」：
##   · 底座三层（外圈暗 / 上偏移的亮面 / 再挖一个更深的心），有个小凸起的手感；
##   · 选中项：暗金环 + 外发光 + 文字下方一条短金线 —— 全用 `LIGHT` 那支暖金，
##     蓝灰 `PARTY` 在这张图里是异色；
##   · 中间那颗（出征）更大、位置更高、顶上一段带菱形的装饰线：
##     这一屏只有它是「该点的地方」，尺寸差本身就是提示；
##   · 图标走图集（半身像 / 契约 / 金币），和名册、任务板同一套画风。
func _draw_dock() -> void:
	var h: float = DOCK_H
	var dw: float = DOCK_W
	var dx: float = (size.x - dw) * 0.5
	var y0: float = size.y - h

	# 场景 → dock：往上压 24px 的渐隐。一条硬边会把画面从中间切断，
	# 压暗之后底栏像是从场景里「沉下去」的。
	# 只在栏宽范围内压：整宽的话两侧会留下一条看不见的暗带，
	# 把本来该露出来的半个铁匠铺白白压暗。
	for i in 8:
		draw_rect(Rect2(dx, y0 - 24.0 + float(i) * 3.0, dw, 3.0),
			Color(0.02, 0.02, 0.025, 0.032 * float(8 - i)))
	draw_rect(Rect2(dx, y0, dw, h), Color(0.035, 0.036, 0.040, 0.97))
	if _sk_grain != null:
		draw_texture_rect(_sk_grain, Rect2(dx, y0, dw, h), true)
	# 顶边双线：上暗金、下近黑。单线像分隔符，双线才像「一条栏」的上沿。
	draw_line(Vector2(dx, y0), Vector2(dx + dw, y0), Color(0.30, 0.25, 0.15), 1.0)
	draw_line(Vector2(dx, y0 + 1.5), Vector2(dx + dw, y0 + 1.5), Color(0.0, 0.0, 0.0, 0.55), 1.0)
	# 窄栏两侧要收边：否则它读成「一块贴在屏幕上的贴图」，而不是一条栏
	draw_line(Vector2(dx, y0), Vector2(dx, size.y), Color(0.22, 0.18, 0.11, 0.8), 1.0)
	draw_line(Vector2(dx + dw, y0), Vector2(dx + dw, size.y), Color(0.22, 0.18, 0.11, 0.8), 1.0)

	# 中间那颗顶上的装饰线 + 菱形。栏只有 264 宽，横线从 ±56 收到 ±34。
	var mx: float = size.x * 0.5
	var my: float = y0 + 8.0
	draw_line(Vector2(mx - 34.0, my), Vector2(mx - 12.0, my),
		Color(0.34, 0.28, 0.15), 1.0)
	draw_line(Vector2(mx + 12.0, my), Vector2(mx + 34.0, my),
		Color(0.34, 0.28, 0.15), 1.0)
	draw_colored_polygon(PackedVector2Array([
		Vector2(mx, my - 4.0), Vector2(mx + 4.0, my),
		Vector2(mx, my + 4.0), Vector2(mx - 4.0, my)]),
		Color(0.56, 0.45, 0.22))

	_dock_tab(dx + dw * 0.11, y0 + 66.0, 24.0, "town", "城镇", "town")
	_dock_tab(dx + dw * 0.37, y0 + 60.0, 30.0, "gate", "出征", "gate", true)
	# 队伍（M106）：装备、技能、上阵三件事放一屏。
	# 原来它们分散在「商店→饰品货架」（装备）、「公会」（技能）、
	# 「出发准备」（上阵）三个互不相干的地方，玩家根本拼不起来。
	_dock_tab(dx + dw * 0.63, y0 + 66.0, 24.0, "guild", "队伍", "party")
	_dock_tab(dx + dw * 0.89, y0 + 66.0, 24.0, "shop", "商店", "shop")


## dock 图标缓存。**不能每帧 load()**：在 `_draw()` 里同步加载，
## 第一帧拿到的是一张「尺寸对、但还没上传到 GPU」的纹理，
## 画出来就是一块纯白（乘以 modulate 之后正好等于 tint 色）。
var _dock_tex: Dictionary = {}


## dock 图标（M64 第十轮）。
##
## 优先用美术新交付的 `assets/art/ui/town/dock/icon_<key>.png`（512×512），
## 没有就退回图集里那三张 40px 的旧图。
## 这样新图丢进目录、重开一次编辑器就生效，不用改代码也不用等一次往返。
func _dock_icon(key: String) -> Texture2D:
	if _dock_tex.has(key):
		return _dock_tex[key]
	var tex: Texture2D = null
	var p: String = "res://assets/art/ui/town/dock/icon_%s.png" % key
	if ResourceLoader.exists(p):
		tex = load(p)
	if tex != null:
		_dock_tex[key] = tex
		return tex
	var fallback: Texture2D = null
	match key:
		"town":
			fallback = _ico("icon_bust")
		"gate":
			fallback = _ico("icon_deed")
		"shop":
			fallback = _ico("icon_gold")
	_dock_tex[key] = fallback
	return fallback


## dock 上的一颗。`tab` 和 `_dock_cur()` 相同即为选中（金色点亮）。
func _dock_tab(cx: float, cy: float, rad: float, key: String, label: String,
		tab: String, primary: bool = false) -> void:
	var active: bool = tab == _dock_cur()
	# 命中区把文字也框进来：只框圆圈的话，点名字没反应，玩家会以为按钮坏了。
	# M67：横向只比圆宽 6px —— 三颗间距只有 66，原来的 +28 会让相邻两颗
	# 的热区叠在一起，点「城镇」可能落到「出征」上。
	var hit := Rect2(cx - rad - 3.0, cy - rad - 14.0, rad * 2.0 + 6.0, rad * 2.0 + 46.0)
	var st: int = _hit_state(hit, "dock:" + tab)
	var hot: bool = st != TILE_IDLE
	# 按下时整体沉 2px：只有颜色变化在大屏上看不出「按进去了」
	var c := Vector2(cx, cy + (2.0 if st == TILE_PRESS else 0.0))

	if active or hot:
		draw_circle(c, rad + 14.0, Color(0.88, 0.68, 0.30, 0.05))
		draw_circle(c, rad + 7.0, Color(0.88, 0.68, 0.30, 0.07))
	elif primary:
		# 主按钮静止时也留一层极淡的暖光，否则和旁边两颗一样「死」
		draw_circle(c, rad + 10.0, Color(0.88, 0.68, 0.30, 0.035))

	# 金属托：三层同心圆。亮面往上偏 1.5px —— 光源在上方，偏移量不用大
	draw_circle(c, rad, Color(0.018, 0.018, 0.022))
	draw_circle(c + Vector2(0.0, -1.5), rad - 2.0,
		Color(0.145, 0.132, 0.108) if active else Color(0.088, 0.085, 0.080))
	draw_circle(c, rad - 6.5,
		Color(0.108, 0.090, 0.055) if active else Color(0.052, 0.050, 0.048))

	# 三档：选中（亮金）> 主按钮/悬停（暗金）> 其余（近黑）。
	# 中间那颗是「这一屏唯一该点的地方」，它不亮就等于没有主次。
	var ring: Color = Color(0.66, 0.52, 0.25) if active else (
		Color(0.40, 0.33, 0.17) if primary else (
			Color(0.44, 0.41, 0.36) if hot else Color(0.19, 0.18, 0.17)))
	draw_arc(c, rad - 1.0, 0.0, TAU, 64, ring, 2.4)
	if active:
		# 外面再套一道半透明的细环，金色才「发」得出来
		draw_arc(c, rad + 2.5, 0.0, TAU, 64, Color(0.62, 0.49, 0.24, 0.38), 1.0)

	var tint: Color = Color(1.0, 1.0, 1.0, 1.0) if active else (
		Color(0.95, 0.93, 0.89, 1.0) if (hot or primary) else Color(0.86, 0.83, 0.79, 1.0))
	# 按纹理的实际宽高比居中 —— 新交付的图未必是正方形内容
	var isz: float = rad * (1.50 if primary else 1.54)
	var tex: Texture2D = _dock_icon(key)
	if tex != null:
		var k: float = isz / float(maxi(1, maxi(tex.get_width(), tex.get_height())))
		var tw: float = float(tex.get_width()) * k
		var th: float = float(tex.get_height()) * k
		draw_texture_rect(tex,
			Rect2(cx - tw * 0.5, c.y - th * 0.5, tw, th), false, tint)
	else:
		# 没有图标就画个人形剪影（M123）：「队伍」这一项是后加的，
		# 原素材里只有城镇/出征/商店三张图。留个空圆看起来像加载失败。
		var hr: float = isz * 0.22
		draw_circle(Vector2(cx, c.y - isz * 0.18), hr, tint)
		draw_rect(Rect2(cx - hr * 1.5, c.y - isz * 0.02, hr * 3.0, isz * 0.30),
			tint, true)
		draw_circle(Vector2(cx - isz * 0.24, c.y + isz * 0.10), hr * 0.72, tint)
		draw_circle(Vector2(cx + isz * 0.24, c.y + isz * 0.10), hr * 0.72, tint)

	var lab_c: Color = DdTheme.LIGHT if active else (
		Color(0.92, 0.82, 0.60) if (hot or primary) else DdTheme.DIM)
	# 基线固定在「屏幕底往上 22」：三颗无论圆多大都落在同一条线上，
	# 跟着 `cy + rad` 走的话，中间那颗的字会低一截。
	# M67 原来是「栏底 + 188 - 26」，188 是写死的旧栏高，栏一改就错位。
	var lab_y: float = size.y - 22.0
	_text(Vector2(cx - 38.0, lab_y), label, 12, lab_c,
		HORIZONTAL_ALIGNMENT_CENTER, 76.0)
	if active:
		draw_rect(Rect2(cx - 16.0, lab_y + 6.0, 32.0, 2.0),
			Color(0.88, 0.70, 0.31, 0.85))

	_add_hit(hit, "dock:" + tab)


## 名册页（M64）。
##
## 城镇首页那块名册条只放得下 5 个头像，回答的是「我有几个人」；
## 「该送谁去疗养院、谁在忙、谁带了病」要在一屏里看全，就是这屏。
## 点任意一行仍然走原来的详情抽屉 —— 这里只做一览，不重复造详情。
func _draw_roster_page() -> void:
	var ids: Array = campaign.hero_ids_deployed_first()
	var alive_n: int = campaign.alive_ids().size()
	var stress_hi: int = 0
	var sick: int = 0
	var idle_n: int = 0
	for hv in ids:
		var h: String = str(hv)
		var row: Dictionary = campaign.hero(h)
		if not bool(row.get("alive", false)):
			continue
		if float(row.get("stress", 0.0)) >= 100.0:
			stress_hi += 1
		if campaign.diseases_of(h).size() > 0:
			sick += 1
		if campaign.busy_of(h) <= 0:
			idle_n += 1
	# 字号放大 1.5 倍后这一行放不下了（"带病 N"被截在边缘外）。
	# 带病人数在每张卡的属性行里有，副标题不重复（M138）。
	_header("名册", "存活 %d/%d · 可出征 %d · 压力过百 %d" % [
		alive_n, ids.size(), idle_n, stress_hi])

	var top: float = float(DdTheme.HEADER_H) + 16.0
	var btn_h: float = 56.0
	var by: float = size.y - 44.0 - btn_h - NAV_H
	var n: int = ids.size()

	if n == 0:
		_text(Vector2(DdTheme.MARGIN, top + 40.0),
			"名册是空的 —— 去马车征召几个人", DdTheme.FONT_LG, DdTheme.WARN)
	else:
		var gap: float = 10.0
		var avail: float = by - 18.0 - top
		var cols: int = 1
		var rows: int = n
		var rh: float = (avail - gap * float(maxi(n - 1, 0))) / float(n)
		# 15 人单列只剩 55 高，头像都塞不下 —— 过线就转两列。
		# 两列不是「好看」，是「15 个人必须在一屏里不滚动地看全」。
		if rh < 104.0:
			cols = 2
			rows = int(ceil(float(n) / 2.0))
			rh = (avail - gap * float(maxi(rows - 1, 0))) / float(maxi(rows, 1))
		rh = clampf(rh, 76.0, 176.0)
		var cw: float = (size.x - 48.0 - (gap if cols == 2 else 0.0)) / float(cols)
		for i in n:
			var col: int = i % cols
			var rowi: int = int(float(i) / float(cols))
			_draw_roster_row(Rect2(24.0 + float(col) * (cw + gap),
				top + float(rowi) * (rh + gap), cw, rh), str(ids[i]))

	var half: float = (size.x - 60.0) * 0.5
	_add_button(Rect2(24.0, by, half, btn_h), "roster_coach",
		"去马车征召（%d / %d）" % [alive_n, campaign.roster_max()])
	_add_button(Rect2(24.0 + half + 12.0, by, half, btn_h), "roster_back", "返回城镇")

	# 抽屉画在最后：它是模态的，要盖住这一屏（含底部按钮）
	_draw_hero_sheet()


## 头像 + 职业纹章（M64 第十三轮）。
##
## 六个界面共用：名册页、建筑屏列表、饰品仓库、结算、地图队伍卡、准备屏出战卡。
## 图集里 15 张 `job_*` 之前只在英雄详情抽屉用过一次，其余全是纯文字。
##
## 纹章一律叠在头像**右下角**：那一带通常是肩膀或背景，不挡脸；
## 放名字左边的话，窄卡（212 宽的建筑列表、345 宽的两列名册）名字要后退 40px，
## 直接放不下。
func _draw_hero_badge(hid: String, r: Rect2, alive: bool = true) -> void:
	var tex: Texture2D = _art.texture_of(campaign.def_of(hid))
	if tex != null:
		draw_texture_rect(tex, r, false,
			Color(1, 1, 1, 1) if alive else Color(0.45, 0.45, 0.45, 0.7))
	draw_rect(r, DdTheme.PANEL_EDGE, false, 1.0)
	# 纹章边长跟着头像走：16px 以下就只剩一团，干脆不画
	var br: float = clampf(minf(r.size.x, r.size.y) * 0.46, 16.0, 32.0)
	var jt: Texture2D = _ico("job_" + campaign.def_of(hid))
	if jt == null or br < 15.0:
		return
	var bc := Vector2(r.end.x - br * 0.66, r.end.y - br * 0.66)
	draw_circle(bc, br * 0.5 + 2.5, Color(0.045, 0.045, 0.052, 0.96))
	draw_arc(bc, br * 0.5 + 2.5, 0.0, TAU, 24, Color(0.34, 0.30, 0.24), 1.0)
	_draw_ico("job_" + campaign.def_of(hid),
		Vector2(bc.x - br * 0.5, bc.y - br * 0.5), br,
		Color(1, 1, 1, 1) if alive else Color(0.55, 0.55, 0.55, 0.8))


## 名册页的一行：头像 + 名字 + 等级装备 + 压力 + 状态。
##
## 信息取舍和详情抽屉一致：只放「城镇里能改变决策」的。
## 战斗数值（闪避/命中）不在这里 —— 那些在铁匠铺和出发准备里看。
func _draw_roster_row(r: Rect2, hid: String) -> void:
	var row: Dictionary = campaign.hero(hid)
	if row.is_empty():
		return
	var alive: bool = bool(row.get("alive", false))
	var st: int = _hit_state(r, "hero_info:" + hid)
	_panel(r, DdTheme.PANEL_HI if st != TILE_IDLE else DdTheme.PANEL_DEEP)
	if not alive:
		# 阵亡的人留在名册里是给墓园记名字的：整行压暗 + 左侧红条，
		# 一眼就能跳过，又不会被误当成「还能用」。
		draw_rect(r, Color(0.0, 0.0, 0.0, 0.34))
		draw_rect(Rect2(r.position.x, r.position.y, 4.0, r.size.y), DdTheme.CRIT)

	# 头像：高度贴着行高走，宽度按立绘比例（实测 0.754）。
	# 上限 120 —— 5 人时行高 176，头像是这张卡的主角，不该只有指甲盖大。
	var ph: float = minf(r.size.y - 26.0, 120.0)
	var pw2: float = ph * 0.754
	var pr := Rect2(r.position.x + 14.0, r.position.y + (r.size.y - ph) * 0.5, pw2, ph)
	_draw_hero_badge(hid, pr, alive)

	var tx: float = pr.end.x + 16.0
	# 内容以卡片中线为基准上下分布。
	# 原来用「内容块 78 高再居中」，行高一放大就变成「上半截有字、下半截空」——
	# 定高内容配变高卡片，必然在大的那档露馅。
	var cy: float = r.position.y + r.size.y * 0.5
	var nm_fs: int = DdTheme.FONT_H1 if r.size.y >= 120.0 else DdTheme.FONT_LG

	# 左侧职业色条：卡片之间只隔 10px，全靠边框区分太弱
	draw_rect(Rect2(r.position.x + 2.0, r.position.y + 12.0, 3.0, r.size.y - 24.0),
		DdTheme.PARTY if alive else DdTheme.CRIT)

	_text(Vector2(tx, cy - 34.0), _hero_label(hid), nm_fs,
		DdTheme.TEXT if alive else DdTheme.FAINT)
	_text(Vector2(tx, cy - 10.0), "Lv%d · 装备 %d 阶 · 出征 %d 次 · 阵亡 %d 次" % [
		campaign.resolve_of(hid), campaign.gear_of(hid),
		int(row.get("runs", 0)), int(row.get("deaths", 0))],
		DdTheme.FONT_MD, DdTheme.DIM if alive else DdTheme.FAINT)

	# 压力条和数值同一行：分两行写会白吃掉一个行位，
	# 而 15 人两列时每一像素都要算。
	var stress: float = float(row.get("stress", 0.0))
	var num_w: float = 96.0
	var bar_w: float = maxf(60.0, r.end.x - tx - 16.0 - num_w)
	_bar(Rect2(tx, cy + 6.0, bar_w, 7.0), stress / 200.0,
		DdTheme.STRESS, DdTheme.STRESS_TRACK)
	_text(Vector2(r.end.x - 16.0 - num_w, cy + 15.0), "压力 %.0f / 200" % stress,
		DdTheme.FONT_SM, DdTheme.STRESS if stress >= 100.0 else DdTheme.FAINT,
		HORIZONTAL_ALIGNMENT_RIGHT, num_w)

	# 第四行：技能 / 饰品 / 病 —— 这三样决定「要不要现在处理他」，
	# 也是详情抽屉里最常被翻的两块，在列表上先给个数字。
	var sk_n: int = campaign.equipped_skills(hid).size()
	var sk_max: int = campaign.skill_slot_max(hid)
	var tr_n: int = campaign.equipped_of(hid).filter(
		func(t: Variant) -> bool: return not str(t).is_empty()).size()
	var bits: Array = [
		"技能 %d/%d" % [sk_n, sk_max] if sk_n < sk_max else "技能 %d" % sk_n,
		"饰品 %d/%d" % [tr_n, campaign.equip_slots],
	]
	var dn: int = campaign.diseases_of(hid).size()
	if dn > 0:
		bits.append("病 %d" % dn)
	_text(Vector2(tx, cy + 44.0), " · ".join(bits), DdTheme.FONT_SM,
		DdTheme.DIM if alive else DdTheme.FAINT)

	# 右上角状态：阵亡 > 忙 > 病/负 > 空闲。只写一件最要紧的，
	# 一行塞三个标签在窄卡里会互相压。
	# 优先级：阵亡 > 上阵 > 修养 > 带病 > 空闲（M127）。
	# 加「上阵」和「空闲」是用户提的：原来只写「忙 N 周」，
	# 看不出谁在阵容里、谁只是待着。
	var tag: String = ""
	var tag_c: Color = DdTheme.FAINT
	if not alive:
		tag = "阵亡"
		tag_c = DdTheme.CRIT
	elif _is_deployed(hid):
		tag = "上阵"
		tag_c = DdTheme.OK
	elif campaign.busy_of(hid) > 0:
		tag = "修养 %d 周" % campaign.busy_of(hid)
		tag_c = DdTheme.PARTY
	elif campaign.diseases_of(hid).size() > 0:
		tag = "病 %d" % campaign.diseases_of(hid).size()
		tag_c = DdTheme.WARN
	else:
		# 「负 N」不再占这一格（M127）：几乎每个人都有负面怪癖，
		# 它把「空闲」挤掉之后，四个人全显示「负 1」，等于没有状态。
		# 怪癖明细在详情抽屉里，这里只回答「这人这周能不能用」。
		tag = "空闲"
		tag_c = DdTheme.DIM
	# 色点 + 文字（M127）：用户要「明确的图标标识」。
	# 圆点用状态色，文字跟在右边 —— 比纯文字扫得快，也不占额外高度。
	#
	# 这一块**可点**（M128）：点「上阵」= 下阵，点「空闲」= 上阵。
	# 名册页原来只能看，要改阵容得跑队伍屏，多一步且不直观。
	var can_toggle: bool = alive and campaign.busy_of(hid) <= 0
	var tag_r := Rect2(r.end.x - 128.0, r.position.y + 4.0, 116.0, 32.0)
	var tag_hot: bool = can_toggle and tag_r.has_point(_mouse)
	draw_circle(Vector2(r.end.x - 100.0, r.position.y + 20.0), 5.0,
		tag_c.lightened(0.25) if tag_hot else tag_c)
	_text(Vector2(r.end.x - 92.0, r.position.y + 24.0), tag, DdTheme.FONT_TAG,
		tag_c.lightened(0.3) if tag_hot else tag_c,
		HORIZONTAL_ALIGNMENT_RIGHT, 78.0)
	if not alive:
		# 阵亡的人右上角给一个**快捷复活**（M153）：原来只写「阵亡」两个字，
		# 想复活得先跑马车、再在里面找这个人。死人排到末尾之后，
		# 这一格正好空出来 —— 和公会的「升技能」是同一个道理。
		var rcost: int = int((campaign.effective_recruit_cost(hid) as Dictionary).get("gold", 0))
		var can_rv: bool = campaign.can_recruit(hid)
		# 宽度 120 → 148：「复活 1000 金」五个字加数字放不进 120，
		# 末尾的「金」被切掉 —— 而它正是单位（M153）。
		_add_button(Rect2(r.end.x - 160.0, r.position.y + 4.0, 148.0, 32.0),
			"revive:" + hid, "复活 %d 金" % rcost, can_rv)
	if can_toggle:
		# 悬停时在下面补一句动作提示：光靠「标签能点」这件事没人猜得到。
		if tag_hot:
			_text(Vector2(r.end.x - 128.0, r.position.y + 40.0),
				"点此下阵" if _is_deployed(hid) else "点此上阵",
				DdTheme.FONT_TAG, DdTheme.CRIT, HORIZONTAL_ALIGNMENT_RIGHT, 116.0)
		_add_hit(tag_r, "roster_deploy:" + hid)

	_hit_overlay(r, "hero_info:" + hid)
	_add_hit(r, "hero_info:" + hid)


## 出征页（M64）：区域 + 难度从城镇屏搬到这里。
##
## 底部被名册条（126 高）和 dock（160 高）占满之后，那两栏在城镇屏上
## 已经没有纵向位置了。逻辑沿用原来那套，只是从「一块」变成「一整屏」。
func _draw_gate() -> void:
	var cycle: Dictionary = campaign.cfg.get("town_cycle", {}) as Dictionary
	var idle_cost: int = int(cycle.get("idle_cost", 50))
	var wk_relief: int = int(cycle.get("weekly_stress_relief", 0))
	_header("出征", "点难度卡出发 · 换区域会换整块任务板 · 休整一周全队恢复 %d 压力" % wk_relief)
	var top: float = 96.0
	var gap: float = 10.0
	# 行高按剩余高度算：固定 150 会让整页下面空 400px（1334 的屏只用到 750）
	var btn_h: float = 56.0
	var by: float = size.y - 44.0 - btn_h - NAV_H
	var row_h: float = clampf((by - 14.0 - top - gap * 3.0) / 4.0, 110.0, 240.0)
	var lx: float = 24.0
	var lw: float = 214.0
	var rx: float = lx + lw + 12.0
	var rw: float = size.x - rx - 24.0
	var alive: int = campaign.alive_ids().size()

	var dungeons: Array = ["weald", "crypts", "warrens", "cove"]
	for i in dungeons.size():
		var did: String = str(dungeons[i])
		var on: bool = did == _dungeon
		var dr := Rect2(lx, top + float(i) * (row_h + gap), lw, row_h)
		var dst: int = _hit_state(dr, "dungeon:" + did)
		if on and dst == TILE_IDLE:
			dst = TILE_ACTIVE
		_tile(dr, dst)
		if on:
			draw_rect(Rect2(dr.position.x, dr.position.y, 5.0, dr.size.y), DdTheme.PARTY)
		var tx: float = dr.position.x + 18.0
		if _ico("sigil_" + did) != null:
			_draw_ico("sigil_" + did, Vector2(dr.position.x + 12.0,
				dr.position.y + (dr.size.y - 52.0) * 0.5), 52.0,
				Color(1, 1, 1, 1) if on else Color(0.72, 0.72, 0.75, 0.92))
			tx = dr.position.x + 74.0
		_text(Vector2(tx, dr.position.y + 38.0), DdNames.dungeon_name(did),
			DdTheme.FONT_BD, DdTheme.TEXT if on else DdTheme.DIM)
		_text(Vector2(tx, dr.position.y + 66.0), DdNames.dungeon_tag(did),
			DdTheme.FONT_TAG, DdTheme.DIM if on else DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_LEFT, dr.size.x - (tx - dr.position.x) - 10.0)
		if not on:
			_text(Vector2(tx, dr.position.y + 96.0), "点选切换", DdTheme.FONT_TAG,
				DdTheme.FAINT)
		_add_hit(dr, "dungeon:" + did)

	var rows: Array = _board_rows()
	for i in rows.size():
		_draw_board_card(rows[i], Rect2(rx, top + float(i) * (row_h + gap), rw, row_h), alive)

	var half: float = (size.x - 60.0) * 0.5
	_add_button(Rect2(24.0, by, half, 56.0), "idle_week",
		"休整一周 · %d 金" % idle_cost, campaign.gold >= idle_cost)
	_add_button(Rect2(24.0 + half + 12.0, by, half, 56.0), "gate_back", "返回城镇")


## 一句话情报。首领任务报首领池（「首领：海妖、溺亡船长」），
## 普通任务报这一档最常见的两种怪。
##
## 只报基础名，不报具体是哪一只——遭遇是随机抽的，
## 写死一个名字等于撒谎。报「可能出现哪几种」才是诚实的说法。
func _foe_brief(info: Dictionary, quest: String) -> String:
	var ids: Array = info.get("bosses" if quest == "kill_boss" else "common", [])
	if ids.is_empty():
		return ""
	var names: Array = []
	for i in ids.slice(0, 2):
		names.append(DdNames.monster_name(str(i)))
	return ("首领：" if quest == "kill_boss" else "主要：") + "、".join(names)


## 存活英雄的平均装备阶。用来判断「这趟够不够格」，不是精确战力评估。
## 不传 `ids` 就是整个存活名册；传了就是这几个人（准备屏要算的是**出战名单**）。
func _party_gear_avg(ids: Array = []) -> int:
	var who: Array = ids if not ids.is_empty() else campaign.alive_ids()
	if who.is_empty():
		return 0
	var s: int = 0
	for hid in who:
		s += campaign.gear_of(hid)
	return int(round(float(s) / float(who.size())))


## 名册里有几个人能进这个等级的本（M25）。
##
## 逻辑在 `Campaign.fit_count` 里，这里只转发——任务板的权重也算同一件事，
## 两处各写一遍的话，改规则时必然只改一处，然后界面和板子对不上。
func _fit_count(quest_level: int) -> int:
	return campaign.fit_count(quest_level)


## 恢复出发准备屏的补给包（M116）。
##
## 存过就用存档那份；没存过（新档 / 旧档）才回退到保底包。
## 只保留还认识的行 —— 补给表删过条目的话，旧档里会有已经不存在的 id。
func _restore_prep_pack() -> Dictionary:
	var d: Dictionary = _default_prep_pack()
	if campaign == null or campaign.supply_pack.is_empty():
		return d
	for k in campaign.supply_pack.keys():
		if d.has(str(k)):
			d[str(k)] = int(campaign.supply_pack[k])
	return d


## 把名单从「内存 → 存档 → 默认」三层兜底里取出来，供**修改**用。
##
## 只读展示可以用 `_is_deployed` 现算，但一改就得有一份真的数组在手上，
## 否则「显示 4 个人、改完发现名单是空的」。
func _ensure_party() -> void:
	if not _prep_party.is_empty() or campaign == null:
		return
	if not campaign.party_ids.is_empty():
		_prep_party = campaign.party_ids.duplicate()
	else:
		_prep_party = _party_restore(_prep_level)


## 名册页直接上下阵（M128）。每条拒绝都要说清原因 ——
## 「点了没反应」比「点不动」糟得多。
func _toggle_deploy(hid: String) -> void:
	if campaign == null:
		return
	_ensure_party()
	var row: Dictionary = campaign.hero(hid)
	if not bool(row.get("alive", false)):
		_flash_msg("他已经阵亡了 —— 去马车复活")
		return
	if campaign.busy_of(hid) > 0:
		_flash_msg("他在修养（还剩 %d 周），这周不能出征" % campaign.busy_of(hid))
		return
	if _prep_party.has(hid):
		if _prep_party.size() <= 1:
			_flash_msg("至少要留一个人")
			return
		_prep_party.erase(hid)
		_flash_msg("%s 下阵" % _hero_label(hid))
	elif _prep_party.size() >= Campaign.PARTY_MAX:
		_flash_msg("出征最多 %d 人 —— 先下阵一个" % Campaign.PARTY_MAX)
		return
	else:
		_prep_party.append(hid)
		_flash_msg("%s 上阵" % _hero_label(hid))
	_party_persist()
	queue_redraw()


## 这个人在不在本趟阵容里（M127）。
##
## 三层兜底，和名册条的取法保持一致：内存名单 → 存档名单 → 能出征的前四个。
## 只用 `_prep_party` 的话，直接从名册页进来（没经过城镇）时它是空的，
## 所有人都被判成「没上阵」——而那时左上角还写着「名册 4 人」。
func _is_deployed(hid: String) -> bool:
	if campaign == null:
		return false
	if not _prep_party.is_empty():
		return _prep_party.has(hid)
	if not campaign.party_ids.is_empty():
		return campaign.party_ids.has(hid)
	return campaign.selectable_ids().slice(0, Campaign.PARTY_MAX).has(hid)


## 恢复玩家的出战名单（M114）。
##
## 优先用存档里的 `campaign.party_ids`；只有它为空（从没定过）才现算。
## 存档里的人会被过滤：名册里没了、死了、这周在建筑里 —— 这三种都不能出征。
## 过滤后只要还剩一个就用它，不自动补满：玩家少一个人是玩家自己的选择。
func _party_restore(level: int) -> Array:
	var out: Array = []
	if campaign != null:
		for hv in campaign.party_ids:
			var k2: String = str(hv)
			if not campaign.roster.has(k2):
				continue
			if not bool((campaign.roster[k2] as Dictionary).get("alive", false)):
				continue
			if campaign.busy_of(k2) > 0:
				continue
			if out.has(k2):
				continue
			out.append(k2)
			if out.size() >= Campaign.PARTY_MAX:
				break
	if out.is_empty():
		return _party_for(level)
	return out


## 把「进行中的这趟远征」写进存档（M116）。
##
## 战斗不存（见 `Expedition.to_save_dict` 的注释）：切后台时若正在打，
## 恢复到战斗开始前的地图状态，这一场重打。
func _exp_persist() -> void:
	if campaign == null:
		return
	if exp == null or exp.ended:
		campaign.expedition_run = {}
	else:
		var snap: Dictionary = exp.to_save_dict()
		# 记下「切出去时停在哪一屏」（M117）。
		# 只存远征数据的话，回来只能落在城镇、让玩家再点一次「继续」——
		# 那不是继续，那是重新进入。玩家按 Home 键回个消息，回来应该在原地。
		snap["ui_state"] = _state
		snap["room"] = {
			"step": _room_step.duplicate(true), "phase": _room_phase,
			"kind": _room_kind, "room": _room_room, "lines": _room_lines.duplicate(),
		}
		campaign.expedition_run = snap
	campaign.save()


## 从存档恢复上一次没打完的远征（M116）。
func _resume_expedition() -> void:
	if campaign == null or db == null or campaign.expedition_run.is_empty():
		return
	var e: Expedition = Expedition.new()
	e.db = db
	if not e.from_save_dict(campaign.expedition_run):
		_flash_msg("存档里的远征读不出来，只能重新出发")
		return
	exp = e
	_dungeon = e.dungeon
	_size = e.size_name
	_level = e.dungeon_level
	# 界面状态全部重置：这些都是「上一场」的残留，带进恢复后的远征会直接错乱
	_battle = null
	_ev_pos = 0
	_order_ids = []
	_order_cur = -1
	_pending = {}
	_options = []
	_room_step = {}
	_room_battle = false
	_summoned_uids.clear()
	_step_timer = 0.0
	_log.clear()
	_add_log("继续上一次远征：第 %d 步 · 光照 %.0f · 补给 火把 %d / 口粮 %d" % [
		exp.step_index, exp.light, exp.torch, exp.food], DdTheme.OK)
	# 回到切出去时那一屏（M117）。战斗是唯一回不去的（见 `_exp_persist`），
	# 那种情况退回地图 —— 这一场重打，但整趟还在。
	var us: int = int(campaign.expedition_run.get("ui_state", S_MAP))
	# 战斗（M118）：有快照就原地接着打，从这一回合开头。
	# 重建走一遍 `exp.resume_battle()`，装配逻辑和正常开战完全一致。
	var bs: Dictionary = campaign.expedition_run.get("battle", {})
	if us == S_BATTLE and not bs.is_empty():
		var rb: Battle = exp.resume_battle(bs)
		if rb != null:
			_battle = rb
			_battle.decision_provider = func(_b: Battle, _a: Combatant) -> Dictionary: return {}
			_battle_no += 1
			_battle_corridor = false
			_summoned_uids.clear()
			_order_ids = []
			_order_cur = -1
			_ev_pos = 0
			_state = S_BATTLE
			queue_redraw()
			return
	if us == S_ROOM:
		var rd: Dictionary = campaign.expedition_run.get("room", {})
		_room_step = (rd.get("step", {}) as Dictionary).duplicate(true)
		_room_phase = int(rd.get("phase", 0))
		_room_kind = str(rd.get("kind", ""))
		_room_room = int(rd.get("room", -1))
		_room_lines = (rd.get("lines", []) as Array).duplicate()
		# 卡背后没有地图可垫（M80 之后地图是子节点），但房间卡本身能正常显示
		_state = S_ROOM if not _room_step.is_empty() or _room_phase == 1 else S_MAP
	else:
		_state = S_MAP
	queue_redraw()


## 把当前出战名单写回存档（M114）。
##
## 名单原来只活在界面变量里，切后台被系统回收 = 白改。现在每一次
## 「上阵/下阵」都落盘：宁可多写几次存档，也不要让玩家的选择凭空消失。
func _party_persist() -> void:
	if campaign == null:
		return
	campaign.party_ids = _prep_party.duplicate()
	campaign.save()


## 默认出战名单：够格的人里，**最能打的那 4 个**（M27）。
##
## 不能直接用 `Campaign.default_party()`——它不知道这一趟打几级。
## 也不能「按名册顺序取前 4」：名册顺序是加入顺序，和强度无关。
## 名册扩到 15 人之后，按顺序取会默认派上刚到手的 4 个 1 级新人，
## 而后面明明坐着一排 4 级老将——玩家每次都要手动改，那就等于没有默认值。
func _party_for(level: int) -> Array:
	var cands: Array = []
	for hid in campaign.selectable_ids():
		if campaign.can_join(str(hid), level):
			cands.append(str(hid))
	return _sort_by_power(cands).slice(0, mini(Campaign.PARTY_MAX, cands.size()))


## 按「等级 → 装备阶」降序。
##
## 准备屏的列表和默认出战名单**必须用同一个序**：两边不一致的话，
## 玩家会看到「前两行一个勾都没有，最后一行全勾上」，第一反应是选中逻辑坏了。
func _sort_by_power(arr: Array) -> Array:
	var out: Array = arr.duplicate()
	out.sort_custom(func(a: String, b: String) -> bool:
		var la: int = campaign.resolve_of(a)
		var lb: int = campaign.resolve_of(b)
		if la != lb:
			return la > lb
		return campaign.gear_of(a) > campaign.gear_of(b))
	return out


## 城镇名册的一张卡（M27，112 高）。
##
## 从 240 高压缩过来的：名册要能显示 15 个人，一行大卡放不下。
## 砍掉的是「生命 / 护甲 / 闪避」那一块——那些在铁匠铺面板里有，
## 而城镇屏真正要回答的只有四件事：谁在、几级、压力多少、这周忙不忙。
func _draw_hero_tile(hid: String, r: Rect2) -> void:
	var row: Dictionary = campaign.hero(hid)
	var alive: bool = bool(row.get("alive", false))
	_panel(r)
	draw_rect(Rect2(r.position, Vector2(r.size.x, 3)),
		DdTheme.PARTY if alive else Color("#3a3a3a"))

	# 头像（M40）：名册里「这是谁」应该一眼看出来，而不是读四个字。
	# 36px 的方形格放在左上，文字列整体右移 42。
	# 卡片只有 144 宽，所以名字之外最长的「要 Lv2 才能升装备」也一并缩短了。
	var tx: float = r.position.x + 10.0
	var portrait: Texture2D = _art.texture_of(campaign.def_of(hid))
	if portrait != null:
		var ps: float = 32.0
		var pr := Rect2(r.position.x + 7.0, r.position.y + 13.0, ps, ps)
		var ptint: Color = Color(1, 1, 1, 1) if alive else Color(0.5, 0.5, 0.5, 0.6)
		draw_texture_rect(portrait, pr, false, ptint)
		tx = r.position.x + 46.0

	# 名字最长四字（瘟疫医生），13px 约 52px
	var busy: int = campaign.busy_of(hid)
	# 忙的人名字降一档（M94）：原来他和空闲的人长得一模一样，
	# 只有右上角一个小沙漏，玩家扫一眼分不出「这周谁能出征」。
	_text(Vector2(tx, r.position.y + 22), _hero_label(hid), DdTheme.FONT_BD,
		DdTheme.TEXT if (alive and busy <= 0) else DdTheme.DIM)

	# 忙要单独标：名册里「忙」和「阵亡」看起来一样（都是不能出征），
	# 但一个是等几周、一个是花钱重招。不区分玩家会点进去骂人。
	#
	# M63：改成「沙漏图标 + 周数」。卡片 150 宽、右上只剩 52px，
	# 「忙 2 周」四个字正好占满，任何再长一点的文案都会顶掉名字；
	# 图标之后只剩 12px，数字怎么涨都不会挤。
	if alive and busy > 0:
		var bt_s: String = str(busy)
		var bt_w: float = _font.get_string_size(bt_s, HORIZONTAL_ALIGNMENT_LEFT, -1,
			DdTheme.FONT_TAG).x
		if _ico("icon_busy") != null:
			var bx0: float = r.position.x + r.size.x - 10.0 - bt_w - 17.0
			_draw_ico("icon_busy", Vector2(bx0, r.position.y + 9.0), 15.0,
				Color(1.15, 1.15, 1.15, 1))
			_text(Vector2(bx0 + 17.0, r.position.y + 22.0), bt_s, DdTheme.FONT_TAG, DdTheme.WARN)
		else:
			_text(Vector2(r.position.x + r.size.x - 74.0, r.position.y + 22), "忙 %d 周" % busy, DdTheme.FONT_TAG, DdTheme.WARN, HORIZONTAL_ALIGNMENT_RIGHT, 64)

	_text(Vector2(tx, r.position.y + 40),
		"Lv%d · 装备 %d 阶" % [campaign.resolve_of(hid), campaign.gear_of(hid)], DdTheme.FONT_SM, DdTheme.DIM)

	# 职业纹章（M61）：贴在头像正下方那一列。
	# 卡片左侧 x+7~x+40 这段，头像只占 y+13~y+45，下面一直空着 ——
	# 正好是唯一不压文字的位置。22px 在 150 宽的卡里也不会显得挤。
	var job: String = "job_" + campaign.def_of(hid)
	if _ico(job) != null:
		_draw_ico(job, Vector2(r.position.x + 12.0, r.position.y + 56.0), 22.0,
			Color(1, 1, 1, 1) if alive else Color(0.55, 0.55, 0.55, 0.75))

	var st: float = float(row.get("stress", 0.0))
	_bar(Rect2(tx, r.position.y + 48, r.position.x + r.size.x - 10.0 - tx, 4),
		st / 200.0, DdTheme.STRESS, DdTheme.STRESS_TRACK)
	# 压力 / 疾病 / 怪癖（M62）：图标 + 数字，替掉「压力 0」「病 1 · 负 2」。
	#
	# 这两行原来是纯文字，一行就吃掉 90px 宽、两行 30px 高，
	# 而卡片只有 150×184 —— 换成 15px 图标之后宽度省一半，
	# 压力值也终于能和图标并排（原来「压力 0」是三个字）。
	var px: float = tx
	if _ico("icon_stress") != null:
		px = _draw_ico("icon_stress", Vector2(tx, r.position.y + 51.0), 16.0,
			Color(1.2, 1.2, 1.2, 1)) + 4.0
	_text(Vector2(px, r.position.y + 64), "%.0f" % st, DdTheme.FONT_TAG,
		DdTheme.STRESS if st >= 100.0 else DdTheme.FAINT)

	# 病 / 负面怪癖：有病整行转警告色，那是唯一需要立刻去疗养院的状态。
	# 两者可能同时存在，横着并排；图标本身就说明了「病」和「怪癖」。
	var dn: int = campaign.diseases_of(hid).size()
	var qn: int = campaign.negative_quirks_of(hid).size()
	var bx: float = tx
	if dn > 0:
		if _ico("icon_disease") != null:
			bx = _draw_ico("icon_disease", Vector2(bx, r.position.y + 69.0), 16.0,
				Color(1.2, 1.2, 1.2, 1)) + 3.0
		_text(Vector2(bx, r.position.y + 82), str(dn), DdTheme.FONT_TAG, DdTheme.WARN)
		bx += _font.get_string_size(str(dn), HORIZONTAL_ALIGNMENT_LEFT, -1, DdTheme.FONT_TAG).x + 10.0
	if qn > 0:
		if _ico("icon_quirk") != null:
			bx = _draw_ico("icon_quirk", Vector2(bx, r.position.y + 69.0), 16.0,
				Color(1.2, 1.2, 1.2, 1)) + 3.0
		_text(Vector2(bx, r.position.y + 82), str(qn), DdTheme.FONT_TAG,
			DdTheme.WARN if dn > 0 else DdTheme.FAINT)

	# M58：名册卡改成可点（点开看这个人的完整状态）。
	# 它原来只是展示，但外观和建筑卡一样，玩家会去点 —— 「点了没反应」
	# 比「多一个详情」糟得多。
	_hit_overlay(r, "hero_info:" + hid)
	_add_hit(r, "hero_info:" + hid)

	# 最后一行：这张卡现在「卡在哪」。三种状态互斥，只写一条。
	if not alive:
		_text(Vector2(tx, r.position.y + 98), "已阵亡", DdTheme.FONT_TAG, DdTheme.WARN)
	elif campaign.gear_of(hid) >= Campaign.MAX_GEAR:
		_text(Vector2(tx, r.position.y + 98), "已满阶", DdTheme.FONT_TAG, DdTheme.OK)
	elif campaign.upgrade_cost(hid).is_empty():
		_text(Vector2(tx, r.position.y + 98),
			"需 Lv%d 升装备" % (campaign.gear_of(hid) + 2), DdTheme.FONT_TAG, DdTheme.FAINT)
	else:
		_text(Vector2(tx, r.position.y + 98), "铁匠铺可升级", DdTheme.FONT_TAG, DdTheme.FAINT)


# ============================================================
# 地图屏
# ============================================================

func _draw_map() -> void:
	if _supply_open:
		_draw_supply_panel()
		return
	if exp == null:
		return
	var tier: String = ExpeditionCfg.light_tier_name(exp.light)
	_header("远征 · %s · %s %s" % [DdNames.dungeon_name(_dungeon),
		_size_name_of(_size), "Lv%d" % _level],
		"点相邻房间移动    F 点火把    C 休整    Esc 撤退")

	# —— 资源条 ——
	var y: float = 76.0
	# 条从 60 改成 78（M142）：字号放大 1.5 倍后「光照」两个字宽到 64，
	# 正好压在条头上 —— 数字 "65" 也跟着挤。整套一起右移。
	_text(Vector2(24, y), "光照", DdTheme.FONT_MD, DdTheme.DIM)
	_bar(Rect2(78, y - 10, 132, 12), exp.light / 100.0, DdTheme.LIGHT, DdTheme.PANEL_DEEP)
	_text(Vector2(216, y), "%.0f · %s" % [exp.light, tier], DdTheme.FONT_MD, DdTheme.LIGHT if exp.light < 50.0 else DdTheme.DIM)
	# 资源条（M63）：口粮改成「图标 + 数字」，后面几项改成顺序排。
	#
	# 原来六项写死在 316 / 386 / 456 / 524 / 592 这几个 x 上，
	# 750 宽下字与字之间只剩 5px——读起来是一串数字而不是四件东西。
	# 换成流式排布 + 图标省下来的宽度正好把间距撑开。
	var ix: float = 306.0
	if _ico("icon_food") != null:
		ix = _draw_ico("icon_food", Vector2(ix, y - 15.0), 18.0) + 4.0
		var fs_f: String = str(exp.food)
		_text(Vector2(ix, y), fs_f, DdTheme.FONT_MD, DdTheme.FOOD if exp.food > 0 else DdTheme.WARN)
		ix += _font.get_string_size(fs_f, HORIZONTAL_ALIGNMENT_LEFT, -1, DdTheme.FONT_MD).x + 18.0
	else:
		var fs_t: String = "口粮 %d" % exp.food
		_text(Vector2(ix, y), fs_t, DdTheme.FONT_MD, DdTheme.FOOD if exp.food > 0 else DdTheme.WARN)
		ix += _font.get_string_size(fs_t, HORIZONTAL_ALIGNMENT_LEFT, -1, DdTheme.FONT_MD).x + 18.0
	for it in [
			["火把 %d" % exp.torch, DdTheme.LIGHT],
			["铁锹 %d" % exp.shovel, DdTheme.FOOD if exp.shovel <= 0 else DdTheme.DIM],
			["休整 %d" % exp.camps_left, DdTheme.DIM],
			["已探明 %d/%d 间" % [exp.spotted.size(), (exp.map["room_ids"] as Array).size()],
				DdTheme.OK]]:
		var s_it: String = str(it[0])
		_text(Vector2(ix, y), s_it, DdTheme.FONT_MD, it[1] as Color)
		ix += _font.get_string_size(s_it, HORIZONTAL_ALIGNMENT_LEFT, -1, DdTheme.FONT_MD).x + 18.0
	# x 是文本框左边界，要减宽度。原来写的是 `size.x - 24`，于是整行画在屏幕外，
	# 「侦察概率」这个数从加上那天起就没显示过 —— 而它是光照的第三个作用，
	# 玩家一直在为一个看不见的收益做决策。
	_text(Vector2(size.x - 224.0, y), "侦察 %.0f%%" % (exp.scout_chance() * 100.0), DdTheme.FONT_MD,
		DdTheme.OK if exp.scout_chance() >= 0.6 else DdTheme.FAINT,
		HORIZONTAL_ALIGNMENT_RIGHT, 200)

	# 地图区域按接近正方形给：5×5 的图放在宽扁区域里，格子只能按高度定，
	# 于是左右各空一大片。收窄之后格子填满，省下的宽度给右面板。
	# M58 竖屏：网格铺满宽、房间信息面板挪到网格下面、行动按钮贴底。
	#
	# 横屏是「左网格 470 + 右面板 350」并排。竖屏 750 宽放不下并排，
	# 改成纵向四段：网格 → 房间信息 → 队伍条 → 日志条 → 按钮（贴底）。
	var m: float = 24.0
	# 网格高度按「格子接近正方」给：给太多只会在上下留两片黑（网格是居中的），
	# 给太少又会把格子压扁。340 ≈ 4 行 × 85，正好铺满。
	#
	# M63：这一屏同样是一串定高块（156+340+300+140+60+204+44 = 1284），
	# 1334 时只剩 50 的余量，底部安全区一吃就叠：动作区是贴底的，
	# 日志条却按队伍条往下排固定 60 —— 两者**直接重合**，动作按钮盖住日志，
	# 只从按钮缝隙里漏出几个字。所以按差额先压网格（格子居中，矮了只是图小一圈）、
	# 再压房间说明、最后压日志条。
	var grid_h: float = 340.0
	var room_h: float = 300.0
	var log_h: float = 60.0
	# 房间面板按内容取高（M77），省下的纵向空间**全部给地图**：
	# 格子边长是 min(宽/列, 高/行)，高度是瓶颈，多给 100px 格子就大一截。
	if exp != null and exp.map_mode:
		room_h = _room_panel_h()
		grid_h = 340.0 + (300.0 - room_h)
	var over: float = 1284.0 - size.y
	if over > 0.0:
		var cg: float = minf(over, 60.0)
		grid_h -= cg
		over -= cg
	if over > 0.0:
		var cr: float = minf(over, 40.0)
		room_h -= cr
		over -= cr
	if over > 0.0:
		log_h = maxf(36.0, log_h - over)
	# 房间信息在上、地图在下（M76）。
	# 地图是**手指区**：竖屏握持时拇指够得到下半屏，上半屏要抬手。
	# 原来地图在 156~496、房间信息在 506~806，等于把手要点的东西放在最上面、
	# 只需要读的东西放在拇指舒适区，方向正好反了。
	var room_r := Rect2(m, 156.0, size.x - m * 2.0, room_h)
	var grid_r := Rect2(m, room_r.end.y + 10.0, size.x - m * 2.0, grid_h)
	var party_r := Rect2(m, grid_r.end.y + 10.0, size.x - m * 2.0, 140.0)
	var log_r := Rect2(m, party_r.end.y + 10.0, size.x - m * 2.0, log_h)
	_map_banner_y = log_r.position.y
	var act_r := Rect2(m, size.y - 44.0 - 204.0, size.x - m * 2.0, 204.0)
	_map_rect = grid_r       # 拖拽热区（M78）
	_panel(grid_r, DdTheme.PANEL_DEEP)
	# 地图本身交给子节点画（M80）：它带 `clip_contents`，
	# 超出面板的格子会被裁掉，而不是画到面板外面的背景上。
	if _map_layer != null:
		_map_layer.position = grid_r.position
		_map_layer.size = grid_r.size
		# 弹窗 / 补给面板 / 英雄长按浮层开着时**不能** show（M194 / M201）。
		# `_draw()` 开头已经把子节点收起来了，这里原来无条件 `show()`，
		# 一句就把那次 hide 抵消掉 —— 表现是「遮罩画了、格子照样压在弹窗上」，
		# 而且代码看起来两处都对。
		if not (_dlg_open or _supply_open or _hold_shown.begins_with("hero_stat:")):
			_map_layer.show()
			_map_layer.queue_redraw()
	_draw_room_panel(room_r)
	_draw_party_strip(party_r)
	# 「能拖」这件事必须写出来（M185）：拖拽是没有视觉线索的交互，
	# 不写玩家永远不知道；而队伍屏那行提示在地图上根本看不见。
	_text(Vector2(party_r.position.x, party_r.position.y - 6.0),
		"拖动卡片可换站位", DdTheme.FONT_TAG, DdTheme.FAINT,
		HORIZONTAL_ALIGNMENT_LEFT, party_r.size.x)
	_draw_log_bar(log_r)
	# 背包余量（M105）：地图上原来**完全看不到**身上还有几支火把、几份口粮。
	# 而「点火把」「休整」都是消耗品驱动的动作 —— 玩家点下去才知道没了，
	# 这是回合制里最不该出现的信息缺口。放在操作区正上方，和消耗它的按钮同屏。
	_supply_row(Vector2(m, act_r.position.y - 14.0), act_r.size.x)
	_draw_map_actions(act_r)
	_text(Vector2(m, size.y - 12.0),
		"光照决定你能提前看见多远：明亮侦察 +15%、微光 +7.5%，昏暗以下基本摸黑。",
		DdTheme.FONT_TAG, DdTheme.FAINT)
	# 走廊事件横幅（M75）：画在最后，压在网格上，不拦操作
	_draw_map_banner()
	# 事件弹窗（M194）压在最上层：它会清掉底部按钮，所以必须在它们之后调
	_draw_event_dialog()


## 房间图。只画「已经探明」的房间——没探明的连位置都不显示，
## 否则侦察就没有意义了。
## 卡片层的绘制回调（M80）。铺满全屏，坐标和屏幕一致。
func _draw_card_layer() -> void:
	if _state != S_ROOM or exp == null:
		return
	_draw_target = _card_layer
	_draw_room_card()
	_draw_target = null


## 地图层的绘制回调（M80）。用的是子节点局部坐标，`r.position` 恒为 ZERO。
func _draw_map_layer() -> void:
	if exp == null or not exp.map_mode or _map_layer == null:
		return
	_room_hits.clear()
	_draw_grid_map_on(_map_layer, Rect2(Vector2.ZERO, _map_layer.size))
	_draw_target = null


func _draw_grid_map_on(ci: CanvasItem, r: Rect2) -> void:
	# 绘制目标切到地图子节点（M80）。子节点 `clip_contents = true`，
	# 超出面板的部分会被真正裁掉 —— 这是 `_draw()` 唯一能拿到裁剪的办法。
	# 坐标系是子节点局部的：`r.position` 传 ZERO，全部用相对坐标。
	_draw_target = ci
	var m: Dictionary = exp.map
	var grid: Array = m["grid"]
	var rooms: Dictionary = m["rooms"]

	# 视野跟着「已探明的房间」走：只框住已知区域向外扩一格。
	# 固定按整张网格画的话，开局只有两间房却占满一整屏，看着像空页面。
	var minx: int = 999
	var maxx: int = -999
	var miny: int = 999
	var maxy: int = -999
	for id in (m["room_ids"] as Array):
		if not exp.is_room_spotted(int(id)):
			continue
		var p0: Vector2i = (rooms[int(id)] as Dictionary)["pos"]
		minx = mini(minx, p0.x); maxx = maxi(maxx, p0.x)
		miny = mini(miny, p0.y); maxy = maxi(maxy, p0.y)
	if minx > maxx:
		minx = 0; maxx = 0; miny = 0; maxy = 0
	# 扩一格只在**那一圈真有房间**时才做（M79）。
	# 按坐标硬扩会把空地也算进内容尺寸：两行房间被撑成三行，
	# 200×3=600 塞进 424 的面板，屏幕上就只剩半截房间，像画坏了。
	var all_pos: Array = []
	for idp in (m["room_ids"] as Array):
		all_pos.append(((rooms[int(idp)] as Dictionary)["pos"] as Vector2i))
	if minx > 0 and _line_has_pos(all_pos, minx - 1, true):
		minx -= 1
	if maxx < int(grid[0]) - 1 and _line_has_pos(all_pos, maxx + 1, true):
		maxx += 1
	if miny > 0 and _line_has_pos(all_pos, miny - 1, false):
		miny -= 1
	if maxy < int(grid[1]) - 1 and _line_has_pos(all_pos, maxy + 1, false):
		maxy += 1
	var gx0: int = minx
	var gy0: int = miny
	var cols: int = maxx - minx + 1
	var rows: int = maxy - miny + 1

	# 格子尺寸固定（M78）：原来取 `min(宽/列, 高/行)` 让整张图塞进面板，
	# 结果房间多的时候格子被压得很小。现在格子是常量，内容超出面板就靠拖拽看，
	# 房间可以一直保持可读的尺寸。
	var cell: float = MAP_CELL
	var cw: float = cell
	var ch: float = cell
	# 房间要留出走廊中点的位置：徽标半径 8，两边各让 12——
	# 不留的话「陷」会压在房间边框上，看起来像房间自己的标记。
	# 房间框跟着格子上限走（M77）：原来写死 `min(56, cell-30)`，
	# 地图区放大之后格子到 90 了，框还卡在 56 —— 白给的高度看不出效果。
	# 仍要留走廊中点的位置（徽标半径 8，两边各让 12），所以不是满格。
	var bw: float = minf(cell * 0.74, cell - 26.0)
	var bh: float = minf(cell * 0.60, cell - 24.0)
	# 自动居中：进房间时把当前房间摆在面板中间（M78）。
	# 玩家手动拖过之后 `_map_pan_auto` 就关了，直到下一次换房间。
	_map_bounds = Vector2i(cols, rows)
	if _map_pan_auto and rooms.has(exp.current_room):
		var pc: Vector2i = (rooms[exp.current_room] as Dictionary)["pos"]
		_map_pan = Vector2(
			r.size.x * 0.5 - (float(pc.x - gx0) * cell + cell * 0.5),
			r.size.y * 0.5 - (float(pc.y - gy0) * cell + cell * 0.5))
		_map_pan_auto = false
	_map_clamp_pan(r)
	var origin: Vector2 = r.position + _map_pan

	var cell_center := func(gx: int, gy: int) -> Vector2:
		return origin + Vector2(float(gx - gx0) * cw + cw * 0.5, float(gy - gy0) * ch + ch * 0.5)

	# 点阵背景：只给空间感，不泄露房间位置
	for gx in cols:
		for gy in rows:
			_dci().draw_circle(origin + Vector2(float(gx) * cw + cw * 0.5, float(gy) * ch + ch * 0.5),
				1.2, Color(DdTheme.PANEL_EDGE.r, DdTheme.PANEL_EDGE.g, DdTheme.PANEL_EDGE.b, 0.7))

	# 走廊：两端都探明才画
	var edge_i: int = 0
	for e in (m["edges"] as Array):
		var ei_now: int = edge_i
		edge_i += 1
		var ea: int = int(e.a)
		var eb: int = int(e.b)
		if not exp.is_room_spotted(ea) or not exp.is_room_spotted(eb):
			continue
		var pa: Vector2i = (rooms[ea] as Dictionary)["pos"]
		var pb: Vector2i = (rooms[eb] as Dictionary)["pos"]
		var ca: Vector2 = cell_center.call(pa.x, pa.y)
		var cb: Vector2 = cell_center.call(pb.x, pb.y)
		if bool(e.get("walked", false)):
			_dci().draw_line(ca, cb, Color(DdTheme.LIGHT.r, DdTheme.LIGHT.g, DdTheme.LIGHT.b, 0.65), 5.0)
		else:
			# 未走过的走廊画**细实线**而不是虚线（M159）。
			#
			# 虚线在大地图上读作「这条路不通 / 只是示意」—— 而它其实**能走**，
			# 斜着连的对角房间尤其明显（用户就是这么误解的）。
			# 现在两条线只差明暗：走过的亮、没走过的暗，都明确是路。
			_dci().draw_line(ca, cb, Color(DdTheme.DIM.r, DdTheme.DIM.g,
				DdTheme.DIM.b, 0.45), 2.5)
		_edge_badge((ca + cb) * 0.5, exp.edge_kind(ei_now))

	# 房间
	for id in (m["room_ids"] as Array):
		var rid: int = int(id)
		if not exp.is_room_spotted(rid):
			continue
		var rr: Dictionary = rooms[rid]
		var pos: Vector2i = rr["pos"]
		var center: Vector2 = cell_center.call(pos.x, pos.y)
		var box := Rect2(center - Vector2(bw, bh) * 0.5, Vector2(bw, bh))
		var kind: String = str(rr["kind"])
		var visited: bool = bool(rr.get("visited", false))
		var is_cur: bool = rid == exp.current_room
		# 「站在门口、里面还有东西」这一格必须能点（M146）。
		# 原来只有 `movable`（相邻房间）才注册命中区，而玩家自己脚下那间
		# 永远不相邻于自己 —— 于是提示写着「点脚下这一格」，点半天没反应。
		var enterable: bool = is_cur and exp.has_pending_room()
		var movable: bool = _is_adjacent(rid)

		_dci().draw_rect(box, DdTheme.PANEL_HI if visited else DdTheme.PANEL)
		# 房间编号（M73）。右侧面板写「→ 1 号 · 入口房间」「位置 7」，
		# 但地图格子上从来没有编号，玩家对不上说的是哪一间。
		# 放在格子**正上方**：压在图标上会和图案抢位置（第一版就是这样，
		# 数字被打成一小块深色、读不出来），而格子之间本来就有 30px 空隙。
		_text(Vector2(box.position.x, box.position.y - 4.0), str(rid),
			DdTheme.FONT_SM, DdTheme.CRIT if is_cur else DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_CENTER, box.size.x)
		var edge: Color = DdTheme.PANEL_EDGE
		if kind == MapGen.K_GOAL:
			edge = DdTheme.CRIT
		elif kind == MapGen.K_BOSS:
			edge = DdTheme.HP
		elif kind == MapGen.K_BATTLE:
			edge = DdTheme.ENEMY.lightened(0.15)
		elif kind == MapGen.K_CURIO:
			edge = DdTheme.STAT
		_dci().draw_rect(box, edge, false, 1.0)
		if is_cur:
			_dci().draw_rect(box, DdTheme.CRIT, false, 2.0)
		elif movable:
			_dci().draw_rect(box, DdTheme.HEAL, false, 2.0)

		# 打过的战斗房要看得出来（M32）：清剿任务的判据是「图上所有战斗都清掉」，
		# 而房间类型打完仍然是 K_BATTLE。两者画成一个样子的话，
		# 玩家只能靠记忆判断还剩几场——那正好是这一期想消灭的东西。
		# 房间的 step 只在第一次进门时触发，所以「到过」就等于「清过」。
		#
		# 图标本身是彩色的，所以这里只做**压暗**而不是染色：
		# 把 mark_col 乘上去会把六种图案全染成同一个色调，反而更难分。
		var dimmed: bool = kind == MapGen.K_BATTLE and visited
		# 这批图标是墨线稿，石拱门 / 石板 / 宝箱本身就很深，
		# 直接贴在近黑的格子上等于看不见（实测入口那格是一团黑）。
		# 往上乘 >1 提亮，形状不变、对比度回来；打过的战斗房仍然压暗。
		var mark_col: Color = Color(0.40, 0.40, 0.44, 1.0) if dimmed \
			else Color(1.85, 1.78, 1.66, 1.0)
		# 「你在这里」放在框内底部：放框外会压到下一间房
		# 房间里只放图标，居中。
		# 格子实测只有 52×54（bw=min(56, cell-30)、bh=min(cell*0.68, cell-28)），
		# 「图标 + 你在这里四个字」塞不下 —— 之前把图标挤到上半格，
		# 下缘还是被字压掉一截。金框 + 右侧「位置 N」已经说明你在哪间。
		var mark_y: float = box.position.y + box.size.y * 0.42
		var rico: Texture2D = _room_icon(kind)
		if rico != null:
			var isz: float = minf(box.size.x, box.size.y) * 0.80
			_dci().draw_texture_rect(rico, Rect2(box.position.x + (box.size.x - isz) * 0.5,
				mark_y - isz * 0.5, isz, isz), false, mark_col)
		else:
			_text(Vector2(box.position.x, mark_y), _room_mark(kind), DdTheme.FONT_LG,
				DdTheme.TEXT if not dimmed else DdTheme.FAINT,
				HORIZONTAL_ALIGNMENT_CENTER, box.size.x)
		# 「你在这里」只在房间够宽时写：窄格里那四个字会溢出到邻居头上，
		# 而金框本身已经说明了位置，右侧面板也写着「位置 N」。
		# 「你在这里」只在格子真的够高时写：字号提了两档（M72）之后
		# 四个字要 44px 宽、11px 高，78 高的格子里会压在图标下缘。
		# M79 框放大到 170×138 之后，这行字可以再大一号，但得垫一条暗底
		# —— 直接压在房间图上读不出来。
		if is_cur:
			# 印章（M160）：**整个落在格子内部**的右上角。
			#
			# M141 那版半径 21、圆心在框角外 4px，一半压在相邻格上 ——
			# 选中的房间会画一圈外框，两者叠在一起时框会盖住印章
			# （用户原话「有时候是框画在标签前面」）。缩到 r=15 并移进框内，
			# 和任何外框都不会相交。
			var sc := box.position + Vector2(box.size.x - 17.0, 17.0)
			var srad: float = 15.0
			_dci().draw_circle(sc, srad, Color(0.72, 0.15, 0.12, 0.96))
			_dci().draw_arc(sc, srad, 0.0, TAU, 28, Color(0.98, 0.86, 0.55, 1.0), 2.0)
			_dci().draw_arc(sc, 10.5, 0.0, TAU, 22, Color(0.98, 0.86, 0.55, 0.5), 1.2)
			_text(Vector2(sc.x - 15.0, sc.y + 6.0), "你", DdTheme.FONT_TAG,
				Color(1.0, 0.95, 0.82), HORIZONTAL_ALIGNMENT_CENTER, 30.0)
		elif visited:
			# 走过的房间：左上角一枚小实心点（M160）。
			# 和「已探索」文字标签重复，但两者在不同缩放级别起作用 ——
			# 地图缩小时字读不清，一个点还能看见。
			_dci().draw_circle(box.position + Vector2(8.0, 8.0), 5.0,
				Color(0.42, 0.62, 0.38, 0.95))
			_dci().draw_arc(box.position + Vector2(8.0, 8.0), 5.0, 0.0, TAU, 16,
				Color(0.85, 0.92, 0.8, 0.8), 1.2)

		if enterable:
			# 门口待进入：金色描边 + 底部居中「互动」（M155）
			_dci().draw_rect(box, DdTheme.CRIT, false, 3.0)
		# 「已探索」标在**所有走过的房间**上（M159），不只当前那间。
		# 原来只在 `is_cur` 时画，玩家扫一眼地图看不出哪几间已经翻过 ——
		# 而「哪些还没去」正是选下一站时最需要的信息。
		if visited or is_cur:
			var pend: bool = is_cur and (exp.has_pending_room() or _show_interact)
			var lb_txt: String = "互动" if pend else "已探索"
			var lb_col: Color = DdTheme.CRIT if pend else DdTheme.OK
			var lb_w: float = 64.0 if lb_txt == "已探索" else 44.0
			var lb_x: float = box.position.x + (box.size.x - lb_w) * 0.5
			var lb_y: float = box.position.y + box.size.y - 16.0
			# 「互动」做成呼吸式闪烁（M190）+ 缩放呼吸（M192）：
			# 这一格不点，整局就卡在这 —— 它不是一个提示，是一道**闸门**。
			# 静态小标签太容易被略过（用户原话「最好做成动态动画性质，时刻提醒着玩家」）。
			# 相位用绝对时间算，不靠累加 —— 重绘频率变了速度也不会变。
			var lb_bg: Color = Color(0.0, 0.0, 0.0, 0.72)
			var lb_scale: float = 1.0
			var pulse: float = 0.0
			if pend:
				var ph: float = fmod(Time.get_ticks_msec() / 1000.0 * 2.2, TAU)
				# 0→1→0，用 cos 起跳：标签从原大小开始，吸满再落回，
				# 不会出现"一进这一屏就已经是大的"那种跳变。
				pulse = 0.5 - 0.5 * cos(ph)
				lb_bg = Color(0.0, 0.0, 0.0, 0.45 + 0.35 * pulse)
				lb_col = DdTheme.CRIT.lerp(Color(1.0, 0.93, 0.75), pulse)
				# 只放大、不缩小：标签底边贴着房间框，缩到 1.0 以下会离线看不清。
				# 26% 是上限（44×16 → 55×20）：再大就会盖住格子里的图标。
				lb_scale = 1.0 + 0.26 * pulse
			# 缩放必须围绕标签中心，否则放大时右下角会顶出房间框。
			# 用 draw_set_transform 而不是手动改矩形：字是 draw_string 画的，
			# 只改矩形会出现"框变大了、字没变"的两层分离感。
			var lb_c: Vector2 = Vector2(lb_x + lb_w * 0.5, lb_y + 8.0)
			var tf: bool = pend and lb_scale > 1.001
			if tf:
				_dci().draw_set_transform(lb_c, 0.0, Vector2(lb_scale, lb_scale))
			var ox: float = -lb_c.x if tf else 0.0
			var oy: float = -lb_c.y if tf else 0.0
			_dci().draw_rect(Rect2(lb_x + ox, lb_y + oy, lb_w, 16.0), lb_bg)
			if pend:
				# 外圈跟着同一个 pulse 亮，边缘亮起时整格都在"叫"。
				# 线宽也跟着 pulse 走：只变亮度在扫视时不够扎眼，
				# 加粗的那一瞬间整块标签会"顶"出来。
				var ring_a: float = 0.35 + 0.65 * pulse
				_dci().draw_rect(Rect2(lb_x + ox - 2.0, lb_y + oy - 2.0, lb_w + 4.0, 20.0),
					Color(DdTheme.CRIT.r, DdTheme.CRIT.g, DdTheme.CRIT.b, ring_a), false,
					1.5 + 1.0 * pulse)
			_text(Vector2(lb_x + ox, lb_y + oy + 13.0), lb_txt, DdTheme.FONT_TAG, lb_col,
				HORIZONTAL_ALIGNMENT_CENTER, lb_w)
			if tf:
				# 立刻复位：draw_set_transform 是全局的，漏掉会把后面所有格子
				# 一起缩放（症状是"越往下画缩得越小"，而且不报错）。
				_dci().draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

		if movable or enterable:
			# 房间原来完全没反馈：网格里几十个格子，鼠标划过不知道哪个能去。
			_hit_overlay(box, "room:%d" % rid)
			# 命中区存**屏幕坐标**（M80）：`box` 是地图子节点的局部坐标，
			# 而 `_hit_id_at` 拿到的是鼠标的屏幕位置。
			_room_hits.append({"rect": Rect2(box.position + _map_layer.position,
				box.size), "id": rid})


## 走廊中点的内容徽标。
##
## 只有**已侦察**的走廊才有徽标——这一层机制的全部价值就在于
## 「走进去之前知不知道」，在这里免费泄露等于把陷阱变成纯掉血。

	# 方向提示（M81）：内容比面板大时，在对应边缘亮一个小三角。
	# 裁剪之后超出部分一点痕迹都不留，看起来就是「地图到此为止」，
	# 玩家不会想到还能拖。
	var cw_all: float = float(cols) * cell
	var ch_all: float = float(rows) * cell
	var hcol := Color(0.86, 0.72, 0.38, 0.8)
	if _map_pan.x < -2.0:
		_edge_tri(Vector2(r.position.x + 13.0, r.position.y + r.size.y * 0.5),
			Vector2(-1.0, 0.0), hcol)
	if _map_pan.x + cw_all > r.size.x + 2.0:
		_edge_tri(Vector2(r.end.x - 13.0, r.position.y + r.size.y * 0.5),
			Vector2(1.0, 0.0), hcol)
	if _map_pan.y < -2.0:
		_edge_tri(Vector2(r.position.x + r.size.x * 0.5, r.position.y + 13.0),
			Vector2(0.0, -1.0), hcol)
	if _map_pan.y + ch_all > r.size.y + 2.0:
		_edge_tri(Vector2(r.position.x + r.size.x * 0.5, r.end.y - 13.0),
			Vector2(0.0, 1.0), hcol)



func _edge_badge(pos: Vector2, kind: String) -> void:
	if kind.is_empty():
		return
	var col: Color = DdTheme.DIM
	var mark: String = ""
	match kind:
		"trap":
			col = DdTheme.WARN
			mark = "陷"
		"obstacle":
			col = DdTheme.FOOD
			mark = "障"
		"battle":
			col = DdTheme.ENEMY.lightened(0.2)
			mark = "战"
		"hunger":
			col = DdTheme.FOOD
			mark = "饥"
		_:
			return
	var r: float = 8.0
	_dci().draw_circle(pos, r, Color(0.05, 0.05, 0.06, 0.95))
	_dci().draw_arc(pos, r, 0.0, TAU, 20, col, 1.3, true)
	_text(Vector2(pos.x - r, pos.y + 3.5), mark, DdTheme.FONT_TAG, col,
		HORIZONTAL_ALIGNMENT_CENTER, r * 2.0)


## 当前房间能走的每一条走廊：通往哪、路上有什么。
##
## 逐行列出而不是挤成一句——玩家站在房间里要做的判断就是「这几条里选哪条」，
## 一行一条才对得上他的思考顺序。
func _front_rows() -> Array:
	var out: Array = []
	if exp == null:
		return out
	for nb in exp.adjacent():
		var ei: int = int(nb.edge)
		var rid: int = int(nb.room)
		var known: bool = exp.edge_known(ei)
		var k: String = exp.edge_kind(ei)
		var label: String = "路况不明" if not known else "无异常"
		var col: Color = DdTheme.FAINT
		match k:
			"trap":
				label = "有陷阱"
				col = DdTheme.WARN
			"obstacle":
				label = "有障碍"
				col = DdTheme.FOOD
			"battle":
				label = "有敌人"
				col = DdTheme.ENEMY.lightened(0.25)
			"hunger":
				label = "可补给"
				col = DdTheme.OK
		var rk: String = _room_label(rid)
		out.append({"room": rid, "label": label, "col": col, "room_kind": rk})
	return out


## 房间的显示名（M33）。奇物房报**具体奇物**，其它房间报类型。
##
## 为什么要把奇物名提前告诉玩家：收集/激活任务的判据是「找到某一类奇物」，
## 而这一屏原本只会写「奇物房」——玩家得一间间进才知道是不是要找的那个。
## 原版靠美术就能认出来（精灵图摆在那儿），我们没有美术，
## 名字就是它的等价物。信息层级没变：房间类型本来就已探明。
func _room_label(rid: int) -> String:
	var kind: String = exp.room_kind(rid)
	if kind != MapGen.K_CURIO:
		return _kind_name(kind)
	var step: Dictionary = ((exp.map["rooms"][rid] as Dictionary).get("step", {}) as Dictionary)
	var cid: String = str(step.get("curio", ""))
	if cid.is_empty():
		return _kind_name(kind)
	return DdNames.curio_name(cid)


## 房间图标（M64 第十六轮）。六种格子各一枚，替掉原来的单字 `入/出/王/战/奇/·`。
##
## 单字的问题不是不好看，是**读得慢**：一张图上十几个格子，
## 每个都要先认出字再想起含义；图标是直接认形的。
func _room_icon(kind: String) -> Texture2D:
	var key: String = "room_empty"
	match kind:
		MapGen.K_START:
			key = "room_start"
		MapGen.K_GOAL:
			key = "room_goal"
		MapGen.K_BOSS:
			key = "room_boss"
		MapGen.K_BATTLE:
			key = "room_battle"
		MapGen.K_CURIO:
			key = "room_curio"
	return _skin.texture("icons", key)


func _room_mark(kind: String) -> String:
	match kind:
		MapGen.K_START:
			return "入"
		MapGen.K_GOAL:
			return "出"
		MapGen.K_BOSS:
			return "王"
		MapGen.K_BATTLE:
			return "战"
		MapGen.K_CURIO:
			return "奇"
		_:
			return "·"


func _is_adjacent(rid: int) -> bool:
	if exp == null or exp.ended:
		return false
	for nb in exp.adjacent():
		if int(nb.room) == rid:
			return true
	return false


## 右侧信息面板：当前房间 + 操作按钮。
## 相邻房间靠点地图走，面板不重复列一遍——两个入口会让人犹豫点哪个。
## 某一行（或一列）上有没有房间（M79）。视野框扩边之前先问一句。
func _line_has_pos(list: Array, v: int, is_col: bool) -> bool:
	for p in list:
		var pv: Vector2i = p
		if (pv.x if is_col else pv.y) == v:
			return true
	return false


## 地图格子边长（M78 / M79）。
##
## 固定值而不是「按面板大小平摊」：平摊会让房间多的图把格子压到 60 以下，
## 图标和编号全糊。现在格子 230、房间框 170×138 —— 房间图本身是信息的主载体，
## 尺寸要配得上它（参考图上那间屋子差不多就是这个比例）。
## 代价是内容一定超出面板，只能靠拖拽看；这正是拖拽存在的理由。
##
## 220 是「两行刚好」的上限值：视野框通常扩到两行，2×220 = 440，
## 比面板 424 多 16px —— 这 16px 全落在格子四周的留白里（框只有 163×132），
## 所以房间本身不会被切。再往上就会切到图标了。
const MAP_CELL: float = 210.0
##
## 这块内容量差别很大：空房间只有「空房间，没有东西」+ 两三条走廊（约 190），
## 目标房间带任务未完成提示时会到 280 以上。原来一律给 300，
## 空房间下面空掉一百多像素，而那些空白本来可以让地图格子更大。
##
## 算的是**内容高度的上界**，宁多不少：少 2px 会让最后一行贴到边框上。
## 面板边缘的方向小三角（M81）。
func _edge_tri(c: Vector2, dir: Vector2, col: Color) -> void:
	var sz: float = 11.0
	var n := Vector2(-dir.y, dir.x)
	_dci().draw_colored_polygon(PackedVector2Array([
		c + dir * sz,
		c - dir * sz * 0.55 + n * sz * 0.8,
		c - dir * sz * 0.55 - n * sz * 0.8]), col)


## 把平移夹在合法范围（M78）。
##
## 内容比面板大 → 允许在 [面板-内容, 0] 之间拖（拖到边就停）；
## 内容比面板小 → 直接居中，拖也拖不动。
func _map_clamp_pan(r: Rect2) -> void:
	if _map_pan_lock:
		return      # 验收用：`--map-pan=` 直接钉死偏移，跳过夹取
	var cw: float = float(_map_bounds.x) * MAP_CELL
	var chh: float = float(_map_bounds.y) * MAP_CELL
	if cw <= r.size.x:
		_map_pan.x = (r.size.x - cw) * 0.5
	else:
		_map_pan.x = clampf(_map_pan.x, r.size.x - cw, 0.0)
	if chh <= r.size.y:
		_map_pan.y = (r.size.y - chh) * 0.5
	else:
		_map_pan.y = clampf(_map_pan.y, r.size.y - chh, 0.0)


func _room_panel_h() -> float:
	if exp == null or not exp.map_mode:
		return 300.0
	var kind: String = exp.room_kind(exp.current_room)
	var rows: Array = _front_rows()
	var lines_n: int = 1
	if kind == MapGen.K_GOAL and not exp.quest_met():
		lines_n = 2
	var has_qi: bool = not _quest_items_line().is_empty()
	# 起点跟着任务行一起下移（M204）：任务行提到 FONT_MD 之后多占 10px。
	var h: float = (108.0 if has_qi else 98.0) + float(lines_n) * 20.0 + 18.0
	h += float(maxi(1, rows.size())) * 17.0
	h += 30.0     # 「点地图上的绿框走过去」
	h += 26.0     # 底部「出口在 N 步之外」+ 下边距
	return clampf(h, 196.0, 300.0)


func _draw_room_panel(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	var kind: String = exp.room_kind(exp.current_room)
	_text(Vector2(r.position.x + 14, r.position.y + 26), _room_label(exp.current_room), DdTheme.FONT_LG, DdTheme.TEXT)
	_text(Vector2(r.position.x + 14, r.position.y + 48),
		"位置 %d · 已走 %d 步" % [exp.current_room, exp.step_index], DdTheme.FONT_SM, DdTheme.FAINT)
	# 任务目标（M32）：原来这一屏只有「已探明 X/Y 间」这种过程指标，
	# 玩家不知道自己在为哪件事走——清剿和探索在这一屏长得一模一样，
	# 于是「走到出口发现还差两场仗」变成一次纯粹的背刺。
	#
	# 放在右面板而不是顶部状态条：顶条在 1080 宽下已经排到「侦察」，
	# 再塞一句会把两个数叠在一起（缩放窗口就复现）。
	var ql: String = _quest_line()
	if not ql.is_empty():
		# 字号 TAG → MD（M204）：这行是「这一趟到底要干什么、走到哪了」的唯一答案，
		# 原来和「位置 0 · 已走 0 步」一个尺寸，扫一眼根本注意不到
		# —— 用户说的是「完全没有任何进度提示」，其实有，只是看不见。
		var qkind: String = str(exp.quest_goal.get("kind", ""))
		var pr: Vector2i = QuestGoal.progress(exp.quest_goal, exp.quest_state())
		var has_bar: bool = pr.y > 0 and qkind != QuestGoal.KIND_REACH
		_text(Vector2(r.position.x + 14, r.position.y + 68), "任务 " + ql,
			DdTheme.FONT_MD, DdTheme.OK if exp.quest_met() else DdTheme.WARN,
			HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 28.0 - (100.0 if has_bar else 0.0))
		# 进度条（M204）：清剿 3/4、收集 2/3 这类有分母的任务，数字之外再给一条 ——
		# 扫一眼就知道还差多少，而不用逐字读数字。
		if has_bar:
			# 轨道用 `PANEL_EDGE` 而不是 `PANEL_DEEP`（M204）：进度 0/4 时只画轨道，
			# 而深色轨道和面板底几乎同色 —— 看起来像「没画进度条」。
			_bar(Rect2(r.end.x - 110.0, r.position.y + 59.0, 96.0, 9.0),
				clampf(float(pr.x) / float(pr.y), 0.0, 1.0), DdTheme.OK, DdTheme.PANEL_EDGE)
	# 任务物品（M35）：只有带道具的任务才有这一行。
	# 不显示的话玩家无法判断「还剩几次能激活」——而那直接决定要不要绕路。
	var qi: String = _quest_items_line()
	if not qi.is_empty():
		_text(Vector2(r.position.x + 14, r.position.y + 90), qi,
			DdTheme.FONT_TAG, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 28.0)

	# 有物品行时整体下移一行，避免和下面的房间状态挤在一起
	var lines_y: float = r.position.y + (106.0 if not qi.is_empty() else 96.0)
	var lines: Array = []
	if kind == MapGen.K_GOAL:
		# 目标房间不再无条件写「可以离开」（M32）：清剿任务走到出口
		# 只是「到了出口」，图上还有仗没打。这一句是玩家最后一次知道
		# 「现在走会算未完成」的机会，藏起来等于让人白跑一趟。
		if exp.quest_met():
			lines.append(["这里可以离开地牢", DdTheme.CRIT])
		else:
			lines.append(["任务还没完成，现在走算未完成", DdTheme.WARN])
			lines.append([exp.quest_line(), DdTheme.WARN])
	elif kind == MapGen.K_BOSS:
		# 首领会战结束后房间仍然是 K_BOSS，这里按「有没有打完」给两种文案
		if bool(exp.stats.get("boss_killed", false)):
			lines.append(["首领已被击杀，可以离开地牢", DdTheme.OK])
		else:
			lines.append(["首领就在这儿——打不赢别想走", DdTheme.HP])
	elif kind == MapGen.K_START:
		lines.append(["入口。选一个相邻房间开始探索", DdTheme.DIM])
	elif kind == MapGen.K_BATTLE:
		lines.append(["这里的战斗已经结束", DdTheme.DIM])
	elif kind == MapGen.K_CURIO:
		lines.append(["这里的奇物已经搜过", DdTheme.DIM])
	else:
		lines.append(["空房间，没有东西", DdTheme.FAINT])
	var ly: float = lines_y
	for ln in lines:
		_text(Vector2(r.position.x + 14, ly), str(ln[0]), DdTheme.FONT_MD, ln[1])
		ly += 20.0

	# 前路：一行一条走廊。这是玩家此刻真正要做的判断。
	ly += 6.0
	_text(Vector2(r.position.x + 14, ly), "可走的走廊", DdTheme.FONT_MD, DdTheme.DIM)
	ly += 18.0
	var rows: Array = _front_rows()
	if rows.is_empty():
		_text(Vector2(r.position.x + 14, ly), "没有可走的路", DdTheme.FONT_MD, DdTheme.FAINT)
	for row in rows:
		_text(Vector2(r.position.x + 14, ly), "→ %d 号 · %s" % [int(row["room"]), str(row["room_kind"])], DdTheme.FONT_MD, DdTheme.TEXT)
		_text(Vector2(r.position.x + 168, ly), str(row["label"]), DdTheme.FONT_MD, row["col"])
		ly += 17.0
	# 门口有内容时换一句话（M144）：这时玩家站在房间里，要点的**是脚下这一格**，
	# 还写「点绿框走过去」会让他往别处走 —— 而这一间的内容还没触发。
	if exp != null and exp.has_pending_room():
		_text(Vector2(r.position.x + 14, ly + 4), "点脚下这一格 · 进去看看",
			DdTheme.FONT_SM, DdTheme.CRIT)
	else:
		_text(Vector2(r.position.x + 14, ly + 4), "点地图上的绿框走过去",
			DdTheme.FONT_SM, DdTheme.HEAL)

	_text(Vector2(r.position.x + 14, r.position.y + r.size.y - 12),
		"出口在 %d 步之外（按最短路算）" % _dist_to_goal(), DdTheme.FONT_SM, DdTheme.FAINT)


## 远征屏的四个行动（M58）：贴底 2×2 大按钮。
##
## 原来它们挤在右面板里，每个 34 高、340 宽 —— 竖屏下右面板没了，
## 而且那四个按钮是这一屏唯一能按的东西，值得占住拇指落点。
## 一行补给余量（M105）。火把/口粮/铁锹有独立字段，其余在 `supplies` 里。
##
## 只列**大于 0** 的：六个都摆出来时，「解毒剂 0 · 绷带 0」这种空条目
## 比不显示更占地方，还会让人误以为本来就没有。
func _supply_row(pos: Vector2, w: float) -> void:
	if exp == null:
		return
	# 火把 / 铁铲不列：顶部那条光照栏里已经各有一个计数（「火把 4」）。
	# 同一屏重复出现两个数字，玩家会怀疑哪个才是真的。
	# 口粮要列 —— 顶部没有，而「休整」按钮上写的是「口粮 2」，
	# 那个 2 是**这次休整要花几份**，不是库存。
	var bits: Array = []
	if exp.food > 0:
		bits.append("口粮 %d" % exp.food)
	for k in (exp.supplies as Dictionary).keys():
		var n: int = int(exp.supplies[k])
		if n > 0:
			bits.append("%s %d" % [DdNames.supply_name(str(k)), n])
	if bits.is_empty():
		_text(pos, "背包空了", DdTheme.FONT_TAG, DdTheme.WARN)
		return
	_text(pos, "背包　" + " · ".join(bits), DdTheme.FONT_TAG, DdTheme.DIM,
		HORIZONTAL_ALIGNMENT_LEFT, w)


func _draw_map_actions(r: Rect2) -> void:
	if exp == null:
		return
	# 3 列 × 2 行，**中间那一列跨两行**（M194 定版）。
	#
	#   [点火把] [        ] [休整]
	#   [撤退  ] [互动探索] [补给]
	#
	# 中间那颗是这一屏唯一「往前走」的动作，给足两行的高度；
	# 四个功能各占一角，手的落点固定，不用每次找。
	var gap: float = 10.0
	var cw: float = (r.size.x - gap * 2.0) / 3.0
	var rh: float = (r.size.y - gap) * 0.5
	var x0: float = r.position.x
	var y0: float = r.position.y
	var x1: float = x0 + cw + gap
	var x2: float = x1 + cw + gap
	var y1: float = y0 + rh + gap
	# 文案压到 7–9 个字（M194）：三等分后每格只有 ~227px，
	# 「✦ 点火把 +光（剩 4）」这种 13 字会被切掉尾巴 —— 和 M142 同一个坑。
	_add_button(Rect2(x0, y0, cw, rh), "torch",
		"✦ 点火把（%d）" % exp.torch, exp.torch > 0)
	_add_button(Rect2(x2, y0, cw, rh), "camp",
		"⌂ 休整（粮 %d）" % int((exp.cfg.get("camp", {}) as Dictionary).get("food_cost", 2)),
		exp.can_camp())
	# 撤退是**放弃**，用 danger（红）而不是 accent（金）——
	# 金色留给「离开地牢」，那是这一趟的目的地（M142）。
	_add_button(Rect2(x0, y1, cw, rh), "retreat",
		"↩ 撤退 +%.0f 压" % db.rules.retreat_stress, true, true)
	_add_button(Rect2(x2, y1, cw, rh), "supply_open",
		"◈ 补给（%d）" % _supply_kinds(), true)
	# 中间：**有待互动优先**（M203）。
	#
	# 这里原来的顺序是 `at_goal > pending`，而 BOSS 房恰好两条同时成立：
	# 它是终点（at_goal），也有一场**待触发**的首领战（pending）。
	# 于是走到 BOSS 房时，中间那颗直接变成「离开地牢」，
	# 「互动探索」被顶掉 —— 玩家没有任何入口触发首领战，只能点离开，
	# 结算时任务判未完成。用户报的「到了 BOSS 房间没打就赢了」就是这条。
	# **位置永远在**：一会儿有一会儿没有，按钮会跳，玩家记不住在哪儿。
	if exp.has_pending_room() or _show_interact:
		_add_button(Rect2(x1, y0, cw, r.size.y), "enter_room", "▸ 互动探索", true, false, true)
	elif exp.at_goal():
		# 文案要区分任务达没达成：首领还没打时写「完成远征」是在骗人。
		var done: bool = exp.quest_met()
		_add_button(Rect2(x1, y0, cw, r.size.y), "leave",
			"▣ 离开地牢" if done else "▣ 离开（未完成）", true, false, true)
	else:
		_add_button(Rect2(x1, y0, cw, r.size.y), "enter_room", "▸ 互动探索", false)


## 任务目标的一句话（M33）。核心层不认识名字表，所以奇物名在这里补上：
## 收集/激活任务如果只说「在目标奇物上」，玩家不知道要找哪个。
func _quest_line() -> String:
	if exp == null or exp.quest_goal.is_empty():
		return ""
	var cid: String = str(exp.quest_goal.get("curio", ""))
	var base: String = exp.quest_line(DdNames.curio_name(cid) if not cid.is_empty() else "")
	# 探索类任务要给出**距离**（M204）。
	#
	# 清剿 / 收集 / 激活都有分母，`quest_line()` 会带上「3/4」；
	# 而「走到出口」是个二元判据，原来只写四个字 —— 玩家在图上走，
	# 完全不知道自己离出口还有多远，这就是「任务进度看不到」的来源。
	if str(exp.quest_goal.get("kind", "")) == QuestGoal.KIND_REACH:
		var d: int = _dist_to_goal()
		base = "%s（还差 %d 步）" % [base, d] if d > 0 else "%s（已到达）" % base
	# 补上「这玩意儿在哪片区域」（M156）。
	# 原来只写「在『老树』上收集 3 件东西」—— 玩家不知道老树只在荒野出，
	# 跑去遗迹翻一整趟也见不到。奇物的 region 在数据里，界面上没人用。
	if cid.is_empty() or db == null:
		return base
	# 奇物表挂在 `db.curio_lib` 上，`db` 本身没有 `curios` 字段（M156 差点写错）
	var reg: String = ""
	if db.curio_lib != null and db.curio_lib.is_loaded():
		var cdef: Dictionary = (db.curio_lib.curios.get(cid, {}) as Dictionary)
		reg = str(cdef.get("region", ""))
	if reg.is_empty() or reg == "ALL":
		return base
	return "%s（只在%s）" % [base, DdNames.dungeon_name(reg.to_lower())]


## 名册里的人显示成什么（M34）。
##
## 名字表按**职业**建（`DdNames.hero_name`），而屏幕上要区分的**人**。
## 同职业第二个起带罗马数字：`十字军 Ⅱ`。
## 这条后缀来自实例 id 本身（`crusader#2`），所以读档之后仍然一样。
func _hero_label(hid: String) -> String:
	var nm: String = DdNames.hero_name(campaign.def_of(str(hid)))
	var sfx: String = campaign.variant_suffix(str(hid))
	return nm if sfx.is_empty() else "%s %s" % [nm, sfx]


## 任务物品那一行（M35）。没有任务物品时返回空串。
##
## 只报「还剩几件」，不报「总共带了几件」：玩家关心的是还能做几次，
## 而总数已经在任务行里（激活 0/3）说过了。
func _quest_items_line() -> String:
	if exp == null or exp.quest_items.is_empty():
		return ""
	var bits: Array = []
	for id in exp.quest_items.keys():
		var n: int = int(exp.quest_items[id])
		if n <= 0 and not str(id).is_empty():
			# 用完的也列出来（写 ×0），否则玩家会以为「本来就没带」
			bits.append("%s ×0" % DdNames.quest_item_name(str(id)))
			continue
		bits.append("%s ×%d" % [DdNames.quest_item_name(str(id)), n])
	return "任务物品 " + "、".join(bits)


func _hazard_name(kind: String) -> String:
	match kind:
		"trap":
			return "有陷阱"
		"obstacle":
			return "有障碍"
		"battle":
			return "有敌人"
		"hunger":
			return "补给点"
		_:
			return "无异常"


func _kind_name(kind: String) -> String:
	match kind:
		MapGen.K_START:
			return "入口房间"
		MapGen.K_GOAL:
			return "出口房间"
		MapGen.K_BOSS:
			return "首领房间"
		MapGen.K_BATTLE:
			return "战斗房"
		MapGen.K_CURIO:
			return "奇物房"
		_:
			return "空房间"


func _dist_to_goal() -> int:
	if exp == null or not exp.map_mode:
		return 0
	return exp._room_dist(exp.current_room, int(exp.map["goal"]))


## 紧凑队伍条：四条信息（名字、血量、压力、状态）就够，
## 详细数值在战斗界面里看。
func _draw_party_strip(r: Rect2) -> void:
	var n: int = exp.hero_ids.size()
	if n == 0:
		return
	var gap: float = 12.0
	var cw: float = (r.size.x - gap * float(n - 1)) / float(n)
	_strip_rects = []
	for i in n:
		var hid: String = str(exp.hero_ids[i])
		var s: Dictionary = exp.state.get(hid, {})
		var cr := Rect2(r.position.x + float(i) * (cw + gap), r.position.y, cw, r.size.y)
		_strip_rects.append({"id": hid, "rect": cr})
		var dead: bool = bool(s.get("dead", false))
		_panel(cr)
		draw_rect(Rect2(cr.position, Vector2(cr.size.x, 3)),
			Color("#3a3a3a") if dead else DdTheme.PARTY)

		# 头像 + 纹章（M64 第十三轮）：地图上这三四张卡是「谁快死了」的第一眼，
		# 只有名字的话还得逐个读。
		var av_h: float = minf(cr.size.y - 20.0, 92.0)
		var av_r := Rect2(cr.position.x + 10.0, cr.position.y + 10.0, av_h * 0.754, av_h)
		_draw_hero_badge(hid, av_r, not dead)
		var cx2: float = av_r.end.x + 10.0

		# 基线 24 → 32（M142）：FONT_BD 提到 22 之后，基线 24 等于把
		# 字顶顶在卡片上边框上，名字看着像"贴"在框线上。
		_text(Vector2(cx2, cr.position.y + 32), _hero_label(hid), DdTheme.FONT_BD, DdTheme.FAINT if dead else DdTheme.TEXT)
		# 「装备 N」删掉（M149）。它是**装备阶**（0~4 级，铁匠铺升的），
		# 不是「身上有几件装备」—— 字号放大后它又和名字挤在一起，
		# 玩家读到「装备 0」会以为这人光着。阶数在队伍屏和详情里都有。

		var hp_r: float = float(s.get("hp_ratio", 0.0))
		var max_hp: int = _max_hp(hid)
		var bar := Rect2(cx2, cr.position.y + 34, cr.end.x - cx2 - 12, 14)
		_bar(bar, hp_r, _hp_color(true), DdTheme.HP_TRACK)
		_text(Vector2(bar.position.x, bar.position.y + 11),
			"%d / %d" % [int(round(hp_r * float(max_hp))), max_hp], DdTheme.FONT_TAG,
			Color("#f2eee2"), HORIZONTAL_ALIGNMENT_CENTER, bar.size.x)

		var st: float = float(s.get("stress", 0.0))
		# 压力数值（M199）：原来只有一条 8px 的条 + 中点刻度。
		# 条只能回答「离崩溃远不远」，回答不了「现在到底多少」——
		# 而崩溃线是 100、上限是 200 这件事，光看长度更读不出来（用户报的原文）。
		# 数字放左边、条相应缩短：16px 的字压在 8px 的条上会溢出条外。
		var snum_w: float = 26.0
		_text(Vector2(bar.position.x, bar.position.y + 28.0), "%.0f" % st,
			DdTheme.FONT_TAG, DdTheme.STRESS if st >= 100.0 else DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_LEFT, snum_w)
		var sb := Rect2(bar.position.x + snum_w, bar.position.y + 20,
			maxf(10.0, bar.size.x - snum_w), 8)
		_bar(sb, st / 200.0, DdTheme.STRESS, DdTheme.STRESS_TRACK)
		var midx: float = sb.position.x + sb.size.x * 0.5
		draw_line(Vector2(midx, sb.position.y - 1.0), Vector2(midx, sb.end.y + 1.0),
			Color(0.65, 0.60, 0.50, 0.5), 1.0)

		var tags: Array = []
		if dead:
			tags.append("阵亡")
		else:
			if bool(s.get("at_deaths_door", false)):
				tags.append("死门")
			if not str(s.get("affliction", "")).is_empty():
				tags.append("崩溃")
			elif not str(s.get("virtue", "")).is_empty():
				tags.append("美德")
			if bool(s.get("recovering", false)):
				tags.append("恢复期")
		if not tags.is_empty():
			_text(Vector2(sb.position.x, cr.position.y + cr.size.y - 8), " ".join(tags), DdTheme.FONT_TAG, DdTheme.FAINT if dead else DdTheme.WARN)


func _draw_log_panel(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	_text(Vector2(r.position.x + 14, r.position.y + 22), "行程记录", DdTheme.FONT_MD, DdTheme.DIM)
	var line_h: float = 18.0
	var max_lines: int = int((r.size.y - 40.0) / line_h)
	var start: int = maxi(0, _log.size() - max_lines)
	var y: float = r.position.y + 44.0
	for i in range(start, _log.size()):
		var e: Dictionary = _log[i]
		_text(Vector2(r.position.x + 14, y),
			DdTheme.ellipsis(str(e.text), _font, r.size.x - 28.0, 12), DdTheme.FONT_MD, e.color)
		y += line_h


# ============================================================
# 战斗屏
# ============================================================

func _draw_battle() -> void:
	if _battle == null:
		return
	var tier: String = ExpeditionCfg.light_tier_name(exp.light)
	# M70：不再画顶部 header。那条铁牌搬到了两军之间（`_draw_battle_strip`）——
	# 血条上移之后敌人头顶本来就挤，header 压在那儿只会更挤；
	# 而「第几轮 / 光照多少」正好在两军中间，读的时候不用来回找。
	var title: String = "第 %d 场 · 第 %d 轮 · 光照 %.0f（%s）" % [
		maxi(1, _battle_no), _battle.round_index, exp.light, tier]

	if not _fx_pose.is_empty():
		for pu in _battle.party:
			var pc := pu as Combatant
			if not pc.dead:
				_pose[pc.uid] = {"anim": _fx_pose, "t": POSE_TIME * 0.5, "dur": POSE_TIME}
				break

	_draw_battle_bg()

	# 地面线。没有地面线，立绘就是「贴在背景上」，不是「站在地上」。
	# 敌方那条地面线（M45）：有背景之后，一条细线撑不住「他们站在这儿」——
	# 剪影会读成浮在墙前。所以改成 10px 的暗色台面带 + 上沿高光，
	# 像一段比战场更高、更靠后的石台。
	draw_rect(Rect2(0.0, GROUND_ENEMY, size.x, 10.0), Color(0.030, 0.028, 0.026, 0.62))
	draw_line(Vector2(0.0, GROUND_ENEMY), Vector2(size.x, GROUND_ENEMY),
		Color(0.30, 0.27, 0.23, 0.55), 1.0)
	draw_line(Vector2(30.0, GROUND_PARTY), Vector2(size.x - 30.0, GROUND_PARTY),
		Color(0.24, 0.22, 0.19, 0.9), 1.0)
	# 两军之间原来画一条交战线虚线（M45）。M65 起那块空档让给行动序条：
	# 虚线的信息量为零，而「谁先手」是每一轮都要用的信息。

	for u in _battle.enemies:
		var e := u as Combatant
		_draw_unit(e, _anim_x(e, true), GROUND_ENEMY, true)
	for u2 in _battle.party:
		var h := u2 as Combatant
		_draw_unit(h, _anim_x(h, false), GROUND_PARTY, false)

	# —— 技能特效（M57）——
	# 画在单位之后、光照之前：特效要被暗处压暗，那才像「在同一盏灯下」。
	# 放到光照之后会变成「自发光」，在至暗难度里会亮得很假。
	_draw_fx()

	# —— 光照（M44）——
	# 画在单位之后、UI 面板之前：光要能压住人和地面（那才有「范围」），
	# 但不能压住日志和技能按钮（那是界面，不是场景）。
	# 光源放在**我方阵中**（地面线上方 90px），不是屏幕中心也不是两军正中：
	# 火把在队伍手里，敌人本来就该在光圈外。放正中会让两边一样亮，
	# 「光照低」就只剩「整屏变暗」一个读法。
	_draw_lighting(Vector2(_party_focus_x(), GROUND_PARTY - 90.0))

	# 单位状态块画在光照**之后**（M84）：名字/血条/状态字是界面信息，
	# 被那层按亮度铺的暗色压过之后，紫字就看着像半透明了。
	for sl in _slots:
		var su: Combatant = _unit_by_uid(int(sl["uid"]))
		if su != null:
			_draw_unit_status(su, float(sl["cx"]), float(sl["gy"]),
				float(sl["top"]), str(sl["side"]) == "enemy")

	# 屏幕溅血（M57 续）：在光照之后、UI 之前——它是「镜头」层面的东西，
	# 该压在场景上；但盖住技能按钮就会挡操作。
	_draw_fx_overlay()

	# 战斗信息条（M70）：从顶部 header 搬下来，占两军之间那条空档。
	# 和行动序条一样，属于界面，必须画在光照之后。
	_draw_battle_strip(title, "点技能 → 点目标    点单位看状态")
	_draw_party_status()

	# 行动序条（M65）：画在光照之后 —— 它属于界面，被暗处压住就没法读了。
	_draw_order_strip()

	# 遭遇横幅（M65）：进战斗后的头一秒，先告诉玩家「遇见了谁」。
	_draw_encounter_banner()

	# —— 竖屏三段（M58）——
	# 日志摘要条 → 次级操作 → 技能区（压在屏幕最底，拇指落点）。
	# 顺序照 `docs/HUD_PORTRAIT_MOCK.html` 的 M1：技能最高频，所以它在最下面。
	var m: float = 24.0
	# 技能区高度跟着「有几个技能」走：一行 90、两行 180。
	# 固定成 340 的话，只有 4 个技能的职业会留一大片空面板，
	# 而 abomination 这种 7 技能的又要挤 —— 按行数算，两头都不难看。
	# 技能区固定两行（8 格）：所有职业最多 7 个技能，两行一定放得下。
	# 不按实际技能数收缩 —— 那样切人时面板高度会跳，敌方回合还会缩成一条。
	var scl_h: float = 66.0 + 90.0 * 2.0
	# 技能永远贴底（一级热区），操作行与日志条依次往上叠
	var scl := Rect2(m, size.y - 44.0 - scl_h, size.x - m * 2.0, scl_h)
	var act := Rect2(m, scl.position.y - 100.0, size.x - m * 2.0, 92.0)
	var bar := Rect2(m, act.position.y - 52.0, size.x - m * 2.0, 44.0)
	_draw_log_bar(bar)
	_draw_action_row(act)
	_draw_skill_panel(scl)
	_draw_log_float()
	# 单位详情放最后：它是模态的，应该盖住日志、行动序和光照说明。
	_draw_unit_info()
	_text(Vector2(m, size.y - 12.0), "光照影响：怪物伤害 %+.0f%% · 我方受压 %+.0f%%" % [
		exp.light_mods().get("monster_dmg", 0.0) * 100.0,
		exp.light_mods().get("stress_damage", 0.0) * 100.0], DdTheme.FONT_TAG, DdTheme.FAINT)


## 状态键的中文名（M65 续）。数据里 keyStatus 只有这四种，
## 其余未见过的键原样显示 —— 见到英文总比见到空白好。
const STATUS_CN: Dictionary = {
	"tagged": "被标记",
	"poisoned": "中毒",
	"stunned": "眩晕",
	"bleeding": "流血",
}


## 单位的「状态与效果」行（M65 续）。
##
## 三条通道都要走：`buffs`（战斗内临时修正）、`dots`（持续伤害）、
## `statuses`（标记类）。玩家最想知道的「还剩几回合」在 `remaining` 里，
## 而头顶的 4 字标签只写了「DOT×2」。
func _unit_status_rows(u: Combatant) -> Array:
	var out: Array = []
	for b in u.buffs:
		var line: String = _buff_line(b)
		if line.is_empty():
			continue
		out.append({"text": line, "left": int(b.get("remaining", 0))})
	for d in u.dots:
		var kk: String = str(d.get("kind", ""))
		var kind: String = "流血" if kk == "bleed" else (
			"中毒" if (kk == "blight" or kk == "poison") else kk)
		out.append({"text": "%s %d/回合" % [kind, int(d.get("amount", 0))],
			"left": int(d.get("remaining", 0))})
	for k in u.statuses.keys():
		var key: String = str(k)
		# 中毒/流血在 dots 那一路已经报过：数据里是同一机制的两层皮，
		# 两边都写会出现「中毒 3/回合」和「中毒 2 回合」两条打架的条目。
		if key == "poisoned" or key == "bleeding":
			continue
		out.append({"text": str(STATUS_CN.get(key, key)), "left": int(u.statuses[k])})
	return out


## 单位详情浮层（M65 续）。
##
## 战斗中唯一看不到的东西是「这个状态还剩几回合、具体多少」——
## 头顶只有 4 个字的标签（死门 眩晕 DOT×2 崩溃），超过 4 条还会被截断，
## 而排先后手恰恰要算这些。**非瞄准态**点任意单位打开，点同一单位或空白关闭。
func _draw_unit_info() -> void:
	if _info_uid < 0 or _battle == null:
		return
	var u: Combatant = _battle.unit_by_uid(_info_uid)
	if u == null:
		_info_uid = -1
		return
	var rows: Array = _unit_status_rows(u)
	var shown: int = mini(rows.size(), 10)
	# 敌人没有压力条（压力只落在英雄身上），高度和起始位置都要跟着缩 42，
	# 否则敌方详情卡会在血条和「状态与效果」之间空出一大块。
	var stress_h: float = 42.0 if u.is_hero else 0.0
	var h: float = 138.0 + stress_h + float(maxi(1, shown)) * 24.0 \
		+ (24.0 if rows.size() > shown else 0.0)
	var w: float = 620.0
	var r := Rect2((size.x - w) * 0.5, maxf(64.0, (size.y - h) * 0.5 - 30.0), w, h)
	# 模态遮罩：和日志浮层同一套。点空白落进 `_on_click` 的空分支 → 关掉。
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.0, 0.0, 0.42))
	_panel(r, DdTheme.PANEL_DEEP)
	# 顶部一条敌我色：不看名字也能知道这是谁那边的人
	draw_rect(Rect2(r.position, Vector2(r.size.x, 3.0)),
		DdTheme.PARTY if u.is_hero else DdTheme.ENEMY)

	_text(Vector2(r.position.x + 20.0, r.position.y + 36.0),
		DdNames.unit_name(u.def_id), DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(r.position.x + 20.0, r.position.y + 56.0),
		"%d 号位 · %s" % [u.rank + 1, "我方" if u.is_hero else "敌方"],
		DdTheme.FONT_TAG, DdTheme.DIM)

	var bx: float = r.position.x + 20.0
	var bw: float = r.size.x - 40.0
	var by: float = r.position.y + 72.0
	_bar(Rect2(bx, by, bw, 14.0), u.hp_ratio(), _hp_color(u.is_hero), DdTheme.HP_TRACK)
	_text(Vector2(bx + 8.0, by + 11.0), "%d / %d" % [u.hp, u.base_hp],
		DdTheme.FONT_TAG, Color("#f2eee2"))
	if u.is_hero:
		_bar(Rect2(bx, by + 20.0, bw, 6.0), u.stress / 200.0,
			DdTheme.STRESS, DdTheme.STRESS_TRACK)
		# 100 崩溃刻度：压力条唯一的判据就是这条线。不画出来，玩家只能靠记。
		var tx: float = bx + bw * 0.5
		draw_line(Vector2(tx, by + 18.0), Vector2(tx, by + 28.0), DdTheme.DIM, 1.0)
		_text(Vector2(bx, by + 43.0), "压力 %.0f / 200" % u.stress, DdTheme.FONT_TAG,
			DdTheme.STRESS if u.stress >= 100.0 else DdTheme.DIM)

	var y: float = by + 34.0 + stress_h
	_text(Vector2(bx, y), "状态与效果", DdTheme.FONT_TAG, DdTheme.FAINT)
	y += 22.0
	if rows.is_empty():
		_text(Vector2(bx, y + 8.0), "没有任何状态", DdTheme.FONT_BD, DdTheme.FAINT)
	for i in shown:
		var row: Dictionary = rows[i]
		_text(Vector2(bx, y + 8.0), str(row["text"]), DdTheme.FONT_BD, DdTheme.TEXT)
		var left: int = int(row["left"])
		var lt: String = "不限时" if left <= 0 else "%d 回合" % left
		# 右对齐时 x 是**左边界**，必须从 end.x 往回退
		_text(Vector2(r.end.x - 156.0, y + 8.0), lt, DdTheme.FONT_TAG,
			DdTheme.WARN if (left > 0 and left <= 1) else DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_RIGHT, 136.0)
		y += 24.0
	if rows.size() > shown:
		_text(Vector2(bx, y + 8.0), "还有 %d 条…" % (rows.size() - shown),
			DdTheme.FONT_TAG, DdTheme.FAINT)

	_add_button(Rect2(r.end.x - 96.0, r.position.y + 14.0, 76.0, 40.0),
		"info_close", "关闭")


## 战斗信息条（M70）。
##
## 原来这段在页面顶部（`_header`）：一条铁牌 + 左标题 + 右提示。
## 血条搬到头顶之后，敌人那排状态块就贴在铁牌下面，两样东西挤在一起；
## 而「第几轮 / 光照多少 / 点哪儿」本来就和战场中段的关系更近。
##
## 现在放进两军之间的空档（M69 把这条空档拉开到 72px）。
## 两侧各留 24：贴边会读成「另一条地面线」。
## 我方状态一览（M162）：两军之间那条空档原来什么都没画。
##
## 战斗里玩家要判断「这人还能不能打」时，看的是 buff/debuff ——
## 而原来只有把鼠标移到单位身上、或者去翻日志才能知道。
## 现在每个英雄一行，把当前的增益/减益都摆出来：
## `[▲攻 2]` = 攻击增益、还剩 2 回合；红块是减益。
##
## 用文字块而不是图标：`buffs.json` 里 2020 条数据**没有 icon 字段**，
## 临时找图只会出现「一堆长得一样的箭头」。
func _draw_party_status() -> void:
	if _battle == null:
		return
	# 位置（M162 第二版）：第一版放在信息条下方（GROUND_ENEMY+54），
	# 那里正好是**立绘的上半身** —— 四行字直接糊在英雄脸上。
	# 真正的空档是立绘脚下到地面线之间那一段（GROUND_PARTY 往上 120）。
	var row_h: float = 28.0
	# 状态条挪到**立绘下方**（M187）。
	#
	# 原来 `top = GROUND_PARTY - 8 - n*28` —— 四行正好叠在自己人身上
	# （半透明黑条压着腿和血条），而脚下到日志条之间空着 184px 没人用。
	# 用户截图问「这块空地干嘛的」，答案是「没干嘛」，那就让状态条住进去。
	var top: float = GROUND_PARTY + 12.0
	var x0: float = 24.0
	var full_w: float = size.x - 48.0
	for i in _battle.party.size():
		var u: Combatant = _battle.party[i]
		if u.dead:
			continue
		var y: float = top + float(i) * row_h
		var row := Rect2(x0, y, full_w, row_h - 4.0)
		draw_rect(row, Color(0.02, 0.02, 0.026, 0.72))
		draw_rect(row, Color(0.16, 0.15, 0.13, 0.9), false, 1.0)
		# 名字（左 84 宽）+ 当前生命比例的小条
		_text(Vector2(row.position.x + 8.0, row.position.y + 19.0),
			DdNames.hero_name(u.def_id), DdTheme.FONT_TAG, DdTheme.TEXT,
			HORIZONTAL_ALIGNMENT_LEFT, 96.0)
		var hb := Rect2(row.position.x + 106.0, row.position.y + 11.0, 44.0, 8.0)
		draw_rect(hb, DdTheme.HP_TRACK)
		draw_rect(Rect2(hb.position, Vector2(hb.size.x * clampf(u.hp_ratio(), 0.0, 1.0), hb.size.y)),
			DdTheme.HP)
		var tx: float = row.position.x + 158.0
		# 先把 buff 归并再画（M196）。
		#
		# 一次减益往往同时压三条属性（`attack_rating_add` / `damage_low_multiply` /
		# `damage_high_multiply`），`_buff_short` 把三条全映射成「攻」，
		# 于是同一件事被画成三个「▼攻」—— 玩家会以为中了三次。
		# 归并键是「类别 + 增减 + 是否永久」：数值本来就按类别显示，分开列没有信息量。
		var groups: Array = []
		for b in u.buffs:
			var amt: float = float(b.get("amount", 0.0))
			if is_zero_approx(amt):
				continue
			var tag: String = _buff_short(str(b.get("stat_type", "")), str(b.get("stat_sub_type", "")))
			if tag.is_empty():
				continue
			var rem: int = int(b.get("remaining", 0))
			var pos_s: bool = amt > 0.0
			var found: bool = false
			for g in groups:
				if str(g["tag"]) == tag and bool(g["pos"]) == pos_s and int(g["rem"]) == rem:
					found = true
					break
			if not found:
				groups.append({"tag": tag, "pos": pos_s, "rem": rem})
		var drawn: int = 0
		for g in groups:
			if drawn >= 6:
				_text(Vector2(tx, row.position.y + 19.0), "…",
					DdTheme.FONT_TAG, DdTheme.FAINT)
				break
			var rem2: int = int(g["rem"])
			# 0 = 永久（`combatant.tick_round` 里 remaining 0 的条目永不递减）。
			# 原来直接印 "0"，玩家读成「0 回合 / 0 效果」——这是 M195 用户报的原文。
			var rem_txt: String = "永" if rem2 == 0 else str(rem2)
			var bw2: float = 62.0
			var bcol: Color = DdTheme.OK if bool(g["pos"]) else DdTheme.CRIT
			var br2 := Rect2(tx, row.position.y + 4.0, bw2, 18.0)
			draw_rect(br2, Color(bcol.r, bcol.g, bcol.b, 0.16))
			draw_rect(br2, bcol, false, 1.0)
			_text(Vector2(br2.position.x + 2.0, br2.position.y + 14.0),
				"%s%s %s" % ["▲" if bool(g["pos"]) else "▼", str(g["tag"]), rem_txt],
				DdTheme.FONT_TAG, bcol, HORIZONTAL_ALIGNMENT_CENTER, bw2 - 4.0)
			tx += bw2 + 4.0
			drawn += 1
		# 状态（M197）：崩溃/中毒/流血/眩晕/标记原来**完全不进这一栏**，
		# 于是出现「头顶写着崩溃、下面写无状态」的矛盾（用户报的原文）。
		# 状态不分增减，统一按负面配色；未收录的键跳过，别画出看不懂的字。
		for sk in u.statuses.keys():
			if drawn >= 6:
				_text(Vector2(tx, row.position.y + 19.0), "…",
					DdTheme.FONT_TAG, DdTheme.FAINT)
				break
			var sd: int = int(u.statuses[sk])
			if sd <= 0:
				continue
			var st_tag: String = _status_short(str(sk))
			if st_tag.is_empty():
				continue
			var sw: float = 62.0
			var scol: Color = DdTheme.WARN if str(sk) == "tagged" else DdTheme.CRIT
			var sr := Rect2(tx, row.position.y + 4.0, sw, 18.0)
			draw_rect(sr, Color(scol.r, scol.g, scol.b, 0.16))
			draw_rect(sr, scol, false, 1.0)
			_text(Vector2(sr.position.x + 2.0, sr.position.y + 14.0),
				"%s %d" % [st_tag, sd], DdTheme.FONT_TAG, scol,
				HORIZONTAL_ALIGNMENT_CENTER, sw - 4.0)
			tx += sw + 4.0
			drawn += 1
		# 没有状态就写一句「无」—— 空着会让人以为「还没算完」
		if drawn == 0:
			_text(Vector2(tx, row.position.y + 19.0), "无状态",
				DdTheme.FONT_TAG, DdTheme.FAINT)


## 血条颜色（M197）：我方绿、敌方红。
##
## 原来全场一律 `DdTheme.HP`（红）。战斗里两边的血条长得一样，
## 扫一眼分不清「这条快空了的是我的人还是它」；用治疗技能点队友时更别扭 ——
## 目标列表上全是红条，看起来像在打自己人。
static func _hp_color(is_hero: bool) -> Color:
	return DdTheme.OK if is_hero else DdTheme.HP


## 状态键 → 单字（M197）。
##
## 只收游戏里真实出现过的四个（`data/*.json` 的 `keyStatus` 全量扫描结果：
## bleeding / poisoned / stunned / tagged）。未收录的返回空、跳过绘制 ——
## 硬翻成「异」会让玩家以为是同一种状态，比不显示更误导。
static func _status_short(k: String) -> String:
	match k:
		"bleeding":
			return "血"
		"poisoned":
			return "毒"
		"stunned":
			return "晕"
		"tagged":
			return "标"
		_:
			return ""


## buff 的 `stat_type` → 两个字的缩写（M162）。
func _buff_short(t: String, sub: String = "") -> String:
	# **`combat_stat_add` / `combat_stat_multiply` 是容器，真属性在 `stat_sub_type`**（M191）。
	#
	# 原来只按 `stat_type` 分支，于是这两种（战斗里绝大多 buff 都是它们，
	# 技能写的 `attack_rating_add` / `damage_low_multiply` 最后都归一到这里）
	# 全都匹配不上、`continue` 掉 —— 界面上就永远显示「无状态」，
	# 而玩家明明中了一堆减益。用户报的就是这个。
	if t == "combat_stat_add" or t == "combat_stat_multiply":
		return _buff_short(sub)
	# 用 if/elif 而不是 match：`match` 的多个 pattern 必须写在同一行，
	# 而这十来个分类竖着排更好读（GDScript 的跨行 pattern 会直接 Parse Error）。
	if t in ["attack_rating", "damage_percent", "damage_low", "damage_high"]:
		return "攻"
	if t in ["defense_rating", "protection"]:
		return "防"
	if t in ["hit_chance", "accuracy"]:
		return "准"
	if t in ["crit_chance", "crit"]:
		return "暴"
	if t in ["dodge", "evasion"]:
		return "闪"
	if t == "speed":
		return "速"
	if t in ["heal_percent", "heal"]:
		return "疗"
	if t in ["stress_percent", "stress_dmg"]:
		return "压"
	if t in ["stun_resist", "blight_resist", "bleed_resist", "disease_resist",
			"move_resist", "debuff_resist"]:
		return "抗"
	return ""


func _draw_battle_strip(title: String, hint: String) -> void:
	var y: float = GROUND_ENEMY + 4.0
	# 44 而不是 54（第一版）：54 加上我方状态块之后，两军之间像叠了两块黑牌，
	# 反而更分不清谁是谁的。薄一点、离下面留 28px，读起来是「一条分隔带」。
	var h: float = 44.0
	var r := Rect2(24.0, y, size.x - 48.0, h)
	draw_rect(r, Color(0.028, 0.029, 0.034, 0.86))
	# 只留上沿一条暗金：下沿再画黑线会把它和下面那块状态区连成一片
	draw_line(Vector2(r.position.x, y), Vector2(r.end.x, y),
		Color(0.26, 0.21, 0.13), 1.0)
	_text(Vector2(r.position.x + 16.0, y + 28.0), title, DdTheme.FONT_BD, DdTheme.TEXT)
	# 右对齐时 x 是**左边界**，从 end 往回退才不会画到屏幕外
	_text(Vector2(r.end.x - 436.0, y + 27.0), hint, DdTheme.FONT_TAG,
		DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 420.0)


## 行动序条（M65）。
##
## 规则层每轮都会 emit `{"t":"order","ids":[...]}`（battle.gd 的 begin_round），
## 但界面从来没消费过 —— 于是「谁先手」只能靠猜：
## 不知道奶妈会不会在自己之前被打死，也不知道该抢先集火哪一只。
## DD 的战斗节奏基本是这条带子撑起来的，而数据一直是现成的。
##
## 位置在两军之间的空档（敌方地面线 → 我方立绘头顶）。
## 那块地方原来画一条交战线虚线，信息量为零。
func _draw_order_strip() -> void:
	if _battle == null or _order_ids.is_empty():
		return
	var n: int = _order_ids.size()
	var cell: float = 36.0
	var gap: float = 5.0
	var total: float = float(n) * cell + float(maxi(0, n - 1)) * gap
	var x0: float = (size.x - total) * 0.5
	# 位置（M88）：挪到**屏幕最上方**。
	#
	# 原来放在我方血条和日志条之间（GROUND_PARTY + 64 ≈ 716）——那正好是
	# 屏幕中下、视线最常停留的一块，一排「谁先手」占着它太浪费。
	# 上面这条是真空的：敌方立绘顶在 GROUND_ENEMY-SPRITE_H = 108，
	# 名字基线在 82，所以 20~56 谁也挡不住。
	# 标题也去掉了：这里的纵向空间只够一条带子，而带子本身已经够直观。
	var y0: float = 20.0
	draw_rect(Rect2(x0 - 8.0, y0 - 4.0, total + 16.0, cell + 8.0),
		Color(0.025, 0.025, 0.028, 0.74))
	for i in n:
		var u2: Combatant = _battle.unit_by_uid(int(_order_ids[i]))
		if u2 == null:
			continue
		var cr := Rect2(x0 + float(i) * (cell + gap), y0, cell, cell)
		var done: bool = i < _order_cur
		var here: bool = i == _order_cur
		var base: Color = DdTheme.PARTY if u2.is_hero else DdTheme.ENEMY
		var alpha: float = 0.10 if (done or u2.dead) else (0.52 if here else 0.32)
		draw_rect(cr, Color(base.r, base.g, base.b, alpha))
		draw_rect(cr, DdTheme.CRIT if here else DdTheme.PANEL_EDGE, false,
			2.0 if here else 1.0)
		var txt: Color = DdTheme.FAINT if (done or u2.dead) else (
			DdTheme.CRIT if here else DdTheme.TEXT)
		_text(Vector2(cr.position.x, cr.position.y + 24.0),
			DdNames.unit_name(u2.def_id).substr(0, 1), DdTheme.FONT_BD, txt,
			HORIZONTAL_ALIGNMENT_CENTER, cell)
		if done:
			# 已出手的人划一道：不划的话「轮到谁」和「谁打完了」读不出来
			draw_line(Vector2(cr.position.x + 7.0, cr.position.y + cell - 7.0),
				Vector2(cr.end.x - 7.0, cr.position.y + 7.0), Color(0, 0, 0, 0.6), 2.0)
		if u2.dead:
			_text(Vector2(cr.position.x, cr.position.y + 24.0), "×",
				DdTheme.FONT_BD, DdTheme.WARN, HORIZONTAL_ALIGNMENT_CENTER, cell)


## 遭遇横幅（M65）：进战斗后的头一秒。
##
## 以前从地图切战斗是硬切，唯一的解释是日志里一行【遭遇】——
## 而那行字在屏幕最下方的摘要条里，一进战斗就被技能面板顶掉了。
## 压得很淡、位置压在 header 下面：它只是「报幕」，不该挡住敌人。
func _draw_encounter_banner() -> void:
	if _banner_t <= 0.0 or _battle == null:
		return
	var a: float = clampf(_banner_t / 0.45, 0.0, 1.0)   # 最后 0.45 秒淡出
	var names: Array = []
	for it in _battle.enemies:
		var c := it as Combatant
		if not c.dead:
			names.append(DdNames.monster_name(c.def_id))
	if names.is_empty():
		return
	# 位置（M68）：两军之间那条空档在 M68 之后被我方头顶状态块占了一半
	# （360~414），所以报幕改到**战场中段**（敌人剪影上）：压 1.7 秒，
	# 背景是深色剪影，字反而最清楚。原来在 y=52，正好盖住敌方那排血条。
	var y: float = 214.0
	# 74 而不是 58（M102）：加了「走廊遭遇 / 房间遭遇」标题之后是**三行**
	# （标题 / 怪物名 / 惊袭提示），58 高会把最后一行裁掉一半。
	draw_rect(Rect2(0.0, y, size.x, 74.0), Color(0.02, 0.02, 0.022, 0.82 * a))
	draw_line(Vector2(0.0, y + 74.0), Vector2(size.x, y + 74.0),
		Color(DdTheme.ENEMY.r, DdTheme.ENEMY.g, DdTheme.ENEMY.b, 0.55 * a), 1.0)
	_text(Vector2(0.0, y + 20.0), "走廊遭遇" if _battle_corridor else "房间遭遇",
		DdTheme.FONT_BD,
		Color(DdTheme.ENEMY.r, DdTheme.ENEMY.g, DdTheme.ENEMY.b, a),
		HORIZONTAL_ALIGNMENT_CENTER, size.x)
	_text(Vector2(0.0, y + 48.0),
		DdTheme.ellipsis("、".join(names), _font, size.x - 60.0, 16),
		DdTheme.FONT_H1, Color(DdTheme.TEXT.r, DdTheme.TEXT.g, DdTheme.TEXT.b, a),
		HORIZONTAL_ALIGNMENT_CENTER, size.x)
	if str(_battle.surprised) == "party":
		_text(Vector2(0.0, y + 66.0), "被惊袭 · 首轮不行动", DdTheme.FONT_TAG,
			Color(DdTheme.WARN.r, DdTheme.WARN.g, DdTheme.WARN.b, a),
			HORIZONTAL_ALIGNMENT_CENTER, size.x)


## 战斗结算卡（M65）。
##
## 存在的理由不是好看，是**给「我赢了」一个落点**。
## 以前打赢只有日志里一行【战果】，0.45 秒后画面已经回到地图：
## 掉了什么、还剩多少血、有没有人进了死门，全靠玩家自己翻流水。
##
## 这一屏只回答两个问题：「拿到了什么」「还能不能再打一场」。
## 不加经验条、不加评级——那些数字在远征结算屏里已经有一份。
func _draw_battle_end() -> void:
	var cx: float = size.x * 0.5
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.014, 0.013, 0.015, 0.94))

	# 竖向居中（M65）：内容自身高约 344（标题 40 + 收获卡 176 + 队伍卡 76 + 间距）。
	# 不居中的话，1334 高的屏幕上会有 800px 纯黑压在卡片下面（第一版就是这样，
	# 整屏像只画了上半页）。按钮仍然贴底 —— 那是拇指的位置。
	var vy: float = maxf(0.0, (size.y - 48.0 - 344.0) * 0.5 - 154.0)
	_text(Vector2(0, 154.0 + vy), "战 斗 胜 利", DdTheme.FONT_DISPLAY, DdTheme.CRIT,
		HORIZONTAL_ALIGNMENT_CENTER, size.x)
	_text(Vector2(0, 192.0 + vy), "%d 轮结束" % int(_be_data.get("rounds", 0)),
		DdTheme.FONT_MD, DdTheme.DIM, HORIZONTAL_ALIGNMENT_CENTER, size.x)

	var gain: Dictionary = _be_data.get("gain", {})
	var rows: Array = []
	if int(gain.get("gold", 0)) > 0:
		rows.append(["金币", "+%d" % int(gain["gold"])])
	for k in (gain.get("heirlooms", {}) as Dictionary).keys():
		rows.append([DdNames.heirloom_name(str(k)),
			"×%d" % int((gain["heirlooms"] as Dictionary)[k])])
	if int(gain.get("trinkets", 0)) > 0:
		rows.append(["饰品", "%d 件" % int(gain["trinkets"])])
	if rows.is_empty():
		rows.append(["战利品", "这一场什么都没有"])

	var card := Rect2(cx - 240.0, 232.0 + vy, 480.0, 72.0 + float(rows.size()) * 26.0)
	_panel(card, DdTheme.PANEL_DEEP)
	_text(Vector2(card.position.x + 24.0, card.position.y + 30.0), "这一场的收获",
		DdTheme.FONT_TAG, DdTheme.FAINT)
	var y: float = card.position.y + 56.0
	for r in rows:
		# 行首图标（M146）：和「这一趟」那块同一套判定 —— 那两块本来就是
		# 同一件事的两种呈现，一块有图标一块没有，看着像两套系统。
		var tx4: float = _reward_icon_x(card.position.x + 24.0, y, str(r[0]))
		_text(Vector2(tx4, y), str(r[0]), DdTheme.FONT_BD, DdTheme.DIM)
		_text(Vector2(card.position.x + 172.0, y), str(r[1]), DdTheme.FONT_BD, DdTheme.TEXT)
		y += 26.0

	# 队伍状态：玩家第二个想知道的是「还能不能再打一场」。
	# 只给「最低血量」，不给逐人明细——那是地图屏 HUD 的活。
	var worst: float = 1.0
	var alive_n: int = 0
	if exp != null:
		for k2 in exp.state.keys():
			var row2: Dictionary = exp.state[k2]
			if bool(row2.get("dead", false)):
				continue
			alive_n += 1
			worst = minf(worst, float(row2.get("hp_ratio", 1.0)))
	var stat := Rect2(cx - 240.0, card.end.y + 14.0, 480.0, 76.0)
	_panel(stat, DdTheme.PANEL)
	_text(Vector2(stat.position.x + 24.0, stat.position.y + 28.0), "队伍",
		DdTheme.FONT_TAG, DdTheme.FAINT)
	_text(Vector2(stat.position.x + 24.0, stat.position.y + 54.0),
		"%d 人存活 · 最低血量 %.0f%%" % [alive_n, worst * 100.0],
		DdTheme.FONT_BD, DdTheme.TEXT)

	var bw: float = 360.0
	_add_button(Rect2(cx - bw * 0.5, size.y - 44.0 - 64.0, bw, 64.0),
		"be_continue", "继续")
	_text(Vector2(0.0, size.y - 60.0), "点继续回到地图", DdTheme.FONT_TAG,
		DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, size.x)


## 战斗背景（M45）。
##
## 背景的底边就是原图的地面线（提取时按 1280:422 裁到地面线为止），
## 所以这里只做两件事：**铺满宽度**、**底边压在我方地面线上**。
## 不做垂直居中——一旦居中，地面线就会随背景比例浮动，角色看起来像在换身高。
##
## 背景本身在提取时已经压暗到 86%，这里不再二次乘色：
## 二次压暗会让 weald（本来就是苔绿+暗）几乎看不见，还会和光照层叠加成一片糊。
func _draw_battle_bg() -> void:
	if not _bg_on or exp == null:
		return
	var region: String = str(exp.dungeon)
	var room: int = int(exp.current_room)
	var tex: Texture2D = _bg.texture(region, room)
	if tex == null:
		return
	if _dev_ui:
		# 换房间要换背景，这件事只能靠打印确认：静态截图看不出「index 有没有真的在变」。
		var tag: String = "%s/%d" % [region, room]
		if tag != _bg_log_key:
			_bg_log_key = tag
			print("[bg] region=%s room=%d 张数=%d -> %s" % [
				region, room, _bg.count_of(region),
				"%d" % (room % _bg.count_of(region)) if room >= 0 else "0"])
	# M70：背景从 y=0 铺起。header 搬走之后顶部不再有铁牌压着，
	# 还从 48 起的话会在最上面留一条纯色黑带。
	var top: float = 0.0
	var mid: float = GROUND_ENEMY
	# M60：出图方交的 bg_battle 本来就是**上下两段**（上半拱门大厅、下半地牢走廊，
	# 中间隔一条黑边）。这个结构反而正好：上半贴敌方区、下半贴我方区，
	# 中缝天然落在两军之间。优先用它，没有才退回 M58 的「横图切半」。
	var bt: Texture2D = _skin.texture("skin", "bg_battle_top")
	var bb: Texture2D = _skin.texture("skin", "bg_battle_bottom")
	if bt != null and bb != null:
		# 下半段一直铺到屏幕底部，不是只铺到 GROUND_PARTY：
		# 652 到日志条之间还有 240px，只铺到地面线会在两军脚下留一条纯黑带。
		# 面板是浮在背景上的，铺满不会有副作用。
		_draw_bg_tex(bt, Rect2(0.0, top, size.x, mid - top))
		_draw_bg_tex(bb, Rect2(0.0, mid, size.x, size.y - mid))
	else:
		# M58：**横图对半切，左右各贴一段**。
		#
		# 原来整张 1280×422 cover 到 750×604：等比例没错，但横向裁掉了 60%，
		# 只看得到画面正中间一条，两侧的房间结构全丢。
		# 把原图从中间竖切：右半（敌人那侧）→ 上方敌方区，
		# 左半（我方那侧）→ 下方我方区。
		_draw_bg_half(tex, Rect2(0.0, top, size.x, mid - top), 1)
		_draw_bg_half(tex, Rect2(0.0, mid, size.x, GROUND_PARTY - mid), 0)
	# 接缝渐隐：以 mid 为中心压一条 40 高的暗带，中间最浓、两头化开 ——
	# 直接画一条等浓度的矩形会在上下各留一道硬边，比接缝本身还显眼。
	for i in 8:
		var t3: float = float(i) / 7.0
		var a3: float = 0.5 * (1.0 - absf(t3 * 2.0 - 1.0))
		draw_rect(Rect2(0.0, mid - 20.0 + 40.0 * t3, size.x, 40.0 / 8.0 + 1.0),
			Color(DdTheme.BG.r, DdTheme.BG.g, DdTheme.BG.b, a3))
	# 雾（M45）：盖一层底色的半透明。
	#
	# 只压暗不够——压暗之后背景的**对比度**还在：骷髅堆、木桶、砖缝仍然清清楚楚，
	# 和前景立绘抢视线。加雾把对比度也压下来，背景才真的退到「后面」。
	# 这比在提取阶段做高斯模糊好：模糊是不可逆的，而雾的浓度可以随时调。
	draw_rect(Rect2(0.0, top, size.x, GROUND_PARTY - top),
		Color(DdTheme.BG.r, DdTheme.BG.g, DdTheme.BG.b, 0.36))
	# 顶栏下沿到背景之间：背景顶边被硬切会留下一条清晰的分界，用 34px 渐隐盖掉。
	for i in 5:
		var t2: float = float(i) / 5.0
		draw_rect(Rect2(0.0, top + 34.0 * t2, size.x, 34.0 / 5.0 + 1.0),
			Color(DdTheme.BG.r, DdTheme.BG.g, DdTheme.BG.b, 0.95 - 0.95 * t2))
	# 地面线以下：背景在 470 处截断，到日志面板（530）之间的 60px 用近黑的纯色接上。
	# 试过 6 段渐隐，反而在衔接处画出一条比背景更亮的横带，像地面被切了一刀。
	draw_rect(Rect2(0.0, GROUND_PARTY, size.x, size.y - GROUND_PARTY),
		Color(0.045, 0.043, 0.042))


## 整图 cover 到目标矩形（M60）：等比、不变形、裁掉多出来的边。
func _draw_bg_tex(tex: Texture2D, dst: Rect2) -> void:
	var ts: Vector2 = tex.get_size()
	if ts.x <= 0.0 or dst.size.y <= 0.0:
		return
	var k: float = maxf(dst.size.x / ts.x, dst.size.y / ts.y)
	var sw: float = dst.size.x / k
	var sh: float = dst.size.y / k
	draw_texture_rect_region(tex, dst,
		Rect2((ts.x - sw) * 0.5, (ts.y - sh) * 0.5, sw, sh))


## 把背景图的一半 cover 到目标矩形里（M58）。
##
## `half` = 0 取左半、1 取右半。先按「铺满目标、等比缩放」算源区域，
## 再在那一半里居中裁 —— 这样两段的比例一致，不会一段扁一段长。
func _draw_bg_half(tex: Texture2D, dst: Rect2, half: int) -> void:
	var ts: Vector2 = tex.get_size()
	var hw: float = ts.x * 0.5
	if hw <= 0.0 or dst.size.y <= 0.0:
		return
	var k: float = maxf(dst.size.x / hw, dst.size.y / ts.y)
	var sw: float = minf(hw, dst.size.x / k)
	var sh: float = minf(ts.y, dst.size.y / k)
	var sx: float = float(half) * hw + (hw - sw) * 0.5
	var sy: float = (ts.y - sh) * 0.5
	# 压暗到 0.62：素材是给「人物站在同一条地面线」的构图用的，
	# 我们的敌人站得更高，背景一清楚就会读成「他浮在半空」。
	draw_texture_rect_region(tex, dst, Rect2(sx, sy, sw, sh),
		Color(0.54, 0.54, 0.58))


## 光照层（M44）：暗角 + 一层暖光。
##
## 两张纹理都铺成**比屏幕大**的矩形：暗角纹理中心透明、边缘全黑，
## 所以「屏幕中心区透出画面、四周逐渐压黑」——CanvasItem 不能挖洞，
## 只能靠「盖一张中间有透明区的图」来模拟。
##
## 半径跟着光照缩，不只是变暗：光照低时「能看见的范围」真的变小，
## 这才和规则层「光照低 → 更容易被偷袭、侦察变差」是同一件事的两面。
func _draw_lighting(center: Vector2) -> void:
	if not _light_on:
		return
	var p: Dictionary = LightLayer.params(_light_vis)
	var dim: float = float(p["dim"])
	if dim > 0.001:
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.012, 0.011, 0.013, dim))
	var r: float = size.x * float(p["radius_k"])
	# 椭圆而不是圆：画面是 16:10 的横构图，正圆会在上下留出大片死黑。
	var ry: float = r * 0.62
	draw_texture_rect(_light.vignette(),
		Rect2(center.x - r, center.y - ry, r * 2.0, ry * 2.0), false,
		Color(1.0, 1.0, 1.0, float(p["vignette"])))
	# 暖光只罩中心一小块（0.46r）。第一版给了 0.74r，结果橙色铺满全屏，
	# 看起来像加了一层滤镜而不是「中间有盏灯」——暖光的**范围**比强度更影响观感。
	var wt: Color = p["warm_tint"]
	draw_texture_rect(_light.warm(),
		Rect2(center.x - r * 0.46, center.y - ry * 0.46, r * 0.92, ry * 0.92), false,
		Color(wt.r, wt.g, wt.b, float(p["warm"])))


## 单位的姿势帧（M38）。优先级：死亡 > 出招（计时内）> 待机。
func _unit_anim(u: Combatant) -> String:
	if u.dead:
		return "dead"
	var p: Dictionary = _pose.get(u.uid, {})
	if float(p.get("t", 0.0)) > 0.0:
		var a: String = str(p.get("anim", ""))
		if not a.is_empty():
			return a
	return "combat"


## 给某个单位挂上「出招姿势」（M38）。0.45 秒后自动回 combat。
##
## 姿势帧名来自数据：`heroes.json` 里每个技能的 `art.anim`（如 `attack_sword`），
## 素材包里有同名文件。两边不用人为对齐，所以换职业/加技能不会漏。
## uid -> 上次发声的时刻（毫秒）。同一只怪 0.25 秒内不重复叫。
var _voice_at: Dictionary = {}
## 上一次「出手咆哮」的时刻。全场限流——四只怪一轮各叫一次会叠成一片。
var _aggro_at: int = -100000
## 已经咆哮过的单位（一场战斗重置一次）。咆哮是登场台词，不是每回合的台词。
var _aggro_done: Dictionary = {}


func _unit_by_uid(uid: int) -> Combatant:
	if _battle == null:
		return null
	for x in _battle.all_units():
		if x.uid == uid:
			return x
	return null


## 某个技能的姿势帧名（`attack_sword` 这种）。出招换帧和命中音都用它。
func _anim_of(uid: int, skill_id: String) -> String:
	if skill_id.is_empty():
		return ""
	var u: Combatant = _unit_by_uid(uid)
	if u == null:
		return ""
	return _art.anim_for_skill(u.def_id, skill_id)


## 放一句敌人语音（M51）。不是敌人、没有对应分组、或者刚叫过 —— 都不出声。
##
## 限流是本函数存在的另一半理由：语音素材每个 1–2 秒，而一场战斗里
## 命中事件密集得多。不限流的话四五只怪会同时在叫，听起来像音效坏了。
func _enemy_voice(uid: int, kind: String, db: float = 0.0) -> void:
	if _sfx == null:
		return
	var u: Combatant = _unit_by_uid(uid)
	if u == null or u.is_hero:
		return
	var now: int = Time.get_ticks_msec()
	if kind == "aggro":
		# 咆哮一场只来一次。第一版是「每次出手都叫」，结果同一只猪连着
		# 三次出手吼了三声，听起来像音效卡在循环里。
		if _aggro_done.has(uid):
			return
		if now - _aggro_at < 800:
			return
		_aggro_done[uid] = true
		_aggro_at = now
	elif now - int(_voice_at.get(uid, -100000)) < 260:
		return
	var slot: String = EnemyVoice.slot(u.def_id, kind)
	if slot.is_empty():
		return
	var used: String = slot
	var played: bool = _sfx.play_variant(slot, EnemyVoice.TAKES, 1.0, db)
	if not played:
		# 这个分组没录这一种叫声（见 EnemyVoice.FALLBACK），换个组补位
		var alt: String = EnemyVoice.fallback_slot(u.def_id, kind)
		if alt.is_empty():
			return
		used = alt
		played = _sfx.play_variant(alt, EnemyVoice.TAKES, 1.0, db)
	if played:
		_voice_at[uid] = now
		if _dev_ui:
			print("[vo] %s %s -> %s" % [u.def_id, kind, used])


func _pose_for_action(uid: int, skill_id: String) -> void:
	if skill_id.is_empty() or _battle == null:
		return
	var u: Combatant = _unit_by_uid(uid)
	if u == null:
		return
	var anim: String = _art.anim_for_skill(u.def_id, skill_id)
	# 即使没有姿势帧也要记 pose（M53）：怪物没有立绘帧，但**位移补间要照样走**。
	# 只给「有帧的人」记 pose 的话，怪物出手永远是「站着不动、血条掉一截」。
	_pose[uid] = {"anim": anim, "t": POSE_TIME, "dur": POSE_TIME}
	if anim.is_empty():
		if _dev_ui:
			print("[pose] %s/%s 没有对应动作帧" % [u.def_id, skill_id])
		return
	if _dev_ui:
		print("[pose] %s 用 %s -> %s" % [u.def_id, skill_id, anim])


## 出招补间（M39）：前冲 → 收回，顺带一点放大。
##
## 为什么需要它：DD1 的攻击骨架里**没有分帧动画**，只有「一整张姿势图 + 对整张图的位移/旋转」
## （`attack_sword.skel` 里只有 2 个插槽：shadow 和 attack_sword，各挂一张整图）。
## 导出包给的是姿势图本身、没带变换，所以只换图看起来就是「站那儿不动」。
## 补上这一段位移，换图才读得出「他冲上去打了一下」。
##
## 返回 (x 偏移, 额外缩放)。无敌/无出招时返回零。
## 进近战算「冲出去」，远程算「后坐」——这一组 kind 用后坐。
const RANGED_POSE: Array = ["arrow", "gun", "gas", "liquid", "magic_dark", "staff"]


func _pose_motion(u: Combatant, is_enemy: bool) -> Vector2:
	var p: Dictionary = _pose.get(u.uid, {})
	var t: float = float(p.get("t", 0.0))
	if t <= 0.0 or u.dead:
		return Vector2.ZERO
	var dur: float = maxf(0.01, float(p.get("dur", POSE_TIME)))
	var prog: float = clampf(1.0 - t / dur, 0.0, 1.0)
	var k: float = sin(prog * PI)          # 0 → 1 → 0，冲出去再收回来
	# 我方在左、敌方在右，所以冲锋方向相反
	var dir: float = -1.0 if is_enemy else 1.0
	# 用命中音反推这一招是近战还是远程（M53）。M52 已经建好了
	# 「动作名 → 武器种类」这张表，不必再单独判断一次技能类型。
	var kind: String = Sfx.impact_slot(str(p.get("anim", ""))).substr(4)
	if RANGED_POSE.has(kind):
		# 远程：小幅后坐，不冲。原来一律 26px 前冲，开枪也在往前撞。
		return Vector2(-dir * 9.0 * k, k * 0.025)
	# 近战：42px。原来是 26px，1080 宽下一格 143px，只有 1/5 格——
	# 配上 0.42 秒的正弦曲线基本看不出来。
	return Vector2(dir * 42.0 * k, k * 0.07)


## 播一个特效（M57）。
##
## `uid` 决定它跟着谁走：站位滑动的插值、受击抖动都会被算进去，
## 所以溅血是「跟着目标晃」而不是「钉在他原来站的地方」。
## `delay` 用来错开——施法特效先亮、命中特效晚 0.12 秒才见血。
## `--fx-check`：纯查表验收（M57），两秒出结果。
##
## 判什么：
##   1. manifest 读到了；
##   2. 数据里每个技能的每个特效字段，都能在 manifest 里找到；
##   3. 每个特效的第 0 帧能真的加载出纹理（文件在、导入成功）；
##   4. 锚点落在画布内（落在外面的表现是「整块飘到屏幕外」，不报错）。
func _run_fx_check() -> void:
	# 先落一个标记：Windows 上脚本 print 抓不到，只能靠文件判断走到了哪一步
	var f0: FileAccess = FileAccess.open("user://fx_check.log", FileAccess.WRITE)
	if f0 != null:
		f0.store_string("FX_CHECK start\n资源 %d 个\n" % _fx.defs.size())
		f0.close()
	var lines: Array = []
	var total: int = 0
	var hit: int = 0
	var bad: Array = []
	var tex_bad: int = 0
	var names: Dictionary = {}
	var groups: Array = [["英雄", db.heroes], ["怪物", db.monsters]]
	var per_group: Dictionary = {}
	for gi in groups:
		var g_name: String = str(gi[0])
		per_group[g_name] = [0, 0]      # [引用数, 命中数]
		var g_row: Dictionary = gi[1]
		for did in g_row.keys():
			var row: Dictionary = g_row[did]
			for s in (row.get("skills", []) as Array):
				if not (s is Dictionary):
					continue
				var art: Dictionary = (s as Dictionary).get("art", {})
				for k in ["fx", "targchestfx", "targheadfx", "targlowfx", "targfx", "performerfx"]:
					var nm: String = str(art.get(k, ""))
					if nm.is_empty():
						continue
					total += 1
					var cnt: Array = per_group[g_name]
					cnt[0] = int(cnt[0]) + 1
					if _fx.has(nm):
						hit += 1
						cnt[1] = int(cnt[1]) + 1
						names[nm] = true
					else:
						if not bad.has(nm):
							bad.append(nm)
	for nm in names.keys():
		if _fx.frame(str(nm), 0) == null:
			tex_bad += 1
			bad.append("帧读不到:%s" % nm)
	# 锚点只查「有没有」——落在画布外是合法的（原点在内容一侧），
	# 位置由 `位置 = 目标点 - 锚点*缩放` 决定，不在画布内也能摆对。
	var anchor_bad: Array = []
	for nm in names.keys():
		var d: Dictionary = _fx.def_of(str(nm))
		if (d.get("anchor", []) as Array).size() < 2:
			anchor_bad.append(nm)
	# 屏幕溅血层不挂在任何技能上，得单独点名检查（M57 续）
	for nm2 in ["attack_overlay_hit", "attack_overlay_crit"]:
		names[nm2] = true
		if not _fx.has(nm2):
			bad.append(nm2)
		elif _fx.frame(nm2, 0) == null:
			tex_bad += 1
			bad.append("帧读不到:%s" % nm2)

	var verdict: String = "PASS"
	if tex_bad > 0 or anchor_bad.size() > 0:
		verdict = "FAIL"
	lines.append("FX_CHECK %s" % verdict)
	lines.append("  资源 %d 个｜技能引用 %d 处｜命中 %d 处" % [_fx.defs.size(), total, hit])
	for g_name in per_group.keys():
		var cnt2: Array = per_group[g_name]
		lines.append("  %s：引用 %d，命中 %d" % [g_name, int(cnt2[0]), int(cnt2[1])])
	lines.append("  缺资源 %d 个（唯一名）：%s" % [bad.size(), str(bad.slice(0, 10))])
	lines.append("  帧读不到 %d；锚点缺字段 %d：%s" % [tex_bad, anchor_bad.size(), str(anchor_bad.slice(0, 8))])
	var txt: String = "\n".join(lines)
	print(txt)
	var f: FileAccess = FileAccess.open("user://fx_check.log", FileAccess.WRITE)
	if f != null:
		f.store_string(txt + "\n")
		f.close()
	# 顺带把路径打出来，方便找不到文件时直接去看
	print("日志：%s" % ProjectSettings.globalize_path("user://fx_check.log"))
	get_tree().quit(0 if verdict == "PASS" else 1)


func _fx_play(fx_name: String, uid: int, delay: float = 0.0, anch: String = "feet") -> void:
	if not _fx_on or fx_name.is_empty():
		return
	if not _fx.has(fx_name):
		# 「没有这个特效」是正常状态（skinnedmesh 那 49 个就导不出来），不报错
		if _dev_ui:
			print("[fx] 缺资源 %s" % fx_name)
		return
	var d: Dictionary = _fx.def_of(fx_name)
	_fx_active.append({"name": fx_name, "uid": uid, "anch": anch,
		"t": -delay, "dur": float(d.get("dur", 1.0))})
	if _dev_ui:
		print("[fx] %s @%d/%s" % [fx_name, uid, anch])


## 受击血花（M68）。
##
## 和 `_fx_overlay_play` 的分工：那个是**屏幕级叠加**（原版钉在屏幕中心、
## 铺满全屏），战斗里已经不用了 —— 竖屏下它会糊住整屏，连施法者身上都是血。
## 这个版本跟着受击者走，进 `_fx_active` 的普通层，会被光照正常压暗。
## overlay 那一套留着，`--fx-overlay` 验收还在用。
func _fx_blood_at(nm: String, uid: int, delay: float = 0.04) -> void:
	if not _fx_on or nm.is_empty() or not _fx.has(nm):
		return
	var d: Dictionary = _fx.def_of(nm)
	_fx_active.append({"name": nm, "uid": uid, "local": true,
		"t": -delay, "dur": float(d.get("dur", 0.75))})


## 局部血花的绘制。
##
## 素材（`attack_overlay_hit` 358×513 / `crit` 682×513）的 anchor 是
## `[-318, 256]`，那是给「钉在屏幕中心铺满全屏」准备的；直接套
## `_fx_draw_one` 会把它画到锚点右上方三百多像素之外。这里只取原图宽高比，
## 重新算尺寸：高 ≈ 角色高度，中心略高于胸口（血是从伤口往上溅的）。
func _fx_draw_blood(nm: String, t: float, at: Vector2) -> void:
	var d: Dictionary = _fx.def_of(nm)
	if d.is_empty() or t < 0.0:
		return
	var tex: Texture2D = _fx.frame(nm, int(t * float(d.get("fps", 12))))
	if tex == null:
		return
	var w0: float = maxf(1.0, float(d.get("w", 1)))
	# 0.62 是试出来的：素材本来是按「全屏血幕」画的，缩到 0.95 倍角色高度
	# 会把人整个盖住，看起来像「浑身是血」而不是「挨了一下」。
	var hh: float = SPRITE_H * 0.62
	var k: float = hh / maxf(1.0, float(d.get("h", 1)))
	var sz := Vector2(w0 * k, hh)
	draw_texture_rect(tex, Rect2(at - Vector2(sz.x * 0.5, sz.y * 0.55), sz), false)


func _fx_tick(delta: float) -> void:
	var j: int = 0
	while j < _fx_overlay.size():
		var o: Dictionary = _fx_overlay[j]
		var ot: float = float(o["t"]) + delta
		o["t"] = ot
		if ot >= float(o["dur"]):
			_fx_overlay.remove_at(j)
		else:
			j += 1
	if _fx_add != null:
		_fx_add.queue_redraw()
	if _fx_active.is_empty():
		return
	var i: int = 0
	while i < _fx_active.size():
		var f: Dictionary = _fx_active[i]
		var t: float = float(f["t"]) + delta
		f["t"] = t
		if t >= float(f["dur"]):
			_fx_active.remove_at(i)
		else:
			i += 1


## 某个单位此刻的锚点。
##
## `anch` 表示这个特效的原点该落在身体的哪儿：
##   feet  —— 出手特效（挥击/施法），资源就是按「角色脚底」画的；
##   chest —— 命中胸口，DD1 里 `targchestfx` 的原点就在被打的地方；
##   head  —— 命中头部（眩晕星星这类）；
##   low   —— 脚下（地面效果）。
## 全用「脚底」的话，溅血会落在地上——这正是第一次接完的样子。
const FX_ANCHOR_Y: Dictionary = {"feet": 0.0, "chest": 0.60, "head": 0.84, "low": 0.12}

func _fx_pos_of(uid: int, anch: String = "feet") -> Vector2:
	var u: Combatant = _unit_by_uid(uid)
	if u == null:
		return Vector2.ZERO
	var enemy: bool = not u.is_hero
	var gy: float = GROUND_ENEMY if enemy else GROUND_PARTY
	# 必须把出招补间算进来（M57 修）：`_draw_unit` 画的是 `cx + mo.x`，
	# 角色前冲 42px 时特效留在原地，就成了「血溅在空气里」。
	# 之前漏了这一步，预览图上看着还行，真打起来错开半格。
	var mo: Vector2 = _pose_motion(u, enemy)
	var k: float = 1.0 + mo.y
	return Vector2(_anim_x(u, enemy) + mo.x,
		gy - SPRITE_H * float(FX_ANCHOR_Y.get(anch, 0.0)) * k)


func _fx_draw_one(ci: CanvasItem, fx_name: String, t: float, at: Vector2) -> void:
	var d: Dictionary = _fx.def_of(fx_name)
	if d.is_empty() or t < 0.0:
		return
	var idx: int = int(t * float(d.get("fps", 20)))
	var tex: Texture2D = _fx.frame(fx_name, idx)
	if tex == null:
		return
	var k: float = _fx_draw_scale(d)
	var anchor: Array = d.get("anchor", [0.0, 0.0])
	var rect := Rect2(at - Vector2(float(anchor[0]), float(anchor[1])) * k,
		Vector2(float(d.get("w", 0)), float(d.get("h", 0))) * k)
	ci.draw_texture_rect(tex, rect, false)
	if _fx_debug:
		# 验收用：把「图的位置」和「锚点」画出来，肉眼就能判断公式对不对
		ci.draw_rect(rect, Color(1, 0, 0, 0.8), false, 1.0)
		ci.draw_circle(at, 3.0, Color(0.2, 1.0, 0.3, 0.95))


## 屏幕级溅血（M57 续）。
##
## 原版挨打时角色**不换姿势**（素材里没有任何 hit/hurt 动画，见 M57 §7），
## 打击感全靠这层：`fx/attack_overlay` 是全屏叠加，三个变体 hit / crit / miss，
## 0.79 秒，`.attack_overlay_pos 960 360` 钉在屏幕中心。
##
## 为什么只接 hit / crit：`miss` 那条的时间轴 alpha 全是 0（原版就是不溅血），
## 导出来是空的，接了也看不见，不如不接。
##
## `flip` 控制血往哪边溅：我方在左、敌方在右，打谁就朝谁那边溅。
func _fx_overlay_play(kind: String, flip: bool) -> void:
	if not _fx_on:
		return
	var nm: String = "attack_overlay_" + kind
	if not _fx.has(nm):
		return
	var d: Dictionary = _fx.def_of(nm)
	# 同一时刻只留一层：范围技一次打四个目标会叠四张，屏幕直接糊成红布。
	_fx_overlay.clear()
	_fx_overlay.append({"name": nm, "t": 0.0, "dur": float(d.get("dur", 0.8)),
		"flip": flip})


func _fx_overlay_one(nm: String, t: float, flip: bool) -> void:
	var d: Dictionary = _fx.def_of(nm)
	if d.is_empty():
		return
	var idx: int = int(t * float(d.get("fps", 12)))
	var tex: Texture2D = _fx.frame(nm, idx)
	if tex == null:
		return
	# 按**宽度**贴合（M57 修）：原版资产 1921 宽、舞台 1920 → 本来就是铺满宽度，
	# 高度多出来的部分让它溢出屏幕（血迹本来就在上下边缘）。
	# 之前按高度贴，1280 下只铺到 79%，两边留空，看着像一张贴纸。
	var k: float = size.x / maxf(1.0, float(d.get("w", 1)))
	var h: float = float(d.get("h", 1)) * k
	var r := Rect2(0.0, (size.y - h) * 0.5, size.x, h)
	# `draw_texture_rect` 只有 5 个参数，没有 flip_h；翻面只能靠整块画布的负缩放。
	if flip:
		draw_set_transform(Vector2(size.x, 0.0), 0.0, Vector2(-1.0, 1.0))
		draw_texture_rect(tex, r, false)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	else:
		draw_texture_rect(tex, r, false)


func _draw_fx_overlay() -> void:
	if not _fx_on:
		return
	if not _fx_overlay_preview.is_empty():
		var pv: String = _fx_overlay_preview
		var pf: bool = pv.ends_with(":flip")
		if pf:
			pv = pv.substr(0, pv.length() - 5)
		_fx_overlay_one("attack_overlay_" + pv, 0.4, pf)
	for o in _fx_overlay:
		_fx_overlay_one(str(o["name"]), float(o["t"]), bool(o.get("flip", false)))


## 普通 alpha 层：只画 manifest 里没有标 `add` 的（溅血、烟雾、尘土）。
func _draw_fx() -> void:
	if not _fx_on:
		return
	# 预览（验收用）：不跑战斗也能看锚点对不对
	if not _fx_preview.is_empty() and _battle != null:
		for u in _battle.party:
			var c := u as Combatant
			if not c.dead:
				var d0: Dictionary = _fx.def_of(_fx_preview)
				if not bool(d0.get("add", false)):
					_fx_draw_one(self, _fx_preview, _fx_preview_t,
						_fx_pos_of(c.uid, _fx_preview_anch))
				break
	for f in _fx_active:
		var nm: String = str(f["name"])
		if bool(_fx.def_of(nm).get("add", false)):
			continue
		# 血花跟目标胸口走，不吃 manifest 的 anchor（那是全屏用法算的，见 _fx_draw_blood）
		if bool(f.get("local", false)):
			_fx_draw_blood(nm, float(f["t"]), _fx_pos_of(int(f["uid"]), "chest"))
			continue
		_fx_draw_one(self, nm, float(f["t"]),
			_fx_pos_of(int(f["uid"]), str(f.get("anch", "feet"))))


## 加法层：由 `FxAddLayer._draw()` 回调。刀光、火花、光晕走这里。
##
## 分成两层是必须的：同一张图用普通 alpha 画出来是一块灰贴纸，
## 用加法画才是光。素材本身是「暗灰 + 高透明度」，只有加法能读出来。
func draw_fx_additive(ci: CanvasItem) -> void:
	if not _fx_on:
		return
	if not _fx_preview.is_empty() and _battle != null:
		for u in _battle.party:
			var c := u as Combatant
			if not c.dead:
				if bool(_fx.def_of(_fx_preview).get("add", false)):
					_fx_draw_one(ci, _fx_preview, _fx_preview_t,
						_fx_pos_of(c.uid, _fx_preview_anch))
				break
	for f in _fx_active:
		var nm: String = str(f["name"])
		if not bool(_fx.def_of(nm).get("add", false)):
			continue
		_fx_draw_one(ci, nm, float(f["t"]),
			_fx_pos_of(int(f["uid"]), str(f.get("anch", "feet"))))


func _draw_unit(u: Combatant, cx: float, gy: float, is_enemy: bool) -> void:
	var is_active: bool = _battle.awaiting_input != null and _battle.awaiting_input.uid == u.uid
	var is_target: bool = false
	if not _pending.is_empty():
		for t in (_pending.get("targets", []) as Array):
			if t.uid == u.uid:
				is_target = true
				break
	# 挪位模式下，可落点的队友也亮一圈（M72）。
	# 只给底部列一排按钮的话，玩家得先读「3 号位」再回头在屏幕上数人。
	var is_move_spot: bool = false
	if _move_mode and _battle != null and _battle.awaiting_input != null:
		var mv_actor: Combatant = _battle.awaiting_input
		if mv_actor.uid != u.uid and _battle.move_options(mv_actor).has(u.rank):
			is_move_spot = true

	var accent: Color = DdTheme.ENEMY if is_enemy else DdTheme.PARTY
	if u.dead:
		accent = Color("#3a3a3a")

	# 脚下阴影：没有这一步，立绘看起来像浮在地上
	draw_set_transform(Vector2(cx, gy + 2.0), 0.0, Vector2(1.0, 0.30))
	draw_circle(Vector2.ZERO, 34.0, Color(0.0, 0.0, 0.0, 0.45))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

	var anim: String = _unit_anim(u)
	var tex: Texture2D = _art.frame(u.def_id, anim)
	var mo: Vector2 = _pose_motion(u, is_enemy)
	var sx: float = (SPRITE_H / BASE_H) * (1.0 + mo.y)
	var top: float = gy - SPRITE_H
	var hw: float = 60.0
	if tex != null:
		var w: float = tex.get_width() * sx
		var h: float = tex.get_height() * sx
		top = gy - h
		hw = maxf(34.0, w * 0.5)
		var tint: Color = Color(1, 1, 1, 1)
		if u.dead:
			tint = Color(0.48, 0.46, 0.44, 0.7)
		elif u.has_affliction():
			# 崩溃没有战斗姿势帧：素材里的 `afflicted` 是 2000×2000 的爆发插图，
			# 不是站姿。硬塞一张不对的图比染色更糟。
			tint = Color(1.0, 0.72, 0.68, 1.0)
		draw_texture_rect(tex, Rect2(cx + mo.x - w * 0.5, top, w, h), false, tint)
	else:
		# 没有立绘的单位（怪物）。死了就**塌成一堆**：
		# 没有死亡帧可用，而「站着但变灰」读不出「它已经死了」。
		_draw_silhouette(cx, gy, SPRITE_H * (0.36 if u.dead else 1.0), accent)

	# 选中/目标：画一圈地环，而不是框住立绘——立绘不是方块，框起来很别扭
	# 压扁成「地环」：正圆会盖住脚下的血条，而血条比装饰重要
	var ring_col: Color = Color(0, 0, 0, 0)
	var ring_w: float = 0.0
	# 顺序（M65）：按下 > 当前行动者 > 可打目标 > 悬停。
	# 原来 `is_target` 排在 `_press_id` 前面，而按住的那个单位一定也是合法目标，
	# 于是 LIGHT 那一档永远走不到 —— 注释写着「按下的更亮」，行为从来没发生过。
	if _press_id == "tgt:%d" % u.uid:
		ring_col = DdTheme.LIGHT
		ring_w = 4.0
	elif is_active:
		ring_col = DdTheme.CRIT
		ring_w = 2.5
	elif is_move_spot:
		ring_col = DdTheme.LIGHT
		ring_w = 3.0
	elif is_target:
		ring_col = DdTheme.HEAL
		ring_w = 3.0
	elif _hover_uid == u.uid:
		ring_col = DdTheme.DIM
		ring_w = 1.0
	if ring_w > 0.0:
		draw_set_transform(Vector2(cx, gy + 1.0), 0.0, Vector2(1.0, 0.26))
		draw_arc(Vector2.ZERO, 54.0, 0.0, TAU, 40, ring_col, ring_w)
		# 可打的目标再加一圈外环（M65）：地环被压扁到 0.26，单环只有几个像素高，
		# 在深色背景上分不出「这只能打」和「它只是站在这儿」。
		if is_target and not u.dead:
			draw_arc(Vector2.ZERO, 64.0, 0.0, TAU, 48,
				Color(ring_col.r, ring_col.g, ring_col.b, 0.45), 1.5)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

	# 状态块的几何在这里先算出来（M84）：点击区要用它，
	# 真正的绘制延后到光照之后，见 `_draw_unit_status`。
	var head_ref: float = gy - SPRITE_H
	var head_y2: float = clampf(top, head_ref - 16.0, head_ref)
	var blk_top_g: float = (head_y2 - (40.0 if u.is_hero else 26.0)) - 13.0
	_slots.append({"rect": Rect2(cx - hw, blk_top_g, hw * 2.0,
			(gy - blk_top_g) + 14.0),
		"uid": u.uid, "side": "enemy" if is_enemy else "party",
		"cx": cx, "gy": gy, "top": top})


## 某个 rank 上站的是谁（M72）。挪位要写「与谁换位」，得先查到人。
func _unit_at_rank(actor: Combatant, rk: int) -> Combatant:
	if _battle == null or actor == null:
		return null
	var arr: Array = _battle.party if actor.is_hero else _battle.enemies
	if rk >= 0 and rk < arr.size():
		return arr[rk] as Combatant
	return null



## 单位头顶的状态块（M84）。
##
## 从 `_draw_unit` 里拆出来的，原因是**绘制顺序**：
## 它原来画在光照层之前，会被那层全屏暗色按「这一带够不够亮」压暗 ——
## 敌方区域远离我方火把，紫色状态字就被压成半透明，叠在剪影上读不出来。
## 名字、血条、状态标记是界面信息，不该跟着环境一起变暗。
func _draw_unit_status(u: Combatant, cx: float, gy: float, top: float,
		is_enemy: bool) -> void:
	var is_active: bool = _battle.awaiting_input != null and _battle.awaiting_input.uid == u.uid
	var is_target: bool = false
	if not _pending.is_empty():
		for t in (_pending.get("targets", []) as Array):
			if t.uid == u.uid:
				is_target = true
				break
	var accent: Color = DdTheme.ENEMY if is_enemy else DdTheme.PARTY
	if u.dead:
		accent = Color("#3a3a3a")
	# —— 头顶状态块（M68）——
	#
	# 原来名字在头顶、血条和压力条在脚下：一条命被拆成上下两半，
	# 看血要低头、看名字要抬头，而 buff 标签又压在脚边和血量数字挤在一起。
	# 现在整块贴着脑袋往上堆：名字 → 血条 → 压力 → 状态标签。
	#
	# **基准用 SPRITE_H 而不是 tex 高度**。第一版跟着 `top`（tex 实际顶边）走，
	# 结果举着剑的十字军把整块顶到屏幕中间，四个人的血条高低差出 100px。
	# 允许上移 16px 给「头确实很高」的单位一点余地，再多就回到统一基准。
	# 第一版给到 26，举着剑的十字军会明显凸出四个人的那条线。
	var head_ref: float = gy - SPRITE_H
	var head_y: float = clampf(top, head_ref - 16.0, head_ref)
	var is_h: bool = u.is_hero
	# 敌人没有压力条（压力只落在英雄身上），整块要压矮 12px，
	# 否则敌方那排在 header 下面挤成一团。
	# 宽度（M70）：原来 nm_w 取槽宽的 1.06 倍、暗底再 +16，四个人的底板
	# 直接连成一片，读起来像「一整条黑带」而不是四个人的信息。
	# 现在留出缝：块宽不超过槽宽 -6，眼睛能顺着缝隙分开。
	var slot_w: float = _battle_slot_w()
	var nm_w: float = clampf(slot_w * 0.94, 112.0, 172.0)
	var blk_w: float = minf(nm_w + 12.0, slot_w - 6.0)
	var name_y: float = head_y - (40.0 if is_h else 26.0)
	var hp_r := Rect2(cx - 52.0, name_y + 5.0, 104.0, 11.0)
	var st_r := Rect2(cx - 52.0, hp_r.end.y + 4.0, 104.0, 4.0)
	# 状态标签的基线（M73 调过）：敌方那行要落在块内，
	# 原来的 +14 会让「残骸 N」掉到块外、压在立绘头顶上，读不出来。
	var mk_y: float = hp_r.end.y + (16.0 if is_h else 9.0)
	# 召唤角标（M102）：尸体会被召唤顶替（这是 M12 的主动设计，有测试钉住），
	# 所以玩家看到的是「打死一个又冒出来一个」。规则不动，把「它是被叫来的」
	# 写在脸上——不然只能靠翻底部日志才知道刚才发生了什么。
	if _summoned_uids.has(u.uid):
		_text(Vector2(cx + 54.0, name_y + 14.0), "召", DdTheme.FONT_TAG,
			DdTheme.WARN)

	# 状态标签先算出来：它决定块的高度和 marks 的基线
	var marks: Array = []
	# 死亡不写文字（M38）：我方是躺倒的 `dead` 帧、敌方是塌掉的剪影，
	# 图形已经说清楚了。
	# 例外是「还能被打掉的残骸」（M73）：它头顶要写耐久，
	# 否则玩家不知道这堆东西打一下还在、打两下才清。
	if u.dead:
		if u.corpse_hp > 0 and not u.is_hero:
			marks.append("残骸 %d" % u.corpse_hp)
	else:
		if u.at_deaths_door:
			marks.append("死门")
		if u.stun_turns > 0:
			marks.append("眩晕")
		if u.dots.size() > 0:
			marks.append("DOT×%d" % u.dots.size())
		if u.has_affliction():
			marks.append("崩溃")
		elif u.is_virtuous():
			marks.append("美德")
		var gt: Combatant = _battle.guard_target_of(u.uid)
		if gt != null:
			marks.append("守%d" % (gt.rank + 1))
		if _battle.guardian_of(u.uid) != null:
			marks.append("被守")
		if _battle.has_riposte(u.uid):
			marks.append("反击")
		if marks.size() > 4:
			marks = marks.slice(0, 4)

	# 整块垫一层暗底（M68）：血条和 9px 的小字直接压在砖墙上读不出来。
	# 行动中换成暖金底 + 描边 —— 原来只有脚下一圈 2.5px 的地环，
	# 在满屏立绘里根本读不出「现在轮到谁」。
	var blk_top: float = name_y - 13.0
	var blk := Rect2(cx - blk_w * 0.5, blk_top, blk_w, head_y - blk_top + 2.0)
	if is_active:
		draw_rect(blk, Color(0.78, 0.60, 0.26, 0.20))
		draw_rect(blk, Color(0.92, 0.74, 0.34, 0.75), false, 1.5)
		# 顶上一颗朝下的三角，指着这个人：远看也能找到
		draw_colored_polygon(PackedVector2Array([
			Vector2(cx - 7.0, blk_top - 8.0), Vector2(cx + 7.0, blk_top - 8.0),
			Vector2(cx, blk_top - 1.0)]), Color(0.92, 0.74, 0.34, 0.95))
	# 底色分敌我（M69）：两排状态块长得一模一样时，玩家要靠"它离谁近"来判断归属，
	# 而这正好是最容易看错的地方。左边那排压一点红、右边压一点蓝，
	# 不靠位置也能分出「这是谁的信息」。
	else:
		draw_rect(blk, Color(0.075, 0.020, 0.018, 0.62) if is_enemy
			else Color(0.018, 0.030, 0.058, 0.62))

	# 名字 + 位次。**两块是镜像的**（M69）：
	#   敌方——位次在名字左侧（靠近屏幕外沿）；
	#   我方——位次在名字右侧（同样靠外沿）。
	# 两块的「贴边方向」一致，中间那块就是干净的，归属不用猜。
	var bsz: float = 16.0
	var bx0: float = cx - nm_w * 0.5 if is_enemy else cx + nm_w * 0.5 - bsz
	var name_x: float = (bx0 + bsz + 4.0) if is_enemy else (cx - nm_w * 0.5)
	_text(Vector2(name_x, name_y),
		DdTheme.ellipsis(DdNames.unit_name(u.def_id), _font, nm_w - bsz - 6.0, 12),
		DdTheme.FONT_MD,
		DdTheme.LIGHT if is_active else (DdTheme.FAINT if u.dead else DdTheme.TEXT),
		HORIZONTAL_ALIGNMENT_CENTER, nm_w - bsz - 4.0)

	# 位次徽章（M68）。原来只是挂在名字右边一个 9px 的灰数字，
	# 在 750 宽的战场上等于没有。现在做成带敌我底色的方块：
	# 排先后手时「我在几号位」是第一信息。
	var br := Rect2(bx0, name_y - 12.0, bsz, bsz)
	draw_rect(br, Color(accent.r, accent.g, accent.b, 0.85))
	draw_rect(br, Color(1.0, 1.0, 1.0, 0.22), false, 1.0)
	_text(Vector2(br.position.x, name_y - 1.0), str(u.rank + 1), DdTheme.FONT_TAG,
		Color("#f2eee2"), HORIZONTAL_ALIGNMENT_CENTER, bsz)

	# 血条 + 数字（数字仍压在条内，省一行高度）
	# 颜色按阵营分（M197）：我方绿、敌方红。原来两侧都是 `DdTheme.HP`（红），
	# 战场上扫一眼分不出「哪条是我的、哪条是它的」。
	_bar(hp_r, u.hp_ratio(), _hp_color(u.is_hero), DdTheme.HP_TRACK)
	_text(Vector2(hp_r.position.x, hp_r.position.y + 9.5),
		"%d / %d" % [u.hp, u.base_hp], DdTheme.FONT_TAG,
		Color("#f2eee2"), HORIZONTAL_ALIGNMENT_CENTER, hp_r.size.x)

	# 命中率（M65）：点下去之前唯一算得出来的东西，也比「伤害 6-12」更有用——
	# 伤害再高，打不中就是 0。只在瞄准态、只对敌对目标显示。
	if is_target and not u.dead and not _pending.is_empty() and _battle != null:
		var holder: Combatant = _battle.awaiting_input
		var pa: Dictionary = _pending.get("action", {})
		var is_attack: bool = holder != null and u.is_hero != holder.is_hero \
			and not bool(pa.get("friendly", false)) and float(pa.get("heal", 0.0)) <= 0.0
		if is_attack:
			var pch: float = _preview_hit(holder, pa, u)
			var pcol: Color = DdTheme.OK if pch >= 0.75 else (
				DdTheme.STAT if pch >= 0.5 else DdTheme.CRIT)
			# 血条右侧外面。压在条上的话会盖掉 "14/14" 的后两位（第一版就是这样）。
			_text(Vector2(hp_r.end.x + 4.0, hp_r.position.y + 9.5),
				"%.0f%%" % (pch * 100.0), DdTheme.FONT_TAG, pcol)

	if u.is_hero:
		_bar(st_r, u.stress / 200.0, DdTheme.STRESS, DdTheme.STRESS_TRACK)
		# 100 崩溃刻度：压力条唯一的判据就是这条线
		var tx2: float = st_r.position.x + st_r.size.x * 0.5
		draw_line(Vector2(tx2, st_r.position.y - 2.0), Vector2(tx2, st_r.end.y + 2.0),
			Color(0.65, 0.60, 0.50, 0.55), 1.0)
		# 数值写在条右侧：条本身只有 4px 高，光靠长度读不出「离 100 还有多少」，
		# 而 100 正是崩溃线。
		_text(Vector2(st_r.end.x + 4.0, st_r.end.y + 1.0), "%.0f" % u.stress,
			DdTheme.FONT_TAG,
			DdTheme.STRESS if u.stress >= 100.0 else DdTheme.DIM)

	if not marks.is_empty():
		_text(Vector2(cx - 52.0, mk_y), " ".join(marks),
			DdTheme.FONT_TAG, DdTheme.WARN if (u.dead or u.at_deaths_door) else DdTheme.STAT,
			HORIZONTAL_ALIGNMENT_CENTER, 104.0)



## 没有美术的单位：一件兜帽斗篷的剪影（M38）。
##
## 不画空格、也不画圆牌——「一个人形站在那儿」比「一个圆里有字」更像战场。
## 只有怪物走这条路（英雄有立绘）。英雄缺图说明是导入出了问题，
## 那时候剪影会立刻显眼，比静默空白好。
func _draw_silhouette(cx: float, gy: float, h: float, col: Color) -> void:
	# 头 + 袍子两段。第一版把整个人画成一个钟形多边形，
	# 缩到 180px 之后像一顶帐篷——**没有头肩分界，人形就读不出来**。
	var body: Color = Color(0.10, 0.09, 0.09, 0.95)
	var head_r: float = 0.075 * h
	var head_c := Vector2(cx, gy - 0.870 * h)
	draw_circle(head_c, head_r, body)
	draw_arc(head_c, head_r, 0.0, TAU, 20, Color(col.r, col.g, col.b, 0.55), 1.0)
	var pts := PackedVector2Array([
		Vector2(cx - 0.150 * h, gy - 0.800 * h),   # 左肩
		Vector2(cx - 0.130 * h, gy - 0.400 * h),   # 左腰
		Vector2(cx - 0.215 * h, gy),               # 左袍底
		Vector2(cx + 0.215 * h, gy),               # 右袍底
		Vector2(cx + 0.130 * h, gy - 0.400 * h),   # 右腰
		Vector2(cx + 0.150 * h, gy - 0.800 * h),   # 右肩
	])
	draw_colored_polygon(pts, body)
	for i in pts.size():
		draw_line(pts[i], pts[(i + 1) % pts.size()], Color(col.r, col.g, col.b, 0.55), 1.0)
	# 眼睛：没有这两点，暗背景上的剪影几乎看不见
	var eye_y: float = gy - 0.885 * h
	var er: float = maxf(1.2, 0.011 * h)
	draw_circle(Vector2(cx - 0.030 * h, eye_y), er, Color(0.85, 0.45, 0.35, 0.9))
	draw_circle(Vector2(cx + 0.030 * h, eye_y), er, Color(0.85, 0.45, 0.35, 0.9))


## 日志摘要条（M58）。竖屏底部让给技能，日志只留一行最近记录。
##
## 点整条展开浮层看完整记录。信息没删，只是从「一直看得见」变成「点开看得见」。
func _draw_log_bar(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	_hit_overlay(r, "log_toggle")
	var last: String = "行程记录"
	var col: Color = DdTheme.FAINT
	if not _log.is_empty():
		var e: Dictionary = _log[_log.size() - 1]
		last = str(e.text)
		col = e.color
	_text(Vector2(r.position.x + 14.0, r.position.y + r.size.y * 0.5 + 5.0),
		DdTheme.ellipsis(last, _font, r.size.x - 110.0, 12), DdTheme.FONT_MD, col)
	_text(Vector2(r.position.x + r.size.x - 78.0, r.position.y + r.size.y * 0.5 + 5.0),
		"▴ 收起" if _log_open else "▾ 全部", DdTheme.FONT_TAG, DdTheme.DIM,
		HORIZONTAL_ALIGNMENT_RIGHT, 64.0)
	_add_hit(r, "log_toggle")


## 日志浮层：铺在下半屏，点关闭收起。
func _draw_log_float() -> void:
	if not _log_open or _state != S_BATTLE:
		return
	var r := Rect2(24.0, 300.0, size.x - 48.0, size.y - 340.0)
	draw_rect(r.grow(8.0), Color(0.0, 0.0, 0.0, 0.55))
	_draw_log_panel(r)
	_add_button(Rect2(r.position.x + r.size.x - 116.0, r.position.y + r.size.y - 64.0,
		100.0, 48.0), "log_toggle", "关闭")


## 次级操作行（M58）：调整站位 / 跳过。
##
## 这两个动作一回合最多用一次，频率远低于技能，所以从最底部上移一层，
## 把屏幕最下方那块最容易够到的位置留给技能。
func _draw_action_row(r: Rect2) -> void:
	if _battle == null:
		return
	var actor: Combatant = _battle.awaiting_input
	_panel(r, DdTheme.PANEL_DEEP)
	_text(Vector2(r.position.x + 16.0, r.position.y + 22.0),
		"次级操作 · 每回合最多一次 · 撤退会放弃整趟", DdTheme.FONT_TAG, DdTheme.FAINT)
	if actor == null:
		return
	# 三个按钮并排（M65）。撤退以前只有键盘 ESC，而 ESC 只在地图屏生效，
	# 手机上根本没有这个键 —— 打不过的时候没有任何出路。
	# 它是「丢掉整趟」的动作，所以走二次确认（`_retreat_arm`）。
	var can_move: bool = not _battle.move_options(actor).is_empty()
	var cells: Array = []
	if can_move:
		cells.append(["movemode", "挪位（%d 号）" % (actor.rank + 1), false])
	cells.append(["pass", "跳过 +%.0f 压力" % float(
		db.rules.raw.get("passed_turn_stress_dmg", 5.0)), false])
	cells.append(["retreat", "确认撤退" if _retreat_arm else "撤退", true])
	var by: float = r.position.y + 32.0
	var bh: float = maxf(48.0, r.size.y - 40.0)
	var gap: float = 12.0
	var bw: float = (r.size.x - 32.0 - gap * float(cells.size() - 1)) / float(cells.size())
	for i in cells.size():
		var c: Array = cells[i]
		_add_button(Rect2(r.position.x + 16.0 + float(i) * (bw + gap), by, bw, bh),
			str(c[0]), str(c[1]), true, bool(c[2]))


## 技能区（M58 竖屏）：4 列 × 2 行 = 8 格，每格 80 高。
##
## 横屏是 3 列 × 3 行、卡高 34 —— 那是被 206 高的面板逼出来的。
## 竖屏这条面板有 340 高，卡片终于能做到 80，手指点得准，
## 「狂热点名」这种四字名也不用截断。
func _draw_skill_panel(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	var actor: Combatant = _battle.awaiting_input
	if actor == null:
		_text(Vector2(r.position.x, r.position.y + 34.0), "敌方行动中…", DdTheme.FONT_MD,
			DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, r.size.x)
		return

	_text(Vector2(r.position.x + 16.0, r.position.y + 28.0),
		"%s 的行动" % DdNames.unit_name(actor.def_id), DdTheme.FONT_BD, DdTheme.TEXT)
	_text(Vector2(r.position.x + 16.0, r.position.y + 48.0),
		"武器伤害 %d-%d · 暴击 %.0f%% · 速度 %.0f" % [
			int(actor.base_dmg_low), int(actor.base_dmg_high),
			_crit_pct(actor), actor.speed()], DdTheme.FONT_SM, DdTheme.FAINT)

	if _show_move_demo and _battle != null and _battle.awaiting_input != null:
		_move_mode = true

	# **2 列 × 2 行**（M164）。原来 4 张横排，每张 (750-32-30)/4 ≈ 172 ——
	# 名字四字 + 摘要一句话，摘要必然被 ellipsis 截掉（「修正 +15%…」
	# 这种半截话玩家读不出所以然）。改成两列后每张 350，摘要放得下。
	# 行数靠 `bh` 自动排，技能超过 4 个也不会挤出去（超出会被下面那行 `break` 挡掉）。
	var cols: int = 2
	var gap: float = 10.0
	var bw: float = (r.size.x - 32.0 - gap * float(cols - 1)) / float(cols)
	# 卡片高度按**可用空间**算（M141）：原来写死 80，而这块面板下面
	# 常年空着 60~80px —— 卡片偏矮的直接后果是摘要被 ellipsis 截掉，
	# 「修正 +15%…」这种半截话玩家读不出所以然。
	var avail_h: float = r.size.y - 66.0 - 12.0
	# 下限从 80 降到 44（M178）：战斗底部面板只有 ~180 高，
	# `avail_h` 算出来约 102，而两行 80 高 + 间距 = 170 —— 第二行直接
	# 被下面的 `if ... > r.end.y: break` 丢掉。
	# 表现就是「装了 4 个技能、战斗里只画 2 张卡」，而且**不报错**。
	# 用户报的「城镇 4/4、战斗只有 2 个」就是这个。
	var bh: float = clampf((avail_h - gap) * 0.5, 44.0, 132.0)
	var y0: float = r.position.y + 66.0

	# 瞄准态：面板原地变成目标列表（M89）。
	# 挪位优先——那是另一种「选一个格子」的形态，两者不会同时出现。
	if not _move_mode and not _pending.is_empty():
		_draw_target_panel(r, actor)
		return

	if _move_mode:
		var spots: Array = _battle.move_options(actor)
		_text(Vector2(r.position.x + 16.0, y0 - 8.0), "挪到哪个位置？换位会消耗这一回合",
			DdTheme.FONT_MD, DdTheme.HEAL)
		for i in spots.size():
			var rk: int = int(spots[i])
			# 文案带方向 + 格数 + 交换对象（M72）。
			# 原来只写「移到 3 号位」，看起来像两个预先写死的选项；
			# 而它其实是按 `move_action.move = [1,1]` 现算的前后各一格。
			var dir_txt: String = "前移" if rk < actor.rank else "后移"
			var gap_n: int = absi(rk - actor.rank)
			var other: Combatant = _unit_at_rank(actor, rk)
			var swap_txt: String = ""
			if other != null:
				swap_txt = "（与 %s 换位）" % DdNames.unit_name(other.def_id)
			var sr := Rect2(r.position.x + 16.0, y0 + 10.0 + float(i) * 56.0,
				r.size.x - 32.0, 48.0)
			_add_button(sr, "goto:%d" % rk,
				"%s %d 格 → %d 号位%s" % [dir_txt, gap_n, rk + 1, swap_txt])
		_add_button(Rect2(r.position.x + 16.0, r.position.y + r.size.y - 58.0,
			r.size.x - 32.0, 48.0), "movecancel", "取消，回到技能")
		return

	for i in _options.size():
		var col: int = i % cols
		var row: int = i / cols
		var br := Rect2(r.position.x + 16.0 + float(col) * (bw + gap),
			y0 + float(row) * (bh + gap), bw, bh)
		if br.position.y + br.size.y > r.position.y + r.size.y - 12.0:
			break
		var opt: Dictionary = _options[i]
		var action: Dictionary = opt.action
		# 不可用的招留在原位灰显（M65）。直接不画的话，玩家只会看到「少了一格」。
		var usable: bool = bool(opt.get("usable", true))
		var selected: bool = usable and not _pending.is_empty() \
			and str(_pending.action.id) == str(action.id)
		var st: int = TILE_IDLE if not usable else _hit_state(br, "skill:%d" % i)
		if not usable:
			draw_rect(br, DdTheme.BTN_OFF)
		else:
			draw_rect(br, DdTheme.BTN_ACTIVE if selected else (
				DdTheme.BTN_HOVER if st == TILE_HOVER else DdTheme.BTN))
		draw_rect(br, DdTheme.CRIT if selected else DdTheme.PANEL_EDGE, false, 1.0)
		if st == TILE_PRESS:
			# 按下压过选中：选中是「这一招正在瞄准」，按下是「我正按着它」，
			# 两者同时成立时，手指下的那个必须更亮才看得出按中了。
			draw_rect(br, Color(1.0, 1.0, 1.0, 0.10))
			draw_rect(br.grow(-1.0), DdTheme.DIM, false, 2.0)
		# 技能图标（M64 第十六轮）：六类之一，放在卡片左侧。
		# 有图标之后名字和摘要整体右移 38 —— 卡片 172 宽仍够放四字技能名。
		var ico_tex: Texture2D = _action_icon_tex(action, actor)
		var tx0: float = br.position.x + 10.0
		if ico_tex != null:
			var isz: float = minf(46.0, bh - 8.0)
			# 和公会屏同一个理由：原版图标是黑底彩边，贴深色卡要提亮（M129）
			draw_texture_rect(ico_tex, Rect2(br.position.x + 5.0,
				br.position.y + (bh - isz) * 0.5, isz, isz), false,
				Color(1.95, 1.95, 1.95))
			tx0 = br.position.x + 52.0
		# 施法者头像（M157）：四张卡长得一样，玩家分不清「这是谁在出手」。
		# 放右上角 —— 左边是技能图标、下面两行被文字占满，只有这里空着。
		if actor != null and actor.is_hero and not actor.hero_key.is_empty():
			var htex: Texture2D = _art.texture_of(campaign.def_of(actor.hero_key))
			if htex != null:
				var hsz: float = 24.0
				draw_texture_rect(htex, Rect2(br.end.x - hsz - 6.0,
					br.position.y + 4.0, hsz, hsz), false)
		# 位次提示挪到第二行（M87）。
		#
		# 原来它挂在名字行右上角（宽 54），名字区因此少 30px ——
		# 13px 之后「抵近射击」这种四字名一挤就顶到边上。
		# 现在名字行拿满宽度，提示并进第二行的摘要前面：
		# 「需 1 号位 · 修正 +50% · 敌」。
		# 顺便说明：那不是名字的一部分（名字表里没有「第 N 号位」），
		# 它是 `opt.why`（不可用原因）和 `_move_badge`（自带位移）两个来源。
		var badge: String = _move_badge(action) if usable else str(opt.get("why", ""))
		var name_w: float = br.end.x - tx0 - 10.0
		_text(Vector2(tx0, br.position.y + 24.0),
			DdTheme.ellipsis(DdNames.skill_name(str(action.id)), _font, name_w,
				DdTheme.FONT_MD),
			DdTheme.FONT_MD, DdTheme.TEXT if usable else DdTheme.FAINT)
		var sum_line: String = _action_summary(action, actor)
		if not badge.is_empty():
			sum_line = badge + " · " + sum_line
		# 卡片够高就折两行（M141）：80 高的卡塞两行会顶到边框，
		# 100 以上的就放得下，而折行的目的正是「别再用省略号截断」。
		var sum_lines: Array = _wrap_tokens(sum_line, br.end.x - tx0 - 10.0,
			DdTheme.FONT_TAG, 2 if bh >= 100.0 else 1)
		var sy2: float = br.position.y + 44.0
		for sl in sum_lines:
			_text(Vector2(tx0, sy2), str(sl), DdTheme.FONT_TAG,
				DdTheme.WARN if not usable else DdTheme.FAINT,
				HORIZONTAL_ALIGNMENT_LEFT, br.end.x - tx0 - 10.0)
			sy2 += 22.0
		_add_hit(br, "skill:%d" % i)

	if not _pending.is_empty():
		var pa: Dictionary = _pending.get("action", {})
		var tip: String = "全体技能 · 点任一高亮目标释放 · 点空白取消"
		if not bool(pa.get("target_aoe", false)):
			tip = "点高亮的目标（绿环）出手 · 点空白取消"
		_text(Vector2(r.position.x + 16.0, r.position.y + r.size.y - 14.0),
			tip, DdTheme.FONT_SM, DdTheme.HEAL)


## 目标选择面板（M89）。
##
## 点完技能之后，技能面板**原地**变成目标列表。
##
## 原来的做法是抬手去点战场上的单位：敌人在地面线以上（100~290），
## 技能卡贴底（1044+），中间隔着整个战场——单手够不到，每打一下都得换手。
## 现在「选技能 → 打谁」都在屏幕底部完成，点一行就是出手。
##
## 代价是瞄准期间看不到技能卡：这个阶段招式已经定了，不需要再看一遍。
func _draw_target_panel(r: Rect2, actor: Combatant) -> void:
	var act: Dictionary = _pending.get("action", {})
	var rows: Array = _pending.get("targets", [])
	var aoe: bool = bool(act.get("target_aoe", false))
	var y0: float = r.position.y + 8.0
	var ttl: String = "%s → %s" % [DdNames.unit_name(actor.def_id),
		"全体，点一行即出手" if aoe else "打谁？点一行就出手"]
	_text(Vector2(r.position.x + 16.0, y0 + 22.0), ttl,
		DdTheme.FONT_BD, DdTheme.TEXT)
	# 取消放右上：瞄准态下技能卡被盖住了，没有退路就只能硬打出去
	_add_button(Rect2(r.end.x - 112.0, y0 + 2.0, 96.0, 34.0), "cancel_pick", "取消")

	var top: float = y0 + 52.0
	var avail: float = r.end.y - top - 12.0
	# 行高按目标数把可用高度吃满（M89）：两行时用 84、四行时 45，
	# 固定 56 会让「只有两个目标」的面板下面空掉一大块。
	var row_h: float = minf(84.0, avail / float(maxi(1, rows.size())))
	for i in rows.size():
		var t: Combatant = rows[i]
		var rr := Rect2(r.position.x + 16.0, top + float(i) * row_h,
			r.size.x - 32.0, row_h - 6.0)
		var id: String = "atk:%d" % t.uid
		var st: int = _hit_state(rr, id)
		draw_rect(rr, DdTheme.BTN_HOVER if st == TILE_HOVER else DdTheme.BTN)
		draw_rect(Rect2(rr.position, Vector2(3.0, rr.size.y)),
			DdTheme.ENEMY if not t.is_hero else DdTheme.PARTY)
		draw_rect(rr, DdTheme.PANEL_EDGE, false, 1.0)
		_add_hit(rr, id)
		var mid: float = rr.position.y + rr.size.y * 0.5
		# 位次写在最左：战场上的位次方块和这里要能对上
		_text(Vector2(rr.position.x + 12.0, mid + 6.0), str(t.rank + 1),
			DdTheme.FONT_BD, DdTheme.DIM)
		# 头像（M141）：英雄有立绘就贴，怪物没有就用色块 + 首字占位。
		# 一列名字读起来全靠认字，加了头像之后扫一眼就知道打谁。
		var av := Rect2(rr.position.x + 34.0, mid - 17.0, 34.0, 34.0)
		var atex: Texture2D = null
		if t.is_hero and campaign != null and not t.hero_key.is_empty():
			atex = _art.texture_of(campaign.def_of(t.hero_key))
		if atex != null:
			draw_texture_rect(atex, av, false)
			draw_rect(av, DdTheme.PANEL_EDGE, false, 1.0)
		else:
			var pcol: Color = DdTheme.HARM.darkened(0.45) if not t.is_hero \
				else DdTheme.PARTY.darkened(0.45)
			draw_rect(av, pcol)
			draw_rect(av, DdTheme.PANEL_EDGE, false, 1.0)
			var nm0: String = DdNames.unit_name(t.def_id)
			_text(Vector2(av.position.x, av.position.y + 24.0),
				nm0.substr(0, 1), DdTheme.FONT_BD, DdTheme.DIM,
				HORIZONTAL_ALIGNMENT_CENTER, av.size.x)
		# 名字要限宽（M197）：这里原来不传宽度，长名字（「土匪火枪手」）会一路
		# 画到右边的「0%」和血条上 —— 用户报的「文字重叠」就是这一处。
		_text(Vector2(rr.position.x + 76.0, mid + 6.0),
			DdTheme.ellipsis(DdNames.unit_name(t.def_id), _font, 168.0, DdTheme.FONT_BD),
			DdTheme.FONT_BD, DdTheme.TEXT if t.is_hero else DdTheme.HARM,
			HORIZONTAL_ALIGNMENT_LEFT, 168.0)
		# 实际命中率（M112）：技能卡上写的「命中 +85%」是**己方**的修正，
		# 对着这一只具体能不能打上，还要减去它的闪避、加上双方的 buff。
		# 公式直接用规则层那一份（`DamageFormula.hit_chance`），界面**不自己算** ——
		# 两套公式迟早会对不上，而玩家会以界面为准去骂规则。
		var hc_pct: int = -1
		if _battle != null and act is Dictionary and not (act as Dictionary).is_empty():
			var sp2: Dictionary = _battle.build_spec(actor, act as Dictionary, t)
			if not sp2.is_empty():
				var hcv: float = DamageFormula.hit_chance(
					float(sp2.get("acc", 0.0)), float(sp2.get("dodge", 0.0)),
					float(sp2.get("cutoff_miss", 0.0)), float(sp2.get("cutoff_hit", 0.95)))
				hc_pct = int(round(hcv * 100.0))
		# 血条 + 数字贴右
		var bw2: float = 170.0
		var hb := Rect2(rr.end.x - bw2 - 84.0, mid - 7.0, bw2, 14.0)
		if hc_pct >= 0:
			# 右边界再退 6px（M197）：原来贴着血条，两位数命中率会压到条头上
			_text(Vector2(hb.position.x - 72.0, mid - 1.0), "%d%%" % hc_pct,
				DdTheme.FONT_BD,
				DdTheme.OK if hc_pct >= 85 else (DdTheme.WARN if hc_pct >= 60
					else DdTheme.CRIT),
				HORIZONTAL_ALIGNMENT_RIGHT, 60.0)
		# 目标是我方队友时用绿色（M197）：治疗/增益技能对着自己人，
		# 血条还长成敌人那样，玩家会以为选错了目标。
		_bar(hb, float(t.hp) / float(maxi(1, t.base_hp)), _hp_color(t.is_hero),
			DdTheme.HP_TRACK)
		_text(Vector2(hb.end.x + 6.0, mid + 5.0), "%d/%d" % [t.hp, t.base_hp],
			DdTheme.FONT_SM, DdTheme.TEXT, HORIZONTAL_ALIGNMENT_LEFT, 76.0)
		if t.dead:
			# 尸体也能打（M73），但要一眼看出它不是活人
			_text(Vector2(rr.position.x + 36.0, mid - 14.0), "残骸",
				DdTheme.FONT_TAG, DdTheme.WARN)


## 技能图标分类（M64 第十六轮）。
##
## 六个类，不是每个技能一张图：技能有 105 个，逐个画不可能，
## 而玩家真正需要区分的是「这一招是打人、是治人、还是挪位置」。
##
## 判定顺序是**刻意排的**，不是随便写的：
##   1. 有治疗量 → 治疗（带位移的治疗技也还是治疗）；
##   2. 有 move → 位移；
##   3. 目标标记是友方 → 增益；
##   4. 效果名里带控制/持续伤害 → 减益；
##   5. 剩下按攻击距离分近战/远程。
##
## 第 4 步只能靠关键词：数据里的 `effect` 是效果名字符串（"Unholy Killer 1"），
## 没有结构化的「减益」标记。所以这一档会漏——但漏了只会退回近战/远程，
## 不会错成相反的意思。
const SKILL_ICON_KEYS: Array = [
	"stun", "bleed", "poison", "blight", "weak", "vuln", "horror", "daze", "suppress",
]


## 按**原始技能 level 数据**判定（公会屏用）。
##
## 战斗屏拿到的是 `Combatant.build_actions()` 解析后的 action（friendly 已算好），
## 公会屏只有 `{id, levels:[...]}` 原始字典，所以这里再解一次 target 掩码。
## 两处判据必须一致，否则同一招在战斗里是号角、在公会里变成破盾。
## 技能图标：原版优先，取不到退回「按类型猜」的那 6 张（M129）。
func _skill_icon_tex(hid: String, sid: String) -> Texture2D:
	var art: Texture2D = _skill_icon_art(hid, sid)
	if art != null:
		return art
	return _skin.texture("icons", _skill_icon_level(_skill_level_of(hid, sid)))


## 某个技能的**原版图标**（M129）。
##
## 原工程每个职业有 7 张 `heroes/<def>/<def>.ability.<one..seven>.png`
## （72×72），顺序和 `heroes.json` 里 `skills` 数组一一对应。
## 这比原来那 6 张「按类型猜」（近战/远程/治疗…）准确得多 ——
## 同一套剑的技能，原版画的是各自的图案，不是同一个「近战」标记。
##
## 取不到（怪物技能、新加的技能）返回 null，调用方退回分类图标。
func _skill_icon_art(hid: String, sid: String) -> Texture2D:
	# 缓存（M133）：这个函数在战斗/公会/名册里**每帧**被调，每次都拼路径 + 查表。
	# 桌面看不出，手机上（res:// 走 PCK）这些开销会叠在每帧绘制上。
	var ck: String = hid + "|" + sid
	if _skill_icon_cache.has(ck):
		return _skill_icon_cache[ck]
	if campaign == null or db == null:
		return null
	var def: String = campaign.def_of(hid)
	var h: Dictionary = db.hero(def)
	if h.is_empty():
		return null
	var idx: int = 0
	for raw in (h.get("skills", []) as Array):
		if typeof(raw) != TYPE_DICTIONARY:
			continue
		idx += 1
		if str((raw as Dictionary).get("id", "")) == sid:
			break
	if idx <= 0:
		return null
	var path: String = "res://assets/art/ui/icons/skill/%s/%d.png" % [def, idx]
	if not ResourceLoader.exists(path):
		_skill_icon_cache[ck] = null
		return null
	var tex: Texture2D = load(path) as Texture2D
	_skill_icon_cache[ck] = tex
	return tex


func _skill_icon_level(lv: Dictionary) -> String:
	if lv.has("heal") and lv.get("heal") != null:
		return "skill_heal"
	var mv: Variant = lv.get("move", [])
	if mv is Array and not (mv as Array).is_empty():
		return "skill_move"
	if str(lv.get("target", "")).contains("@"):
		return "skill_buff"
	var eff_text: String = ""
	var ev: Variant = lv.get("effect", "")
	if ev is String:
		eff_text = (ev as String).to_lower()
	elif ev is Array:
		for e in (ev as Array):
			eff_text += " " + str(e).to_lower()
	for k in SKILL_ICON_KEYS:
		if eff_text.contains(str(k)):
			return "skill_debuff"
	return "skill_melee" if str(lv.get("type", "melee")) == "melee" else "skill_ranged"


## 从英雄原始定义里取某个技能的首级数据。
func _skill_level_of(hid: String, sid: String) -> Dictionary:
	var h: Dictionary = db.hero(campaign.def_of(hid))
	for raw in (h.get("skills", []) as Array):
		if typeof(raw) != TYPE_DICTIONARY:
			continue
		var d: Dictionary = raw
		if str(d.get("id", "")) != sid:
			continue
		var lvs: Array = d.get("levels", [])
		if lvs.is_empty():
			return d
		# 取**当前等级**那一份（M126）：描述和数值要跟着技能等级变，
		# 否则升到 4 级之后卡上还写着 1 级的数字。
		var lv_i: int = clampi(campaign.skill_level_of(hid, sid), 0, lvs.size() - 1)
		return (lvs[lv_i] as Dictionary)
	return {}


## 战斗技能卡的图标：英雄的原版图标优先，怪物/取不到退回分类（M129）。
func _action_icon_tex(action: Dictionary, actor: Combatant) -> Texture2D:
	if actor != null and actor.is_hero and not actor.hero_key.is_empty():
		var art: Texture2D = _skill_icon_art(actor.hero_key, str(action.get("id", "")))
		if art != null:
			return art
	return _skin.texture("icons", _skill_icon(action))


func _skill_icon(action: Dictionary) -> String:
	if float(action.get("heal", 0.0)) > 0.0:
		return "skill_heal"
	var mv: Variant = action.get("move", [])
	if mv is Array and not (mv as Array).is_empty():
		return "skill_move"
	if bool(action.get("friendly", false)):
		return "skill_buff"
	for e in (action.get("effects", []) as Array):
		var low: String = str(e).to_lower()
		for k in SKILL_ICON_KEYS:
			if low.contains(str(k)):
				return "skill_debuff"
	return "skill_melee" if str(action.get("type", "melee")) == "melee" else "skill_ranged"


func _action_summary(action: Dictionary, actor: Combatant) -> String:
	var bits: Array = []
	if float(action.heal) > 0.0:
		bits.append("治疗 %d-%d" % [int((action.heal_range as Array)[0]), int((action.heal_range as Array)[1])])
	var rng_arr: Array = action.dmg_range
	if rng_arr.size() >= 2:
		bits.append("伤害 %d-%d" % [int(rng_arr[0]), int(rng_arr[1])])
	elif absf(float(action.dmg_mod)) > 0.001:
		bits.append("修正 %+.0f%%" % (float(action.dmg_mod) * 100.0))
	# 「命中 +X%」「暴击 +X%」不再进摘要（M72）：字号提了两档之后，
	# 卡片第二行只放得下 10 个字，这两项最不重要 ——
	# 真实命中率在瞄准态直接标在目标头上，比这里写「+15%」有用得多。
	if bool(action.get("is_guard", false)):
		bits.append("守护")
	if bool(action.get("is_riposte", false)):
		bits.append("反击")
	# 位次（M186）：这一条是用户提出的核心缺口 ——
	# 「这个技能要在几号位放、能打到对面几号位」，原来**一个字都没写**，
	# 只能靠长按或者实战猜。DD1 的 tooltip 里这两项是必列的。
	var lm2: int = int(action.get("launch_mask", 0))
	var tm2: int = int(action.get("target_mask", 0))
	if lm2 > 0:
		bits.append("自发 %s" % _mask_text(lm2))
	if tm2 > 0:
		bits.append("%s %s" % ["友" if bool(action.friendly) else "敌", _mask_text(tm2)])
	else:
		bits.append("敌" if not bool(action.friendly) else "友")
	if bool(action.target_aoe):
		bits.append("全体")
	return " · ".join(bits)


## 技能的位移角标（M53）：`进1` / `退3`，没有位移就返回空串。
func _move_badge(action: Dictionary) -> String:
	var mv: Variant = action.get("move", [])
	if not (mv is Array) or (mv as Array).size() < 2:
		return ""
	var back: int = maxi(0, int((mv as Array)[0]))
	var fwd: int = maxi(0, int((mv as Array)[1]))
	if fwd > 0:
		return "进%d" % fwd
	if back > 0:
		return "退%d" % back
	return ""


func _crit_pct(u: Combatant) -> float:
	return u.crit() * 100.0


## 瞄准态的命中率预览（M65）。
##
## 必须走规则层的 `build_spec` + `DamageFormula.hit_chance`，
## 不能在界面里另写一份 `acc - dodge`：光照、怪癖、技能的 `atk` 修正
## 全在 spec 里，手算一份就是「显示 78%、实际 62%」的来源。
func _preview_hit(actor: Combatant, action: Dictionary, target: Combatant) -> float:
	if _battle == null or actor == null or target == null:
		return 0.0
	var spec: Dictionary = _battle.build_spec(actor, action, target)
	return DamageFormula.hit_chance(float(spec.get("acc", 0.0)),
		float(spec.get("dodge", 0.0)), float(spec.get("cutoff_miss", 0.0)),
		float(spec.get("cutoff_hit", 0.95)))


# ============================================================
# 结算屏
# ============================================================

## 胜利屏（M46）。
##
## 这是全项目唯一的「结束」：四个区域首领都清掉之后的下一趟结算。
## 刻意做得很简单——一张卡、几个数字、两个按钮。
## 加一段剧情文本反而更差：本作没有剧情系统，写两句煽情的话只会显得假。
func _draw_victory() -> void:
	_header("战役完成", "")
	var cx: float = size.x * 0.5

	# 背景压一层暗色，让这张卡从任何状态下都能立住
	draw_rect(Rect2(0.0, 48.0, size.x, size.y - 48.0), Color(0.02, 0.02, 0.025, 0.82))

	# 竖向居中（M63）：这一屏的内容原本写死在 56~538，
	# 1334 高时下面空 800px（占 60%），整屏像只画了上半页。
	# 通关闭幕不是表单，居中的一块「海报」比贴顶更对。
	# 内容自身高 498，按剩余高度算出上移量，所有 y 统一加它。
	var vy: float = maxf(0.0, (size.y - 48.0 - 498.0) * 0.5 - 8.0)

	# 完成纹章（M61）：整屏唯一的「你赢了」的时刻，值得一枚完整的盾。
	if _ico("emblem_done") != null:
		_draw_ico("emblem_done", Vector2((size.x - 76.0) * 0.5, 56.0 + vy), 76.0)
	_text(Vector2(0, 168.0 + vy), "四境皆平", DdTheme.FONT_DISPLAY, DdTheme.LIGHT,
		HORIZONTAL_ALIGNMENT_CENTER, size.x)
	_text(Vector2(0, 214.0 + vy), "荒野、墓穴、巢穴、海湾的首领全部被讨伐", DdTheme.FONT_MD, DdTheme.DIM,
		HORIZONTAL_ALIGNMENT_CENTER, size.x)

	var card := Rect2(cx - 250, 250.0 + vy, 500, 194)
	_panel(card, DdTheme.PANEL_DEEP)

	var rows: Array = [
		["远征趟数", "%d 趟" % campaign.expeditions],
		["历经周数", "%d 周" % campaign.week],
		["首领讨伐", "%d / 4" % campaign.bosses_cleared()],
		["名册人数", "%d 人（存活 %d）" % [campaign.hero_ids().size(), campaign.alive_ids().size()]],
		["金币", "%d" % campaign.gold],
	]
	var y: float = card.position.y + 34.0
	for r in rows:
		_text(Vector2(card.position.x + 30, y), str(r[0]), DdTheme.FONT_BD, DdTheme.DIM)
		_text(Vector2(card.position.x + 200, y), str(r[1]), DdTheme.FONT_BD, DdTheme.TEXT)
		y += 30.0

	# 火漆印（M62）：盖在卡片右下角，**转 -12°**。
	# 正着放像贴纸，歪一点才像「手按上去的一枚印」。
	# 位置避开左边的数值列（值从 card.x+200 开始，印在 card.x+308 之后）。
	if _ico("seal_victory") != null:
		var sc: Vector2 = Vector2(card.end.x - 68.0, card.end.y - 68.0)
		draw_set_transform(sc, deg_to_rad(-12.0), Vector2.ONE)
		draw_texture_rect(_ico("seal_victory"), Rect2(-52.0, -52.0, 104.0, 104.0),
			false, Color(1, 1, 1, 0.9))
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

	# 结束之后还能继续玩：不是「通关即锁档」，本作没有多周目设计，
	# 锁档等于把玩家攒的东西全扔了。
	_add_button(Rect2(cx - 250, 472.0 + vy, 240, 40), "victory_continue", "继续经营这座城镇")
	_add_button(Rect2(cx + 10, 472.0 + vy, 240, 40), "victory_new", "开一档新的", true, true)
	_text(Vector2(0, 538.0 + vy), "战役已完成，但城镇还开着 —— 剩下的时间是你的", DdTheme.FONT_SM,
		DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, size.x)


## 换下弹窗（M168）：列仓库，点一件就「卖掉它、把带不走的换进来」。
func _draw_swap_pick() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.0, 0.0, 0.66))
	var w: float = minf(600.0, size.x - 50.0)
	var h: float = 420.0
	var r := Rect2((size.x - w) * 0.5, (size.y - h) * 0.5, w, h)
	_panel(r, DdTheme.PANEL_DEEP)
	draw_rect(r, DdTheme.PANEL_EDGE, false, 2.0)
	# 带上「要换进来的那件」的图标（M184）：整屏都是图标的地方，
	# 弹窗标题旁边空着反而认不出是哪件。
	var want_ico: Texture2D = _trinket_icon(_swap_ask)
	var wt: float = 20.0
	if want_ico != null:
		draw_texture_rect(want_ico, Rect2(r.position.x + 20.0, r.position.y + 14.0, 44.0, 44.0), false)
		wt = 74.0
	_text(Vector2(r.position.x + wt, r.position.y + 38.0),
		"用仓库里的哪一件换「%s」？" % DdNames.trinket_name(_swap_ask),
		DdTheme.FONT_BD, DdTheme.TEXT, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - wt - 20.0)
	_text(Vector2(r.position.x + 20.0, r.position.y + 62.0),
		"点哪件就卖掉哪件，换新的进来", DdTheme.FONT_SM, DdTheme.FAINT)

	var y: float = r.position.y + 80.0
	var n: int = 0
	for i in campaign.trinket_store.size():
		if y > r.end.y - 100.0:
			break
		var tid: String = str(campaign.trinket_store[i])
		var row := Rect2(r.position.x + 16.0, y, r.size.x - 32.0, 34.0)
		var st: int = _hit_state(row, "tk_swapsell:%d" % i)
		draw_rect(row, DdTheme.BTN_HOVER if st == TILE_HOVER else DdTheme.BTN)
		var row_ico: Texture2D = _trinket_icon(tid)
		var rtx: float = row.position.x + 10.0
		if row_ico != null:
			draw_texture_rect(row_ico, Rect2(row.position.x + 6.0, row.position.y + 3.0, 28.0, 28.0), false)
			rtx = row.position.x + 40.0
		_text(Vector2(rtx, row.position.y + 23.0),
			DdNames.trinket_name(tid), DdTheme.FONT_MD, DdTheme.TEXT,
			HORIZONTAL_ALIGNMENT_LEFT, row.end.x - rtx - 110.0)
		_text(Vector2(row.end.x - 108.0, row.position.y + 23.0),
			"卖 %d 金" % _trinket_sell(tid), DdTheme.FONT_SM, DdTheme.WARN,
			HORIZONTAL_ALIGNMENT_RIGHT, 100.0)
		_add_hit(row, "tk_swapsell:%d" % i)
		y += 38.0
		n += 1
	if n == 0:
		_text(Vector2(r.position.x + 20.0, y + 20.0), "仓库是空的", DdTheme.FONT_MD, DdTheme.DIM)

	_add_button(Rect2(r.position.x + 16.0, r.end.y - 52.0, r.size.x - 32.0, 38.0),
		"tk_swapcancel", "算了，折价就行")


func _trinket_sell(id: String) -> int:
	if campaign.shop == null:
		return 0
	return campaign.shop.trinket_sell_price(id)


func _draw_result() -> void:
	if exp == null:
		return
	var s: Dictionary = exp.summary()
	var title: String = "远征结束"
	var color: Color = DdTheme.TEXT
	match str(s.get("end_reason", "")):
		"complete":
			title = "走出地牢"
			color = DdTheme.OK
		"wipe":
			title = "全队覆没"
			color = DdTheme.WARN
		"retreat":
			title = "撤退"
			color = DdTheme.LIGHT
		"incomplete":
			# M32 起这条不只属于首领任务：清剿没清完就走，同样落在这里。
			# 标题里带上没完成的目标，否则玩家只看到「任务未完成」，
			# 不知道是没杀首领还是漏了两场仗。
			title = "任务未完成 · %s" % str(s.get("quest_goal", ""))
			if exp != null and not exp.quest_goal.is_empty():
				var cid: String = str(exp.quest_goal.get("curio", ""))
				title = "任务未完成 · " + QuestGoal.describe(exp.quest_goal, exp.quest_state(),
					DdNames.curio_name(cid) if not cid.is_empty() else "")
			color = DdTheme.WARN

	_header("结算", "点下面的按钮回城镇")
	_text(Vector2(0, 128), title, DdTheme.FONT_DISPLAY, color, HORIZONTAL_ALIGNMENT_CENTER, size.x)

	var cx: float = size.x * 0.5
	# 卡片高度从 424 提到 470（M25）：结算里最坏情况要放
	# 统计 10 行 + 金币 + 传家宝 + 宝石 + 经验 + 升级 + 饰品 + 阵亡 8 段，
	# 按原来的行距会掉出卡片底边。行距从 31 压到 26，纵向腾了 50。
	# M63：这屏原来只画到 y≈700，下面 634px（48%）全黑。
	# 改成「统计卡 + 战利品卡」两段，按钮贴底 —— 屏幕就没有空的了。
	var btn_h: float = 56.0
	var btn_y: float = size.y - 44.0 - btn_h
	# 10 行 × 31 + 上下留白 = 404。原来 470 会在最后一行下面空 233px，
	# 而下面那张战利品卡又挤满了 —— 两张卡的高度本来就该按内容分配。
	var card := Rect2(cx - 320, 138, 640, 404)
	_panel(card, DdTheme.PANEL_DEEP)
	var loot_card := Rect2(cx - 320, card.end.y + 14.0, 640, btn_y - 26.0 - (card.end.y + 14.0))
	_panel(loot_card, DdTheme.PANEL_DEEP)

	var lines: Array = [
		["推进", "%d / %d 步" % [int(s.steps_done), int(s.steps_total)]],
		["遭遇", "%d 场 · 共 %d 轮" % [int(s.battles), int(s.rounds)]],
		["阵亡", "%d 人" % int(s.hero_deaths)],
		["崩溃 / 美德", "%d / %d" % [int(s.afflictions), int(s.virtues)]],
		["陷阱", "%d 次 · 躲开 %d" % [int(s.get("traps", 0)), int(s.get("traps_dodged", 0))]],
		["障碍", "%d 处 · 凿开 %d" % [int(s.get("obstacles", 0)), int(s.get("obstacles_cleared", 0))]],
		["心脏骤停", "%d 次" % int(s.heart_attacks)],
		["终局血量", "%.0f%%" % (float(s.hp_end) * 100.0)],
		["终局压力", "%.0f / 200" % float(s.stress_end)],
		["剩余补给", "光照 %.0f · 口粮 %d · 火把 %d · 铁锹 %d" % [
			float(s.light_end), int(s.food_end), int(s.torch_end), int(s.get("shovel_end", 0))]],
	]
	var y: float = card.position.y + 34.0
	for line in lines:
		_text(Vector2(card.position.x + 30, y), str(line[0]), DdTheme.FONT_BD, DdTheme.DIM)
		_text(Vector2(card.position.x + 190, y), str(line[1]), DdTheme.FONT_BD, DdTheme.TEXT)
		y += 31.0

	# —— 战利品卡：这一趟真正的产出 ——
	# 占了原来那 634px 空白，并且金币/传家宝改用图集图标（M63）：
	# 「半身像 ×3、画像 ×3、纹章 ×7、地契 ×3」21 个字读起来是账本，
	# 四个图标并排就一眼看清这趟捡了什么。
	var lx: float = loot_card.position.x + 34.0
	var ly: float = loot_card.position.y + 50.0
	_text(Vector2(lx, ly), "本趟所得", DdTheme.FONT_LG, DdTheme.TEXT)

	var got_gold: int = int(_settle_gain.get("gold", 0))
	var q_gold: int = int(_settle_gain.get("quest_gold", 0))
	ly += 62.0
	var gx: float = lx
	if _ico("icon_gold") != null:
		gx = _draw_ico("icon_gold", Vector2(lx, ly - 34.0), 46.0) + 14.0
	_text(Vector2(gx, ly), "+%d" % got_gold, DdTheme.FONT_H1, DdTheme.CRIT)
	if q_gold > 0:
		# 金币分两笔账（M46）：路上捡的 + 交差拿的。
		# 只报总数的话，玩家看到「一趟 4658」会以为掉率变了 ——
		# 而其中 3000 是固定的任务报酬，跟运气无关。
		var gw: float = _font.get_string_size("+%d" % got_gold, HORIZONTAL_ALIGNMENT_LEFT,
			-1, DdTheme.FONT_H1).x
		_text(Vector2(gx + gw + 14.0, ly - 2.0),
			"其中任务奖励 %d" % q_gold, DdTheme.FONT_MD, DdTheme.DIM)

	# 传家宝一行：图标 + ×N
	var hb: Dictionary = _settle_gain.get("heirlooms", {})
	var hx2: float = lx
	var hy: float = ly + 74.0
	var any_h: bool = false
	for k in hb.keys():
		var n: int = int(hb[k])
		if n <= 0:
			continue
		any_h = true
		var kid2: String = str(k)
		if _ico("icon_" + kid2) != null:
			hx2 = _draw_ico("icon_" + kid2, Vector2(hx2, hy - 34.0), 40.0) + 6.0
			_text(Vector2(hx2, hy), "×%d" % n, DdTheme.FONT_BD, DdTheme.TEXT)
			hx2 += _font.get_string_size("×%d" % n, HORIZONTAL_ALIGNMENT_LEFT, -1,
				DdTheme.FONT_BD).x + 34.0
		else:
			_text(Vector2(hx2, hy), "%s ×%d" % [DdNames.heirloom_name(kid2), n],
				DdTheme.FONT_BD, DdTheme.TEXT)
			hx2 += 130.0
	if not any_h:
		_text(Vector2(hx2, hy), "这一趟没有传家宝", DdTheme.FONT_MD, DdTheme.FAINT)
	# 剩余明细落到卡片下半部：上半是「得了什么」（图标），下半是「细节」（文字）。
	# 全挤在图标下面会让卡片下半截空 400px，分两段之后留白变成节奏。
	y = maxf(hy + 56.0, loot_card.position.y + loot_card.size.y * 0.52)

	# —— 首领讨伐（M46）——
	# 只在「这一趟真的清掉了某个区域的首领」时报。
	# 平时不报进度：进度放在城镇屏，结算屏是「这趟发生了什么」，
	# 不是「战役打到哪了」——两件事混在一起，玩家会找不到重点。
	var boss_reg: String = str(_settle_gain.get("boss_cleared", ""))
	if not boss_reg.is_empty():
		y += 24.0
		var bt: int = int(_settle_gain.get("bosses_total", 0))
		_text(Vector2(loot_card.position.x + 34.0, y),
			"首领讨伐 · %s   累计 %d / 4%s" % [DdNames.dungeon_name(boss_reg), bt,
				"    ★ 全部区域已清剿" if bt >= 4 else ""],
			DdTheme.FONT_BD, DdTheme.LIGHT)

	# 宝石已经折进上面的金币，这里只报件数——否则玩家会以为还有一笔没进账
	var gem_counts: Dictionary = _settle_gain.get("gems", {})
	var gem_n: int = 0
	for gk in gem_counts.keys():
		gem_n += int(gem_counts[gk])
	if gem_n > 0:
		y += 20.0
		_text(Vector2(loot_card.position.x + 34.0, y),
			"附带宝石 %d 颗（已折入金币）" % gem_n, DdTheme.FONT_MD, DdTheme.FAINT)

	# —— 决心经验（M25）——
	# 这是这一趟里唯一「只要完成就一定有、而且永久留着」的收获。
	# 没升级也要报：不报的话玩家不知道「再打一趟就能升」还差多远，
	# 而等级现在决定了能穿几阶装备、能进哪些本。
	var xp_gain: int = int(_settle_gain.get("xp", 0))
	if xp_gain > 0:
		y += 22.0
		_text(Vector2(loot_card.position.x + 34.0, y), "经验 +%d（全队）" % xp_gain, DdTheme.FONT_MD, DdTheme.OK)
	var ups: Dictionary = _settle_gain.get("levelups", {})
	if not ups.is_empty():
		y += 18.0
		# 名字最多列两个：四个人一起升级时，全列出来有 36 个字（约 430px），
		# 而这一栏从 x+190 到卡片右边只有 420px——正好会顶出边框。
		var names_u: Array = []
		var max_lv: int = 0
		for uk in ups.keys():
			names_u.append(_hero_label(str(uk)))
			max_lv = maxi(max_lv, campaign.resolve_of(str(uk)))
		var tail: String = "" if names_u.size() <= 2 else " 等 %d 人" % names_u.size()
		_text(Vector2(loot_card.position.x + 34.0, y),
			"升级：%s%s → Lv%d" % ["、".join(names_u.slice(0, 2)), tail, max_lv], DdTheme.FONT_MD, DdTheme.OK)

	# —— 饰品：这一期唯一「拿到了就能改变下次出发」的东西 ——
	# 件数要和进仓库分开报：仓库满或超同名上限时，掉出来的东西会进不去，
	# 只报「掉了 2 件」而实际一件没进，玩家会以为存档坏了。
	var tids: Array = _settle_gain.get("trinket_ids", [])
	var dropped: int = int(_settle_gain.get("trinkets_dropped", 0))
	if not tids.is_empty() or dropped > 0:
		y += 22.0
		# 每件带形态图标横排（M64 第十六轮）：这一行原来是把名字用「、」串起来，
		# 「先祖的手枪、蛇油、闪避石」读起来是一句话；带上图标之后是「三件东西」。
		# 最多报 3 件，再多卡片会顶到右边框。
		var ttx: float = loot_card.position.x + 34.0
		_text(Vector2(ttx, y), "饰品", DdTheme.FONT_MD, DdTheme.CRIT)
		ttx += 44.0
		for k in mini(tids.size(), 3):
			var tid2: String = str(tids[k])
			var tico: Texture2D = _trinket_icon(tid2)
			if tico != null:
				draw_texture_rect(tico, Rect2(ttx, y - 4.0, 22.0, 22.0), false)
				ttx += 26.0
			var tn: String = DdNames.trinket_name(tid2)
			_text(Vector2(ttx, y), tn, DdTheme.FONT_MD, DdTheme.CRIT)
			ttx += _font.get_string_size(tn, HORIZONTAL_ALIGNMENT_LEFT, -1,
				DdTheme.FONT_MD).x + 14.0
		if tids.size() > 3:
			_text(Vector2(ttx, y), "等 %d 件" % tids.size(), DdTheme.FONT_MD, DdTheme.DIM)
		if tids.is_empty():
			_text(Vector2(ttx, y), "无", DdTheme.FONT_MD, DdTheme.CRIT)
		if dropped > 0:
			y += 18.0
			var refund_n: int = int(_settle_gain.get("trinket_refund", 0))
			# 文案要写清「哪个仓库」（M170）：原来写「仓库满或同名上限」，
			# 玩家第一反应是「背包格子」—— 可我们根本没有背包格子。
			# 卡住他的是**饰品仓库**（`campaign.store_slots` = 16，和原版一样 4×4）。
			var dline: String = "另有 %d 件没能带走（饰品仓库 %d/%d 已满，或同名上限）" % [
				dropped, campaign.trinket_store.size(), campaign.store_slots]
			if refund_n > 0:
				dline += "，已折价 +%d 金" % refund_n
			_text(Vector2(loot_card.position.x + 34.0, y), dline,
				DdTheme.FONT_MD, DdTheme.WARN,
				HORIZONTAL_ALIGNMENT_LEFT, loot_card.size.x - 68.0)
			# 「换下」入口（M168）：折价只是保底，玩家真正要的是**自己挑**
			# ——用仓库里哪一件去换这趟掉的东西。
			var refused: Array = _settle_gain.get("trinket_refused", [])
			var yy: float = y + 24.0
			var shown: int = 0
			for rr in refused:
				if shown >= 3:
					break
				var rid: String = str((rr as Dictionary).get("id", ""))
				if rid.is_empty():
					continue
				_text(Vector2(loot_card.position.x + 34.0, yy),
					"· " + DdNames.trinket_name(rid), DdTheme.FONT_MD, DdTheme.WARN,
					HORIZONTAL_ALIGNMENT_LEFT, loot_card.size.x - 180.0)
				_add_button(Rect2(loot_card.end.x - 138.0, yy - 18.0, 100.0, 26.0),
					"tk_swap:" + rid, "换下", true)
				yy += 30.0
				shown += 1

	var deaths: Array = _settle_gain.get("deaths", [])
	if not deaths.is_empty():
		y += 24.0
		var names: Array = []
		for d in deaths:
			names.append(_hero_label(str(d)))
		_text(Vector2(loot_card.position.x + 34.0, y), "永久损失：" + "、".join(names), DdTheme.FONT_MD, DdTheme.WARN)

	# —— 队伍状态（M63）——
	# 这趟东西少的时候（全灭只报一句「永久损失」），战利品卡下半截会空 300px 以上，
	# 空卡片比留白更显眼，看着像「这屏没画完」。而「打完这趟谁的压力涨到多少」
	# 是玩家进城镇前唯一要做的判断（该送谁去疗养院），用这块空白装它正好。
	# 剩余空间不够 132 就不画：宁可留白，也不能压到「回城镇」按钮上。
	var left: float = loot_card.end.y - 20.0 - y
	# 行高从 26 提到 30，给头像留位置；需要的总高跟着人数算，
	# 写死 132 的话四人队会正好差几像素、整块不画。
	var need: float = 52.0 + float(mini(exp.hero_ids.size(), 4)) * 30.0
	if left >= need and not exp.hero_ids.is_empty():
		y += 26.0
		_divider(loot_card.position.x + 30.0, y, loot_card.size.x - 60.0)
		y += 26.0
		_text(Vector2(loot_card.position.x + 34.0, y), "队伍状态", DdTheme.FONT_BD, DdTheme.DIM)
		# 本趟染上什么（M113）：`settle()` 一直有 `quirks` / `diseases` 计数，
		# 结算屏从来没读过它们 —— 玩家要回英雄面板一个个点开才知道谁中招了。
		# 注意 diseases 是 quirks 的子集（染病时两个计数都 +1）。
		var q_gain: int = int(_settle_gain.get("quirks", 0))
		var d_gain: int = int(_settle_gain.get("diseases", 0))
		var q_only: int = maxi(0, q_gain - d_gain)
		if d_gain > 0 or q_only > 0:
			var b2: Array = []
			if d_gain > 0:
				b2.append("疾病 %d" % d_gain)
			if q_only > 0:
				b2.append("怪癖 %d" % q_only)
			_text(Vector2(loot_card.position.x + 190.0, y),
				"本趟染上 " + " · ".join(b2), DdTheme.FONT_MD, DdTheme.WARN,
				HORIZONTAL_ALIGNMENT_RIGHT, loot_card.size.x - 220.0)
		for hid in exp.hero_ids:
			var hk: String = str(hid)
			y += 30.0
			var hr: Dictionary = campaign.hero(hk)
			var alive_h: bool = bool(hr.get("alive", false))
			var st2: float = float(hr.get("stress", 0.0))
			# 头像 22×28（M64 第十三轮）：行高 30 塞不下纹章，
			# 但「谁死了」这件事头像比名字快得多。
			var pr5 := Rect2(loot_card.position.x + 34.0, y - 23.0, 21.0, 28.0)
			_draw_hero_badge(hk, pr5, alive_h)
			_text(Vector2(loot_card.position.x + 64.0, y), _hero_label(hk), DdTheme.FONT_MD,
				DdTheme.TEXT if alive_h else DdTheme.FAINT)
			_text(Vector2(loot_card.position.x + 190.0, y),
				"压力 %.0f" % st2, DdTheme.FONT_MD,
				DdTheme.STRESS if st2 >= 100.0 else DdTheme.DIM)
			# 经验进度（M113）：结算屏原来只报「全队 +N」，个体差多少不知道。
			# 而「再打一趟能不能升」直接决定下一趟带不带他 —— 装备阶在名册里随时能看，
			# 这个进度只有这里能看，所以让位给它。
			var xp_n: int = campaign.xp_of(hk)
			var xp_need: int = campaign.xp_to_next(hk)
			_text(Vector2(loot_card.position.x + 300.0, y),
				("Lv%d · 经验 %d/%d" % [campaign.resolve_of(hk), xp_n, xp_need])
					if xp_need > 0 else ("Lv%d · 满级" % campaign.resolve_of(hk)),
				DdTheme.FONT_MD, DdTheme.DIM)
			_text(Vector2(loot_card.position.x + 470.0, y),
				"存活" if alive_h else "阵亡", DdTheme.FONT_TAG,
				DdTheme.OK if alive_h else DdTheme.WARN)

	_add_button(Rect2(cx - 320, btn_y, 640, btn_h), "restart", "回城镇")


# ============================================================
# 出发准备（M16）
# ============================================================

## 保底包：和 M13 之前硬编码的默认完全一致
## （`DEFAULT_SUPPLY_PACK` 六种各 1 + 火把 4 + 口粮 4 + 铁锹 1）。
##
## 为什么要有它：新档金币是 0。如果出发必须先买补给，第一趟就卡死了。
## 保底包让「不花钱也能走」，钱只花在「比保底多带的那部分」上。
func _default_prep_pack() -> Dictionary:
	var out: Dictionary = {
		"torch": 4, "food": 4, "shovel": 1,
		"bandage": 1, "antivenom": 1, "medicinal_herbs": 1,
		"holy_water": 1, "skeleton_key": 1,
	}
	# 商店预买的补给叠加进来（M66）：默认包是「没库存时的建议」，
	# 库存是「已经付过钱的」，两者相加才对——玩家在商店买了 3 根火把，
	# 出发时就该看到 7 根，其中 3 根不再收钱。
	# 加完按携带上限截断，否则出发结算会直接被 over_limit 挡回去。
	if campaign == null or campaign.shop == null:
		return out
	for k in campaign.supplies.keys():
		var n2: int = int(campaign.supplies[k])
		if n2 <= 0:
			continue
		var cur: int = int(out.get(str(k), 0)) + n2
		var lim2: int = campaign.shop.supply_limit(str(k))
		out[str(k)] = mini(cur, lim2) if lim2 > 0 else cur
	return out


## 现在还能招到几个死掉的英雄（免费额度或者钱够）。
##
## 准备屏用它决定「队伍不满 4 人时该不该放人走」：
## 能招就必须先招满，招不到才允许少人出发——两边都是为了避免死循环。
func _recruitable_now() -> int:
	var n: int = 0
	for hid in campaign.hero_ids():
		var hid_s: String = str(hid)
		if bool((campaign.hero(hid_s) as Dictionary).get("alive", false)):
			continue
		if campaign.can_recruit(hid_s):
			n += 1
	return n


## 点一个人：已选就移出，没选就加入。
##
## 满 4 人时加入会先挤掉**最后加入的那个**，而不是拒绝——
## 「点不动」比「换掉一个」更让人困惑。至少保留 1 人：
## 0 人出发在 Battle 里会直接崩，而且也没意义。
func _toggle_party(hid: String) -> void:
	if _prep_party.has(hid):
		if _prep_party.size() <= 1:
			_flash_msg("至少带一个人")
			return
		_prep_party.erase(hid)
	elif _prep_party.size() >= Campaign.PARTY_MAX:
		_prep_party.remove_at(_prep_party.size() - 1)
		_prep_party.append(hid)
	else:
		_prep_party.append(hid)
	_party_persist()
	queue_redraw()


func _adjust_pack(id: String, delta: int) -> void:
	var cur: int = int(_prep_pack.get(id, 0)) + delta
	if campaign.shop != null:
		var lim: int = campaign.shop.supply_limit(id)
		if lim > 0:
			cur = mini(cur, lim)
	_prep_pack[id] = maxi(0, cur)
	campaign.supply_pack = _prep_pack.duplicate()
	campaign.save()
	queue_redraw()


## 支付并出发。
##
## 金币不够时**不阻止出发**：改用保底包（免费），并明说一句。
## 阻止出发会让「打完一趟才有钱」这个循环在第一趟就断掉。
func _launch_with_pack() -> void:
	# 先扣库存再付钱（M66）：商店里预买的补给不该在出发时再收一次。
	# 报错仍然分两种——金币不够就退回保底包，其它原因（超上限）停下来让玩家改。
	var res: Dictionary = campaign.buy_pack_with_stock(_prep_pack)
	if not bool(res.get("ok", false)):
		var why: String = str(res.get("reason", ""))
		if why == "no_gold":
			# 屏幕上只留结论（M200）：整句带数字会在 750 宽的屏上横着冲出去。
			# 具体数字进日志，那里是横向可读的。
			_flash_msg("金币不足，按保底补给出发")
			_add_log("【补给】金币不足（需 %d，有 %d），按保底配给出发" % [
				int(res.get("cost", 0)), campaign.gold], DdTheme.WARN)
			_prep_pack = _restore_prep_pack()
			_state = S_TOWN
			_start_expedition(_prep_size, _prep_level, {}, _prep_party, _prep_quest)
			return
		_flash_msg(_shop_reason(why))
		return
	campaign.save()
	_state = S_TOWN
	_start_expedition(_prep_size, _prep_level, _prep_pack, _prep_party, _prep_quest)


## 出发准备屏的「行程」卡（M198）。
##
## 和选关屏那张 `_draw_board_card` 不是一回事：那边是横卡（一屏四行，宽 ~500），
## 这边是一排里的一张（宽 216）。两处显示的是同一批信息，
## 所以文案来源相同（`_board_rows()`），但**排版各自算** —— 硬套同一套坐标必然错位。
func _draw_prep_card(row: Array, r: Rect2) -> void:
	# 选中态要同时比尺寸、任务类型**和等级**（M29）：
	#   · 中程与首领都是 medium —— 只比尺寸会让两张卡同时高亮
	#   · 同一个尺寸每周的等级不同 —— 只比尺寸+类型会让「中程 1 级」
	#     在标题写着「中程 3 级」时也亮着，玩家会以为自己选错了
	var sel: bool = _prep_size == str(row[0]) and _prep_quest == str(row[4]) \
		and _prep_level == int(row[1])
	var key: String = "prep:%s:%d:%s" % [str(row[0]), int(row[1]), str(row[4])]
	_panel(r, DdTheme.PANEL_HI if sel else DdTheme.PANEL_DEEP)
	_hit_overlay(r, key)
	if sel:
		draw_rect(r, DdTheme.PARTY, false, 2.0)
	var px: float = r.position.x + 10.0
	var pw: float = r.size.x - 20.0
	# 卡片实际只有 84 高（`_hscroll_zone` 上下各吃掉 8），所以行距按 84 排：
	# 标题 22 / 说明 44、62，最后一行离底还有 6px。
	var ty: float = r.position.y + 22.0
	# 标题让出右上角 62px 给「✓ 通关」角标
	_text(Vector2(px, ty), str(row[2]), DdTheme.FONT_MD,
		DdTheme.TEXT if sel else DdTheme.DIM,
		HORIZONTAL_ALIGNMENT_LEFT, pw - 62.0)
	# 「已通关」角标（M198）。固定在右上角、不占说明的行：
	# 说明本身已经要折行，再挤一行会被裁掉 —— 那正是这一轮要修的东西。
	if campaign.is_quest_cleared(_dungeon, str(row[0]), str(row[4]), int(row[1])):
		_text(Vector2(r.end.x - 72.0, ty - 2.0), "✓ 通关", DdTheme.FONT_TAG,
			DdTheme.OK, HORIZONTAL_ALIGNMENT_RIGHT, 62.0)
	# 说明折行（最多 2 行）：216 宽、16px，一行约 12 个汉字，
	# 「清光全图战斗，支路也得去」正好一行放得下，长一点的会折第二行。
	_text_wrap(Vector2(px, ty + 22.0), str(row[3]), DdTheme.FONT_TAG,
		DdTheme.FAINT, pw, 2)
	_add_hit(r, key)


func _draw_prep() -> void:
	# 忙的人（疗养院/减压建筑）**不出现在下面的出战名单里**。
	# 原来这里只写「名册 5 人 · 上限 4 人」，玩家看到名册是满的、名单却少两个，
	# 完全不知道为什么（M93 反馈：以为人"不见了"）。补一句计数。
	var busy_n: int = campaign.alive_ids().size() - campaign.selectable_ids().size()
	var sub: String = "名册 %d 人 · 出战 %d 人 · 金币 %d" % [
		campaign.alive_ids().size(), Campaign.PARTY_MAX, campaign.gold]
	if busy_n > 0:
		sub = "⚠ %d 人在建筑里，本趟不能出征（可去马车补人）    " % busy_n + sub
	_header("出发准备 · %s · %s %d 级" % [DdNames.dungeon_name(_dungeon),
		_size_name_of(_prep_size), _prep_level], sub)

	# —— 左：补给清单 ——
	if campaign.shop == null:
		_text(Vector2(28, 90), "inventory.json 没读到，补给不可用（可按保底包出发）。", DdTheme.FONT_MD, DdTheme.WARN)
		_add_button(Rect2(size.x - 208, 640, 180, 40), "prep_back", "返回")
		return
	# M58：原来左右两栏各 335 宽，竖屏下补给行只有半个屏幕。改成上下排，补给占满宽
	var sw: float = size.x - 56.0
	var y: float = 88.0
	# —— 竖向预算（M63）——
	# 这一屏是「8 项补给 + 4 张行程卡 + 出战卡 + 合计块」四段定高块，
	# 1334 时刚好贴到「出发」按钮上；底部安全区一吃，整串就压到按钮底下——
	# 症状是出战卡的下半排被「出发」按钮盖掉一半（按钮在上层，卡看起来像被切了）。
	# 按差额依次压：补给行高 → 出战/行程卡行距 → 合计块。
	var n_sup: int = campaign.shop.supply_ids().size()
	var n_rows: int = int(ceil(float(campaign.selectable_ids().size()) / 4.0))
	var budget: float = size.y - 186.0 - 100.0
	var need_h: float = float(n_sup) * 72.0 + 26.0 + 100.0 + 26.0 \
		+ (float(n_rows) * 100.0 + 10.0) + 228.0
	var sup_step: float = 72.0
	var sup_h: float = 64.0
	var pick_step: float = 100.0
	var pick_h: float = 94.0
	var tail_h: float = 228.0
	var over: float = need_h - budget
	if over > 0.0:
		var c1: float = minf(over, float(n_sup) * 14.0)
		sup_step -= c1 / float(maxi(1, n_sup))
		sup_h = minf(64.0, sup_step - 8.0)
		over -= c1
	if over > 0.0:
		var c2: float = minf(over, float(maxi(1, n_rows)) * 16.0)
		pick_step -= c2 / float(maxi(1, n_rows))
		pick_h = minf(94.0, pick_step - 6.0)
		over -= c2
	if over > 0.0:
		tail_h = maxf(170.0, tail_h - over)
	_text(Vector2(28, y), "补给", DdTheme.FONT_BD, DdTheme.TEXT)
	y += 12.0
	for sid in campaign.shop.supply_ids():
		var id: String = str(sid)
		var n: int = int(_prep_pack.get(id, 0))
		var price: int = campaign.shop.supply_buy(id)
		var lim: int = campaign.shop.supply_limit(id)
		var rr := Rect2(28, y, sw, sup_h)
		_panel(rr, DdTheme.PANEL_DEEP)
		# 图标（M64 第十六轮）：8 行补给全是文字时只能靠读，
		# 有图之后「解毒剂 / 绷带 / 圣水」一眼分得开。
		var sup_tex: Texture2D = _supply_icon(id)
		var sx: float = rr.position.x + 14.0
		if sup_tex != null:
			var isz: float = minf(40.0, sup_h - 12.0)
			draw_texture_rect(sup_tex, Rect2(rr.position.x + 14.0,
				rr.position.y + (sup_h - isz) * 0.5, isz, isz), false)
			# 图标右沿到 54，名称从 62 起 —— 贴太近时「绷带」两个字会顶上去
			sx = rr.position.x + 62.0
		# 行内三样东西按行高比例放：行被压矮之后写死的 26/48 会顶到边框上
		_text(Vector2(sx, rr.position.y + sup_h * 0.42),
			_supply_label(id), DdTheme.FONT_BD, DdTheme.TEXT)
		_text(Vector2(sx, rr.position.y + sup_h * 0.78),
			"%d 金 / 份    上限 %d%s" % [price, lim,
				("    已付 %d" % mini(n, campaign.supply_stock(id)))
					if campaign.supply_stock(id) > 0 else ""],
			DdTheme.FONT_SM, DdTheme.DIM)
		# 减 / 数量 / 加
		var bx: float = rr.position.x + rr.size.x - 176.0
		# M58：原来这两个只有一个悬空的「－」「＋」字符，按下完全没有反馈。
		# 补一个 40×40 的底，走和普通按钮同一套 `_tile()` 三态。
		var by: float = rr.position.y + (sup_h - 40.0) * 0.5
		var sub_r := Rect2(bx, by, 40, 40)
		var add_r := Rect2(bx + 90, by, 40, 40)
		_tile(sub_r, _hit_state(sub_r, "prep_sub:" + id), DdTheme.BTN)
		_text(Vector2(bx, by + 26), "－", DdTheme.FONT_LG, DdTheme.WARN,
			HORIZONTAL_ALIGNMENT_CENTER, 40)
		_text(Vector2(bx + 44, by + 26), "%d" % n, DdTheme.FONT_BD, DdTheme.TEXT if n > 0 else DdTheme.FAINT, HORIZONTAL_ALIGNMENT_CENTER, 40)
		_tile(add_r, _hit_state(add_r, "prep_add:" + id), DdTheme.BTN)
		_text(Vector2(bx + 90, by + 26), "＋", DdTheme.FONT_LG, DdTheme.OK,
			HORIZONTAL_ALIGNMENT_CENTER, 40)
		_add_hit(sub_r, "prep_sub:" + id)
		_add_hit(add_r, "prep_add:" + id)
		# 行内金额也要扣掉库存（M66）：否则九行加起来对不上「合计」那一栏。
		var pay: int = (n - mini(n, campaign.supply_stock(id))) * price
		_text(Vector2(rr.position.x + rr.size.x - 232, by + 26),
			"%d 金" % pay, DdTheme.FONT_MD, DdTheme.DIM, HORIZONTAL_ALIGNMENT_RIGHT, 52)
		y += sup_step

	# —— 右：难度与结算 ——
	var rx: float = 28.0
	var rw: float = size.x - 56.0
	# 行程区起点：补给区下面（补给 8 项 × 72）
	var ry_top: float = y + 26.0
	_text(Vector2(rx, ry_top - 12.0), "行程", DdTheme.FONT_BD, DdTheme.TEXT)
	# 可拖动要写出来（M198）：右边缘被裁半张卡已经是提示，但不够明确 ——
	# 玩家可能以为是排版坏了，而不是"还有"。
	_text(Vector2(rx + 60.0, ry_top - 12.0), "← 左右拖动 →", DdTheme.FONT_TAG,
		DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, rw - 60.0)
	# 和城镇用同一块板子（M26）：这一屏是「换一张卡」的地方，
	# 如果它自己另算一套等级，玩家在这里切一下就和城镇看到的对不上了。
	var rows: Array = _board_rows()
	var ry: float = ry_top
	# 横向滚动（M198）：四张挤在一行里每张只有 ~166 宽，
	# 「清光全图战斗，支路也得去」直接压到下一张卡上 —— 用户截图指的就是这里。
	# 改成固定 216 宽 + 左右拖动，一张卡把标题和说明都说完。
	# 高一格（+16）是为了补回 `_hscroll_zone` 内部上下各 8 的内边距。
	# 但这 16px **必须从预算里出**（`need_h` 已经按 100 算过），
	# 否则行程卡下边缘会压到「出战（已选 4/4 人）」那一行上。
	_hscroll_zone("prep_board", Rect2(rx, ry, rw, pick_step), rows.size(), 216.0, 10.0,
		func(cr: Rect2, i: int) -> void:
			_draw_prep_card(rows[i], cr))

	# —— 出战名单（M18）——
	# 名册 5 人、只能带 4 个，所以这里是一个真实的选择。
	# 点一下切换；满员时加入会挤掉最后加进来的那个（不是拒绝）。
	var py: float = ry + pick_step + 26.0
	# 排序（M176）：**上阵的人按出征顺序排在前面**，其余按强度。
	# 原来整列按强度排，于是「已选 4/4」那四个和下面的没选的人混在一起，
	# 玩家看不出「我这四个人是谁、谁站几号位」—— 而这一屏恰恰是定这个的地方。
	# 这和队伍屏是同一个毛病（M174），只是那一屏改了、这一屏漏了。
	var _pool: Array = _sort_by_power(campaign.selectable_ids())
	var ids_all: Array = []
	for _h_on in _prep_party:
		if _pool.has(str(_h_on)):
			ids_all.append(str(_h_on))
	for _h_rest in _pool:
		if not ids_all.has(str(_h_rest)):
			ids_all.append(str(_h_rest))
	# 够格的人数（M25）。等级锁之后「名册有几个活人」不再是可带人数——
	# 太高级的人会被拒绝，所以门槛必须跟着**够格人数**走。
	# 不这么改的话，一个 6 级的名册去打学徒本会永远显示「还缺 4 人」。
	var fit_ids: Array = []
	for hid_f in ids_all:
		if campaign.can_join(str(hid_f), _prep_level):
			fit_ids.append(hid_f)
	# 门槛 = min(上限, 够格人数)，但**能招人时不许降门槛**。
	# 只降门槛会放 1 人队出门，那是必死，不是「灵活」；
	# 只有真的一个人都招不到了（没钱、没免费额度），才允许少人出发，否则死锁。
	var fillable: int = _recruitable_now()
	var need: int = mini(Campaign.PARTY_MAX, fit_ids.size())
	var must_recruit: bool = need < Campaign.PARTY_MAX and fillable > 0
	var want: int = Campaign.PARTY_MAX if must_recruit else need
	_text(Vector2(rx, py), "出战（已选 %d / %d 人）· 点一下切换" % [
		_prep_party.size(), want], DdTheme.FONT_MD, DdTheme.OK if _prep_party.size() >= want else DdTheme.WARN)
	# 出战卡布局（M27）：名册能到 15 人，一行放不下，改成 6 列 × 最多 3 行。
	# 卡片从 68 压到 52，只留「名字 + Lv」两行——「出征 N 次」这种信息
	# 在这一屏没有决策价值，占着位置反而让人看不清谁够格。
	var per_row: int = 4
	var bw: float = (rw - 10.0 * float(per_row - 1)) / float(per_row)
	for k in ids_all.size():
		var hid: String = str(ids_all[k])
		var picked: bool = _prep_party.has(hid)
		# 等级锁（M25）：带不了的人要**显示出来并说明原因**，
		# 而不是从列表里消失。消失会让玩家以为「这个人没了」，
		# 而真相是「他太高级，不屑于来这种小地方」——这两种感觉完全不同。
		var fit: bool = campaign.can_join(hid, _prep_level)
		var col: int = k % per_row
		var rowi: int = k / per_row
		var br := Rect2(rx + float(col) * (bw + 10.0), py + 10.0 + float(rowi) * pick_step, bw, pick_h)
		_panel(br, DdTheme.PANEL_HI if picked else DdTheme.PANEL_DEEP)
		_hit_overlay(br, "prep_pick:" + hid)
		if picked:
			draw_rect(br, DdTheme.PARTY, false, 2.0)
		# 光靠边框粗细分辨「选没选」在小屏上几乎看不出来，
		# 所以再给一个文字标记——这是唯一能一眼确认的地方。
		# 头像 + 纹章（M64 第十三轮）：四列 166 宽的卡，头像 32×42 放左边就够。
		var ph3: float = minf(br.size.y - 14.0, 42.0)
		var pr3 := Rect2(br.position.x + 8.0, br.position.y + (br.size.y - ph3) * 0.5,
			ph3 * 0.754, ph3)
		_draw_hero_badge(hid, pr3, fit)
		var txp: float = pr3.end.x + 8.0
		_text(Vector2(txp, br.position.y + 20), ("✓ " if picked else "＋ ") +
			_hero_label(hid), DdTheme.FONT_MD, DdTheme.TEXT if picked else (DdTheme.FAINT if fit else DdTheme.CRIT))
		if fit:
			# 够格但等级不够（会吃惩罚）：这一行转警告色，具体代价在下面的队伍摘要里
			var gap_h: int = campaign.level_gap(hid, _prep_level)
			# 这里**不用显示血量**（M185 查证）：英雄在城镇里没有持久血量，
			# `roster` 里根本没有 `hp` 字段 —— 生命是出征时按等级/装备算的，
			# 每趟都从满血开始。所以「带伤上阵」这件事不存在。
			_text(Vector2(txp, br.position.y + 38),
				"Lv%d · 装备 %d 阶" % [campaign.resolve_of(hid), campaign.gear_of(hid)],
				DdTheme.FONT_TAG, DdTheme.WARN if gap_h > 0 else DdTheme.DIM)
			_add_hit(br, "prep_pick:" + hid)
		else:
			# 「高出 2 级就拒绝」是原版唯一的硬门槛，所以这句话要直说：
			# 玩家会以为是 bug（我的人更强了为什么不能带），必须解释。
			_text(Vector2(txp, br.position.y + 38),
				"高出 %d 级" % (campaign.resolve_of(hid) - _prep_level), DdTheme.FONT_TAG, DdTheme.CRIT)

	# 合计要扣掉「商店里已经付过钱」的那部分（M66），否则界面写 1925、
	# 实际扣 1700，玩家会以为算错了。
	var cost: int = campaign.pack_cost_with_stock(_prep_pack)
	var enough: bool = cost <= campaign.gold
	# 三行卡最坏情况占 py+10 ~ py+178，所以合计块从卡底 +18 起，
	# 留 18px 空隙——贴着卡片底边画会让字和边框粘在一起。
	var cy: float = py + 10.0 + float(n_rows) * pick_step + 18.0
	_text(Vector2(rx, cy), "补给合计", DdTheme.FONT_MD, DdTheme.DIM)
	_text(Vector2(rx + 120, cy), "%d 金" % cost, DdTheme.FONT_LG, DdTheme.CRIT if enough else DdTheme.WARN)
	_text(Vector2(rx, cy + 24),
		"余额 %d 金%s" % [campaign.gold, "" if enough else "　— 不足，将按保底补给出发"], DdTheme.FONT_MD, DdTheme.DIM if enough else DdTheme.WARN)
	# 等级惩罚（M29）：不够格的人要在这里说清楚代价。
	# 卡片太小写不下（那是 6 列 × 52 高），而「这趟会吃多少罚」正好是一整队的事，
	# 放队伍摘要里比放在某张卡上更合适。
	var under: int = 0
	var max_gap: int = 0
	for hid_p in _prep_party:
		var g: int = campaign.level_gap(str(hid_p), _prep_level)
		if g > 0:
			under += 1
			max_gap = maxi(max_gap, g)
	var line: String = "出战 %d 人 · 平均装备 %d 阶" % [
		_prep_party.size(), _party_gear_avg(_prep_party)]
	if _prep_party.size() < want:
		line += "　— 不满 %d 人，单挑必死" % want
	elif under > 0:
		# 报「最多」而不是逐人列：队伍里可能同时有差 1 级和差 2 级的人，
		# 逐人列太长，而玩家需要的判断只有一句「这趟大概多疼」。
		line += "　— %d 人低于任务等级：最多进本 +%d 压力、受压 ×%.2f" % [
			under, int(float(max_gap) * Campaign.JOIN_STRESS_PER_LEVEL),
			1.0 + float(max_gap) * Campaign.JOIN_STRESS_MULT_PER_LEVEL]
	_text(Vector2(rx, cy + 48), line, DdTheme.FONT_MD, DdTheme.WARN if (under > 0 or _prep_party.size() < want) else DdTheme.DIM)

	# 不满 `want` 人就不给走：这不是数值平衡，是防手滑——
	# 上一版允许 1 人出发，结果「5 张卡全是尸体只剩 1 个新兵」的档
	# 一路 1v4，玩家看到的是「战斗里只有 1 个人」。
	var ready: bool = want > 0 and _prep_party.size() >= want
	var go_label: String = "出发（%d 金）" % cost if enough else "按保底补给出发"
	if not ready and must_recruit:
		go_label = "先回城镇征召 —— 队伍要满 %d 人" % Campaign.PARTY_MAX
	elif not ready:
		go_label = "还缺 %d 人 —— 名册里够格的人不够" % (want - _prep_party.size())
	# M58：两个按钮贴底。原来写死 y=596 / 652，竖屏下整个悬在页面中段。
	var back_h: float = 56.0
	var back_y: float = size.y - 44.0 - back_h - NAV_H
	var go_y: float = back_y - 12.0 - 64.0
	_add_button(Rect2(rx, go_y, rw, 64.0), "prep_go", go_label, ready)
	_add_button(Rect2(rx, back_y, rw, back_h), "prep_back", "返回城镇")


# ============================================================
# 建筑屏（M22）
# ============================================================

## 六座「对人做事」的建筑共用这一屏。
##
## 不拆成六个屏，是因为它们百分之七十是一样的：左边同样的名册列表、
## 同样的「选中态」、同样的返回按钮。差别只在右侧那几行字和一个动作按钮。
## 拆开会得到六份几乎相同的代码，改一次排版要改六处——
## 而这类重复正是 M13~M19 反复踩的坑（同一套判定两处实现，然后分叉）。
## 建筑升级条（M131）：等级 + 升级价，点一下升一阶。
##
## 放在底部按钮那块的上方 —— 各建筑屏的内容高度都不一样（疗养院 300、
## 马车 520），塞在标题下面会挤到列表；底部这块每屏都是空的。
func _building_upgrade_row(bid: String, y: float, w: float) -> float:
	var lv: int = campaign.building_level(bid)
	var cost: int = campaign.building_upgrade_cost(bid)
	# 高度 44 → 74（M181）：多留一行写「升级后变成什么」。
	# 原来这一条只有一个等级 + 一颗灰按钮，玩家点下去完全不知道买到什么 ——
	# 而这一屏的每一块钱都关系到下周能不能打。
	var box := Rect2(24.0, y, w, 74.0)
	_panel(box, DdTheme.PANEL_DEEP)
	_text(Vector2(box.position.x + 14.0, box.position.y + 28.0),
		"%s · 等级 %d / %d" % [str(_building_meta(bid)[1]), lv, Campaign.BUILDING_MAX_LEVEL],
		DdTheme.FONT_BD, DdTheme.TEXT)
	# 「现在 → 下一级」的效果差
	var now_t: String = _building_effect_text(bid, lv)
	var next_t: String = _building_effect_text(bid, lv + 1)
	var eff: String = now_t if cost < 0 else "%s　→　%s" % [now_t, next_t]
	_text(Vector2(box.position.x + 14.0, box.position.y + 52.0), eff,
		DdTheme.FONT_TAG, DdTheme.DIM if cost < 0 else DdTheme.OK,
		HORIZONTAL_ALIGNMENT_LEFT, box.size.x - 160.0)
	if cost < 0:
		_text(Vector2(box.end.x - 130.0, box.position.y + 28.0), "已满级",
			DdTheme.FONT_TAG, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 116.0)
	else:
		var br := Rect2(box.end.x - 138.0, box.position.y + 18.0, 124.0, 38.0)
		var st: int = _hit_state(br, "bld_up:" + bid)
		var can: bool = campaign.gold >= cost
		# 按钮改成**实心主色**（M181）：原来用 `_tile` 的灰底，
		# 在一条本来就灰的条上等于没有按钮，用户原话「太不显眼了」。
		draw_rect(br, DdTheme.CRIT if can else DdTheme.BTN_OFF)
		draw_rect(br, DdTheme.BTN_HOVER if st == TILE_HOVER and can else DdTheme.CRIT.darkened(0.35), false, 2.0)
		_text(Vector2(br.position.x, br.position.y + 25.0), "升级 · %d 金" % cost,
			DdTheme.FONT_BD, Color(1.0, 0.96, 0.88) if can else DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_CENTER, br.size.x)
		_add_hit(br, "bld_up:" + bid)
	return box.end.y + 10.0


## 某座建筑在某个等级下的效果文字（M181）。
##
## 原来升级条上只有一个「等级 N / 3」，玩家不知道升上去买到什么。
## 这里把「这一级实际改了什么数值」写出来 —— 和 `campaign` 里真正生效的
## 那几处一一对应（减压量、治疗费、库存、折扣），不是编的。
func _building_effect_text(bid: String, lv: int) -> String:
	match bid:
		"tavern":
			return "减压 %d / 次" % (70 + lv * 10)
		"abbey":
			return "减压 %d / 次" % (90 + lv * 10)
		"sanitarium":
			return "治疗费 -%d%%" % (5 * lv)
		"smith":
			return "升级折扣 %d%%" % int(round((1.0 - pow(0.9, float(lv))) * 100.0))
		"wagon":
			return "货架 %d 件" % (Shop.STOCK_SIZE + lv * 2)
		"coach":
			return "可征召 %d 人" % (3 + lv)
		"guild":
			return "技能位 %d" % (4 + lv)
		"graveyard":
			return "墓园位 %d" % (8 + lv * 2)
	return "等级 %d" % lv


func _draw_building() -> void:
	var meta: Array = _building_meta(_building)
	# 商队和墓园没有左栏名册，副标题就别再写「左侧点人」——
	# 它会让玩家去找一个不存在的东西，而这一屏本来就没有可点的人。
	var has_list: bool = _building != "wagon" and _building != "graveyard"
	_header("%s · %s" % [str(meta[1]), str(meta[2])],
		("金币 %d · 左侧点人 · 右下角返回城镇" % campaign.gold) if has_list
		else ("金币 %d · 右下角返回城镇" % campaign.gold))

	var rx: float = 248.0
	var rw: float = size.x - rx - 24.0

	# 墓园和商队不需要选人，直接给整块面板
	if _building == "graveyard":
		var by2: float = size.y - 44.0 - 56.0
		_draw_graveyard(Rect2(rx, 88, rw, by2 - 88.0 - 34.0))
		_add_button(Rect2(rx, by2, rw, 56.0), "bld_back", "返回城镇")
		_text(Vector2(DdTheme.MARGIN, by2 - 14.0), _building_hint(_building),
			DdTheme.FONT_MD, DdTheme.FAINT)
		return
	if _building == "wagon":
		var by3: float = size.y - 44.0 - 56.0
		_draw_wagon(Rect2(rx, 88, rw, by3 - 88.0 - 34.0))
		_add_button(Rect2(rx, by3, rw, 56.0), "bld_back", "返回城镇")
		_text(Vector2(DdTheme.MARGIN, by3 - 14.0), _building_hint(_building),
			DdTheme.FONT_MD, DdTheme.FAINT)
		return

	# —— 左：名册 ——
	var alive: Array = campaign.alive_ids()
	if alive.is_empty():
		_text(Vector2(28, 120), "名册里没有活人，先去马车征召。", DdTheme.FONT_BD, DdTheme.WARN)
		_add_button(Rect2(24.0, size.y - 100.0 - NAV_H, size.x - 48.0, 56.0), "bld_back", "返回城镇")
		return
	# 马车要能选到死人（M28）：复活和「从墓园移除」都作用在他们身上。
	# 其他建筑只列活人——铁匠铺对着一个死人没有可做的事。
	var who: Array = campaign.hero_ids() if _building == "coach" else alive
	if _building_hero.is_empty() or not who.has(_building_hero):
		_building_hero = str(alive[0])

	# 面板高度要**先算**（M181）：名册的步长要用它。
	# 原来名册按 `minf(80, 1080/人数)` 排，10 个人就是 100~900，
	# 而升级条固定落在 `88 + panel_h(700) + 10 = 798` ——
	# 直接压在最后两三个人身上。截图里「强盗 II」就是这么被盖住的。
	var _btn_y: float = size.y - 44.0 - 56.0 - NAV_H
	var _panel_h: float = minf(_btn_y - 88.0 - 34.0 - 64.0, 700.0)
	_text(Vector2(28, 88), "名册 %d 人" % who.size(), DdTheme.FONT_BD, DdTheme.TEXT)
	# 名册列表（M27）：15 人按「68 高一列」排会直接溢出屏幕底部
	# （15 × 78 = 1170，而可用高度只有 600 出头）。
	# 改成两列 × 42 高：8 行 × 46 = 368，从 100 到 468，正好落在面板里。
	# M58：名册改**单列 212 宽**（原来是 2 列 × 118 × 42 的小格子）。
	# 竖屏左侧栏能到 212 宽，一人一行读起来比两列小格子清楚得多。
	# 步长按**面板内部可用高度**算，不再用写死的 1080
	var rstep: float = minf(80.0, (_panel_h - 118.0) / float(maxi(1, who.size())))
	for i in who.size():
		var hid: String = str(who[i])
		var sel: bool = hid == _building_hero
		var r := Rect2(24.0, 100.0 + float(i) * rstep, 212.0, rstep - 8.0)
		_panel(r, DdTheme.PANEL_HI if sel else DdTheme.PANEL_DEEP)
		if sel:
			draw_rect(r, DdTheme.PARTY, false, 2.0)
		# 死人在马车里也要能认出来（M28）：他们会出现在同一列里，
		# 但可做的事完全不同（复活 / 移除记录，而不是解雇）。
		var is_alive: bool = bool((campaign.hero(hid) as Dictionary).get("alive", true))
		# 头像 + 职业纹章（M64 第十三轮）：这一列原来只有名字，
		# 而这几屏（马车/铁匠铺/疗养院/公会）恰恰是「按人头做决定」的地方。
		var ph2: float = minf(r.size.y - 16.0, 50.0)
		var pr2 := Rect2(r.position.x + 8.0, r.position.y + (r.size.y - ph2) * 0.5,
			ph2 * 0.754, ph2)
		_draw_hero_badge(hid, pr2, is_alive)
		var txr: float = pr2.end.x + 10.0
		_text(Vector2(txr, r.position.y + 26), _hero_label(hid), DdTheme.FONT_MD,
			(DdTheme.TEXT if sel else DdTheme.DIM) if is_alive else DdTheme.FAINT)
		# 压力放右边：它和名字同属「一眼要看到」的那一档。
		# draw_string 的 width 是从 pos.x **向右**量的文本框宽度，
		# 所以右对齐要把起点左移一个框宽，否则文字整个画到卡片外面去。
		var st: float = float((campaign.hero(hid) as Dictionary).get("stress", 0.0))
		_text(Vector2(r.position.x + r.size.x - 34, r.position.y + 26), "%.0f" % st, DdTheme.FONT_TAG, DdTheme.STRESS if st >= 100.0 else DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 24)
		# 第二行只放「需要处理」的状态：没状态就留白，别拿「装备 0 阶」凑数——
		# 那一行在 118 宽里放不下，硬塞会溢出到隔壁格子。
		_text(Vector2(txr, r.position.y + 48),
			_hero_flags(hid) if is_alive else "已阵亡", DdTheme.FONT_TAG, DdTheme.WARN if is_alive else DdTheme.FAINT)
		_add_hit(r, "bld_hero:" + hid)
		_hit_overlay(r, "bld_hero:" + hid)

	var btn_y: float = _btn_y
	# 面板高度按内容收缩（M100）。
	#
	# 六座建筑的实际内容只用到 300~520 高（疗养院约 300、马车约 520），
	# 而面板原来一路拉到按钮上方（约 1100）——卡片内部空出 400~700px，
	# 玩家看到的是「一张几乎全空的卡」，比留白更像没画完。
	# 收到 700（内容 + 贴底区块 + 余量）之后，各屏都是一张完整卡片。
	# 升级条跟着面板走（M131）：贴底放会离内容 500px 远，
	# 玩家得先滑到屏幕最下面才知道这里还能升级。
	var avail_h: float = btn_y - 88.0 - 34.0 - 64.0
	var panel_h: float = minf(avail_h, 700.0)
	_draw_building_panel(Rect2(rx, 88, rw, panel_h))
	_building_upgrade_row(_building, 88.0 + panel_h + 10.0, rw)
	_add_button(Rect2(rx, btn_y, rw, 56.0), "bld_back", "返回城镇")
	# 页脚（M31）：建筑屏原来是唯一没有底注的屏，内容排到 470 就断了，
	# 下面 290px 全空——看起来像「这屏还没画完」。城镇/地图/准备屏都有页脚，
	# 这里补上同一层的解释，顺便把「这个建筑在规则上到底怎么运作」说清楚。
	_text(Vector2(DdTheme.MARGIN, btn_y - 14.0), _building_hint(_building),
		DdTheme.FONT_MD, DdTheme.FAINT)


## 建筑屏名册卡的第二行：只列「需要处理的状态」（M27）。
##
## 原来这里写的是「装备 0 阶 · 压力 0」，一列 236 宽够用；
## 改成两列 118 宽之后放不下，而且装备阶在这个位置没有决策价值——
## 你在疗养院看的是「他有没有病」，在铁匠铺才看装备。
func _hero_flags(hid: String) -> String:
	var bits: Array = []
	# 「上阵」放最前面（M177）：建筑屏（疗养院/酒馆/铁匠铺）是在「按人头做决定」，
	# 而「这人会不会跟我下去」是决定的前提 —— 病/负/忙都在标签里，
	# 唯独缺了这一档，用户一眼就发现公会没有、建筑也没有。
	if _prep_party.has(hid):
		bits.append("上阵")
	var dn: int = campaign.diseases_of(hid).size()
	if dn > 0:
		bits.append("病 %d" % dn)
	var qn: int = campaign.negative_quirks_of(hid).size()
	if qn > 0:
		bits.append("负 %d" % qn)
	var bz: int = campaign.busy_of(hid)
	if bz > 0:
		bits.append("忙 %d 周" % bz)
	return " · ".join(bits)


## 名册卡的详情抽屉（M58）。
##
## 为什么是抽屉而不是新开一屏：竖屏上「点一个人看细节」是**临时查询**，
## 不是一段流程。开新屏要经历「进入 → 看 → 返回」三次跳转，
## 而这三次跳转里玩家想看的还是同一屏的名册。
##
## 内容只挑「城镇里能改变决策」的：
## 等级、装备阶、压力、出征/阵亡、已装备技能、饰品、要不要送去处理。
## 战斗数值（闪避/护甲/命中）不在这里 —— 那些在铁匠铺和出发准备里看，
## 两处都写会在换版本时对不上。
func _draw_hero_sheet() -> void:
	if _roster_open.is_empty() or (_state != S_TOWN and _state != S_ROSTER):
		return
	var row: Dictionary = campaign.hero(_roster_open)
	if row.is_empty():
		_roster_open = ""
		return
	var hid: String = _roster_open
	var alive: bool = bool(row.get("alive", false))

	# 遮罩：盖住整屏，只留抽屉。0.62 比纯黑浅 —— 还能看见底下是哪一屏。
	draw_rect(Rect2(0.0, 0.0, size.x, size.y), Color(0.0, 0.0, 0.0, 0.62))

	# 抽屉高度跟着技能行数走（M58 第二轮）。
	# 固定 720 时，只带 4 个技能的英雄会在技能和饰品之间空出一大段 ——
	# 那段空白是「给 7 技能的变身职业预留」，对大多数人是纯浪费。
	# 至少留三行：只带 1 个技能时抽屉扁得像张纸条，还不如不弹。
	var skills_n: int = mini(campaign.equipped_skills(_roster_open).size(), 7)
	var rows_sk: int = maxi(3, skills_n)
	var sh: float = 464.0 + float(rows_sk) * 34.0 + 296.0
	var r := Rect2(24.0, size.y - 44.0 - sh, size.x - 48.0, sh)
	draw_rect(r.grow(2.0), Color(0.0, 0.0, 0.0, 0.45))
	_panel(r, DdTheme.PANEL)
	draw_rect(Rect2(r.position, Vector2(r.size.x, 3.0)),
		DdTheme.PARTY if alive else Color("#3a3a3a"))

	var x: float = r.position.x + 24.0
	var y: float = r.position.y + 24.0

	# —— 头像 + 身份 ——
	var portrait: Texture2D = _art.texture_of(campaign.def_of(hid))
	if portrait != null:
		var tint: Color = Color(1, 1, 1, 1) if alive else Color(0.5, 0.5, 0.5, 0.6)
		draw_texture_rect(portrait, Rect2(x, y, 92.0, 122.0), false, tint)
	# 职业纹章（M61）：放在名字左边，比名字本身先被认出来。
	var nx: float = x + 112.0
	var jt: Texture2D = _ico("job_" + campaign.def_of(hid))
	if jt != null:
		_draw_ico("job_" + campaign.def_of(hid), Vector2(x + 112.0, y + 2.0), 36.0,
			Color(1, 1, 1, 1) if alive else Color(0.55, 0.55, 0.55, 0.75))
		nx = x + 158.0
	_text(Vector2(nx, y + 34.0), _hero_label(hid), DdTheme.FONT_H1,
		DdTheme.TEXT if alive else DdTheme.FAINT)
	_text(Vector2(nx, y + 60.0),
		"%s · Lv%d · 装备 %d 阶" % [
			DdNames.hero_name(campaign.def_of(hid)), campaign.resolve_of(hid),
			campaign.gear_of(hid)], DdTheme.FONT_MD, DdTheme.DIM)
	# 压力条：200 是上限（100 起开始判定崩溃）
	var st: float = float(row.get("stress", 0.0))
	var sw: float = r.size.x - 24.0 - 112.0 - 24.0
	_bar(Rect2(x + 112.0, y + 74.0, sw, 8.0), st / 200.0,
		DdTheme.STRESS, DdTheme.STRESS_TRACK)
	_text(Vector2(x + 112.0, y + 100.0), "压力 %.0f / 200" % st, DdTheme.FONT_SM,
		DdTheme.STRESS if st >= 100.0 else DdTheme.DIM)
	_text(Vector2(x + 112.0, y + 120.0),
		"出征 %d 次 · 阵亡 %d 次" % [int(row.get("runs", 0)), int(row.get("deaths", 0))],
		DdTheme.FONT_SM, DdTheme.FAINT)

	# —— 技能 ——
	y = r.position.y + 172.0
	_divider(x, y, r.size.x - 48.0)
	var skills: Array = campaign.equipped_skills(hid)
	var smax: int = campaign.skill_slot_max(hid)
	var selectable: bool = campaign.skill_selectable(hid)
	_text(Vector2(x, y + 26.0),
		"技能　%d / %d" % [skills.size(), smax] if selectable else "技能　全开（%d）" % skills.size(),
		DdTheme.FONT_BD, DdTheme.TEXT)
	_text(Vector2(r.end.x - 24.0 - 200.0, y + 26.0), "（在公会调整）", DdTheme.FONT_TAG,
		DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 200.0)
	y += 38.0
	if skills.is_empty():
		_text(Vector2(x, y + 18.0), "一个技能都没带 —— 去公会装备", DdTheme.FONT_MD, DdTheme.WARN)
		y += 30.0
	for i in mini(skills.size(), 7):
		var sid: String = str(skills[i])
		# 技能图标（M64 第十六轮）：抽屉里七行技能全是名字，
		# 和公会/战斗用同一套六分类，三处看到的是同一个图案。
		var sico: Texture2D = _skill_icon_tex(hid, sid)
		var stx: float = x
		if sico != null:
			draw_texture_rect(sico, Rect2(x, y + 4.0, 22.0, 22.0), false)
			stx = x + 28.0
		_text(Vector2(stx, y + 18.0), "✓ " + DdNames.skill_name(sid),
			DdTheme.FONT_MD, DdTheme.TEXT)
		var line_w: float = r.size.x - 24.0 * 2.0 - 168.0 - (stx - x)
		_text(Vector2(stx + 168.0, y + 18.0),
			DdTheme.ellipsis(_skill_line(hid, sid), _font, line_w, 12),
			DdTheme.FONT_SM, DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_LEFT, line_w)
		y += 34.0

	# —— 饰品 ——
	y = r.position.y + 210.0 + float(rows_sk) * 34.0 + 10.0
	_divider(x, y, r.size.x - 48.0)
	var tr: Array = campaign.equipped_of(hid)
	_text(Vector2(x, y + 26.0), "饰品　%d / %d" % [
		tr.filter(func(t: Variant) -> bool: return not str(t).is_empty()).size(),
		campaign.equip_slots], DdTheme.FONT_BD, DdTheme.TEXT)
	_text(Vector2(r.end.x - 24.0 - 200.0, y + 26.0), "（在仓库调整）", DdTheme.FONT_TAG,
		DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 200.0)
	var tw2: float = (r.size.x - 48.0 - 12.0) * 0.5
	for si in campaign.equip_slots:
		var sr := Rect2(x + float(si) * (tw2 + 12.0), y + 40.0, tw2, 44.0)
		var cur: String = str(tr[si]) if si < tr.size() else ""
		_panel(sr, DdTheme.PANEL_DEEP if cur.is_empty() else DdTheme.PANEL_HI)
		var eico: Texture2D = _trinket_icon(cur) if not cur.is_empty() else null
		var etx: float = sr.position.x + 12.0
		if eico != null:
			draw_texture_rect(eico, Rect2(sr.position.x + 10.0, sr.position.y + 7.0,
				30.0, 30.0), false)
			etx = sr.position.x + 46.0
		_text(Vector2(etx, sr.position.y + 27.0),
			DdNames.trinket_name(cur) if not cur.is_empty() else "空槽",
			DdTheme.FONT_MD, DdTheme.TEXT if not cur.is_empty() else DdTheme.FAINT)

	# —— 抗性（M110）——
	#
	# 原版英雄面板一定列这六项：它们决定「这个人在这个地牢里能扛住什么」。
	# 我们之前**一项都没有** —— `resist_of()` 在整个 UI 里引用 0 次，
	# 玩家只能靠踩坑记住谁的流血抗性低。
	y += 104.0
	_divider(x, y, r.size.x - 48.0)
	_text(Vector2(x, y + 26.0), "抗性", DdTheme.FONT_BD, DdTheme.TEXT)
	var hdef: Dictionary = db.heroes.get(campaign.def_of(hid), {}) if db != null else {}
	var res: Dictionary = hdef.get("resistances", {})
	var r_order: Array = ["stun", "poison", "bleed", "disease", "move", "death_blow"]
	var rcol_w: float = (r.size.x - 48.0) * 0.5
	for i in r_order.size():
		var key: String = str(r_order[i])
		var val: float = float(res.get(key, 0.0)) * 100.0
		var cx3: float = x + float(i % 2) * rcol_w
		var cy3: float = y + 48.0 + float(i / 2) * 24.0
		_text(Vector2(cx3, cy3), str(RES_CN.get(key, key)) + "抗", DdTheme.FONT_SM,
			DdTheme.DIM)
		_text(Vector2(cx3 + 90.0, cy3), "%.0f%%" % val, DdTheme.FONT_SM,
			DdTheme.TEXT if val >= 30.0 else DdTheme.WARN)

	# —— 怪癖与疾病（M110）——
	#
	# `_hero_flags()` 只拼「负 2」这种计数：玩家知道有问题，但不知道是哪两个、
	# 各自扣什么。效果文本 `_quirk_effect_text()` 一直是现成的，只是没人调用。
	var gy2: float = y + 48.0 + 3.0 * 24.0 + 22.0
	_divider(x, gy2, r.size.x - 48.0)
	_text(Vector2(x, gy2 + 26.0), "怪癖与疾病", DdTheme.FONT_BD, DdTheme.TEXT)
	var qall: Array = campaign.quirks_of(hid)
	if qall.is_empty():
		_text(Vector2(x, gy2 + 50.0), "这一趟没沾上什么。", DdTheme.FONT_SM, DdTheme.FAINT)
	var qy: float = gy2 + 50.0
	for qv in qall:
		var qid: String = str(qv)
		var is_dis: bool = campaign.quirk_lib != null and campaign.quirk_lib.is_disease(qid)
		var qcol: Color = DdTheme.CRIT if is_dis else DdTheme.WARN
		var qn2: String = DdNames.quirk_name(qid)
		_text(Vector2(x, qy), qn2, DdTheme.FONT_SM, qcol,
			HORIZONTAL_ALIGNMENT_LEFT, 150.0)
		var eff2: String = _quirk_effect_text(qid)
		_text(Vector2(x + 158.0, qy),
			DdTheme.ellipsis(eff2 if not eff2.is_empty() else "（无数值影响）",
				_font, r.size.x - 48.0 - 158.0, 12),
			DdTheme.FONT_SM, DdTheme.DIM, HORIZONTAL_ALIGNMENT_LEFT,
			r.size.x - 48.0 - 158.0)
		qy += 24.0
	y = qy

	# —— 状态 ——
	y += 36.0
	_divider(x, y, r.size.x - 48.0)
	# 这里不再用 `_hero_flags()`（M110）：它拼的是「病 1 · 负 2」这种**计数**，
	# 而上面已经把每个怪癖的名字和效果列出来了 —— 再写一遍数字等于重复，
	# 而且会在抽屉底部留下一行孤零零的「负 2」。现在只留「在建筑里」。
	var flags: String = ""
	var bz3: int = campaign.busy_of(hid)
	if bz3 > 0:
		flags = "这周在建筑里（剩 %d 周）" % bz3
	if not alive:
		_text(Vector2(x, y + 28.0), "已阵亡 —— 去马车复活（要花钱）", DdTheme.FONT_MD, DdTheme.CRIT)
	elif not flags.is_empty():
		_text(Vector2(x, y + 28.0), flags, DdTheme.FONT_MD, DdTheme.WARN)
	else:
		_text(Vector2(x, y + 28.0), "状态正常，随时能出征", DdTheme.FONT_MD, DdTheme.OK)

	# —— 关闭 ——
	var cr := Rect2(x, r.end.y - 24.0 - 56.0, r.size.x - 48.0, 56.0)
	_tile(cr, _hit_state(cr, "sheet_close"), DdTheme.BTN)
	_text(Vector2(cr.position.x, cr.position.y + 34.0), "关闭", DdTheme.FONT_BD,
		DdTheme.TEXT, HORIZONTAL_ALIGNMENT_CENTER, cr.size.x)
	_sheet_hits.append({"rect": cr, "id": "sheet_close"})


func _draw_building_panel(r: Rect2) -> void:
	var hid: String = _building_hero
	_panel(r, DdTheme.PANEL_DEEP)
	# 马车不按「选中的人」组织（M27）：它卖的是**没见过的人**，
	# 而那些人还不在名册里，左侧列表根本没有他们的位置。
	# 所以这一屏跳过通用标题，整个面板交给 _panel_coach 自己排版。
	if _building == "coach":
		_panel_coach(r, hid)
		return
	var row: Dictionary = campaign.hero(hid)
	_text(Vector2(r.position.x + 16, r.position.y + 30), _hero_label(hid), DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(r.position.x + 16, r.position.y + 52),
		"出征 %d 次 · 阵亡 %d 次" % [int(row.get("runs", 0)), int(row.get("deaths", 0))], DdTheme.FONT_SM, DdTheme.FAINT)
	# 忙的时候按钮会全灰，光灰着不解释等于「点了没反应」
	var bz: int = campaign.busy_of(hid)
	if bz > 0:
		_text(Vector2(r.position.x + 300, r.position.y + 30),
			"这周还有事（剩 %d 周）" % bz, DdTheme.FONT_MD, DdTheme.WARN,
			HORIZONTAL_ALIGNMENT_RIGHT, r.size.x - 320)

	match _building:
		"coach":
			pass
		"smith":
			_panel_smith(r, hid)
		"sanitarium":
			_panel_sanitarium(r, hid)
		"abbey", "tavern":
			_panel_rest(r, hid)
		_:
			_text(Vector2(r.position.x + 16, r.position.y + 96), "这座建筑还在图纸上。", DdTheme.FONT_MD, DdTheme.FAINT)

	# —— 面板底部：这个人现在带什么技能、压力多少（M63）——
	# 这六座建筑的面板都只用到上半截（疗养院约 300、马车约 520），
	# 下面空 400~700px，一张几乎全空的卡比留白更像「没画完」。
	# 空出来的部分放换人之前要确认的两件事：他带什么技能、压力多少。
	# 贴底画而不是接在内容后面：各面板的内容长度差一倍，贴底才不会互相顶。
	var tail_h: float = 170.0
	var ty0: float = r.end.y - 24.0 - tail_h
	if ty0 <= r.position.y + 300.0:
		return
	_divider(r.position.x + 16.0, ty0, r.size.x - 48.0)
	var ski: Array = campaign.equipped_skills(hid)
	_text(Vector2(r.position.x + 16.0, ty0 + 26.0),
		"当前技能　%d / %d" % [ski.size(), campaign.skill_slot_max(hid)],
		DdTheme.FONT_MD, DdTheme.DIM)
	var col_w: float = (r.size.x - 48.0) * 0.5
	for i in ski.size():
		# 16px 的技能图标：行高只有 22，再大就压行了；
		# 这个尺寸看不清细节，但「剑 / 号角 / 破盾」的轮廓还分得出来。
		var cx0: float = r.position.x + 16.0 + (col_w if i % 2 == 1 else 0.0)
		var cy0: float = ty0 + 48.0 + float(int(i / 2)) * 22.0
		var sico: Texture2D = _skill_icon_tex(hid, str(ski[i]))
		var ox: float = cx0
		if sico != null:
			draw_texture_rect(sico, Rect2(cx0, cy0, 18.0, 18.0), false)
			ox = cx0 + 21.0
		# 有图标时不再加「·」前缀，两个都留着像排版没做完；
		# 文字顶到 cy0+3 才和 18px 图标垂直居中（原来是 +12，字全沉在下方）。
		_text(Vector2(ox, cy0 + 3.0),
			(("" if sico != null else "· ") + DdNames.skill_name(str(ski[i]))),
			DdTheme.FONT_SM, DdTheme.TEXT)
	var stv: float = float(row.get("stress", 0.0))
	var strow: float = ty0 + 50.0 + float(int(maxi(ski.size(), 1) / 2) + 1) * 22.0
	_text(Vector2(r.position.x + 16.0, strow), "压力 %.0f / 200" % stv, DdTheme.FONT_SM,
		DdTheme.STRESS if stv >= 100.0 else DdTheme.DIM)
	_bar(Rect2(r.position.x + 130.0, strow - 10.0, r.size.x - 170.0, 10.0),
		stv / 200.0, DdTheme.STRESS, DdTheme.STRESS_TRACK)


## 马车（M27 / M28）：招人、捞人、赶人。
##
## 三件事挤在一屏，是因为它们都作用在「名册上的人」——
## 但分成上下两半：上半是**往名册里加**（新面孔），
## 下半是**处理名册里的人**（复活 / 解雇）。
func _panel_coach(r: Rect2, hid: String) -> void:
	var x: float = r.position.x + 16
	var y: float = r.position.y + 30
	_text(Vector2(x, y), "马车", DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(x, y + 22), "名册 %d / %d 人（存活 %d）" % [
		campaign.hero_ids().size(), campaign.roster_max(), campaign.alive_ids().size()], DdTheme.FONT_SM, DdTheme.FAINT)
	y += 46

	# —— 上半：本周新面孔 ——
	_text(Vector2(x, y), "本周新面孔（每周换一批）", DdTheme.FONT_MD, DdTheme.DIM)
	var cands: Array = campaign.recruit_candidates
	if cands.is_empty():
		var why: String = "所有职业都已入册" if campaign.hireable_pool().is_empty() \
			else "这批都招走了，下周再来"
		_text(Vector2(x, y + 22), why, DdTheme.FONT_MD, DdTheme.FAINT)
	else:
		# 候选做成卡片（M98）：原来只有一行文字按钮「麻风病人（1000 金币）」，
		# 招之前看不到长相，也看不到招来是什么水平——玩家得先花钱才认识这个人。
		# 左边名册每个人都有头像，右边「即将加入的人」却是一片空白，观感也是断的。
		var ch: float = 84.0
		for i in cands.size():
			var cls: String = str(cands[i])
			var cost: Dictionary = campaign.hire_cost()
			var ok: bool = campaign.can_hire(cls)
			var cid2: String = "hire:" + cls
			var cr2 := Rect2(x, y + 16.0 + float(i) * (ch + 8.0), 360.0, ch)
			var st3: int = _hit_state(cr2, cid2)
			draw_rect(cr2, DdTheme.BTN_ACTIVE if st3 != TILE_IDLE else DdTheme.BTN)
			draw_rect(cr2, DdTheme.CRIT if st3 == TILE_HOVER else DdTheme.PANEL_EDGE,
				false, 1.0)
			if ok:
				_add_hit(cr2, cid2)
			# 头像：用职业定义取立绘，和左边名册同一套
			var tx2: Texture2D = _art.texture_of(cls)
			var ir := Rect2(cr2.position.x + 8.0, cr2.position.y + 8.0, 68.0, 68.0)
			if tx2 != null:
				draw_texture_rect(tx2, ir, false, Color(1, 1, 1, 1) if ok
					else Color(0.45, 0.45, 0.5, 1.0))
			else:
				draw_rect(ir, DdTheme.PANEL_HI)
			_text(Vector2(cr2.position.x + 88.0, cr2.position.y + 32.0),
				_hero_label(cls), DdTheme.FONT_LG,
				DdTheme.TEXT if ok else DdTheme.FAINT)
			_text(Vector2(cr2.position.x + 88.0, cr2.position.y + 56.0),
				"新招募 · Lv1 · 装备 0 阶", DdTheme.FONT_TAG, DdTheme.DIM)
			_text(Vector2(cr2.end.x - 120.0, cr2.position.y + 36.0),
				"%d 金币" % int(cost.get("gold", 0)), DdTheme.FONT_BD,
				DdTheme.CRIT if ok else DdTheme.FAINT,
				HORIZONTAL_ALIGNMENT_RIGHT, 104.0)
			if not ok:
				_text(Vector2(cr2.end.x - 120.0, cr2.position.y + 58.0),
					_hire_why(cls), DdTheme.FONT_TAG, DdTheme.WARN,
					HORIZONTAL_ALIGNMENT_RIGHT, 104.0)
		y += 16.0 + float(cands.size()) * (ch + 8.0) + 18.0
	draw_line(Vector2(x, y), Vector2(x + 340, y), DdTheme.PANEL_EDGE, 1.0)
	y += 22.0

	# —— 下半：处理选中的人 ——
	_text(Vector2(x, y), "名册管理", DdTheme.FONT_MD, DdTheme.DIM)
	y += 10.0
	if hid.is_empty() or campaign.hero(hid).is_empty():
		_text(Vector2(x, y + 16), "左侧点一个人。", DdTheme.FONT_MD, DdTheme.FAINT)
		return
	var alive: bool = bool((campaign.hero(hid) as Dictionary).get("alive", true))
	var nm: String = _hero_label(hid)
	y += 12.0
	if alive:
		_text(Vector2(x, y),
			"%s · Lv%d · 装备 %d 阶 · 出征 %d 次" % [nm, campaign.resolve_of(hid),
			campaign.gear_of(hid), int((campaign.hero(hid) as Dictionary).get("runs", 0))], DdTheme.FONT_MD, DdTheme.TEXT)
		y += 18.0
		_text(Vector2(x, y), "解雇会把他的等级和装备一起抹掉，招回来还是 Lv1。", DdTheme.FONT_SM, DdTheme.FAINT)
	else:
		_text(Vector2(x, y), "%s · 已阵亡 %d 次" % [
			nm, int((campaign.hero(hid) as Dictionary).get("deaths", 0))], DdTheme.FONT_MD, DdTheme.WARN)
		y += 18.0
		_text(Vector2(x, y), "复活他，或者把这条墓园记录删掉。", DdTheme.FONT_SM, DdTheme.FAINT)
	y += 22.0

	if not alive:
		# 复活（破产保护）：没有它，玩家会在「没人能出征、也没钱招募」
		# 的死局里卡住，而存档不会自己回退。
		var rc: Dictionary = campaign.effective_recruit_cost(hid)
		var label: String = "免费征召（全员阵亡保底）"
		if not rc.is_empty():
			label = "复活（%d 金币）" % int(rc.get("gold", 0))
		_add_button(Rect2(x, y, 340, 42), "bld_act:recruit", label,
			campaign.can_recruit(hid))
		y += 50.0

	# 解雇（M28）：不可逆且清空投入，所以要点两次。
	if _fire_pending == hid:
		_add_button(Rect2(x, y, 340, 42), "fire2:" + hid,
			"再点一次 —— %s 会消失，等级不保留" % nm, true, true)
	else:
		var reason: String = ""
		if campaign.busy_of(hid) > 0:
			reason = "（他这周还在外面办事）"
		elif alive and campaign.alive_ids().size() <= 1:
			reason = "（至少要留一个能出征的人）"
		_add_button(Rect2(x, y, 340, 42), "fire:" + hid,
			("解雇 %s%s" % [nm, reason]) if alive else ("从墓园移除 %s" % nm),
			campaign.can_dismiss(hid))


## 真的解雇（M28）。到这一步时玩家已经点过两次了。
func _do_fire(hid: String) -> void:
	_fire_pending = ""
	var nm: String = _hero_label(hid)
	var alive: bool = bool((campaign.hero(hid) as Dictionary).get("alive", true))
	# 解雇前先把他从出征名单里摘掉（M177）。
	#
	# 原来直接 `dismiss`，而 `_prep_party` 是**另一份数据**，里面还留着他的 id ——
	# 出征时按名单拉人，拉到一个已经不存在的人，轻则少一个人下地牢、
	# 重则整条 `_start_expedition` 出错。这和 M174 那个「改了数据源、渲染没跟」
	# 是同一类问题：**两份互相引用的数据，只改了一份**。
	var was_on: bool = _prep_party.has(hid)
	if was_on:
		_prep_party.erase(hid)
		_party_persist()
	if not campaign.dismiss(hid):
		# 解雇失败（还在修养 / 只剩一个人）：把名单恢复回去，别留下半截状态
		if was_on:
			_prep_party.append(hid)
			_party_persist()
		if campaign.busy_of(hid) > 0:
			_flash_msg("这周他还在外面办事，下周再说")
		elif alive and campaign.alive_ids().size() <= 1:
			_flash_msg("至少要留一个能出征的人")
		else:
			_flash_msg("这个人已经不在名册上了")
		queue_redraw()
		return
	campaign.save()
	# 选中的人被删了，指针要换到别人身上，否则右侧面板会引用一个不存在的 id
	if _building_hero == hid:
		var av: Array = campaign.alive_ids()
		if av.is_empty():
			av = campaign.hero_ids()
		_building_hero = str(av[0]) if not av.is_empty() else ""
	_flash_msg(("已解雇 %s" % nm) if alive else ("已从墓园移除 %s" % nm))
	queue_redraw()


## 铁匠铺（M64 第十七轮重排）。
##
## 原来只有「当前属性一行」+「升一阶：生命 +7」+ 一个按钮，加起 130 高，
## 面板 1050 —— 中间空 900px，是全项目最空的一屏。
##
## 现在补两样：
##   1. **逐项对比表**（生命/闪避/护甲/速度/命中/暴击/伤害 ×现在→升级后）；
##   2. 「名册里谁的装备还能升」—— 铁匠一次只升一个人。
func _panel_smith(r: Rect2, hid: String) -> void:
	var x: float = r.position.x + 16.0
	var y: float = r.position.y + 96.0
	var gear: int = campaign.gear_of(hid)
	var maxed: bool = gear >= Campaign.MAX_GEAR
	var cost: Dictionary = campaign.upgrade_cost(hid)

	# —— 逐项对比 ——
	if maxed:
		_text(Vector2(x, y), "已经满阶（%d 阶）。" % gear, DdTheme.FONT_BD, DdTheme.OK)
		y += 30.0
	else:
		var cur: Dictionary = db.hero_base(campaign.def_of(hid), gear)
		var nxt: Dictionary = db.hero_base(campaign.def_of(hid),
			mini(gear + 1, Campaign.MAX_GEAR))
		_text(Vector2(x, y), "%d 阶 → %d 阶" % [gear, gear + 1],
			DdTheme.FONT_BD, DdTheme.TEXT)
		# 列头：三列都要对齐，否则「现在」和「升级后」两列数字会飘
		_text(Vector2(x + 120.0, y), "现在", DdTheme.FONT_TAG, DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_RIGHT, 70.0)
		_text(Vector2(x + 200.0, y), "升级后", DdTheme.FONT_TAG, DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_RIGHT, 70.0)
		y += 26.0
		for row in _smith_rows(cur, nxt):
			var nm: String = str(row[0])
			var a: float = float(row[1])
			var b: float = float(row[2])
			var un: String = str(row[3])
			var up: bool = b > a + 0.001
			_text(Vector2(x + 6.0, y + 16.0), nm, DdTheme.FONT_MD, DdTheme.DIM,
				HORIZONTAL_ALIGNMENT_LEFT, 110.0)
			_text(Vector2(x + 120.0, y + 16.0), "%.0f%s" % [a, un], DdTheme.FONT_MD,
				DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 70.0)
			_text(Vector2(x + 200.0, y + 16.0), "%.0f%s" % [b, un], DdTheme.FONT_MD,
				DdTheme.TEXT if up else DdTheme.FAINT,
				HORIZONTAL_ALIGNMENT_RIGHT, 70.0)
			if up:
				_text(Vector2(x + 278.0, y + 16.0), "+%.0f%s" % [b - a, un],
					DdTheme.FONT_TAG, DdTheme.OK)
			y += 26.0
		y += 6.0

	# —— 按钮 / 为什么不给点 ——
	if maxed:
		pass
	elif cost.is_empty():
		# 等级不够（M25）。这和「满阶」是两件事：一个到头了，一个还能练。
		# 混成一句会让玩家以为这个人的装备线走完了，去练别人。
		_text(Vector2(x, y + 16.0),
			"要 Lv%d 才能穿 %d 阶。他目前 Lv%d（经验 %d/%d）。" % [
				gear + 2, gear + 1, campaign.resolve_of(hid), campaign.xp_of(hid),
				int(Campaign.RESOLVE_XP[mini(campaign.resolve_of(hid) + 1,
					Campaign.MAX_RESOLVE)])], DdTheme.FONT_MD, DdTheme.WARN,
			HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 48.0)
		_text(Vector2(x, y + 42.0), "打几趟升上去就能升装备。",
			DdTheme.FONT_SM, DdTheme.FAINT)
		y += 62.0
	else:
		var hb: Dictionary = cost.get("heirlooms", {})
		var extra: String = ""
		if not hb.is_empty():
			var k: String = str(hb.keys()[0])
			extra = " + %d %s" % [int(hb[k]), DdNames.heirloom_name(k)]
		_add_button(Rect2(x, y + 4.0, 340, 44), "bld_act:upgrade",
			"升到 %d 阶（%d 金币%s）" % [gear + 1, int(cost.get("gold", 0)), extra],
			campaign.can_upgrade(hid))
		y += 56.0

	# —— 名册里谁的装备还能升 ——
	var rows: Array = []
	for ov in campaign.hero_ids():
		var oid: String = str(ov)
		if oid == hid:
			continue
		if not bool((campaign.hero(oid) as Dictionary).get("alive", false)):
			continue
		var og: int = campaign.gear_of(oid)
		if og >= Campaign.MAX_GEAR:
			continue
		rows.append({
			"name": _hero_label(oid),
			"right": "已 %d 阶 · 可升 %d 阶" % [og, Campaign.MAX_GEAR - og],
			"w": Campaign.MAX_GEAR - og,
		})
	rows.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return int(a["w"]) > int(b["w"]))
	_draw_pending_list(r, y + 44.0, "名册里谁的装备还能升（缺口大的在前）", rows)


## 「名册里还有谁该来」列表（M64 第十七轮）。疗养院与铁匠铺共用。
##
## 这两座建筑都是「一次只能处理一个人」，而玩家真正要做的判断是「先处理谁」。
## 原来这个信息不在界面上，只能回名册页一个个点开看。
##
## `rows` 由调用方排好序，每项 `{name, right}`；行高固定 26，
## 超出可用高度的直接不画（不滚动 —— 这个列表是提示，不是主界面）。
func _draw_pending_list(r: Rect2, top: float, title: String, rows: Array) -> void:
	var x: float = r.position.x + 16.0
	var bottom: float = r.end.y - 194.0
	if bottom - top < 90.0:
		return
	_divider(x, top, r.size.x - 48.0)
	_text(Vector2(x, top + 22.0), title, DdTheme.FONT_MD, DdTheme.DIM)
	if rows.is_empty():
		_text(Vector2(x, top + 48.0), "名册里没有需要处理的人。", DdTheme.FONT_SM, DdTheme.FAINT)
		return
	var ly: float = top + 46.0
	for i in mini(rows.size(), 6):
		if ly + 24.0 > bottom:
			break
		var one: Dictionary = rows[i]
		_text(Vector2(x + 6.0, ly + 16.0), str(one.get("name", "")),
			DdTheme.FONT_MD, DdTheme.TEXT)
		# 颜色可以逐行给：酒馆那张列表要区分「压力过百」和「还没过百」，
		# 统一用 WARN 的话两档看起来一样，而这两档的处理优先级差很多。
		var right_col: Color = (one.get("col", DdTheme.WARN) as Color)
		_text(Vector2(r.end.x - 24.0 - 200.0, ly + 16.0), str(one.get("right", "")),
			DdTheme.FONT_MD, right_col, HORIZONTAL_ALIGNMENT_RIGHT, 200.0)
		ly += 26.0


## 铁匠铺的升阶对比（M64 第十七轮）。
##
## 原来只有一句「升一阶：生命 +7，命中与伤害随武器提升」——
## 玩家没法判断这钱花得值不值，而铁匠铺的全部决策就是这一件事。
## 现在逐项列，返回 `[名字, 现在, 升级后, 单位]`。
##
## 数字来源是 `db.hero_base()`：武器给命中/暴击/伤害/速度，护甲给生命/闪避/护甲，
## 所以升一阶其实是**两件东西一起变**，只看生命会漏掉一半。
func _smith_rows(cur: Dictionary, nxt: Dictionary) -> Array:
	var out: Array = []
	var defs: Array = [
		["生命", "hp_max", 1.0, ""],
		["闪避", "dodge", 100.0, "%"],
		["护甲", "prot", 100.0, "%"],
		["速度", "speed", 1.0, ""],
		["命中", "acc", 1.0, ""],
		["暴击", "crit", 100.0, "%"],
		["伤害下限", "dmg_low", 1.0, ""],
		["伤害上限", "dmg_high", 1.0, ""],
	]
	for d in defs:
		out.append([
			str(d[0]),
			float(cur.get(str(d[1]), 0.0)) * float(d[2]),
			float(nxt.get(str(d[1]), 0.0)) * float(d[2]),
			str(d[3]),
		])
	return out


## 疗养院（M64 第十七轮重排）。
##
## 原来只有「疾病 N 条 + 名字横排」和「负面怪癖 N 条 + 名字横排」两段，
## 加起来 300 高，面板高 1050 —— 中间空 600px，一张半空的卡比留白更像没做完。
##
## 现在补三样**决策时真的要看**的东西：
##   1. 每条疾病/怪癖带上**效果**（数据里 buffs → buffs.json，182 个 id 全部命中）；
##   2. 中段列出「名册里还有谁该来」—— 疗养院一次只能治一个人，
##      而玩家要判断的正是「先治谁」；
##   3. 标题右侧直接写「已治好 X 条 / 还剩 Y 条」这种进度感。
func _panel_sanitarium(r: Rect2, hid: String) -> void:
	var x: float = r.position.x + 16.0
	var y: float = r.position.y + 96.0
	var ds: Array = campaign.diseases_of(hid)
	var ns: Array = campaign.negative_quirks_of(hid)

	# —— 疾病 ——
	_text(Vector2(x, y), "疾病 %d 条" % ds.size(), DdTheme.FONT_BD,
		DdTheme.WARN if not ds.is_empty() else DdTheme.DIM)
	if ds.is_empty():
		_text(Vector2(x, y + 26.0), "没有病 —— 这个人现在不需要这里。", DdTheme.FONT_SM, DdTheme.FAINT)
		y += 52.0
	else:
		y += 28.0
		for i in mini(ds.size(), 4):
			var did: String = str(ds[i])
			_text(Vector2(x + 6.0, y + 18.0), "· " + DdNames.quirk_name(did),
				DdTheme.FONT_MD, DdTheme.STRESS)
			_text(Vector2(x + 130.0, y + 18.0), _quirk_effect_text(did),
				DdTheme.FONT_SM, DdTheme.DIM,
				HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 160.0)
			y += 26.0
		if ds.size() > 4:
			_text(Vector2(x + 6.0, y + 16.0), "等 %d 条" % ds.size(), DdTheme.FONT_TAG, DdTheme.FAINT)
			y += 22.0
		y += 8.0
	_add_button(Rect2(x, y, 320, 42), "bld_act:disease",
		"治病一条（%d 金币）" % campaign.disease_cost(),
		not ds.is_empty() and campaign.gold >= campaign.disease_cost() \
		and campaign.busy_of(hid) <= 0)

	# —— 负面怪癖 ——
	var y2: float = y + 66.0
	_text(Vector2(x, y2), "负面怪癖 %d 条" % ns.size(), DdTheme.FONT_BD,
		DdTheme.WARN if not ns.is_empty() else DdTheme.DIM)
	if ns.is_empty():
		_text(Vector2(x, y2 + 26.0), "没有负面怪癖。", DdTheme.FONT_SM, DdTheme.FAINT)
		y2 += 52.0
	else:
		y2 += 28.0
		for i in mini(ns.size(), 5):
			var qid: String = str(ns[i])
			_text(Vector2(x + 6.0, y2 + 18.0), "· " + DdNames.quirk_name(qid),
				DdTheme.FONT_MD, DdTheme.STRESS)
			_text(Vector2(x + 130.0, y2 + 18.0), _quirk_effect_text(qid),
				DdTheme.FONT_SM, DdTheme.DIM,
				HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 160.0)
			y2 += 26.0
		if ns.size() > 5:
			_text(Vector2(x + 6.0, y2 + 16.0), "等 %d 条" % ns.size(), DdTheme.FONT_TAG, DdTheme.FAINT)
			y2 += 22.0
		y2 += 8.0
	_add_button(Rect2(x, y2, 320, 42), "bld_act:quirk",
		"清掉一条（%d 金币）" % campaign.quirk_cost(),
		not ns.is_empty() and campaign.gold >= campaign.quirk_cost() \
		and campaign.busy_of(hid) <= 0)
	_text(Vector2(x, y2 + 66.0),
		"一次只处理一条：一次全清的话，疗养院就退化成一个「点一下」的按钮。",
		DdTheme.FONT_SM, DdTheme.FAINT)

	# —— 中段：名册里还有谁该来 ——
	# 这一屏一次只能治一个人，所以「先治谁」是玩家真正要做的判断。
	# 原来整个界面都不给这个信息，只能回名册页一个个点开看。
	var list_top: float = y2 + 96.0
	var list_bottom: float = r.end.y - 194.0
	if list_bottom - list_top < 90.0:
		return
	_divider(x, list_top, r.size.x - 48.0)
	_text(Vector2(x, list_top + 22.0), "名册里还有谁该来（按需要程度排）",
		DdTheme.FONT_MD, DdTheme.DIM)
	var others: Array = []
	for ov in campaign.hero_ids():
		var oid: String = str(ov)
		if oid == hid:
			continue
		if not bool((campaign.hero(oid) as Dictionary).get("alive", false)):
			continue
		var dn: int = campaign.diseases_of(oid).size()
		var qn: int = campaign.negative_quirks_of(oid).size()
		if dn == 0 and qn == 0:
			continue
		others.append({"id": oid, "d": dn, "q": qn, "w": dn * 2 + qn})
	others.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return int(a["w"]) > int(b["w"]))
	if others.is_empty():
		_text(Vector2(x, list_top + 48.0), "名册里其他人也没有病和怪癖。", DdTheme.FONT_SM, DdTheme.FAINT)
		return
	var ly: float = list_top + 46.0
	for i in mini(others.size(), 5):
		var o: Dictionary = others[i]
		var orow := Rect2(x, ly, r.size.x - 48.0, 24.0)
		if orow.end.y > list_bottom:
			break
		_text(Vector2(x + 6.0, ly + 16.0), _hero_label(str(o["id"])),
			DdTheme.FONT_MD, DdTheme.TEXT)
		var bits: Array = []
		if int(o["d"]) > 0:
			bits.append("病 %d" % int(o["d"]))
		if int(o["q"]) > 0:
			bits.append("癖 %d" % int(o["q"]))
		_text(Vector2(r.end.x - 24.0 - 160.0, ly + 16.0), " · ".join(bits),
			DdTheme.FONT_MD, DdTheme.WARN, HORIZONTAL_ALIGNMENT_RIGHT, 160.0)
		ly += 26.0


func _panel_rest(r: Rect2, hid: String) -> void:
	var y: float = r.position.y + 96
	var opt: Dictionary = campaign.rest_option(_building)
	var cur: float = float((campaign.hero(hid) as Dictionary).get("stress", 0.0))
	var relief: int = int(opt.get("relief", 0))
	var cost: int = int(opt.get("cost", 0))

	_text(Vector2(r.position.x + 16, y), "当前压力 %.0f / 200 —— 待完这次是 %.0f" % [
		cur, maxf(0.0, cur - float(relief))], DdTheme.FONT_BD,
		DdTheme.STRESS if cur >= 100.0 else DdTheme.DIM,
		HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 32.0)
	_bar(Rect2(r.position.x + 16, y + 10, 340, 12), cur / 200.0, DdTheme.STRESS,
		DdTheme.STRESS_TRACK)
	# 限宽 + 折行（M181）：原来这行 40 个字不限宽，一路画到面板外面
	# （截图里「…崩」之后被切掉）。用户提的「界面有覆盖重叠」，一半是它。
	var note: String = "一次减 %d 点，%d 金币。压力过 100 就该来了——崩溃一次要赔进去的可不止这点。" % [
		relief, cost]
	var nw: float = r.size.x - 32.0
	if _font.get_string_size(note, HORIZONTAL_ALIGNMENT_LEFT, -1, DdTheme.FONT_MD).x > nw:
		_text(Vector2(r.position.x + 16, y + 42), "一次减 %d 点，%d 金币" % [relief, cost],
			DdTheme.FONT_MD, DdTheme.DIM, HORIZONTAL_ALIGNMENT_LEFT, nw)
		_text(Vector2(r.position.x + 16, y + 66), "压力过 100 就该来了——崩溃的代价远不止这点",
			DdTheme.FONT_TAG, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_LEFT, nw)
	else:
		_text(Vector2(r.position.x + 16, y + 42), note,
			DdTheme.FONT_MD, DdTheme.DIM, HORIZONTAL_ALIGNMENT_LEFT, nw)
	_add_button(Rect2(r.position.x + 16, y + 92, 320, 44), "bld_act:rest",
		"减压（%d 金币）" % cost, cur > 0.01 and campaign.gold >= cost \
		and campaign.busy_of(hid) <= 0)

	# —— 名册里谁压力最高 ——
	# 酒馆/修道院一次只接一个人，而「先送谁」要横着比一遍全队压力。
	# 原来这个信息只能回名册页看，而那一屏不显示别人的压力条。
	var rows: Array = []
	for ov in campaign.hero_ids():
		var oid: String = str(ov)
		if oid == hid:
			continue
		var orow: Dictionary = campaign.hero(oid)
		if not bool(orow.get("alive", false)):
			continue
		var sp: float = float(orow.get("stress", 0.0))
		if sp < 1.0:
			continue
		rows.append({
			"name": _hero_label(oid),
			"right": "压力 %.0f / 200" % sp,
			"w": sp,
			"col": DdTheme.STRESS if sp >= 100.0 else DdTheme.DIM,
		})
	rows.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return float(a["w"]) > float(b["w"]))
	_draw_pending_list(r, y + 130.0, "名册里谁压力最高（过百的该先来）", rows)


func _draw_graveyard(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	_text(Vector2(r.position.x + 16, r.position.y + 30), "墓园", DdTheme.FONT_H1, DdTheme.TEXT)
	# 副标题也要给宽度（M152）：没写宽度时 Godot 按单行画，
	# 字号放大后「那一趟结成了什么样」直接画出面板。
	_text(Vector2(r.position.x + 16, r.position.y + 54),
		"每一位倒在这里的人：死在第几周、哪片区域、那一趟结成了什么样。",
		DdTheme.FONT_SM, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 32.0)
	var gv: Array = campaign.graveyard()
	if gv.is_empty():
		_text(Vector2(r.position.x + 16, r.position.y + 96), "还没有人死在这里。", DdTheme.FONT_BD, DdTheme.DIM)
		return
	var y: float = r.position.y + 88
	for g in gv:
		var row: Dictionary = g
		# 三行竖排（M152）：原来名字在左、统计和死因都挤在 x+180 那一列，
		# 而且**没有宽度上限** —— 字号放大后「阵亡 1 次 · 出征 4 次 · 未归队」
		# 和「最近：第 4 周 · 荒野 · 短途 1 级 · 撤退退」直接画到面板外面。
		# 这一屏右边全是空的，竖着排反而更好读。
		var bw2: float = r.size.x - 32.0
		_text(Vector2(r.position.x + 16, y), _hero_label(str(row["hero"])),
			DdTheme.FONT_BD, DdTheme.TEXT if bool(row["alive"]) else DdTheme.DIM)
		y += 22.0
		_text(Vector2(r.position.x + 16, y), "阵亡 %d 次 · 出征 %d 次 · %s" % [
			int(row["deaths"]), int(row["runs"]),
			"已归队" if bool(row["alive"]) else "未归队"],
			DdTheme.FONT_MD, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_LEFT, bw2)
		y += 20.0
		# 第二行：最近一次的死因（M48）。没有这一行，墓园就只是计数器。
		var last: Dictionary = row.get("last", {})
		if not last.is_empty():
			_text(Vector2(r.position.x + 16, y), "最近：%s" % _death_line(last),
				DdTheme.FONT_SM, DdTheme.DIM, HORIZONTAL_ALIGNMENT_LEFT, bw2)
		y += 30.0


## 一条阵亡记录变成一句话（M48）。
##
## 读作「第 12 周 · 荒野 · 短途 1 级 · 全队覆没」——四段都是玩家当时的选择，
## 顺序也按选择发生的时间排（什么时候 → 去哪 → 打多难 → 结果）。
func _death_line(e: Dictionary) -> String:
	var reg: String = DdNames.dungeon_name(str(e.get("region", "")))
	var size_cn: String = {"short": "短途", "medium": "中途", "long": "长途",
		"boss": "首领"}.get(str(e.get("size", "")), str(e.get("size", "")))
	var reason_cn: String = {
		"wipe": "全队覆没",
		"complete": "走完了，人没回来",
		"retreat": "撤退途中",
		"incomplete": "任务未完成",
	}.get(str(e.get("reason", "")), str(e.get("reason", "")))
	return "第 %d 周 · %s · %s %d 级 · %s" % [
		int(e.get("week", 0)), reg, size_cn, int(e.get("level", 1)), reason_cn]


func _draw_wagon(r: Rect2) -> void:
	_panel(r, DdTheme.PANEL_DEEP)
	# 商队只有两件事可做，而面板和别的建筑一样高——
	# 内容靠上排会显得「下半截是空的」，所以整体垂直居中（M31）。
	var inner: float = 30.0 + 26.0 + 22.0 + 44.0 + 10.0 + 44.0
	var top: float = r.position.y + maxf(30.0, (r.size.y - inner) * 0.5)
	_text(Vector2(r.position.x + 16, top), "商队", DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(r.position.x + 16, top + 26),
		"饰品要在仓库里装上才生效——买回来放着不会自动戴。", DdTheme.FONT_MD, DdTheme.DIM)
	_add_button(Rect2(r.position.x + 16, top + 48, 340, 44), "bld_act:trinkets",
		("饰品仓库（%d / %d）" % [campaign.trinket_store.size(), int(campaign.store_slots)])
		if not campaign.trinket_store.is_empty() else "饰品仓库 · 空（打一趟才会有）",
		not campaign.trinket_store.is_empty())
	_add_button(Rect2(r.position.x + 16, top + 102, 340, 44), "bld_act:shop",
		"补给与饰品买卖", not campaign.shop_stock.is_empty())


## 每个建筑底部的一句「规则说明」（M31）。
##
## 建筑的规则都藏在代码里（占周、价格、上限），玩家只能靠试。
## 这句放在页脚，和城镇/地图屏的底部说明同一层：不抢视线，想知道时能看到。
func _building_hint(bid: String) -> String:
	match bid:
		"coach":
			return "新面孔每周换一批；免费征召是全员阵亡的保底。解雇会连等级和装备一起清空。"
		"smith":
			return "装备阶受等级限制：第 N 级才穿得上 N 阶。升级时技能等级同步 +1。"
		"guild":
			# 补一句「怎么升级」（M186）：右上角那颗按钮写着「需决心 3」，
			# 但玩家不知道「决心」从哪来 —— 而它只能靠出征攒。
			return "每人只能带 4 个技能。升级要决心等级够（每次出征涨），决心越高能升到的技能等级越高。"
		"sanitarium":
			return "一次只处理一条：先治病还是先清负面怪癖，本身就是要做的决定。"
		"abbey", "tavern":
			return "减压一次占一周。压力过 100 就会开始崩溃，越早处理越便宜。"
		"wagon":
			return "饰品买回来是放进仓库的，要在仓库里装上才生效——不会自动佩戴。"
		"graveyard":
			return "每个名字都记着死在第几周、哪片区域、那一趟结成了什么。"
		_:
			return ""


func _building_meta(bid: String) -> Array:
	for b in BUILDINGS:
		if str((b as Array)[0]) == bid:
			return b
	return ["", bid, ""]


## 建筑里的动作。全部走 Campaign 的校验方法，界面只负责把错误原因显示出来——
## 「为什么点不动」比「点了没反应」重要得多。
func _do_building_action(act: String) -> void:
	if act == "trinkets":
		_sel_trinket = ""
		_state = S_TRINKET
		queue_redraw()
		return
	if act == "shop":
		_sel_trinket = ""
		_state = S_SHOP
		queue_redraw()
		return
	if _building_hero.is_empty():
		_flash_msg("先选一个英雄")
		return
	var err: String = ""
	match act:
		"recruit":
			if not campaign.recruit(_building_hero):
				err = "招募失败（钱不够，或这个人还活着）"
		"upgrade":
			if not campaign.upgrade(_building_hero):
				err = "升级失败（钱或传家宝不够，或已满阶）"
		"disease":
			err = campaign.treat_disease(_building_hero)
		"quirk":
			err = campaign.purge_quirk(_building_hero)
		"rest":
			err = campaign.rest_at(_building, _building_hero)
	if not err.is_empty():
		_flash_msg(err)
	else:
		campaign.save()
		# 招募和升级是「立刻办完」，不占时间；疗养和减压才占一周
		if act == "disease" or act == "quirk" or act == "rest":
			_flash_msg("办好了 · 这一周他不能出征")
		else:
			_flash_msg("办好了")
	queue_redraw()


## 招一个新人入册（M27）。
##
## 单独一个入口而不是塞进 `_do_building_action`：那个函数的每一个分支
## 都作用在 `_building_hero`（左侧选中的人）上，而招新的对象还不在名册里，
## 根本没有「选中」这回事。硬塞进去只会让参数变成摆设。
func _do_hire(cls: String) -> void:
	if not campaign.hire(cls):
		# 三种失败原因分开说：钱不够 / 名册满 / 候选过期（换周了）
		if campaign.roster_full():
			# M28 起能解雇了，这句「还没做」从那时起就是错的
			_flash_msg("名册满了（%d 人）—— 先去马车赶走一个" % campaign.roster_max())
		elif not campaign.recruit_candidates.has(cls):
			_flash_msg("这个人已经不在本周的马车上了")
		else:
			_flash_msg("金币不足（需 %d）" % int(campaign.hire_cost().get("gold", 0)))
		return
	campaign.save()
	_flash_msg("%s 入册了 · Lv1，装备 0 阶" % _hero_label(cls))
	queue_redraw()


# ============================================================
# 公会屏：技能组（M19）
# ============================================================

## 一个英雄从 7 个技能里带 4 个。
##
## 这一屏存在的理由不是「配置」，是**取舍**：带上治疗就少一个输出位，
## 带满控制就没有回血。原来 7 个全开的时候，战斗里每个英雄都有 7 个按钮，
## 从来没有「必须放弃什么」的时刻——那不像原版，也不像决策。
## 公会卡上那一行数值（M150）：伤害、命中、暴击。
##
## 复用的 `build_spec` 是规则层算「这一击会怎样」的唯一入口 ——
## 界面自己再算一遍，迟早和战斗里对不上。
func _guild_skill_summary(hid: String, sid: String) -> String:
	if db == null:
		return ""
	var lv: Dictionary = _skill_level_of(hid, sid)
	if lv.is_empty():
		return ""
	var bits: Array = []
	# 数值一律先过 `_num()` 取，别直接 `float(x)`：技能等级表里缺字段时
	# 拿到的是 null，而 GDScript 的 `float(null)` 会抛「Nonexistent constructor」，
	# 报错信息完全不提是哪个字段（M150 第一次跑就撞上了）。
	# 数据里的 `dmg` 是**修正值**（0.0 / -0.4），不是「打多少点」——
	# 真实数字要过 `battle.build_spec`，那需要一个真实的 Combatant，
	# 而公会屏里没有战斗单位。所以这里给修正值：玩家要的是「哪个技能更狠」，
	# 加减号已经够比了（M150）。
	var dmg: float = _num(lv.get("dmg", 0.0))
	if dmg != 0.0:
		bits.append("伤害 %+.0f%%" % (dmg * 100.0))
	var acc: float = _num(lv.get("atk", 0.0))
	if acc != 0.0:
		# 「基础」两个字必须写（M151）：这一屏**没有目标单位**，
		# 算不了实战命中率（那要减去目标闪避、加上双方 buff）。
		# 写「命中 85%」会让玩家以为是这一刀真能打中的概率。
		bits.append("基础命中 %.0f%%" % (acc * 100.0))
	var crit: float = _num(lv.get("crit", 0.0))
	if crit != 0.0:
		bits.append("暴击 %+.0f%%" % (crit * 100.0))
	var hlv: float = _num(lv.get("heal", 0.0))
	if hlv > 0.0:
		bits.append("治疗 %+.0f%%" % (hlv * 100.0))
	return " · ".join(bits)


## 把 Variant 安全地当数字用（M150）。null / 字符串 → 0.0。
func _num(v: Variant) -> float:
	if v is int or v is float:
		return float(v)
	return 0.0


func _draw_guild() -> void:
	_header("公会 · 技能组",
		"每个英雄只能带 4 个 · 点技能卡切换 · 改完自动存档")

	var alive: Array = campaign.alive_ids()
	if alive.is_empty():
		_text(Vector2(28, 120), "名册里没有活人，先回城镇征召。", DdTheme.FONT_BD, DdTheme.WARN)
		_add_button(Rect2(24.0, size.y - 100.0 - NAV_H, size.x - 48.0, 56.0), "close_guild", "返回城镇")
		return
	if _guild_hero.is_empty() or not alive.has(_guild_hero):
		_guild_hero = str(alive[0])

	# —— 左：名册 ——
	# 两列紧凑列表（M31）：M19 建这一屏时名册只有 5 个人，单列 68 高刚好；
	# M27 名册能到 15 人后，单列 15×78 = 1170 会直接冲出屏幕底部，
	# 盖住底部说明和返回按钮——而工会是唯一没跟着改的建筑屏。
	# M58 竖屏：**左栏是角色清单，右栏是选中角色的技能清单**。
	#
	# 左栏 220 宽、一人一行（卡 212×64）。名册最多 15 个职业，
	# 15 × 72 = 1080，从 100 起刚好落到 1180，不用滚动。
	_text(Vector2(24, 88), "名册 %d 人" % alive.size(), DdTheme.FONT_BD, DdTheme.TEXT)
	# 底部安全区（M63）：这一屏原来把「7 张 142 高」和「15 人 × 72」都当成定值算，
	# 1334 高时刚好落到返回按钮上方；高度一少，最后一张技能卡的底边就落到
	# 「每人只能带 4 个技能…」那行说明字底下（看着像卡被切了）。
	# 所以两栏的步长都改成「按钮之上还剩多少」除出来。
	var g_btn_y: float = size.y - 44.0 - 56.0
	var g_span: float = g_btn_y - 30.0 - 100.0
	# 步长跟着人数走：5 人时一人 80 高（好点），15 人时压到最小能放得下
	var rstep: float = minf(80.0, g_span / float(maxi(1, alive.size())))
	for i in alive.size():
		_guild_roster_card(str(alive[i]),
			Rect2(24.0, 100.0 + float(i) * rstep, 212.0, rstep - 8.0))

	# —— 右：技能池 ——
	var rx: float = 248.0
	var rw: float = size.x - 272.0
	var taken: Array = campaign.equipped_skills(_guild_hero)
	var slots: int = campaign.skill_slot_max(_guild_hero)
	# 憎恶这类变身职业：7 个技能全开、不进技能组（M31）。
	# 区分「没选」和「不用选」——原来这里显示「已装备 0 / 7」，
	# 七个技能全是「未装备」，意思正好是反的。
	var selectable: bool = campaign.skill_selectable(_guild_hero)
	if not selectable:
		_text(Vector2(rx, 88), "%s · 变身职业，%d 个技能全开" % [
			_hero_label(_guild_hero), slots], DdTheme.FONT_BD, DdTheme.OK)
	else:
		_text(Vector2(rx, 88), "%s · 已装备 %d / %d" % [
			_hero_label(_guild_hero), taken.size(), slots], DdTheme.FONT_BD,
			DdTheme.TEXT if taken.size() >= slots else DdTheme.WARN)

	var ids: Array = campaign.skill_choices(_guild_hero)
	# M58：技能改 **2 列 × 4 行**网格。
	#
	# 单列 7 条 120 高的长条看起来像「一列标签」，而且每张卡右侧 3/4 是空的。
	# 2 列之后每张 339 宽，正好放下「名字 + 两行描述 + 状态」，整块变成一个方阵。
	# 右栏 478 宽：2 列每张只剩 233，描述放不下，所以**单列**，
	# 用高度换行数 —— 7 个技能 × 142 正好铺到按钮上方。
	var ggap: float = 12.0
	var gtop: float = 100.0
	# 卡高按剩余空间除：7 张 × 142 是 1334 下的算法，安全区一吃就多出来 100+
	var grow_h: float = clampf((g_span + ggap) / float(maxi(1, ids.size())) - ggap, 96.0, 130.0)
	for i in ids.size():
		var sid: String = str(ids[i])
		var on: bool = taken.has(sid) or not selectable
		var r2 := Rect2(rx, gtop + float(i) * (grow_h + ggap), rw, grow_h)
		var st2: int = _hit_state(r2, "guild_skill:" + sid)
		if on and st2 == TILE_IDLE:
			st2 = TILE_ACTIVE
		_tile(r2, st2)
		# 技能图标（M64 第十六轮）：同一套六分类，和战斗技能卡一致。
		# 七个技能排一列，纯文字时很难扫——图标让人一眼分出「哪几个是打人的」。
		var ico_tex: Texture2D = _skill_icon_tex(_guild_hero, sid)
		var tx: float = r2.position.x + 16.0
		if ico_tex != null:
			var isz: float = 46.0
			# 贴文字块而不是卡片正中：卡片 96~130 高，文字只占 38~90，
			# 居中会让图标看着掉到下半截去。
			# 原版图标是深色描边设计（原本画在浅灰按钮上），直接贴深色卡片
			# 会糊成一片，所以统一提亮 45%（M129）。
			# 图标本身是**黑底 + 彩边**（原版画在浅灰按钮上），直接贴深色卡
			# 会整块融进去、只剩几笔彩色线条。提亮到 1.95 让黑底变中灰，
			# 图案才跳得出来 —— 1.45 几乎看不出差别（M129 第一版）。
			draw_texture_rect(ico_tex, Rect2(r2.position.x + 14.0,
				r2.position.y + 18.0, isz, isz), false, Color(1.95, 1.95, 1.95))
			tx = r2.position.x + 62.0
		# ✓ / ＋ 同样是为了「一眼看出装没装」——M18 的出战卡就在这里栽过一次
		_text(Vector2(tx, r2.position.y + 38),
			("✓ " if on else "＋ ") + DdNames.skill_name(sid), DdTheme.FONT_BD,
			DdTheme.TEXT if on else DdTheme.TEXT.darkened(0.22))
		# 右侧：等级 + 状态 + 升级按钮（M126）。
		# 布局：38 行放「Lv2/5 · 已装备」，52~86 放升级按钮。
		var cur_lv: int = campaign.skill_level_of(_guild_hero, sid) if selectable else 0
		var lv_txt: String = ("Lv %d/5 · " % (cur_lv + 1)) if selectable else ""
		_text(Vector2(r2.position.x + r2.size.x - 150, r2.position.y + 38),
			lv_txt + (("全开" if not selectable else "已装备") if on else "未装备"),
			DdTheme.FONT_TAG, DdTheme.OK if on else DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_RIGHT, 134)
		if selectable:
			# 放在「Lvx/5」正下方（38 行文字下面的 44~74）。
			# 第一版写 52，高度 34 会顶到 86，而描述行从 78 开始 —— 和正文重叠。
			var upr := Rect2(r2.end.x - 96.0, r2.position.y + 46.0, 82.0, 26.0)
			var cap: int = campaign.skill_cap(_guild_hero)
			var cost: int = campaign.skill_upgrade_cost(_guild_hero, sid)
			var can_up: bool = cost >= 0 and cur_lv < cap
			_add_hit(upr, "guild_up:" + sid)
			# 画出按钮的样子（M186）：原来只有一行金色的「升级 120」小字，
			# 用户根本没意识到那是能点的 —— 他问「升级的入口在哪」。
			draw_rect(upr, DdTheme.BTN_OFF if not can_up else Color(0.42, 0.16, 0.12))
			draw_rect(upr, DdTheme.CRIT if can_up else DdTheme.PANEL_EDGE, false, 1.5)
			_text(Vector2(upr.position.x, upr.position.y + 19.0),
				("满级" if cost < 0 else (
					# 卡在决心等级：把**需要练到几级**算出来，别写「需 Lv2」——
					# `cap` 是 0 基索引，写 cap+2 会说少一级。
					("需决心 %d" % (2 * cur_lv + 3)) if cur_lv >= cap
					else "升级 %d" % cost)),
				DdTheme.FONT_TAG,
				DdTheme.CRIT if can_up else DdTheme.FAINT,
				HORIZONTAL_ALIGNMENT_CENTER, upr.size.x)
		# 描述行（M90）：原来 12px + DIM(#8b8a84) 压在深灰卡上，
		# 对比度低到「看着眼睛疼」。现在 13px + 提亮，并且**折成两行**
		# ——字号一大，一行就放不下 40 个字了。
		# 卡片够高才折两行：96 高的卡片塞两行会顶到边框。
		# 字号放大后两行描述会顶到右上角的「Lv / 需 LvN」（M138），只留一行。
		# 完整数值在战斗技能卡上能看到，这里负责「快速认技能」。
		# 宽度要给右上角的「Lv1/5 · 需 Lv3」让出 100（M138）：
		# 原来铺满整行，描述字一长就横着压到等级那一列上去。
		# 描述补上数值（M150）：原来只有「近战 · 可从 1、2 位发动」，
		# 而在公会的全部决策是「要不要花 2000 金升这个技能」——
		# 不知道打多少伤害、命中多少，这个决策无从谈起。
		# 数值用战斗卡同一个 `_action_summary`，两边不会说出不同的数。
		# 数值没能接上（M150 未完成）：`_skill_level_of` 返回的字典里
		# 取 `atk` / `dmg` 一直是 0，而我连着两版都没定位到原因。
		# 宁可不显示，也不要显示「命中 0%」这种错的数。留 `_guild_skill_summary`
		# 这个函数在这里，下一轮用调试打印确认字段名之后再接。
		var gline: String = _skill_line(_guild_hero, sid)
		var gsum: String = _guild_skill_summary(_guild_hero, sid)
		# 数值放**前面**（M151）：描述本身就有「近战 · 可从 1、2 位发动 ·
		# 打敌方 1、2 位」这么长，再接一段数值必然被行尾截掉 ——
		# 而这几个数字正是玩家比技能时最想看的。
		if not gsum.is_empty():
			gline = gsum + " · " + gline
		# 折两行（M186）：`gline` = 数值 + 「近战 · 可从 1、2 位发动 · 打敌方 1、2 位」，
		# 一行根本放不下，而 `max_lines = 1` 会把**后半截直接丢掉** ——
		# 丢掉的恰好是位次，也就是用户问的「哪些站位能放、能打到对面哪些位」。
		var dlines: Array = _wrap_tokens(gline,
			r2.end.x - tx - 106.0, DdTheme.FONT_TAG, 2)
		var dy: float = r2.position.y + 78.0
		for dl in dlines:
			_text(Vector2(tx, dy), str(dl), DdTheme.FONT_TAG, DdTheme.DIM,
				HORIZONTAL_ALIGNMENT_LEFT, r2.end.x - tx - 106.0)
			dy += 20.0
		if selectable:
			# 命中按登记顺序**正序**匹配，整卡先登记的话子按钮永远点不到 ——
			# 所以这里整卡最后登记，让上面那个 `guild_up:` 优先。
			_add_hit(r2, "guild_skill:" + sid)

	# M58：返回按钮贴底（原来写死 y=664，竖屏下悬在页面中间）
	# 按钮位置和上面算 `g_span` 用的是同一个值，别再算一遍
	var btn_y: float = g_btn_y
	_text(Vector2(DdTheme.MARGIN, btn_y - 16.0), _building_hint("guild"),
		DdTheme.FONT_MD, DdTheme.FAINT)
	_add_button(Rect2(24.0, btn_y, size.x - 48.0, 56.0), "close_guild", "返回城镇")


## 招不了的原因（M98）。卡片灰掉之后必须说清为什么，
## 否则玩家只会觉得「这个按钮坏了」。
func _hire_why(cls: String) -> String:
	if campaign == null:
		return ""
	if campaign.alive_ids().size() >= campaign.roster_max():
		return "名册已满"
	var cost: Dictionary = campaign.hire_cost()
	if campaign.gold < int(cost.get("gold", 0)):
		return "金币不足"
	var lo: Dictionary = cost.get("heirlooms", {})
	for k in lo.keys():
		if campaign.heirlooms.get(str(k), 0) < int(lo[k]):
			return "纹章不足"
	return "招募失败"


## 把「A · B · C」这种串按宽度折成最多 `max_lines` 行（M58）。
##
## 技能描述是「近战 · 可从 1、2 位发动 · 打敌方 1、2 位 · 命中 +85%」这种结构，
## 2 列卡片只有 339 宽，一行放不下。按分隔符切段比按字符切更不容易切在词中间。
func _wrap_tokens(s: String, width: float, fs: int, max_lines: int = 2) -> Array:
	var parts: PackedStringArray = s.split(" · ")
	var lines: Array = []
	var cur: String = ""
	for k in parts.size():
		var p: String = parts[k]
		var trial: String = p if cur.is_empty() else "%s · %s" % [cur, p]
		if _font.get_string_size(trial, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x <= width:
			cur = trial
			continue
		if not cur.is_empty():
			lines.append(cur)
			if lines.size() >= max_lines - 1:
				cur = DdTheme.ellipsis("%s · %s" % [p, " · ".join(parts.slice(k + 1))],
					_font, width, fs)
				break
		cur = p
	if not cur.is_empty() and lines.size() < max_lines:
		lines.append(cur)
	return lines


## 公会在册的一张卡（M58 横向滚动用）。
func _guild_roster_card(hid: String, r: Rect2) -> void:
	var sel: bool = hid == _guild_hero
	var st3: int = _hit_state(r, "guild_pick:" + hid)
	if sel and st3 == TILE_IDLE:
		st3 = TILE_ACTIVE
	_tile(r, st3)
	# 头像 + 纹章（M64 第十三轮）：公会是「给谁配技能」的地方，
	# 一列名字要挨个读才知道点的是谁。
	var ph6: float = minf(r.size.y - 14.0, 46.0)
	var pr6 := Rect2(r.position.x + 10.0, r.position.y + (r.size.y - ph6) * 0.5,
		ph6 * 0.754, ph6)
	_draw_hero_badge(hid, pr6, true)
	var gtx: float = pr6.end.x + 10.0
	_text(Vector2(gtx, r.position.y + 24), _hero_label(hid), DdTheme.FONT_MD,
		DdTheme.TEXT if sel else DdTheme.DIM)
	var n: int = campaign.equipped_skills(hid).size()
	var mx: int = campaign.skill_slot_max(hid)
	# 变身职业写「全开」而不是「0 / 7」——后者读起来像「一个都没带」
	var sel_ok: bool = campaign.skill_selectable(hid)
	_text(Vector2(gtx, r.position.y + 46),
		("%d / %d" % [n, mx]) if sel_ok else "全开", DdTheme.FONT_TAG,
		DdTheme.OK if (not sel_ok or (mx > 0 and n >= mx)) else DdTheme.WARN)
	# 上阵标记（M176）：这一屏要决定「给谁配技能」，
	# 而「这人会不会跟我下去」是决定要不要现在配的前提 ——
	# 原来这里完全没有这个信息，得退回队伍屏看一眼再进来。
	var g_on: bool = _prep_party.has(hid)
	_text(Vector2(r.end.x - 62.0, r.position.y + 24.0), "上阵" if g_on else "空闲",
		DdTheme.FONT_TAG, DdTheme.OK if g_on else DdTheme.FAINT,
		HORIZONTAL_ALIGNMENT_RIGHT, 54.0)
	_add_hit(r, "guild_pick:" + hid)


## 切换一个技能。满格时**不挤掉**别人，直接提示——挤掉的做法在 M18 的出战屏
## 已经被证明会让人误以为「点了没反应」。
func _toggle_skill(sid: String) -> void:
	if _guild_hero.is_empty():
		return
	var cur: Array = campaign.equipped_skills(_guild_hero)
	if cur.has(sid):
		if cur.size() <= 1:
			_flash_msg("至少带一个技能")
			return
		cur.erase(sid)
	else:
		var max_n: int = campaign.skill_slot_max(_guild_hero)
		if cur.size() >= max_n:
			_flash_msg("技能栏满（%d 个）——先点掉一个再装" % max_n)
			return
		cur.append(sid)
	var why: String = campaign.set_skills(_guild_hero, cur)
	if not why.is_empty():
		_flash_msg(why)
		return
	campaign.save()
	queue_redraw()


## 一行技能说明：类型 + 可发动位 + 目标 + 数值。
##
## 原版有完整描述文本，但那在 `.strings` 里，M0 的管线没抽，
## 所以这里只能从数值反推——比没有强，但离「读得懂这技能干什么」还差一步。
##
## 踩过的坑：`launch` / `target` 在 JSON 里是 **int 或 null**，不是字符串，
## `target` 还带两种前缀（`@` 己方、`~` 全体）。第一版直接 `str()` + 逐字符拆，
## 结果 null 变成 `<null>`，显示成「打 <、11、1、1、> 位」。
func _skill_line(hid: String, sid: String) -> String:
	var h: Dictionary = db.hero(campaign.def_of(hid))
	var lv_i: int = campaign.skill_of(hid)
	for s in (h.get("skills", []) as Array):
		if not (s is Dictionary) or str((s as Dictionary).get("id", "")) != sid:
			continue
		var levels: Array = (s as Dictionary).get("levels", [])
		if levels.is_empty():
			return ""
		var lv: Dictionary = levels[clampi(lv_i, 0, levels.size() - 1)]
		var bits: Array = []
		bits.append(_skill_kind(lv))
		var launch: String = _rank_list(lv.get("launch", null))
		if not launch.is_empty():
			bits.append("可从 %s 发动" % launch)
		bits.append(_target_text(lv.get("target", null)))
		var heal: Array = lv.get("heal", [])
		if not heal.is_empty():
			bits.append("回血 %d–%d" % [int(heal[0]), int(heal[1])])
		var dmg: float = float(lv.get("dmg", 0.0))
		if absf(dmg) > 0.001:
			bits.append("伤害 %+.0f%%" % (dmg * 100.0))
		var atk: float = float(lv.get("atk", 0.0))
		if absf(atk) > 0.001:
			bits.append("命中 %+.0f%%" % (atk * 100.0))
		var cr: float = float(lv.get("crit", 0.0))
		if absf(cr) > 0.001:
			bits.append("暴击 %+.0f%%" % (cr * 100.0))
		if int(lv.get("per_battle_limit", 0)) > 0:
			bits.append("每场 %d 次" % int(lv.get("per_battle_limit", 0)))
		# 不再拼 `Lv0`（M186）：右上角已经有「Lv1/5」，
		# 末尾再挂一个 Lv0 既重复又像是别的东西。
		return " · ".join(bits)
	return ""


## 技能类型。数据里相当一部分辅助技能没有 `type` 字段
## （battle_heal / inspiring_cry 都是空的），只能从效果反推。
##
## 先认「减压」再认「治疗」：鼓舞呐喊也有 heal（1–1），
## 但它的实际作用是压压力，标成治疗会让人以为它是奶。
## 这一格到底带奶还是带减压，是技能组里最核心的取舍，不能标错。
static func _skill_kind(lv: Dictionary) -> String:
	var t: String = str(lv.get("type", ""))
	match t:
		"melee": return "近战"
		"ranged": return "远程"
		"heal": return "治疗"
		"buff": return "增益"
		"debuff": return "减益"
		"move": return "位移"
		_: pass
	for e in (lv.get("effect", []) as Array):
		if str(e).to_lower().contains("stress"):
			return "减压"
	if not (lv.get("heal", []) as Array).is_empty():
		return "治疗"
	if not (lv.get("effect", []) as Array).is_empty():
		return "增益"
	return "其他"


## 掩码里能读出哪些数字位。"21" → "1、2 位"；null → ""。
static func _rank_list(mask: Variant) -> String:
	if mask == null:
		return ""
	var s: String = str(mask)
	var parts: Array = []
	for i in s.length():
		var ch: String = s.substr(i, 1)
		if ch >= "1" and ch <= "4" and not parts.has(ch):
			parts.append(ch)
	if parts.is_empty():
		return ""
	parts.sort()
	return "、".join(parts) + " 位"


## 目标描述。`~` = 敌方全体，`@` = 己方，null = 自身。
static func _target_text(mask: Variant) -> String:
	if mask == null:
		return "自身"
	var s: String = str(mask)
	if s.is_empty() or s == "null":
		return "自身"
	var ranks: String = _rank_list(mask)
	var ally: bool = s.begins_with("@")
	# 己方 1–4 位就是「全队」，写成「作用于己方 1、2、3、4 位」纯属噪音
	if ally and ranks == "1、2、3、4 位":
		return "作用于己方全体"
	var who: String = "己方" if ally else "敌方"
	var verb: String = "作用于" if ally else "打"
	if ranks.is_empty():
		return "%s %s" % [verb, who]
	if s.begins_with("~"):
		who = "敌方全体"
		verb = "打"
	return "%s %s %s" % [verb, who, ranks]


func _size_name_of(size_id: String) -> String:
	match size_id:
		"short": return "短途"
		"medium": return "中程"
		"long": return "长途"
		_: return size_id


## 本周任务板 → 难度卡的五行数据（M26 / M32）。
##
## 在这之前这四行是写死的常量，玩家永远能选 1/3/5 三档。
## 现在等级由 `Campaign.board` 每周重抽，尺寸固定（见 BOARD_SLOTS 的注释）。
## 返回格式沿用老的 `[size, level, 标题, 说明, quest]`，
## 这样两张屏幕里所有的排版代码一行都不用改。
##
## M32 起板子是**按区域**的：城镇上选哪个区域，就显示哪个区域那四张卡。
## 不传区域时用当前选中的，保持旧的调用方（准备屏）不用改。
func _board_rows(region: String = "") -> Array:
	var rgn: String = region if not region.is_empty() else _dungeon
	var src: Array = campaign.board_for(rgn)
	if src.is_empty():
		# 还没抽过（比如老驱动只建了 campaign 没读档）/ 区域名拼错：
		# 退回当前板子，宁可显示一张别的区域的卡，也不要一整屏空白。
		src = campaign.board
	var out: Array = []
	for slot in src:
		var d: Dictionary = slot
		var sn: String = str(d.get("size", "short"))
		var lv: int = int(d.get("level", 1))
		var q: String = str(d.get("quest", "explore"))
		var title: String = "%s · %d 级怪" % [_quest_size_word(q, sn), lv]
		if q == "kill_boss":
			title = "首领 · %d 级怪" % lv
		out.append([sn, lv, title, _board_note(sn, q), q])
	return out


## 任务类型 + 尺寸 → 卡片第一行那个词。
##
## 「探索 · 中程」和「清剿 · 中程」必须长得不一样：两种任务的目标完全不同
## （走到出口 vs 清光全图），只说尺寸等于让玩家点开才知道要干什么。
static func _quest_size_word(quest: String, size_id: String) -> String:
	var head: String = "探索"
	if quest == "cleanse":
		head = "清剿"
	elif quest == "gather":
		head = "收集"
	elif quest == "activate":
		head = "激活"
	elif quest == "inventory_activate":
		# 和「激活」分开写：两者在数据里同 type，但一个是碰到就算、
		# 一个是必须带道具。卡片上混成一个词，玩家进去才发现进度不动。
		head = "仪式"
	var tail: String = "短途"
	match size_id:
		"medium": tail = "中程"
		"long": tail = "长途"
	return "%s · %s" % [head, tail]


## 卡片第二行：这个任务长什么样。按尺寸和类型写，不按等级——
## 等级已经在标题里了，再重复一遍没有信息量。
static func _board_note(size_id: String, quest: String) -> String:
	if quest == "kill_boss":
		return "中程，终点必有首领"
	if quest == "cleanse":
		# 清剿不说「几场」：场数取决于地图随机，写死一个数会骗人。
		# 真正要传达的是「不能走直线」——这条决定玩家怎么规划路线。
		return "清光全图战斗，支路也得去"
	if quest == "gather":
		# 数量来自数据（item.amount = 3），但地图上会多放几个，
		# 所以不写「正好 3 个」——写死了玩家会以为漏找了一个。
		return "翻找指定奇物，集齐 3 件"
	if quest == "activate":
		return "找到铁处女，交互一次"
	if quest == "inventory_activate":
		# 和普通激活的区别就是「要带道具」——不写出来，玩家会以为
		# 这张卡和墓穴那张是一样的，进去才发现进度不动。
		return "带任务物品，用 3 次"
	match size_id:
		"short": return "4-7 场，休整 1 次"
		"medium": return "7-8 场，补给吃紧"
		"long": return "14 场，走出来就算赢"
		_: return ""


## 饰品形态（M64 第十六轮）。
##
## 490 件饰品不可能一件一张图，按 **id 里的物件词** 归到 10 类形态。
## 数组顺序就是优先级：越具体的物件词越靠前（`bloodstone_ring` 要归戒指，
## 不能因为含 stone 就归遗物）。
##
## 用**子串**而不是分词：`crow_wingfeather` / `worrystone` / `surgical_glove`
## 这种复合词分词后一个都命中不了。
##
## 最后兜底归遗物 —— 遗物本身就是最泛的一类（尖顶碑），
## 编号饰品（`antiq_1`、`madman_3`）没有任何语义可用，空着反而让货架参差不齐。
const TRK_RULES: Array = [
	["trk_scroll", ["scroll", "tome", "grimoire", "book", "page", "map", "pen",
		"letter", "orders", "portrait", "diary", "guide"]],
	["trk_chest", ["chest", "satchel", "padlock", "coffer", "casket", "lantern",
		"case", "box", "bag"]],
	["trk_potion", ["vial", "bottle", "flask", "cauldron", "chalice", "tonic",
		"potion", "incense", "tears", "herb", "oil", "cream"]],
	["trk_blade", ["sword", "blade", "dagger", "pistol", "musket", "knife", "axe",
		"spear", "arrow", "sheath", "shield", "bolas", "bulwark"]],
	["trk_bone", ["bone", "skull", "tooth", "claw", "talon", "eye", "hand",
		"heart", "brain"]],
	["trk_cloth", ["cloak", "coat", "robe", "bandana", "hood", "mask", "eyepatch",
		"boots", "greaves", "helmet", "crown", "mantle", "shroud", "collar",
		"glove", "belt", "cap", "handkerchief", "visage"]],
	["trk_ring", ["ring", "buckle", "bracer", "armlet", "signet", "hairpin", "band"]],
	["trk_pendant", ["pendant", "amulet", "charm", "talisman", "seal", "crest",
		"necklace", "medal", "locket", "fetish"]],
	["trk_feather", ["feather", "quill", "plume", "wing"]],
	["trk_relic", ["idol", "relic", "shrine", "statue", "stone", "crystal", "dice",
		"crucifix", "tambourine", "whistle", "orb", "rune", "doll", "censer",
		"candle", "memento", "rock", "weight", "gunpowder"]],
]

## tid → 形态 key。490 件每帧重算一遍子串匹配太浪费，算一次存起来。
var _trk_key_cache: Dictionary = {}


func _trinket_icon_key(tid: String) -> String:
	if _trk_key_cache.has(tid):
		return str(_trk_key_cache[tid])
	var low: String = tid.to_lower()
	var found: String = ""
	for rule in TRK_RULES:
		var key: String = str((rule as Array)[0])
		for w in ((rule as Array)[1] as Array):
			if low.contains(str(w)):
				found = key
				break
		if not found.is_empty():
			break
	if found.is_empty():
		found = "trk_relic"
	_trk_key_cache[tid] = found
	return found


func _trinket_icon(tid: String) -> Texture2D:
	return _skin.texture("icons", _trinket_icon_key(tid))


## 补给图标（M64 第十六轮）。id → 交付文件名的对照。
##
## `firewood` 和 `dog_treats` 这一批没画，故意**留空**而不是拿别的图标凑 ——
## 柴火画成火把、狗粮画成口粮，玩家会以为买错了东西。留空只是没图标。
const SUPPLY_ICONS: Dictionary = {
	"antivenom": "supply_antivenom",
	"bandage": "supply_bandage",
	"holy_water": "supply_holy_water",
	"laudanum": "supply_laudanum",
	"medicinal_herbs": "supply_herbs",
	"shovel": "supply_shovel",
	"skeleton_key": "supply_skeleton_key",
	"torch": "supply_torch",
}


## 补给面板（M154）：地牢里查看 + 使用背包。
##
## 之前玩家在准备屏买了一堆补给，进地牢后**没有任何地方能看到它们** ——
## 只有「点火把」和「休整」会自己扣两种，其余六种既看不到也用不了。
##
## 能直接用的只有三种（火把 / 口粮 / 鸦片酊），另外几种要么需要指定人
## （绷带止血、解毒剂解毒），要么只能对奇物用 —— 那些在行尾写明去处，
## 不让玩家点了才发现「这按钮怎么没反应」。
const SUPPLY_USE_HINT: Dictionary = {
	"bandage": "战斗中止血",
	"antivenom": "战斗中解毒",
	"medicinal_herbs": "战斗/奇物用",
	"holy_water": "奇物上用",
	"shovel": "奇物上用",
	"skeleton_key": "奇物上用",
}


func _supply_kinds() -> int:
	if exp == null:
		return 0
	var n: int = 0
	for k in SUPPLY_ICONS.keys():
		if exp.supply_count(str(k)) > 0:
			n += 1
	if int(exp.food) > 0:
		n += 1
	return n


func _draw_supply_panel() -> void:
	if exp == null:
		return
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.0, 0.0, 0.62))
	var w: float = minf(560.0, size.x - 60.0)
	var rows: int = SUPPLY_ICONS.size() + 1
	var h: float = 104.0 + float(rows) * 48.0 + 108.0
	var r := Rect2((size.x - w) * 0.5, maxf(20.0, (size.y - h) * 0.5), w, h)
	_panel(r, DdTheme.PANEL_DEEP)
	draw_rect(r, DdTheme.PANEL_EDGE, false, 2.0)
	_text(Vector2(r.position.x + 20.0, r.position.y + 34.0), "补给", DdTheme.FONT_H1, DdTheme.TEXT)
	_text(Vector2(r.end.x - 20.0, r.position.y + 34.0), "点「用」当场生效",
		DdTheme.FONT_SM, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 260.0)

	# 口粮排第一（它不在 SUPPLY_ICONS 里，走 Shop.FOOD_KEY）
	var entries: Array = [[Shop.FOOD_KEY, "口粮", int(exp.food)]]
	for k in SUPPLY_ICONS.keys():
		entries.append([str(k), DdNames.supply_name(str(k)), exp.supply_count(str(k))])

	var y: float = r.position.y + 52.0
	for e in entries:
		var sid: String = str(e[0])
		var nm: String = str(e[1])
		var cnt: int = int(e[2])
		var row := Rect2(r.position.x + 16.0, y, r.size.x - 32.0, 42.0)
		draw_rect(row, DdTheme.BTN)
		draw_rect(row, DdTheme.PANEL_EDGE, false, 1.0)
		var ic: Texture2D = _supply_icon(sid)
		var tx: float = row.position.x + 12.0
		if ic != null:
			draw_texture_rect(ic, Rect2(row.position.x + 8.0, row.position.y + 8.0, 26.0, 26.0), false)
			tx = row.position.x + 42.0
		_text(Vector2(tx, row.position.y + 27.0), nm, DdTheme.FONT_BD,
			DdTheme.TEXT if cnt > 0 else DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_LEFT, row.size.x - 220.0)
		_text(Vector2(row.end.x - 216.0, row.position.y + 27.0), "× %d" % cnt,
			DdTheme.FONT_BD, DdTheme.OK if cnt > 0 else DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_RIGHT, 56.0)
		var hint: String = str(SUPPLY_USE_HINT.get(sid, ""))
		if cnt <= 0:
			hint = "没有"
		if hint.is_empty() and cnt > 0:
			_add_button(Rect2(row.end.x - 108.0, row.position.y + 5.0, 100.0, 32.0),
				"supply_use:" + sid, "用", true)
		else:
			_text(Vector2(row.end.x - 116.0, row.position.y + 27.0), hint,
				DdTheme.FONT_TAG, DdTheme.FAINT, HORIZONTAL_ALIGNMENT_RIGHT, 116.0)
		_add_hit(row, "supply_noop:" + sid)
		y += 48.0

	# —— 本趟战利品（M169）——
	#
	# DD1 在地牢里能开背包看战利品，我们这一版没有。原因不是遗漏：
	# 我们的补给**不限格**（没有「背包满了要丢」的压力）、战利品**结算时才入库**
	# （不占地牢内的空间），所以没有「整理」这个动作。
	# 但「看不到这趟捡了多少」是真的缺点 —— 这里补上只读的统计。
	var ly: float = r.end.y - 140.0
	draw_line(Vector2(r.position.x + 16.0, ly - 14.0),
		Vector2(r.end.x - 16.0, ly - 14.0), DdTheme.PANEL_EDGE, 1.0)
	_text(Vector2(r.position.x + 20.0, ly + 6.0), "本趟战利品",
		DdTheme.FONT_MD, DdTheme.DIM)
	var hcount: int = 0
	for hk in (exp.loot_heirlooms as Dictionary).keys():
		hcount += int(exp.loot_heirlooms[hk])
	var gcount: int = 0
	for gk in (exp.loot_gems as Dictionary).keys():
		gcount += int(exp.loot_gems[gk])
	_text(Vector2(r.position.x + 20.0, ly + 32.0),
		"金币 %d · 传家宝 %d 件 · 宝石 %d 颗 · 饰品 %d 件" % [
			int(exp.loot_gold), hcount, gcount, (exp.loot_trinket_ids as Array).size()],
		DdTheme.FONT_BD, DdTheme.LIGHT, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 40.0)
	_text(Vector2(r.position.x + 20.0, ly + 54.0),
		"结算时自动入账 / 入仓库", DdTheme.FONT_TAG, DdTheme.FAINT,
		HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 40.0)

	_add_button(Rect2(r.position.x + 16.0, r.end.y - 50.0, r.size.x - 32.0, 38.0),
		"supply_close", "关闭")


func _supply_icon(id: String) -> Texture2D:
	# 口粮在准备屏排第一，它走的是 Shop.FOOD_KEY 而不是普通补给 id，
	# 图集里早就有 icon_food（第 8 轮就接进地图资源条了），直接复用。
	if id == Shop.FOOD_KEY:
		return _ico("icon_food")
	var key: String = str(SUPPLY_ICONS.get(id, ""))
	if key.is_empty():
		return null
	return _skin.texture("icons", key)


func _supply_label(id: String) -> String:
	if id == Shop.FOOD_KEY:
		return "口粮"
	return DdNames.supply_name(id)


# ============================================================
# 饰品商店（M16）
# ============================================================

## 拒绝原因翻人话。和 `_equip_reason` 分开写，因为两边的集合只有一半重叠
## （比如 `no_gold` 只有商店会有）。合成一个函数会让每个分支都要想
## 「这个 reason 另一半用不用」，反而更容易错。
func _shop_reason(reason: String) -> String:
	match reason:
		"no_gold":
			return "金币不够"
		"store_full":
			return "仓库满了"
		"limit":
			return "这件已经有一份了（唯一件）"
		"no_such_item":
			return "那里没有东西"
		"not_for_sale":
			return "这件不卖"
		"over_limit":
			return "超出携带上限"
		"no_shop":
			return "商店数据没加载"
		_:
			return reason


func _draw_shop() -> void:
	# 分页做成 header 右侧的两个胶囊（M66）：这一屏原来只有饰品，
	# 而 header 下面立刻就排货架，纵向没有余量再塞一条 tab 条。
	_header("城镇商店", "")
	var tab_w: float = 110.0
	var tab_x0: float = size.x - 24.0 - tab_w * 2.0 - 8.0
	# 「我的饰品」入口（M182）：马车中间屏删掉之后，换装备的入口挪到这里 ——
	# 原来它在那个中间屏的按钮里，入口一删就没地方去了。
	_add_button(Rect2(tab_x0 - 232.0, 8.0, 108.0, 34.0), "shop_my_trinkets", "我的饰品",
		not campaign.trinket_store.is_empty())
	_text(Vector2(tab_x0 - 116.0, 32.0), "金币 %d" % campaign.gold,
		DdTheme.FONT_BD, DdTheme.CRIT)
	for ti in 2:
		var tr := Rect2(tab_x0 + float(ti) * (tab_w + 8.0), 8.0, tab_w, 34.0)
		var on: bool = _shop_tab == ti
		_tile(tr, TILE_ACTIVE if on else TILE_IDLE, DdTheme.BTN)
		if on:
			draw_rect(tr, DdTheme.CRIT, false, 2.0)
		_text(Vector2(tr.position.x, tr.position.y + 23.0),
			"饰品货架" if ti == 0 else "补给柜台", DdTheme.FONT_MD,
			DdTheme.TEXT if on else DdTheme.DIM, HORIZONTAL_ALIGNMENT_CENTER, tr.size.x)
		_add_hit(tr, "shop_tab:%d" % ti)

	if campaign.shop == null:
		_text(Vector2(28, 100), "inventory.json / trinkets.json 没读到，商店不可用。", DdTheme.FONT_BD, DdTheme.WARN)
		_add_button(Rect2(24.0, size.y - 100.0 - NAV_H, size.x - 48.0, 56.0), "close_shop", "返回城镇")
		return
	if not _shop_ask.is_empty():
		_draw_shop_ask()
		return
	if _shop_tab == 1:
		_draw_shop_supplies()
		return

	# —— 上排：货架 ——
	_text(Vector2(28, 78), "在售（点一下买）", DdTheme.FONT_BD, DdTheme.DIM)
	# M58：3 列 × 240 = 756 在 750 宽下会溢出，改 **2 列 × 339**
	var cw: float = (size.x - 56.0 - 12.0) * 0.5
	var ch: float = 160.0
	var gap: float = 12.0
	for i in campaign.shop_stock.size():
		var id: String = str(campaign.shop_stock[i])
		var col: int = i % 2
		var row: int = i / 2
		var r := Rect2(28.0 + float(col) * (cw + gap), 90.0 + float(row) * (ch + gap), cw, ch)
		_panel(r, DdTheme.PANEL_DEEP)
		if id.is_empty():
			_text(Vector2(r.position.x + 12, r.position.y + 34), "已售出", DdTheme.FONT_MD, DdTheme.FAINT)
			continue
		var price: int = campaign.shop_price_at(i)
		var can: bool = campaign.gold >= price
		# 形态图标（M64 第十六轮）：货架上八格全是「某某戒指」这种名字，
		# 扫一行读不完；图标按形态分类，一眼分得出「这件是兵器还是书页」。
		var tico: Texture2D = _trinket_icon(id)
		var tx: float = r.position.x + 16.0
		if tico != null:
			var isz: float = 58.0
			draw_texture_rect(tico, Rect2(r.position.x + 14.0, r.position.y + 16.0,
				isz, isz), false)
			tx = r.position.x + 80.0
		_text(Vector2(tx, r.position.y + 34), DdNames.trinket_name(id), DdTheme.FONT_BD, DdTheme.TEXT if can else DdTheme.DIM)
		_text(Vector2(tx, r.position.y + 60), _trinket_summary(id), DdTheme.FONT_SM, DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_LEFT, r.end.x - tx - 12.0)
		_text(Vector2(tx, r.position.y + 96), _trinket_rarity_name(
			campaign.trinket_lib.rarity_of(id)), DdTheme.FONT_TAG, DdTheme.STAT)
		_text(Vector2(tx, r.position.y + 132), "%d 金" % price, DdTheme.FONT_BD, DdTheme.CRIT if can else DdTheme.WARN)
		# 选中的那颗描一道亮边（M183）——两步操作里，第一下必须**看得出来被选中了**，
		# 否则玩家会以为「点了没反应」，然后连点两下变成直接购买。
		if str(_shop_sel.get("kind", "")) == "buy" and int(_shop_sel.get("idx", -1)) == i:
			draw_rect(r, DdTheme.CRIT, false, 3.0)
		_add_hit(r, "shop_buy:%d" % i)
		_hit_overlay(r, "shop_buy:%d" % i)

	# —— 下排：仓库（卖） ——
	var stock_rows: int = int(ceil(float(campaign.shop_stock.size()) / 2.0))
	var store_top: float = 100.0 + float(stock_rows) * (ch + gap) + 18.0
	_text(Vector2(28, store_top - 10.0), "仓库（点一下卖，只能卖仓库里的，身上戴的要先卸）",
		DdTheme.FONT_BD, DdTheme.DIM)
	var sy: float = store_top + 6.0
	# 8 列 × 148 = 1200 也超宽，改 4 列 × 168
	var sw: float = (size.x - 56.0 - 30.0) / 4.0
	var sh: float = 96.0
	if campaign.trinket_store.is_empty():
		_text(Vector2(28, sy + 24), "空。打几趟就有了。", DdTheme.FONT_MD, DdTheme.FAINT)
	for j in campaign.trinket_store.size():
		var tid: String = str(campaign.trinket_store[j])
		var col2: int = j % 4
		var row2: int = j / 4
		var rr := Rect2(28.0 + float(col2) * (sw + 10.0), sy + float(row2) * (sh + 10.0), sw, sh)
		_panel(rr, DdTheme.PANEL)
		var tico2: Texture2D = _trinket_icon(tid)
		var tx2: float = rr.position.x + 12.0
		if tico2 != null:
			# 格子 166×96，44 是「占满高度又留得住边」的上限：
			# 再大名字就得让到 x+60 之外，四字饰品名会顶到卡片右缘。
			var isz2: float = 44.0
			draw_texture_rect(tico2, Rect2(rr.position.x + 10.0, rr.position.y + 8.0,
				isz2, isz2), false)
			tx2 = rr.position.x + 60.0
		_text(Vector2(tx2, rr.position.y + 34), DdNames.trinket_name(tid), DdTheme.FONT_MD, DdTheme.TEXT)
		_text(Vector2(tx2, rr.position.y + 62),
			"卖 %d 金" % campaign.shop.trinket_sell_price(tid), DdTheme.FONT_SM, DdTheme.DIM)
		if str(_shop_sel.get("kind", "")) == "sell" and int(_shop_sel.get("idx", -1)) == j:
			draw_rect(rr, DdTheme.CRIT, false, 3.0)
		_add_hit(rr, "shop_sell:%d" % j)
		_hit_overlay(rr, "shop_sell:%d" % j)

	var btn_y: float = size.y - 44.0 - 56.0
	_text(Vector2(28, btn_y - 46.0),
		"卖出价是买价的 10%%（数据里补给就是 10%%，饰品没有自己的卖价字段）。", DdTheme.FONT_SM, DdTheme.FAINT)
	_text(Vector2(28, btn_y - 26.0),
		"货架每趟回来换一批；已被买走的格子留空，不会往前挤。", DdTheme.FONT_SM, DdTheme.FAINT)
	_add_button(Rect2(24.0, btn_y, size.x - 48.0, 56.0), "close_shop", "返回城镇")


## 长按详情浮层（M183）。
##
## 手机上没有 hover，所以技能/饰品的完整数值只能靠长按看。
## 内容是**数据里全都有、但摘要放不下**的那些：命中、暴击、位次、效果名。
## 恢复期减益的中文说明（M201）。
##
## 键来自 `heroes.json → deaths_door.recovery_buffs`，数值来自 `buffs.json`。
## 没有像技能那样从数据现算：五个 buff 里 `attack_rating` 是 -0.02、
## `speed_rating` 是 -1，一个是比例一个是点数，混在一起换算，
## 算错的概率比写死更高，而算错的表现是「界面写着 -2% 但实际是 -2 点」。
## **改数值时这里要一起改。**
const RECOVERY_TIPS: Dictionary = {
	"mortalityACCDebuff": "命中 −2%",
	"mortalityDMGLowDebuff": "伤害下限 −5%",
	"mortalityDMGHighDebuff": "伤害上限 −5%",
	"mortalitySPDDebuff": "速度 −1",
	"mortalitySRDebuff": "受到的压力伤害 +10%",
	# 心脏骤停那一组更重。`stress_dmg_received_percent` 在数据里是 **-0.15**，
	# 和上面对应项的符号相反（那意味着受压变少，更像好事），疑似抓取时的符号问题，
	# 待核；这里按数据原样写，不在界面上编。
	"heartattackACCDebuff": "命中 −3%",
	"heartattackDMGLowDebuff": "伤害下限 −10%",
	"heartattackDMGHighDebuff": "伤害上限 −10%",
	"heartattackSPDDebuff": "速度 −2",
	"heartattackSRDebuff": "受到的压力伤害 −15%",
}


func _recovery_tips(hid: String) -> Array:
	var out: Array = []
	if db == null or campaign == null:
		return out
	var dd: Dictionary = db.hero(campaign.def_of(hid)).get("deaths_door", {})
	for bid in (dd.get("recovery_buffs", []) as Array):
		var t: String = str(RECOVERY_TIPS.get(str(bid), ""))
		if not t.is_empty():
			out.append(t)
	return out


func _draw_hold_tip() -> void:
	if _hold_shown.is_empty():
		return
	var lines: Array = []
	var title: String = ""
	if _hold_shown.begins_with("skill:") or _hold_shown.begins_with("guild_skill:"):
		var si2: int = int(_hold_shown.substr(_hold_shown.find(":") + 1))
		title = "技能"
		if _state == S_BATTLE and si2 >= 0 and si2 < _options.size():
			var op: Dictionary = _options[si2]
			var act: Dictionary = op.get("action", {})
			title = DdNames.skill_name(str(act.get("id", "")))
			lines.append("可发动：%s 号位" % _mask_text(int(act.get("launch_mask", 0))))
			lines.append("目标：%s 号位%s" % [
				_mask_text(int(act.get("target_mask", 0))),
				"（全体）" if bool(act.get("target_aoe", false)) else ""])
			var dr: Array = act.get("dmg_range", [])
			if dr.size() >= 2:
				lines.append("伤害 %d-%d" % [int(dr[0]), int(dr[1])])
			elif absf(float(act.get("dmg_mod", 0.0))) > 0.001:
				lines.append("伤害修正 %+.0f%%" % (float(act.get("dmg_mod", 0.0)) * 100.0))
			if float(act.get("heal", 0.0)) > 0.0:
				var hr: Array = act.get("heal_range", [])
				lines.append("治疗 %d-%d" % [int(hr[0]), int(hr[1])] if hr.size() >= 2 else "治疗")
			lines.append("命中 %d%% · 暴击 %d%%" % [
				int(round(float(act.get("atk", 0.0)) * 100.0)),
				int(round(float(act.get("crit", 0.0)) * 100.0))])
			var effs: Array = act.get("effects", [])
			if not effs.is_empty():
				lines.append("效果：" + ", ".join(effs.slice(0, 3)))
			if not str(op.get("why", "")).is_empty():
				lines.append("⚠ " + str(op.get("why", "")))
	elif _hold_shown.begins_with("tk_store:"):
		var tid3: String = str(campaign.trinket_store[int(_hold_shown.substr(9))]) \
			if int(_hold_shown.substr(9)) < campaign.trinket_store.size() else ""
		title = DdNames.trinket_name(tid3)
		lines.append(_trinket_summary(tid3))
		lines.append("卖价 %d 金" % (campaign.shop.trinket_sell_price(tid3) if campaign.shop != null else 0))
	elif _hold_shown.begins_with("hero_stat:"):
		# 长按队伍卡看状态（M201）。队伍卡上只有血、压力和几个两字标签，
		# 「恢复期」三个字背后是五条减益 —— 不写出来，玩家只能凭感觉觉得"变弱了"。
		var hid_h: String = _hold_shown.substr(10)
		title = _hero_label(hid_h)
		var st_h: Dictionary = exp.state.get(hid_h, {}) if exp != null else {}
		var mhp: int = _max_hp(hid_h)
		lines.append("生命 %d / %d" % [
			int(round(float(st_h.get("hp_ratio", 1.0)) * float(mhp))), mhp])
		lines.append("压力 %.0f / 200" % float(st_h.get("stress", 0.0)))
		if bool(st_h.get("at_deaths_door", false)):
			lines.append("死门：再受一次伤害即阵亡")
		if bool(st_h.get("recovering", false)):
			lines.append("恢复期（本趟地牢内有效，回城消失）")
			for tip in _recovery_tips(hid_h):
				lines.append("  " + str(tip))
		if not str(st_h.get("affliction", "")).is_empty():
			lines.append("崩溃：%s" % str(st_h.get("affliction", "")))
		if not str(st_h.get("virtue", "")).is_empty():
			lines.append("美德：%s" % str(st_h.get("virtue", "")))
	if lines.is_empty():
		return
	var w: float = minf(420.0, size.x - 40.0)
	var h: float = 64.0 + float(lines.size()) * 26.0
	var r := Rect2((size.x - w) * 0.5, size.y * 0.18, w, h)
	draw_rect(r, Color(0.05, 0.05, 0.07, 0.97))
	draw_rect(r, DdTheme.CRIT, false, 2.0)
	# 有图标就画（M184）：技能有技能图标、饰品有饰品图标，
	# 长按浮层是「看清楚这是啥」的地方，没图标等于少一半信息。
	var tip_tx: float = 16.0
	# 图标按 id 现取（M184）：技能走技能图标表，饰品走饰品图标
	var tic: Texture2D = null
	if _hold_shown.begins_with("skill:") and _state == S_BATTLE \
			and int(_hold_shown.substr(6)) < _options.size():
		var bh_sk: Dictionary = _options[int(_hold_shown.substr(6))]["action"]
		tic = _skill_icon_tex(str(_battle.awaiting_input.def_id) \
			if _battle != null and _battle.awaiting_input != null else "",
			str(bh_sk.get("id", "")))
	elif _hold_shown.begins_with("guild_skill:"):
		tic = _skill_icon_tex(campaign.def_of(_guild_hero), str(_hold_shown.substr(12)))
	elif _hold_shown.begins_with("tk_store:"):
		var ti4: int = int(_hold_shown.substr(9))
		if ti4 < campaign.trinket_store.size():
			tic = _trinket_icon(str(campaign.trinket_store[ti4]))
	if tic != null:
			draw_texture_rect(tic, Rect2(r.position.x + 16.0, r.position.y + 10.0, 34.0, 34.0), false)
			tip_tx = 60.0
	_text(Vector2(r.position.x + tip_tx, r.position.y + 32.0), title,
		DdTheme.FONT_BD, DdTheme.TEXT, HORIZONTAL_ALIGNMENT_LEFT, w - tip_tx - 16.0)
	var yy: float = r.position.y + 60.0
	for ln in lines:
		_text(Vector2(r.position.x + 16.0, yy), str(ln), DdTheme.FONT_MD,
			DdTheme.DIM, HORIZONTAL_ALIGNMENT_LEFT, w - 32.0)
		yy += 26.0


## 位次掩码 → 「1/2」这种可读文本。
func _mask_text(mask: int) -> String:
	if mask == 0:
		return "任意"
	var out: Array = []
	for i in 4:
		if (mask & (1 << i)) != 0:
			out.append(str(i + 1))
	return "/".join(out)


## 商店确认弹窗（M183）：选中之后第二下弹这个，点「确认」才真的交易。
func _draw_shop_ask() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.0, 0.0, 0.0, 0.68))
	var w: float = minf(460.0, size.x - 60.0)
	var h: float = 240.0
	var r := Rect2((size.x - w) * 0.5, (size.y - h) * 0.5, w, h)
	_panel(r, DdTheme.PANEL_DEEP)
	draw_rect(r, DdTheme.PANEL_EDGE, false, 2.0)
	var is_buy: bool = str(_shop_ask.get("kind", "")) == "buy"
	# 把物品图标画出来（M184）：这一屏本来就有一整套饰品图标，
	# 弹窗里却只有一行名字 —— 玩家得靠字去认这是哪件。
	# 用户的原话：「有现成图标的地方尽量都展示出来」。
	var ask_sid: String = ""
	var ask_idx: int = int(_shop_ask.get("idx", -1))
	if is_buy and ask_idx >= 0 and ask_idx < campaign.shop_stock.size():
		ask_sid = str(campaign.shop_stock[ask_idx])
	elif not is_buy and ask_idx >= 0 and ask_idx < campaign.trinket_store.size():
		ask_sid = str(campaign.trinket_store[ask_idx])
	var ask_tx: float = 20.0
	if not ask_sid.is_empty():
		var ico: Texture2D = _trinket_icon(ask_sid)
		if ico != null:
			draw_texture_rect(ico, Rect2(r.position.x + 20.0, r.position.y + 16.0, 52.0, 52.0), false)
			ask_tx = 84.0
	_text(Vector2(r.position.x + ask_tx, r.position.y + 40.0),
		"买下「%s」？" % str(_shop_ask.get("name", "")) if is_buy
		else "卖出「%s」？" % str(_shop_ask.get("name", "")),
		DdTheme.FONT_BD, DdTheme.TEXT, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - ask_tx - 20.0)
	_text(Vector2(r.position.x + 20.0, r.position.y + 76.0),
		("%d 金" % int(_shop_ask.get("price", 0))) if is_buy
		else ("收回 %d 金" % int(_shop_ask.get("price", 0))),
		DdTheme.FONT_H1, DdTheme.CRIT)
	_text(Vector2(r.position.x + 20.0, r.position.y + 112.0),
		"当前金币 %d" % campaign.gold, DdTheme.FONT_MD, DdTheme.DIM)
	_text(Vector2(r.position.x + 20.0, r.position.y + 140.0),
		"饰品是限定掉落，买错了没法退" if is_buy else "卖掉之后这件就没了",
		DdTheme.FONT_TAG, DdTheme.WARN)
	# 买得起 / 仓库还有位置才能确认（M183）：金币 0 摆着 10000 的货，
	# 「确认」照样亮着，点下去弹一句「金币不足」—— 那一步白走。
	var can_do: bool = true
	if is_buy:
		var pr: int = int(_shop_ask.get("price", 0))
		var sid_ask: String = ""
		var ai2: int = int(_shop_ask.get("idx", -1))
		if ai2 >= 0 and ai2 < campaign.shop_stock.size():
			sid_ask = str(campaign.shop_stock[ai2])
		can_do = campaign.gold >= pr and campaign.store_free() > 0 \
			and campaign.can_add_trinket(sid_ask)
	if can_do:
		_add_button(Rect2(r.position.x + 20.0, r.end.y - 62.0, (r.size.x - 52.0) * 0.5, 44.0),
			"shop_yes", "确认" if is_buy else "确认卖出")
	else:
		_add_button(Rect2(r.position.x + 20.0, r.end.y - 62.0, (r.size.x - 52.0) * 0.5, 44.0),
			"shop_yes",
			"金币不够" if campaign.gold < int(_shop_ask.get("price", 0)) else "仓库放不下", false)
	_add_button(Rect2(r.position.x + 32.0 + (r.size.x - 52.0) * 0.5, r.end.y - 62.0,
		(r.size.x - 52.0) * 0.5, 44.0), "shop_no", "再想想")


## 补给柜台（M66）。
##
## 买下一份就当场扣钱、进 `campaign.supplies`；出发屏会把它算进默认包，
## 并且在出发结算时**先扣库存再收钱**，所以这里买过的东西不会白花钱。
##
## 不做「卖回」：补给是消耗品，能卖回就等于开了个「买 75 卖 5」的兑换口，
## 玩家只会在商店里来回点，决策一点没多。
func _draw_shop_supplies() -> void:
	_text(Vector2(28, 78), "补给（点右边买一份，当场扣钱；出发时优先用这里的）",
		DdTheme.FONT_BD, DdTheme.DIM)
	var sids: Array = campaign.shop.supply_ids()
	# 行高按条数分（M66）：9 种补给固定 82 的话屏幕下方会空 300px，
	# 按可用高度均分，两种条数都填得满。
	var top: float = 96.0
	var bottom: float = size.y - 44.0 - 56.0 - 40.0
	var row_h: float = clampf((bottom - top) / float(maxi(1, sids.size())), 64.0, 104.0)
	var y: float = top
	for sid in sids:
		var sf: Dictionary = campaign.shop.supply_def(str(sid))
		var price: int = int(sf.get("buy", 0))
		var lim: int = int(sf.get("limit", 0))
		var stock: int = campaign.supply_stock(str(sid))
		var rr := Rect2(28.0, y, size.x - 56.0, row_h - 8.0)
		_panel(rr, DdTheme.PANEL_DEEP)
		_text(Vector2(rr.position.x + 16.0, rr.position.y + rr.size.y * 0.46),
			DdNames.supply_name(str(sid)), DdTheme.FONT_BD, DdTheme.TEXT)
		# 不编功效说明：数据里补给只有 id 和价钱，没有描述字段，
		# 凭空写一句「恢复少量生命」比不写更糟。
		_text(Vector2(rr.position.x + 16.0, rr.position.y + rr.size.y * 0.76),
			"单价 %d 金 · 上限 %d 份 · 已有 %d 份" % [price, lim, stock],
			DdTheme.FONT_TAG, DdTheme.DIM)
		var full: bool = lim > 0 and stock >= lim
		var poor: bool = campaign.gold < price
		var can: bool = not full and not poor
		var label: String = "到上限" if full else ("金币不足" if poor else "买 1")
		# 按钮做窄做矮一点：行高 104 时 100×76 的方块显得笨重，
		# 而且右侧留白比左侧大 —— 它只是个「买一份」的动作。
		_add_button(Rect2(rr.end.x - 108.0, rr.position.y + (rr.size.y - 56.0) * 0.5,
			92.0, 56.0), "sup_buy:" + str(sid), label, can)
		y += row_h
	_text(Vector2(28, bottom + 22.0),
		"补给只在出发时带走，回城不结余。这里买的数量会叠加进出发准备屏。",
		DdTheme.FONT_SM, DdTheme.FAINT)
	_add_button(Rect2(24.0, size.y - 44.0 - 56.0, size.x - 48.0, 56.0),
		"close_shop", "返回城镇")


# ============================================================
# 饰品：仓库与装备（M15）
# ============================================================

## 点一个槽位。三种情况，都走同一个入口，避免「装/卸」两套代码分叉：
##   * 选中了仓库里的一件 + 槽是空的 → 装上
##   * 槽里有东西 → 卸下来（不管有没有选中）
##   * 槽有东西 + 也选中了一件 → 先卸再装，等于换装
func _toggle_slot(hid: String, slot: int) -> void:
	var eq: Array = campaign.equipped_of(hid)
	var cur: String = str(eq[slot]) if slot < eq.size() else ""
	if not cur.is_empty():
		var err: String = campaign.unequip_trinket(hid, slot)
		if not err.is_empty():
			_flash_msg(_equip_reason(err))
			return
		campaign.save()
		queue_redraw()
		return
	if _sel_trinket.is_empty():
		_flash_msg("先在左边挑一件饰品")
		return
	var why: String = campaign.equip_trinket(hid, _sel_trinket)
	if why.is_empty():
		_flash_msg("%s 戴上 %s" % [_hero_label(hid), DdNames.trinket_name(_sel_trinket)])
		_sel_trinket = ""
		campaign.save()
	else:
		_flash_msg(_equip_reason(why))
	queue_redraw()


## 把拒绝原因翻成人话。
##
## 这些字符串是 Campaign 那一层返回的：那是规则层，不该知道界面语言；
## 界面层也不该反过来猜规则——所以在这里做一次显式映射。
## 不认识的 reason 原样显示，而不是吞掉（吞掉等于「点了没反应」）。
func _equip_reason(reason: String) -> String:
	match reason:
		"store_full":
			return "仓库满了，先把别的卸下来"
		"slots_full":
			return "这个人已经戴了两件"
		"class_mismatch":
			return "这个职业戴不了这件"
		"not_in_store":
			return "仓库里没有这件"
		"no_such_slot":
			return "这个格子是空的"
		"refused":
			return "装不上"
		_:
			return reason


func _draw_trinket() -> void:
	# 没有库就不画格子——`rarity_of` 会在 null 上炸。
	# 这种情况只会在数据包缺 trinkets.json 时出现，属于配置问题，
	# 说清楚比画一堆空格子强。
	if campaign.trinket_lib == null or not campaign.trinket_lib.is_loaded():
		_header("饰品仓库", "数据未加载")
		_text(Vector2(28, 100), "trinkets.json 没读到，饰品系统不可用。", DdTheme.FONT_BD, DdTheme.WARN)
		_add_button(Rect2(24.0, size.y - 100.0 - NAV_H, size.x - 48.0, 56.0), "close_trinkets", "返回城镇")
		return
	_header("饰品仓库",
		"点左边一件 → 再点右边某个空槽    仓库 %d / %d" % [
			campaign.trinket_store.size(), campaign.store_slots])

	# —— 左：仓库 4×4 ——
	# M58：仓库 4 列 × 148 = 632 时右边只剩 38 宽，装备区整块被挤到屏幕外。
	# 改成「上仓库、下装备」两段。
	var gx: float = 28.0
	var gy: float = 78.0
	var cw: float = (size.x - 56.0 - 30.0) / 4.0
	var ch: float = 110.0
	var gap: float = 10.0
	# 底部按钮与装备区的锚点提前算：中间那块详情面板要拿它当上边界，
	# 否则换一台设备（size.y 不同）就会和装备区撞上。
	var btn_y: float = size.y - 44.0 - 56.0
	var ids: Array = campaign.hero_ids()
	var ey: float = btn_y - 60.0 - 168.0
	# 行数按实际件数收缩（M66）。固定 16 格时，只有两件饰品的存档会看到
	# 14 个空格子 —— "仓库"看起来像还没做完的功能。
	# +1 是给新捡到的件留一个落点；上限仍是 store_slots。
	# 这几个量必须在画格子**之前**算好，详情卡还要用 rows_n 定上边界。
	var max_rows: int = int(ceil(float(campaign.store_slots) / 4.0))
	var rows_n: int = clampi(int(ceil(float(campaign.trinket_store.size() + 1) / 4.0)),
		1, max_rows)
	var cells_n: int = mini(rows_n * 4, campaign.store_slots)
	var free_slots: int = campaign.store_slots - cells_n
	_text(Vector2(gx, gy - 12), "仓库（点一下选中）", DdTheme.FONT_MD, DdTheme.DIM)
	if free_slots > 0:
		# 空位不画成空格子，写成一句数字：容量这件事有用，
		# 十几个空框没用 —— 那正是「看着没做完」的来源。
		_text(Vector2(gx + 160.0, gy - 12), "另有 %d 个空位" % free_slots,
			DdTheme.FONT_TAG, DdTheme.FAINT)
	for i in cells_n:
		var col: int = i % 4
		var row: int = i / 4
		var r := Rect2(gx + float(col) * (cw + gap), gy + float(row) * (ch + gap), cw, ch)
		var tid: String = str(campaign.trinket_store[i]) if i < campaign.trinket_store.size() else ""
		_panel(r, DdTheme.PANEL_DEEP if tid.is_empty() else DdTheme.PANEL)
		if tid.is_empty():
			_text(Vector2(r.position.x + 10, r.position.y + 30), "空", DdTheme.FONT_MD, DdTheme.FAINT)
			continue
		var sel: bool = _sel_trinket == tid
		if sel:
			draw_rect(r, DdTheme.CRIT, false, 2.0)
		# 形态图标（M64 第十六轮）：仓库 16 个格子全是名字，
		# 找一件「哪把武器」只能逐个读。图标占左上角，摘要留在它下方，全宽不受影响。
		var rico: Texture2D = _trinket_icon(tid)
		var ntx: float = r.position.x + 12.0
		if rico != null:
			var isz: float = 46.0
			draw_texture_rect(rico, Rect2(r.position.x + 10.0, r.position.y + 6.0,
				isz, isz), false)
			ntx = r.position.x + 60.0
		_text(Vector2(ntx, r.position.y + 30),
			DdNames.trinket_name(tid), DdTheme.FONT_BD, DdTheme.TEXT)
		_text(Vector2(r.position.x + 12, r.position.y + 58),
			_trinket_summary(tid), DdTheme.FONT_SM, DdTheme.DIM,
			HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 24.0)
		_text(Vector2(r.position.x + 12, r.position.y + 86),
			_trinket_rarity_name(campaign.trinket_lib.rarity_of(tid)), DdTheme.FONT_TAG, DdTheme.STAT)
		_add_hit(r, "tk_store:" + tid)
		_hit_overlay(r, "tk_store:" + tid)

	# —— 中：选中详情 ——
	#
	# 这一屏的内容总量本来就不满一屏：16 格仓库 + 5 个英雄空槽，
	# 中间会空 300px（存档里只有一两件饰品时特别明显）。
	# 填「选中饰品的完整属性」—— 格子里的摘要是**前 2 条**（格子窄），
	# 这里给全部，而且顺带补上职业限制和卖价，是这一屏真正缺的信息。
	#
	# 上边界取 min(仓库底 + 10, 装备区顶 - 300)：仓库行数会随 store_slots 变，
	# 写死 4 行在改容量时会直接压到装备区上。
	var d_top: float = gy + float(rows_n) * (ch + gap) + 10.0
	# 详情卡在「仓库底 ~ 装备区顶」之间垂直居中：行数少时上下留白均分，
	# 比「贴在上面、下面一大块黑」顺眼。
	var avail: float = ey - 40.0 - d_top
	var card_h: float = minf(286.0, avail)
	var d_r := Rect2(28.0, d_top + maxf(0.0, (avail - card_h) * 0.5),
		size.x - 56.0, maxf(150.0, card_h))
	_panel(d_r, DdTheme.PANEL_DEEP)
	if _sel_trinket.is_empty():
		_text(Vector2(d_r.position.x + 20, d_r.position.y + d_r.size.y * 0.5 + 8.0),
			"点仓库里任意一件，这里显示完整属性", DdTheme.FONT_BD, DdTheme.FAINT,
			HORIZONTAL_ALIGNMENT_CENTER, d_r.size.x - 40.0)
	else:
		_draw_trinket_detail(d_r)

	# —— 下：四个人的装备槽（横排四列）——
	_text(Vector2(28, ey - 12.0), "谁戴什么（点槽位卸下 / 先点上面一件再点空槽装上）",
		DdTheme.FONT_MD, DdTheme.DIM)
	# 列数跟着人数走：写死 4 列时第 5 个人直接被排到屏幕外
	# **最多 4 列 × 2 行**（M157）。原来 8 个人排一行，每列只有
	# (750-56-56)/8 ≈ 80px —— 头像 + 名字 + 饰品名 + 「卸」全塞进 80px，
	# 缩成一片看不清（用户原话「密密麻麻根本看不清」）。
	# 改成两行四列之后每列 165，正好放得下。
	var cols_h: int = mini(4, maxi(1, ids.size()))
	var rows_h: int = int(ceil(float(ids.size()) / float(cols_h)))
	var ew: float = (size.x - 56.0 - 8.0 * float(cols_h - 1)) / float(cols_h)
	var cell_h: float = (168.0 - 8.0 * float(rows_h - 1)) / float(rows_h)
	for hi in ids.size():
		var hid: String = str(ids[hi])
		var row2: Dictionary = campaign.hero(hid)
		var alive: bool = bool(row2.get("alive", true))
		var e: Array = campaign.equipped_of(hid)
		var hx: float = 28.0 + float(hi % cols_h) * (ew + 8.0)
		var ey2: float = ey + float(hi / cols_h) * (cell_h + 8.0)
		# 头像（M64 第十三轮）：列宽只有 132，纹章缩到 12px 就认不出，
		# 所以这里只放头像，纹章留给更宽的列表。
		var ph4: float = minf(ew * 0.22, 34.0)
		var pr4 := Rect2(hx, ey2 + 4.0, ph4 * 0.754, ph4)
		_draw_hero_badge(hid, pr4, alive)
		var htx: float = pr4.end.x + 8.0
		_text(Vector2(htx, ey2 + 18.0), _hero_label(hid), DdTheme.FONT_BD,
			DdTheme.TEXT if alive else DdTheme.FAINT, HORIZONTAL_ALIGNMENT_LEFT, ew - (htx - hx) - 4.0)
		_text(Vector2(htx, ey2 + 36.0), "装备 %d 阶" % int(row2.get("gear", 0)),
			DdTheme.FONT_TAG, DdTheme.DIM)
		for s in campaign.equip_slots:
			var sr := Rect2(hx, ey2 + 44.0 + float(s) * 50.0, ew, 46.0)
			var cur: String = str(e[s]) if s < e.size() else ""
			_panel(sr, DdTheme.PANEL_DEEP if cur.is_empty() else DdTheme.PANEL_HI)
			_hit_overlay(sr, "tk_slot:%s:%d" % [hid, s])
			if cur.is_empty():
				_slot_hint(sr, alive)
				_add_hit(sr, "tk_slot:%s:%d" % [hid, s])
				continue
			# 槽高只有 52，图标 30 放左侧；名字后面还要留 46 给「卸」
			var sico: Texture2D = _trinket_icon(cur)
			var stx: float = sr.position.x + 10.0
			if sico != null:
				var ssz: float = 34.0
				draw_texture_rect(sico, Rect2(sr.position.x + 8.0,
					sr.position.y + (sr.size.y - ssz) * 0.5, ssz, ssz), false)
				stx = sr.position.x + 44.0
			_text(Vector2(stx, sr.position.y + 22),
				DdNames.trinket_name(cur), DdTheme.FONT_MD, DdTheme.TEXT,
				HORIZONTAL_ALIGNMENT_LEFT, sr.end.x - stx - 46.0)
			_text(Vector2(sr.position.x + sr.size.x - 46, sr.position.y + 22), "卸",
				DdTheme.FONT_SM, DdTheme.WARN)
			_add_hit(sr, "tk_slot:%s:%d" % [hid, s])

	_text(Vector2(28, btn_y - 22.0),
		"每人两格。职业专用的件只能给对应职业；同名唯一的件全库只有一件。",
		DdTheme.FONT_SM, DdTheme.DIM)
	_add_button(Rect2(24.0, btn_y, size.x - 48.0, 56.0), "close_trinkets", "返回城镇")


## 选中饰品的详情卡（M64 第十七轮）。填在饰品仓库中段。
##
## 左：大图标 + 名字 + 稀有度；右：**全部**属性（格子里的摘要是前 2 条）。
## 底部一行：职业限制 + 卖价 —— 这两条是「要不要留」的判断依据，
## 但原来整个界面都没写，只能靠记忆。
func _draw_trinket_detail(r: Rect2) -> void:
	var tid: String = _sel_trinket
	var pad: float = 24.0
	# 图标 112：多数饰品只有 1~2 条属性，图标小了整张卡就空着。
	# 它也是这张卡唯一「一眼认出是什么东西」的东西。
	var ico_r := Rect2(r.position.x + pad, r.position.y + 28.0, 112.0, 112.0)
	var tex: Texture2D = _trinket_icon(tid)
	if tex != null:
		draw_texture_rect(tex, ico_r, false)
	else:
		draw_rect(ico_r, DdTheme.PANEL, true)

	var tx: float = ico_r.end.x + 24.0
	_text(Vector2(tx, r.position.y + 54.0), DdNames.trinket_name(tid),
		DdTheme.FONT_H1, DdTheme.TEXT)
	var rar: String = campaign.trinket_lib.rarity_of(tid)
	_text(Vector2(tx, r.position.y + 84.0), _trinket_rarity_name(rar),
		DdTheme.FONT_BD, DdTheme.STAT)

	# 属性两列：一件饰品最多 4~5 条，两列能在 286 里排得开。
	# 单列的话 5 条要到 y+250，正好压到底部那行限制说明上。
	var bits: Array = _trinket_stat_bits(tid, 0)
	if bits.is_empty():
		_text(Vector2(tx, r.position.y + 112.0), "无属性加成", DdTheme.FONT_MD, DdTheme.FAINT)
	var col_w: float = (r.end.x - tx - pad) * 0.5
	var rows: int = int(ceil(float(bits.size()) / 2.0))
	for i in bits.size():
		var col: int = i / maxi(rows, 1)
		var rowi: int = i % maxi(rows, 1)
		_text(Vector2(tx + float(col) * col_w, r.position.y + 122.0 + float(rowi) * 32.0),
			"· " + str(bits[i]), DdTheme.FONT_BD, DdTheme.TEXT)

	# 底部：职业限制 + 卖价
	var cls: Array = campaign.trinket_lib.classes_of(tid)
	var cls_txt: String = "通用（任何职业）"
	if not cls.is_empty():
		var ns: Array = []
		for c in cls:
			ns.append(DdNames.hero_name(str(c)))
		cls_txt = "限 " + "、".join(ns)
	var foot_y: float = r.end.y - 26.0
	_text(Vector2(r.position.x + pad, foot_y), cls_txt, DdTheme.FONT_MD, DdTheme.DIM)
	_text(Vector2(r.end.x - pad - 200.0, foot_y),
		"卖 %d 金" % campaign.shop.trinket_sell_price(tid), DdTheme.FONT_MD,
		DdTheme.STAT, HORIZONTAL_ALIGNMENT_RIGHT, 200.0)


## 空槽里的提示：能装就写「装这件」，不能装就写原因。
## 直接写「空」的话，玩家点了没反应会以为坏了。
func _slot_hint(sr: Rect2, alive: bool) -> void:
	var msg: String = ""
	if not alive:
		msg = "已阵亡"
	elif _sel_trinket.is_empty():
		msg = "空"
	else:
		msg = "装这件"
	_text(Vector2(sr.position.x + 10, sr.position.y + 21), msg, DdTheme.FONT_MD, DdTheme.DIM if not msg.begins_with("装") else DdTheme.OK)


## 一件饰品「大概加什么」。规则千奇百怪，这里只挑最常见的几种说，
## 抗性 sub_type 的中文。
## 八种，实测就是这八种（buffs.json 里 resistance 的 sub_type 全集）。
const RES_CN: Dictionary = {
	"poison": "中毒", "bleed": "流血", "blight": "枯萎", "disease": "疾病",
	"stun": "眩晕", "debuff": "减益", "move": "位移",
	"death_blow": "致死", "trap": "陷阱",
}


## 一条 buff → 一行中文（M64 第十七轮）。
##
## 覆盖怪癖/疾病引用到的 11 种 stat_type（实测 182 个 buff id 全部能在
## buffs.json 里查到）。认不出的退回 stat_type 原文 —— 显示原文总比空白强。
##
## **量级不统一，逐个确认过**：
##   attack_rating / crit_chance / defense_rating / protection_rating 是**比例**
##   （-0.1 = -10%），而 speed_rating 是**绝对值**（-5 就是 -5 点）。
##   按整数统一打会得到「命中-0」这种看起来像 bug 的文本。
func _buff_line(b: Dictionary) -> String:
	if b.is_empty():
		return ""
	var st: String = str(b.get("stat_type", ""))
	var sub: String = str(b.get("stat_sub_type", ""))
	var amt: float = float(b.get("amount", 0.0))
	# amount 为 0 的条目不显示：数据里有「惧人类 → 受压+15%；命中-0」这种，
	# 零值那条是数据包里的占位，写出来只会让玩家以为是 bug。
	if absf(amt) < 0.0001:
		return ""
	match st:
		"combat_stat_add":
			match sub:
				"speed_rating": return "速度%+.0f" % amt
				"attack_rating": return "命中%+.0f%%" % (amt * 100.0)
				"crit_chance": return "暴击%+.0f%%" % (amt * 100.0)
				"defense_rating": return "闪避%+.0f%%" % (amt * 100.0)
				"protection_rating": return "护甲%+.0f%%" % (amt * 100.0)
				"max_hp": return "生命%+.0f" % amt
		"combat_stat_multiply":
			match sub:
				"damage_low", "damage_high": return "伤害%+.0f%%" % (amt * 100.0)
				"max_hp": return "生命%+.0f%%" % (amt * 100.0)
		"stress_dmg_received_percent":
			return "受压%+.0f%%" % (amt * 100.0)
		"stress_heal_received_percent":
			return "减压%+.0f%%" % (amt * 100.0)
		"resistance":
			return "%s抗%+.0f%%" % [str(RES_CN.get(sub, sub)), amt * 100.0]
		"scouting_chance":
			return "侦察%+.0f%%" % (amt * 100.0)
		"food_consumption_percent":
			# 字段名带 percent，但实测值是**份数**（-1.0 / +3.0），
			# ×100 会写成「口粮消耗+300%」。按份数读才对。
			return "口粮%+.0f 份" % amt
		"hp_heal_percent":
			return "受疗%+.0f%%" % (amt * 100.0)
		"activity_side_effect_chance":
			return "活动副作用%+.0f%%" % (amt * 100.0)
		"resolve_check_percent":
			return "决心检定%+.0f%%" % (amt * 100.0)
		"upgrade_discount":
			return "升级费用%+.0f%%" % (amt * 100.0)
		# —— 以下补齐（M92）——
		# 这 16 个原来落到兜底分支，界面上直接露出英文键：
		# 「stun_chance +0」——既是英文，又是错的（amount 0.1 没 ×100，
		# %.0f 把它写成 +0，看着像「零效果」）。数据里 stat_type 共 27 种，
		# 之前只映射了 11 种，剩下 16 种全在这个兜底里。
		"stun_chance": return "眩晕%+.0f%%" % (amt * 100.0)
		"bleed_chance": return "流血%+.0f%%" % (amt * 100.0)
		"poison_chance": return "中毒%+.0f%%" % (amt * 100.0)
		"debuff_chance": return "减益%+.0f%%" % (amt * 100.0)
		"move_chance": return "位移%+.0f%%" % (amt * 100.0)
		"crit_received_chance": return "被暴击%+.0f%%" % (amt * 100.0)
		"damage_received_percent": return "受伤%+.0f%%" % (amt * 100.0)
		"hp_heal_received_percent": return "受疗%+.0f%%" % (amt * 100.0)
		"stress_dmg_percent": return "施加压力%+.0f%%" % (amt * 100.0)
		"stress_heal_percent": return "施加减压%+.0f%%" % (amt * 100.0)
		"starving_damage_percent": return "饥饿伤害%+.0f%%" % (amt * 100.0)
		"monsters_surprise_chance": return "怪物奇袭%+.0f%%" % (amt * 100.0)
		"party_surprise_chance": return "我方奇袭%+.0f%%" % (amt * 100.0)
		"resolve_xp_bonus_percent": return "决心经验%+.0f%%" % (amt * 100.0)
		"remove_negative_quirk_chance": return "消除负面怪癖%+.0f%%" % (amt * 100.0)
		"ignore_stealth": return "无视潜行"
	return "%s %+.0f" % [st, amt]


## 一条怪癖/疾病的效果文字（多个 buff 用「；」接起来）。
##
## 注意 `QuirkLib.load_from()` 在加载时就把 `buffs` 从 id 字符串
## **展开成 buff 定义字典**了（还顺手转成一个 `missing_buffs` 报缺）。
## 所以这里不能拿字符串去 `db.buff()` 查第二次 —— 那会传进一个
## 字典的 `str()` 结果，永远查不到，效果就静默变成空。
func _quirk_effect_text(qid: String) -> String:
	if campaign.quirk_lib == null or not campaign.quirk_lib.is_loaded():
		return ""
	var q: Dictionary = campaign.quirk_lib.get_quirk(qid)
	var parts: Array = []
	for b in (q.get("buffs", []) as Array):
		var def: Dictionary = (b as Dictionary) if b is Dictionary else db.buff(str(b))
		var line: String = _buff_line(def)
		# 去重：damage_low / damage_high 常常是同一个数，
		# 不去重会写成「伤害+15%；伤害+15%」。
		if not line.is_empty() and not parts.has(line):
			parts.append(line)
	if not parts.is_empty():
		return "；".join(parts)
	# 空的时候要**说明为什么空**（M189）。
	#
	# 170 条怪癖里有 32 条 `buffs: []` —— 原版就是这样（苦修、黑暗诱惑…），
	# 它们的作用在叙事或奇物标签上，没有战斗数值。
	# 原来这里直接返回空串，界面上就是「· 苦修」后面一片空白，
	# 看着像没写完。用户就是这么问的。
	var tag: String = str(q.get("curio_tag", ""))
	if not tag.is_empty():
		return "奇物互动：%s（无战斗数值）" % tag
	return "无战斗数值（背景设定）"


## 说不了的就报 buff 条数——不编造。
## 一件饰品的属性条目（原始数组）。
##
## `limit > 0` 时截断 —— 仓库格子只有一行宽，写满会顶到边框；
## 详情面板要全部，所以这里留了开关。原文案和截断逻辑都搬过来了，
## 改一处两处一起变，不会出现「格子里写的是前两条、详情里写的不一样」。
func _trinket_stat_bits(id: String, limit: int = 0) -> Array:
	var bits: Array = []
	if campaign.trinket_lib == null or not campaign.trinket_lib.is_loaded():
		return bits
	for b in campaign.trinket_lib.buffs_for([id]):
		var line: String = _buff_line(b as Dictionary)
		if line.is_empty():
			continue
		# 去重：damage_low / damage_high 常常是同一个数，
		# 不去重会写成「伤害+15%；伤害+15%」，看起来像 bug。
		if bits.has(line):
			continue
		bits.append(line)
		if limit > 0 and bits.size() >= limit:
			break
	return bits


func _trinket_summary(id: String) -> String:
	var bits: Array = _trinket_stat_bits(id, 2)
	if bits.is_empty():
		if campaign.trinket_lib == null or not campaign.trinket_lib.is_loaded():
			return ""
		var n: int = (campaign.trinket_lib.get_trinket(id).get("buffs", []) as Array).size()
		return "%d 条效果" % n
	return " ".join(bits)


## 这件饰品现在戴在谁身上（M111）。空字符串 = 没人戴。
func _who_wears(tid: String) -> String:
	if campaign == null or tid.is_empty():
		return ""
	for hid in campaign.hero_ids():
		var eq: Array = campaign.equipped_of(str(hid))
		for it in eq:
			if str(it) == tid:
				return str(hid)
	return ""


## 稀有度配色（M108）。原版用颜色区分档位，玩家扫一眼就知道哪件值钱；
## 我们之前只有个「稀有」两个字，还得读一遍才知道档次。
func _rarity_col(r: String) -> Color:
	match r:
		"uncommon":
			return DdTheme.OK
		"rare":
			return DdTheme.PARTY
		"very_rare":
			return DdTheme.STAT
		"ancestral", "trophy", "darkest_dungeon":
			return DdTheme.CRIT
	return DdTheme.DIM


func _trinket_rarity_name(r: String) -> String:
	match r:
		"very_common": return "普通"
		"common": return "常见"
		"uncommon": return "少见"
		"rare": return "稀有"
		"very_rare": return "珍稀"
		"ancestral": return "先祖"
		"trophy": return "战利品"
		"crow": return "乌鸦"
		"madman": return "疯汉"
		"collector": return "收藏家"
		"courtier": return "廷臣"
		"darkest_dungeon": return "至暗"
		"ancestral_shambler": return "先祖·蹒跚者"
		_:
			return DdNames.pretty(r)


# ============================================================
# 杂项
# ============================================================

func _drain_battle_events() -> void:
	if _battle == null:
		return
	if _battle.events.size() < _ev_pos:
		_ev_pos = 0
	while _ev_pos < _battle.events.size():
		_consume_battle_event(_battle.events[_ev_pos])
		_ev_pos += 1


## 打残骸的出手表现（M193）。
##
## `corpse_hit` / `corpse_destroyed` 原来在界面上完全静音：没有出招帧、
## 没有挥击特效、没有武器音。画面上只有「对面尸体掉一格耐久」，
## 玩家分不清是技能打出去了还是自己点空了。
func _corpse_strike_fx(actor_uid: int, target_uid: int, skill: String) -> void:
	_pose_for_action(actor_uid, skill)
	var u: Combatant = _unit_by_uid(actor_uid)
	if u == null:
		return
	if _fx != null:
		var pair: Dictionary = _fx.fx_for(u.def_id, skill)
		_fx_play(str(pair.get("performer", "")), actor_uid, 0.0, "feet")
		# 残骸不喷血，但**命中特效**要留：缺了它，挥击像打在空气里，
		# 看不出这一下到底生效没有。
		_fx_play(str(pair.get("target", "")), target_uid, 0.12, "chest")
	if _sfx != null:
		var imp: String = Sfx.impact_slot(_anim_of(actor_uid, skill))
		if not _sfx.has_slot(imp):
			imp = "imp_general"
		if not _sfx.has_slot(imp):
			imp = "hit"
		_sfx.play(imp, randf_range(0.95, 1.05), -1.0)


func _consume_battle_event(e: Dictionary) -> void:
	match str(e.get("t", "")):
		"round_start":
			_add_log("第 %d 轮" % int(e["round"]), DdTheme.FAINT)
		"order":
			# 本轮的出手顺序（M65）。规则层一直在发，界面从来没接过。
			# 存 uid 而不是名字：换位之后同一个格子里会换人，存名字就错位了。
			_order_ids = (e.get("ids", []) as Array).duplicate()
			_order_cur = -1
		"turn":
			var ti: int = _order_ids.find(int(e.get("actor", 0)))
			if ti >= 0:
				_order_cur = ti
		"stalemate":
			# 僵持以前是静默的：玩家看到的是「战斗突然结束、全队加压、回地图」。
			# 40 轮上限很少触发，但一旦触发就是「游戏坏了」的观感。
			_add_log("【僵持】%d 轮打不出结果，脱离接触" % int(e.get("round", 0)),
				DdTheme.WARN)
			_flash_msg("僵持：拖到回合上限，全队加压")
		"attack":
			var crit: bool = bool(e["crit"])
			_add_log("%s → %s  %d%s" % [_nm(e["actor"]), _nm(e["target"]), int(e["damage"]),
				"   暴击" if crit else ""], DdTheme.CRIT if crit else DdTheme.TEXT)
			# 出招换帧（M38）：事件的 `skill` 加上数据里的 `art.anim` 就能定位姿势。
			# 这是素材包最大的价值——每个技能都有自己的一帧，不是笼统地抖一下。
			_pose_for_action(int(e["actor"]), str(e.get("skill", "")))
			# 技能特效（M57）：`art.fx` 跟出手者（挥击/施法），`art.targchestfx` 跟目标胸口。
			# 命中特效晚 0.12 秒——同一帧出会让「挥」和「中」压成一个动作。
			var atk_u: Combatant = _unit_by_uid(int(e["actor"]))
			if atk_u != null:
				var pair: Dictionary = _fx.fx_for(atk_u.def_id, str(e.get("skill", "")))
				_fx_play(str(pair.get("performer", "")), int(e["actor"]), 0.0, "feet")
				_fx_play(str(pair.get("target", "")), int(e["target"]), 0.12,
					str(pair.get("target_anchor", "chest")))
			# 受击血花（M68）。原来走的是 `_fx_overlay`：那是原版钉在屏幕中心
			# 的**全屏叠加**（`.attack_overlay_pos 960 360`），358×513 的素材
			# 按屏宽拉到 750×1073 —— 竖屏下就是一张糊住整屏的红幕，
			# 所以施法者身上也全是血。现在只跟着受击者的胸口。
			_fx_blood_at("attack_overlay_" + ("crit" if crit else "hit"),
				int(e["target"]))
			_spawn_float(int(e["target"]), str(int(e["damage"])),
				DdTheme.CRIT if crit else DdTheme.HARM, crit)
			if _sfx != null:
				# 命中音（M51/M52）：
				#   怪物 → 它自己的攻击声（`atk/<family>`，3 个变体随机）
				#   英雄 → 按 `art.anim` 推出来的武器音（动作名本身就是武器名）
				# 两条路都有兜底，任何一环缺素材都不会静音。
				var atk_uid: int = int(e["actor"])
				var who: Combatant = _unit_by_uid(atk_uid)
				var played: bool = false
				var used: String = ""
				if who != null and not who.is_hero:
					used = EnemyVoice.attack_slot(who.def_id)
					played = _sfx.play_variant(used, EnemyVoice.ATTACK_TAKES,
						randf_range(0.95, 1.05), -1.0)
				if not played:
					var atk_anim: String = _anim_of(atk_uid, str(e.get("skill", "")))
					var imp: String = Sfx.impact_slot(atk_anim)
					if not _sfx.has_slot(imp):
						imp = "imp_general"      # 素材缺某个 kind 时退到钝击
					if not _sfx.has_slot(imp):
						imp = "hit"              # 再缺就用 M50 那把剑，绝不静音
					_sfx.play(imp, 1.0 if crit else randf_range(0.95, 1.05),
						1.0 if crit else -1.0)
					used = imp
				if crit:
					_sfx.play("crit", 1.0, -2.0)
				if _dev_ui:
					print("[sfx] %s %s" % [used, " + crit" if crit else ""])
			# 敌人语音（M51）：出手的咆哮 + 挨打的痛叫。
			# 两条分开播是有意的——「它扑上来」和「它挨了一下」是两件事，
			# 压成一条就分不出是谁在叫。
			_enemy_voice(int(e["actor"]), "aggro", -7.0)
			_enemy_voice(int(e["target"]), "crit" if crit else "hurt", -3.0)
			if bool(e["died"]):
				_add_log("【阵亡】%s" % _nm(e["target"]), DdTheme.WARN)
			elif bool(e["deaths_door"]):
				_add_log("【死门】%s" % _nm(e["target"]), DdTheme.WARN)
		"miss":
			if _sfx != null:
				_sfx.play("miss", 1.0, -4.0)
			_add_log("%s → %s  未命中（%.0f%%）" % [_nm(e["actor"]), _nm(e["target"]),
				float(e["chance"]) * 100.0], DdTheme.FAINT)
			# 挥空了也要出手（M68）。原来这里只有音效和飘字，于是画面上是
			# 「人站着不动、对面头上冒出 MISS」—— 看不出谁打的，也看不出是怎么落空的。
			# 出手特效照播，命中特效不播（那一下本来就没打中）。
			_pose_for_action(int(e["actor"]), str(e.get("skill", "")))
			var atk_m: Combatant = _unit_by_uid(int(e["actor"]))
			if atk_m != null:
				var pair_m: Dictionary = _fx.fx_for(atk_m.def_id, str(e.get("skill", "")))
				_fx_play(str(pair_m.get("performer", "")), int(e["actor"]), 0.0, "feet")
			_spawn_float(int(e["target"]), "MISS", DdTheme.FAINT)
		"heal":
			if bool(e.get("blocked", false)):
				_add_log("%s 治疗 %s  配额已尽" % [_nm(e["actor"]), _nm(e["target"])], DdTheme.WARN)
			elif int(e["amount"]) > 0:
				if _sfx != null:
					_sfx.play("heal", 1.0, -3.0)
				_add_log("%s 治疗 %s  +%d" % [_nm(e["actor"]), _nm(e["target"]), int(e["amount"])], DdTheme.HEAL)
				_spawn_float(int(e["target"]), "+%d" % int(e["amount"]), DdTheme.HEAL)
				# 治疗的**动作和特效**（M158）。原来这个分支只有音效 + 一行字 +
				# 一个数字，所以「回复类技能没动作」—— 素材包里
				# `fx/battle_heal`（出手）和 `fx/battle_heal_target`（命中）
				# 一直都在，只是从来没人播。
				# 姿势跟着 `_pose_for_action` 走（修女这类没有 attack_heal 帧的，
				# 姿势为空但特效照样出，至少不是「站着不动、血条涨一截」）。
				_pose_for_action(int(e["actor"]), str(e.get("skill", "")))
				_fx_play("battle_heal", int(e["actor"]), 0.0, "feet")
				_fx_play("battle_heal_target", int(e["target"]), 0.12, "chest")
		"effect":
			if e.has("stress") and absf(float(e["stress"])) >= 1.0:
				_spawn_float(int(e["target"]), "%+.0f 压力" % float(e["stress"]), DdTheme.STAT)
			if e.has("dot"):
				_add_log("　%s 陷入%s %d 层" % [_nm(e["target"]),
					"流血" if str(e["dot"]) == "bleed" else "中毒", int(e["amount"])], DdTheme.DIM)
			# 站稳了：这一下本来要把人推开，过了 move 抗性。
			# 不写出来的话，「被推」和「没被推」在界面上没有区别，
			# 玩家会以为抗性这个属性不存在。
			if str(e.get("resisted", "")) == "move":
				move_resists += 1
				_add_log("　%s 站稳了（位移被抵抗）" % _nm(e["target"]), DdTheme.DIM)
		"dot":
			_spawn_float(int(e["target"]), "-%d" % int(e["amount"]), DdTheme.HP)
		"stress":
			if _sfx != null and absf(float(e["delta"])) >= 1.0:
				_sfx.play("stress", 1.0, -5.0)
			_spawn_float(int(e["target"]), "%+.0f" % float(e["delta"]), DdTheme.STAT)
		"stunned":
			_add_log("　%s 被眩晕，跳过" % _nm(e["actor"]), DdTheme.FAINT)
		"pass":
			_add_log("　%s 空过" % _nm(e["actor"]), DdTheme.FAINT)
		"act_out":
			_add_log("　%s 崩溃发作，本回合不行动" % _nm(e["actor"]), DdTheme.WARN)
		"affliction":
			if _sfx != null:
				_sfx.play("stress", 0.7, 2.0)
			_add_log("【崩溃】%s（%s）" % [_nm(e["target"]), str(e.get("kind", ""))], DdTheme.WARN)
			_flash_msg("崩溃！")
		"virtue":
			if _sfx != null:
				_sfx.play("heal", 1.25, 2.0)
			_add_log("【美德】%s（%s）" % [_nm(e["target"]), str(e.get("kind", ""))], DdTheme.CRIT)
			_flash_msg("美德觉醒")
		"heart_attack":
			_add_log("【心脏骤停】%s" % _nm(e["target"]), DdTheme.WARN)
			_flash_msg("心脏骤停")
		"deaths_door":
			_add_log("【死门】%s" % _nm(e["actor"]), DdTheme.WARN)
		"surprised":
			_add_log("　%s 被惊袭，本轮不动" % _nm(e["actor"]), DdTheme.CRIT)
		"guard_up":
			_add_log("　%s 守护 %s（%d 回合）" % [_nm(e["actor"]), _nm(e["target"]),
				int(e.get("turns", 0))], DdTheme.OK)
		"guard":
			# 这一击原本打 target，实际落在 guard 身上。两个名字都要写出来，
			# 否则玩家只会看到「打向奶妈的一击，奶妈却没掉血」。
			_add_log("　%s 挡在 %s 前面" % [_nm(e["guard"]), _nm(e["target"])], DdTheme.OK)
			_spawn_float(int(e["guard"]), "挡住", DdTheme.OK)
			# 探身 + 被守护者标记（M200）：只有飘字的话，画面上两个人各站各的，
			# 看不出「他替你挨了这一下」。探身只改绘制坐标，不动 rank。
			_guard_fx[int(e["guard"])] = {"toward": int(e["target"]), "t": GUARD_FX_TIME}
			_guard_fx[int(e["target"])] = {"blocked": true, "t": GUARD_FX_TIME}
		"riposte_up":
			_add_log("　%s 摆出反击姿态（%d 回合）" % [_nm(e["actor"]),
				int(e.get("turns", 0))], DdTheme.CRIT)
		"riposte":
			_add_log("　%s 反击%s" % [_nm(e["actor"]), "" if bool(e.get("hit", true)) else "（对方扑空）"],
				DdTheme.CRIT)
		"swap":
			_add_log("　%s 与 %s 交换位置" % [_nm(e["a"]), _nm(e["b"])], DdTheme.HEAL)
		"move":
			# 三种 move 必须分开写，否则玩家会以为「怪物在推我」和「我自己走」
			# 是同一件事：前者是被动挨打，后者是花一回合换位置。
			#   skill == "move"  英雄主动调整站位（M9）
			#   shuffle == true  阵型被打乱，落点是随机的（M11）
			#   其它             被技能推开/拉近（M9 的 push/pull，M11 起会判抗性）
			if bool(e.get("shuffle", false)):
				shuffle_moves += 1
				_add_log("　%s 被挤到 %d 号位（阵型打乱）" % [
					_nm(e["actor"]), int(e["to"]) + 1], DdTheme.WARN)
			elif bool(e.get("self", false)):
				# 技能自带的位移（M53）：圣枪突进、开枪后退、收场退到队尾。
				# 这一支必须排在 push/pull 前面——否则「我自己冲上去」会被写成
				# 「被推到 1 号位」，读起来像挨了打。
				var step_fwd: bool = int(e["to"]) < int(e["from"])
				var step_word: String = "前进" if step_fwd else "后退"
				_add_log("　%s %s到 %d 号位" % [_nm(e["actor"]), step_word,
					int(e["to"]) + 1], DdTheme.OK)
				_spawn_float(int(e["actor"]), step_word, DdTheme.OK)
				if _dev_ui:
					# 位移只能靠打印确认：静态截图分不出「挪了一格」和「抖了一下」
					print("[move] %s %s %d -> %d (%s)" % [_nm(e["actor"]), step_word,
						int(e["from"]) + 1, int(e["to"]) + 1, str(e.get("skill", ""))])
			elif str(e.get("skill", "")) == "move":
				_add_log("　%s 移动到 %d 号位" % [
					_nm(e["actor"]), int(e["to"]) + 1], DdTheme.DIM)
			else:
				forced_moves += 1
				var pushed_back: bool = int(e["to"]) > int(e["from"])
				_add_log("　%s 被%s到 %d 号位" % [_nm(e["actor"]),
					"推" if pushed_back else "拉", int(e["to"]) + 1], DdTheme.WARN)
				_spawn_float(int(e["actor"]), "推" if pushed_back else "拉", DdTheme.WARN)
		"death":
			# 英雄阵亡和敌人阵亡是两种声音（M51）。
			# 原来一律用同一个 `death`，队友倒下和杂兵倒地听起来一模一样。
			if bool(e.get("hero", true)):
				if _sfx != null:
					_sfx.play("death")
			else:
				_enemy_voice(int(e["actor"]), "death", -1.0)
			_add_log("【阵亡】%s" % _nm(e["actor"]), DdTheme.WARN)
		"corpse_hit":
			# 打残骸（M73）：它不掉血，只掉耐久，所以日志不能说「造成伤害」。
			# 出手表现（M193）：这一支原来是全静音的，玩家看到的是
			# 「人站着不动、对面尸体掉一格耐久」，和「点错了」分不开。
			_corpse_strike_fx(int(e["actor"]), int(e["target"]), str(e.get("skill", "")))
			_add_log("　%s 击中残骸，还剩 %d 下" % [_nm(e["actor"]), int(e.get("left", 0))],
				DdTheme.DIM)
			_spawn_float(int(e["target"]), "残骸 -1", DdTheme.DIM)
		"corpse_destroyed":
			_corpse_strike_fx(int(e["actor"]), int(e["target"]), str(e.get("skill", "")))
			_add_log("　%s 清掉残骸 → 后排整体前移一格" % _nm(e["actor"]), DdTheme.OK)
			_spawn_float(int(e["target"]), "清场", DdTheme.OK)
			# 尸体从队列里被移除了，行动序里那个 uid 已经失效：
			# 先清掉，下一轮的 `order` 事件会重建。
			_order_ids.erase(int(e["target"]))
		"summon":
			# 召唤物是凭空出现的：没有这条日志，玩家只会看到敌人格子里
			# 多了一个单位，却不知道是谁叫来的、站在第几位。
			summons += 1
			_summoned_uids[int(e["uid"])] = true
			_add_log("　%s 召来了 %s（%d 号位）" % [
				_nm(e["actor"]), DdNames.monster_name(str(e.get("monster", ""))),
				int(e.get("rank", 0)) + 1], DdTheme.WARN)
			_spawn_float(int(e["uid"]), "召唤", DdTheme.WARN)
		"summon_fail":
			# 失败也要报。静默失败会让「这只怪为什么一直不召唤」变成
			# 只能读代码才能回答的问题。
			summon_fails += 1
			var why: String = str(e.get("reason", ""))
			var text: String = "场面满了" if why == "full" else (
				"已经召够了" if why == "capped" else "没有可召的目标")
			_add_log("　%s 想召唤，但%s" % [_nm(e["actor"]), text], DdTheme.DIM)


func _nm(uid: Variant) -> String:
	if _battle == null:
		return "?"
	for u in _battle.all_units():
		if u.uid == int(uid):
			return DdNames.unit_name(u.def_id)
	return "?"


func _monster_list(ids: Array) -> Array:
	var out: Array = []
	for i in ids:
		out.append(DdNames.monster_name(str(i)))
	return out


func _gear_level() -> int:
	if exp == null:
		return 0
	for s in exp.route:
		if s.has("gear"):
			return int(s["gear"])
	return 0


## 英雄自己的装备阶（城镇里花钱升的），路线里的 gear 只是兜底默认值
func _hero_gear(hid: String) -> int:
	if exp != null and exp.hero_gear.has(hid):
		return int(exp.hero_gear[hid])
	return _gear_level()


func _max_hp(hid: String) -> int:
	var b: Dictionary = db.hero_base(campaign.def_of(hid), _hero_gear(hid))
	return int(b.get("hp_max", 1))
