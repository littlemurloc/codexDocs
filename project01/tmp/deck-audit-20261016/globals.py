from pathlib import Path
import json, re
OUT=Path(__file__).resolve().parent
ns={'__file__':str(Path('tmp/card-audit-20261014/inspect_cards.py').resolve())}
exec(Path('tmp/card-audit-20261014/inspect_cards.py').read_text('utf8').split('CARDDATA=')[0], ns)
inv=json.loads((OUT/'inventory.json').read_text('utf8'))
ids={c['id'] for c in inv['cards']}
pattern=re.compile('|'.join(str(i) for i in ids))
for rel,d in ns['DOCS'].items():
    serialized=json.dumps(d,ensure_ascii=False)
    if any(s in rel for s in ['军略','卡牌','匡扶汉室','武器锻造','8虎骑','universe03','universe05']) or pattern.search(serialized):
        content=ns['outline'](d)
        (OUT/(Path(rel).stem+'.txt')).write_text(content,encoding='utf8')
        print(rel, 'IDs',sorted(set(pattern.findall(serialized))), 'lines',len(content.splitlines()))
