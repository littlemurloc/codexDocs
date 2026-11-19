
"""Rebuild the two characters' revised basic actions from transparent source art."""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
SHOTS = HERE.parent
SIZE = (460, 392)
ANCHOR = (210,333)
FPS = 24
BASIC = ("idle","walk","combat","defend","hit","dead")


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def offset(x,y):
    return np.array([[1.,0,x],[0,1.,y],[0,0,1.]])


def rotation(degrees):
    cr,sr=math.cos(math.radians(degrees)),math.sin(math.radians(degrees))
    return np.array([[cr,-sr,0],[sr,cr,0],[0,0,1.]]) 


def scale(x,y):
    return np.diag([x,y,1.])


def xy(matrix, point):
    return (matrix @ (*point,1))[:2]


def move_about(pivot, dx=0,dy=0,angle=0):
    x,y=pivot
    return offset(x+dx,y+dy) @ rotation(angle) @ offset(-x,-y)


def raster_layer(dest, art, matrix):
    inverse=np.linalg.inv(matrix)
    layer=art.transform(dest.size,Image.Transform.AFFINE,tuple(inverse[:2].flatten()),Image.Resampling.BICUBIC)
    dest.alpha_composite(layer)


def opaque_box(image, threshold=30):
    return image.getchannel("A").point(lambda n:255 if n>=threshold else 0).getbbox()


def save_crop(root, path, image, pivot, parent, title):
    bounds=opaque_box(image,5)
    if not bounds:
        raise ValueError(f"Empty art: {path}")
    cropped=image.crop(bounds)
    cropped.save(root/path)
    return dict(parent=parent,pivot=[int(n) for n in pivot],position=list(bounds[:2]),size=list(cropped.size),path=path,label=title)


def smooth(x):
    x=min(1,max(0,x))
    return x*x*(3-2*x)


def sample(keys, frame):
    for (a, first),(b,last) in zip(keys,keys[1:]):
        if frame<=b:
            blend=smooth((frame-a)/(b-a))
            names=set(first)|set(last)
            return {name:tuple(x+(y-x)*blend for x,y in zip(first.get(name,(0,0,0)),last.get(name,(0,0,0)))) for name in names}
    return keys[-1][1] if keys else {}


def segment_matrix(start, finish, new_start, new_finish):
    origin=np.array(start)
    a=np.array(finish)-origin
    target=np.array(new_finish)-new_start
    zoom=float(np.linalg.norm(target)/np.linalg.norm(a))
    turn=math.degrees(math.atan2(target[1],target[0])-math.atan2(a[1],a[0]))
    return offset(*new_start) @ rotation(turn) @ scale(zoom,zoom) @ offset(*(-origin))


def chain_knee(hip, ankle, rest):
    a,b,c=map(np.array,rest)
    first,second=np.linalg.norm(b-a),np.linalg.norm(c-b)
    reach=np.linalg.norm(ankle-hip)
    stretch=max(1.,reach/(first+second-.15))
    first*=stretch
    second*=stretch
    direction=(ankle-hip)/reach
    parallel=(first**2-second**2+reach**2)/(2*reach)
    normal_sq=max(0,first**2-parallel**2)
    sign=np.sign((c[0]-a[0])*(b[1]-a[1])-(c[1]-a[1])*(b[0]-a[0]))
    if not sign:
        sign=-1
    knee=hip+parallel*direction+sign*math.sqrt(normal_sq)*np.array([-direction[1],direction[0]])
    return knee,float(stretch)


class Rig:
    def __init__(self,root,parts):
        self.parts=parts
        self.images={k:Image.open(root/v["path"]).convert("RGBA") for k,v in parts.items()}

    def part(self, canvas, key, matrix):
        raster_layer(canvas,self.images[key],matrix@offset(*self.parts[key]["position"]))

    def combat(self, order, stage, channels):
        cache={}
        canvas=Image.new("RGBA",SIZE)
        points={}
        def locate(name):
            if name not in cache:
                item=self.parts[name]
                parent=item["parent"]
                matrix=move_about(item["pivot"],*channels.get(name,(0,0,0)))
                cache[name]=(locate(parent) if parent else stage)@matrix
            return cache[name]
        for name in order:
            self.part(canvas,name,locate(name))
            points[name]=rounded(xy(cache[name],self.parts[name]["pivot"]))
        return canvas,points


def rounded(point):
    return [round(float(n),2) for n in point]


def poly_mask(shape,points):
    layer=Image.new("L",shape)
    ImageDraw.Draw(layer).polygon(points,fill=255)
    return layer


def visible(source, mask):
    body=source.copy()
    body.putalpha(ImageChops.multiply(body.getchannel("A"),mask))
    return body


class Travel:
    def __init__(self,root,configuration):
        self.root=root
        self.config=configuration
        self.source=Image.open(root/"motion-v2/travel.png").convert("RGBA")
        self.parts={}
        self.build_parts()
        self.rig=Rig(root,self.parts)
        bbox=opaque_box(self.source)
        self.ground=configuration["ground"]
        width=configuration["body_x"]
        self.zoom=configuration["draw_height"]/(self.ground-bbox[1])
        ox,oy=ANCHOR[0]-width*self.zoom,ANCHOR[1]-self.ground*self.zoom
        self.stage=offset(ox,oy)@scale(self.zoom,self.zoom)
        self.vitals=[]

    def put(self,key,mask,pivot,parent,label):
        path="motion-v2/parts/"+key+".png"
        self.parts[key]=save_crop(self.root,path,visible(self.source,mask),pivot,parent,label)

    def build_parts(self):
        shape=self.source.size
        y,x=np.mgrid[:shape[1],:shape[0]]
        removed=Image.new("L",shape)
        assigned=Image.new("L",shape)
        for side,leg in self.config["legs"].items():
            area=ImageChops.subtract(poly_mask(shape,leg["polygon"]),assigned)
            assigned=ImageChops.lighter(assigned,area)
            extended=area.filter(ImageFilter.MaxFilter(19))
            h,k,a=map(np.array,leg["joints"])
            n1=(k-h)/np.linalg.norm(k-h)
            n2=(a-k)/np.linalg.norm(a-k)
            normal=n1+n2
            normal/=np.linalg.norm(normal)
            knee=(x-k[0])*normal[0]+(y-k[1])*normal[1]
            ankle=(x-a[0])*n2[0]+(y-a[1])*n2[1]
            key="travel_"+side
            for suffix,selection,pivot,parent,label in [
                ("thigh",knee<=25,h,"travel_body","大腿"),
                ("shin",(knee>=-24)&(ankle<=24),k,key+"_thigh","小腿"),
                ("boot",ankle>=-22,a,key+"_shin","靴"),
            ]:
                band=Image.fromarray(selection.astype("uint8")*255)
                self.put(key+"_"+suffix,ImageChops.multiply(extended,band),pivot,parent,("探索近侧" if side=="near" else "探索远侧")+label)
            removed=ImageChops.lighter(removed,area.filter(ImageFilter.MinFilter(19)))
        if self.config.get("extra"):
            for key,extra in self.config["extra"].items():
                area=poly_mask(shape,extra["polygon"])
                self.put(key,area.filter(ImageFilter.MaxFilter(9)),extra["pivot"],"travel_body",extra["label"])
                removed=ImageChops.lighter(removed,area.filter(ImageFilter.MinFilter(13)))
        self.put("travel_body",ImageChops.invert(removed),self.config["hip"],None,"探索姿势 · 躯干")

    def leg(self,side,upper,phase,walk):
        leg=self.config["legs"][side]
        h,k,a=map(np.array,leg["joints"])
        heel,toe=map(np.array,leg["sole"])
        support=self.config["support"]
        stride=self.config["stride"]
        if not walk:
            shift,lift,angle,planted=0,0,0,True
        elif phase<support:
            q=phase/support
            shift=stride*(.5-q)
            lift=0
            angle=-9*(1-smooth(q/.18))+13*smooth((q-.70)/.30)
            planted=True
        else:
            q=(phase-support)/(1-support)
            shift=stride*(smooth(q)-.5)
            lift=self.config["lift"]*math.sin(math.pi*q)**1.25
            angle=13-22*smooth(q)
            planted=False
        point=toe if angle>0 else heel
        sole_angle=math.degrees(math.atan2(*(toe-heel)[::-1]))
        boot=offset(point[0]+shift,self.ground-lift)@rotation(angle-sole_angle)@offset(-point[0],-point[1])
        foot=xy(boot,a)
        hip=xy(upper,h)
        knee,stretch=chain_knee(hip,foot,(h,k,a))
        return hip,knee,foot,boot,rounded(xy(boot,point)),planted,stretch

    def frame(self,time,walk):
        phase=time%1
        tau=math.tau*phase
        if walk:
            # Two weight transfers per stride; the torso reaches its low point on contact.
            bob=self.config["walk_drop"]+self.config["bob"]*math.cos(tau*2)
            tx=self.config["sway"]*math.sin(tau)
            angle=self.config["lean"]+self.config["twist"]*math.sin(tau-.24)
        else:
            bob=self.config["idle_drop"]+self.config["idle_bob"]*(math.cos(tau)-1)/2
            tx=0
            angle=.75*math.sin(tau)
        upper=move_about(self.config["hip"],tx,bob,angle)
        canvas=Image.new("RGBA",SIZE)
        points={"travel_body":rounded(xy(self.stage@upper,self.config["hip"]))}
        supports={}
        arms=self.config.get("extra",{})
        for side in ("far","near"):
            p=(phase+(.5 if side=="far" else 0))%1
            hip,knee,foot,boot,contact,planted,stretch=self.leg(side,upper,p,walk)
            base=self.config["legs"][side]["joints"]
            key="travel_"+side
            self.rig.part(canvas,key+"_thigh",self.stage@segment_matrix(base[0],base[1],hip,knee))
            self.rig.part(canvas,key+"_shin",self.stage@segment_matrix(base[1],base[2],knee,foot))
            self.rig.part(canvas,key+"_boot",self.stage@boot)
            points.update({key+"_"+suffix:rounded(xy(self.stage,point))
                           for suffix,point in (("thigh",hip),("shin",knee),("boot",foot))})
            supports[side]={"planted":planted,"contact":rounded(xy(self.stage,contact)),"link_stretch":round(stretch,4)}
        self.rig.part(canvas,"travel_body",self.stage@upper)
        for name,definition in arms.items():
            lag=definition["wave"]
            swing=(definition["walk_swing"] if walk else definition["idle_swing"])*math.sin(tau+lag)
            matrix=self.stage@upper@move_about(definition["pivot"],0,0,swing)
            self.rig.part(canvas,name,matrix)
            points[name]=rounded(xy(matrix,definition["pivot"]))
        if walk:
            self.vitals.append(supports)
        return canvas,points


def painted_pose(image,max_width,max_height,center,floor):
    view=image.crop(opaque_box(image))
    view.thumbnail((max_width,max_height),Image.Resampling.LANCZOS)
    return view, (round(center-view.width/2),floor-view.height)


def draw_paint(pose,dx=0,dy=0,squash=1):
    image,(x,y)=pose
    if squash!=1:
        h=round(image.height*squash)
        y+=image.height-h
        image=image.resize((image.width,h),Image.Resampling.BICUBIC)
    result=Image.new("RGBA",SIZE)
    result.alpha_composite(image,(x+round(dx),y+round(dy)))
    return result


def spot_effect(name,frame,impact,heavy):
    art=Image.new("RGBA",SIZE)
    d=ImageDraw.Draw(art)
    elapsed=frame-impact
    if elapsed<0:
        return art
    x,y=ANCHOR
    if name=="hit" and elapsed<6:
        a=round(239*(1-elapsed/6))
        x+=29 if heavy else 15
        y-=117 if heavy else 123
        d.polygon([(x-11,y+12),(x-5,y),(x+25,y-17),(x+9,y),(x+16,y+2),(x-4,y+6)],fill=(220,120,79,a))
        d.polygon([(x-3,y+3),(x+4,y-3),(x+15,y-10),(x+7,y-1)],fill=(242,203,149,a))
    if name=="dead" and elapsed<13:
        t=elapsed/13
        for i in range(18 if heavy else 11):
            vx=((i*37)%81-39)
            px=x+23+vx*(.34+t*1.5)
            py=y-1-(5+(i%4)*7)*math.sin(t*math.pi)
            r=(2+i%3)*(1-t*.65)
            col=(159,119,81) if heavy else (142,120,141)
            d.polygon([(px-r,py),(px,py-r),(px+r,py),(px,py+r)],fill=(*col,round(190*(1-t))))
    return art


def floor_clamp(body,limit):
    box=opaque_box(body)
    if not box or box[3]<=limit:
        return body
    shifted=Image.new("RGBA",SIZE)
    shifted.alpha_composite(body,(0,limit-box[3]))
    return shifted


def load_catalog(root):
    snap=root/"motion-v2"/"viewer-v1.json"
    if snap.exists():
        return json.loads(snap.read_text(encoding="utf-8"))
    source=(root/"viewer-data.js").read_text(encoding="utf-8-sig")
    data=json.loads(re.sub(r"^window\.\w+\s*=\s*","",source.strip()).rstrip(";"))
    dump(snap,data)
    return data


def keyset(heavy,hand_n,hand_f):
    if heavy:
        combat=[
            (0,dict(torso=(-5,9,-2),head=(0,4,2),arm_near=(0,1,5),arm_far=(0,-3,-7))),
            (8,dict(torso=(-8,-8,-3),head=(0,0,1),arm_near=(0,1,6),arm_far=(0,-3,-6))),
            (16,dict(torso=(-4,-14,-1),head=(1,1,-2),arm_near=(0,-1,8),arm_far=(0,-4,-10),**{hand_n:(0,0,4),hand_f:(0,0,-4)})),
            (25,dict(torso=(3,16,2),head=(1,7,1),arm_near=(0,3,3),arm_far=(0,-4,-9))),
            (37,dict(torso=(-5,9,-2),head=(0,4,2),arm_near=(0,1,5),arm_far=(0,-3,-7))),
        ]
        brace=dict(torso=(-12,26,-4),head=(-4,14,4),arm_near=(3,-4,13),arm_far=(0,-5,-18))
        recoil=dict(torso=(-37,14,-9),head=(-12,6,-13),arm_near=(0,9,9),arm_far=(0,9,7))
    else:
        combat=[
            (0,dict(torso=(5,18,5),head=(1,-2,-4),hair_braid=(0,0,-3),arm_near=(2,-4,2),arm_far=(1,-6,-7),**{hand_n:(0,0,9),hand_f:(0,0,-14)})),
            (6,dict(torso=(8,12,5),head=(3,-7,-6),hair_braid=(1,0,2),arm_near=(0,-3,3),arm_far=(0,-5,-11),**{hand_n:(0,0,12),hand_f:(0,0,-19)})),
            (14,dict(torso=(3,7,4),head=(4,-3,-1),hair_braid=(2,1,7),arm_near=(1,-3,4),arm_far=(0,-3,-9),**{hand_n:(0,0,9),hand_f:(0,0,-15)})),
            (23,dict(torso=(10,23,6),head=(1,-1,-4),hair_braid=(0,0,-9),arm_near=(1,-5,2),arm_far=(0,-8,-7),**{hand_n:(0,0,8),hand_f:(0,0,-13)})),
            (30,dict(torso=(5,18,5),head=(1,-2,-4),hair_braid=(0,0,-3),arm_near=(2,-4,2),arm_far=(1,-6,-7),**{hand_n:(0,0,9),hand_f:(0,0,-14)})),
        ]
        brace=dict(torso=(-18,21,-8),head=(-2,13,1),hair_braid=(0,0,12),arm_near=(4,-6,8),arm_far=(-5,-6,-22))
        recoil=dict(hips_legs=(-25,0,0),torso=(-52,8,-10),head=(-8,14,8),hair_braid=(0,0,18),arm_near=(0,4,5),arm_far=(0,5,2))
    return combat,brace,recoil


def allocate_chart(clip,body,fx,joints,root):
    length=len(body)
    columns=min(8,length)
    dims=columns*SIZE[0],math.ceil(length/columns)*SIZE[1]
    sheet=Image.new("RGBA",dims)
    has_fx=any(img.getchannel("A").getbbox() for img in fx)
    effects=Image.new("RGBA",dims) if has_fx else None
    rects=[]
    preview=[]
    for i,(b,f) in enumerate(zip(body,fx)):
        x,y=i%columns*SIZE[0],i//columns*SIZE[1]
        rects.append([x,y,*SIZE])
        sheet.paste(b,(x,y))
        if effects:
            effects.paste(f,(x,y))
        image=b.copy();image.alpha_composite(f);preview.append(image)
    base="motion-v2/"+clip["id"]
    sheet.save(root/(base+"-atlas.png"),optimize=True)
    data={key:clip[key] for key in ("id","loop","events")}
    data.update(texture=base+"-atlas.png",fps=FPS,frames_xywh=rects,image_size=dims,
                anchor_in_frame=ANCHOR,joint_positions=joints,animation=clip["id"])
    if effects:
        data["fx_texture"]=base+"-fx.png"
        effects.save(root/data["fx_texture"],optimize=True)
    if clip.get("locomotion"):
        data["locomotion"]=clip["locomotion"]
    metadata=base+"-atlas.json";dump(root/metadata,data)
    webp=base+".webp"
    timing=[round((i+1)*1000/FPS)-round(i*1000/FPS) for i in range(length)]
    preview[0].save(root/webp,save_all=True,append_images=preview[1:],duration=timing,loop=0 if clip["loop"] else 1,quality=87,method=3)
    thumb=base+"-thumb.png"
    preview[clip["marks"][1][0]].save(root/thumb)
    return dict(id=clip["id"],name=clip["name"],category="基础动作",atlas=data,atlasPath=metadata,
                webp=webp,motionPath=base+"-motion.json",thumbnail=thumb,marks=clip["marks"]),preview


def process(role,config):
    root=SHOTS/config["folder"]
    heavy=role=="orc"
    old=load_catalog(root)
    old_clips={clip["id"]:clip for clip in old["clips"]}
    all_parts=old["parts"].copy()
    order=old["partOrder"]
    combat_parts=[name for name in order if name not in ("leg_far","leg_near","walk_hips")] if heavy else order
    rig=Rig(root,{name:all_parts[name] for name in combat_parts})
    base_stage=offset(81.67,86.385)@scale(.205,.205) if heavy else offset(210-.191*602,333-.191*1231)@scale(.191,.191)
    travel=Travel(root,config["travel"])
    names={n:v["label"] for n,v in travel.parts.items()}
    all_parts.update(travel.parts)
    name_n="hand_axe_near" if heavy else "hand_dagger_near"
    name_f="hand_axe_far" if heavy else "hand_dagger_far"
    combat,brace,recoil=keyset(heavy,name_n,name_f)
    reaction=Image.open(root/"motion-v2/reactions.png").convert("RGBA")
    split=config["pose_split"]
    seam=int(split*reaction.width)
    guard=painted_pose(reaction.crop((0,0,seam,reaction.height)),286,228 if heavy else 222,205 if heavy else 195,334)
    hurt=painted_pose(reaction.crop((seam,0,reaction.width,reaction.height)),286,232 if heavy else 218,203 if heavy else 198,334)
    dead=painted_pose(Image.open(root/"poses/dead.png").convert("RGBA"),283,116,228 if heavy else 225,335)
    for name,art in [("guard",guard[0]),("hurt",hurt[0])]:
        art.save(root/"motion-v2"/(name+"-pose.png"))

    nwalk=config["walk_frames"]
    defend_hold=(4,15) if heavy else (2,8)
    hurt_hold=(2,8) if heavy else (2,5)
    fall=13 if heavy else 10
    loop_specs=[
        ("idle","探索待机",38 if heavy else 29,True,[(0,"武器收低"),(11,"呼吸"),(24 if heavy else 21,"回稳")],[]),
        ("walk","沉步行走" if heavy else "潜行步",nwalk,True,[(0,"近脚着地"),(nwalk//4,"重心过脚"),(nwalk//2,"远脚着地"),(3*nwalk//4,"摆腿前送")],[(0,"step_near"),(nwalk//2,"step_far")]),
        ("combat","战斗待机",combat[-1][0],True,[(0,"备战"),(combat[1][0],"吸气"),(combat[3][0],"压重心" if heavy else "视线先回")],[]),
        ("defend","合斧架防" if heavy else "撤步招架",25 if heavy else 16,False,[(0,"察觉"),(defend_hold[0],"合斧护胸" if heavy else "撤身抬刃"),(defend_hold[1],"卸力")],[]),
        ("hit","受击沉肩" if heavy else "受击后撤",20 if heavy else 13,False,[(0,"原位"),(2,"受击"),(hurt_hold[1],"回稳")],[(2,"hurt")]),
        ("dead","阵亡倒地",35 if heavy else 29,False,[(0,"受创"),(fall-4,"失衡下坠"),(fall,"接地"),(fall+9,"停住")],[(fall,"ground")]),
    ]
    card={}
    produced={}
    for id,name,count,loop,marks,events in loop_specs:
        clip=dict(id=id,name=name,loop=loop,marks=marks,events=[dict(frame=f,time=round(f/FPS,4),event=e) for f,e in events])
        body=[];fx=[];joints=[]
        for frame in range(count):
            row=Image.new("RGBA",SIZE)
            if id in ("idle","walk"):
                raster,bones=travel.frame(frame/count,id=="walk")
            elif id=="combat":
                raster,bones=rig.combat(combat_parts,base_stage,sample(combat,frame))
            elif id=="defend":
                lo,hi=defend_hold
                if lo<=frame<hi:
                    f=frame-lo
                    raster=draw_paint(guard,(-1 if heavy else -10)*smooth(f/3),0,1-(.017 if heavy else .007)*math.sin(f*.57)**2)
                    bones=None
                else:
                    track=[(0,{}),(lo-1,brace),(hi,brace),(count-1,{})]
                    raster,bones=rig.combat(combat_parts,base_stage,sample(track,frame))
            elif id=="hit":
                lo,hi=hurt_hold
                if lo<=frame<hi:
                    f=frame-lo
                    raster=draw_paint(hurt,(-4 if heavy else -15)*smooth(f/max(1,hi-lo-1)),0,
                                      1-(.03 if heavy else .01)*smooth(f/max(1,hi-lo-1)))
                    bones=None
                else:
                    track=[(0,{}),(1,recoil),(hi,recoil),(count-1,{})]
                    raster,bones=rig.combat(combat_parts,base_stage,sample(track,frame))
                row=spot_effect(id,frame,lo,heavy)
            else:
                if frame>=fall:
                    q=smooth((frame-fall)/(7 if heavy else 5))
                    raster=draw_paint(dead,(11 if heavy else 19)*q,0,1-(.07 if heavy else .045)*(1-q))
                    bones=None
                else:
                    q=smooth(max(0,(frame-2)/(fall-3)))
                    turn=(63 if heavy else 68)*q
                    drop=(35 if heavy else 25)*q
                    sway=(23 if heavy else 14)*q
                    transform=move_about((213,247),sway,drop,turn)
                    channels=sample([(0,{}),(3,recoil),(fall-1,brace)],frame)
                    raster,bones=rig.combat(combat_parts,transform@base_stage,channels)
                    old_box=opaque_box(raster)
                    raster=floor_clamp(raster,335)
                    push=0 if not old_box else max(0,old_box[3]-335)
                    if push:
                        bones={key:[y[0],round(y[1]-push,2)] for key,y in bones.items()}
                row=spot_effect(id,frame,fall,heavy)
            body.append(raster);joints.append(bones);fx.append(row)
        if id=="walk":
            clip["locomotion"]={"stance_fraction":config["travel"]["support"],"travel_pixels_per_cycle":round(config["travel"]["stride"]*travel.zoom/config["travel"]["support"],2),"contacts_by_frame":travel.vitals}
        asset,preview=allocate_chart(clip,body,fx,joints,root)
        dump(root/asset["motionPath"],dict(clip,drawing="travel segmented" if id in ("idle","walk") else "combat rig with painted poses",
            combat_keyframes=combat if id=="combat" else [], guard_range=defend_hold if id=="defend" else None,
            hurt_range=hurt_hold if id=="hit" else None,ground_contact=fall if id=="dead" else None))
        produced[id]=asset
        card[id]=preview
        print(role,id,count,flush=True)
    clips=[]
    for previous in old["clips"]:
        if previous["id"] in produced:
            asset=produced[previous["id"]]
            asset["previous"]=previous
            clips.append(asset)
        else:
            clips.append(previous)
    labels=old.get("partNames",{})
    data=dict(clips=clips,parts=all_parts,partOrder=[*order,*travel.parts],partNames={**labels,**names})
    (root/"viewer-data.js").write_text("window.CHARACTER_VIEWER_DATA = "+json.dumps(data,ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
    dump(root/"actions-index.json",[{k:v for k,v in a.items() if k not in ("atlas","previous")} for a in clips])
    return root,old_clips,produced,card


def compare_gif(results,action):
    bg=Image.new("RGB",(900,460),"#28242a")
    d=ImageDraw.Draw(bg)
    face=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",18)
    for row,role in enumerate(("orc","elf")):
        label="兽人" if role=="orc" else "暗精灵"
        for col,version in enumerate(("旧版","新版")):
            x,y=12+442*col,10+224*row
            d.rounded_rectangle((x,y,x+434,y+217),8,fill="#342e36")
            d.text((x+13,y+9),label+" · "+version,font=face,fill="#e6daca")
    tracks=[]
    for root,old,new,recent in results:
        item=old[action]["atlas"]
        sheet=Image.open(root/item["texture"])
        phases=[]
        for x,y,w,h in item["frames_xywh"]:
            phases.append(sheet.crop((x,y,x+w,y+h)))
        tracks.append((phases,recent[action]))
    frames=[]
    count=math.lcm(*(len(track) for pair in tracks for track in pair)) if action=="walk" else 42
    for k in range(count):
        frame=bg.copy()
        for row,pair in enumerate(tracks):
            for col,track in enumerate(pair):
                tile=track[k % len(track) if action=="walk" else min(len(track)-1,k)]
                tile=tile.resize((198,169),Image.Resampling.LANCZOS)
                frame.paste(tile,(130+442*col,44+224*row),tile)
        frames.append(frame)
    palette=Image.new("RGB",(900*4,460))
    for i,k in enumerate((0,9,18,27)):
        palette.paste(frames[k],(i*900,0))
    palette=palette.quantize(colors=190)
    frames=[frm.quantize(palette=palette,dither=Image.Dither.NONE) for frm in frames]
    frames[0].save(HERE/("before-after-"+action+".gif"),save_all=True,append_images=frames[1:],duration=[round((i+1)*100/FPS)*10-round(i*100/FPS)*10 for i in range(count)],loop=0,disposal=1,optimize=True)


if __name__=="__main__":
    roles=json.loads((HERE/"travel-rigs.json").read_text(encoding="utf-8-sig"))
    result=[process(role,roles[role]) for role in ("orc","elf")]
    compare_gif(result,"walk")
    compare_gif(result,"defend")




