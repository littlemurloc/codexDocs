"""Visual-review corrections to this NEW rebuild only; run on 03_lighting.blend."""
import bpy,sys,math,json,random
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
# Import helpers without executing any construction branch.
saved=list(sys.argv);sys.argv=['blender','--','helpers']
code=(ROOT/'source/rebuild.py').read_text(encoding='utf-8-sig').split("if MODE=='base':base()")[0]
exec(compile(code,str(ROOT/'source/rebuild.py'),'exec'))
sys.argv=saved
config();random.seed(11011)

# The old volume boundary produced a horizontal band in the foreground; place
# the camera inside an extended low-density volume and its bottom below ground.
v=bpy.data.objects['P15 haze volume'];v.location=(0,-1,3);v.dimensions=(18,26,8)
v.data.materials[0].node_tree.nodes.get('Principled Volume').inputs['Density'].default_value=.007
key=bpy.data.objects['P15 right slanted key'];key.data.type='SPOT';key.data.energy=6500;key.data.spot_size=1.15;key.data.spot_blend=.08;key.data.shadow_soft_size=.045
key.location=(6.5,4.6,3.3);target=Vector((1.1,6.28,.30));aim(key,target)
direction=(target-key.location).normalized()
right=direction.cross(Vector((0,0,1))).normalized();up=right.cross(direction).normalized()
angle=math.radians(18);u=right*math.cos(angle)+up*math.sin(angle);v=-right*math.sin(angle)+up*math.cos(angle)
centre=key.location+direction*2.0
dark=bpy.data.materials['Shelf recessed boards']
for a,b,c,d in [(-1.5,-.52,-1.5,1.5),(.52,1.5,-1.5,1.5),(-.52,.52,-1.5,-.24),(-.52,.52,.24,1.5)]:
    pts=[tuple(centre+u*x+v*y) for x,y in [(a,c),(b,c),(b,d),(a,d)]]
    o=mesh('P15 offscreen window light mask',pts,[(0,1,2,3)],dark)
    # Shadow casting architecture is hidden from direct/secondary glossy camera rays.
    o.visible_camera=False;o.visible_glossy=False
bpy.data.objects['P15 pendant downward pool'].data.energy=1800
bpy.data.objects['P15 narrow visible cone'].data.energy=550
bpy.data.objects['P15 narrow visible cone'].data.spot_size=1.05
bpy.data.objects['P15 eye and paper bounce'].data.energy=60
lamp('P15 wall soft indirect bounce','AREA',(-.8,3.9,3.3),95,(.65,.78,.95),2.7,(-.8,6.28,2.7))

# Tone-correct only the sampled paper albedo; no generated/repainted drawings.
m=bpy.data.materials['P08 actual reference paper artwork'];n=m.node_tree.nodes;l=m.node_tree.links
tex=next(x for x in n if x.type=='TEX_IMAGE');p=n.get('Principled BSDF')
mix=n.new('ShaderNodeMixRGB');mix.name='Reference paper mild white balance';mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(1.75,1.65,1.4,1)
l.new(tex.outputs['Color'],mix.inputs[1]);l.new(mix.outputs[0],p.inputs['Base Color'])
for name,corners in [('right upper sheet',[(1805,307),(1850,300),(1861,473),(1811,478)]),('right lower sheet',[(1746,548),(1803,541),(1816,625),(1764,635)])]:
    verts=[tuple(at_y(x/1920,y/1280,6.27)) for x,y in corners]
    o=mesh('P08 '+name,verts,[(0,1,2,3)],m);uv=o.data.uv_layers.new()
    for lp in o.data.loops:
        x,y=corners[lp.vertex_index];uv.data[lp.index].uv=(x/1920,1-y/1280)

# Non-identical side characters: the left rag-doll's bowed head and long arms
# are distinct from the right seated bear; do not reuse the hero's bright gaze.
head=bpy.data.objects['P11 Left slumped bear head pose'];head.rotation_euler.x=.65
for o in bpy.data.objects:
    if o.name.startswith('P11 Left slumped bear') and 'porcelain eye' in o.name:
        o.data.materials.clear();o.data.materials.append(bpy.data.materials['P11 dark ragged fabric'])
    if o.name.startswith('P11 Left slumped bear') and 'upper floppy arm' in o.name:o.scale.z=1.18

# Correct block support and front-face drawing position after the depth change.
for o in list(S.objects):
    if o.name.startswith('P06 patterned block') or o.name.startswith('P06 block'):o.location.x+=.42
# Books were missing from upper cubbies in the first review.
for i in range(5):
    o=box('P06 retained horizontal book',(-4.0,4.92,1.13+i*.065),(.58,.34,.055),bpy.data.materials['P12 aged drawing paper'] if i%2 else dark,.004)

# Add irregular seam paths to the hero forehead and sleeves; preserve dark cloth
# instead of increasing eye highlights to make it appear more "finished".
herohead=bpy.data.objects['P01 Hero bear head pose']
for x in [-.10,.075]:
    pts=[(x+.008*math.sin(i*1.8),-.216,.20-i*.025) for i in range(5)]
    o=line('P01 forehead old seam',pts,.0025,bpy.data.materials['Dark recessed seams']);o.parent=herohead

bpy.data.objects['P01 Hero bear'].location.x-=.12
bpy.data.objects['P15 eye and paper bounce'].data.color=(.83,.85,.83)
bpy.data.objects['P15 pendant downward pool'].data.color=(.86,.91,1)
bpy.data.objects['P15 right slanted key'].data.color=(.90,.94,1)
lamp('P15 floor reflected pool','AREA',(-.3,-.1,3.7),160,(.8,.86,.9),1.0,(-.8,-.3,0))
right_eye=mat('P11 subdued right eyes',(.24,.26,.23),.6)
for o in list(S.objects):
    if o.name.startswith('P11 Right seated bear') and 'porcelain eye' in o.name:
        o.data.materials.clear();o.data.materials.append(right_eye)

# Stronger edge falloff, retaining the 3D scene's actual light and shadows.
for node in S.node_tree.nodes:
    if node.type=='ELLIPSEMASK':node.width=.88;node.height=.80
    if node.type=='VALTORGB':node.color_ramp.elements[0].color=(.065,.09,.14,1)
    if node.type=='MIX_RGB':node.inputs[0].default_value=.92
S.view_settings.exposure=.10
render('04_review_v5.png',1200,48)
save('04_review.blend')

# Actual independent diagnostic camera to inspect the hero asset's silhouette.
p=json.loads((ROOT/'scene_spec.json').read_text())['positions']['bear']
cam('BearDetail',(p[0]-1.05,p[1]-2.6,2.22),(p[0],p[1],1.75),65)
haze=bpy.data.objects['P15 haze volume'];haze.hide_render=True
render('04_bear_detail.png',960,32,'BearDetail')
haze.hide_render=False;S.camera=bpy.data.objects['Hero'];save('04_review.blend')



