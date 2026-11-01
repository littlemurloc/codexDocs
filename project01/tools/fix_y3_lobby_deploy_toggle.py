"""Scoped lobby toggle fix; never change battle recruitment or shared limits."""
from __future__ import annotations
import argparse
import copy
import csv
import gzip
import json
import os
from pathlib import Path
import subprocess
import zipfile
import y3_damage_context_optimization as base

MAP=base.MAP
PROJECT=Path(__file__).resolve().parents[1]
WORK=PROJECT/'tmp/lobby-deploy-toggle-20261031'
FIXTURE=PROJECT/'tests/fixtures/y3-lobby-deploy-toggle/source.json.gz'
REL='global_trigger/function/new/功能执行/记录英雄单位上阵信息.json'
CAP='global_trigger/function/new/条件判断/判断新上阵队长是否达到上限..json'
PROTECTED=[CAP,'global_trigger/function/new/UI/执行备战阶段UI界面队长阵型位置切换.json',
 'global_trigger/function/业务逻辑/仆从召唤功能/返回【单位类型】根据品质随机获得.json',
 'global_trigger/trigger/UI/安全区主界面.json']
FID='739fb9e279ac11f18f9a096f48f60133'
NAMES=('目标记录存在','目标原本已上阵')
FIRST_ID=2099947301000001
load,encode,sha,walk=base.load,base.encode,base.sha,base.walk


def boolean(name):
    return base.expr(100001,'VARIABLE',{'__tuple__':True,'items':['BOOLEAN',name,'local']})


def build(original):
    d=copy.deepcopy(original)
    assert d['func_id']==FID and d['trigger_id']==2008040148
    assert [a['element_id']for a in d['action']]==[2008040148000001,2008040148000136,2008040148000012]
    assert not set(NAMES)&set(d['var_data'][1]),'Already patched'
    counter=FIRST_ID-1
    def node(field,typ,*args):
        nonlocal counter
        counter+=1;n={field:typ,'args_list':list(args),'element_id':counter,'enable':True}
        if field=='action_type':n['bp']=False
        return n
    def assign(name,value):return node('action_type','SET_VARIABLE',base.expr(100030,1,*boolean(name)['args_list']),value)
    def branch(name,value,actions):return node('action_type','IF_THEN_ELSE',
        base.expr(100021,1,node('condition_type','BOOL_COMPARE',boolean(name),base.expr(100035,1,'=='),base.expr(100001,1,value))),
        base.expr(100022,1,*actions),base.expr(100022,1))
    convert,capacity,toggle=d['action']
    # Copy the exact native table traversal/match/read, including enabled optional
    # parameters. This pass only reads the target's original deployment state.
    probe=copy.deepcopy(toggle);counter+=1;probe['element_id']=counter
    match=probe['args_list'][1]['args_list'][0];counter+=1;match['element_id']=counter
    condition=match['args_list'][0]['args_list'][0];counter+=1;condition['element_id']=counter
    current_state=copy.deepcopy(toggle['args_list'][1]['args_list'][0]['args_list'][1]['args_list'][0]['args_list'][0]['args_list'][0]['args_list'][0])
    assert current_state['sub_type']=='GET_PLAYER_SAVE_TABLE_VALUE_BOOLEAN'
    assert current_state['op_arg_enable'][0] and current_state['op_arg'][0]['args_list']==['是否上阵']
    match['args_list'][1]=base.expr(100022,1,assign(NAMES[0],base.expr(100001,1,True)),
        assign(NAMES[1],current_state),node('action_type','BREAK_LOOP'))
    match['args_list'][2]=base.expr(100022,1)
    read_section=node('action_type','STORAGE_BOX',base.expr(100021,1),
        base.expr(100022,1,assign(NAMES[0],base.expr(100001,1,False)),assign(NAMES[1],base.expr(100001,1,False)),probe),
        base.expr(100022,1),base.expr(100003,1,'① 只读确认选中英雄是否存在、原本是否上阵'))
    # Preserve the existing capacity replacement and toggle subtrees verbatim.
    # An existing hero going down must never evict another deployed hero first.
    gate=branch(NAMES[0],True,[branch(NAMES[1],False,[capacity]),toggle])
    d['action']=[convert,read_section,gate]
    for name in NAMES:
        d['var_data'][0]['BOOLEAN'][name]=False;d['var_data'][1][name]=0;d['var_data'][2].append(name)
    comment='2026-10-31：先只读识别目标原上阵状态；仅新增上阵执行原满员替换，下阵只处理目标。未找到目标不写存档。局内与公共上限判断不改。'
    d['func_comment']=original.get('func_comment','')+'\n'+comment
    assert restore(d,original.get('func_comment',''))==original
    return d,counter


def restore(candidate,comment):
    d=copy.deepcopy(candidate);gate=d['action'][2]['args_list'][1]['args_list']
    capacity=gate[0]['args_list'][1]['args_list'][0];toggle=gate[1]
    d['action']=[d['action'][0],capacity,toggle]
    for name in NAMES:
        del d['var_data'][0]['BOOLEAN'][name];del d['var_data'][1][name];d['var_data'][2].remove(name)
    d['func_comment']=comment
    return d


def stage():
    assert not WORK.exists(),'Do not overwrite a reviewed stage or backup'
    raw=(MAP/REL).read_bytes();original=json.loads(raw);candidate,last=build(original)
    for root in ('global_trigger','ability','modifier','unit'):
        for p in (MAP/root).rglob('*.json'):
            assert not any(FIRST_ID<=n.get('element_id',0)<=last for _,n in walk(load(p))),'ID collision'
    source=dict(schema=1,before=original,capacity=load(MAP/CAP),note='Read-only regression input; not a map backup or deployable package')
    payload=gzip.compress(json.dumps(source,ensure_ascii=False,separators=(',',':')).encode('utf8'),mtime=0)
    FIXTURE.parent.mkdir(parents=True,exist_ok=True)
    if FIXTURE.exists():assert FIXTURE.read_bytes()==payload,'Frozen fixture changed; review before restaging'
    else:FIXTURE.write_bytes(payload)
    for folder,data in [('before',raw),('staged',encode(candidate))]:
        dest=WORK/folder/REL;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    manifest=dict(map=str(MAP),path=REL,before=sha(raw),after=sha(encode(candidate)),first_id=FIRST_ID,last_id=last,
        protected={p:sha((MAP/p).read_bytes())for p in PROTECTED},fixture_sha256=sha(payload),
        original_comment=original.get('func_comment',''),editor_verified=False,runtime_verified=False)
    (WORK/'manifest.json').write_bytes(encode(manifest))
    print('Staged one lobby function; shared cap, in-battle swap, recruitment and UI caller protected.')


def check(live=False):
    m=load(WORK/'manifest.json');assert m['map']==str(MAP) and m['path']==REL
    old=(WORK/'before'/REL).read_bytes();new=(WORK/'staged'/REL).read_bytes()
    assert sha(old)==m['before'] and sha(new)==m['after'] and sha(FIXTURE.read_bytes())==m['fixture_sha256']
    assert restore(json.loads(new),m['original_comment'])==json.loads(old)
    assert build(json.loads(old))[0]==json.loads(new)
    if live:
        assert sha((MAP/REL).read_bytes())==m['before'],'Lobby function changed; review saved version'
        assert all(sha((MAP/p).read_bytes())==h for p,h in m['protected'].items()),'Related entry changed; review again'
    return m


def publish(confirmed):
    assert confirmed,'Save and normally close editor, game and debugger first'
    assert not (WORK/'published.json').exists()
    tasks=subprocess.run(['tasklist','/fo','csv','/nh'],capture_output=True,text=True,check=True).stdout
    assert 'game_x64h.exe' not in {r[0].lower()for r in csv.reader(tasks.splitlines())if r}
    m=check(live=True);tests=load(WORK/'tests.json')
    assert tests['passed'] and tests['manifest_sha256']==sha((WORK/'manifest.json').read_bytes())
    assert all(sha((PROJECT/p).read_bytes())==h for p,h in tests['tool_hashes'].items())
    archive=WORK/'map3-before-lobby-toggle.zip';baseline={}
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_STORED,allowZip64=True)as z:
        for p in sorted(MAP.rglob('*')):
            if p.is_file()and '.git'not in p.parts:
                rel=p.relative_to(MAP).as_posix();raw=p.read_bytes();baseline[rel]=sha(raw);z.writestr(rel,raw)
    header=MAP.parents[1]/'header.project';hraw=header.read_bytes();(WORK/'header.project.before').write_bytes(hraw)
    assert all(sha((MAP/p).read_bytes())==h for p,h in baseline.items())
    check(live=True);target=MAP/REL;pending=target.with_name(target.name+'.lobby-pending')
    assert target.resolve().is_relative_to(MAP.resolve()) and not pending.exists()
    written=False
    try:
        pending.write_bytes((WORK/'staged'/REL).read_bytes());assert sha(target.read_bytes())==m['before']
        os.replace(pending,target);written=True
        assert sha(target.read_bytes())==m['after']
        assert all(sha((MAP/p).read_bytes())==h for p,h in baseline.items()if p!=REL)
        assert header.read_bytes()==hraw
    except BaseException:
        if written:pending.write_bytes((WORK/'before'/REL).read_bytes());os.replace(pending,target)
        raise
    finally:
        if pending.exists():pending.unlink()
    (WORK/'published.json').write_bytes(encode(dict(files=1,unchanged_files=len(baseline)-1,backup=str(archive),
        before=m['before'],after=m['after'],header_unchanged=True,editor_verified=False,runtime_verified=False)))
    print('Published one lobby function; actual editor loading and lobby/battle smoke test pending.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['stage','check','publish'])
    p.add_argument('--confirmed-normal-close',action='store_true');a=p.parse_args()
    if a.action=='stage':stage()
    elif a.action=='check':check(live=True);print('Candidate, inverse and live/protected hashes verified.')
    else:publish(a.confirmed_normal_close)
