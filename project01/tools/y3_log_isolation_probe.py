"""Build disposable native-log probes from an unrelated Y3 sample project.

Does not read or write ProjectMonster02. Opening, saving and gameplay must
be verified separately; JSON generation alone is not a compatibility test.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import uuid

SOURCE=Path(r'D:/Program Files/y3/games/2.0/game/LocalData/ProjectDemo01')
WORK=Path(__file__).resolve().parents[1]/'tmp/y3-log-isolation-20261023'
FID='4ec5848498434b6d9df79a9083128fb3'


def read(p):return json.loads(p.read_text('utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=4)+'\n',encoding='utf8')
def arg(t,s,*a):return dict(arg_type=t,sub_type=s,args_list=list(a))
def node(k,i,*a):return dict(action_type=k,element_id=i,args_list=list(a),bp=False,enable=True)


def prepare(stage):
    assert stage in ('A','B')
    target=WORK/('ProjectLogProbe_'+stage)
    assert not target.exists(),'Never overwrite a probe that may be open'
    assert target.resolve().is_relative_to(WORK.resolve())
    shutil.copytree(SOURCE,target,ignore=shutil.ignore_patterns('.git','lock'))
    header=read(target/'header.project')
    header['project_name']='CodexLogProbe_'+stage
    header['project_id']=uuid.uuid4().int
    save(target/'header.project',header)
    root=target/'maps/EntryMap'
    # Disable unrelated sample systems without deleting their original files.
    for p in (root/'global_trigger/trigger').rglob('*.json'):
        d=read(p);d['enabled']=False;save(p,d)
    main=root/'global_trigger/trigger/New trigger.json'
    d=read(main);d['enabled']=True
    message='CODEX_LOG_PROBE_'+stage+'_NATIVE_SUCCESS'
    if stage=='A':
        d['action']=[node('PRINT_MESSAGE_ACTION_TO_DIALOG',209997100100001,
                        arg(100175,1,3),arg(100003,1,message))]
    else:
        func=dict(action=[node('PRINT_MESSAGE_ACTION_TO_DIALOG',209997100200001,
            arg(100175,1,3),arg(100003,2,{'__tuple__':True,'items':['STRING','日志文本','local']}))],
            call_enabled=True,condition=[],enabled=True,event=[],func_category='t_function',
            func_comment='Isolated probe: one string parameter and one native print action.',
            func_des='输出测试日志{日志文本}',func_id=FID,func_name='CodexLogProbeFunction',
            func_param_list=[{'__tuple__':True,'items':['日志文本',True]}],group_id=0,
            is_func=True,is_official_func=False,p_trigger_id=None,trigger_id=2099971002,
            trigger_name='CodexLogProbeFunction',valid=True,
            var_data=[{'STRING':{'日志文本':''}},{'日志文本':0},['日志文本']])
        folder=root/'global_trigger/function';save(folder/'CodexLogProbeFunction.json',func)
        index=read(folder/'index.txt');index['CodexLogProbeFunction.json']=max(index.values(),default=-1)+1
        save(folder/'index.txt',index)
        call=arg(100177,FID,arg(100003,1,message));call.update(op_arg=[],op_arg_enable=[])
        d['action']=[node('CALL_TRIGGER_FUNC',209997100100002,call)]
    save(main,d)
    receipt=dict(stage=stage,project=str(target),map='EntryMap',map_id=header['entry_map']['id'],
                 project_id=header['project_id'],message=message,
                 trigger_sha256=hashlib.sha256(main.read_bytes()).hexdigest(),
                 boundary='Prepared only; no editor or gameplay result yet.')
    save(WORK/('prepared_'+stage+'.json'),receipt)
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['A','B']);a=p.parse_args();prepare(a.stage)
