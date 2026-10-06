from pathlib import Path
import struct, io, json
from PIL import Image
from inspect_y3_resource import decode

ROOT = Path(r'D:\CliCli\games\2.0\game\LocalData\Patch')
OUT = Path(r'D:\codex\project01\assets\art\characters\lvbu\y3-texture-silver-ice-v01')
OUT.mkdir(parents=True, exist_ok=True)
TEXTURES = {
    'original-material-1-basecolor': '01/0124172b-8d30-d76d-66b1-fa59578a7ad4.6',
    'original-material-2-basecolor': 'af/aff15f17-7d43-e2bb-7110-9ff1e79a9e52.6',
}
metadata=[]
for name, rel in TEXTURES.items():
    b=(ROOT/rel).read_bytes()
    p=40
    mips=[]
    while p<len(b):
        n,w,h,depth,row,length=struct.unpack_from('<IHHHHI',b,p)
        payload=b[p+16:p+n]
        if payload.startswith(b'NNNN'):
            data=payload[4:]
        else:
            data=decode(payload)
        assert len(data)==length,(len(data),length)
        mips.append((w,h,data))
        p+=n
    w,h,data=mips[-1]
    fourcc=b'DXT1' if len(data)==w*h//2 else b'DXT5'
    header=bytearray(124)
    struct.pack_into('<7I',header,0,124,0x81007,h,w,len(data),0,1)
    struct.pack_into('<2I',header,72,32,4)
    header[80:84]=fourcc
    struct.pack_into('<I',header,104,0x1000)
    dds=b'DDS '+header+data
    (OUT/(name+'.dds')).write_bytes(dds)
    im=Image.open(io.BytesIO(dds))
    im.save(OUT/(name+'.png'))
    entry={'name':name,'source':str(ROOT/rel),'size':[w,h],'block_format':fourcc.decode(),'mode':im.mode,'alpha_extrema':im.getchannel('A').getextrema() if 'A' in im.getbands() else None,'mip_sizes':[[x[0],x[1]] for x in mips]}
    print(entry)
    metadata.append(entry)
(OUT/'original-texture-metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
