from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
import json,hashlib,io,posixpath
root=Path('D:/codex/RH/fc-pitch')
folder=root/'output'/'羊名立万-提案与网页体验'
ppt=folder/'FC mobile-羊名立万-含网页体验.pptx'
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
with ZipFile(ppt) as z:
    slide=E.fromstring(z.read('ppt/slides/slide19.xml'))
    button=slide.find(".//p:cNvPr[@name='open-offline-demo']",ns)
    click=button.find('a:hlinkClick',ns)
    assert click is not None
    rels=E.fromstring(z.read('ppt/slides/_rels/slide19.xml.rels'))
    rel=next(r for r in rels if r.get('Id')==click.get('{'+ns['r']+'}id'))
    assert rel.get('Target')=='demo.html' and rel.get('TargetMode')=='External'
    assert (folder/rel.get('Target')).is_file()
    assert any(h.get('{'+ns['r']+'}id')==rel.get('Id') for h in slide.findall('.//a:rPr/a:hlinkClick',ns))
web=(folder/'demo.html').read_bytes()
assert web==Path('D:/codex/RH/standalone-phone/开始演示-手机版.html').read_bytes()
archive=root/'output'/'羊名立万-提案与网页体验.zip'
with ZipFile(archive,'w',ZIP_DEFLATED) as z:
    for p in sorted(folder.iterdir()):
        if p.is_file():z.write(p,folder.name+'/'+p.name)
with ZipFile(archive) as z:
    assert len(z.namelist())==3
    nested=folder.name+'/'+ppt.name
    with ZipFile(io.BytesIO(z.read(nested))) as deck:
        rels=E.fromstring(deck.read('ppt/slides/_rels/slide19.xml.rels'))
        link=next(r.get('Target') for r in rels if r.get('Type','').endswith('/hyperlink'))
        assert posixpath.normpath(posixpath.join(posixpath.dirname(nested),link)) in z.namelist()
    assert z.read(folder.name+'/demo.html')==web
record={'status':'passed','slide':19,'relativeLink':'demo.html','wholeButtonAndTextLinked':True,'webIdenticalToLatestPhoneVersion':True,'portableArchiveContainsLinkedTarget':True,'archive':str(archive),'archiveBytes':archive.stat().st_size,'pptxBytes':ppt.stat().st_size,'nativePowerPointClickTest':'not performed'}
(root/'.build-web-entry'/'package-check.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(record,ensure_ascii=False))
