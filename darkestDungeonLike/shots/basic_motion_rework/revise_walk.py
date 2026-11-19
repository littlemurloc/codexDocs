
"""Correct the travel gait for both characters using the existing painted parts."""
import json
import math
import re
import runpy
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE=Path(__file__).parent
SHOTS=HERE.parent
BASE=runpy.run_path(str(HERE/"revise_basics.py"))
SIZE=BASE["SIZE"]
ANCHOR=BASE["ANCHOR"]
FPS=BASE["FPS"]
offset=BASE["offset"]
rotation=BASE["rotation"]
scale=BASE["scale"]
move_about=BASE["move_about"]
segment_matrix=BASE["segment_matrix"]
rounded=BASE["rounded"]
smooth=BASE["smooth"]
dump=BASE["dump"]

# In a 3/4 sprite the legs are separated mostly in depth. The near/far motion
# lanes are deliberately narrow so the swing foot can pass the support foot.
DESIGN={
    "orc":dict(frames=28,support=.62,stride=226,lift=52,hips=(-39,46),lanes=(-32,32),
               drop=(28,36),bob=11,lean=2.4,twist=1.4,lag=.14,sole=1.2,heel=5,toe=12,arm=4.7),
    "elf":dict(frames=24,support=.56,stride=220,lift=61,hips=(25,-25),lanes=(22,-22),
               drop=(29,47),bob=7,lean=4.2,twist=1.2,lag=.22,sole=1.1,heel=3,toe=13,arm=5.8),
}


def gait(phase,profile):
    stride,support=profile["stride"],profile["support"]
    if phase<support:
        u=phase/support
        # Foot position in actor space retreats at world travel speed in stance.
        x=stride*(.5-u)
        pitch=-profile["heel"]*(1-smooth(u/.19))+profile["toe"]*smooth((u-.68)/.32)
        return x,0.,pitch,True
    u=(phase-support)/(1-support)
    # Match x velocity on release and re-contact. Plain smoothstep would stop
    # the boot in actor space at both ends and visibly jerk when stance starts.
    tangent=-stride*(1-support)/support
    x=stride*(smooth(u)-.5)+tangent*(2*u**3-3*u**2+u)
    lift=profile["lift"]*math.sin(math.pi*u)**1.42
    pitch=profile["toe"]*(1-smooth(u)) - profile["heel"]*smooth(u)
    return x,lift,pitch,False


def knee_forward(hip,ankle,lengths):
    first,second=lengths
    delta=ankle-hip
    dist=float(np.linalg.norm(delta))
    if dist>=first+second or dist<=abs(first-second):
        raise ValueError(f"Unreachable leg pose at length {dist:.2f} or max reach {first+second:.2f}")
    unit=delta/dist
    along=(first**2-second**2+dist**2)/(2*dist)
    across=math.sqrt(max(0,first**2-along**2))
    # In screen coordinates +X faces right, and y runs downward.
    bend=np.array([unit[1],-unit[0]])
    return hip+along*unit+across*bend


def point(affine,v):
    return (affine@(*v,1))[:2]


def hips_key(phase,profile):
    tau=math.tau*phase
    # Lowest on loading response, highest around mid-support.
    settle=math.cos(2*(tau-profile["lag"]))
    return 7*math.sin(tau+.26),profile["bob"]*settle


def clean_cutout(image):
    """Strip fragments from neighbouring parts left behind by the atlas cuts."""
    source=image.getchannel("A")
    active=set(zip(*np.nonzero(np.asarray(source)>=55)))
    main=[]
    while active:
        component=[active.pop()]
        for y,x in component:
            for pixel in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if pixel in active:
                    active.remove(pixel)
                    component.append(pixel)
        if len(component)>len(main):
            main=component
    if not main:
        raise ValueError("Empty walk cutout")
    mask=np.zeros((image.height,image.width),dtype=np.uint8)
    yy,xx=np.asarray(main).T
    mask[yy,xx]=255
    result=image.copy()
    result.putalpha(ImageChops.multiply(source,Image.fromarray(mask).filter(ImageFilter.MaxFilter(7))))
    return result


class WalkingModel:
    def __init__(self,root,config,profile,catalog):
        self.profile=profile
        self.config=config
        self.art=BASE["Rig"](root,{key:item for key,item in catalog["parts"].items() if key.startswith("travel_")})
        self.art.images={key:clean_cutout(image) for key,image in self.art.images.items()}
        original=Image.open(root/"motion-v2/travel.png").convert("RGBA")
        self.zoom=config["draw_height"]/(config["ground"]-BASE["opaque_box"](original)[1])
        self.stage=offset(ANCHOR[0]-config["body_x"]*self.zoom,ANCHOR[1]-config["ground"]*self.zoom)@scale(self.zoom,self.zoom)
        self.parts={}
        for i,side in enumerate(("near","far")):
            leg=config["legs"][side]
            joints=np.asarray(leg["joints"],dtype=float)
            heel,toe=np.asarray(leg["sole"],dtype=float)
            partkey="travel_"+side+"_boot"
            boot=self.art.images[partkey]
            x,y=self.art.parts[partkey]["position"]
            ay,ax=np.nonzero(np.asarray(boot.getchannel("A"))>=100)
            support_sample=np.stack([ax+x,ay+y],axis=1).astype(float)-joints[2]
            # Use the actual boot alpha to find the lowest point after rolling.
            self.parts[side]=dict(idx=i,joints=joints,lengths=np.linalg.norm(np.diff(joints,axis=0),axis=1),
                foot=support_sample,level=math.degrees(math.atan2(*(toe-heel)[::-1])),
                sole_center=(heel[0]+toe[0])*.5-joints[2,0])

    def solve_leg(self,side,phase,root_x,bob):
        model=self.parts[side]
        profile=self.profile
        i=model["idx"]
        src_hip,src_knee,src_ankle=model["joints"]
        t=(phase+(0.5 if side=="far" else 0))%1.
        step,lift,roll,planted=gait(t,profile)
        pitch=roll-model["level"]
        rot=rotation(pitch)
        contour=model["foot"]@rot[:2,:2].T
        lowest=int(np.argmax(contour[:,1]))
        contact=contour[lowest]
        depth=profile["sole"]/self.zoom if side=="near" else -profile["sole"]/self.zoom
        ankle=np.array([self.config["body_x"]+profile["lanes"][i]+step-model["sole_center"],
                        self.config["ground"]+depth-lift-contact[1]])
        hip=np.array([self.config["body_x"]+profile["hips"][i]+root_x,
                        src_hip[1]+profile["drop"][i]+bob])
        knee=knee_forward(hip,ankle,model["lengths"])
        boot=offset(*ankle)@rot@offset(*(-src_ankle))
        points=(hip,knee,ankle)
        mats=(segment_matrix(src_hip,src_knee,hip,knee),segment_matrix(src_knee,src_ankle,knee,ankle),boot)
        marker=rounded(point(self.stage,ankle+contact))
        return points,mats,dict(planted=planted,contact=marker,
                               ankle=rounded(point(self.stage,ankle)),relative_foot_x=round(float(ankle[0]),4))

    def frame(self,frame):
        t=frame/self.profile["frames"]
        phase=math.tau*t
        root_x,bob=hips_key(t,self.profile)
        canvas=Image.new("RGBA",SIZE)
        joints,feet={},{}
        for side in ("far","near"):
            points,mats,feet[side]=self.solve_leg(side,t,root_x,bob)
            for region,pivot,matrix in zip(("thigh","shin","boot"),points,mats):
                key=f"travel_{side}_{region}"
                self.art.part(canvas,key,self.stage@matrix)
                joints[key]=rounded(point(self.stage,pivot))
        pivot=self.config["hip"]
        root_drop=math.fsum(self.profile["drop"])/2
        upper=move_about(pivot,root_x*.7,root_drop+bob*.82,self.profile["lean"]+self.profile["twist"]*math.sin(phase-.3))
        self.art.part(canvas,"travel_body",self.stage@upper)
        joints["travel_body"]=rounded(point(self.stage@upper,pivot))
        for name,extra in self.config.get("extra",{}).items():
            if name=="travel_braid":
                angle=3.5*math.sin(phase-1.12)
            else:
                side=-1 if name=="travel_front_arm" else 1
                angle=side*self.profile["arm"]*math.sin(phase-.40)
            transform=self.stage@upper@move_about(extra["pivot"],0,0,angle)
            self.art.part(canvas,name,transform)
            joints[name]=rounded(point(transform,extra["pivot"]))
        return canvas,joints,feet


def read_data(root):
    code=(root/"viewer-data.js").read_text(encoding="utf-8-sig").strip()
    return json.loads(re.sub(r"^window\.\w+\s*=\s*","",code).rstrip(";"))


def build(root,role,config):
    catalog=read_data(root)
    slot=next(i for i,item in enumerate(catalog["clips"]) if item["id"]=="walk")
    current=catalog["clips"][slot]
    old=current["previous"] if current["atlas"]["texture"].startswith("motion-v3/") else current
    # Keep the immediate baseline, not a chain of archived clip records.
    old={key:value for key,value in old.items() if key!="previous"}
    profile=DESIGN[role]
    model=WalkingModel(root,config,profile,catalog)
    bodies,keys,contacts=map(list,zip(*(model.frame(i) for i in range(profile["frames"]))))
    prefix="motion-v3/walk"
    (root/"motion-v3").mkdir(exist_ok=True)
    frames=[]
    atlas_img=Image.new("RGBA",(8*SIZE[0],math.ceil(len(bodies)/8)*SIZE[1]))
    for i,body in enumerate(bodies):
        x,y=(i%8)*SIZE[0],(i//8)*SIZE[1]
        atlas_img.paste(body,(x,y))
        frames.append([x,y,*SIZE])
    atlas_img.save(root/(prefix+"-atlas.png"),optimize=True)
    atlas={
        "id":"walk","animation":"walk","loop":True,"fps":FPS,"image_size":list(atlas_img.size),
        "texture":prefix+"-atlas.png","frames_xywh":frames,"anchor_in_frame":list(ANCHOR),
        "joint_positions":keys,
        "events":[{"event":evt,"frame":f,"time":round(f/FPS,4)}
                  for f,evt in [(0,"step_near"),(len(frames)//2,"step_far")]],
        "locomotion":{"stance_fraction":profile["support"],"travel_pixels_per_cycle":round(profile["stride"]*model.zoom/profile["support"],3),
                      "contacts_by_frame":contacts,"ground_y_by_side":{"near":ANCHOR[1]+profile["sole"],"far":ANCHOR[1]-profile["sole"]}},
    }
    atlas_path=prefix+"-atlas.json"
    dump(root/atlas_path,atlas)
    motion_path=prefix+"-motion.json"
    dump(root/motion_path,{"id":"walk","profile":profile,"gait":"continuous stance and swing, two-bone forward knees, alpha-sole contact",
                           "input_parts":"../motion-v2/parts","events":atlas["events"]})
    delays=[round((i+1)*1000/FPS)-round(i*1000/FPS) for i in range(len(frames))]
    webp=prefix+".webp"
    bodies[0].save(root/webp,save_all=True,append_images=bodies[1:],loop=0,duration=delays,quality=87,method=3)
    thumb=prefix+"-thumb.png"
    bodies[0].save(root/thumb)
    marks=[(0,"近脚落地"),(len(frames)//4,"远脚越过"),(len(frames)//2,"远脚落地"),(len(frames)*3//4,"近脚越过")]
    entry={"id":"walk","name":old["name"],"category":"基础动作","atlas":atlas,"atlasPath":atlas_path,
           "motionPath":motion_path,"webp":webp,"thumbnail":thumb,"marks":marks,"previous":old}
    catalog["clips"][slot]=entry
    (root/"viewer-data.js").write_text("window.CHARACTER_VIEWER_DATA = "+json.dumps(catalog,ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
    dump(root/"actions-index.json",[{k:v for k,v in a.items() if k not in ("atlas","previous")} for a in catalog["clips"]])
    return bodies,old


def make_demo(results):
    width,height=728,456
    base=Image.new("RGB",(width,height),"#2e2a32")
    d=ImageDraw.Draw(base)
    font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",16)
    tracks=[]
    for row,(role,root,bodies,old) in enumerate(results):
        image=Image.open(root/old["atlas"]["texture"])
        a=[]
        for x,y,w,h in old["atlas"]["frames_xywh"]:
            a.append(image.crop((x,y,x+w,y+h)))
        tracks.append((a,bodies))
        for side,version in enumerate(("修正前","修正后")):
            px,py=12+side*356,9+row*225
            d.rounded_rectangle((px,py,px+345,py+217),8,fill="#39333c")
            d.text((px+13,py+8),("兽人" if role=="orc" else "暗精灵")+" · "+version,font=font,fill="#f4e6cb")
            d.line((px+42,py+193,px+302,py+193),fill="#61535f")
    frames=[]
    # Compare at the same gait phase. The downloadable clips keep native tempo.
    for i in range(36):
        canvas=base.copy()
        for row,pair in enumerate(tracks):
            for side,track in enumerate(pair):
                image=track[i*len(track)//36].resize((229,195),Image.Resampling.LANCZOS)
                canvas.paste(image,(61+side*356,36+row*225),image)
        frames.append(canvas)
    samples=Image.new("RGB",(width*4,height))
    for i,f in enumerate((0,9,18,27)):
        samples.paste(frames[f],(i*width,0))
    palette=samples.quantize(colors=180)
    gif=[a.quantize(palette=palette,dither=Image.Dither.NONE) for a in frames]
    gif[0].save(HERE/"walk-correction.gif",save_all=True,append_images=gif[1:],duration=40,loop=0,disposal=1,optimize=True)


if __name__=="__main__":
    configs=json.loads((HERE/"travel-rigs.json").read_text(encoding="utf-8-sig"))
    results=[]
    for role,config in configs.items():
        project=SHOTS/config["folder"]
        sprites,baseline=build(project,role,config["travel"])
        results.append((role,project,sprites,baseline))
    make_demo(results)

