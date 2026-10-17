import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tools').resolve()))
import y3_wu_command_cards as b
seen={};docs={}
for folder in ('global_trigger','ability','modifier'):
 for p in (b.MAP/folder).rglob('*.json'):
  try:d=json.loads(p.read_text('utf8'))
  except:continue
  for node in b.walk(d):
   kind=node.get('action_type',node.get('condition_type',node.get('sub_type')))
   if isinstance(kind,str):seen.setdefault(kind,(p,node))
  docs[p]=d
queries=sys.argv[1:]
for query in queries:
 print('\nQUERY',query)
 for kind,(p,node) in sorted(seen.items()):
  if query.lower() in kind.lower():
   print(kind, str(p.relative_to(b.MAP)))
   print(json.dumps(node,ensure_ascii=False)[:5000])
