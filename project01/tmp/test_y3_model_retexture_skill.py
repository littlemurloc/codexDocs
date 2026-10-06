from pathlib import Path
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
from PIL import Image, ImageChops

SKILL=Path(r'D:\codex\project01\tmp\skill-build\y3-model-retexture')
SCRIPT=SKILL/'scripts/y3_texture.py'
CACHE=Path(r'D:\CliCli\games\2.0\game\LocalData\Patch')
OLD_CACHE=Path(r'D:\Program Files\y3\games\2.0\game\LocalData\Patch')
ART=Path(r'D:\codex\project01\assets\art\characters\lvbu\y3-texture-silver-ice-v01')
OUT=Path(tempfile.mkdtemp(prefix='y3-skill-validation-',dir=r'D:\codex\project01\tmp'))

def run(*args, succeeds=True):
    result=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True,encoding='utf-8')
    if succeeds:
        assert result.returncode==0,result.stderr
        return json.loads(result.stdout)
    assert result.returncode!=0 and result.stderr, result.stdout
    return result.stderr.strip()

spec=importlib.util.spec_from_file_location('texture_helpers',SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.unpack_resource(b'ZZZ4'+struct.pack('<I',4)+b'\x40abcd')[0]==b'abcd'
assert module.unpack_resource(b'ZZZ4'+struct.pack('<I',6)+b'\x11a\x01\x00')[0]==b'aaaaaa'
try:
    module.unpack_resource(b'ZZZ4'+struct.pack('<I',5)+b'\x40abcd')
    raise AssertionError('Truncated decoded data was accepted')
except ValueError:
    pass

repo=run('repository','--source',OLD_CACHE/'resource.repository','--query','504061')
assert any(e['name']=='504061_d' and e['guid']=='0124172b-8d30-d76d-66b1-fa59578a7ad4' for e in repo['entries'])
assert repo['decoded_size']==16328701 and not repo['warnings']
mat=run('material','--source',CACHE/'2b/2baa7546-56cc-ac44-2c7d-bffcefd58b5b')
bases=[e['guid'] for e in mat['references_in_file_order'] if e['parameter']=='tBaseMap']
assert bases==['0124172b-8d30-d76d-66b1-fa59578a7ad4','aff15f17-7d43-e2bb-7110-9ff1e79a9e52']

for number,rel in [(1,'01/0124172b-8d30-d76d-66b1-fa59578a7ad4.6'),(2,'af/aff15f17-7d43-e2bb-7110-9ff1e79a9e52.6')]:
    record=run('extract','--source',CACHE/rel,'--output',OUT/f'original-{number}')
    with Image.open(OUT/f'original-{number}.png') as actual, Image.open(ART/f'original-material-{number}-basecolor.png') as expected:
        assert actual.size==expected.size
        assert ImageChops.difference(actual.convert('RGB'),expected.convert('RGB')).getbbox() is None
    assert record['alpha_extrema']==[255,255]
bc3=run('extract','--source',OLD_CACHE/'57/5714aa40-d045-2fec-3607-dd679ec48e22.6','--output',OUT/'bc3')
assert bc3['block_format']=='DXT5' and bc3['size']==[512,512]

for number,name in [(1,'lvbu-body-silver-ice-v01'),(2,'lvbu-weapon-silver-ice-v01')]:
    record=run('prepare','--source',ART/(name+'-master.png'),'--reference',OUT/f'original-{number}.png','--output',OUT/(name+'.png'))
    with Image.open(OUT/(name+'.png')) as actual, Image.open(ART/(name+'.png')) as expected:
        assert actual.size==expected.size
        assert ImageChops.difference(actual,expected).getbbox() is None

failures=[]
failures.append(run('prepare','--source',ART/'lvbu-weapon-silver-ice-v01-master.png','--reference',OUT/'original-1.png','--output',OUT/'bad-ratio.png',succeeds=False))
Image.new('RGBA',(512,512),(255,255,255,0)).save(OUT/'alpha-reference.png')
failures.append(run('prepare','--source',ART/'lvbu-body-silver-ice-v01-master.png','--reference',OUT/'alpha-reference.png','--output',OUT/'bad-alpha.png',succeeds=False))
failures.append(run('extract','--source',CACHE/'01/0124172b-8d30-d76d-66b1-fa59578a7ad4.6','--output',OUT/'original-1',succeeds=False))
unknown=bytearray((CACHE/'01/0124172b-8d30-d76d-66b1-fa59578a7ad4.6').read_bytes())
unknown[5]=255
(OUT/'unknown-format').write_bytes(unknown)
failures.append(run('extract','--source',OUT/'unknown-format','--output',OUT/'unknown',succeeds=False))
assert not any((OUT/name).exists() for name in ['bad-ratio.png','bad-alpha.png','unknown.png'])
print(json.dumps({'status':'passed','output':str(OUT),'checks':['LZ4 literal and overlapping copies','truncated size rejected','actual repository exact decoded length and GUID lookup','actual material base map order','both BC1 images pixel-identical to prior extraction','BC3 decoded and dimensions checked','both normalized outputs pixel-identical to delivery','aspect ratio, useful Alpha, overwrite and unknown format rejected'],'expected_failures':failures},ensure_ascii=True,indent=2))
