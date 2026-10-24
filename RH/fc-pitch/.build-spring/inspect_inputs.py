from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json, hashlib, re

ROOT=Path('D:/codex/RH/fc-pitch/.build-spring')
ROOT.mkdir(parents=True,exist_ok=True)
NS={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main','w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
src=Path('C:/Users/littl/Downloads/FC mobile.pptx')
with ZipFile(src) as z:
    pres=E.fromstring(z.read('ppt/presentation.xml'))
    out={'size':dict(pres.find('p:sldSz',NS).attrib),'slides':[]}
    for n in sorted([x for x in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+.xml',x)],key=lambda x:int(re.search(r'(\d+)\.xml',x)[1])):
        root=E.fromstring(z.read(n)); shapes=[]
        for sp in root.findall('.//p:sp',NS):
            text='\n'.join(''.join(p.xpath('.//a:t/text()',namespaces=NS)) for p in sp.findall('p:txBody/a:p',NS))
            shapes.append({'id':sp.find('p:nvSpPr/p:cNvPr',NS).get('id'),'name':sp.find('p:nvSpPr/p:cNvPr',NS).get('name'),'text':text,'xml':E.tostring(sp,encoding='unicode')})
        out['slides'].append({'part':n,'text':'\n'.join(root.xpath('//a:t/text()',namespaces=NS)),'shapes':shapes,'pictures':len(root.findall('.//p:pic',NS))})
    (ROOT/'ppt-source.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
    (ROOT/'ppt-source.txt').write_text('\n\n'.join(f"=== {i+1} {s['part']} ===\n{s['text']}" for i,s in enumerate(out['slides'])),encoding='utf8')
    print('PPT',out['size'],'slides',len(out['slides']))
doc=Path('C:/Users/littl/Downloads/羊名立万_春节活动策划案.docx')
with ZipFile(doc) as z:
    root=E.fromstring(z.read('word/document.xml')); lines=[]
    for p in root.findall('.//w:p',NS):
        txt=''.join(p.xpath('.//w:t/text()',namespaces=NS))
        if txt: lines.append(txt)
    (ROOT/'doc-source.txt').write_text('\n'.join(lines),encoding='utf8')
    for n in z.namelist():
        if n.startswith('word/media/'):
            dest=ROOT/'doc-assets'/Path(n).name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(z.read(n))
    print('DOC paragraphs',len(lines),'images',len(list((ROOT/'doc-assets').glob('*'))))
print('Hashes',[(p.name,hashlib.sha256(p.read_bytes()).hexdigest()) for p in (src,doc)])
