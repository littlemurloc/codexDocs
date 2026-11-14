import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=bpy.context.scene
missing=[i.filepath for i in bpy.data.images if i.source=='FILE' and i.filepath and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).is_file()]
assert s.render.engine=='BLENDER_EEVEE_NEXT'
assert s.camera.name=='Hero'
assert not missing
report={'reopened':bpy.data.filepath,'engine':s.render.engine,'active_camera':s.camera.name,'cameras':[o.name for o in s.objects if o.type=='CAMERA'],'missing_images':missing,'passed':True,'performance_tested':False}
(root/'realtime_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('REALTIME_REOPEN_PASS',flush=True)
