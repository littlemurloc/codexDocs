
"""Rebuild the orc's action sheets and offline viewer data using Pillow and NumPy."""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ACTIONS = ROOT / "actions"
ACTIONS.mkdir(exist_ok=True)
FPS = 24
PADDING = (45, 41)
SIZE = (460, 392)
ANCHOR = (210, 333)
SCALE = .205
OFFSET = (36.67 + PADDING[0], 45.385 + PADDING[1])
STAGE = np.array([[SCALE, 0, OFFSET[0]], [0, SCALE, OFFSET[1]], [0, 0, 1]])
IDLE_RIG = json.loads((ROOT/"poisoned-idle-rig.json").read_text(encoding="utf-8"))
NEUTRAL_ORDER = IDLE_RIG["layer_order_back_to_front"]
PARTS = IDLE_RIG["parts"].copy()
IMAGES = {name: Image.open(ROOT/part["path"]).convert("RGBA") for name, part in PARTS.items()}
PELVIS = "hips_legs"


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def split_walk_parts():
    x, y = PARTS[PELVIS]["position"]
    lower = Image.new("RGBA", tuple(IDLE_RIG["source_size"]))
    lower.paste(IMAGES[PELVIS], (x, y))
    near_outline = [(0,733),(505,733),(548,766),(547,805),(521,836),(515,885),
                    (491,935),(503,963),(456,1004),(445,1080),(420,1253),(0,1253)]
    far_outline = [(733,750),(1253,748),(1253,1253),(683,1253),(700,1100),(714,1048),
                   (711,1001),(729,962),(730,915),(748,870),(760,819)]
    def stencil(points):
        mask = Image.new("L", lower.size)
        ImageDraw.Draw(mask).polygon(points, fill=255)
        return mask
    near, far = stencil(near_outline), stencil(far_outline)
    # Keep the red apron and overlap from both hip tops on a separate foreground layer.
    hips = ImageChops.invert(ImageChops.lighter(near, far))
    hips = ImageChops.lighter(hips, stencil([(342,672),(852,675),(855,757),(787,793),(724,781),(660,767),(549,786),(478,796),(345,805)]))
    for name, mask, pivot in [
        ("leg_near", near, (492, 773)),
        ("leg_far", far, (778, 786)),
        ("walk_hips", hips, tuple(PARTS[PELVIS]["pivot"])),
    ]:
        art = lower.copy()
        art.putalpha(ImageChops.multiply(art.getchannel("A"), mask))
        bbox = art.getchannel("A").getbbox()
        art = art.crop(bbox)
        target = "parts/" + name + ".png"
        art.save(ROOT/target)
        PARTS[name] = {"parent": PELVIS, "pivot": pivot, "position": bbox[:2], "size": art.size, "path": target}
        IMAGES[name] = art


split_walk_parts()
WALK_ORDER = ["leg_far", "leg_near", "walk_hips", *NEUTRAL_ORDER[1:]]


def pose(**channels):
    return channels


CLIPS = [
    dict(id="idle", name="探索待机", category="基础动作", frames=44, loop=True, marks=[(0,"站稳"),(13,"抬肩"),(29,"呼气")],
         keys=[
             (0,pose(torso=(-7,8,-2),head=(0,0,-2),arm_near=(1,6,4),arm_far=(0,7,-5))),
             (13,pose(torso=(-9,-4,-3),head=(0,-3,-1),arm_near=(0,2,2),arm_far=(0,4,-3))),
             (29,pose(torso=(-6,12,-1),head=(1,3,-3),arm_near=(2,8,5),arm_far=(0,6,-6))),
             (44,pose(torso=(-7,8,-2),head=(0,0,-2),arm_near=(1,6,4),arm_far=(0,7,-5))),
         ]),
    dict(id="walk", name="探索行走", category="基础动作", frames=24, loop=True, marks=[(0,"远脚着地"),(6,"迈步"),(12,"近脚着地"),(18,"换脚")],
         events=[(0,"step_far"),(12,"step_near")],
         keys=[
             (0,pose(hips_legs=(0,2,0),torso=(4,0,5),leg_near=(0,-1,13),leg_far=(6,0,-11), arm_near=(0,1,7),arm_far=(0,0,-7))),
             (6,pose(hips_legs=(0,-15,0),torso=(5,-1,6),head=(0,-4,-1),leg_near=(9,-19,-13),leg_far=(-4,10,1),arm_near=(2,0,0),arm_far=(0,0,0))),
             (12,pose(hips_legs=(0,3,0),torso=(4,0,4),leg_near=(5,0,-31),leg_far=(-7,-6,21),arm_near=(0,0,-9),arm_far=(0,0,9))),
             (18,pose(hips_legs=(0,-15,0),torso=(5,-1,6),head=(3,-3,0),leg_near=(-4,10,-7),leg_far=(9,-22,2),arm_near=(0,0,0),arm_far=(0,0,0))),
             (24,pose(hips_legs=(0,2,0),torso=(4,0,5),leg_near=(0,-1,13),leg_far=(6,0,-11),arm_near=(0,1,7),arm_far=(0,0,-7))),
         ]),
    dict(id="combat", name="战斗待机", category="基础动作", frames=34, loop=True, marks=[(0,"戒备姿势"),(8,"提斧"),(21,"压重心")],
         keys=[
             (0,pose()),(8,pose(torso=(5,-13,1.4),head=(1,-2,-2),arm_near=(0,-2,5),arm_far=(0,-4,-4),hand_axe_near=(0,0,-3))),
             (21,pose(torso=(4,9,3),head=(0,5,2),arm_near=(0,-1,2),arm_far=(0,-2,-3),hand_axe_far=(0,0,3))),
             (34,pose()),
         ]),
    dict(id="defend", name="架斧防御", category="基础动作", frames=22, loop=False, marks=[(0,"起势"),(5,"架斧"),(9,"稳住"),(17,"放下双斧")],
         keys=[
             (0,pose()),(5,pose(torso=(-12,20,-4),head=(0,13,5),arm_near=(3,-9,42),arm_far=(-7,-8,-49),hand_axe_near=(0,0,19),hand_axe_far=(0,0,-20))),
             (9,pose(torso=(-21,26,-6),head=(4,17,6),arm_near=(4,-6,37),arm_far=(-5,-8,-44),hand_axe_near=(0,0,12),hand_axe_far=(0,0,-10))),
             (14,pose(torso=(-10,16,-3),head=(0,8,3),arm_near=(2,-3,28),arm_far=(-3,-5,-31),hand_axe_near=(0,0,9),hand_axe_far=(0,0,-9))),
             (21,pose()),
         ]),
    dict(id="hit", name="受击后仰", category="基础动作", frames=15, loop=False, marks=[(0,"原位"),(2,"受击"),(5,"后仰"),(13,"站稳")],
         events=[(2,"hurt")], fx="hit",
         keys=[
             (0,pose()),(2,pose(torso=(-62,-14,-12),head=(-17,-8,-13),arm_near=(-5,6,22),arm_far=(10,0,13),hand_axe_near=(0,0,-10))),
             (5,pose(torso=(-48,4,-7),head=(-11,3,-7),arm_near=(0,10,13),arm_far=(6,7,13))),
             (8,pose(torso=(10,12,3),head=(4,1,4),arm_near=(0,2,-3),arm_far=(0,0,-9))),
             (14,pose()),
         ]),
    dict(id="dead", name="阵亡倒地", category="基础动作", frames=33, loop=False, marks=[(0,"踉跄"),(7,"失去支撑"),(11,"落地"),(23,"倒地保持")],
         events=[(11,"ground")], replacement=(11,33), fx="dead",
         keys=[
             (0,pose()),(3,pose(torso=(-41,23,-10),head=(-5,21,19),arm_near=(0,11,12),arm_far=(0,13,-7))),
             (7,pose(hips_legs=(-8,16,15),torso=(9,48,9),head=(5,27,18),arm_near=(1,-6,31),arm_far=(0,1,-28))),
             (10,pose(hips_legs=(0,31,29),torso=(26,48,12),head=(13,26,23),arm_near=(0,10,24),arm_far=(0,6,-22))),
         ]),
    dict(id="cross_break", name="交叉破甲", category="伤害技能", frames=25, loop=False, marks=[(0,"收肘蓄力"),(7,"第一道斧光"),(9,"交叉命中"),(13,"出手停顿"),(21,"回架")],
         events=[(9,"impact")], replacement=(7,14), fx="cross_break",
         keys=[
             (0,pose()),(5,pose(torso=(-31,23,-9),head=(-4,12,5),arm_near=(-4,-9,33),arm_far=(2,-5,-27),hand_axe_far=(0,0,-12))),
             (6,pose(torso=(3,6,7),head=(3,1,1),arm_near=(3,0,18),arm_far=(0,-9,-26))),
             (14,pose(torso=(61,23,9),head=(5,4,-3),arm_near=(5,5,14),arm_far=(0,7,-22),hand_axe_far=(0,0,14))),
             (20,pose(torso=(11,9,3),arm_near=(0,1,5),arm_far=(0,2,-7))),
             (24,pose()),
         ]),
    dict(id="falling_axes", name="双斧坠劈", category="伤害技能", frames=34, loop=False, marks=[(0,"落胯蓄力"),(11,"双斧举高"),(15,"落斧命中"),(20,"地面冲击"),(29,"起身回架")],
         events=[(15,"impact")], replacement=(15,24), fx="falling_axes",
         keys=[
             (0,pose()),(5,pose(torso=(-17,16,-4),head=(-3,8,3),arm_near=(0,-5,12),arm_far=(0,-6,-12))),
             (11,pose(torso=(7,6,-2),head=(4,-3,-7),arm_near=(9,-2,106),arm_far=(-6,-5,-107),hand_axe_near=(0,0,22),hand_axe_far=(0,0,-15))),
             (14,pose(torso=(29,23,13),head=(4,13,3),arm_near=(0,-5,59),arm_far=(-2,-3,-61))),
             (24,pose(torso=(24,63,13),head=(8,14,13),arm_near=(8,12,-18),arm_far=(0,0,13))),
             (29,pose(torso=(9,26,4),head=(4,5,5),arm_near=(2,4,-8),arm_far=(0,0,5))),
             (33,pose()),
         ]),
]


def sample_keys(keys, name, frame):
    if not keys:
        return 0, 0, 0
    for (start, a), (end, b) in zip(keys, keys[1:]):
        if frame <= end:
            p = max(0, (frame-start)/(end-start))
            w = p*p*(3-2*p)
            return tuple(k+(j-k)*w for k,j in zip(a.get(name,(0,0,0)),b.get(name,(0,0,0))))
    return keys[-1][1].get(name, (0,0,0))


def offset(x, y):
    return np.array([[1.,0,x],[0,1.,y],[0,0,1.]])


def world_poses(order, keys, frame, stage=STAGE):
    poses = {}
    def resolve(name):
        if name not in poses:
            x, y, angle = sample_keys(keys, name, frame)
            a = math.radians(angle)
            c, s = math.cos(a), math.sin(a)
            px, py = PARTS[name]["pivot"]
            local = offset(px+x, py+y) @ np.array([[c,-s,0],[s,c,0],[0,0,1]]) @ offset(-px,-py)
            parent = PARTS[name]["parent"]
            poses[name] = (resolve(parent) if parent else stage) @ local
        return poses[name]
    for name in order:
        resolve(name)
    return poses


def raster_pose(order, keys, frame):
    canvas = Image.new("RGBA", SIZE)
    matrices = world_poses(order, keys, frame)
    joints = {}
    for name, matrix in matrices.items():
        x, y, _ = matrix @ (*PARTS[name]["pivot"],1)
        joints[name] = [round(float(x),2), round(float(y),2)]
    for name in order:
        art = IMAGES[name]
        inverse = np.linalg.inv(matrices[name] @ offset(*PARTS[name]["position"]))
        canvas.alpha_composite(art.transform(SIZE, Image.Transform.AFFINE, tuple(inverse[:2].flatten()), Image.Resampling.BICUBIC))
    return canvas, joints


def pose_art(name, scale_size, center, floor):
    art = Image.open(ROOT/"poses"/(name+".png")).convert("RGBA")
    bounds = art.getchannel("A").point(lambda v: 255 if v>=24 else 0).getbbox()
    if not bounds:
        raise ValueError(f"Pose {name} has no visible alpha")
    art = art.crop(bounds)
    art.thumbnail(scale_size, Image.Resampling.LANCZOS)
    return art, (round(center-art.width/2), floor-art.height)


SPECIAL = {
    "cross_break": pose_art("cross_break", (275,250), 204, 292),
    "falling_axes": pose_art("falling_axes", (285,205), 205, 292),
    "dead": pose_art("dead", (280,125), 182, 296),
}


def alpha(value):
    return round(max(0,min(1,value))*255)


def mark(draw, p, strength, colors):
    for points, rgb, amount in zip(p, colors, (.65,.91,.95)):
        draw.polygon(points, fill=(*rgb,alpha(strength*amount)))


def slash(draw, points, strength, color):
    if strength <= 0:
        return
    x1,y1,x2,y2,bend=points
    normal = np.array([-(y2-y1),x2-x1]);normal = normal / np.linalg.norm(normal)
    start, end = np.array([x1,y1]), np.array([x2,y2])
    middles = [(start+(end-start)*k+normal*bend*v) for k,v in [(.23,.60),(.55,1),(.77,.74)]]
    a,b,c=middles
    shapes = [[tuple(x) for x in h] for h in [
       [start,a+normal*8,b+normal*12,c+normal*9,end,c-normal*5,b-normal*8,a-normal*7],
       [start,a+normal*2,b+normal*6,c+normal*4,end,c-normal*3,b-normal*5,a-normal*4],
       [start,a-normal*1,b-normal*1,c-normal*1,end,c-normal*3,b-normal*4,a-normal*2],
    ]]
    mark(draw,shapes,strength,[(30,19,15),color,(246,212,146)])


def dust(draw, frame, first, at, heavy):
    if frame < first or frame > first+12:
        return
    t=(frame-first)/13
    x,y=at
    colors=((105,56,33),(153,86,49),(211,151,91))
    if heavy and t<.6:
        w=10+83*t
        draw.polygon([(x-w,y),(x-14,y-8*(1-t)),(x+16,y-5),(x+w,y+4),(x+11,y+7),(x-19,y+4)],
                     fill=(211,151,91,alpha((.68-t)*.85)))
    for i in range(19 if heavy else 11):
        sign=-1 if i%2 else 1
        drift=sign*((i*19)%83+18)*t
        lift=(i%5+1)*t*19-t*t*62
        rx=x+drift+((i*23)%35)-17
        ry=y-lift-((i*19)%11)*t
        r=(2+i%4)*(1-t*.48)
        rgb=colors[i%3]
        draw.polygon([(rx-r,ry),(rx,ry-r),(rx+r*1.3,ry-.4*r),(rx+.4*r,ry+r)], fill=(*rgb,alpha((1-t)*.72)))


def effect(name, frame):
    ink = Image.new("RGBA", (400, 326))
    d = ImageDraw.Draw(ink)
    if name=="cross_break":
        slash(d,(229,232,371,121,-15),1-(frame-7)/7 if frame>=7 else 0,(207,101,58))
        slash(d,(245,136,375,246,17),1-(frame-9)/7 if frame>=9 else 0,(224,121,64))
        if frame in (9,10,11):
            k=frame-9
            x,y=311,181
            d.polygon([(x-13-k*5,y-3),(x-3,y-3),(x+3,y-22-k*4),(x+6,y-5),(x+25+k*5,y-9),(x+9,y+3),(x+8,y+17+k*5),(x,y+7),(x-11,y+17),(x-6,y+5)],fill=(250,215,153,alpha(1-.24*k)))
    elif name=="falling_axes":
        slash(d,(235,83,331,280,-29),1-(frame-13)/7 if frame>=13 else 0,(192,91,46))
        slash(d,(217,105,313,288,-23),.8-(frame-14)/8 if frame>=14 else 0,(228,132,65))
        dust(d,frame,15,(328,291),True)
    elif name=="dead":
        dust(d,frame,11,(189,293),False)
    elif name=="hit" and 2<=frame<=7:
        slash(d,(182,182,238,147,8),.94-(frame-2)/6,(184,91,72))
    canvas = Image.new("RGBA", SIZE)
    canvas.paste(ink,PADDING)
    return canvas


def build_atlas(filenames, clip, bodies, effects):
    count=len(bodies)
    columns=min(count,8)
    dims=(columns*SIZE[0], math.ceil(count/columns)*SIZE[1])
    sheets=[Image.new("RGBA",dims) for _ in filenames]
    rectangles=[]
    previews=[]
    for index, (body, fx) in enumerate(zip(bodies,effects)):
        x,y=(index%columns)*SIZE[0],(index//columns)*SIZE[1]
        rectangles.append([x,y,*SIZE])
        sheets[0].paste(body,(x,y))
        if len(sheets)==2:
            sheets[1].paste(fx,(x,y))
        combined=body.copy()
        combined.alpha_composite(fx)
        previews.append(combined)
    for image, filename in zip(sheets,filenames):
        image.save(ROOT/filename,optimize=True)
    return rectangles, previews


def make_clip(clip):
    name=clip["id"]
    order=WALK_ORDER if name=="walk" else NEUTRAL_ORDER
    count=clip["frames"]
    prefix=f"actions/{name}"
    filenames=[prefix+"-atlas.png"]
    if "fx" in clip: filenames.append(prefix+"-fx.png")
    bodies, effects, joints = [], [], []
    lower, upper=clip.get("replacement",(0,0))
    for frame in range(count):
        fx=effect(name,frame)
        if lower<=frame<upper:
            body=Image.new("RGBA",SIZE)
            art,(x,y)=SPECIAL[name]
            e=frame-lower
            if name=="cross_break":
                x += round(min(e,2)*5 - max(e-3,0)*1.5)
                y += round(min(e,2)*.5)
            elif name=="falling_axes":
                x += round(min(e,2)*4-max(e-4,0))
                y += 2 if e==1 else 0
            elif name=="dead":
                x += min(e,3)*2
                y += 3 if e==1 else 0
            body.alpha_composite(art,(x+PADDING[0],y+PADDING[1]))
            points=None
        else:
            body, points=raster_pose(order,clip["keys"],frame)
        bodies.append(body)
        effects.append(fx)
        joints.append(points)
    rectangles, preview=build_atlas(filenames,clip,bodies,effects)
    delays=[round((i+1)*1000/FPS)-round(i*1000/FPS) for i in range(count)]
    preview[0].save(ROOT/(prefix+".webp"), save_all=True, append_images=preview[1:],
                    duration=delays, loop=0 if clip["loop"] else 1, quality=87, method=3)
    representative=preview[clip["marks"][min(2,len(clip["marks"])-1)][0]]
    representative.save(ROOT/(prefix+"-thumb.png"))
    atlas={"animation":name, "texture":filenames[0], "fps":FPS, "loop":clip["loop"],
           "anchor_in_frame":ANCHOR, "frames_xywh":rectangles, "image_size":[min(count,8)*SIZE[0], math.ceil(count/8)*SIZE[1]],
           "events":[{"frame":f,"time":round(f/FPS,4),"event":event} for f,event in clip.get("events",[])],
           "joint_positions":joints}
    if len(filenames)==2:
        atlas["fx_texture"]=filenames[1]
    impact_points = {"cross_break": (311,181), "falling_axes": (328,291)}
    if name in impact_points:
        for item in atlas["events"]:
            if item["event"] == "impact":
                item["position_in_frame"] = [x+p for x,p in zip(impact_points[name],PADDING)]
    atlas_path=prefix+"-atlas.json"
    write_json(ROOT/atlas_path,atlas)
    motion_source={key:clip[key] for key in ("id", "name", "frames", "loop", "keys")}
    motion_source["rig_parts"]={name:PARTS[name] for name in dict.fromkeys([PELVIS,*order])}
    motion_source["draw_order"]=order
    motion_source["coordinate_system"]="Source pixels, y down, clockwise degrees. Channels are local x, y, angle."
    motion_source["interpolation"]="Smoothstep between pose frames."
    if "replacement" in clip:
        motion_source["replacement_frames"]={"from_inclusive":lower,"to_exclusive":upper,"path":f"poses/{name}.png"}
    motion_path=prefix+"-motion.json"
    write_json(ROOT/motion_path,motion_source)
    print(f"{name:16} {count:2} frames",flush=True)
    return {"id":name,"name":clip["name"],"category":clip["category"],"atlas":atlas,"atlasPath":atlas_path,
            "webp":prefix+".webp","motionPath":motion_path,"thumbnail":prefix+"-thumb.png","marks":clip["marks"]}


def poison_data():
    atlas=json.loads((ROOT/"poisoned-idle-atlas.json").read_text(encoding="utf-8"))
    marks=[(0,"起始站姿"),(8,"提肩吸气"),(19,"压身低头"),(25,"毒发颤动"),(32,"吐出毒雾"),(48,"回到站姿")]
    atlas["image_size"]=[2640,2608]
    # Evaluate the original source track including wrist tremor at these exact frame times.
    tracks={name:[(key["t"],{name:(key["x"],key["y"],key["angle"])}) for key in keys] for name,keys in IDLE_RIG["keyframes"].items()}
    joint_frames=[]
    stage=np.array([[.205,0,36.5],[0,.205,45.5],[0,0,1]])
    for i in range(60):
        time=i/FPS
        blend={}
        for name, keys in tracks.items():
            x,y,angle=sample_keys(keys,name,time)
            tremor=IDLE_RIG["secondary_tremor"]
            if name in tremor["targets"]:
                angle+=tremor["targets"][name]*math.exp(-((time-tremor["time_center"])/tremor["gaussian_width"])**2)*math.sin(2*math.pi*tremor["frequency_hz"]*time)
            blend[name]=(x,y,angle)
        matrices=world_poses(NEUTRAL_ORDER,[(time,blend)],time,stage)
        joint_frames.append({name:[round(float(x),2) for x in (mat @ (*PARTS[name]["pivot"],1))[:2]] for name,mat in matrices.items()})
    atlas["joint_positions"]=joint_frames
    atlas_art=Image.open(ROOT/atlas["texture"])
    x,y,w,h=atlas["frames_xywh"][31]
    atlas_art.crop((x,y,x+w,y+h)).save(ACTIONS/"poisoned_idle-thumb.png")
    return {"id":"poisoned_idle","name":"沾毒待机","category":"状态动作","atlas":atlas,"atlasPath":"poisoned-idle-atlas.json",
            "webp":"poisoned-idle.webp","motionPath":"poisoned-idle-rig.json","marks":marks,"thumbnail":"actions/poisoned_idle-thumb.png"}


def make_showcase(clips):
    width,height=660,340
    background=Image.new("RGB",(width,height),"#262621")
    font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",17)
    small=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",12)
    d=ImageDraw.Draw(background)
    for i,name in enumerate(("交叉破甲","双斧坠劈")):
        x=12+326*i
        d.rounded_rectangle((x,12,x+310,324),8,fill="#303029")
        d.text((x+13,22),name,font=font,fill="#e9d8b6")
    d.text((24,300),"斧光交叠时结算伤害",font=small,fill="#b7a58a")
    d.text((350,300),"双斧砸地时结算伤害",font=small,fill="#b7a58a")
    images=[]
    for clip in clips:
        body=Image.open(ROOT/clip["atlas"]["texture"])
        fx=Image.open(ROOT/clip["atlas"]["fx_texture"])
        prepared=[]
        for x,y,w,h in clip["atlas"]["frames_xywh"]:
            box=(x,y,x+w,y+h)
            frame=body.crop(box);frame.alpha_composite(fx.crop(box))
            prepared.append(frame.resize((297,253),Image.Resampling.LANCZOS))
        images.append(prepared)
    rendered=[]
    for i in range(42):
        board=background.copy()
        for n,prepared in enumerate(images):
            image=prepared[min(i,len(prepared)-1)]
            board.paste(image,(19+326*n,43),image)
        rendered.append(board)
    palette=Image.new("RGB",(width*4,height))
    for n,i in enumerate((0,8,15,21)): palette.paste(rendered[i],(n*width,0))
    palette=palette.quantize(colors=190)
    frames=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in rendered]
    frames[0].save(ROOT/"skills-preview.gif",save_all=True,append_images=frames[1:],duration=[round((i+1)*100/FPS)*10-round(i*100/FPS)*10 for i in range(len(frames))],loop=0,optimize=True,disposal=1)


clips=[make_clip(clip) for clip in CLIPS]
clips.insert(6,poison_data())
parts_order=[*NEUTRAL_ORDER,"leg_far","leg_near","walk_hips"]
summary=[{key:value for key,value in item.items() if key not in ("atlas","thumbnail","marks")} for item in clips]
write_json(ROOT/"actions-index.json",summary)
bundle={"clips":clips,"parts":PARTS,"partOrder":parts_order}
(ROOT/"viewer-data.js").write_text("window.ORC_VIEWER_DATA = "+json.dumps(bundle,ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
make_showcase(clips[-2:])

