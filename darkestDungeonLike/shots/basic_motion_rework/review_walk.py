
"""Walk revision after frame-by-frame review. Reuses the painted travel parts."""
import argparse
import copy
import json
import math
import runpy
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / "author_walk.py"))
CORE = BASE["CORE"]
RIG = BASE["BASE"]
FRAMES, FPS, DISTANCE, SIZE, ANCHOR = (BASE[key] for key in ("FRAMES", "FPS", "DISTANCE", "SIZE", "ANCHOR"))
offset, rotation, move_about, point = (BASE[key] for key in ("offset", "rotation", "move_about", "point"))
smooth, rounded, segment_matrix = (BASE[key] for key in ("smooth", "rounded", "segment_matrix"))
FOLDER = "walk-study-v2"


# Independently authored contact, load, and passing poses. Each channel owns
# its own timing. x/y are in source pixels, angles in degrees.
ORC = {
    "pelvis": [(0,-3,10,-1),(3,9,27,2),(8,16,13,1),(12,2,2,-1),
               (14,-3,10,1),(17,9,27,-2),(22,16,13,-1),(26,2,2,1)],
    "chest": [(0,14,3,3),(4,20,14,5),(8,16,7,4),(12,14,0,3),
              (14,14,3,3),(18,20,14,5),(22,16,7,4),(26,14,0,3)],
    "head": [(0,-1,-3,-4),(4,-6,-6,-7),(9,0,-2,-5),(13,-1,-2,-3),
             (14,-1,-3,-4),(18,-6,-6,-3),(23,0,-2,-3),(27,-1,-2,-5)],
    "shoulder_near": [(0,0,1,-3),(4,4,10,-4),(8,0,5,2),(12,-3,-2,4),(17,0,3,5),(22,-4,1,-4),(26,0,-1,-5)],
    "shoulder_far": [(0,-3,-3,5),(4,0,2,3),(8,-3,5,-3),(13,1,2,-5),(18,4,9,-4),(22,0,4,2),(26,-2,-3,4)],
    "forearm_near": [(0,0,0,1),(5,0,0,5),(9,0,0,1),(13,0,0,-5),(19,0,0,-5),(23,0,0,4),(26,0,0,3)],
    "forearm_far": [(0,0,0,-4),(5,0,0,-5),(9,0,0,2),(13,0,0,4),(19,0,0,5),(23,0,0,0),(27,0,0,-4)],
}
ELF = {
    "pelvis": [(0,-15,12,0),(2,-13,14,0),(8,11,6,1),(11,13,5,0),
               (14,-15,12,0),(16,-13,14,0),(22,11,6,-1),(25,13,5,0)],
    "chest": [(0,12,1,5),(4,14,2,6),(8,11,1,6),(12,9,1,5),(15,12,1,5),(19,14,2,6),(23,11,1,6),(26,9,1,5)],
    "head": [(0,2,-6,-11),(5,3,-6,-12),(9,2,-5,-12),(13,1,-6,-11),
             (16,2,-6,-11),(20,3,-6,-12),(24,2,-5,-11)],
    "shoulder_near": [(0,4,-5,-4),(5,4,-5,-3),(10,5,-7,-2),(15,4,-5,-4),(20,4,-5,-3),(25,5,-7,-2)],
    "shoulder_far": [(0,0,-4,-3),(5,-2,-6,-4),(10,-1,-5,-4),(15,0,-4,-3),(20,-2,-6,-4),(25,-1,-5,-4)],
    "forearm_near": [(0,0,0,-64),(4,0,0,-66),(9,0,0,-72),(13,0,0,-66),(18,0,0,-68),(23,0,0,-73),(27,0,0,-66)],
    "forearm_far": [(0,0,0,5),(6,0,0,3),(11,0,0,5),(15,0,0,6),(21,0,0,4),(26,0,0,6)],
    "hand_near": [(0,0,0,56),(5,0,0,57),(10,0,0,63),(15,0,0,56),(20,0,0,58),(25,0,0,63)],
    "braid": [(0,0,0,2),(4,0,0,-2),(9,0,0,-5),(13,0,0,1),(18,0,0,-1),(23,0,0,-4),(27,0,0,3)],
}


def channel(keys, number):
    """Periodic cubic with a tangent at each monotone key and no overshoot."""
    t = number % FRAMES
    i = next(j for j,v in enumerate(keys) if v[0]>t)-1 if t<keys[-1][0] else len(keys)-1
    a = np.array(keys[i][1:],dtype=float)
    b = np.array(keys[(i+1)%len(keys)][1:],dtype=float)
    prev = np.array(keys[(i-1)%len(keys)][1:],dtype=float)
    nxt = np.array(keys[(i+2)%len(keys)][1:],dtype=float)
    width = (keys[(i+1)%len(keys)][0]-keys[i][0])%FRAMES
    before = (keys[i][0]-keys[(i-1)%len(keys)][0])%FRAMES
    after = (keys[(i+2)%len(keys)][0]-keys[(i+1)%len(keys)][0])%FRAMES
    def tangent(x,y):
        return np.divide(2*x*y, x+y, out=np.zeros_like(x), where=(x*y>0))
    current=(b-a)/width
    left=tangent((a-prev)/before,current)*width
    right=tangent(current,(nxt-b)/after)*width
    u=(t-keys[i][0])/width
    return (2*u**3-3*u*u+1)*a+(u**3-2*u*u+u)*left+(-2*u**3+3*u*u)*b+(u**3-u*u)*right


def foot_track(phase,role,support,stride):
    if phase < support:
        t=phase/support
        if role=="orc":
            pitch=-8*(1-smooth(t/.23))+13*smooth((t-.72)/.28)
        else:
            pitch=7*(1-smooth(t/.32))+11*smooth((t-.71)/.29)
        return stride*(.5-t),0.,pitch,True
    t=(phase-support)/(1-support)
    tangent=-stride*(1-support)/support
    x=stride*(smooth(t)-.5)+tangent*(2*t**3-3*t*t+t)
    # Raise the boot at the passing pose so the near/far silhouettes separate.
    lift=(93 if role=="orc" else 85)*math.sin(math.pi*t)**1.26
    roll=13-21*smooth(t) if role=="orc" else 11-11*math.sin(math.pi*t)-4*smooth(t)
    return x,lift,roll,False


class Revision(BASE["Study"]):
    def __init__(self, root, role, config, catalog):
        super().__init__(root,role,config,catalog)
        self.design=copy.deepcopy(self.design)
        self.design["lanes"]=(-28,26) if role=="orc" else (22,-22)
        self.design["drop"]=(34,41) if role=="orc" else (35,52)
        for part in self.parts.values():
            neutral=part["foot"]@rotation(-part["level"])[:2,:2].T
            # Hold the heel or forefoot in actor space while the shoe rolls.
            part["heel"]=neutral[np.argmax((neutral@rotation(-8)[:2,:2].T)[:,1])]
            part["toe"]=neutral[np.argmax((neutral@rotation(13)[:2,:2].T)[:,1])]
            part["flat"]=neutral[np.argmax(neutral[:,1])]
        if role=="elf":
            self.divide_hand()

    def divide_hand(self):
        """Cut at the glove cuff so the blade can stay down while the elbow folds."""
        source=self.art.images["travel_rear_arm"]
        sx,sy=self.art.parts["travel_rear_arm"]["position"]
        self.hand_pivot=(389,672)
        y,x=np.mgrid[sy:sy+source.height,sx:sx+source.width]
        boundary= y-(670+.14*(x-389))
        def cropped(mask):
            layer=source.copy()
            layer.putalpha(ImageChops.multiply(source.getchannel("A"),Image.fromarray(np.uint8(mask)*255)))
            bounds=RIG["opaque_box"](layer,12)
            return layer.crop(bounds),(bounds[0]+sx,bounds[1]+sy)
        self.forearm,self.forearm_pos=cropped(boundary<=11)
        self.blade,self.blade_pos=cropped(boundary>=-11)

    def step(self,side,t,pelvis):
        part=self.parts[side]
        idx=part["idx"]
        h,k,a=part["joints"]
        phase=(t+(0.5 if side=="far" else 0))%1
        design=self.design
        dx,lift,pitch,planted=foot_track(phase,self.role,design["support"],self.stride)
        rotation_boot=rotation(pitch-part["level"])
        rolled=part["foot"]@rotation_boot[:2,:2].T
        contact=part["toe"] if pitch>0.01 else part["heel"] if pitch<-.01 else part["flat"]
        pivoted=rotation(pitch)[:2,:2]@contact
        correction=contact[0]-pivoted[0]
        ground=self.config["ground"]+design["sole"]/self.zoom*(1 if side=="near" else -1)
        ankle=np.array([self.config["body_x"]+design["lanes"][idx]+dx-part["sole_center"]+correction,
                        ground-lift-rolled[:,1].max()])
        hip=point(pelvis,(self.config["body_x"]+design["hips"][idx],h[1]+design["drop"][idx]))
        knee=CORE["knee_forward"](hip,ankle,part["lengths"])
        boot=offset(*ankle)@rotation_boot@offset(*(-a))
        tracks=zip(("thigh","shin","boot"),(hip,knee,ankle),
                   (segment_matrix(h,k,hip,knee),segment_matrix(k,a,knee,ankle),boot))
        info={
            "planted":planted,"contact":rounded(point(self.stage,(ankle[0]+pivoted[0],ground-lift))),
            "contact_mode":("forefoot" if pitch>.01 else "heel" if pitch<-.01 else "flat") if planted else "swing",
            "sole_height":round(float(point(self.stage,(0,ground-lift))[1]),2),
        }
        return tracks,info

    def frame(self,number):
        tracks=ORC if self.role=="orc" else ELF
        controls={name:channel(keys,number) for name,keys in tracks.items()}
        pivot=self.design["pivot"]
        pelvis=move_about(pivot["pelvis"],*controls["pelvis"])
        chest=pelvis@move_about(pivot["chest"],*controls["chest"])
        head=chest@move_about(pivot["head"],*controls["head"])
        canvas=Image.new("RGBA",SIZE)
        joints,contacts={},{}
        def mark(name,matrix,pos):
            joints[name]=rounded(point(self.stage@matrix,pos))
        def draw(name,matrix):
            image,pos=self.upper[name]
            RIG["raster_layer"](canvas,image,self.stage@matrix@offset(*pos))
            mark("study_"+name,matrix,pivot[name])
        for side in ("far","near"):
            regions,contacts[side]=self.step(side,number/FRAMES,pelvis)
            for region,pos,matrix in regions:
                name=f"travel_{side}_{region}"
                self.art.part(canvas,name,self.stage@matrix)
                joints[name]=rounded(point(self.stage,pos))
        draw("pelvis",pelvis)
        for side,source in (("far","travel_front_arm"),("near","travel_rear_arm")):
            if side=="near":
                if self.role=="elf":
                    braid=self.art.parts["travel_braid"]["pivot"]
                    weave=head@move_about(braid,*controls["braid"])
                    self.art.part(canvas,"travel_braid",self.stage@weave)
                    mark("travel_braid",weave,braid)
                draw("chest",chest)
                draw("head",head)
            shoulder="shoulder_"+side
            arm=chest@move_about(pivot[shoulder],*controls[shoulder])
            draw(shoulder,arm)
            elbow=self.art.parts[source]["pivot"]
            wrist=arm@move_about(elbow,*controls["forearm_"+side])
            if self.role=="elf" and side=="near":
                RIG["raster_layer"](canvas,self.forearm,self.stage@wrist@offset(*self.forearm_pos))
                blade=wrist@move_about(self.hand_pivot,*controls["hand_near"])
                RIG["raster_layer"](canvas,self.blade,self.stage@blade@offset(*self.blade_pos))
                mark("study_elf_hand",blade,self.hand_pivot)
            else:
                self.art.part(canvas,source,self.stage@wrist)
            mark(source,wrist,elbow)
        return canvas,joints,contacts


def collect():
    result={}
    for role,config in BASE["loaded_config"]().items():
        root=HERE.parent/config["folder"]
        catalog=CORE["read_data"](root)
        prior=next(clip for clip in catalog["clips"] if clip["id"]=="walk_study")
        if prior["atlas"]["texture"].startswith(FOLDER+"/"):
            prior=prior["previous"]
        model=Revision(root,role,config["travel"],catalog)
        frames=[]
        for frame in range(FRAMES):
            try:
                frames.append(model.frame(frame))
            except ValueError as error:
                raise ValueError(f"{role}, frame {frame}: {error}") from error
        result[role]=(root,model,catalog,prior,frames)
    return result


def passing(joints):
    gaps=[pose["travel_near_boot"][0]-pose["travel_far_boot"][0] for pose in joints]
    return [i for i in range(FRAMES) if gaps[i-1]*gaps[i]<0]


def previews(results):
    font=BASE["font"]
    names=(("orc","兽人"),("elf","暗精灵"))
    board=Image.new("RGBA",(1120,570),"#cbbfb7")
    d=ImageDraw.Draw(board)
    d.text((25,16),"步态二版 · 接地 / 承重 / 过步",font=font(25),fill="#362c36")
    for i,(role,label) in enumerate(names):
        _,_,_,_,sequence=results[role]
        cross=passing([row[1] for row in sequence])
        y=59+i*256
        d.rounded_rectangle((12,y,1107,y+242),8,fill="#dfd3ca")
        d.text((27,y+13),label,font=font(17),fill="#372c39")
        for j,n in enumerate((0,3,cross[0],14,17,cross[1])):
            px=90+j*166
            sprite=sequence[n][0].crop((115,63,304,341))
            sprite.thumbnail((156,185),Image.Resampling.LANCZOS)
            board.alpha_composite(sprite,(px+(158-sprite.width)//2,y+18))
            d.text((px+34,y+213),f"第 {n+1} 帧",font=font(13),fill="#695768")
        d.line((100,y+197,1090,y+197),fill="#ae9d97",width=1)
    board.convert("RGB").save(HERE/"walk-review-poses.png")
    back=Image.new("RGB",(920,560),"#28242d")
    d=ImageDraw.Draw(back)
    tracks=[]
    for row,(role,label) in enumerate(names):
        root,_,_,prior,after=results[role]
        atlas=prior["atlas"]
        page=Image.open(root/atlas["texture"])
        before=[page.crop((x,y,x+w,y+h)) for x,y,w,h in atlas["frames_xywh"]]
        tracks.append((before,[sprite for sprite,_,_ in after]))
        for col,version in enumerate(("上一版","审片修订版")):
            x,y=12+449*col,10+270*row
            d.rounded_rectangle((x,y,x+436,y+258),8,fill="#352f3b")
            d.text((x+13,y+11),label+" · "+version,font=font(17),fill="#f0dfc8")
            ground=y+227
            d.line((x+15,ground,x+420,ground),fill="#726274")
            for a in range(x+22,x+420,26):
                d.line((a,ground,a-5,ground+6),fill="#695968")
    frames=[]
    # Fixed camera with real x translation and identical native speed.
    for n in range(FRAMES*2):
        fmt=back.copy()
        shift=round(n*DISTANCE/FRAMES*.76)
        for row,pair in enumerate(tracks):
            for col,sequence in enumerate(pair):
                sprite=sequence[n%FRAMES].crop((86,61,380,349)).resize((223,219),Image.Resampling.LANCZOS)
                fmt.paste(sprite,(18+449*col+shift,31+270*row),sprite)
        frames.append(fmt)
    palette_source=Image.new("RGB",(920*4,560))
    for i,p in enumerate((0,6,13,20)):
        palette_source.paste(frames[p],(i*920,0))
    palette=palette_source.quantize(colors=190)
    gif=[image.quantize(palette=palette,dither=Image.Dither.NONE) for image in frames]
    timing=[round((i+1)*100/FPS)*10-round(i*100/FPS)*10 for i in range(len(gif))]
    gif[0].save(HERE/"walk-review-fixed-camera.gif",save_all=True,append_images=gif[1:],duration=timing,loop=0,disposal=1,optimize=True)


def publish(results):
    for role,(root,model,catalog,prior,frames) in results.items():
        (root/FOLDER).mkdir(exist_ok=True)
        tile_list=[]
        sheet=Image.new("RGBA",(8*SIZE[0],math.ceil(FRAMES/8)*SIZE[1]))
        for i,(body,_,_) in enumerate(frames):
            x,y=(i%8)*SIZE[0],(i//8)*SIZE[1]
            sheet.paste(body,(x,y))
            tile_list.append([x,y,*SIZE])
        prefix=FOLDER+"/walk"
        paths={name:prefix+suffix for name,suffix in [("texture","-atlas.png"),("meta","-atlas.json"),
                  ("webp",".webp"),("thumb","-thumb.png"),("keys","-keys.json")]}
        sheet.save(root/paths["texture"],optimize=True)
        joints=[entry[1] for entry in frames]
        atlas={**prior["atlas"]}
        atlas.update(texture=paths["texture"],image_size=list(sheet.size),frames_xywh=tile_list,joint_positions=joints)
        atlas["locomotion"]={**prior["atlas"]["locomotion"],"contacts_by_frame":[item[2] for item in frames],
                             "travel_pixels_per_cycle":DISTANCE}
        if role=="elf":
            atlas["joint_parents"]={**atlas["joint_parents"],"study_elf_hand":"travel_rear_arm"}
            for key,image,pos,title,parent,pivot in [
                ("forearm",model.forearm,model.forearm_pos,"试做修订 · 近前臂","study_shoulder_near",model.art.parts["travel_rear_arm"]["pivot"]),
                ("hand",model.blade,model.blade_pos,"试做修订 · 近手与匕首","travel_rear_arm",model.hand_pivot),
            ]:
                path=f"{FOLDER}/{key}.png"
                image.save(root/path)
                ident="study_elf_"+key
                catalog["parts"][ident]={"parent":parent,"position":list(pos),"pivot":list(pivot),"size":list(image.size),"path":path,"label":title}
                catalog.setdefault("partNames",{})[ident]=title
                if ident not in catalog["partOrder"]:
                    catalog["partOrder"].append(ident)
        RIG["dump"](root/paths["meta"],atlas)
        RIG["dump"](root/paths["keys"],{"channels":ORC if role=="orc" else ELF,
                       "motion":"periodic monotone cubic; heel/flat/forefoot support", "episode_frames":FRAMES})
        images=[item[0] for item in frames]
        delays=[round((i+1)*1000/FPS)-round(i*1000/FPS) for i in range(len(images))]
        images[0].save(root/paths["webp"],save_all=True,append_images=images[1:],duration=delays,loop=0,quality=87,method=3)
        images[3].save(root/paths["thumb"])
        cross=passing(joints)
        entry={**prior,"name":"行走试做二版 · "+model.design["name"],"atlas":atlas,
               "atlasPath":paths["meta"],"webp":paths["webp"],"thumbnail":paths["thumb"],"motionPath":paths["keys"],
               "marks":[(0,"接地"),(3,"承重"),(cross[0],"远脚过步"),(14,"另一脚接地"),(17,"另一侧承重"),(cross[1],"近脚过步")],
               "previous":{k:v for k,v in prior.items() if k!="previous"}}
        old=next(i for i,a in enumerate(catalog["clips"]) if a["id"]=="walk_study")
        catalog["clips"][old]=entry
        (root/"viewer-data.js").write_text("window.CHARACTER_VIEWER_DATA = "+json.dumps(catalog,ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
        RIG["dump"](root/"actions-index.json",[{k:v for k,v in a.items() if k not in ("atlas","previous")} for a in catalog["clips"]])


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--preview-only",action="store_true")
    args=parser.parse_args()
    clips=collect()
    previews(clips)
    if not args.preview_only:
        publish(clips)

