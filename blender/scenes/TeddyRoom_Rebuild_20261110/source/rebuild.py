import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'renders'
MODE=sys.argv[sys.argv.index('--')+1]
S=bpy.context.scene
random.seed(11010)

def mat(name, color, rough=.8, noise=0, depth=.01, metal=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True; m.use_fake_user=True; m.diffuse_color=(*color,1)
    n=m.node_tree.nodes; n.clear(); l=m.node_tree.links
    p=n.new('ShaderNodeBsdfPrincipled'); p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
    out=n.new('ShaderNodeOutputMaterial'); l.new(p.outputs['BSDF'],out.inputs['Surface'])
    if noise:
        coord=n.new('ShaderNodeTexCoord'); tex=n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=noise; tex.inputs['Detail'].default_value=5
        l.new(coord.outputs['Generated'],tex.inputs['Vector'])
        ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.24; ramp.color_ramp.elements[1].position=.78
        ramp.color_ramp.elements[0].color=(*(c*.30 for c in color),1)
        ramp.color_ramp.elements[1].color=(*(min(c*1.35,1) for c in color),1)
        l.new(tex.outputs['Fac'],ramp.inputs[0]); l.new(ramp.outputs[0],p.inputs['Base Color'])
        fine=n.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value=noise*18; fine.inputs['Detail'].default_value=3
        l.new(coord.outputs['Generated'],fine.inputs['Vector']); bump=n.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value=.36; bump.inputs['Distance'].default_value=depth
        l.new(fine.outputs['Fac'],bump.inputs['Height']); l.new(bump.outputs[0],p.inputs['Normal'])
    return m

def materials():
    global M
    M={
      'wall':mat('P14 cold grey-green plaster',(.13,.18,.19),.93,5,.018),
      'floor':mat('P14 broad concrete floor',(.12,.145,.125),.85,5,.012),
      'wood':mat('P02 dark weathered walnut',(.24,.105,.055),.66,5,.006),
      'edge':mat('P02 rubbed wood edges',(.36,.20,.115),.7,12,.005),
      'stool':mat('P04 faded ochre stool',(.51,.30,.17),.8,8,.007),
      'shadow':mat('Shelf recessed boards',(.055,.064,.06),.9,5,.008),
      'fur':mat('P01 mottled old hessian plush',(.16,.12,.070),.96,6,.006),
      'fur2':mat('P11 dark ragged fabric',(.10,.105,.075),.97,7,.009),
      'pad':mat('Worn bear paw pads',(.19,.16,.10),.98,16,.008),
      'thread':mat('Dark recessed seams',(.033,.031,.022),.94),
      'stitch':mat('Old linen stitches',(.30,.265,.18),.96),
      'socket':mat('Sunken brown sockets',(.022,.021,.015),.93),
      'eye':mat('P01 dirty porcelain eye',(.67,.69,.64),.34),
      'pupil':mat('P01 dark pupils',(.006,.009,.01),.27),
      'coat':mat('P05 charcoal coat cloth',(.008,.014,.019),.97,10,.003),
      'hat':mat('P05 dark worn hat',(.018,.026,.028),.93,12,.004),
      'rug':mat('P10 coarse faded rug',(.10,.102,.075),.98,120,.008),
      'border':mat('P10 straw rug border',(.27,.23,.145),.97,100,.004),
      'red':mat('P03 muted red toy',(.41,.032,.017),.64,10,.003),
      'yellow':mat('P03 faded yellow toy',(.50,.43,.045),.8,8,.005),
      'green':mat('P03 toy green cloth',(.16,.21,.065),.94,20,.005),
      'blue':mat('P06 blue block',(.025,.105,.13),.78,7,.003),
      'paper':mat('P12 aged drawing paper',(.67,.66,.53),.96,18,.002),
      'brass':mat('P07 aged brass knobs',(.23,.16,.055),.5,4,.003,.6),
      'peel':mat('P14 exposed pale plaster',(.36,.40,.36),.99,12,.012),
      'box':mat('P13 faded cardboard',(.16,.17,.12),.98,9,.006),
    }
    for key in ['fur','fur2','rug','coat']:
        M[key].node_tree.nodes.get('Principled BSDF').inputs['Sheen Weight'].default_value=.22

def mesh(name,verts,faces,m=None):
    d=bpy.data.meshes.new(name); d.from_pydata(verts,[],faces); d.update()
    o=bpy.data.objects.new(name,d); S.collection.objects.link(o)
    if m:o.data.materials.append(m)
    return o

def box(name,loc,size,m,bevel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=name; o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if m:o.data.materials.append(m)
    if bevel:
        b=o.modifiers.new('Worn rounded arris','BEVEL'); b.width=bevel; b.segments=3
        o.modifiers.new('Corner normals','WEIGHTED_NORMAL')
    return o

def ell(name,loc,scale,m,power=1,detail=36):
    verts=[]; faces=[]; rings=24
    def sp(v):return math.copysign(abs(v)**power,v)
    for j in range(rings+1):
        a=math.pi*j/rings
        for i in range(detail):
            b=math.tau*i/detail
            rr=1+.016*math.sin(b*7+a*9)+.008*math.sin(b*13-a*12)
            verts.append((sp(math.sin(a)*math.cos(b))*scale[0]*rr,sp(math.sin(a)*math.sin(b))*scale[1]*rr,sp(math.cos(a))*scale[2]*rr))
    for j in range(rings):
        for i in range(detail):
            a=j*detail+i;b=j*detail+(i+1)%detail;faces.append((a,b,b+detail,a+detail))
    o=mesh(name,verts,faces,m);o.location=loc
    for p in o.data.polygons:p.use_smooth=True
    return o

def line(name,pts,r,m,closed=False):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=r;d.bevel_resolution=2
    sp=d.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,v in zip(sp.points,pts):p.co=(*v,1)
    sp.use_cyclic_u=closed
    o=bpy.data.objects.new(name,d);S.collection.objects.link(o)
    if m:d.materials.append(m)
    return o

def cyl(name,loc,r,h,m,verts=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=h,location=loc);o=bpy.context.object;o.name=name
    if m:o.data.materials.append(m)
    mod=o.modifiers.new('Soft rim','BEVEL');mod.width=.012;mod.segments=3;o.modifiers.new('Normals','WEIGHTED_NORMAL')
    return o

def rod(name,a,b,r,m):
    a,b=Vector(a),Vector(b);o=cyl(name,(a+b)/2,r,(b-a).length,m,16);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
def cam(name,loc,target,lens=45):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);S.collection.objects.link(o);o.location=loc;d.lens=lens;d.sensor_width=36;aim(o,target);return o
def lamp(name,kind,loc,energy,color,size,target):
    d=bpy.data.lights.new(name,kind);d.energy=energy;d.color=color
    if kind=='AREA':d.shape='DISK';d.size=size
    elif kind=='SPOT':d.spot_size=size;d.spot_blend=.35;d.shadow_soft_size=.07
    o=bpy.data.objects.new(name,d);S.collection.objects.link(o);o.location=loc;aim(o,target);return o

def ray(u,v):
    c=bpy.data.objects['Hero'];q=c.rotation_euler.to_quaternion()
    return c.location.copy(),q@Vector(((u-.5)*36/c.data.lens,(.5-v)*24/c.data.lens,-1))
def at_z(u,v,z):
    a,d=ray(u,v);return a+d*((z-a.z)/d.z)
def at_y(u,v,y):
    a,d=ray(u,v);return a+d*((y-a.y)/d.y)

def config():
    S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=True;S.cycles.preview_samples=32
    S.cycles.max_bounces=7;S.cycles.volume_bounces=1;S.render.threads_mode='FIXED';S.render.threads=6
    S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGB'
    S.render.resolution_x=1440;S.render.resolution_y=960;S.render.resolution_percentage=100
    S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast'
    S.world.use_nodes=True
    try:
        p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
        for d in p.devices:d.use=d.type=='OPTIX'
        if any(d.use for d in p.devices):S.cycles.device='GPU'
    except Exception as e:print(e)

def save(name):
    for m in bpy.data.materials:m.use_fake_user=True
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/name))
def render(name,w=960,samples=32,camera='Hero'):
    S.camera=bpy.data.objects[camera];S.render.resolution_x=w;S.render.resolution_y=round(w*2/3);S.render.resolution_percentage=100
    S.cycles.samples=samples;S.render.filepath=str(R/name);bpy.ops.render.render(write_still=True)
    print('RENDER_DONE',name,flush=True)

def get_spec():return json.loads((ROOT/'scene_spec.json').read_text(encoding='utf8'))

def base():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.materials):bpy.data.materials.remove(block)
    config();materials()
    c=cam('Hero',(0,-12,3.1),(0,0,2.0),45);S.camera=c;bpy.context.view_layer.update()
    points={
      'table':list(at_z(.435,.611,1.10)),
      'bear':list(at_z(.468,.610,1.155)),
      'chair':list(at_z(.286,.735,.03)),
      'stool':list(at_z(.592,.762,.03)),
      'figure':list(at_z(.407,.819,.03)),
      'left_bear':list(at_z(.192,.668,.0)),
      'right_bear':list(at_z(.755,.750,.0)),
    }
    spec={'units':'design meters, not measured','axes':'X right, Y toward wall, Z up','camera':{'location':list(c.location),'rotation':list(c.rotation_euler),'lens':45,'ratio':'3:2'},'positions':points,'source':'fresh factory-startup; no previous blend loaded','assumptions':['Planar floor','Offscreen right light aperture','Unseen geometry designed']}
    (ROOT/'scene_spec.json').write_text(json.dumps(spec,indent=2),encoding='utf8')
    box('P14 floor',(0,0,-.10),(14,14,.2),M['floor'],.005)
    box('P14 back wall',(0,6.4,3.2),(15,.18,6.4),M['wall'],.004)
    box('P14 left wall',(-7.4,1,3.2),(.15,10.8,6.4),M['wall'],.004)
    box('P14 ceiling',(0,1,6.5),(15,10.8,.16),M['wall'])
    box('P14 skirting',(0,6.28,.11),(15,.09,.16),M['shadow'])
    # Only proxies in this checkpoint. All assets are constructed in subsequent stage.
    t=Vector(points['table']);cyl('Proxy table',(t.x,t.y,1.045),1,.11,M['wood'])
    b=Vector(points['bear']);ell('Proxy bear',(b.x,b.y,1.68),(.36,.25,.53),M['fur'])
    a=Vector(points['chair']);box('Proxy chair',(a.x,a.y,.88),(.58,.6,1.70),M['stool'])
    a=Vector(points['stool']);box('Proxy stool',(a.x,a.y,.51),(.78,.68,.96),M['stool'])
    a=Vector(points['figure']);box('Proxy figure',(a.x,a.y,.65),(.27,.23,1.22),M['coat'])
    box('Proxy left cabinet',(-5.05,5.15,1.02),(3.3,.85,2.04),M['wood'])
    box('Proxy right cabinet',(4.05,4.1,2.30),(2.05,.95,4.6),M['wood'])
    lp=at_y(.443,.062,.2);cyl('Proxy pendant',lp,.43,.035,M['paper'])
    rug=[at_z(u,v,.027) for u,v in [(.098,.812),(.771,.816),(.681,.685),(.204,.685)]]
    mesh('P10 rug body',[tuple(p) for p in rug],[(0,1,2,3)],M['rug'])
    S.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.18
    lamp('Diagnostic softbox','AREA',(0,-4,5),1000,(.83,.89,1),5,(0,1,1))
    save('01_blockout.blend');clay=mat('Diagnostic clay',(.43,.48,.49),.83);S.view_layers[0].material_override=clay
    render('01_blockout.png',960,24);S.view_layers[0].material_override=None
    print(json.dumps(spec),flush=True)

def paper_material():
    m=bpy.data.materials.new('P08 actual reference paper artwork');m.use_nodes=True;m.use_fake_user=True
    n=m.node_tree.nodes;p=n.get('Principled BSDF');p.inputs['Roughness'].default_value=.97
    im=bpy.data.images.load(str(ROOT/'reference.png'));im.name='Reference artwork source';im.pack()
    tex=n.new('ShaderNodeTexImage');tex.image=im;m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    return m

# Four observed corners in 1920x1280 display coordinates; artwork is never reinvented.
POSTERS=[
 ('left eye',[(550,414),(646,439),(625,503),(533,477)]),
 ('upper scribble',[(684,323),(788,311),(797,389),(694,402)]),
 ('tall figure',[(835,245),(919,262),(888,383),(812,366)]),
 ('small figure',[(958,282),(1008,267),(1032,339),(982,357)]),
 ('large eye',[(770,393),(891,388),(902,479),(773,486)]),
 ('slanted marks',[(675,440),(733,412),(787,515),(716,544)]),
 ('spiral',[(744,525),(832,506),(846,584),(764,597)]),
 ('right eye',[(888,465),(996,467),(988,548),(877,536)]),
 ('right figure',[(1018,501),(1098,540),(1062,622),(977,589)]),
 ('lower scribble',[(585,563),(650,528),(691,619),(624,645)]),
 ('red scribble',[(1098,557),(1162,554),(1166,652),(1102,644)]),
 ('hanging sketch',[(1208,304),(1257,320),(1237,391),(1181,376)]),
 ('far left sheet',[(15,352),(55,378),(52,506),(13,493)]),
]

def artwork():
    pm=paper_material()
    for name,corners in POSTERS:
        verts=[tuple(at_y(x/1920,y/1280,6.285)) for x,y in corners]
        o=mesh('P08 paper '+name,verts,[(0,1,2,3)],pm)
        uv=o.data.uv_layers.new(name='Reference paper UV')
        for loop in o.data.loops:
            x,y=corners[loop.vertex_index];uv.data[loop.index].uv=(x/1920,1-y/1280)
        mod=o.modifiers.new('Paper thickness','SOLIDIFY');mod.thickness=.002
    # Thin cable carries the separate right-hand sheet.
    p=at_y(.634,.24,6.26);line('P08 sketch cord',[(p.x,6.26,6.5),tuple(p)],.003,M['shadow'])

def cabinet(name,x,y,w,d,h,upper=False):
    box(name+' recessed back',(x,y+d*.43,h*.5),(w,.08,h),M['shadow'])
    for side in [-1,1]:box(name+' side',(x+side*(w/2-.045),y,h/2),(.095,d,h),M['wood'])
    levels=[.07,1.02,2.04] if not upper else [.09,1.57,2.30,3.04,3.79,4.28]
    for z in levels:
        if z<=h+.05:box(name+' shelf',(x,y,z),(w+.06,d+.08,.09),M['wood'])
    box(name+' top moulding',(x,y,h),(w+.19,d+.16,.14),M['edge'],.025)
    box(name+' top lip',(x,y,h+.055),(w+.21,d+.17,.035),M['wood'],.008)
    if upper:
        for side in [-1,1]:
            xx=x+side*w*.245
            box(name+' lower door',(xx,y-d/2-.04,.71),(w*.475,.075,1.20),M['wood'],.018)
            for zz in [.19,1.22]:box(name+' door frame',(xx,y-d/2-.085,zz),(w*.43,.028,.055),M['edge'],.006)
            ell(name+' round knob',(x+side*.12,y-d/2-.13,.84),(.05,.035,.065),M['brass'])
        box(name+' upper divider',(x+.12,y,2.72),(.075,d,2.55),M['wood'])
        for i,(xx,zz) in enumerate([(x-.45,1.52),(x+.42,1.55),(x-.34,2.23),(x+.45,2.98),(x-.5,3.72)]):
            if i in [1,3]:
                o=cyl(name+' toy ring',(xx,y-d/2+.13,zz+.13),.13,.07,M['red'] if i==3 else M['blue']);o.rotation_euler[0]=math.pi/2
                o=cyl(name+' ring centre',(xx,y-d/2+.085,zz+.13),.055,.01,M['yellow']);o.rotation_euler[0]=math.pi/2
            else:
                for j in range(3):box(name+' small stacked book',(xx,y-d/2+.19,zz+.035+j*.055),(.25,.30,.045),M['paper'] if j==1 else M['shadow'],.004)
    else:
        for dx in [-.45,.48]:box(name+' vertical divider',(x+dx,y,1.02),(.075,d,1.95),M['wood'])
        for j in range(5):box(name+' horizontal books',(x+.88,y-d/2+.2,.79+j*.055),(.48,.38,.05),M['paper'] if j%2 else M['shadow'],.005)
        o=cyl(name+' rolled paper',(x-.19,y-d/2+.22,.9),.105,.27,M['paper']);o.rotation_euler[0]=math.pi/2
        for xx in [x-.84,x-.73]:box(name+' dark leaning book',(xx,y-d/2+.25,.32),(.10,.36,.46),M['shadow'],.004)
    # Irregular wear along important horizontal edges, kept subtle.
    for k in range(38):
        xx=x+random.uniform(-w*.48,w*.48);zz=random.choice(levels)
        if zz>h:continue
        line(name+' edge scratch',[(xx,y-d/2-.052,zz+.035),(xx+random.uniform(.025,.11),y-d/2-.055,zz+.033)],.0018,M['edge'])

def teddy(name,loc,scale=1,dark=False,tilt=.25):
    root=bpy.data.objects.new(name,None);S.collection.objects.link(root);root.location=loc;root.scale=(scale,)*3
    cloth=M['fur2'] if dark else M['fur']
    def E(n,p,sc,m=cloth,power=1,parent=root):
        o=ell(name+' '+n,p,sc,m,power);o.parent=parent;return o
    E('pear body',(0,.035,.31),(.25,.19,.33),power=.91)
    E('sewn belly',(0,-.116,.28),(.22,.095,.255),M['pad'])
    # Limp arms and outward feet, rather than an upright waving toy.
    for side in [-1,1]:
        o=E('upper floppy arm',(side*.262,.002,.35),(.082,.105,.22));o.rotation_euler[1]=side*.20
        E('worn hand',(side*.29,-.085,.16),(.084,.105,.09))
        E('splayed foot',(side*.18,-.145,.095),(.125,.165,.10))
        E('foot felt',(side*.18,-.267,.105),(.087,.025,.078),M['pad'])
        # Bent seam around hand.
        q=line(name+' wrist seam',[(side*.28+.082*math.cos(a),-.09+.09*math.sin(a),.205) for a in [i*math.tau/40 for i in range(41)]],.003,M['thread']);q.parent=root
    head=bpy.data.objects.new(name+' head pose',None);S.collection.objects.link(head);head.parent=root;head.location=(.025,-.01,.73);head.rotation_euler=(.025,tilt,-.08)
    E('rounded square head',(0,0,0),(.285,.215,.255),cloth,.75,head)
    for side in [-1,1]:
        E('ear',(side*.245,.005,.23),(.105,.073,.105),cloth,1,head)
        E('dark ear hollow',(side*.245,-.061,.228),(.065,.018,.061),M['socket'],1,head)
        E('ear inner worn cloth',(side*.245,-.078,.216),(.042,.009,.035),M['pad'],1,head)
        x=side*.145;z=.01 if side==-1 else -.025
        r=.092 if side==-1 else .072
        E('deep eye socket',(x,-.193,z),(.115,.053,.125),M['socket'],1,head)
        E('uneven porcelain eye',(x,-.23,z),(r,.045,r*1.08),M['eye'],1,head)
        E('offcentre pupil',(x+.006,-.271,z-.004),(r*.49,.014,r*.58),M['pupil'],1,head)
        # No oversized cartoon catchlights.
    E('compressed snout',(-.015,-.197,-.135),(.145,.065,.075),cloth,.88,head)
    E('small dark nose',(-.05,-.26,-.097),(.046,.022,.03),M['socket'],.85,head)
    q=line(name+' crooked mouth',[(-.13,-.248,-.16),(-.075,-.266,-.177),(-.015,-.269,-.166),(.07,-.25,-.17)],.010,M['socket']);q.parent=head
    E('mouth inner cloth',(-.035,-.269,-.171),(.047,.007,.012),M['pad'],1,head)
    # Long tailoring seams follow the face and body surface.
    for pts,parent in [([(0,-.215,.245),(.025,-.232,.17),(.032,-.24,.09),(.01,-.237,0)],head),
                       ([(0,-.19,.53),(.015,-.209,.44),(-.005,-.215,.34),(.02,-.21,.22),(.00,-.18,.10)],root)]:
        q=line(name+' recessed tailor seam',pts,.004,M['thread']);q.parent=parent
        for j in range(len(pts)-1):
            a,b=Vector(pts[j]),Vector(pts[j+1])
            for t in [.2,.5,.8]:
                p=a.lerp(b,t);q=line(name+' cross stitch',[tuple(p+Vector((-.018,-.003,.007))),tuple(p+Vector((.018,-.003,-.007)))],.002,M['stitch']);q.parent=parent
    for k in range(5):
        z=.18+k*.064
        pts=[(.205*math.cos(a),-.11-.091*math.sin(a),z+.014*math.sin(a*3+k)) for a in [i*math.pi/30 for i in range(31)]]
        q=line(name+' belly cloth fold',pts,.0035,M['thread']);q.parent=root
    # Sparse short fibre silhouettes, generated as one curve datablock per bear.
    d=bpy.data.curves.new(name+' frayed fibres','CURVE');d.dimensions='3D';d.bevel_depth=.00065;d.bevel_resolution=0
    for k in range(700 if not dark else 250):
        a=random.uniform(0,math.tau);v=random.uniform(-.85,.85);rr=math.sqrt(1-v*v)
        normal=Vector((rr*math.cos(a),rr*math.sin(a),v));p=Vector((normal.x*.252,normal.y*.195+.035,normal.z*.325+.31))
        sp=d.splines.new('POLY');sp.points.add(1)
        for q,pt in zip(sp.points,[p,p+normal*random.uniform(.003,.009)]):q.co=(*pt,1)
    o=bpy.data.objects.new(name+' fibres',d);S.collection.objects.link(o);d.materials.append(cloth);o.parent=root
    return root

def stool(loc):
    x,y,_=loc;z0=.03;h=.92
    box('P04 rounded saddle top',(x,y,z0+h),(.82,.66,.13),M['stool'],.07)
    # Each panel has a through-hole; arches cut into all lower edges.
    for axis in [0,1]:
        for sign in [-1,1]:
            if axis==0:
                p=box('P04 pierced side panel',(x+sign*.30,y,z0+.435),(.13,.58,.83),M['stool'],.035)
                p.rotation_euler[1]=-sign*.07
                c=cyl('Temporary round opening',(x+sign*.30,y,z0+.53),.125,.45,None);c.rotation_euler[1]=math.pi/2
                arch=cyl('Temporary lower arch',(x+sign*.30,y,z0+.01),.155,.5,None);arch.rotation_euler[1]=math.pi/2
            else:
                p=box('P04 end panel',(x,y+sign*.255,z0+.435),(.59,.11,.83),M['stool'],.035)
                c=cyl('Temporary end opening',(x,y+sign*.255,z0+.53),.11,.45,None);c.rotation_euler[0]=math.pi/2
                arch=cyl('Temporary end arch',(x,y+sign*.255,z0+.01),.16,.5,None);arch.rotation_euler[0]=math.pi/2
            for cutter in [c,arch]:
                bpy.context.view_layer.objects.active=p;mod=p.modifiers.new('Visible through opening','BOOLEAN');mod.object=cutter;mod.operation='DIFFERENCE';bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)

def figure(loc):
    x,y,_=loc
    # Tailored coat with uneven silhouette and hem, not a rigid straight cone.
    verts=[];faces=[];N=24
    for j,(z,rx,ry) in enumerate([(.18,.13,.075),(.37,.14,.085),(.65,.095,.068),(.78,.085,.065)]):
        for i in range(N):
            a=math.tau*i/N;verts.append((x+rx*math.cos(a),y+ry*math.sin(a),z+(.025*math.sin(a*4) if j==0 else .008*math.cos(a*3))))
    for j in range(3):
        for i in range(N):faces.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
    o=mesh('P05 tailored long coat',verts,faces,M['coat']);mo=o.modifiers.new('Fabric thickness','SOLIDIFY');mo.thickness=.009
    for p in o.data.polygons:p.use_smooth=True
    for side in [-1,1]:
        rod('P05 sleeve',(x+side*.08,y,.72),(x+side*.15,y-.02,.43),.035,M['coat'])
        ell('P05 small hand',(x+side*.15,y-.03,.41),(.027,.027,.04),M['hat'])
    ell('P05 head',(x+.005,y,.86),(.067,.065,.075),M['hat'])
    verts=[];faces=[]
    for j,(z,xx,w,dep) in enumerate([(.86,.00,.095,.075),(.99,.025,.105,.075),(1.17,.04,.09,.065),(1.33,.025,.085,.055)]):
        verts.extend([(x+xx-w,y-dep,z),(x+xx+w,y-dep,z),(x+xx+w,y+dep,z),(x+xx-w,y+dep,z)])
    for j in range(3):
        for i in range(4):faces.append((j*4+i,j*4+(i+1)%4,(j+1)*4+(i+1)%4,(j+1)*4+i))
    faces.append((12,13,14,15));o=mesh('P05 crooked tall cloth hat',verts,faces,M['hat']);mod=o.modifiers.new('Soft hat corners','BEVEL');mod.width=.016;mod.segments=3
    line('P05 hat centre seam',[(x+.02,y-.079,.90),(x+.035,y-.079,1.10),(x+.025,y-.06,1.32)],.002,M['shadow'])
    for a,b in [((x-.045,y,.2),(x-.06,y+.035,.052)),((x+.045,y,.2),(x+.11,y-.045,.052))]:
        rod('P05 stocking',a,b,.025,M['coat']);ell('P05 walking shoe',(b[0]+.02,b[1]-.035,.04),(.058,.09,.033),M['hat'])

def details():
    config();materials();spec=get_spec();P={k:Vector(v) for k,v in spec['positions'].items()}
    for o in list(S.objects):
        if o.name.startswith('Proxy'):bpy.data.objects.remove(o,do_unlink=True)
    t=P['table'];cyl('P02 thin circular tabletop',(t.x,t.y,1.10),1,.09,M['wood'],128)
    cyl('P02 dark table apron',(t.x,t.y,1.005),.90,.13,M['shadow'],96)
    for dx,dy in [(-.66,-.49),(.66,-.49),(-.66,.49),(.66,.49)]:
        a=(t.x+dx,t.y+dy,1.03);b=(t.x+dx*1.09,t.y+dy*1.06,.03)
        o=rod('P02 slender wooden leg',a,b,.052,M['wood'])
    # An imperfect worn rim, with a visible nick near the front.
    line('P02 rubbed rim',[(t.x+1.002*math.cos(a),t.y+1.002*math.sin(a),1.128+.002*math.sin(a*11)) for a in [i*math.tau/200 for i in range(201)]],.007,M['edge'],True)
    for k in range(18):
        xx=t.x+random.uniform(-.85,.85);yy=t.y+random.uniform(-.30,.55)
        if (xx-t.x)**2+(yy-t.y)**2<.8:line('P02 surface grain',[(xx,yy,1.147),(xx+.08,yy+.008,1.148)],.0015,M['edge'])
    p=P['chair'];x,y=p.x,p.y
    box('P03 chair seat',(x,y,.64),(.63,.61,.085),M['stool'])
    for side in [-1,1]:
        for dy in [-.23,.23]:box('P03 chair leg',(x+side*.25,y+dy,.33),(.065,.065,.60),M['wood'],.012)
        box('P03 chair tall back post',(x+side*.25,y+.24,1.12),(.067,.068,1.08),M['stool'],.012)
        box('P03 chair side stretcher',(x+side*.25,y,.26),(.045,.48,.045),M['wood'],.009)
    box('P03 chair flat backrest',(x,y+.25,1.48),(.57,.075,.43),M['stool'],.015)
    box('P03 toy green torso',(x+.04,y-.13,.68),(.25,.2,.38),M['green'],.045)
    h=box('P03 toy tilted yellow head',(x-.08,y-.16,.98),(.33,.24,.28),M['yellow'],.035);h.rotation_euler=(.05,-.35,-.08)
    ell('P03 toy red body',(x+.12,y-.34,.56),(.19,.16,.15),M['red'])
    o=cyl('P03 toy yellow wheel',(x+.28,y-.42,.52),.13,.055,M['yellow']);o.rotation_euler[0]=math.pi/2
    o=cyl('P03 toy red wheel hub',(x+.28,y-.455,.52),.065,.02,M['red']);o.rotation_euler[0]=math.pi/2
    for side in [-1,1]:
        rod('P03 toy dangling limb',(x+side*.11,y-.15,.56),(x+side*.15,y-.17,.23),.032,M['green'])
        ell('P03 toy yellow hand',(x+side*.18,y-.28,.78),(.055,.045,.075),M['yellow'])
    stool(P['stool']);figure(P['figure'])
    teddy('P01 Hero bear',P['bear'],1,False,.27)
    teddy('P11 Left slumped bear',P['left_bear']+Vector((.1,-.8,0)),1.1,True,-.17)
    teddy('P11 Right seated bear',P['right_bear']+Vector((0,.30,0)),.95,True,-.10)
    cabinet('P06 left low cabinet',-5.05,5.15,3.3,.85,2.04)
    cabinet('P07 right cupboard',3.95,4.1,1.65,1.25,4.28,True)
    for i,(xx,zz,m) in enumerate([(-3.1,1.68,'yellow'),(-3.37,1.69,'red'),(-3.30,1.96,'blue'),(-3.18,2.23,'green')]):
        box('P06 patterned block',(xx,1.40,zz),(.27,.27,.27),M[m],.009)
        ring=[(xx+.087*math.cos(a),1.258,zz+.055*math.sin(a)) for a in [j*math.tau/40 for j in range(41)]]
        line('P06 block eye design',ring,.008,M['paper'],True);ell('P06 block pupil',(xx,1.246,zz),(.023,.006,.025),M['yellow'])
    # The block stack is supported by the rebuilt low cabinet, not floating in front.
    for o in list(S.objects):
        if o.name.startswith('P06 patterned block') or o.name.startswith('P06 block'):
            o.location+=Vector((-1.2,3.65,.54))
            # Curve coordinates are stored in world coordinates, so location is the offset.
    # Match the visible oblique sides of the stool and right cupboard.
    from mathutils import Matrix
    for prefix,centre,angle in [('P04',P['stool'],math.radians(-25)),('P07',Vector((3.95,4.1,0)),math.radians(-28))]:
        transform=Matrix.Translation(centre) @ Matrix.Rotation(angle,4,'Z') @ Matrix.Translation(-centre)
        for o in list(S.objects):
            if o.name.startswith(prefix):o.matrix_world=transform @ o.matrix_world
    for o in list(S.objects):
        if o.name.startswith('P03'):o.location.x-=.18
        if o.name.startswith('P05'):
            o.location.z*=.82
            if o.type=='MESH':
                for v in o.data.vertices:v.co.z*=.82
            elif o.type=='CURVE':
                for sp in o.data.splines:
                    for p in sp.points:p.co.z*=.82
    bpy.data.objects['P11 Left slumped bear head pose'].rotation_euler.x=.35
    artwork()
    # Paper lies on the actual tabletop and contains retained reference marks.
    pm=bpy.data.materials['P08 actual reference paper artwork']
    corners=[(724,762),(804,754),(855,784),(766,788)]
    verts=[tuple(at_z(x/1920,y/1280,1.152)) for x,y in corners];o=mesh('P12 original drawing on table',verts,[(0,1,2,3)],pm)
    uv=o.data.uv_layers.new()
    for lp in o.data.loops:
        x,y=corners[lp.vertex_index];uv.data[lp.index].uv=(x/1920,1-y/1280)
    p=at_z(.385,.613,1.166);o=cyl('P12 single red crayon',p,.018,.07,M['red'],16);o.rotation_euler=(.3,math.pi/2,.8)
    p=at_z(.45,.611,1.16)
    for i in range(4):o=cyl('P12 yellow short crayon',(p.x+i*.045,p.y,1.164),.013,.085,M['yellow'],12);o.rotation_euler[1]=math.pi/2
    # Rug edges follow the same projected physical plane, with multiple woven bands.
    base=bpy.data.objects['P10 rug body'];corners=[Vector(v.co) for v in base.data.vertices];centre=sum(corners,Vector())/4
    for factor,r in [(.982,.012),(.90,.006),(.884,.003),(.868,.003)]:
        pts=[]
        for i in range(4):
            a=centre+(corners[i]-centre)*factor;b=centre+(corners[(i+1)%4]-centre)*factor
            for j in range(35):
                p=a.lerp(b,j/35);p.z=.039+.006*math.sin(j*.7+i);pts.append(tuple(p))
        line('P10 faded woven border',pts,r,M['border'],True)
    # Floor joints: large quiet slabs instead of invented narrow floorboards.
    for xx in [-4.9,-1.2,2.3,5.4]:line('P14 faint floor joint',[(xx,-6,.004),(xx+.15,3,.004)],.004,M['shadow'])
    for yy in [-3.9,1.9]:line('P14 cross floor joint',[(-7,yy,.004),(7,yy,.004)],.003,M['shadow'])
    for xx in [-4.6,-1.2,.9,2.0,5.3]:line('P14 wall panel seam',[(xx,6.293,.25),(xx,6.293,5.5)],.003,M['shadow'])
    # Torn plaster regions restricted to the lower wall, not random oval blobs.
    for k,(x,w,h) in enumerate([(-1.2,.8,.51),(.1,.5,.50),(1.1,.7,.66),(2.05,.9,.75)]):
        pts=[]
        for i in range(28):
            a=i*math.tau/28;xx=x+w*.5*math.cos(a);zz=.48+h*.5*math.sin(a)
            zz+=random.uniform(-.085,.085);xx+=random.uniform(-.035,.035);pts.append((xx,6.292,zz))
        mesh('P14 torn peeling patch',pts,[tuple(range(28))],M['peel'])
    # Open cardboard box and stray dark shapes at the right edge.
    q=at_z(.89,.742,0);x,y=q.x,q.y
    for dx in [-.27,.27]:box('P13 open box side',(x+dx,y,.30),(.018,.53,.60),M['box'],.003)
    for dy in [-.25,.25]:box('P13 open box end',(x,y+dy,.30),(.55,.018,.60),M['box'],.003)
    flap=box('P13 raised box flap',(x+.33,y,.68),(.24,.53,.018),M['box'],.003);flap.rotation_euler[1]=-.5
    rod('P13 long discarded stick',(x-.12,y,.45),(x+.65,y+.38,1.0),.025,M['shadow'])
    # Hanging lamp profile is a genuine lathed shade with a lit underside.
    for o in list(S.objects):
        if o.name.startswith('Diagnostic'):bpy.data.objects.remove(o,do_unlink=True)
    lp=at_y(.443,.062,.2);verts=[];faces=[];profile=[(.05,.16),(.13,.10),(.28,.045),(.43,0),(.42,-.018),(.27,.02),(.12,.075)]
    for radius,z in profile:
        for i in range(96):a=i*math.tau/96;verts.append((lp.x+radius*math.cos(a),lp.y+radius*math.sin(a),lp.z+z))
    for j in range(len(profile)-1):
        for i in range(96):faces.append((j*96+i,j*96+(i+1)%96,(j+1)*96+(i+1)%96,(j+1)*96+i))
    mesh('P09 spun lamp shade',verts,faces,M['shadow'])
    em=mat('P09 warm enamel underside',(.80,.78,.63),.65);p=em.node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(.85,.88,.72,1);p.inputs['Emission Strength'].default_value=4
    cyl('P09 luminous underside',(lp.x,lp.y,lp.z-.013),.405,.008,em,96)
    line('P09 hanging wire',[(lp.x,lp.y,lp.z+.16),(lp.x,lp.y,5.7)],.005,M['shadow'])
    lamp('Diagnostic softbox','AREA',(0,-4,5),700,(.8,.88,1),5,(-.5,1,1))
    S.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.14
    save('02_assets.blend');render('02_assets.png',1200,40)

def lighting():
    config()
    for o in list(S.objects):
        if o.type=='LIGHT':bpy.data.objects.remove(o,do_unlink=True)
    lp=bpy.data.objects['P09 luminous underside'].location
    lamp('P15 pendant downward pool','AREA',(lp.x,lp.y,lp.z-.08),420,(.78,.87,1),.60,(-.3,.2,.1))
    lamp('P15 narrow visible cone','SPOT',(lp.x,lp.y,lp.z-.06),300,(.74,.85,1),.86,(-.25,.1,.0))
    # Diagonal beam is cast by real geometry in front of a bounded offscreen source.
    lamp('P15 right slanted key','AREA',(5,-1.8,4.2),950,(.75,.85,1),.45,(-.6,2.2,.4))
    lamp('P15 eye and paper bounce','AREA',(-.6,-3,2.1),24,(.55,.68,.88),2.8,(-.3,.5,1.2))
    S.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.04,.075,.13,1)
    S.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.055
    # Local haze avoids replacing the entire room with an opaque wash.
    m=bpy.data.materials.new('P15 bounded blue haze');m.use_nodes=True;n=m.node_tree.nodes;n.clear();l=m.node_tree.links
    v=n.new('ShaderNodeVolumePrincipled');v.inputs['Density'].default_value=.012;v.inputs['Color'].default_value=(.57,.69,.82,1);v.inputs['Anisotropy'].default_value=.2
    out=n.new('ShaderNodeOutputMaterial');l.new(v.outputs['Volume'],out.inputs['Volume']);m.use_fake_user=True
    box('P15 haze volume',(0,.8,2.55),(12,5,5.1),m,0)
    S.view_settings.exposure=-.2
    # Mild vignette only, no reference image or generated image compositing.
    S.use_nodes=True;n=S.node_tree.nodes;n.clear();l=S.node_tree.links;rl=n.new('CompositorNodeRLayers')
    mask=n.new('CompositorNodeEllipseMask');mask.width=.95;mask.height=.90
    blur=n.new('CompositorNodeBlur');blur.filter_type='GAUSS';blur.size_x=350;blur.size_y=300;l.new(mask.outputs[0],blur.inputs[0])
    ramp=n.new('CompositorNodeValToRGB');ramp.color_ramp.elements[0].color=(.22,.28,.36,1);ramp.color_ramp.elements[1].color=(1,1,1,1);l.new(blur.outputs[0],ramp.inputs[0])
    mix=n.new('CompositorNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.72;l.new(rl.outputs['Image'],mix.inputs[1]);l.new(ramp.outputs[0],mix.inputs[2])
    out=n.new('CompositorNodeComposite');l.new(mix.outputs[0],out.inputs[0])
    render('03_lighting_v1.png',1200,48);save('03_lighting.blend')

if MODE=='base':base()
elif MODE=='assets':details()
elif MODE=='lighting':lighting()
else:raise ValueError(MODE)
print('STAGE_COMPLETE',MODE,flush=True)

