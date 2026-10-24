"""Refresh Xiahou Yuan's target list without clearing a borrowed team group."""
from copy import deepcopy as cp
import argparse
import json
import shutil

import y3_hero_runtime_followup_20261024 as base
import y3_hero_runtime_followup_r4_20261024 as previous

ROOT=base.ROOT
WORK=previous.WORK.parent/'hero-followup-20261024-r5'
FILES=['ability/134256160.json']
PREFIX='[技能排查/20261024-r5] '
LOG=previous.LOG.parent/'littlemurloc_2026_10_24_10_53_28.log'


def summer(source):
    d=cp(source);b=base.Builder(d);b.index=209997100100000
    phase=d['trigger_dict']['82759685']
    clear=base.one(phase['action'],'CLEAR_GROUP',82759685000003)
    phase['action'].remove(clear)
    assignment=base.one(phase['action'],'SET_VARIABLE',82759685000015)
    lookup=cp(assignment['args_list'][1])
    assert lookup['sub_type']=='869622f5961411f1933a3fb31c846afd'
    assert lookup['call_rt_index']==1
    timer=base.one(d['trigger_dict']['1959489540']['action'],'RUN_LOOP_TIMER')
    pick=base.one(timer,'PICK_UNIT_DO_ACTION',1959489540974224)
    group=base.var('UNIT_GROUP','搜索组','actor')
    # Refresh only after phase, owner, cooldown and action-state guards pass.
    # Do not clear this value: it aliases a shared group returned by the helper.
    base.replace_action(timer,pick['element_id'],[b.set(group,lookup),cp(pick)])
    return d


def build(root):
    return {FILES[0]:summer(base.trace.read(root/FILES[0]))}


def configure():
    base.WORK,base.FILES,base.build,base.PREFIX=WORK,FILES,build,PREFIX


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','publish','verify']);a=p.parse_args().action
    configure()
    if a=='prepare':
        base.prepare();shutil.copy2(LOG,WORK/'runtime-before.log')
    elif a=='publish':base.publish()
    else:
        result=base.verify()
        assert all(t.get('valid') for t in base.trace.read(ROOT/FILES[0])['trigger_dict'].values())
        result['all_triggers_valid']=True
        base.trace.save(WORK/'editor-verified.json',result)
        print(json.dumps(result))
