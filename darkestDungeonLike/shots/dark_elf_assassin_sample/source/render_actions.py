"""Build the dark elf animation atlases and offline viewer catalog."""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FPS = 24
SIZE = (460,392)
ANCHOR = (210,333)
SCALE = .191
BINDING = json.loads((ROOT/"rig-binding.json").read_text(encoding="utf-8"))
PARTS = BINDING["parts"]
ORDER = BINDING["order"]
IMAGES = {name:Image.open(ROOT/part["path"]).convert("RGBA") for name,part in PARTS.items()}
OFFSET = tuple(screen-SCALE*origin for screen,origin in zip(ANCHOR,BINDING["source_anchor"]))
STAGE = np.array([[SCALE,0,OFFSET[0]],[0,SCALE,OFFSET[1]],[0,0,1]])


def pose(**channels):
    return channels


CLIPS = [
    dict(id="idle",name="探索待机",category="基础动作",frames=42,loop=True,marks=[(0,"落肩静立"),(12,"吸气"),(27,"辫梢回摆")],
         keys=[
             (0,pose(torso=(-4,5,-3),head=(0,0,-2),hair_braid=(0,0,3),arm_near=(0,6,7),arm_far=(0,5,-6))),
             (12,pose(torso=(-8,-7,-3),head=(1,-3,-1),hair_braid=(1,-2,-1),arm_near=(1,2,5),arm_far=(0,2,-4))),
             (27,pose(torso=(-1,8,-2),head=(0,1,1),hair_braid=(-2,1,6),arm_near=(0,7,8),arm_far=(0,6,-7))),
             (42,pose(torso=(-4,5,-3),head=(0,0,-2),hair_braid=(0,0,3),arm_near=(0,6,7),arm_far=(0,5,-6))),
         ]),
    dict(id="walk",name="潜行步",category="基础动作",frames=24,loop=True,marks=[(0,"远脚落地"),(6,"低身过步"),(12,"近脚落地"),(18,"换脚")],
         events=[(0,"step_far"),(12,"step_near")],
         keys=[
             (0,pose(hips_legs=(0,6,0),torso=(11,6,7),head=(4,-2,-3),hair_braid=(0,0,-4),leg_near=(0,3,10),leg_far=(4,1,-8),arm_near=(0,-3,9),arm_far=(0,6,-9))),
             (6,pose(hips_legs=(0,-14,0),torso=(11,4,8),head=(4,1,-4),hair_braid=(0,-1,3),leg_near=(5,-27,-13),leg_far=(-4,8,4),arm_near=(0,0,0),arm_far=(1,2,0))),
             (12,pose(hips_legs=(0,5,0),torso=(10,4,6),head=(3,0,-1),hair_braid=(0,1,8),leg_near=(3,-1,-24),leg_far=(-4,-3,19),arm_near=(0,0,-9),arm_far=(0,3,8))),
             (18,pose(hips_legs=(0,-13,0),torso=(9,5,7),head=(3,-1,-2),hair_braid=(0,1,2),leg_near=(-3,8,-5),leg_far=(7,-30,1),arm_near=(0,4,0),arm_far=(0,1,1))),
             (24,pose(hips_legs=(0,6,0),torso=(11,6,7),head=(4,-2,-3),hair_braid=(0,0,-4),leg_near=(0,3,10),leg_far=(4,1,-8),arm_near=(0,-3,9),arm_far=(0,6,-9))),
         ]),
    dict(id="combat",name="战斗待机",category="基础动作",frames=36,loop=True,marks=[(0,"双刃戒备"),(10,"提腕"),(23,"沉身")],
         keys=[
             (0,pose()),
             (10,pose(torso=(6,-11,2),head=(2,-3,-2),hair_braid=(0,-1,-5),arm_near=(1,-2,-5),arm_far=(0,-5,5),hand_dagger_far=(0,0,-9))),
             (23,pose(torso=(4,7,4),head=(1,5,3),hair_braid=(-1,0,7),arm_near=(2,-1,2),arm_far=(0,2,-5),hand_dagger_near=(0,0,-6))),
             (36,pose()),
         ]),
    dict(id="defend",name="双刃招架",category="基础动作",frames=19,loop=False,marks=[(0,"察觉"),(5,"抬刃招架"),(9,"稳住"),(15,"收刃")],
         keys=[
             (0,pose()),
             (5,pose(torso=(-18,18,-6),head=(-2,18,7),hair_braid=(-2,2,13),arm_near=(6,-6,50),arm_far=(-6,-8,-63),hand_dagger_near=(1,-1,24),hand_dagger_far=(0,0,-39))),
             (9,pose(torso=(-18,22,-5),head=(-1,15,4),hair_braid=(0,0,4),arm_near=(4,-3,42),arm_far=(-4,-6,-57),hand_dagger_near=(0,0,22),hand_dagger_far=(0,0,-26))),
             (18,pose()),
         ]),
    dict(id="hit",name="受击后撤",category="基础动作",frames=14,loop=False,marks=[(0,"原位"),(2,"受击"),(5,"后撤"),(12,"站稳")],
         events=[(2,"hurt")],fx=True,
         keys=[
             (0,pose()),
             (2,pose(hips_legs=(-16,0,0),torso=(-74,-15,-13),head=(-15,-8,-12),hair_braid=(0,0,31),arm_near=(-5,4,23),arm_far=(5,-5,14),hand_dagger_near=(0,0,-15))),
             (5,pose(hips_legs=(-11,0,0),torso=(-48,5,-7),head=(-11,0,-8),hair_braid=(0,0,15),arm_near=(-1,7,11),arm_far=(4,5,9))),
             (9,pose(torso=(10,7,4),head=(2,7,6),hair_braid=(0,0,-10))),
             (13,pose()),
         ]),
    dict(id="dead",name="阵亡倒地",category="基础动作",frames=29,loop=False,marks=[(0,"踉跄"),(6,"失去支撑"),(10,"落地"),(22,"倒地保持")],
         events=[(10,"ground")],replacement=(10,29),fx=True,
         keys=[
             (0,pose()),
             (3,pose(torso=(-25,23,-13),head=(5,14,21),hair_braid=(0,0,15),arm_near=(0,10,7),arm_far=(0,4,-17))),
             (7,pose(hips_legs=(-5,13,16),torso=(12,28,10),head=(6,22,15),hair_braid=(0,0,-18),arm_near=(0,5,22),arm_far=(0,4,-30))),
             (9,pose(hips_legs=(6,18,25),torso=(10,46,15),head=(7,29,21),hair_braid=(0,0,-29),arm_near=(1,0,27),arm_far=(0,1,-24))),
         ]),
    dict(id="dusk_lunge",name="暮影突刺",category="伤害技能",frames=23,loop=False,
         marks=[(0,"低身蓄势"),(5,"残影突进"),(7,"刺击命中"),(12,"拔刃"),(20,"回架")],
         events=[(7,"impact")],replacement=(6,13),fx=True,
         keys=[
             (0,pose()),
             (4,pose(torso=(-25,25,-8),head=(-8,9,4),hair_braid=(0,0,16),arm_near=(0,-3,25),arm_far=(0,-8,-24),hand_dagger_far=(0,0,-18))),
             (5,pose(hips_legs=(25,-2,0),torso=(42,22,15),head=(11,10,-3),hair_braid=(0,0,-8),arm_near=(0,-1,-8),arm_far=(2,-2,-36))),
             (13,pose(hips_legs=(109,0,0),torso=(31,7,11),head=(8,4,-4),hair_braid=(0,0,-19),arm_near=(4,3,2),arm_far=(0,1,-21))),
             (19,pose(hips_legs=(8,0,0),torso=(8,7,3),hair_braid=(0,0,7))),
             (22,pose()),
         ]),
    dict(id="crescent_cut",name="回月双切",category="伤害技能",frames=28,loop=False,
         marks=[(0,"收腕转肩"),(7,"贴地转身"),(10,"第一刃命中"),(14,"回手命中"),(22,"抽身回架")],
         events=[(10,"impact"),(14,"impact")],replacement=(9,18),fx=True,
         keys=[
             (0,pose()),
             (5,pose(torso=(-22,31,-9),head=(5,9,7),hair_braid=(0,0,17),arm_near=(0,0,42),arm_far=(0,-10,-42),hand_dagger_near=(0,0,28))),
             (8,pose(hips_legs=(20,10,0),torso=(26,35,12),head=(6,10,9),hair_braid=(0,0,-13),arm_near=(0,0,18),arm_far=(0,0,-48))),
             (18,pose(hips_legs=(63,4,0),torso=(34,35,12),head=(8,5,5),hair_braid=(0,0,-14),arm_near=(0,3,18),arm_far=(0,-2,-23))),
             (23,pose(hips_legs=(9,0,0),torso=(9,12,4),hair_braid=(0,0,8))),
             (27,pose()),
         ]),
]


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


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


SPECIAL = {
    "dusk_lunge": pose_art("dusk_lunge",(274,222),252,333),
    "crescent_cut": pose_art("crescent_cut",(278,226),249,333),
    "dead": pose_art("dead",(272,110),215,335),
}

IMPACTS = {
    ("dusk_lunge",7):(367,199),
    ("crescent_cut",10):(358,210),
    ("crescent_cut",14):(368,229),
}


def sparkle(draw, xy, amount, accent):
    x,y=xy
    draw.polygon([(x-22,y-2),(x-4,y-4),(x+1,y-18),(x+4,y-5),(x+22,y-8),
                  (x+9,y+2),(x+6,y+14),(x,y+7),(x-13,y+9),(x-7,y+3)],fill=(*accent,alpha(amount)))


def effect(name, frame, body):
    canvas=Image.new("RGBA",SIZE)
    if name=="dusk_lunge" and 5<=frame<=10:
        echo=Image.new("RGBA",SIZE,(80,66,125,0))
        echo.putalpha(body.getchannel("A").point(lambda v:round(v*.24*(1-(frame-5)/7))))
        canvas.alpha_composite(echo,(-36-(frame-5)*2,1))
    draw=ImageDraw.Draw(canvas)
    if name=="dusk_lunge":
        if 6<=frame<=12:
            fade=1-(frame-6)/7
            slash(draw,(279,214,401,198,-4),fade,(144,184,220))
        if 7<=frame<=9:
            sparkle(draw,IMPACTS[name,7],1-.28*(frame-7),(220,236,248))
    elif name=="crescent_cut":
        if 9<=frame<=15:
            slash(draw,(257,261,387,157,-24),1-(frame-9)/7,(150,111,192))
        if 13<=frame<=20:
            slash(draw,(254,181,402,248,22),1-(frame-13)/8,(185,140,213))
        for impact in (10,14):
            if impact<=frame<=impact+2:
                sparkle(draw,IMPACTS[name,impact],.91-.24*(frame-impact),(226,192,244))
    elif name=="dead":
        dust(draw,frame,10,(227,333),False)
    elif name=="hit" and 2<=frame<=7:
        slash(draw,(221,244,270,199,5),.94-(frame-2)/6,(190,87,87))
    return canvas


def build_atlas(paths, bodies, effects):
    count=len(bodies)
    columns=min(count,8)
    dims=columns*SIZE[0], math.ceil(count/columns)*SIZE[1]
    sheets=[Image.new("RGBA",dims) for _ in paths]
    frames=[]
    previews=[]
    for index,(body,fx) in enumerate(zip(bodies,effects)):
        x,y=(index%columns)*SIZE[0],(index//columns)*SIZE[1]
        frames.append([x,y,*SIZE])
        sheets[0].paste(body,(x,y))
        if len(sheets)==2:
            sheets[1].paste(fx,(x,y))
        preview=body.copy()
        preview.alpha_composite(fx)
        previews.append(preview)
    for sheet,path in zip(sheets,paths):
        sheet.save(ROOT/path,optimize=True)
    return frames,dims,previews


def render_clip(clip):
    name=clip["id"]
    count=clip["frames"]
    prefix="actions/"+name
    body_path=prefix+"-atlas.png"
    fx_path=prefix+"-fx.png" if clip.get("fx") else None
    lo,hi=clip.get("replacement",(0,0))
    bodies,effects,points=[],[],[]
    for frame in range(count):
        if lo<=frame<hi:
            body=Image.new("RGBA",SIZE)
            art,(x,y)=SPECIAL[name]
            e=frame-lo
            if name=="dusk_lunge":
                x+=min(e,2)*9-max(0,e-3)*2
            elif name=="crescent_cut":
                x+=min(e,5)*3-max(0,e-5)*3
                y+=round(math.sin(e*.7)*2)
            elif name=="dead":
                x+=min(e,3)*2
            body.alpha_composite(art,(x,y))
            joints=None
        else:
            body,joints=raster_pose(ORDER,clip["keys"],frame)
        bodies.append(body)
        effects.append(effect(name,frame,body))
        points.append(joints)
    keys,size,preview=build_atlas([body_path]+([fx_path] if fx_path else []),bodies,effects)
    timing=[round((i+1)*1000/FPS)-round(i*1000/FPS) for i in range(count)]
    webp=prefix+".webp"
    preview[0].save(ROOT/webp,save_all=True,append_images=preview[1:],duration=timing,loop=0 if clip["loop"] else 1,quality=87,method=3)
    thumb=prefix+"-thumb.png"
    preview[clip["marks"][2][0]].save(ROOT/thumb)
    events=[]
    for frame,label in clip.get("events",[]):
        event={"frame":frame,"time":round(frame/FPS,4),"event":label}
        if label=="impact":
            event["position_in_frame"]=IMPACTS[name,frame]
            event["hit_index"]=1+sum(item["event"]=="impact" for item in events)
        events.append(event)
    atlas={"animation":name,"texture":body_path,"fps":FPS,"loop":clip["loop"],"anchor_in_frame":ANCHOR,
           "frames_xywh":keys,"image_size":size,"events":events,"joint_positions":points}
    if fx_path:
        atlas["fx_texture"]=fx_path
    atlas_path=prefix+"-atlas.json"
    write_json(ROOT/atlas_path,atlas)
    motion={key:clip[key] for key in ("name","id","frames","loop","keys")}
    motion.update({"binding":"rig-binding.json","fps":FPS,"interpolation":"smoothstep between keyed poses",
                   "coordinate_system":"source pixels, clockwise degrees, local x/y/angle per channel"})
    if hi:
        motion["replacement_frames"]={"from_inclusive":lo,"to_exclusive":hi,"path":f"poses/{name}.png"}
    motion_path=prefix+"-motion.json"
    write_json(ROOT/motion_path,motion)
    print(name,count,flush=True)
    return {"id":name,"name":clip["name"],"category":clip["category"],"atlas":atlas,
            "atlasPath":atlas_path,"motionPath":motion_path,"webp":webp,"thumbnail":thumb,"marks":clip["marks"]},preview


def save_demo(dusk,crescent):
    count=39
    background=Image.new("RGB",(744,388),"#24222a")
    d=ImageDraw.Draw(background)
    title=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",20)
    detail=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",13)
    for i,(name,desc) in enumerate([("暮影突刺","残影突进 · 单次命中"),("回月双切","贴地旋身 · 两次命中")]):
        x=12+368*i
        d.rounded_rectangle((x,13,x+352,373),8,fill="#322d38")
        d.text((x+15,24),name,font=title,fill="#eedee9")
        d.text((x+15,346),desc,font=detail,fill="#bbadc7")
    frames=[]
    for i in range(count):
        panel=background.copy()
        for j,sequence in enumerate((dusk,crescent)):
            image=sequence[min(i,len(sequence)-1)].resize((335,285),Image.Resampling.LANCZOS)
            panel.paste(image,(20+368*j,57),image)
        frames.append(panel)
    sample=Image.new("RGB",(744*4,388))
    for i,frame in enumerate((0,7,10,14)):
        sample.paste(frames[frame],(744*i,0))
    palette=sample.quantize(colors=190)
    gif=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    timing=[round((i+1)*100/FPS)*10-round(i*100/FPS)*10 for i in range(count)]
    gif[0].save(ROOT/"skills-preview.gif",save_all=True,append_images=gif[1:],duration=timing,loop=0,disposal=1,optimize=True)


rendered=[render_clip(clip) for clip in CLIPS]
clips=[clip for clip,_ in rendered]
write_json(ROOT/"actions-index.json",[{key:v for key,v in clip.items() if key!="atlas"} for clip in clips])
viewer={"clips":clips,"parts":PARTS,"partOrder":ORDER,"partNames":{n:p["label"] for n,p in PARTS.items()}}
(ROOT/"viewer-data.js").write_text("window.CHARACTER_VIEWER_DATA = "+json.dumps(viewer,ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
save_demo(rendered[-2][1],rendered[-1][1])
