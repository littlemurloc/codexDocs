import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]; R=ROOT/'renders'; R.mkdir(exist_ok=True)
MODE=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'base'
random.seed(207); S=bpy.context.scene
FACE=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
BATCH={}; M={}; FONT=None
BUILDINGS=[]
for side in [-1,1]:
    starts=[-2.1,2.9,7.8,12.8,17.8,23.0,28.0]
    for i,y in enumerate(starts):
        BUILDINGS.append({'side':side,'i':i,'y':y,'length':4.65 if i!=4 else 4.9,'height':([7.1,6.5,5.8,6.7,5.7,5.9,5.5] if side<0 else [5.3,5.85,5.1,5.8,5.5,5.6,5.1])[i],'x':side*3.55})

def mesh(name,verts,faces,mat,uv=True):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update()
    o=bpy.data.objects.new(name,d);S.collection.objects.link(o)
    if mat:d.materials.append(mat)
    if uv:
        u=d.uv_layers.new(name='UVMap')
        for p in d.polygons:
            vs=[d.vertices[d.loops[j].vertex_index].co for j in p.loop_indices]
            n=p.normal; axes=([1,2] if abs(n.x)>.7 else [0,2] if abs(n.y)>.7 else [0,1])
            lo=[min(v[a] for v in vs) for a in axes];hi=[max(v[a] for v in vs) for a in axes]
            for j,v in zip(p.loop_indices,vs):u.data[j].uv=tuple((v[a]-lo[k])/max(hi[k]-lo[k],1e-6) for k,a in enumerate(axes))
    return o

def boxgeo(loc,size):
    x,y,z=loc;a,b,c=[s/2 for s in size]
    return [(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]

def box(name,loc,size,mat,bevel=.015,batch=False):
    vs=boxgeo(loc,size)
    if batch:
        key=(name,mat.name);b=BATCH.setdefault(key,[[],[],mat]);n=len(b[0]);b[0].extend(vs);b[1].extend([tuple(n+i for i in f) for f in FACE]);return None
    o=mesh(name,vs,FACE,mat)
    if bevel:
        b=o.modifiers.new('Worn edge radius','BEVEL');b.width=bevel;b.segments=2
        o.modifiers.new('Face normals','WEIGHTED_NORMAL')
    return o

def flush():
    for (name,_),(v,f,m) in BATCH.items():mesh(name,v,f,m)
    BATCH.clear()

def line(name,pts,r,mat):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=r;d.bevel_resolution=2
    p=d.splines.new('POLY');p.points.add(len(pts)-1)
    for q,v in zip(p.points,pts):q.co=(*v,1)
    o=bpy.data.objects.new(name,d);S.collection.objects.link(o);d.materials.append(mat);return o

def rod(name,a,b,r,mat,r2=None):
    a,b=Vector(a),Vector(b)
    if r2 is None:bpy.ops.mesh.primitive_cylinder_add(vertices=10,radius=r,depth=(b-a).length,location=(a+b)/2)
    else:bpy.ops.mesh.primitive_cone_add(vertices=10,radius1=r,radius2=r2,depth=(b-a).length,location=(a+b)/2)
    o=bpy.context.object;o.name=name;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    return o

def basicmat(name,c,rough=.7,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*c,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m

def textured(name,tile,tint,rough=.7,bump=.025):
    m=basicmat(name,tint,rough);n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    uv=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY_ADD';mapping.inputs[1].default_value=(.478,.478,1)
    mapping.inputs[2].default_value={0:(.011,.511,0),1:(.511,.511,0),2:(.011,.011,0),3:(.511,.011,0)}[tile]
    l.new(uv.outputs['UV'],mapping.inputs[0]);im=n.new('ShaderNodeTexImage');im.image=bpy.data.images.get('Material Atlas')
    l.new(mapping.outputs[0],im.inputs['Vector'])
    mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*tint,1)
    l.new(im.outputs['Color'],mix.inputs[1]);l.new(mix.outputs[0],p.inputs['Base Color'])
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=45;noise.inputs['Detail'].default_value=3
    l.new(uv.outputs['Generated'],noise.inputs['Vector']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.28;b.inputs['Distance'].default_value=bump
    l.new(noise.outputs['Fac'],b.inputs['Height']);l.new(b.outputs[0],p.inputs['Normal'])
    return m

def materials():
    global M,FONT
    if 'Material Atlas' not in bpy.data.images:
        im=bpy.data.images.load(str(ROOT/'assets/material_atlas.png'));im.name='Material Atlas';im.pack()
    if 'Cedar structural timber' not in bpy.data.materials:
        textured('Cedar structural timber',0,(.65,.62,.55),.73,.025)
        textured('Old door planks',0,(.9,.83,.7),.65,.02)
        textured('Weathered plaster',1,(.73,.71,.60),.94,.035)
        textured('Green stained plaster',1,(.39,.48,.34),.9,.04)
        textured('Dark grey roof tiles',2,(.55,.61,.66),.6,.02)
        for i in range(8):textured('Stone variant %d'%i,3,(.6+i*.055,.58+i*.05,.52+i*.045),.35+i*.035,.027)
        basicmat('Mortar',(.07,.063,.05),.94)
        basicmat('Blackened iron',(.035,.042,.04),.43,.65)
        basicmat('Aged paper sign',(.58,.47,.28),.85)
        basicmat('Soot black ink',(.025,.026,.021),.86)
        basicmat('Rust red sign',(.19,.037,.018),.87)
        basicmat('Warm ivory lettering',(.73,.63,.39),.75)
        basicmat('Dark blue awning',(.07,.12,.16),.84)
        basicmat('Plant leaves',(.085,.15,.034),.85)
        basicmat('Cherry bark',(.105,.055,.037),.92)
        for i,c in enumerate([(.91,.64,.67),(.96,.78,.77),(.69,.37,.45),(.97,.88,.83)]):basicmat('Cherry petal %d'%i,c,.68)
        m=basicmat('Lamp paper glow',(1,.63,.25),.65);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(1,.57,.21,1);p.inputs['Emission Strength'].default_value=3
        water=basicmat('Shallow rain water',(.17,.19,.17),.065);p=water.node_tree.nodes.get('Principled BSDF');p.inputs['Metallic'].default_value=.35;p.inputs['Coat Weight'].default_value=.7;p.inputs['IOR'].default_value=1.333
        n=water.node_tree.nodes;l=water.node_tree.links;tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=18
        b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.12;b.inputs['Distance'].default_value=.008;l.new(tex.outputs['Fac'],b.inputs['Height']);l.new(b.outputs[0],p.inputs['Normal'])
    M={m.name:m for m in bpy.data.materials}
    try:FONT=bpy.data.fonts.get('Chinese Sign Font') or bpy.data.fonts.load('C:/Windows/Fonts/simsun.ttc');FONT.name='Chinese Sign Font'
    except Exception:FONT=bpy.data.fonts[0]

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
def camera(name,loc,target,lens=32,ortho=None):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);S.collection.objects.link(o);o.location=loc;aim(o,target);d.lens=lens;d.clip_start=.06;d.clip_end=180
    if ortho:d.type='ORTHO';d.ortho_scale=ortho
    return o
def light(name,typ,loc,energy,color,size,target):
    d=bpy.data.lights.new(name,typ);d.energy=energy;d.color=color
    if typ=='AREA':d.shape='DISK';d.size=size
    elif typ=='SUN':d.angle=size
    else:d.shadow_soft_size=size
    o=bpy.data.objects.new(name,d);S.collection.objects.link(o);o.location=loc;aim(o,target);return o

def config(samples=48):
    S.render.engine='CYCLES';S.cycles.samples=samples;S.cycles.use_denoising=True;S.cycles.use_preview_denoising=True;S.cycles.preview_samples=32
    S.cycles.max_bounces=7;S.cycles.diffuse_bounces=3;S.cycles.glossy_bounces=4;S.cycles.transparent_max_bounces=6
    S.render.threads_mode='FIXED';S.render.threads=6;S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGB'
    S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast';S.view_settings.exposure=.25
    try:
        p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
        for d in p.devices:d.use=d.type!='CPU'
        if any(d.use for d in p.devices):S.cycles.device='GPU'
        print('DEVICES',[(d.name,d.use) for d in p.devices],flush=True)
    except Exception as e:print('GPU_FALLBACK',str(e),flush=True)

def render(name,cam='Hero',w=1200,h=900,samples=48):
    config(samples);S.camera=bpy.data.objects[cam];S.render.resolution_x=w;S.render.resolution_y=h;S.render.resolution_percentage=100;S.render.filepath=str(R/name)
    bpy.ops.render.render(write_still=True);print('RENDER_DONE',name,flush=True)

def save(name):
    for m in bpy.data.materials:m.use_fake_user=True
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/name));print('SAVE_DONE',name,flush=True)

def roof_shed(name,side,x,y,w,length,z,mat):
    # Sloped roof, lower edge projects into the street.
    inner=x-side*w;outer=x+side*.35
    return mesh(name,[(inner,y-length/2,z-.32),(inner,y+length/2,z-.32),(outer,y+length/2,z+.35),(outer,y-length/2,z+.35)],[(0,1,2,3)],mat)

def base():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);materials()
    box('Street foundation',(0,12,-.16),(8.7,39,.27),M['Mortar'],0)
    for side in [-1,1]:box('Sidewalk foundation',(side*3.05,12,.07),(.9,39,.2),M['Stone variant 2'],.02)
    for b in BUILDINGS:
        s,i,y,L,H,x=[b[k] for k in ['side','i','y','length','height','x']]
        box('Building_%s_%02d'%(s,i),(x+s*1.1,y,H/2),(2.2,L,H),M['Weathered plaster'] if i%3 else M['Green stained plaster'],.025)
        roof_shed('Upper eave_%s_%s'%(s,i),s,x,y,.8,L+.3,H,M['Dark grey roof tiles'])
        roof_shed('Shop canopy_%s_%s'%(s,i),s,x,y,.82,L+.15,2.75+(.1 if i%2 else 0),M['Dark grey roof tiles'])
    box('Bridge deck',(0,15,3.95),(7.2,1.25,.22),M['Cedar structural timber'])
    for yy in [14.37,15.63]:box('Bridge railing base',(0,yy,4.45),(7.2,.09,.8),M['Cedar structural timber'])
    # Starting camera: a slightly offset view with an upward view direction.
    camera('Hero',(-.15,-6,1.9),(-2.5,18,2.55),32)
    camera('NearFacade',(.5,-1,2.2),(-3.45,2.5,2.7),27)
    camera('GroundDetail',(1.9,-.8,1.0),(-.2,5,.05),36)
    camera('Reverse',(.2,15,2.1),(0,-1,2.4),26)
    camera('HighStreet',(-.1,-3,6),(0,12,1),27)
    camera('MidStreet',(0,7.5,1.8),(0,24,2.4),30)
    camera('RightDetail',(-.8,-.4,1.8),(3.4,2,2),30)
    camera('Overhead',(0,12,30),(0,12,0),35,38)
    S.world.use_nodes=True;n=S.world.node_tree.nodes;n.clear();l=S.world.node_tree.links
    sky=n.new('ShaderNodeTexSky');sky.sky_type='NISHITA';sky.sun_elevation=math.radians(42);sky.sun_rotation=math.radians(125);sky.sun_disc=False
    bg=n.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.45;out=n.new('ShaderNodeOutputWorld');l.new(sky.outputs[0],bg.inputs[0]);l.new(bg.outputs[0],out.inputs[0])
    light('Soft morning sun','SUN',(-6,0,12),1.3,(1,.88,.70),.16,(0,10,0))
    light('Sky opening fill','AREA',(0,8,13),850,(.72,.8,1),12,(0,8,0))
    config();S['Source']='Single input reference, not a measured reconstruction';S['Units']='Meters are design assumptions';S['Build stages']='base > facade > dress > lighting > views > realtime'
    save('02_blockout.blend')
    clay=basicmat('White model clay',(.48,.48,.46),.8);S.view_layers[0].material_override=clay
    render('02_blockout.png',w=1024,h=768,samples=24);S.view_layers[0].material_override=None

def facade():
    materials();wood=M['Cedar structural timber'];plank=M['Old door planks'];roof=M['Dark grey roof tiles'];iron=M['Blackened iron']
    for b in BUILDINGS:
        s,i,y,L,H,x=[b[k] for k in ['side','i','y','length','height','x']];xf=x-s*.055
        # Structural bay grid and exposed wood framing.
        for yy in [y-L/2+.08,y,y+L/2-.08]:box('Facade posts',(xf,yy,H/2),(.16,.15,H),wood,batch=True)
        for z in [.28,2.45,3.05,H-.25]:box('Facade horizontal beams',(xf-s*.035,y,z),(.19,L,.14),wood,batch=True)
        # Ground-floor plank shutters and doors, all with a real thickness.
        for bay,yy in enumerate([y-L*.26,y+L*.26]):
            for j in range(9):box('Door planks',(xf-s*.07,yy-.65+j*.16,1.25),(.055,.15,1.95),plank,batch=True)
            for zz in [.42,2.14]:box('Door crossbars',(xf-s*.11,yy,zz),(.06,1.48,.09),wood,batch=True)
            box('Door handle',(xf-s*.15,yy+.42,1.21),(.035,.06,.17),iron,batch=True)
        # Upper floors with lattice windows and two distinct balcony modules.
        for yy in [y-L*.26,y+L*.26]:
            for z in ([3.55,5.4] if H>6.3 else [3.55]):
                box('Upper dark window',(xf-s*.02,yy,z),(.04,1.38,1.12),M['Soot black ink'],batch=True)
                for j in range(9):box('Upper window slats',(xf-s*.08,yy-.63+j*.155,z),(.045,.035,1.14),wood,batch=True)
                for zz in [z-.56,z,z+.56]:box('Window sill rail',(xf-s*.10,yy,zz),(.12,1.5,.065),wood,batch=True)
        if i in [0,1,3] and s<0:
            box('Balcony deck',(xf-s*.36,y,3.0),(.85,L*.78,.13),wood)
            for yy in [y-L*.39,y+L*.39]:box('Balcony end rail',(xf-s*.4,yy,3.46),(.9,.07,.8),wood,batch=True)
            for yy in [y-L*.36+j*.22 for j in range(int(L*.72/.22)+1)]:box('Balcony baluster',(xf-s*.77,yy,3.43),(.065,.055,.84),wood,batch=True)
            box('Balcony top rail',(xf-s*.77,y,3.88),(.09,L*.8,.10),wood,batch=True)
        # Separate little roof pieces create edge silhouettes and rain-runoff rhythm.
        for upper,z,w in [(True,H,.8),(False,2.75+(.1 if i%2 else 0),.82)]:
            for yy in [y-L/2+j*.21 for j in range(int(L/.21)+2)]:
                for row in range(3):
                    t=row/3;xx=x-s*w+s*(w+.35)*t;zz=z-.32+.67*t
                    box('Roof tile courses',(xx,yy,zz),(.42,.205,.045),roof,batch=True)
            rod('Eave rain gutter',(x-s*w,y-L/2,z-.33),(x-s*w,y+L/2,z-.33),.06,iron)
            for yy in [y-L*.32,y+L*.32]:rod('Canopy diagonal brace',(xf,yy,2.25),(x-s*.72,yy,2.65),.045,wood)
        # Foundation ledges and shop entry steps.
        for zz,depth in [(.17,.52),(.29,.28)]:box('Doorstep stone',(x-s*.2,y,zz/2),(depth,L-.12,zz),M['Stone variant 3'],.025)
    # Bridge railing replaces the placeholder slab while deck remains shared geometry.
    for o in list(S.objects):
        if o.name.startswith('Bridge railing base'):bpy.data.objects.remove(o,do_unlink=True)
    for yy in [14.37,15.63]:
        for xx in [-3.5+j*.3 for j in range(25)]:box('Bridge spindles',(xx,yy,4.45),(.07,.07,.85),wood,batch=True)
        for z in [4.04,4.9]:box('Bridge handrail',(0,yy,z),(7.4,.12,.1),wood,batch=True)
    # Wooden sign slabs are still blank at this stage.
    for x,y,z,w,h in [(-2.65,.5,3.8,.8,2.1),(-2.7,6.3,4.5,.72,1.8),(2.6,1.8,3.75,.73,1.9),(0,13,4.3,.55,1.85)]:box('Sign blank',(x,y,z),(w,.1,h),wood,.035)
    flush();save('03_facades.blend');render('03_facades.png',w=1200,h=900,samples=40)
    render('03_facade_detail.png','NearFacade',1000,750,40)

def text(name,body,loc,size,mat,align='CENTER'):
    d=bpy.data.curves.new(name,'FONT');d.body=body;d.font=FONT;d.size=size;d.align_x=align;d.align_y='CENTER';d.extrude=.001
    o=bpy.data.objects.new(name,d);S.collection.objects.link(o);o.location=loc;o.rotation_euler=(math.pi/2,0,0);d.materials.append(mat);return o

def sign(x,y,z,w,h,body,bg,fg):
    box('Painted sign face',(x,y-.061,z),(w-.09,.012,h-.09),bg,.01)
    for dx in [-w/2,w/2]:box('Sign frame',(x+dx,y-.07,z),(.04,.035,h+.06),M['Old door planks'],.008)
    for dz in [-h/2,h/2]:box('Sign frame',(x,y-.07,z+dz),(w+.07,.035,.045),M['Old door planks'],.008)
    chars=list(body);step=min(w*.65,(h-.35)/len(chars))
    for i,c in enumerate(chars):text('Sign glyph '+c,c,(x,y-.085,z+(len(chars)-1)*step/2-i*step),step*.88,fg)
    # Decorative seal is an explicit geometric graphic.
    box('Sign red seal',(x+w*.29,y-.083,z-h*.38),(.1,.012,.12),M['Rust red sign'],.002)

def lantern(x,y,z,s=.4):
    wood=M['Cedar structural timber'];glow=M['Lamp paper glow']
    box('Lantern glowing paper',(x,y,z),(s*.7,s*.65,s),glow,.03)
    for dx in [-s*.38,s*.38]:
        for dy in [-s*.35,s*.35]:box('Lantern frame',(x+dx,y+dy,z),(.035,.035,s+.1),wood,.005)
    for zz in [z-s*.55,z+s*.55]:box('Lantern cap',(x,y,zz),(s*.95,s*.9,.065),wood,.02)
    rod('Lantern hanging rod',(x,y,z+s*.6),(x,y,z+s),.016,M['Blackened iron'])
    light('Lantern practical','POINT',(x,y-.05,z),12,(1,.5,.16),.13,(x,y,0))

def barrel(x,y,z=0,s=.48):
    wood=M['Old door planks'];iron=M['Blackened iron']
    # Profile rings produce a barrel rather than a cylinder proxy.
    verts=[];faces=[];N=20
    for zz,rr in [(0,.78),(.1,.9),(.5,1),(.9,.9),(1,.8)]:
        verts.extend([(x+s*rr*math.cos(i*math.tau/N),y+s*rr*math.sin(i*math.tau/N),z+zz*s*1.6) for i in range(N)])
    for j in range(4):
        for i in range(N):faces.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
    faces.append(tuple(range(4*N,5*N)));mesh('Coopered barrel',verts,faces,wood)
    for t,rr in [(.12,.91),(.52,1.01),(.88,.92)]:
        pts=[(x+s*rr*math.cos(i*math.tau/48),y+s*rr*math.sin(i*math.tau/48),z+t*s*1.6) for i in range(49)];line('Iron barrel hoop',pts,.018,iron)

def cherry_tree(x,y,height=6.0,spread=2.3):
    bark=M['Cherry bark'];tips=[];verts=[[] for _ in range(4)];faces=[[] for _ in range(4)]
    trunk=(x,y,height*.58);rod('Cherry trunk',(x,y,0),trunk,.16,bark,.095)
    for k in range(9):
        a=k*math.tau/9+random.uniform(-.2,.2);end=Vector((x+spread*math.cos(a),y+spread*.8*math.sin(a),height+random.uniform(-.5,.6)))
        elbow=Vector(trunk).lerp(end,.55);rod('Cherry bough',trunk,elbow,.07,bark,.035);rod('Cherry twig',elbow,end,.035,bark,.009)
        tips.extend([end,elbow.lerp(end,.5)])
    for tip in tips:
        for k in range(140):
            c=tip+Vector((random.gauss(0,.52),random.gauss(0,.4),random.gauss(0,.36)))
            normal=Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-1,1))).normalized();u=normal.cross(Vector((0,0,1)))
            if u.length<.01:u=Vector((1,0,0))
            u.normalize();v=normal.cross(u);size=random.uniform(.045,.09);mi=random.choices(range(4),[2,4,1,3])[0]
            for j in range(5):
                a=j*math.tau/5;direction=u*math.cos(a)+v*math.sin(a);across=-u*math.sin(a)+v*math.cos(a);start=len(verts[mi])
                pts=[c+direction*(size*(.48+.48*math.cos(t*math.tau/8)))+across*(size*.34*math.sin(t*math.tau/8))+normal*(size*.12*math.sin(t*math.tau/8)**2) for t in range(8)]
                verts[mi].extend([tuple(q) for q in pts]);faces[mi].append(tuple(start+t for t in range(8)))
    for i in range(4):mesh('Cherry blossom clusters',verts[i],faces[i],M['Cherry petal %d'%i])

def dress():
    materials();wood=M['Cedar structural timber'];iron=M['Blackened iron']
    water=M['Shallow rain water'].node_tree.nodes.get('Principled BSDF')
    water.inputs['Base Color'].default_value=(.045,.04,.028,1);water.inputs['Metallic'].default_value=0
    water.inputs['Transmission Weight'].default_value=.35;water.inputs['Roughness'].default_value=.10
    # Large-scale wetness varies continuously across separate stone blocks.
    for i in range(8):
        mat=M['Stone variant %d'%i];ns=mat.node_tree.nodes;ls=mat.node_tree.links
        geo=ns.new('ShaderNodeNewGeometry');wet=ns.new('ShaderNodeTexNoise');wet.inputs['Scale'].default_value=.75;wet.inputs['Detail'].default_value=3
        ls.new(geo.outputs['Position'],wet.inputs['Vector']);rng=ns.new('ShaderNodeMapRange');rng.inputs['From Min'].default_value=.25;rng.inputs['From Max'].default_value=.75;rng.inputs['To Min'].default_value=.16;rng.inputs['To Max'].default_value=.65
        ls.new(wet.outputs['Fac'],rng.inputs[0]);ls.new(rng.outputs[0],ns.get('Principled BSDF').inputs['Roughness'])
    # A designed distant turn screens the formerly empty horizon without inventing an interior.
    box('Distant turning-street facade',(-1.1,35,2.65),(5.5,.8,5.3),M['Weathered plaster'],.02)
    for xx in [-3.7,-1.9,-.1,1.55]:box('Distant facade posts',(xx,34.56,2.65),(.12,.12,5.3),wood,batch=True)
    for zz in [.3,2.5,5.15]:box('Distant facade rails',(-1.1,34.55,zz),(5.6,.12,.13),wood,batch=True)
    for xx in [-2.8,-1,.8]:
        box('Distant dark opening',(xx,34.53,1.35),(1.15,.05,2.05),M['Soot black ink'],batch=True)
        for k in range(7):box('Distant door lattice',(xx-.5+k*.16,34.48,1.35),(.035,.07,2),wood,batch=True)
    mesh('Distant ridge eave',[(-4,34.2,5.05),(1.9,34.2,5.05),(1.9,35.6,5.6),(-4,35.6,5.6)],[(0,1,2,3)],M['Dark grey roof tiles'])
    # Individually bounded flagstones with irregular seams and small actual relief.
    for row in range(65):
        yy=-5+row*.56;offset=(row%2)*.28
        for col in range(10):
            x=-2.45+col*.54+offset
            if x>2.55:continue
            z=random.uniform(-.003,.003);box('Street flagstones',(x,yy,z),(.535+random.uniform(-.004,.002),.553+random.uniform(-.004,.002),.075),M['Stone variant %d'%random.randrange(8)],batch=True)
    for side in [-1,1]:
        for row in range(72):
            yy=-5+row*.52
            box('Kerbstones',(side*2.68,yy,.135),(.23,.49,.27),M['Stone variant %d'%random.randrange(8)],batch=True)
            for j in range(2):box('Sidewalk pavers',(side*(2.9+j*.33),yy,.22),(.31,.49,.09),M['Stone variant %d'%random.randrange(8)],batch=True)
        for yy in [-1,4,10,18,25]:
            for j in range(10):box('Drain grating',(side*2.42,yy+j*.09,.045),(.24,.035,.027),iron,batch=True)
    flush()
    # Shallow puddles are surfaces, not assumed terrain depressions.
    for x,y,rx,ry in [(.2,-2,1.3,.7),(-.45,1.4,.9,1.0),(.9,4,.7,.5),(-1.0,6.5,.8,.6),(.1,10,.9,.5),(1.6,12,.6,1.2),(-1.6,16,.5,.8),(.4,20,.8,.7)]:
        vs=[(x+rx*math.cos(i*math.tau/64)*(1+.08*math.sin(i*.7)),y+ry*math.sin(i*math.tau/64)*(1+.08*math.sin(i*.7)),.043) for i in range(64)]
        mesh('Shallow puddle',vs,[tuple(range(64))],M['Shallow rain water'])
    # Fabric awning at the nearest left shop and small repeating distant shades.
    for side,y in [(-1,-1.1),(-1,8),(1,4.6),(1,11),(1,20)]:
        x=side*3.4;verts=[(x-side*1.1,y-1.15,2.32),(x-side*1.1,y+1.15,2.32),(x,y+1.15,2.85),(x,y-1.15,2.85)]
        mesh('Faded fabric canopy',verts,[(0,1,2,3)],M['Dark blue awning'])
        for j in range(12):box('Awning hanging tabs',(x-side*1.1,y-1.12+j*.195,2.25),(.025,.19,.15),M['Dark blue awning'],.025)
    # Foreground signage and a few distant signs.
    sign(-2.65,.5,3.8,.8,2.1,'旅龍',M['Soot black ink'],M['Warm ivory lettering'])
    for arm in range(3):
        line('Red inn emblem',[(-2.65+(.018+j*.0038)*math.cos(arm*math.tau/3+j*.17),.409,4.53+(.018+j*.0038)*math.sin(arm*math.tau/3+j*.17)) for j in range(42)],.015,M['Rust red sign'])
    sign(-2.7,6.3,4.5,.72,1.8,'源宿',M['Rust red sign'],M['Warm ivory lettering'])
    sign(2.6,1.8,3.75,.73,1.9,'茶屋',M['Aged paper sign'],M['Soot black ink'])
    sign(0,13,4.3,.55,1.85,'古寺小路',M['Rust red sign'],M['Warm ivory lettering'])
    for x,y,z in [(-2.65,.5,3.8),(-2.7,6.3,4.5),(2.6,1.8,3.75)]:
        side=1 if x>0 else -1;box('Sign bracket',(x+side*.35,y,z+1.2),(.85,.09,.1),wood);rod('Sign suspension',(x,y,z+1.2),(x,y,z+.95),.025,iron)
    for side,y,z in [(-1,2.2,4.0),(1,.2,4.8),(1,7,3.3),(-1,10,3.1),(1,13,3.1),(-1,18,3.1),(1,23,3.2),(-1,27,3)]:
        x=side*2.85;lantern(x,y,z,.35 if y>5 else .45);rod('Lamp wall arm',(side*3.6,y,z+.6),(x,y,z+.6),.045,wood)
    # Shops have small, placed props rather than uniform scatter.
    for x,y,ss in [(-3.0,4,.38),(2.95,3.8,.4),(-3.0,10,.32),(2.95,13,.32),(-3,18,.3)]:barrel(x,y,.27,ss)
    for x,y in [(-2.98,4.2),(3.1,10.3),(-2.95,16)]:
        box('Planter',(x,y,.51),(.42,.42,.5),wood)
        for j in range(17):
            p=Vector((x,y,.78));q=p+Vector((random.uniform(-.26,.26),random.uniform(-.26,.26),random.uniform(.05,.38)))
            rod('Planter stems',p,q,.008,M['Plant leaves'])
            a=random.random()*math.tau;u=Vector((math.cos(a)*.06,math.sin(a)*.06,0));v=Vector((0,0,.12))
            mesh('Planter foliage',[tuple(q+u*math.cos(k*math.tau/8)+v*math.sin(k*math.tau/8)) for k in range(8)],[tuple(range(8))],M['Plant leaves'])
    # Chalk menu panel near tea shop.
    menu=box('Tea shop menu',(2.95,4.3,.85),(.5,.06,.9),M['Cedar structural timber']);menu.rotation_euler[0]=-.13
    box('Menu black face',(2.95,4.25,.85),(.43,.02,.79),M['Soot black ink'])
    for i,t in enumerate(['茶','甘味','本日']):text('Menu lettering',t,(2.95,4.23,1.12-i*.21),.13,M['Warm ivory lettering'])
    # Curved hanging utility lines and festoon cords.
    for y,z in [(4,5.7),(11,4.8),(18,5.2)]:
        for dz in [0,.22]:line('Suspended utility cable',[(-3.5+7*i/30,y,z+dz-.55*math.sin(math.pi*i/30)) for i in range(31)],.015,iron)
    for side in [-1,1]:line('Facade utility cable',[(side*3.34,-3+i*1.1,3.0+.05*math.sin(i)) for i in range(32)],.018,iron)
    # Rear tree crowns: geometry completes what the single image does not specify.
    cherry_tree(4.8,8.5,6.4,2.65);cherry_tree(-4.8,13,6.6,2.35);cherry_tree(4.7,23,6.2,2.1)
    # A convex shop mirror is a modeled foreground landmark.
    mirror=basicmat('Old convex mirror',(.66,.7,.72),.07,.92)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,location=(-2.95,-.8,1.65))
    mo=bpy.context.object;mo.name='Convex street mirror';mo.scale=(.32,.07,.32);mo.data.materials.append(mirror)
    line('Mirror iron rim',[(-2.95+.33*math.cos(i*math.tau/64),-.87,1.65+.33*math.sin(i*math.tau/64)) for i in range(65)],.028,iron)
    rod('Mirror mounting post',(-3.05,-.73,.28),(-3.05,-.73,1.7),.045,wood)
    for j in range(900):
        x=random.uniform(-3.4,3.4);y=random.uniform(-4,27);z=.283 if abs(x)>2.6 else .058
        if abs(x)<1.3 and random.random()<.7:continue
        a=random.random()*math.tau;s=random.uniform(.012,.035);u=Vector((math.cos(a)*s,math.sin(a)*s,0));v=Vector((-math.sin(a)*s*.45,math.cos(a)*s*.45,0));c=Vector((x,y,z));mi=random.randrange(4)
        key=('Fallen cherry petals','Cherry petal %d'%mi);b=BATCH.setdefault(key,[[],[],M[key[1]]]);n=len(b[0]);b[0].extend([tuple(c-u),tuple(c+v),tuple(c+u),tuple(c-v)]);b[1].append((n,n+1,n+2,n+3))
    flush();save('04_dressed.blend');render('04_dressed.png',w=1200,h=900,samples=48)
    render('04_ground_detail.png','GroundDetail',1000,750,40)

def lighting():
    materials();S.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.36
    bpy.data.objects['Soft morning sun'].data.energy=1.05
    bpy.data.objects['Soft morning sun'].location=(-3,16,14)
    aim(bpy.data.objects['Soft morning sun'],(0,0,0))
    S.view_settings.exposure=.1
    # Bounded distant atmosphere keeps the foreground crisp.
    if 'Distant haze' not in bpy.data.objects:
        m=bpy.data.materials.new('Distant atmosphere material');m.use_nodes=True;n=m.node_tree.nodes;n.clear();v=n.new('ShaderNodeVolumePrincipled');v.inputs['Density'].default_value=.012;v.inputs['Color'].default_value=(.8,.76,.67,1);v.inputs['Anisotropy'].default_value=.15;o=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(v.outputs['Volume'],o.inputs['Volume'])
        box('Distant haze',(0,23,5),(10,22,10),m,0)
    # Mild finishing only; geometry diagnostics are rendered before this compositor is created.
    S.use_nodes=True;n=S.node_tree.nodes;n.clear();l=S.node_tree.links;rl=n.new('CompositorNodeRLayers');gl=n.new('CompositorNodeGlare');gl.glare_type='FOG_GLOW';gl.quality='MEDIUM';gl.threshold=2.5;gl.mix=-.94
    l.new(rl.outputs['Image'],gl.inputs['Image']);out=n.new('CompositorNodeComposite');l.new(gl.outputs['Image'],out.inputs[0])
    render('05_final.png',w=1440,h=1080,samples=96);save('scene_cycles.blend')

def views():
    cams=[('hero','Hero'),('near_facade','NearFacade'),('ground','GroundDetail'),('reverse','Reverse'),('high','HighStreet'),('mid_street','MidStreet'),('right_detail','RightDetail'),('overhead','Overhead')]
    manifest={}
    for label,camname in cams:
        haze=bpy.data.objects.get('Distant haze');old=haze.hide_render if haze else False
        if label=='overhead' and haze:haze.hide_render=True
        render('view_'+label+'.png',camname,960,720,40)
        if haze:haze.hide_render=old
        c=bpy.data.objects[camname];manifest[label]={'camera':camname,'location':list(c.location),'rotation':list(c.rotation_euler),'lens_mm':c.data.lens,'orthographic':c.data.type=='ORTHO','haze_hidden':label=='overhead'}
    (ROOT/'cameras.json').write_text(json.dumps(manifest,indent=2),encoding='utf8');S.camera=bpy.data.objects['Hero'];save('scene_cycles.blend')

def integration():
    materials()
    if 'Extended distant ground' not in bpy.data.objects:
        box('Extended distant ground',(0,17,-.20),(18,60,.3),M['Stone variant 3'],.01)
        for side in [-1,1]:
            row=[b for b in BUILDINGS if b['side']==side]
            for a,b in zip(row,row[1:]):
                start=a['y']+a['length']/2;end=b['y']-b['length']/2;h=min(a['height'],b['height'])
                if end>start:box('Filled party-wall joint',(side*3.63,(start+end)/2,h/2),(.2,end-start+.1,h),M['Weathered plaster'],.012)
        for b in BUILDINGS:
            s,y,L,H,x=[b[k] for k in ['side','y','length','height','x']]
            center=x+s*1.1;left=center-1.5;right=center+1.5;yy0=y-L/2-.18;yy1=y+L/2+.18
            o=mesh('Complete pitched roof',[(left,yy0,H-.1),(left,yy1,H-.1),(center,yy1,H+.65),(center,yy0,H+.65),(right,yy0,H-.1),(right,yy1,H-.1)],[(0,1,2,3),(3,2,5,4)],M['Dark grey roof tiles'])
            mod=o.modifiers.new('Roof thickness','SOLIDIFY');mod.thickness=.07
            rod('Ridge cap',(center,yy0,H+.67),(center,yy1,H+.67),.075,M['Dark grey roof tiles'])
    render('05_final.png',w=1440,h=1080,samples=96);save('scene_cycles.blend')

def realtime():
    S.render.engine='BLENDER_EEVEE_NEXT'
    if bpy.data.objects.get('Distant haze'):bpy.data.objects['Distant haze'].hide_set(True)
    S.camera=bpy.data.objects['Hero']
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                sp=a.spaces.active;sp.overlay.show_overlays=False;sp.show_gizmo=False;sp.show_region_toolbar=False;sp.show_region_ui=False;sp.shading.type='RENDERED'
                sp.region_3d.view_perspective='CAMERA';sp.region_3d.view_camera_zoom=0
    save('scene_realtime.blend')

def verify():
    result={'blender':bpy.app.version_string,'objects':len(S.objects),'meshes':sum(o.type=='MESH' for o in S.objects),'cameras':[o.name for o in S.objects if o.type=='CAMERA'],'packed_images':[i.name for i in bpy.data.images if i.packed_file],'external_missing':[i.filepath for i in bpy.data.images if i.source=='FILE' and not i.packed_file and i.filepath and not Path(bpy.path.abspath(i.filepath)).exists()],'known_limits':['Interpretation from one image, not measured','Rear sides and remote geometry designed','No engine import, collision or gameplay FPS validation','Approximate signs and structural details','Generated albedo atlas is not a scanned PBR material set']}
    render('07_reopen_check.png',w=640,h=480,samples=24);result['reopened_and_rendered']=True
    (ROOT/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result),flush=True)

if MODE=='base':base()
elif MODE=='facade':facade()
elif MODE=='dress':dress()
elif MODE=='lighting':lighting()
elif MODE=='views':views()
elif MODE=='integration':integration()
elif MODE=='realtime':realtime()
elif MODE=='verify':verify()
else:raise ValueError(MODE)
print('STAGE_COMPLETE',MODE,flush=True)
