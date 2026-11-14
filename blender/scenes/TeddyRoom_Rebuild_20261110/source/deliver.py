import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1]
mode=sys.argv[sys.argv.index('--')+1]
saved=list(sys.argv);sys.argv=['blender','--','helpers']
exec(compile((ROOT/'source/rebuild.py').read_text(encoding='utf-8-sig').split("if MODE=='base':base()")[0],str(ROOT/'source/rebuild.py'),'exec'))
sys.argv=saved
config()

if mode=='final':
    S['Construction provenance']='New factory-startup build. No prior .blend loaded or appended.'
    S['Reference policy']='Reference pixels used only on individual paper artwork meshes. No full-scene background image or composite.'
    S['Scope']='Single hero camera recreation, diagnostic views, not a game-ready level.'
    for name,loc,target,lens in [
      ('Left',(-3,-3,2.7),(-.6,1.7,1.3),38),
      ('Right',(2.8,-3,2.6),(-.6,1.7,1.4),38),
      ('Reverse',(-.5,5.8,2.7),(-.4,1.6,1.0),28),
      ('Overhead',(-.4,1.5,12),(-.4,1.5,0),35),
      ('StoolDetail',(2.3,-1.6,1.7),(1.0,1.1,.5),55),
      ('WallDetail',(-.6,0,3.1),(-.6,6.28,2.9),50)]:
        cam(name,loc,target,lens)
    bpy.data.objects['Overhead'].data.type='ORTHO';bpy.data.objects['Overhead'].data.ortho_scale=13
    render('05_final.png',1440,128)
    S.camera=bpy.data.objects['Hero'];save('scene_cycles.blend')
    # Conservative projected geometry bounds, not segmented pixel silhouettes.
    measured={}
    for label,prefix in [('table','P02 thin circular tabletop'),('bear','P01 Hero bear'),('stool','P04'),('figure','P05'),('lamp','P09 luminous underside')]:
        uv=[]
        for o in S.objects:
            if o.type=='MESH' and o.name.startswith(prefix):
                uv.extend([world_to_camera_view(S,S.camera,o.matrix_world@Vector(p)) for p in o.bound_box])
        if uv:measured[label]={'u_min':min(p.x for p in uv),'u_max':max(p.x for p in uv),'v_min':1-max(p.y for p in uv),'v_max':1-min(p.y for p in uv)}
    target_bounds={'table':[.335,.585,.535,.645],'bear':[.420,.445,.508,.617],'stool':[.533,.615,.647,.765],'figure':[.375,.630,.430,.825],'lamp':[.396,.045,.488,.078]}
    (ROOT/'camera_alignment.json').write_text(json.dumps({'method':'Manual reference anchors plus projected conservative geometry bounds; not pixel silhouette or similarity score','reference_estimated_bounds_u0_v0_u1_v1':target_bounds,'new_geometry_bounds':measured,'camera':{'location':list(S.camera.location),'rotation':list(S.camera.rotation_euler),'lens':S.camera.data.lens,'sensor_width':S.camera.data.sensor_width},'note':'Single-image camera is not uniquely recoverable; matched composition within design assumptions'},indent=2),encoding='utf8')
elif mode=='views':
    manifest={}
    for label,name in [('hero','Hero'),('left','Left'),('right','Right'),('reverse','Reverse'),('overhead','Overhead'),('bear','BearDetail'),('stool','StoolDetail'),('wall','WallDetail')]:
        changed=[]
        if name in ['Overhead','Reverse','StoolDetail','WallDetail']:
            for o in S.objects:
                if o.name.startswith(('P14 ceiling','P15 haze volume','P15 offscreen window')):
                    changed.append((o,o.hide_render));o.hide_render=True
            dl=lamp('Temporary diagnostic fill','AREA',(0,0,5.5),650,(.8,.87,1),5,(0,2,.7))
        render('view_'+label+'.png',720,24,name)
        for o,old in changed:o.hide_render=old
        if changed:bpy.data.objects.remove(dl,do_unlink=True)
        c=bpy.data.objects[name]
        manifest[label]={'camera':name,'location':list(c.location),'rotation':list(c.rotation_euler),'lens':c.data.lens,'projection':c.data.type,'diagnostic_cutaway_and_fill':bool(changed)}
    (ROOT/'cameras.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    S.camera=bpy.data.objects['Hero'];S.render.resolution_x=1440;S.render.resolution_y=960;S.cycles.samples=128
    save('scene_cycles.blend')
elif mode=='realtime':
    S.render.engine='BLENDER_EEVEE_NEXT';S.camera=bpy.data.objects['Hero'];bpy.data.objects['P15 haze volume'].hide_set(True)
    for o in S.objects:
        if o.name.startswith('P15 offscreen window'):o.hide_set(True)
    bpy.data.objects['P15 right slanted key'].data.energy=1800
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                sp=area.spaces.active;sp.overlay.show_overlays=False;sp.show_gizmo=False;sp.show_region_toolbar=False;sp.show_region_ui=False;sp.shading.type='RENDERED';sp.region_3d.view_perspective='CAMERA';sp.region_3d.view_camera_zoom=0
    save('scene_realtime.blend')
elif mode=='verify':
    missing=[{'name':i.name,'path':i.filepath} for i in bpy.data.images if i.source=='FILE' and i.filepath and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).is_file()]
    if missing:raise RuntimeError(missing)
    render('07_reopen_check.png',720,32)
    prefixes=['P%02d'%i for i in range(1,16)]
    result={'blender':bpy.app.version_string,'reopened_file':str(Path(bpy.data.filepath).resolve()),'objects':len(S.objects),'cameras':[o.name for o in S.objects if o.type=='CAMERA'],'active_camera':S.camera.name,'missing_external_images':missing,'packed_images':[i.name for i in bpy.data.images if i.packed_file],'asset_groups':{p:sum(o.name.startswith(p) for o in S.objects) for p in prefixes},'reopened_and_rendered':True,'loaded_previous_scene':False,'limitations':['Designed scale and hidden geometry','Original visible artwork retained as photo-derived texture, including some baked illumination','Character shapes and fabric still approximate','No game engine import or performance validation']}
    assert len(result['cameras'])==8
    assert all(result['asset_groups'].values())
    spec=json.loads((ROOT/'scene_spec.json').read_text(encoding='utf8'))
    spec['as_built']={'note':'positions above are the initial construction inputs; final corrections below are read from actual saved objects','hero_bear_root':list(bpy.data.objects['P01 Hero bear'].location),'chair_seat':list(bpy.data.objects['P03 chair seat'].location),'stool_top':list(bpy.data.objects['P04 rounded saddle top'].location),'foreground_hat_projected_bounds':'camera_alignment.json','main_camera_unchanged':True,'wall_y':6.4}
    (ROOT/'scene_spec.json').write_text(json.dumps(spec,indent=2),encoding='utf8')
    (ROOT/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print('VALIDATED',json.dumps(result),flush=True)
else:raise ValueError(mode)
