import bpy, math, random, json, sys, time
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'renders'; R.mkdir(exist_ok=True)
random.seed(77)
MODE=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'blockout'
S=bpy.context.scene

def material(name,color,rough=.7,noise=0,bump=.04,metal=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    n=m.node_tree.nodes; l=m.node_tree.links; p=n.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metal
    if noise:
        tex=n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=noise; tex.inputs['Detail'].default_value=4
        ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.2
        ramp.color_ramp.elements[0].color=(*(c*.45 for c in color),1)
        ramp.color_ramp.elements[1].position=.8; ramp.color_ramp.elements[1].color=(*(min(c*1.35,1) for c in color),1)
        l.new(tex.outputs['Fac'],ramp.inputs[0]); l.new(ramp.outputs[0],p.inputs['Base Color'])
        b=n.new('ShaderNodeBump'); b.inputs['Strength'].default_value=.3; b.inputs['Distance'].default_value=bump
        l.new(tex.outputs['Fac'],b.inputs['Height']); l.new(b.outputs[0],p.inputs['Normal'])
    return m

def assign(o,m):
    if m:o.data.materials.append(m)
    return o

def cube(name,loc,size,mat,bevel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=name
    o.dimensions=size; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    assign(o,mat)
    if bevel:
        b=o.modifiers.new('Soft worn edges','BEVEL');b.width=bevel;b.segments=3
        o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
    return o

def ell(name,loc,scale,mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=loc)
    o=bpy.context.object;o.name=name;o.scale=scale;assign(o,mat)
    for p in o.data.polygons:p.use_smooth=True
    return o

def cylinder(name,loc,radius,depth,mat,verts=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=loc)
    o=bpy.context.object;o.name=name;assign(o,mat)
    b=o.modifiers.new('Round edges','BEVEL');b.width=.012;b.segments=3
    o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
    return o

def curve(name,points,radius,mat,closed=False):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=radius;d.bevel_resolution=2
    p=d.splines.new('POLY');p.points.add(len(points)-1)
    for q,v in zip(p.points,points):q.co=(*v,1)
    p.use_cyclic_u=closed
    o=bpy.data.objects.new(name,d);S.collection.objects.link(o);assign(o,mat);return o

def beam(name,a,b,radius,mat):
    a,b=Vector(a),Vector(b);o=cylinder(name,(a+b)/2,radius,(b-a).length,mat,16)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o

def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def camera(name,loc,target,lens=38,ortho=None):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);S.collection.objects.link(o);o.location=loc;aim(o,target)
    d.lens=lens;d.clip_start=.05;d.clip_end=100
    if ortho:d.type='ORTHO';d.ortho_scale=ortho
    return o
def light(name,kind,loc,energy,color,size,target):
    d=bpy.data.lights.new(name,kind);d.energy=energy;d.color=color
    if kind=='AREA':d.shape='DISK';d.size=size
    if kind=='SPOT':d.spot_size=size;d.spot_blend=.25;d.shadow_soft_size=.08
    o=bpy.data.objects.new(name,d);S.collection.objects.link(o);o.location=loc;aim(o,target);return o

def render(path,cam,w=1080,h=720,samples=40):
    S.camera=cam;S.render.resolution_x=w;S.render.resolution_y=h;S.render.resolution_percentage=100
    S.cycles.samples=samples;S.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    print('RENDER_DONE',str(path),flush=True)

def configure():
    S.render.engine='CYCLES';S.cycles.use_denoising=True;S.cycles.preview_samples=16
    S.cycles.max_bounces=6;S.cycles.diffuse_bounces=3;S.cycles.glossy_bounces=3;S.cycles.transparent_max_bounces=4
    S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGB'
    S.render.threads_mode='FIXED';S.render.threads=6
    S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast';S.view_settings.exposure=0
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for d in prefs.devices:d.use=d.type!='CPU'
        if any(d.use for d in prefs.devices):S.cycles.device='GPU'
        print('DEVICES',[(d.name,d.type,d.use) for d in prefs.devices],flush=True)
    except Exception as e:print('GPU_FALLBACK',str(e),flush=True)

def bear(name,x,y,z,scale,fur,eye,black,stitch):
    # Each bear is a reusable local assembly. Feet rest at the supplied support height.
    root=bpy.data.objects.new(name,None);S.collection.objects.link(root);root.location=(x,y,z);root.scale=(scale,)*3
    parts=[]
    def e(n,loc,sc,m):o=ell(name+'_'+n,loc,sc,m);parts.append(o);return o
    e('body',(0,.025,.38),(.27,.21,.34),fur)
    e('belly',(0,-.155,.35),(.21,.075,.24),fur)
    for side in [-1,1]:
        e('foot',(side*.205,-.16,.105),(.135,.20,.105),fur)
        arm=e('arm',(side*.29,-.015,.38),(.095,.115,.235),fur);arm.rotation_euler[1]=side*.25
    hroot=bpy.data.objects.new(name+'_head_tilt',None);S.collection.objects.link(hroot);hroot.location=(0,0,.77);parts.append(hroot)
    hparts=[]
    def he(n,loc,sc,m):o=ell(name+'_'+n,loc,sc,m);o.parent=hroot;hparts.append(o);return o
    he('head',(0,0,0),(.29,.235,.26),fur)
    for side in [-1,1]:
        he('ear',(side*.24,.01,.22),(.105,.075,.105),fur)
        he('inner_ear',(side*.24,-.06,.22),(.052,.018,.055),stitch)
        he('eye',(side*.13,-.207,.025 if side==-1 else -.015),(.084,.045,.093),eye)
        he('pupil',(side*.13+.012,-.25,.025 if side==-1 else -.015),(.038,.015,.045),black)
        he('eye_glint',(side*.13,-.265,.042 if side==-1 else .002),(.012,.007,.014),eye)
    he('muzzle',(0,-.215,-.105),(.12,.07,.085),fur)
    he('nose',(0,-.282,-.075),(.055,.025,.035),black)
    hroot.rotation_euler[1]=.19;hroot.rotation_euler[2]=-.07
    for pts in [[(-.085,-.281,-.14),(0,-.29,-.17),(.08,-.281,-.14)],[(0,-.285,-.1),(0,-.29,-.165)]]:
        o=curve(name+'_mouth',pts,.008,stitch);o.parent=hroot
    pts=[(.02*math.sin(i),-.215,.15+i*.055) for i in range(8)]
    o=curve(name+'_belly_seam',pts,.004,stitch);parts.append(o)
    for i in range(7):
        zz=.18+i*.05;o=curve(name+'_seam_stitch',[(-.025,-.221,zz),(.025,-.221,zz+.018)],.003,stitch);parts.append(o)
    for o in parts:o.parent=root
    return root

def shelf(name,x,y,w,d,h,wood,back,upper=False):
    cube(name+'_back',(x,y+d/2-.025,h/2),(w,.05,h),back)
    for sx in [-1,1]:cube(name+'_side',(x+sx*(w/2-.045),y,h/2),(.09,d,h),wood)
    for zz in [.07,h*.49,h-.055]:cube(name+'_shelf',(x,y,zz),(w+.08,d+.06,.1),wood)
    cube(name+'_divider',(x,y,h*.49),(.06,d,h-.2),wood)
    if upper:
        for sx in [-1,1]:
            xx=x+sx*w*.24
            cube(name+'_door',(xx,y-d/2-.03,.55),(w*.46,.07,.95),wood)
            knob=ell(name+'_handle',(xx-sx*.1,y-d/2-.09,.63),(.035,.035,.06),M['brass'])
        for zz in [1.5,2.05,2.7]:cube(name+'_upper_shelf',(x,y,zz),(w+.03,d,.065),wood)
    cube(name+'_top',(x,y,h+.015),(w+.14,d+.1,.12),wood,.035)

def drawing(name,x,z,w,h,kind,angle=0,y=2.535):
    root=bpy.data.objects.new(name,None);S.collection.objects.link(root);root.location=(x,y,z);root.rotation_euler[1]=angle
    p=cube(name+'_paper',(0,0,0),(w,.009,h),M['paper'],.002);p.parent=root
    def line(pts,r=.004,mat=None):
        o=curve(name+'_ink',[(a,-.009,b) for a,b in pts],r,mat or M['ink']);o.parent=root
    if kind=='eye':
        for k in [.85,1]:line([(w*.43*math.cos(t),h*.23*math.sin(t)*k) for t in [i*math.tau/60 for i in range(61)]],.005)
        for rr in [w*.07,w*.13]:line([(rr*math.cos(i*math.tau/40),rr*math.sin(i*math.tau/40)) for i in range(41)],.005)
        for i in range(12):
            xx=-w*.4+i*w*.073;line([(xx,h*.3),(xx+.02,h*.4)],.003)
    elif kind=='spiral':
        line([((.005+i*.00055)*math.cos(i*.18),(.005+i*.00055)*math.sin(i*.18)) for i in range(270)],.005,M['rust'])
    elif kind=='person':
        line([(w*.12*math.cos(i*math.tau/30),h*.23+h*.12*math.sin(i*math.tau/30)) for i in range(31)],.006)
        for pts in [[(0,h*.1),(0,-h*.15)],[(-w*.35,0),(0,h*.08),(w*.32,-h*.05)],[(-w*.25,-h*.4),(0,-h*.12),(w*.25,-h*.4)]]:line(pts,.009)
    else:
        for k in range(5):
            pts=[(random.uniform(-w*.42,w*.42),random.uniform(-h*.43,h*.43)) for i in range(12)]
            line(pts,.0035,M['rust'] if kind=='red' else None)
    return root

def build():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    global M
    M={
        'wall':material('Cold peeling plaster',(.14,.19,.19),.92,4,.06),
        'floor':material('Worn green floorboards',(.13,.17,.15),.8,9,.025),
        'wood':material('Old dark walnut',(.19,.095,.053),.58,7,.014),
        'lightwood':material('Stool worn ochre wood',(.44,.27,.15),.72,9,.02),
        'back':material('Deep shelf shadow',(.055,.065,.06),.85,5,.02),
        'rug':material('Coarse woven rug',(.12,.115,.075),.96,170,.016),
        'rugedge':material('Rug border faded thread',(.29,.25,.15),.95,130,.01),
        'fur':material('Teddy distressed ochre cloth',(.28,.215,.115),.92,100,.018),
        'fur_dark':material('Teddy dark cloth',(.105,.105,.073),.94,90,.016),
        'eye':material('Teddy cloudy white eyes',(.7,.71,.61),.4),
        'black':material('Pupils and seams',(.009,.013,.013),.6),
        'paper':material('Aged paper',(.57,.57,.45),.92,24,.004),
        'ink':material('Charcoal blue scribbles',(.025,.065,.075),.95),
        'rust':material('Faded red scribbles',(.25,.045,.036),.9),
        'brass':material('Tarnished brass',(.34,.24,.08),.5,8,.006,.6),
        'red':material('Toy red',(.43,.035,.022),.55,12,.005),
        'yellow':material('Toy mustard',(.55,.43,.035),.6,12,.004),
        'blue':material('Toy faded teal',(.035,.14,.16),.72,16,.007),
        'coat':material('Foreground dark coat',(.011,.02,.025),.95,30,.007),
        'peel':material('Exposed plaster',(.35,.37,.31),.98,15,.025)
    }
    # Room shell. The front is a camera opening; the right wall has a designed light aperture.
    cube('Floor support',(0,-.95,-.09),(7.2,7.1,.16),M['floor'])
    for ix in range(12):
        for iy in range(6):
            x=-3.3+ix*.6;y=-3.9+iy*1.25+(ix%2)*.31
            if y<2.6:cube('Floor plank',(x,y,-.012),(.59,1.23,.035),M['floor'],.005)
    cube('Back wall',(0,2.65,1.85),(7.4,.16,3.7),M['wall'],.005)
    cube('Left wall',(-3.65,-.95,1.85),(.16,7.1,3.7),M['wall'],.005)
    cube('Right wall back',(3.65,1.95,1.85),(.16,1.4,3.7),M['wall'],.005)
    cube('Right wall front',(3.65,-3.15,1.85),(.16,2.7,3.7),M['wall'],.005)
    cube('Right window sill wall',(3.65,-.55,.55),(.16,2.8,1.1),M['wall'],.005)
    cube('Right window lintel',(3.65,-.55,3.5),(.16,2.8,.4),M['wall'],.005)
    cube('Ceiling',(0,-.95,3.79),(7.4,7.1,.16),M['wall'])
    for z in [.09,.2]:cube('Back skirting',(0,2.53,z),(7.2,.09,.07),M['back'])
    # Peeling wall islands: actual irregular shapes, not a brightness interpretation of terrain.
    for x in [-2.8,-1.5,.7,1.4,2.9]:
        verts=[(x+.38*math.cos(i*math.tau/13)*random.uniform(.7,1.2),2.557,.5+.35*math.sin(i*math.tau/13)*random.uniform(.7,1.2)) for i in range(13)]
        d=bpy.data.meshes.new('peeling plaster');d.from_pydata(verts,[],[list(range(13))]);o=bpy.data.objects.new('Peeling plaster patch',d);S.collection.objects.link(o);assign(o,M['peel'])
    # Rug and stitched border.
    cube('Rug',(0,-.65,.014),(5.3,3.35,.028),M['rug'],.025)
    for inset,rad in [(.1,.012),(.22,.006),(.25,.004)]:
        x=2.65-inset;y0=-2.325+inset;y1=1.025-inset
        curve('Rug woven border',[(-x,y0,.033),(x,y0,.033),(x,y1,.033),(-x,y1,.033)],rad,M['rugedge'],True)
    # Table.
    cylinder('Round table top',(-.35,0,.895),1,.09,M['wood'],96)
    cylinder('Table apron',(-.35,0,.805),.87,.13,M['wood'],64)
    for dx,dy in [(-.64,-.52),(.64,-.52),(-.64,.52),(.64,.52)]:cube('Table leg',(-.35+dx,dy,.4),(.105,.105,.8),M['wood'],.025)
    # Chair at left, back toward positive Y.
    cx,cy=-1.65,-.15
    cube('Chair seat',(cx,cy,.63),(.66,.64,.085),M['lightwood'])
    for dx in [-.26,.26]:
        for dy in [-.24,.24]:cube('Chair leg',(cx+dx,cy+dy,.32),(.065,.065,.64),M['wood'])
        cube('Chair back post',(cx+dx,cy+.24,1.01),(.065,.065,.9),M['lightwood'])
    cube('Chair backrest',(cx,cy+.24,1.33),(.58,.07,.32),M['lightwood'])
    # Stool built as a shell with side openings.
    sx,sy=1.35,-.4
    cube('Stool top',(sx,sy,.635),(.73,.66,.09),M['lightwood'],.06)
    for side in [-1,1]:
        for yy in [-.23,.23]:
            leg=cube('Stool tapered leg',(sx+side*.26,sy+yy,.30),(.13,.13,.60),M['lightwood'],.035);leg.rotation_euler[1]=-side*.08
        cube('Stool side bridge',(sx+side*.26,sy,.43),(.14,.5,.18),M['lightwood'],.045)
    # Cabinets.
    shelf('Left low cabinet',-2.6,1.65,1.7,.65,1.3,M['wood'],M['back'])
    shelf('Right tall cabinet',2.65,1.65,1.65,.72,3.35,M['wood'],M['back'],True)
    # Small books and toy blocks in the shelves.
    for k in range(8):
        x=-3.21+k*.11
        cube('Old book left',(x,1.4,.81),(.08,.28,.25+random.random()*.08),M['paper'] if k%3==0 else M['back'],.004)
    for i in range(9):
        xx=2.1+(i%3)*.4;zz=1.66+(i//3)*.55
        if i%2==0:cube('Right shelf book',(xx,1.45,zz),(.16,.25,.24),M['paper'],.005)
        else:
            o=cylinder('Right shelf toy ring',(xx,1.43,zz),.11,.04,M['red'] if i%3 else M['blue']);o.rotation_euler[0]=math.pi/2
    for i,(xx,zz) in enumerate([(-2.5,1.43),(-2.65,1.69),(-2.55,1.95)]):
        cube('Stacked alphabet block',(xx,1.62,zz),(.25,.25,.25),[M['yellow'],M['blue'],M['red']][i])
    # Table and floor characters.
    bear('HeroBear',-.25,.18,.94,.92,M['fur'],M['eye'],M['black'],M['black'])
    bear('LeftFloorBear',-2.65,.9,.0,.66,M['fur_dark'],M['eye'],M['black'],M['black'])
    bear('RightFloorBear',2.42,.53,.0,.64,M['fur_dark'],M['eye'],M['black'],M['black'])
    # Toy robot leaning on the chair.
    cube('Toy body',(-1.69,-.44,.61),(.28,.22,.36),M['blue'],.04)
    head=cube('Toy yellow head',(-1.74,-.44,.92),(.33,.28,.25),M['yellow'],.03);head.rotation_euler[1]=-.25
    ell('Toy red ball',(-1.57,-.62,.51),(.18,.16,.15),M['red'])
    for dx in [-.13,.13]:beam('Toy dangling leg',(-1.69+dx,-.44,.45),(-1.7+dx,-.5,.14),.035,M['yellow'])
    # Foreground figure. Original silhouette-inspired placeholder with a separate coat and tall cap.
    fx,fy=-.55,-2.05
    bpy.ops.mesh.primitive_cone_add(vertices=8,radius1=.17,radius2=.08,depth=.48,location=(fx,fy,.47));o=bpy.context.object;o.name='Foreground coat';assign(o,M['coat'])
    ell('Foreground head',(fx,fy,.77),(.085,.075,.095),M['coat'])
    cap=cube('Foreground tall cap',(fx,fy,.96),(.18,.15,.32),M['coat'],.008);cap.rotation_euler[1]=-.12
    for dx in [-.07,.07]:
        beam('Foreground leg',(fx+dx,fy,.26),(fx+dx,fy-.015,.055),.025,M['coat'])
        ell('Foreground shoe',(fx+dx,fy-.04,.045),(.045,.08,.035),M['coat'])
        beam('Foreground arm',(fx+dx,fy,.6),(fx+dx*2,fy-.04,.36),.025,M['coat'])
    # Drawings are editable 2D curve geometry mounted on paper, not inferred real geometry.
    posters=[(-1.25,2.05,.44,.42,'eye',-.15),(-.56,2.5,.46,.48,'scribble',.08),(.07,2.82,.42,.61,'person',-.15),(.65,2.68,.31,.42,'person',.3),
      (-.65,2.0,.4,.53,'person',.3),(-.08,2.12,.53,.4,'eye',.1),(.47,1.79,.48,.42,'eye',-.1),(.99,1.58,.39,.55,'person',.25),
      (-1.05,1.49,.38,.49,'scribble',.25),(-.32,1.61,.37,.35,'spiral',-.08),(1.57,1.42,.36,.46,'red',-.12),(1.86,2.48,.31,.48,'spiral',-.15)]
    for i,args in enumerate(posters):drawing('Wall drawing %02d'%i,*args)
    # Loose paper and crayons on the table.
    for i in range(3):
        o=cube('Table paper',(-.75+i*.12,-.3+i*.06,.947),(.4,.26,.003),M['paper'],.001);o.rotation_euler[2]=i*.27
    for i in range(5):
        o=cylinder('Crayon',(-.29+i*.065,-.42,.961),.013,.1,[M['yellow'],M['red'],M['blue']][i%3],12);o.rotation_euler[1]=math.pi/2
    # Pendant shade and bulb.
    beam('Pendant cord',(-.25,.1,3.7),(-.25,.1,3.52),.012,M['black'])
    bpy.ops.mesh.primitive_cone_add(vertices=64,radius1=.42,radius2=.13,depth=.13,location=(-.25,.1,3.48));o=bpy.context.object;o.name='Pendant metal shade';assign(o,M['back'])
    em=material('Pendant glowing underside',(.8,.77,.57),.5);p=em.node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(1,.86,.58,1);p.inputs['Emission Strength'].default_value=3
    cylinder('Pendant glowing disc',(-.25,.1,3.412),.39,.008,em)
    # Two lighting rigs allow geometry and atmosphere to be reviewed separately.
    light('Diagnostic key','AREA',(0,-3.5,4.5),650,(.8,.88,1),5,(0,.7,.8))
    light('Diagnostic fill','AREA',(-3,-.5,3),220,(1,.9,.75),3,(0,1,1))
    light('Pendant pool','AREA',(-.25,.1,3.36),150,(1,.84,.6),.55,(-.25,.1,0))
    light('Window shaft','AREA',(4.8,-.9,3.5),1100,(.67,.82,1),1.0,(-1,1.7,.4))
    spot=light('Ceiling light cone','SPOT',(-.25,.1,3.38),95,(.85,.9,1),1.25,(-.25,.1,0));spot.data.spot_blend=.55
    light('Camera subtle bounce','AREA',(0,-4,2),28,(.38,.52,.7),4,(0,.5,1))
    vol=bpy.data.materials.new('Thin bounded haze');vol.use_nodes=True;n=vol.node_tree.nodes;n.clear();v=n.new('ShaderNodeVolumePrincipled');v.inputs['Density'].default_value=.018;v.inputs['Color'].default_value=(.65,.72,.78,1);v.inputs['Anisotropy'].default_value=.2;out=n.new('ShaderNodeOutputMaterial');vol.node_tree.links.new(v.outputs['Volume'],out.inputs['Volume'])
    cube('Atmosphere volume',(0,-.9,1.85),(7.18,7.05,3.66),vol,0)
    S.world.use_nodes=True;S.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.07,.12,.2,1);S.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.14
    camera('Hero',(.3,-9.5,3.1),(.3,.4,1.36),35)
    camera('Left',(-2.8,-4,2.2),(0,.7,1.1),27)
    camera('Right',(2.8,-4,2.2),(0,.7,1.1),27)
    camera('Reverse',(0,2.1,2.7),(0,-.9,.9),25)
    camera('Overhead',(0,-.65,10),(0,-.65,0),35,8.4)
    camera('TableDetail',(-1.65,-2.9,2.0),(-.25,.1,1.4),45)
    camera('LeftCorner',(-3.2,.2,1.9),(.2,.6,1.2),24)
    camera('RightCorner',(3.2,.1,2.0),(-.3,.7,1.2),24)
    # Composition revision 02: wider furniture framing, taller unseen shell, higher pendant.
    for o in list(S.objects):
        if o.parent or o.type in {'CAMERA','LIGHT'}:continue
        if o.name.startswith(('Right tall cabinet','Right shelf','RightFloorBear')):o.location.x+=.6
        elif o.name.startswith(('Left low cabinet','Old book left','Stacked alphabet','LeftFloorBear')):o.location.x-=.6
        if o.name.startswith(('Pendant','Ceiling light cone')):o.location.z+=.8
    for n in ['Left wall','Right wall back','Right wall front','Right window sill wall','Right window lintel']:
        o=bpy.data.objects[n];o.location.x+=.6 if o.location.x>0 else -.6
    for n in ['Back wall','Ceiling','Floor support']:
        o=bpy.data.objects[n];o.dimensions.x+=1.2
    for n in ['Left wall','Right wall back','Right wall front','Back wall']:
        o=bpy.data.objects[n];o.dimensions.z+=1;o.location.z+=.5
    bpy.data.objects['Ceiling'].location.z+=1
    bpy.data.objects['Pendant pool'].location.z+=.8
    bpy.data.objects['Ceiling light cone'].location.z+=.8
    configure()
    S['Reference']='reference.png';S['Scale']='Designed meters, not a survey';S['Limitations']='Single-image interpretation; procedural character approximations; unseen areas designed; no game-engine validation'
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'scene.blend'))

def set_rig(diagnostic=False):
    for o in S.objects:
        if o.type=='LIGHT':
            isdiag=o.name.startswith('Diagnostic');o.hide_render=(not diagnostic if isdiag else diagnostic)
    bpy.data.objects['Atmosphere volume'].hide_render=diagnostic
    S.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.3 if diagnostic else .14

if MODE=='blockout':
    build();set_rig(True)
    clay=material('Diagnostic clay',(.47,.51,.52),.82)
    S.view_layers[0].material_override=clay
    render(R/'03_blockout.png',bpy.data.objects['Hero'],960,640,24)
    S.view_layers[0].material_override=None
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'03_blockout.blend'))
elif MODE=='materials':
    configure();set_rig(True);S.view_layers[0].material_override=None
    render(R/'04_materials.png',bpy.data.objects['Hero'],1080,720,40)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'04_materials.blend'))
elif MODE=='final':
    configure();set_rig(False);S.view_layers[0].material_override=None
    # Art-direction revision: reduce broad side wash, preserve a central light pool.
    S.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.035
    S.view_settings.exposure=-.25
    bpy.data.objects['Window shaft'].data.energy=160
    bpy.data.objects['Window shaft'].location=(4.8,-.6,2.8)
    aim(bpy.data.objects['Window shaft'],(.5,2.55,.7))
    bpy.data.objects['Pendant pool'].data.energy=850
    bpy.data.objects['Pendant pool'].data.color=(.78,.87,1)
    bpy.data.objects['Ceiling light cone'].data.energy=550
    bpy.data.objects['Ceiling light cone'].data.spot_size=.9
    bpy.data.objects['Camera subtle bounce'].data.energy=5
    if 'Directed window accent' not in bpy.data.objects:
        light('Directed window accent','SPOT',(4.8,-.6,2.8),1800,(.7,.83,1),.8,(.5,2.56,.65))
    bpy.data.objects['Directed window accent'].data.energy=1800
    if 'Stool hollow panel left' not in bpy.data.objects:
        wood=bpy.data.materials['Stool worn ochre wood']
        for side in [-1,1]:
            panel=cube('Stool hollow panel '+('left' if side<0 else 'right'),(1.35+side*.26,-.4,.3),(.12,.56,.57),wood,.035)
            cutter=cylinder('Temporary stool hole',(1.35+side*.26,-.4,.31),.145,.4,None,48);cutter.rotation_euler[1]=math.pi/2
            bpy.context.view_layer.objects.active=panel
            mod=panel.modifiers.new('Through opening','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
            bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    # Compositor vignette is explicitly a presentation effect, never used for geometry evidence.
    S.use_nodes=True;n=S.node_tree.nodes;n.clear();l=S.node_tree.links
    rl=n.new('CompositorNodeRLayers');el=n.new('CompositorNodeEllipseMask');el.width=.88;el.height=.9
    blur=n.new('CompositorNodeBlur');blur.filter_type='GAUSS';blur.size_x=380;blur.size_y=280
    l.new(el.outputs['Mask'],blur.inputs['Image'])
    ramp=n.new('CompositorNodeValToRGB');ramp.color_ramp.elements[0].color=(.23,.23,.23,1);ramp.color_ramp.elements[1].color=(1,1,1,1)
    l.new(blur.outputs['Image'],ramp.inputs[0]);mix=n.new('CompositorNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
    l.new(rl.outputs['Image'],mix.inputs[1]);l.new(ramp.outputs[0],mix.inputs[2]);out=n.new('CompositorNodeComposite');l.new(mix.outputs[0],out.inputs[0])
    render(R/'05_final.png',bpy.data.objects['Hero'],1440,960,80)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'scene.blend'))
elif MODE=='views':
    configure();set_rig(False)
    manifest={}
    for label,camname in [('hero','Hero'),('left','Left'),('right','Right'),('reverse','Reverse'),('overhead','Overhead'),('table_detail','TableDetail'),('left_corner','LeftCorner'),('right_corner','RightCorner')]:
        cam=bpy.data.objects[camname];changed=[]
        if label=='overhead':
            for name in ['Ceiling','Pendant metal shade','Pendant glowing disc','Atmosphere volume']:
                o=bpy.data.objects[name];changed.append((o,o.hide_render));o.hide_render=True
            for o in S.objects:
                if o.type=='LIGHT' and o.name.startswith('Diagnostic'):changed.append((o,o.hide_render));o.hide_render=False
        render(R/('view_'+label+'.png'),cam,960,640,40)
        for o,v in changed:o.hide_render=v
        manifest[label]={'camera':camname,'location':list(cam.location),'rotation_euler':list(cam.rotation_euler),'lens_mm':cam.data.lens,'orthographic':cam.data.type=='ORTHO','cutaway':label=='overhead'}
    (ROOT/'cameras.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    S.camera=bpy.data.objects['Hero'];bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'scene.blend'))
elif MODE=='verify':
    configure();missing=[i.filepath for i in bpy.data.images if i.source=='FILE' and not i.packed_file and i.filepath and not Path(bpy.path.abspath(i.filepath)).exists()]
    measured={}
    for prefix in ['Round table top','Rug','Left low cabinet','Right tall cabinet','Stool','HeroBear','Foreground','Pendant']:
        pts=[]
        for o in S.objects:
            if o.type=='MESH' and o.name.startswith(prefix):pts.extend([o.matrix_world@Vector(v) for v in o.bound_box])
        if pts:measured[prefix]={'min':[min(v[i] for v in pts) for i in range(3)],'max':[max(v[i] for v in pts) for i in range(3)]}
    (ROOT/'scene_as_built.json').write_text(json.dumps({'units':'designed meters, not measured','source':'scene.blend object bounds; excludes modifier-expanded bounds','bounds':measured},indent=2),encoding='utf8')
    render(R/'07_reopen_check.png',bpy.data.objects['Hero'],720,480,24)
    result={'blender':bpy.app.version_string,'object_count':len(S.objects),'mesh_objects':sum(o.type=='MESH' for o in S.objects),'cameras':[o.name for o in S.objects if o.type=='CAMERA'],'missing_external_images':missing,'stage_renders':{p.name:p.stat().st_size for p in R.glob('*.png')},'known_limits':['Designed scale, not measured','Programmatic shape and material interpretation, not original game assets','Hidden areas completed by design','No target engine import, collisions or gameplay performance validated'],'verified':['Reopened scene.blend in a separate Blender process','Rendered the reopened project at 720x480','Enumerated cameras and missing texture dependencies']}
    (ROOT/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf8');print('VALIDATION',json.dumps(result),flush=True)
print('STAGE_COMPLETE',MODE,flush=True)
