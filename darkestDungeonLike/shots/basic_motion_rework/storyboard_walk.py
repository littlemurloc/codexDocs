
"""Side-profile locomotion authored from the two 2026-11-18 storyboards."""
import argparse
import json
import math
import re
import runpy
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
CORE = runpy.run_path(str(ROOT / "revise_walk.py"))
RIG = CORE["BASE"]
SIZE, ANCHOR, FPS = CORE["SIZE"], CORE["ANCHOR"], CORE["FPS"]
SECTION = "storyboard-walk"
TRAVEL = {"orc":210, "elf":190}
shift = RIG["offset"]


def rotate(degrees):
    a=math.radians(degrees)
    return np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1.]])


def about(pivot,delta=(0,0),angle=0):
    return shift(pivot[0]+delta[0],pivot[1]+delta[1])@rotate(angle)@shift(-pivot[0],-pivot[1])


def apply(matrix,point):
    return (matrix@(*point,1))[:2]


def ease(t):
    t=max(0,min(1,t))
    return t*t*(3-2*t)


def bounds(image,cut=24):
    return image.getchannel("A").point(lambda a:255 if a>=cut else 0).getbbox()


def masked(image,mask):
    a=image.copy();a.putalpha(ImageChops.multiply(image.getchannel("A"),mask));return a


def depth_tint(image):
    alpha=image.getchannel("A")
    a=ImageEnhance.Brightness(image).enhance(.73)
    a.putalpha(alpha);return a


def point(vector):
    return [round(float(n),3) for n in vector]


def dump(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def read_catalog(root):
    code=(root/"viewer-data.js").read_text(encoding="utf-8-sig").strip()
    return json.loads(re.sub(r"^window\.\w+\s*=\s*","",code).rstrip(";"))


class Model:
    def __init__(self,role,config):
        self.role,self.c=role,config
        self.root=ROOT.parent/config["folder"]
        self.asset=self.root/SECTION
        self.source=Image.open(self.asset/"profile-source.png").convert("RGBA")
        box=bounds(self.source)
        self.ground=box[3]-1
        self.zoom=config["height"]/(self.ground-box[1])
        self.stage=shift(ANCHOR[0]-config["hip"][0]*self.zoom,ANCHOR[1]-self.ground*self.zoom)@np.diag([self.zoom,self.zoom,1.])
        self.rest=np.array(config["near"],dtype=float)
        self.lengths=np.linalg.norm(np.diff(self.rest,axis=0),axis=1)
        self.parts={}
        self.split()
        art,pos=self.parts["boot"]
        y,x=np.where(np.asarray(art.getchannel("A"))>=110)
        self.foot=np.column_stack((x+pos[0],y+pos[1]))-self.rest[2]
        heel,toe=np.array(config["sole"],dtype=float)
        self.sole_angle=math.degrees(math.atan2(*(toe-heel)[::-1]))
        neutral=self.foot@rotate(-self.sole_angle)[:2,:2].T
        self.sole_center=(heel[0]+toe[0])/2-self.rest[2,0]
        self.contact_heel=neutral[np.argmax((neutral@rotate(-7)[:2,:2].T)[:,1])]
        self.contact_toe=neutral[np.argmax((neutral@rotate(28 if self.role=="orc" else 25)[:2,:2].T)[:,1])]

    def take(self,name,mask):
        art=CORE["clean_cutout"](masked(self.source,mask))
        box=bounds(art)
        if not box:raise ValueError("Empty "+name)
        self.parts[name]=(art.crop(box),box[:2])

    def split(self):
        size=self.source.size
        masks={}
        for name,points in self.c["masks"].items():
            mask=Image.new("L",size)
            ImageDraw.Draw(mask).polygon(points,fill=255)
            masks[name]=mask
        covered=Image.new("L",size);owned={}
        for name in ("arm_near","arm_far","leg_near","leg_far","hair","head"):
            if name in masks:
                owned[name]=ImageChops.subtract(masks[name],covered)
                covered=ImageChops.lighter(covered,owned[name])
        trunk=ImageChops.invert(covered.filter(ImageFilter.MinFilter(9)))
        waist=Image.new("L",size)
        ImageDraw.Draw(waist).polygon(self.c["split_waist"],fill=255)
        self.take("pelvis",ImageChops.multiply(trunk,waist.filter(ImageFilter.MaxFilter(17))))
        self.take("chest",ImageChops.multiply(trunk,ImageChops.invert(waist.filter(ImageFilter.MinFilter(17)))))
        for name in ("arm_near","arm_far","head","hair"):
            if name in owned:self.take(name,owned[name].filter(ImageFilter.MaxFilter(11)))
        leg=owned["leg_near"].filter(ImageFilter.MaxFilter(17))
        y,x=np.mgrid[:size[1],:size[0]]
        h,k,a=self.rest;axis=(a-h)/np.linalg.norm(a-h)
        first=(x-k[0])*axis[0]+(y-k[1])*axis[1]
        second=(x-a[0])*axis[0]+(y-a[1])*axis[1]
        for name,select in (("thigh",first<34),("shin",(first>-32)&(second<28)),("boot",second>-27)):
            self.take(name,ImageChops.multiply(leg,Image.fromarray(select.astype("uint8")*255)))

    def paint(self,canvas,name,matrix,far=False,key=None):
        image,pos=self.parts[name]
        if far:image=depth_tint(image)
        placed=self.stage@matrix@shift(*pos)
        self.transforms[key or ("sb_"+name)]=[[round(float(v),7) for v in row] for row in placed]
        inverse=np.linalg.inv(placed)
        canvas.alpha_composite(image.transform(SIZE,Image.Transform.AFFINE,tuple(inverse[:2].ravel()),Image.Resampling.BICUBIC))

    def boot(self,side,t):
        support=.62 if self.role=="orc" else .58
        phase=(t+(0.5 if side=="far" else 0))%1
        stride=TRAVEL[self.role]*support/self.zoom
        if phase<support:
            u=phase/support;x=stride*(.5-u);height=0
            pitch=(-7 if self.role=="orc" else -3)*(1-ease(u/.2))+(28 if self.role=="orc" else 25)*ease((u-.72)/.28)
            planted=True
        else:
            u=(phase-support)/(1-support)
            tangent=-stride*(1-support)/support
            x=stride*(ease(u)-.5)+tangent*(2*u**3-3*u*u+u)
            height=(95 if self.role=="orc" else 70)*math.sin(math.pi*u)**1.35
            pitch=(28 if self.role=="orc" else 25)*(1-ease(u))-7*ease(u);planted=False
        rotation=rotate(pitch-self.sole_angle)
        silhouette=self.foot@rotation[:2,:2].T
        contact=self.contact_toe if pitch>=0 else self.contact_heel
        mapped=rotate(pitch)[:2,:2]@contact
        fix=contact[0]-mapped[0]
        ground=self.ground+(3 if side=="near" else -3)
        ankle=np.array([self.c["hip"][0]+x-self.sole_center+fix,ground-height-silhouette[:,1].max()])
        matrix=shift(*ankle)@rotation@shift(*(-self.rest[2]))
        info={"planted":planted,"contact":point(apply(self.stage,(ankle[0]+mapped[0],ground-height))),
              "height":round(height*self.zoom,3),"contact_mode":"toe" if pitch>=0 else "heel"}
        return ankle,matrix,info

    def frame(self,number):
        t=number/self.c["duration"];phase=t*math.tau
        canvas=Image.new("RGBA",SIZE);joints={};contacts={};self.transforms={}
        if self.role=="orc":
            down=10*math.cos(2*phase-.55)-4;fx=3*math.sin(phase-.2)
            lean=.8*math.sin(phase-.5);head_turn=-.7*math.sin(2*phase-.9);drop=0
        else:
            down=7*math.cos(2*phase-.5);fx=3*math.sin(phase-.3)
            lean=.6*math.sin(phase-.4);head_turn=-lean;drop=0
        pivot=self.c["pivots"]
        feet = {side:self.boot(side,t) for side in ("far","near")}
        # Lower the pelvis only as much as the trailing, planted leg requires.
        # This preserves the open contact silhouette and bends the knees on load.
        for side,(ankle,_,_) in feet.items():
            hip_x=self.rest[0,0]+fx+(-18 if side=="far" else 18)
            reach=self.lengths.sum()*.975
            dx=ankle[0]-hip_x
            floor=ankle[1]-math.sqrt(max(1,reach*reach-dx*dx))
            drop=max(drop,floor-self.rest[0,1]-down)
        pelvis=about(pivot["pelvis"],(fx,down+drop))
        chest=pelvis@about(pivot["chest"],(0,0 if self.role=="elf" else 5*math.sin(2*phase-.8)),lean)
        head=chest@about(pivot["head"],(0,-2*math.sin(2*phase-.7)),head_turn)
        def paint(name,matrix,far=False):
            self.paint(canvas,name,matrix,far)
            if name in pivot:joints["sb_"+name]=point(apply(self.stage@matrix,pivot[name]))
        for side in ("far","near"):
            ankle,boot,contacts[side]=feet[side]
            hip=apply(pelvis,self.rest[0]+np.array([-18 if side=="far" else 18,0]))
            knee=CORE["knee_forward"](hip,ankle,self.lengths)
            for label,pos,transform in (
                ("thigh",hip,segment(self.rest[0],self.rest[1],hip,knee)),
                ("shin",knee,segment(self.rest[1],self.rest[2],knee,ankle)),
                ("boot",ankle,boot),
            ):
                self.paint(canvas,label,transform,side=="far",key="sb_"+side+"_"+label)
                joints["sb_"+side+"_"+label]=point(apply(self.stage,pos))
        paint("arm_far",chest@about(pivot["arm_far"],(0,0),(-2.4 if self.role=="orc" else -1.2)*math.sin(phase-.5)),True)
        paint("pelvis",pelvis);paint("chest",chest);paint("head",head)
        if "hair" in self.parts:
            paint("hair",head@about(pivot["hair"],(0,0),1.7*math.sin(phase-1.1)))
        paint("arm_near",chest@about(pivot["arm_near"],(0,0),(4 if self.role=="orc" else 1.1)*math.sin(phase-.8)))
        return canvas,joints,contacts,self.transforms

    def export(self):
        result={};pivot=self.c["pivots"]
        labels={"pelvis":"骨盆腰布","chest":"前倾胸廓","head":"头颈","hair":"银辫","arm_near":"近持械臂","arm_far":"远持械臂"}
        for name,(art,pos) in self.parts.items():
            path=SECTION+"/parts/"+name+".png";art.save(self.root/path)
            if name in ("thigh","shin","boot"):continue
            ident="sb_"+name
            parent={"pelvis":None,"chest":"sb_pelvis","head":"sb_chest","hair":"sb_head","arm_near":"sb_chest","arm_far":"sb_chest"}[name]
            result[ident]={"parent":parent,"pivot":pivot[name],"position":pos,"size":art.size,"path":path,"label":"分镜 · "+labels[name],"brightness":.73 if name=="arm_far" else 1}
        for side in ("far","near"):
            for name,i in (("thigh",0),("shin",1),("boot",2)):
                ident="sb_"+side+"_"+name;art,pos=self.parts[name]
                parent={"thigh":"sb_pelvis","shin":"sb_"+side+"_thigh","boot":"sb_"+side+"_shin"}[name]
                result[ident]={"parent":parent,"pivot":self.rest[i].tolist(),"position":pos,"size":art.size,"path":SECTION+"/parts/"+name+".png",
                               "brightness":.73 if side=="far" else 1,"label":"分镜 · "+("近" if side=="near" else "远")+{"thigh":"大腿","shin":"小腿","boot":"靴"}[name]}
        return result


def segment(p1,p2,q1,q2):
    old=np.array(p2)-p1;now=np.array(q2)-q1
    zoom=np.linalg.norm(now)/np.linalg.norm(old)
    angle=math.degrees(math.atan2(now[1],now[0])-math.atan2(old[1],old[0]))
    return shift(*q1)@rotate(angle)@np.diag([zoom,zoom,1.])@shift(-p1[0],-p1[1])


def render():
    config=json.loads((ROOT/"storyboard-binding.json").read_text(encoding="utf-8-sig"))
    results={}
    for role,c in config.items():
        model=Model(role,c);frames=[]
        for n in range(c["duration"]):
            try:frames.append(model.frame(n))
            except ValueError as err:raise ValueError(f"{role} frame {n}: {err}") from err
        results[role]=(model,frames)
    return results


def save_gif(frames,path):
    palette_input=Image.new("RGB",(frames[0].width*4,frames[0].height))
    for i,n in enumerate((0,len(frames)//4,len(frames)//2,len(frames)*3//4)):palette_input.paste(frames[n],(i*frames[0].width,0))
    palette=palette_input.quantize(colors=192)
    items=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    delay=[round((i+1)*100/FPS)*10-round(i*100/FPS)*10 for i in range(len(frames))]
    items[0].save(path,save_all=True,append_images=items[1:],duration=delay,loop=0,disposal=1,optimize=True)


def overview(results):
    page=Image.new("RGB",(920,438),"#29262b");d=ImageDraw.Draw(page)
    font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",19)
    for i,label in enumerate(("兽人 · 分镜步态","暗精灵 · 分镜潜行")):
        x=12+455*i;d.rounded_rectangle((x,10,x+440,425),8,fill="#39333d")
        d.text((x+16,25),label,font=font,fill="#ecddc4")
    frames=[]
    for n in range(math.lcm(*(len(item[1]) for item in results.values()))):
        img=page.copy()
        for i,role in enumerate(("orc","elf")):
            tile=results[role][1][n%len(results[role][1])][0].resize((410,349),Image.Resampling.LANCZOS)
            img.paste(tile,(26+455*i,45),tile)
        frames.append(img)
    save_gif(frames,ROOT/"storyboard-walk-preview.gif")
    pose_phases=(0,.107,.321,.429,.5,.607,.821,.929)
    labels=("接地","承重","通过","前伸","反侧接地","反侧承重","反侧通过","前伸")
    sheet=Image.new("RGBA",(1680,1440),"#cfc1b6");d=ImageDraw.Draw(sheet)
    for i,role in enumerate(("orc","elf")):
        y=i*720;d.text((22,y+12),("兽人 · 低斧沉步" if role=="orc" else "暗精灵 · 双刃潜行"),font=font,fill="#312832")
        for j,phase in enumerate(pose_phases):
            n=round(phase*len(results[role][1]))
            col,row=j%4,j//4
            image=results[role][1][n][0].resize((414,353),Image.Resampling.LANCZOS)
            sheet.alpha_composite(image,(col*420,y+row*340+12))
            d.text((col*420+24,y+row*340+314),f"{n+1:02d}  "+labels[j],font=font,fill="#645458")
    sheet.convert("RGB").save(ROOT/"storyboard-walk-poses.png")



def integrate(results):
    for role,(model,seq) in results.items():
        root=model.root;catalog=read_catalog(root);length=len(seq)
        (model.asset/"parts").mkdir(parents=True,exist_ok=True)
        prior=next(item for item in catalog["clips"] if item["id"]=="walk_study")
        images=[item[0] for item in seq]
        texture=SECTION+"/walk-atlas.png";meta=SECTION+"/walk-atlas.json"
        sheet=Image.new("RGBA",(8*SIZE[0],math.ceil(length/8)*SIZE[1]));rects=[]
        for i,img in enumerate(images):
            x,y=i%8*SIZE[0],i//8*SIZE[1];sheet.paste(img,(x,y));rects.append([x,y,*SIZE])
        sheet.save(root/texture,optimize=True)
        joints=[item[1] for item in seq]
        gap=[f["sb_near_boot"][0]-f["sb_far_boot"][0] for f in joints]
        passes=[i for i in range(length) if gap[i-1]*gap[i]<0]
        records=model.export()
        atlas={"animation":"walk_storyboard","texture":texture,"image_size":list(sheet.size),"fps":FPS,"loop":True,"anchor_in_frame":list(ANCHOR),
               "frames_xywh":rects,"joint_positions":joints,"events":[{"event":e,"frame":n,"time":round(n/FPS,4)} for n,e in ((0,"step_near"),(length//2,"step_far"))],
               "joint_parents":{k:v["parent"] for k,v in records.items() if v["parent"]},
               "locomotion":{"travel_pixels_per_cycle":TRAVEL[role],"stance_fraction":.62 if role=="orc" else .58,"contacts_by_frame":[item[2] for item in seq]}}
        dump(root/meta,atlas)
        webp=SECTION+"/walk.webp";thumb=SECTION+"/walk-thumb.png"
        timing=[round((i+1)*1000/FPS)-round(i*1000/FPS) for i in range(length)]
        images[0].save(root/webp,save_all=True,append_images=images[1:],duration=timing,loop=0,quality=89,method=3);images[0].save(root/thumb)
        binding=SECTION+"/rig.json"
        dump(root/binding,{"animation":"walk_storyboard","parts":records,"config":model.c,"fps":FPS,"duration_frames":length,
            "frame_size":list(SIZE),"anchor_in_frame":list(ANCHOR),"loop":True,
            "matrix_convention":"3x3 column-vector affine, cropped part pixels to frame pixels",
            "draw_order":list(seq[0][3]),"part_matrices":[item[3] for item in seq],
            "locomotion":atlas["locomotion"],"joint_positions":joints})
        for k,item in records.items():
            catalog["parts"][k]=item;catalog.setdefault("partNames",{})[k]=item["label"]
            if k not in catalog["partOrder"]:catalog["partOrder"].append(k)
        entry={"id":"walk_storyboard","name":"分镜行进 · "+("低斧沉步" if role=="orc" else "双刃潜行"),"category":"分镜重制","atlas":atlas,
               "atlasPath":meta,"motionPath":binding,"thumbnail":thumb,"webp":webp,
               "marks":[(0,"前脚接地"),(round(length*.107),"承重"),(passes[0],"远脚通过"),(length//2,"另一脚接地"),(round(length*.607),"另一侧承重"),(passes[1],"近脚通过")],
               "previous":{**{k:v for k,v in prior.items() if k!="previous"},"id":"walk_storyboard"}}
        catalog["clips"]=[item for item in catalog["clips"] if item["id"]!="walk_storyboard"];catalog["clips"].insert(0,entry)
        (root/"viewer-data.js").write_text("window.CHARACTER_VIEWER_DATA = "+json.dumps(catalog,ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
        dump(root/"actions-index.json",[{k:v for k,v in a.items() if k not in ("atlas","previous")} for a in catalog["clips"]])


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--preview-only",action="store_true")
    args=parser.parse_args();results=render();overview(results)
    if not args.preview_only:integrate(results)

