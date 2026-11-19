"""Align old attribute-detail display with the existing capped calculation.

Only the display function is published. Actual stars, saves, skill unlocks,
attribute configuration and gameplay calculation are read-only dependencies.
"""
import argparse,copy,json,re,shutil,os
from pathlib import Path
import y3_hero_skill_overview as m
from safezone_ui_fixtures import retired_publish,stage as fixture_stage,result_path
b=m.b;PROJECT=b.PROJECT;ROOT=b.ROOT
WORK=Path(os.environ.get('Y3_HERO_ATTR_STAGE',str(ROOT/'tmp/hero-attribute-display-guard-20261119/revision-01')))
ATTR_TID='5cafb37d-96db-4ef9-a2a4-2d7127f45b4e';WEIGHT_TID='9ff21cc3-ee02-4b80-8804-d3fbec9f253b'
TITLE='be50f123-6eb2-471b-8bbc-52911da29a74'
GAME=b.MAP+'global_trigger/function/new/功能执行/根据升星属性给英雄队长赋值.json'
GLOBAL=b.MAP+'global_trigger/function/业务逻辑/仆从召唤功能/主角单位更新赋值仆从伙伴属性.json'
BASE=2101120500

def build(source,cap):
    d=copy.deepcopy(source);n=b.Nodes(BASE);p=b.ref('PLAYER','执行玩家')
    actual=b.ref('INTEGER','伙伴星级');effective=b.s.declare(d,'INTEGER','属性配置星级')
    block=d['action'][5];actions=block['args_list'][1]['args_list']
    assert actions[0]['action_type']=='ITER_UI_COMP_DO'and actions[-1]['action_type']=='LIST_LOOP'
    # Change only the two computed attribute-column keys, never the actual star.
    count=0
    for z in b.walk(actions[1:3]):
        if z==actual:z['args_list']=copy.deepcopy(effective['args_list']);count+=1
    assert count==2
    read=actions[1:3];parse=actions[3:]
    # Reuse this function's native scalar STRING references exactly. Generic
    # STRING/VARIABLE expressions were erased to null by the native editor.
    assert [a['action_type']for a in parse[:2]]==['SET_VARIABLE_STR_LIST','SET_VARIABLE_STR_LIST']
    types=copy.deepcopy(parse[0]['args_list'][1]);values=copy.deepcopy(parse[1]['args_list'][1])
    assert types['arg_type']==values['arg_type']==100003 and types['sub_type']==values['sub_type']==2
    block['args_list'][1]['args_list']=[actions[0],n.set(effective,actual),
        n.label(p,b.u(TITLE),'主角属性加成'),
        n.branch([n.cmp(actual,'>',b.integer(cap))],[n.set(effective,b.integer(cap)),
            n.label(p,b.u(TITLE),f'主角属性加成（按{cap}星配置）')]),
        n.branch([n.cmp(effective,'>=',b.integer(1))],read+[
            n.branch([n.cmp(types,'!=',b.text(''),'STRING_COMPARE'),n.cmp(values,'!=',b.text(''),'STRING_COMPARE')],parse)])]
    return d

def paths():
    result=[b.HD,b.UI,GAME,GLOBAL]
    for p in(PROJECT/b.MAP/'tables').glob('*.json'):
        if b.load(p).get('tid')in [ATTR_TID,WEIGHT_TID]:result.append(p.relative_to(PROJECT).as_posix())
    return result

def stage():
    """Retired after closeout; never publish a historical stage again."""
    retired_publish()
def publish():
    """Retired after closeout; never publish a historical stage again."""
    retired_publish()
def verify_native():
    source=WORK if(WORK/'candidate'/b.HD).exists()else fixture_stage('attributes')
    expected=b.load(source/'candidate'/b.HD);actual=b.load(PROJECT/b.HD);before=b.load(source/'before'/b.HD)
    def clean(x):
        if isinstance(x,dict):return{k:clean(v)for k,v in x.items()if k!='fake_op'}
        if isinstance(x,list):return[clean(v)for v in x]
        return x
    expected_refs=[n['args_list'][0]for n in b.walk(expected['action'][5])if n.get('condition_type')=='STRING_COMPARE']
    actual_refs=[n['args_list'][0]for n in b.walk(actual['action'][5])if n.get('condition_type')=='STRING_COMPARE']
    old_ids={n['element_id']for n in b.walk(before)if'element_id'in n}
    saved_new_branches=sum(1 for n in b.walk(actual)if n.get('element_id')not in old_ids and n.get('action_type')=='IF_THEN_ELSE'and'fake_op'in n)
    checks=dict(function_valid=actual['valid'],native_string_refs_preserved=actual_refs==expected_refs,
        action_semantics_preserved=clean(actual['action'])==clean(expected['action']),
        identity_preserved=all(actual[k]==expected[k]for k in ['func_id','trigger_id','func_param_list']),
        native_saved_new_branches=saved_new_branches,actual_sha256=b.sha((PROJECT/b.HD).read_bytes()),runtime_acceptance='pending')
    checks['passed']=all(checks[k]for k in ['function_valid','native_string_refs_preserved','action_semantics_preserved','identity_preserved'])and saved_new_branches==3
    result_path('attribute-live-readback').write_bytes(b.encode(checks));print(json.dumps(checks))
    return checks['passed']
if __name__=='__main__':
    args=argparse.ArgumentParser();args.add_argument('mode',choices=['stage','publish','verify-native']);mode=args.parse_args().mode
    if mode=='stage':stage()
    elif mode=='verify-native':raise SystemExit(0 if verify_native()else 1)
    else:publish()
