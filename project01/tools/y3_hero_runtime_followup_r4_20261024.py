"""Refresh Zhang Liao's mark lifetime; distinguish Xiahou Yuan cast instances."""
from copy import deepcopy as cp
import argparse
import json
import shutil

import y3_hero_runtime_followup_20261024 as base
import y3_hero_runtime_followup_r3_20261024 as previous

ROOT = base.ROOT
WORK = previous.WORK.parent/'hero-followup-20261024-r4'
FILES = ['editor_table/modifierall/134259870.json', 'ability/134256160.json']
PREFIX = '[技能排查/20261024-r4] '
LOG = previous.LOG.parent/'littlemurloc_2026_10_24_10_36_31.log'
ex, lit, walk = base.ex, base.lit, base.walk


def note(b, label, *values):
    result = base.trace.log_node(b.node('unused')['element_id'], PREFIX+label)
    if values:
        pieces = [lit(PREFIX+label, 100003)]
        for key, value in values:
            pieces += [lit(' | '+key+'=',100003),ex(100003,'ANY_VAR_TO_STR',cp(value))]
        assert 2 <= len(pieces) <= 10
        joined=ex(100003,'STR_JOIN',*pieces[:2])
        joined.update(op_arg=pieces[2:]+[None]*(10-len(pieces)),
                      op_arg_enable=[True]*(len(pieces)-2)+[False]*(10-len(pieces)))
        result['args_list'][1]=joined
    return result


def mark(source):
    d=cp(source)
    assert d['modifier_cover_type']==4 and d['time_change_of_cover']==2
    # In additive mode, 1 takes the NEW duration; 2 keeps the OLD duration.
    # The approved design refreshes eight seconds on each primary-target cast.
    d['time_change_of_cover']=1
    return d


def summer(source):
    d=cp(source);b=base.Builder(d);b.index=209997000100000
    owner,skill=ex(100006,'ABILITY_OWNER'),ex(100014,'CUR_ABILITY')
    target=base.var('UNIT_ENTITY','目标单位','actor')
    tid='1959489540'; t=d['trigger_dict'][tid]
    timer=base.one(t['action'],'RUN_LOOP_TIMER')
    command=base.one(timer,'UNIT_RELEASE_COMMAND')
    location=lambda u:ex(100004,'UNIT_ENTITY_POINT',cp(u))
    payload=[note(b,'夏侯渊3星/实际命令上下文',('施法者',owner),('技能',skill),('目标',target),
                  ('当前记录技能',ex(100014,'GET_UNIT_CUR_RECORD_ABILITY',cp(owner)))),
             note(b,'夏侯渊3星/实际距离与配置',
                  ('距离',ex(100000,'GET_POINTS_DIS',location(owner),location(target))),
                  ('施法范围',ex(100000,'GET_ABILITY_FLOAT_ATTR',cp(skill),lit('ability_cast_range',100078))),
                  ('技能等级',ex(100002,'GET_ABILITY_INT_ATTR',cp(skill),lit('ability_level',100079)))),
             cp(command)]
    base.replace_action(timer,command['element_id'],payload)
    count=base.declare(d,tid,'INTEGER','排查4_贯阵缓存总数',actor=True)
    marks=base.declare(d,tid,'INTEGER','排查4_贯阵来源猎印数',actor=True)
    last_count=base.declare(d,tid,'INTEGER','排查4_贯阵上次缓存数',-1,actor=True)
    last_marks=base.declare(d,tid,'INTEGER','排查4_贯阵上次猎印数',-1,actor=True)
    pick=base.one(timer,'PICK_UNIT_DO_ACTION',1959489540974224)
    pick['args_list'][1]['args_list'].insert(0,b.set(count,ex(100002,'INT_PLUS_ONE',cp(count))))
    source_check=next(n for n in walk(pick) if n.get('action_type')=='IF_THEN_ELSE'
                     and any(c.get('condition_type')=='UNIT_COMPARE'
                             and c['args_list'][0].get('sub_type')=='GET_BUFF_SOURCE'
                             for c in n['args_list'][0]['args_list']))
    source_check['args_list'][1]['args_list'].insert(0,b.set(marks,ex(100002,'INT_PLUS_ONE',cp(marks))))
    changed=b.cond('OR',ex(100021,1,b.cmp(count,'!=',last_count),b.cmp(marks,'!=',last_marks)))
    report=b.branch([changed],[note(b,'夏侯渊3星/缓存扫描变化',('施法者',owner),('缓存总数',count),('本来源猎印数',marks)),
                               b.set(last_count,count),b.set(last_marks,marks)])
    base.replace_action(timer,pick['element_id'],[b.set(count,lit(0)),b.set(marks,lit(0)),cp(pick),report])
    t['action'].insert(1,note(b,'夏侯渊3星/实例获得',('施法者',owner),('技能',skill)))
    return d


def build(root):
    return {FILES[0]:mark(base.trace.read(root/FILES[0])),
            FILES[1]:summer(base.trace.read(root/FILES[1]))}


def configure():
    base.WORK,base.FILES,base.build,base.PREFIX=WORK,FILES,build,PREFIX


def verify():
    result=base.verify()
    skill=base.trace.read(ROOT/FILES[1])
    result['all_triggers_valid']=all(t.get('valid') for t in skill['trigger_dict'].values())
    assert result['all_triggers_valid']
    assert base.trace.read(ROOT/FILES[0])['time_change_of_cover']==1
    base.trace.save(WORK/'editor-verified.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','publish','verify']);a=p.parse_args().action
    configure()
    if a=='prepare':
        base.prepare();shutil.copy2(LOG,WORK/'runtime-before.log')
        records={path:[cp(n) for n in walk(base.trace.read(WORK/'candidate'/path))
                       if n.get('action_type')=='PRINT_MESSAGE_ACTION_TO_DIALOG' and PREFIX in str(n)] for path in FILES}
        base.trace.save(WORK/'diagnostic-expressions.json',records)
    elif a=='publish':base.publish()
    else:print(json.dumps(verify()))
