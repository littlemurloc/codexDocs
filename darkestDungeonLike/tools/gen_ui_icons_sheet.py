"""生成第二批图标（30 张）的分组总览图，用于验收与存档。

画布宽度按「最长的组」算出来，不写死 ——
饰品那组有 10 个，写 1180 会把最后一个「遗物」切到画布外，
而且看图时不容易发现（右边正好是深色底）。
"""
from PIL import Image, ImageDraw, ImageFont

F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"


def f(sz, b=False):
    return ImageFont.truetype(FB if b else F, sz)


GROUPS = [
    ("技能 6（战斗卡 / 公会 / 抽屉 / 建筑内页共用）", [
        ("skill_melee", "近战"), ("skill_ranged", "远程"), ("skill_heal", "治疗"),
        ("skill_buff", "增益"), ("skill_debuff", "减益"), ("skill_move", "位移")]),
    ("补给 8（出发准备 9 行里除口粮外全部）", [
        ("supply_antivenom", "解毒剂"), ("supply_bandage", "绷带"),
        ("supply_holy_water", "圣水"), ("supply_laudanum", "鸦片酊"),
        ("supply_herbs", "药草"), ("supply_shovel", "铲子"),
        ("supply_skeleton_key", "骷髅钥匙"), ("supply_torch", "火把")]),
    ("饰品形态 10（490 件共用，按 id 关键词归类）", [
        ("trk_potion", "药瓶"), ("trk_feather", "羽毛"), ("trk_ring", "戒指"),
        ("trk_pendant", "吊坠"), ("trk_scroll", "书页"),
        ("trk_blade", "兵器"), ("trk_cloth", "衣物"), ("trk_bone", "骨头"),
        ("trk_chest", "容器"), ("trk_relic", "遗物")]),
    ("房间 6（地图格子）", [
        ("room_start", "入口"), ("room_goal", "出口"), ("room_battle", "战斗"),
        ("room_boss", "首领"), ("room_curio", "奇物"), ("room_empty", "空房")]),
]

CELL = 132
MARGIN = 28
COLS = max(len(items) for _, items in GROUPS)
W = MARGIN * 2 + CELL * COLS
H = 92 + sum(30 + CELL + 22 for _ in GROUPS)

canvas = Image.new("RGB", (W, H), (20, 20, 22))
d = ImageDraw.Draw(canvas)
d.text((MARGIN, 24), "第二批图标 · 30 张已入库并全部接进界面", font=f(26, True),
       fill=(236, 228, 212))
d.text((MARGIN, 60), "assets/art/ui/icons/   256×256 透明 PNG   内容占画布 97%   缩到 18~58px 显示",
       font=f(14), fill=(146, 144, 138))

y = 92
for title, items in GROUPS:
    d.text((MARGIN, y), title, font=f(17, True), fill=(224, 178, 74))
    y += 30
    x = MARGIN
    for key, cn in items:
        # 框 118、图 110：图里内容已经占到 97%，留 4px 边就够。
        # 原来框 118 只放 88 的图，再叠 80% 内容 —— 两层缩下来
        # 窄高的东西（圣水）只剩半个格子，看着像没画满。
        box = Image.new("RGB", (CELL - 14, CELL - 14), (32, 32, 36))
        im = Image.open("assets/art/ui/icons/%s.png" % key).convert("RGBA")
        im = im.resize((CELL - 22, CELL - 22), Image.LANCZOS)
        box.paste(im, ((box.width - im.width) // 2, (box.height - im.height) // 2), im)
        canvas.paste(box, (x, y))
        d.text((x + 2, y + CELL - 12), cn, font=f(13), fill=(198, 194, 186))
        x += CELL
    y += CELL + 22

canvas.save("docs/ui_icons_ingame.png")
print(canvas.size, "cols", COLS)
