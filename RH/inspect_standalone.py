from pathlib import Path
import re,json
p=Path('C:/Users/littl/Downloads/standalone.html')
s=p.read_text(encoding='utf-8')
out=Path('D:/codex/RH/standalone-phone/.build')
out.mkdir(parents=True,exist_ok=True)
clean=re.sub(r'data:[^\s"\x27<>)]{180,}',lambda m:'[EMBEDDED_RESOURCE:'+str(len(m[0]))+']',s)
clean=re.sub(r'([A-Za-z0-9+/]{500,}={0,2})',lambda m:'[BASE64:'+str(len(m[0]))+']',clean)
(out/'source-readable.html').write_text(clean,encoding='utf-8')
print('original',len(s),'readable',len(clean),'scripts',len(re.findall('<script',s)))
