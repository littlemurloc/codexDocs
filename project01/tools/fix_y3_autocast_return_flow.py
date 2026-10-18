"""Repair only the auto-cast helper's return-value fall-through regression.

Keep the 74 caller ECA files and the separate formation guard untouched. Use
one result variable, mutually exclusive branches and one final result node.
"""
from __future__ import annotations
import argparse,copy,json,os,zipfile
import fix_y3_combat_warning_guards as base

WORK=base.WORK.parent/'autocast-return-fix-20261018'
STAGE=WORK/'staged'

def stage():
    assert not (WORK/'manifest.json').exists(),'Do not overwrite existing repair evidence'
    original=base.load(base.MAP/base.HELPER)
    assert original['func_id']==base.FID and original['trigger_id']==base.TID
    # Opening/saving a native ECA page can rewrite JSON whitespace and key
    # order. Require exact semantic identity, then protect the actual bytes.
    assert original==base.load(base.STAGE/base.HELPER),'Helper logic changed since initial publication'
    used={n['element_id'] for root in ('ability','modifier','global_trigger')
          for p in (base.MAP/root).rglob('*.json') for _,n in base.walk(base.load(p)) if 'element_id' in n}
    nodes=base.Nodes(used);nodes.serial=base.TID*1000000+100000
    generated=base.make_helper(nodes);fixed=copy.deepcopy(original)
    for field in ('action','var_data','func_comment'):fixed[field]=copy.deepcopy(generated[field])
    assert fixed==generated,'Unexpected helper metadata; preserve and inspect before editing'
    result_nodes=[(path,node) for path,node in base.walk(fixed) if node.get('action_type')==400342]
    assert len(result_nodes)==1 and result_nodes[0][0]==('action',2)
    assert result_nodes[0][1]['args_list'][0]['sub_type']=='VARIABLE'
    raw=(base.MAP/base.HELPER).read_bytes();after=base.encode(fixed)
    WORK.mkdir(parents=True,exist_ok=True);target=STAGE/base.HELPER;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(after)
    with zipfile.ZipFile(WORK/'before-return-fix.zip','w',zipfile.ZIP_DEFLATED) as backup:backup.writestr(base.HELPER,raw)
    manifest={base.HELPER:{'before':base.sha(raw),'after':base.sha(after)}}
    protected={p.relative_to(base.MAP).as_posix():base.sha(p.read_bytes()) for p in base.MAP.rglob('*')
               if p.is_file() and p.suffix in ('.json','.txt','.lua') and p.relative_to(base.MAP).as_posix()!=base.HELPER}
    (WORK/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    (WORK/'protected-hashes.json').write_text(json.dumps(protected,ensure_ascii=False,indent=2),encoding='utf8')
    print('Staged helper-only repair; one final result node; all 74 callers and formation guard protected.')

def publish(apply=False):
    assert not (WORK/'published.json').exists(),'Already published'
    record=base.load(WORK/'manifest.json')[base.HELPER];dest=(base.MAP/base.HELPER).resolve()
    assert base.MAP.resolve() in dest.parents
    assert base.sha(dest.read_bytes())==record['before'],'Concurrent helper edit'
    raw=(STAGE/base.HELPER).read_bytes();assert base.sha(raw)==record['after']
    with zipfile.ZipFile(WORK/'before-return-fix.zip') as backup:assert base.sha(backup.read(base.HELPER))==record['before']
    protected=base.load(WORK/'protected-hashes.json')
    for rel,digest in protected.items():assert base.sha((base.MAP/rel).read_bytes())==digest,'Protected file changed: '+rel
    print('Preflight passed: 1 helper,',len(protected),'protected files.')
    if not apply:return
    pending=dest.with_name(dest.name+'.codex-return-fix-pending');assert not pending.exists()
    try:
        pending.write_bytes(raw);os.replace(pending,dest)
        assert base.sha(dest.read_bytes())==record['after']
        for rel,digest in protected.items():assert base.sha((base.MAP/rel).read_bytes())==digest,'Protected file changed: '+rel
    except BaseException:
        with zipfile.ZipFile(WORK/'before-return-fix.zip') as backup:dest.write_bytes(backup.read(base.HELPER))
        raise
    finally:
        if pending.exists():pending.unlink()
    (WORK/'published.json').write_text(json.dumps({'helper':base.HELPER,'editor_verified':False,'game_verified':False},ensure_ascii=False,indent=2),encoding='utf8')
    print('Published helper-only repair; all other resources unchanged.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['stage','publish']);p.add_argument('--apply',action='store_true');args=p.parse_args()
    if args.command=='stage':stage()
    else:publish(args.apply)
