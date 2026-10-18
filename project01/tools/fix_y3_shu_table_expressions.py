"""Repair runtime TABLE expressions accidentally encoded as resource literals.

Only functions 03, 15 and 18 are eligible. Preserve all other live fields and
require the corrected actions to match the maintained generator exactly.
"""
from __future__ import annotations
import argparse,copy,json,os,zipfile
from pathlib import Path
import y3_shu_command_cards as s
WORK=s.WORK.parent/'shu-table-fix-20261018'
STAGE=WORK/'staged'
EXPECTED={3:6,15:1,18:1}

def repair_tree(obj):
    count=0
    def visit(v):
        nonlocal count
        if isinstance(v,list):return [visit(x) for x in v]
        if not isinstance(v,dict):return v
        if v.get('arg_type')==100011 and v.get('sub_type')==1:
            args=v.get('args_list',[])
            if len(args)==1 and isinstance(args[0],dict) and args[0].get('arg_type')==100011:
                assert set(v)=={'arg_type','sub_type','args_list'},'Unexpected literal metadata'
                count+=1;return visit(args[0])
        return {k:visit(x) for k,x in v.items()}
    return visit(obj),count

def comparison_tree(obj):
    if isinstance(obj,list):return [comparison_tree(x) for x in obj]
    if not isinstance(obj,dict):return obj
    result={k:comparison_tree(v) for k,v in obj.items()}
    # Y3 materializes disabled optional slots when a page is opened. They have
    # no execution effect and must be preserved in the surgical candidate.
    if 'op_arg_enable' in result and not any(result['op_arg_enable']):
        result.pop('op_arg_enable',None);result.pop('op_arg',None)
    return result

def stage():
    assert not (WORK/'published.json').exists(),'Repair already published'
    WORK.mkdir(parents=True,exist_ok=True)
    rules=json.loads((s.WORK/'attribute-rules.json').read_text('utf8'))
    generated=s.build_functions(rules,require_level5=True)
    manifest={}
    with zipfile.ZipFile(WORK/'before-table-fix.zip','w',compression=zipfile.ZIP_DEFLATED) as backup:
        for index,expected in EXPECTED.items():
            rel=f'{s.FOLDER}/{s.NAMES[index]}.json';raw=(s.MAP/rel).read_bytes();original=json.loads(raw)
            candidate,count=repair_tree(original);assert count==expected,(index,count)
            assert comparison_tree(candidate['action'])==comparison_tree(generated[rel]['action']),'Generator differs from surgical repair: '+rel
            assert candidate['func_id']==s.FIDS[index]
            candidate['valid']=True
            target=STAGE/rel;target.parent.mkdir(parents=True,exist_ok=True)
            after=(json.dumps(candidate,ensure_ascii=True,indent=4)+'\n').encode('utf8');target.write_bytes(after)
            backup.writestr(rel,raw)
            manifest[rel]={'before':s.sha(raw),'after':s.sha(after),'fixed_expressions':count}
    (WORK/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print('Staged 3 functions; 8 table-expression wrappers removed; generator actions match exactly.')

def publish(apply):
    assert s.MAP.resolve()==Path('D:/littl/testTempFile/ProjectMonster02/maps/map3').resolve()
    manifest=json.loads((WORK/'manifest.json').read_text('utf8'))
    assert set(manifest)=={f'{s.FOLDER}/{s.NAMES[i]}.json' for i in EXPECTED}
    with zipfile.ZipFile(WORK/'before-table-fix.zip') as backup:
        for rel,record in manifest.items():
            assert s.sha((s.MAP/rel).read_bytes())==record['before'],'Live changed: '+rel
            assert s.sha(backup.read(rel))==record['before']
            candidate=(STAGE/rel).read_bytes();assert s.sha(candidate)==record['after']
            repaired,count=repair_tree(json.loads(backup.read(rel)))
            repaired['valid']=True
            assert repaired==json.loads(candidate) and count==record['fixed_expressions']
    print('Preflight passed: exactly 3 functions; 8 expression fixes; no table, number or route edits.')
    if not apply:return
    assert not (WORK/'published.json').exists(),'Already published'
    protected={}
    for folder in ('ability','modifier','global_trigger','editor_table','tables'):
        for p in (s.MAP/folder).rglob('*.json'):
            rel=p.relative_to(s.MAP).as_posix()
            if rel not in manifest:protected[rel]=s.sha(p.read_bytes())
    done=[]
    try:
        for rel in manifest:
            dest=(s.MAP/rel).resolve();assert s.MAP.resolve() in dest.parents
            pending=dest.with_name(dest.name+'.codex-table-fix-pending');assert not pending.exists()
            try:pending.write_bytes((STAGE/rel).read_bytes());os.replace(pending,dest)
            finally:
                if pending.exists():pending.unlink()
            done.append(rel)
        for rel,rec in manifest.items():assert s.sha((s.MAP/rel).read_bytes())==rec['after']
        for rel,h in protected.items():assert s.sha((s.MAP/rel).read_bytes())==h,'Protected changed: '+rel
    except BaseException:
        with zipfile.ZipFile(WORK/'before-table-fix.zip') as backup:
            for rel in reversed(done):(s.MAP/rel).write_bytes(backup.read(rel))
        raise
    (WORK/'protected-hashes.json').write_text(json.dumps(protected,ensure_ascii=False,indent=2),encoding='utf8')
    (WORK/'published.json').write_text(json.dumps({'manifest':manifest,'map':str(s.MAP),'editor_page_verified':False,'game_verified':False},ensure_ascii=False,indent=2),encoding='utf8')
    print('Published 3 repaired functions;',len(protected),'other resources hash-protected.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['stage','publish']);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if args.command=='stage':stage()
    else:publish(args.apply)
