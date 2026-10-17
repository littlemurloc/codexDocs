import sys,json,hashlib,collections
from pathlib import Path
sys.path.insert(0,str(Path('tools').resolve()))
import refactor_y3_wu_cards as r
def load(p):return json.loads(p.read_text('utf8'))
manifest=load(r.WORK/'manifest.json')
original=r.b.STAGE
for rel in manifest:
 if not rel.startswith(('ability/','modifier/')):continue
 path=r.b.MAP/rel
 expected=Path('tmp/wu-fix-20261017/controller-fixed.json') if rel=='modifier/134285001.json' else original/rel
 live=load(path);prior=load(expected)
 def normalize(doc):
  for node in r.b.walk(doc):node.pop('valid',None)
  return doc
 assert normalize(live)==normalize(prior),'User modifications require review: '+rel
def counts(d):
 return collections.Counter(n['action_type'] for n in r.b.walk(d) if 'action_type' in n)
old=collections.Counter();new=collections.Counter()
for rel in manifest:
 if not rel.startswith(('ability/','modifier/','global_trigger/function/')) or not rel.endswith('.json'):continue
 if (r.b.MAP/rel).exists():old+=counts(load(r.b.MAP/rel))
 new+=counts(load(r.STAGE/rel))
print('Action nodes before/after:',sum(old.values()),sum(new.values()))
print('Hardcoded card lookups before:',old['SET_ENTITY_KV'],'new:',new['SET_ENTITY_KV'])
for oid in (r.b.CONTROL,r.b.ARMY):
 rel=f'modifier/{oid}.json'
 print('Buff',oid,'actions',sum(counts(load(r.b.MAP/rel)).values()),'->',sum(counts(load(r.STAGE/rel)).values()))
# Compare native node signatures with real source schemas, ignoring entity generic type variations separately.
known={};live_trigger_ids=set();live_func_ids=set();live_table_ids=set()
for p in r.b.MAP.rglob('*.json'):
 try:doc=load(p)
 except:continue
 if not isinstance(doc,dict):continue
 if doc.get('func_id'):live_func_ids.add(doc['func_id'])
 if doc.get('tid'):live_table_ids.add(doc['tid'])
 for node in r.b.walk(doc):
  if 'trigger_id' in node:live_trigger_ids.add(node['trigger_id'])
  for tag in ('action_type','condition_type','sub_type'):
   typ=node.get(tag)
   if isinstance(typ,(str,int)) and 'args_list' in node:
    signature=tuple(x.get('arg_type') if isinstance(x,dict) else type(x).__name__ for x in node['args_list'])
    known.setdefault((tag,typ),set()).add(signature)
unknown=set()
for rel in manifest:
 doc=load(r.STAGE/rel)
 if doc.get('func_id'):assert doc['func_id'] not in live_func_ids
 if doc.get('tid'):assert doc['tid'] not in live_table_ids
 if doc.get('trigger_id'):assert doc['trigger_id'] not in live_trigger_ids
 for node in r.b.walk(doc):
  if node.get('trigger_id') and rel.startswith(('ability/','modifier/')):assert node['trigger_id'] not in live_trigger_ids
  for tag in ('action_type','condition_type','sub_type'):
   typ=node.get(tag)
   if not isinstance(typ,(str,int)) or 'args_list' not in node:continue
   if typ in r.FIDS.values() or isinstance(typ,int):continue
   signature=tuple(x.get('arg_type') if isinstance(x,dict) else type(x).__name__ for x in node['args_list'])
   if signature not in known.get((tag,typ),set()):unknown.add((tag,typ,signature))
print('Signatures for individual review:',sorted(unknown,key=str))
print('Live 33 ECAs match corrected previous delivery; no manual edits overwritten.')
