"""Read-only Y3 runtime error attribution, preserving full integer IDs.

Groups exact (type, trigger, element, object) tuples, resolves live sources,
checks retained historical evidence and source protection hashes. It never
modifies the editor, map, logs or gameplay data.
"""
from __future__ import annotations
import argparse,ast,collections,hashlib,json,re
from pathlib import Path
import y3_shu_command_cards as shu

LOG_ROOT=Path('D:/Program Files/y3/games/2.0/game/LocalData/trigger_log/map3/Log')
BASELINE=shu.WORK.parent/'wu-play-review-20261018-0207/analysis.json'

def walk(node,path=''):
    if isinstance(node,dict):
        yield path,node
        for k,v in node.items():yield from walk(v,path+'/'+str(k).replace('~','~0').replace('/','~1'))
    elif isinstance(node,list):
        for i,v in enumerate(node):yield from walk(v,path+'/'+str(i))

def key(row):return row['type'],row['trigger'],row['element'],row['object']
def signature(frames):return tuple(tuple(sorted(f.items())) for f in frames)

def analyze(log_path,out):
    before=log_path.stat();raw=log_path.read_bytes();text=raw.decode('utf8',errors='replace');lines=text.splitlines()
    groups={};other=collections.Counter();severity=collections.Counter();parse_errors=[]
    for lineno,line in enumerate(lines,1):
        if '__BATTLE_SPLIT_TAG__' not in line:
            if '[Warning]' in line or '[Error]' in line:other[line.split(']:',1)[-1].strip()]+=1
            continue
        try:
            typ,tid,eid,oid,frames=ast.literal_eval(line.split('__BATTLE_SPLIT_TAG__',1)[1].strip())
        except (SyntaxError,ValueError) as ex:parse_errors.append({'line':lineno,'error':str(ex)});continue
        group=groups.setdefault((typ,tid,eid,oid),{'type':typ,'trigger':tid,'element':eid,'object':oid,
          'count':0,'first_line':lineno,'last_line':lineno,'first_time':line[:21],'last_time':line[:21],
          'severity':collections.Counter(),'stacks':{}})
        group['count']+=1;group['last_line']=lineno;group['last_time']=line[:21]
        sev='Error' if '[Error]' in line else 'Warning';severity[sev]+=1;group['severity'][sev]+=1
        sig=signature(frames);stack=group['stacks'].setdefault(sig,{'frames':frames,'count':0,'first_line':lineno});stack['count']+=1
    baseline=json.loads(BASELINE.read_text('utf8')) if BASELINE.exists() else {'groups':[]}
    old={key(row):row for row in baseline['groups']}
    target_tids={g['trigger'] for g in groups.values()}
    target_eids={g['element'] for g in groups.values()}
    for g in groups.values():
        for stack in g['stacks'].values():
            target_tids.update(f.get('trigger_id') for f in stack['frames'])
            target_eids.update(f.get('element_id') for f in stack['frames'])
    language=json.loads((shu.MAP/'zhlanguage.json').read_text('utf8'))
    index=collections.defaultdict(list);triggers=collections.defaultdict(list);hashes={}
    protection={}
    for name,folder in [('before_shu',shu.WORK),('before_table_fix',shu.WORK.parent/'shu-table-fix-20261018')]:
        p=folder/'protected-hashes.json';protection[name]=json.loads(p.read_text('utf8')) if p.exists() else {}
    for root in ('global_trigger','ability','modifier'):
        for p in (shu.MAP/root).rglob('*.json'):
            data=p.read_bytes()
            try:doc=json.loads(data)
            except (ValueError,UnicodeError):continue
            if not isinstance(doc,dict):continue
            # Standalone triggers keep children in sub_trigger; object ECA
            # keeps them in trigger_dict. Resolve both without guessing scope.
            entries=[node for _,node in walk(doc) if node.get('trigger_id') in target_tids and
                     isinstance(node.get('action'),list) and isinstance(node.get('event'),list)]
            if not entries:continue
            rel=p.relative_to(shu.MAP).as_posix();hashes[rel]=hashlib.sha256(data).hexdigest()
            oid=int(p.stem) if p.stem.isdigit() and root in ('ability','modifier') else None
            object_name=None
            if oid:
                obj=shu.MAP/'editor_table'/('abilityall' if root=='ability' else 'modifierall')/p.name
                if obj.exists():
                    object_doc=json.loads(obj.read_text('utf8'));object_name=language.get(str(object_doc.get('name')),str(object_doc.get('name')))
            for entry in entries:
                tid=entry['trigger_id'];base={'path':rel,'name':object_name or doc.get('func_name') or entry.get('trigger_name'),
                    'trigger_name':entry.get('trigger_name'),'trigger':tid,'object':oid,'func_id':doc.get('func_id'),
                    'unchanged':{label:values.get(rel)==hashes[rel] if rel in values else None for label,values in protection.items()}}
                triggers[tid].append(base)
                local_entry={k:v for k,v in entry.items() if k not in ('sub_trigger','trigger_dict')}
                for pointer,node in walk(local_entry):
                    eid=node.get('element_id')
                    if eid not in target_eids:continue
                    literal=[n.get('args_list',[None])[0] for _,n in walk(node) if n.get('sub_type')==1 and len(n.get('args_list',[]))==1 and isinstance(n['args_list'][0],(str,int,float,bool))]
                    index[tid,eid].append({**base,'pointer':pointer,'node_type':node.get('action_type') or node.get('condition_type') or node.get('event_type') or node.get('sub_type'),
                       'literals':literal[:18],'node':node})
    shu_objects={int(x) for x in json.loads((shu.WORK/'specs.json').read_text('utf8'))}|{shu.CONTROL,shu.ARMY}
    shu_tids=set()
    for folder in [shu.MAP/shu.FOLDER]:
        for p in folder.glob('*.json'):shu_tids.add(json.loads(p.read_text('utf8'))['trigger_id'])
    for root,ids in [('ability',shu_objects-{shu.CONTROL,shu.ARMY}),('modifier',{shu.CONTROL,shu.ARMY})]:
        for oid in ids:
            doc=json.loads((shu.MAP/root/f'{oid}.json').read_text('utf8'));shu_tids.update(int(x) for x in doc.get('trigger_dict',{}))
    for g in groups.values():
        candidates=index[g['trigger'],g['element']]
        g['sources']=[x for x in candidates if g['object'] is None or x['object']==g['object']]
        g['stacks']=list(g['stacks'].values())
        for stack in g['stacks']:
            stack['resolved_frames']=[{'frame':frame,'sources':index[frame.get('trigger_id'),frame.get('element_id')]} for frame in stack['frames']]
        g['direct_shu']=g['object'] in shu_objects or g['trigger'] in shu_tids
        g['shu_in_call_stack']=any(frame.get('trigger_id') in shu_tids or any(frame.get(k) in shu_objects for k in ('group_id','__group_id__')) for stack in g['stacks'] for frame in stack['frames'])
        prior=old.get(key(g));g['previous_review_match']=prior is not None
        if prior:g['prior_evidence']={k:prior[k] for k in ('line','time','count','history','old_match') if k in prior}
    result={'log':str(log_path),'log_bytes':len(raw),'log_sha256':hashlib.sha256(raw).hexdigest(),
       'first_line':lines[0] if lines else None,'last_line':lines[-1] if lines else None,
       'file_grew_during_read':log_path.stat().st_size!=before.st_size,
       'located_errors':sum(g['count'] for g in groups.values()),'unique_points':len(groups),'severity':dict(severity),
       'shu_direct_count':sum(g['count'] for g in groups.values() if g['direct_shu']),
       'shu_stack_count':sum(g['count'] for g in groups.values() if g['shu_in_call_stack']),
       'previous_review_matched_points':sum(g['previous_review_match'] for g in groups.values()),
       'previous_review_matched_count':sum(g['count'] for g in groups.values() if g['previous_review_match']),
       'other_warnings':dict(other),'parse_errors':parse_errors,'source_hashes':hashes,'groups':list(groups.values())}
    out.mkdir(parents=True,exist_ok=True);(out/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('groups','source_hashes')},ensure_ascii=False,indent=2))
    for g in sorted(groups.values(),key=lambda x:-x['count']):
        print(json.dumps({'point':key(g),'count':g['count'],'severity':dict(g['severity']),'old_match':g['previous_review_match'],
          'shu':g['direct_shu'] or g['shu_in_call_stack'],'sources':[{k:src.get(k) for k in ('path','name','trigger_name','node_type','literals','unchanged')} for src in g['sources']]},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--log',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();log=args.log or max((p for p in LOG_ROOT.glob('*.log') if p.stat().st_size),key=lambda p:p.stat().st_mtime)
    analyze(log,args.out)
