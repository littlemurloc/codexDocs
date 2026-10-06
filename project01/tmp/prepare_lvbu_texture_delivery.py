from pathlib import Path
from PIL import Image
import json, hashlib, zipfile

OUT=Path(r'D:\codex\project01\assets\art\characters\lvbu\y3-texture-silver-ice-v01')
JOBS=[('lvbu-body-silver-ice-v01',(512,512)),('lvbu-weapon-silver-ice-v01',(256,512))]
records=[]
for name,size in JOBS:
    master=OUT/(name+'-master.png')
    im=Image.open(master)
    assert im.width*size[1]==im.height*size[0], (name,im.size,size)
    native_size=im.size
    if im.size!=size:
        im=im.resize(size,Image.Resampling.LANCZOS)
    # Deliver standard RGB PNGs: the source textures have no transparent pixels.
    if im.mode!='RGB':
        if 'A' in im.getbands(): assert im.getchannel('A').getextrema()==(255,255)
        im=im.convert('RGB')
    final=OUT/(name+'.png')
    im.save(final)
    verify=Image.open(final)
    assert verify.size==size and verify.mode=='RGB'
    records.append({'file':final.name,'size':list(verify.size),'mode':verify.mode,'generator_master_size':list(native_size),'sha256':hashlib.sha256(final.read_bytes()).hexdigest()})
(OUT/'final-texture-metadata.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
package=Path(r'D:\codex\project01\deliverables\lvbu-silver-ice-textures-v01.zip')
package.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):
        if p.is_file() and '-master' not in p.name:
            z.write(p,p.name)
print(json.dumps({'textures':records,'package':str(package)},ensure_ascii=True,indent=2))
