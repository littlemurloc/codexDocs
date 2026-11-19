
"""Separate the original alpha sprite and sample painted overlap at the rig joints."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SPRITE = Image.open(ROOT/"dark-elf-assassin.png").convert("RGBA")
WIDTH, HEIGHT = SPRITE.size
assert SPRITE.size == (1254,1254)
PAINT = Image.open(ROOT/"poses"/"underpaint-source.png").convert("RGBA")
ALPHA = SPRITE.getchannel("A")
INNER = ALPHA.filter(ImageFilter.MinFilter(15))
EMPTY = Image.new("RGBA", SPRITE.size)


def polygon(points):
    mask = Image.new("L", SPRITE.size)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return mask


def subtract(a, b):
    return ImageChops.subtract(a, b)


def union(*masks):
    result = masks[0]
    for mask in masks[1:]:
        result = ImageChops.lighter(result, mask)
    return result


def mask_art(art, mask):
    result = art.copy()
    result.putalpha(ImageChops.multiply(art.getchannel("A"), mask))
    return result


braid = polygon([(0,0),(680,0),(670,90),(658,121),(633,148),(617,177),(608,207),
    (551,201),(512,252),(483,291),(448,309),(432,339),(355,373),(277,387),(231,402),
    (231,526),(94,526),(0,530)])
head = subtract(polygon([(538,0),(1253,0),(1253,384),(814,384),(782,376),(748,361),
    (731,380),(702,413),(676,420),(664,398),(642,383),(626,354),(607,339),(595,321),
    (590,301),(550,296),(538,275)]),braid)
arm_near = subtract(polygon([(0,313),(456,315),(489,318),(527,328),(545,352),
    (565,388),(564,426),(547,449),(530,458),(508,470),(483,485),(452,496),(429,528),
    (418,550),(379,552),(346,562),(323,584),(313,624),(307,671),(310,698),(306,745),(290,778),
    (282,808),(270,821),(270,994),(0,995)]),union(braid,head))
arm_far = subtract(polygon([(791,392),(1253,388),(1253,1023),(995,1023),(943,914),
    (940,862),(931,819),(910,784),(890,759),(876,740),(851,719),(811,694),(792,663),
    (779,628),(772,596),(752,565),(742,540),(735,512),(747,482),(765,452),(768,417)]),head)
hand_near = ImageChops.multiply(arm_near, polygon([(0,715),(178,725),(197,714),(219,713),
    (246,722),(275,721),(314,718),(314,994),(0,994)]))
hand_far = ImageChops.multiply(arm_far, polygon([(886,740),(913,738),(941,730),(963,724),
    (984,725),(1004,734),(1022,745),(1253,739),(1253,1023),(886,1023)]))
lower = subtract(polygon([(0,636),(412,625),(449,615),(483,616),(520,635),(554,648),
    (592,663),(635,663),(668,654),(726,663),(805,681),(1253,685),(1253,1253),(0,1253)]),union(arm_near,arm_far,head,braid))
leg_near = ImageChops.multiply(lower,polygon([(0,812),(304,813),(340,807),(370,801),
    (410,808),(450,803),(484,790),(514,784),(528,813),(540,852),(552,883),(524,917),
    (507,948),(483,995),(459,1050),(460,1253),(0,1253)]))
leg_far = ImageChops.multiply(lower,polygon([(705,721),(1253,717),(1253,1253),(740,1253),
    (757,1144),(760,1075),(757,1034),(750,997),(735,969),(739,944),(738,921),(719,900),
    (706,876),(706,831),(705,791),(692,758)]))
visible = {
    "leg_far": leg_far, "leg_near": leg_near, "hips_legs": subtract(lower,union(leg_far,leg_near)),
    "hair_braid": braid, "hand_dagger_far": hand_far, "arm_far": subtract(arm_far,hand_far),
    "torso": ImageChops.invert(union(arm_near,arm_far,braid,head,lower)),
    "head": head, "hand_dagger_near": hand_near, "arm_near": subtract(arm_near,hand_near),
}
# Each visible pixel belongs to exactly one source part.
masks = np.stack([np.asarray(mask)>0 for mask in visible.values()])
assert np.all(masks.sum(axis=0)==1)

BIND = {
    "leg_far": ("hips_legs", (741,753), "远侧腿"),
    "leg_near": ("hips_legs", (478,807), "近侧腿"),
    "hips_legs": (None, (602,1231), "骨盆与腰布"),
    "hair_braid": ("head", (625,141), "银白长辫"),
    "hand_dagger_far": ("arm_far", (998,746), "远手与匕首"),
    "arm_far": ("torso", (778,459), "远侧手臂"),
    "torso": ("hips_legs", (599,647), "皮甲与躯干"),
    "head": ("torso", (689,355), "头部"),
    "hand_dagger_near": ("arm_near", (217,720), "近手与匕首"),
    "arm_near": ("torso", (493,385), "近侧手臂"),
}

# Pixel boxes in the paint sheet are mapped under the corresponding cut edges.
# Only pixels hidden by a different part in the reference pose can become underpaint.
PATCHES = [
    ("torso", (276,105,490,270), (598,306,762,427), [(605,336),(639,310),(724,315),(757,350),(733,413),(648,412),(613,380)]),
    ("torso", (152,289,336,424), (462,339,576,486), [(505,334),(561,370),(575,419),(561,459),(513,481),(471,444),(473,392)]),
    ("torso", (510,269,657,447), (726,396,827,555), [(747,395),(782,404),(821,448),(814,502),(766,552),(733,520)]),
    ("head", (310,124,463,241), (641,342,765,426), [(642,353),(681,341),(734,348),(758,374),(731,420),(670,414)]),
    ("arm_near", (933,120,1115,270), (448,325,572,467), [(467,339),(505,322),(554,343),(571,389),(552,443),(525,466),(468,427)]),
    ("arm_far", (1250,149,1432,296), (716,397,830,528), [(748,398),(809,422),(827,454),(800,504),(760,524),(725,485)]),
    ("hips_legs", (266,685,485,837), (398,596,782,801), [(438,609),(559,631),(660,645),(733,642),(783,731),(754,789),(661,786),(547,778),(467,786),(429,734)]),
    ("leg_near", (171,691,351,834), (397,737,561,856), [(421,743),(478,734),(552,765),(559,801),(523,845),(450,839)]),
    ("leg_far", (467,698,635,849), (682,674,825,797), [(709,682),(792,695),(823,736),(794,788),(733,793),(689,752)]),
    ("hand_dagger_near", (920,654,1075,747), (183,685,259,756), [(187,712),(212,689),(244,699),(257,732),(230,748),(193,745)]),
    ("hand_dagger_far", (1240,661,1405,758), (946,707,1042,774), [(957,732),(993,709),(1025,718),(1037,746),(1006,772),(956,764)]),
]

underpaint = {name: EMPTY.copy() for name in visible}
paint_scale = (PAINT.width/1536, PAINT.height/1024)
for name, source, dest, points in PATCHES:
    left, top, right, bottom = dest
    origin_box = [round(value*paint_scale[i%2]) for i,value in enumerate(source)]
    stamp = PAINT.crop(origin_box).resize((right-left,bottom-top), Image.Resampling.BICUBIC)
    layer = EMPTY.copy()
    layer.paste(stamp,(left,top))
    edge = ImageChops.multiply(polygon(points).filter(ImageFilter.GaussianBlur(1)),INNER)
    mask = ImageChops.multiply(edge,ImageChops.invert(visible[name]))
    underpaint[name].alpha_composite(mask_art(layer,mask))

parts = {}
assembled = EMPTY.copy()
for name, mask in visible.items():
    parent, pivot, title = BIND[name]
    layer = underpaint[name].copy()
    layer.alpha_composite(mask_art(SPRITE, mask))
    bbox = layer.getchannel("A").point(lambda a: 255 if a>=5 else 0).getbbox()
    assert bbox
    path = "parts/"+name+".png"
    part = layer.crop(bbox)
    part.save(ROOT/path)
    parts[name] = {"path":path,"position":bbox[:2],"size":part.size,"parent":parent,"pivot":pivot,"label":title}
    assembled.alpha_composite(layer)
(ROOT/"rig-binding.json").write_text(json.dumps({"parts":parts,"order":list(visible),"source_anchor":[602,1231]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def fit(target, art, area):
    bbox = art.getchannel("A").getbbox()
    if not bbox:
        return
    x,y,w,h = area
    tile = art.crop(bbox)
    tile.thumbnail((w,h),Image.Resampling.LANCZOS)
    target.alpha_composite(tile,(x+(w-tile.width)//2,y+(h-tile.height)//2))


def contact_sheet():
    page = Image.new("RGBA",(1280,753),"#211f23")
    draw = ImageDraw.Draw(page)
    def text(x, y, label, size):
        draw.text((x,y),label,fill="#ebded0",font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",size))
    text(26,18,"暗精灵女刺客 · 部件与补绘",29)
    draw.rounded_rectangle((22,68,335,720),9,fill="#2e2a2f")
    text(38,85,"原立绘",20)
    fit(page,SPRITE,(36,119,289,317))
    text(38,450,"零位拼装",19)
    fit(page,assembled,(44,479,278,214))
    draw.rounded_rectangle((351,68,1256,465),9,fill="#2e2a2f")
    text(369,86,"10 个绑定部件",20)
    for i,(name, part) in enumerate(parts.items()):
        x,y=366+(i%5)*176,126+(i//5)*163
        draw.rounded_rectangle((x,y,x+165,y+149),7,fill="#28252b")
        fit(page,Image.open(ROOT/part["path"]).convert("RGBA"),(x+9,y+8,147,111))
        text(x+9,y+123,part["label"],14)
    draw.rounded_rectangle((351,481,1256,720),9,fill="#2e2a2f")
    text(369,498,"隐藏重叠区域的补绘",18)
    for i,(name,title) in enumerate([("torso","颈根与胸侧"),("arm_near","肩袖"),("hips_legs","腰线"),("leg_near","腿根"),("hand_dagger_far","腕口")]):
        x,y=366+i*176,539
        draw.rounded_rectangle((x,y,x+165,y+165),7,fill="#28252b")
        fit(page,underpaint[name],(x+8,y+11,149,116))
        text(x+9,y+139,title,14)
    page.convert("RGB").save(ROOT/"parts-and-underpaint.png")


contact_sheet()
print("Bound", len(parts), "transparent parts,", sum(layer.getchannel("A").getbbox() is not None for layer in underpaint.values()), "underpaint layers.")

