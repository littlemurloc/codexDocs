
"""Pose-to-pose locomotion study using the existing painted character assets."""
import argparse
import json
import math
import runpy
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
SHOTS = HERE.parent
CORE = runpy.run_path(str(HERE / "revise_walk.py"))
BASE = CORE["BASE"]
SIZE, ANCHOR, FPS = CORE["SIZE"], CORE["ANCHOR"], CORE["FPS"]
offset, rotation, scale = CORE["offset"], CORE["rotation"], CORE["scale"]
move_about, point = CORE["move_about"], CORE["point"]
clean_cutout, smooth = CORE["clean_cutout"], CORE["smooth"]
segment_matrix, rounded = CORE["segment_matrix"], CORE["rounded"]
dump = CORE["dump"]
FRAMES = 28
DISTANCE = 76.0
PHASES = (0, 3, 7, 11, 14, 17, 21, 25, 28)
CHANNELS = ("pelvis", "chest", "head", "shoulder_near", "shoulder_far", "wrist_near", "wrist_far", "braid")

# Each row is one full-body key pose. Triples are authored local x/y and
# clockwise rotation in image space. The last row closes the loop exactly.
ORC_FIRST = (
    ((-7, 7,-1), (19, 2,5), ( 1,-2,-3), ( 5, 1,-3), ( 0,-1, 5), (0,2, 4), (0,1,-4), (0,0,0)),
    (( 9,24, 3), (33,16,8), ( 8,-4,-4), ( 8,12,-7), (-2, 2, 3), (0,4, 6), (0,1,-3), (0,0,0)),
    ((12,11, 1), (22, 7,5), ( 9,-3,-2), ( 3, 7, 2), ( 0, 1,-4), (0,6,-7), (0,1, 3), (0,0,0)),
    ((-3,-7,-2), (15,-5,3), ( 4, 1,-2), ( 0,-5, 5), ( 1,-2,-3), (0,1,-4), (0,4, 6), (0,0,0)),
    ((-7, 7, 1), (21, 4,6), ( 2,-1,-3), (-2,-2, 5), ( 5, 1,-4), (0,1,-4), (0,2, 5), (0,0,0)),
    (( 8,23,-3), (30,14,7), ( 7,-5,-4), ( 0, 2, 3), ( 6,10,-7), (0,1,-3), (0,4, 6), (0,0,0)),
    ((13,10,-1), (20, 6,4), ( 8,-3,-2), ( 0, 1,-3), ( 3, 6, 3), (0,1, 3), (0,6,-6), (0,0,0)),
    ((-2,-6, 2), (17,-4,3), ( 5, 0,-2), ( 1,-3,-5), ( 1,-4, 4), (0,4, 5), (0,1,-3), (0,0,0)),
)

ELF_FIRST = (
    ((-19,11, 0), (13, 6,9), (5,-1,-9), ( 4,-4,-6), (-1,-5,-4), (1,-3,-12), ( 1,-3, 4), (0,0, 3)),
    ((-12, 9, 0), (15, 8,8), (4,-1,-8), ( 4,-5,-7), (-1,-6,-5), (0,-4,-13), ( 1,-4, 4), (0,0,-2)),
    (( 14, 3, 1), (10, 5,7), (1, 1,-7), ( 0,-5,-5), (-2,-5,-5), (2,-4,-11), ( 1,-3, 3), (0,0,-6)),
    (( 23, 1, 0), ( 7, 3,7), (2, 3,-7), ( 3,-5,-6), ( 0,-4,-3), (1,-4,-11), ( 1,-3, 4), (0,0, 1)),
    ((-18,12, 0), (15, 7,9), (5,-1,-9), ( 2,-4,-5), (-2,-5,-5), (1,-3,-10), ( 1,-3, 4), (0,0, 5)),
    ((-11, 8, 0), (16, 7,8), (4, 0,-8), ( 2,-5,-6), (-2,-6,-4), (0,-4,-11), ( 1,-4, 5), (0,0,-1)),
    (( 13, 3,-1), (10, 5,7), (1, 1,-7), ( 0,-5,-5), ( 0,-5,-4), (2,-4,-10), ( 1,-3, 4), (0,0,-4)),
    (( 23, 2, 0), ( 8, 3,7), (2, 3,-7), ( 3,-5,-6), ( 0,-4,-3), (1,-4,-12), ( 1,-3, 4), (0,0, 2)),
)

DESIGN = {
    "orc": {
        "name": "负重行进",
        "support": .65, "lift": 57, "hips": (-45, 47), "lanes": (-33, 34),
        "drop": (33, 40), "sole": 1.2,
        "keys": (*ORC_FIRST, ORC_FIRST[0]),
        "pivot": {"pelvis": (618, 744), "chest": (623, 651), "head": (659, 345),
                  "shoulder_near": (452, 395), "shoulder_far": (797, 409)},
        "masks": {
            "head": [(0,0),(1253,0),(1253,350),(834,349),(791,354),(758,373),(717,381),(693,371),
                     (661,352),(630,343),(617,320),(609,292),(590,272),(573,251),(558,242),(0,238)],
            "pelvis": [(0,651),(408,629),(497,618),(548,634),(604,648),(661,650),(731,630),(1253,643),(1253,1253),(0,1253)],
            "shoulder_near": [(265,328),(385,298),(451,311),(511,345),(531,379),(511,419),(484,449),
                              (456,485),(430,534),(439,584),(260,603),(250,484)],
            "shoulder_far": [(795,345),(917,374),(945,599),(973,736),(771,708),(761,643),(758,592),
                             (765,541),(756,505),(770,470),(774,431)],
        }
    },
    "elf": {
        "name": "警戒探步",
        "support": .57, "lift": 63, "hips": (32, -33), "lanes": (25, -25), "drop": (30, 49), "sole": 1.05,
        "keys": (*ELF_FIRST, ELF_FIRST[0]),
        "pivot": {"pelvis": (575, 669), "chest": (591, 540), "head": (687, 264),
                  "shoulder_near": (522, 325), "shoulder_far": (746, 350)},
        "masks": {
            "head": [(0,0),(1253,0),(1253,280),(832,279),(790,289),(747,281),(714,282),(687,299),
                     (661,288),(641,267),(628,241),(622,228),(592,223),(0,219)],
            "pelvis": [(0,538),(451,533),(492,534),(541,548),(584,557),(640,552),(691,546),(1253,548),
                       (1253,1253),(0,1253)],
            "shoulder_near": [(421,287),(500,271),(550,289),(576,317),(569,350),(553,385),(530,421),
                              (503,449),(487,487),(429,486),(402,501),(398,390)],
            "shoulder_far": [(743,282),(838,312),(848,489),(769,516),(737,485),(709,468),(687,436),
                             (697,405),(717,374),(725,343)],
        }
    },
}


def track_at(keys, frame):
    """Ease pose spacing within each authored interval."""
    for i, end in enumerate(PHASES[1:]):
        if frame <= end:
            start = PHASES[i]
            t = smooth((frame - start) / (end - start))
            return {name: tuple(a + (b-a)*t for a,b in zip(keys[i][j], keys[i+1][j]))
                    for j,name in enumerate(CHANNELS)}
    raise ValueError(frame)


def authored_foot(phase, role, support, stride, lift):
    if phase < support:
        weight = phase / support
        if role == "orc":
            roll = -8*(1 - smooth(weight/.22)) + 13*smooth((weight-.69)/.31)
        else:
            roll = 6*(1 - smooth(weight/.31)) + 11*smooth((weight-.7)/.3)
        return stride*(.5-weight), 0, roll, True
    u = (phase-support)/(1-support)
    tangent = -stride*(1-support)/support
    x = stride*(smooth(u)-.5)+tangent*(2*u**3-3*u**2+u)
    if role == "orc":
        height = lift*math.sin(math.pi*u)**1.38
        roll = 13-21*smooth(u)
    else:
        height = lift*math.sin(math.pi*u)**1.58
        roll = 11 - 16*math.sin(math.pi*u) - 5*smooth(u)
    return x, height, roll, False


class Study(CORE["WalkingModel"]):
    def __init__(self, root, role, config, catalog):
        design = DESIGN[role]
        super().__init__(root, config, design, catalog)
        self.role = role
        self.design = design
        self.stride = DISTANCE * design["support"] / self.zoom
        self.upper = self.dissect()

    def dissect(self):
        """Split body card at the belt, neck and shoulders with painted overlap."""
        original = self.art.images["travel_body"]
        pos = self.art.parts["travel_body"]["position"]
        full = Image.new("RGBA", (1254, 1254))
        full.paste(original, tuple(pos))
        occupied = Image.new("L", full.size)
        custom = {}
        definitions = self.design["masks"]
        for name, points in definitions.items():
            mask = BASE["poly_mask"](full.size, points)
            picked = ImageChops.subtract(mask, occupied)
            occupied = ImageChops.lighter(occupied, picked)
            padded = picked.filter(ImageFilter.MaxFilter(19))
            cut = BASE["visible"](full, padded)
            crop = BASE["opaque_box"](cut, 9)
            if not crop:
                raise ValueError(f"{self.role}: empty {name}")
            custom[name] = (clean_cutout(cut.crop(crop)), crop[:2])
        chest = BASE["visible"](full, ImageChops.invert(occupied.filter(ImageFilter.MinFilter(19))))
        bbox = BASE["opaque_box"](chest, 9)
        custom["chest"] = (clean_cutout(chest.crop(bbox)), bbox[:2])
        return custom

    def leg(self, side, t, pelvis):
        part = self.parts[side]
        idx = part["idx"]
        oldhip, oldknee, oldankle = part["joints"]
        phase = (t + (.5 if side == "far" else 0)) % 1
        d = self.design
        dx,lift,roll,planted=authored_foot(phase,self.role,d["support"],self.stride,d["lift"])
        rot = rotation(roll-part["level"])
        contour = part["foot"] @ rot[:2,:2].T
        sole = contour[np.argmax(contour[:,1])]
        depth = d["sole"]/self.zoom * (1 if side == "near" else -1)
        ankle = np.array([self.config["body_x"]+d["lanes"][idx]+dx-part["sole_center"],
                          self.config["ground"]+depth-lift-sole[1]])
        hip = point(pelvis, (self.config["body_x"]+d["hips"][idx],oldhip[1]+d["drop"][idx]))
        knee = CORE["knee_forward"](hip, ankle, part["lengths"])
        transforms = (segment_matrix(oldhip,oldknee,hip,knee),segment_matrix(oldknee,oldankle,knee,ankle),
                      offset(*ankle)@rot@offset(*(-oldankle)))
        metadata = {"planted":planted, "contact":rounded(point(self.stage,ankle+sole)),
                    "ankle":rounded(point(self.stage,ankle))}
        return zip(("thigh","shin","boot"),(hip,knee,ankle),transforms),metadata

    def frame(self, number):
        channels = track_at(self.design["keys"], number)
        pivot = self.design["pivot"]
        pelvis = move_about(pivot["pelvis"],*channels["pelvis"])
        chest = pelvis @ move_about(pivot["chest"],*channels["chest"])
        head = chest @ move_about(pivot["head"],*channels["head"])
        canvas = Image.new("RGBA", SIZE)
        joints, contacts = {}, {}
        def paint(name, matrix):
            art,pos = self.upper[name]
            BASE["raster_layer"](canvas, art, self.stage @ matrix @ offset(*pos))
            joints["study_"+name] = rounded(point(self.stage@matrix,pivot[name]))
        for side in ("far","near"):
            regions, contacts[side] = self.leg(side, number/FRAMES, pelvis)
            for region, joint, matrix in regions:
                key = f"travel_{side}_{region}"
                self.art.part(canvas,key,self.stage@matrix)
                joints[key] = rounded(point(self.stage,joint))
        paint("pelvis",pelvis)
        for side,source in (("far","travel_front_arm"),("near","travel_rear_arm")):
            if side == "near":
                if "travel_braid" in self.art.parts:
                    glue = head @ move_about(self.art.parts["travel_braid"]["pivot"], *channels["braid"])
                    self.art.part(canvas,"travel_braid",self.stage@glue)
                    joints["travel_braid"] = rounded(point(self.stage@glue,self.art.parts["travel_braid"]["pivot"]))
                paint("chest",chest)
                paint("head",head)
            shoulder = "shoulder_"+side
            arm = chest @ move_about(pivot[shoulder], *channels[shoulder])
            paint(shoulder,arm)
            wrist_pivot=self.art.parts[source]["pivot"]
            wrist=arm @ move_about(wrist_pivot,*channels["wrist_"+side])
            self.art.part(canvas,source,self.stage@wrist)
            joints[source] = rounded(point(self.stage@wrist,wrist_pivot))
        return canvas, joints, contacts


def loaded_config():
    return json.loads((HERE/"travel-rigs.json").read_text(encoding="utf-8-sig"))


def make_clips():
    results={}
    for role, settings in loaded_config().items():
        root=SHOTS/settings["folder"]
        catalog=CORE["read_data"](root)
        model=Study(root,role,settings["travel"],catalog)
        frames=[]
        for i in range(FRAMES):
            try:
                frames.append(model.frame(i))
            except ValueError as error:
                raise ValueError(f"{role}: frame {i}: {error}") from error
        results[role]=(root,model,catalog,frames)
    return results


def font(size):
    return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",size)


def flat(image):
    mask=image.getchannel("A")
    color=Image.new("RGBA",image.size,"#141119")
    color.putalpha(mask)
    return color


def contact_sheet(results):
    board = Image.new("RGBA", (1124,674), "#cbbfb7")
    draw = ImageDraw.Draw(board)
    draw.text((27,19),"同一速度下的两种步态",font=font(26),fill="#2e2530")
    for j,title in enumerate(("接地","承重","过步","蹬离")):
        draw.text((193+229*j,66),title,font=font(19),fill="#3b2c39")
    for row,role in enumerate(("orc","elf")):
        _,model,_,frames=results[role]
        py=90+285*row
        draw.rounded_rectangle((17,py,1105,py+266),7,fill="#ddd3c9")
        draw.text((29,py+15),model.design["name"],font=font(17),fill="#362b36")
        for j,n in enumerate((0,3,7,11)):
            sprite=flat(frames[n][0])
            view=sprite.crop((72,68,375,345)).resize((219,201),Image.Resampling.LANCZOS)
            board.alpha_composite(view,(153+229*j,py+27))
        draw.line((151,py+227,1069,py+227),fill="#a09089",width=2)
        note="脚跟落地后，肩才压下去" if role=="orc" else "刀收身侧，视线先稳住"
        draw.text((29,py+238),note,font=font(13),fill="#584654")
    board.convert("RGB").save(HERE/"walk-study-poses.png")


def compare_gif(results):
    width,height=784,390
    panel=Image.new("RGB", (width,height), "#27232c")
    dr=ImageDraw.Draw(panel)
    for i,(role,title) in enumerate((("orc","兽人 · 负重行进"),("elf","暗精灵 · 警戒探步"))):
        px=9+391*i
        dr.rounded_rectangle((px,9,px+375,380),8,fill="#342d39")
        dr.text((px+15,20),title,font=font(20),fill="#eee0c8")
        dr.text((px+15,348),f"同速预览 · 每循环前进 {DISTANCE:g} px",font=font(13),fill="#bfb1bf")
        dr.line((px+13,322,px+360,322),fill="#756476",width=1)
    frames=[]
    for n in range(FRAMES):
        page=panel.copy()
        draw=ImageDraw.Draw(page)
        for i,role in enumerate(("orc","elf")):
            _,_,_,sprites=results[role]
            tile=sprites[n][0].crop((67,51,393,350)).resize((302,277),Image.Resampling.LANCZOS)
            px=49+391*i
            page.paste(tile,(px,60),tile)
            x_shift=n*DISTANCE/FRAMES*.926
            # Fixed spacing and matching speed highlight foot contact.
            for k in range(-1,9):
                x=round(24+391*i+(k*DISTANCE*.926-x_shift))
                if 26+391*i<x<370+391*i:
                    draw.line((x,324,x-5,330),fill="#5b4a60",width=1)
        frames.append(page)
    sample=Image.new("RGB",(width*4,height))
    for i,n in enumerate((0,3,7,14)):
        sample.paste(frames[n],(i*width,0))
    palette=sample.quantize(colors=192)
    frame_list=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    delays=[round((i+1)*100/FPS)*10-round(i*100/FPS)*10 for i in range(FRAMES)]
    frame_list[0].save(HERE/"walk-performance-study.gif",save_all=True,append_images=frame_list[1:],
                       duration=delays,loop=0,disposal=1,optimize=True)


def integrate(results):
    for role,(root,model,catalog,sequence) in results.items():
        section=root/"walk-study"
        section.mkdir(exist_ok=True)
        links={
            "study_pelvis": (None,"步态试作 · 骨盆"),
            "study_chest": ("study_pelvis","步态试作 · 胸廓"),
            "study_head": ("study_chest","步态试作 · 头颈"),
            "study_shoulder_far": ("study_chest","步态试作 · 远肩"),
            "study_shoulder_near": ("study_chest","步态试作 · 近肩"),
        }
        for piece,(parent,title) in links.items():
            name=piece.removeprefix("study_")
            art,pos=model.upper[name]
            part_path=f"walk-study/{piece}.png"
            art.save(root/part_path)
            catalog["parts"][piece]={"label":title,"parent":parent,"path":part_path,
                                     "position":list(pos),"size":list(art.size),"pivot":list(model.design["pivot"][name])}
            if piece not in catalog["partOrder"]:
                catalog["partOrder"].append(piece)
            catalog.setdefault("partNames",{})[piece]=title

        sheet=Image.new("RGBA",(8*SIZE[0],math.ceil(FRAMES/8)*SIZE[1]))
        tiles,poses,contact=[],[],[]
        for i,(image,joints,support) in enumerate(sequence):
            x,y=i%8*SIZE[0],i//8*SIZE[1]
            sheet.paste(image,(x,y))
            tiles.append([x,y,*SIZE])
            poses.append(joints)
            contact.append(support)
        texture="walk-study/walk-atlas.png"
        sheet.save(root/texture,optimize=True)
        atlas_path="walk-study/walk-atlas.json"
        atlas={
            "animation":"walk_study","texture":texture,"fps":FPS,"loop":True,"image_size":list(sheet.size),
            "frames_xywh":tiles,"anchor_in_frame":list(ANCHOR),"joint_positions":poses,
            "joint_parents":{"travel_near_thigh":"study_pelvis","travel_far_thigh":"study_pelvis",
                              "travel_front_arm":"study_shoulder_far","travel_rear_arm":"study_shoulder_near",
                              "travel_braid":"study_head"},
            "events":[{"event":eid,"frame":f,"time":round(f/FPS,4)} for f,eid in ((0,"step_near"),(14,"step_far"))],
            "locomotion":{"stance_fraction":model.design["support"],"travel_pixels_per_cycle":DISTANCE,
                          "ground_y_by_side":{"near":ANCHOR[1]+model.design["sole"],"far":ANCHOR[1]-model.design["sole"]},
                          "contacts_by_frame":contact},
        }
        dump(root/atlas_path,atlas)
        motion_path="walk-study/author-keys.json"
        dump(root/motion_path,{"phase_frames":PHASES,"channels":CHANNELS,"definition":model.design})
        preview="walk-study/walk.webp"
        images=[row[0] for row in sequence]
        delays=[round((i+1)*1000/FPS)-round(i*1000/FPS) for i in range(FRAMES)]
        images[0].save(root/preview,save_all=True,append_images=images[1:],duration=delays,loop=0,quality=87,method=3)
        thumb="walk-study/walk-thumb.png"
        images[3].save(root/thumb)
        old=next(item for item in catalog["clips"] if item["id"]=="walk")
        compare={**old,"id":"walk_study"}
        compare.pop("previous",None)
        label="行走试做 · "+model.design["name"]
        entry={"id":"walk_study","name":label,"category":"动作试做","atlas":atlas,"atlasPath":atlas_path,
               "motionPath":motion_path,"webp":preview,"thumbnail":thumb,
               "marks":[(0,"接地"),(3,"承重"),(7,"过步"),(11,"蹬离"),(14,"另一脚接地"),(21,"另一脚过步")],
               "previous":compare}
        catalog["clips"]=[item for item in catalog["clips"] if item["id"]!="walk_study"]
        order=next(i for i,item in enumerate(catalog["clips"]) if item["id"]=="walk")
        catalog["clips"].insert(order+1,entry)
        (root/"viewer-data.js").write_text("window.CHARACTER_VIEWER_DATA = "+json.dumps(catalog,ensure_ascii=False,separators=(",",":"))+";\n",encoding="utf-8")
        dump(root/"actions-index.json",[{k:v for k,v in item.items() if k not in ("atlas","previous")} for item in catalog["clips"]])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--preview-only",action="store_true")
    args=parser.parse_args()
    results=make_clips()
    contact_sheet(results)
    compare_gif(results)
    if not args.preview_only:
        integrate(results)


if __name__=="__main__":
    main()

