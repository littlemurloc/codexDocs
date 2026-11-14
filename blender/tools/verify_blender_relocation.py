"""Read-only .blend relocation check; invoked inside Blender, never saves the scene."""
import bpy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:]
report_path = Path(args[0]).resolve()
expected_engine = args[1]
should_render = '--render' in args[2:]
scene = bpy.context.scene
missing = []
for image in bpy.data.images:
    if image.source == 'FILE' and image.filepath and not image.packed_file:
        resolved = Path(bpy.path.abspath(image.filepath))
        if not resolved.is_file():
            missing.append({'kind': 'image', 'name': image.name, 'path': str(resolved)})
for font in bpy.data.fonts:
    if font.filepath and not font.filepath.startswith('<') and not font.packed_file:
        resolved = Path(bpy.path.abspath(font.filepath))
        if not resolved.is_file():
            missing.append({'kind': 'font', 'name': font.name, 'path': str(resolved)})
for library in bpy.data.libraries:
    resolved = Path(bpy.path.abspath(library.filepath))
    if not resolved.is_file():
        missing.append({'kind': 'library', 'name': library.name, 'path': str(resolved)})
report = {
    'checked_at': datetime.now(timezone.utc).isoformat(),
    'file': str(Path(bpy.data.filepath).resolve()),
    'blender': bpy.app.version_string,
    'engine': scene.render.engine,
    'expected_engine': expected_engine,
    'objects': len(scene.objects),
    'cameras': [o.name for o in scene.objects if o.type == 'CAMERA'],
    'active_camera': scene.camera.name if scene.camera else None,
    'packed_images': [i.name for i in bpy.data.images if i.packed_file],
    'packed_fonts': [f.name for f in bpy.data.fonts if f.packed_file],
    'missing_dependencies': missing,
    'rendered': None,
    'scene_saved': False,
    'passed': False,
}
report_path.parent.mkdir(parents=True, exist_ok=True)
try:
    if missing:
        raise RuntimeError('Missing external dependencies')
    if scene.render.engine != expected_engine:
        raise RuntimeError('Unexpected render engine')
    if not scene.camera or len(report['cameras']) != 8:
        raise RuntimeError('Expected active camera and eight cameras')
    if should_render:
        # Retain existing artistic settings, only lower resolution and sample budget.
        aspect = scene.render.resolution_y / scene.render.resolution_x
        scene.render.resolution_x = 480
        scene.render.resolution_y = round(480 * aspect)
        scene.render.resolution_percentage = 100
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = 6
        scene.cycles.samples = 16
        scene.cycles.use_denoising = True
        scene.cycles.device = 'CPU'
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = 'OPTIX'
            prefs.get_devices()
            for device in prefs.devices:
                device.use = device.type == 'OPTIX'
            if any(d.use for d in prefs.devices):
                scene.cycles.device = 'GPU'
        except Exception as error:
            report['device_note'] = str(error)
        output = report_path.with_suffix('.png')
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        report['rendered'] = str(output)
        report['render_device'] = scene.cycles.device
    report['passed'] = True
except Exception as error:
    report['error'] = str(error)
    raise
finally:
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print('RELOCATION_CHECK', report_path.name, report['passed'], flush=True)
