from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
import hashlib,json
root=Path('D:/codex/RH/fc-pitch')
tmp=root/'.build-web-entry'
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
rel_ns='http://schemas.openxmlformats.org/package/2006/relationships'
with ZipFile(tmp/'draft.pptx') as src, ZipFile(tmp/'candidate.pptx','w',ZIP_DEFLATED) as dst:
    target=None;relpart=None
    for name in src.namelist():
        if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
            slide=E.fromstring(src.read(name))
            button=slide.find(".//p:cNvPr[@name='open-offline-demo']",ns)
            if button is not None:
                relpart=str(Path(name).parent/'_rels'/(Path(name).name+'.rels')).replace('\\','/')
                rels=E.fromstring(src.read(relpart))
                link=next((r for r in rels if r.get('Type','').endswith('/hyperlink') and r.get('Target')=='demo.html'),None)
                if link is None: raise RuntimeError('Native text hyperlink missing')
                click=E.SubElement(button,'{'+ns['a']+'}hlinkClick')
                click.set('{'+ns['r']+'}id',link.get('Id'))
                click.set('tooltip','在本地浏览器开启网页体验')
                click.set('action','ppaction://hlinkfile')
                target=(name,E.tostring(slide,xml_declaration=True,encoding='UTF-8',standalone=True))
    if target is None: raise RuntimeError('Missing experience-entry button')
    for member in src.infolist():dst.writestr(member,target[1] if member.filename==target[0] else src.read(member.filename))
folder=root/'output'/'羊名立万-提案与网页体验'
folder.mkdir(parents=True,exist_ok=True)
web=Path('D:/codex/RH/standalone-phone/开始演示-手机版.html').read_bytes()
(folder/'demo.html').write_bytes(web)
(folder/'使用说明.txt').write_text('请先将整个ZIP解压，再打开PPTX。\n在第19页的放映模式下，点击“点击开启网页体验”，即可由本机浏览器打开活动原型。\n请保留PPTX和demo.html在同一文件夹，不要只发送PPTX。也可以直接双击demo.html离线打开。\n网页无需联网或登录，购买、比赛及奖励仅用于原型演示。\n',encoding='utf-8-sig')
print(json.dumps({'shapeHyperlinkPart':target[0],'relativeTarget':'demo.html','webSha256':hashlib.sha256(web).hexdigest(),'folder':str(folder)},ensure_ascii=False))
