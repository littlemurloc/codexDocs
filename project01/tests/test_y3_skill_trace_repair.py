"""Strict bounded AST tests; mover/event timing and native engine are not emulated."""
from copy import deepcopy as cp
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT))
import y3_skill_trace_repair as fix
spec=importlib.util.spec_from_file_location('trace_base_vm',ROOT/'tests/test_y3_hero_repair_p2_state.py')
base=importlib.util.module_from_spec(spec);sys.modules[spec.name]=base;spec.loader.exec_module(base)
Entity=base.Entity


class VM(base.VM):
    def __init__(self,doc):
        super().__init__(dict(variable_dict=doc.get('variable_dict',{})))
        self.doc=doc;self.context='spell';self.skill.source=self.owner
        self.target=Entity(team=2);self.skill.target=self.target
        self.skill.kv.update({'单次射击子弹数':1,'等级影响系数':1.0,'伤害系数':1.0,'额外系数':.25})
        self.skill.name='skill';self.owner.name='hero';self.target.name='enemy'
        self.core=Entity('buff',resource=134242511,stack=2);self.owner.modifiers=[self.core]
        self.owner.kv['能力循环机制']=self.core
        self.callbacks=[];self.ticks=[];self.logs=[];self.deleted=[]
        self.expired=Entity('timer')
        self.actor.update({'品质伤害系数':1.0,'子弹外观类型':1,'actName':'idle','目标单位':self.target})
        for kind,values in fix.GLOBALS.items():self.global_values.update(values)
        self.global_values[fix.PREFIX+'开关']=False

    def reference(self,node):
        a=node.get('args_list',[])
        if len(a)==1 and isinstance(a[0],dict)and a[0].get('__tuple__'):return a[0]['items']
        if len(a)==1 and isinstance(a[0],list)and len(a[0])in (2,3):return a[0]
        return None

    def assign(self,node,value):
        r=self.reference(node)
        if r is None:raise AssertionError('bad assignment')
        (self.global_values if len(r)==2 else self.local if r[2]=='local'else self.actor)[r[1]]=value

    def ev(self,n):
        s,a=n['sub_type'],n['args_list'];r=self.reference(n)
        if r:return (self.global_values if len(r)==2 else self.local if r[2]=='local'else self.actor).get(r[1],0)
        if s=='NONE_ABILITY':return None
        if s=='GET_ABILITY_TARGET_UNIT_FROM_EVENT':return self.target
        if s=='GET_UNIT_NAME':return getattr(self.require(self.ev(a[0]),'unit'),'name','unit')
        if s=='GET_ABILITY_INT_ATTR':self.require(self.ev(a[0]),'ability');return 1
        if s=='ANY_VAR_TO_STR':
            v=self.ev(a[0]);assert not isinstance(v,Entity),'No speculative entity-to-text support'
            return str(v)
        if s=='STR_JOIN':
            assert len(a)==2
            value=''.join(str(self.ev(v))for v in a)
            return value+''.join(str(self.ev(v))for i,v in enumerate(n.get('op_arg',[]))if n['op_arg_enable'][i])
        if s=='GET_STRING_KV':return self.require(self.ev(a[0])).kv[self.ev(a[1])]
        if s=='UNIT_HAS_TAG':return self.ev(a[1])in self.require(self.ev(a[0]),'unit').tags
        if s=='UNIT_ENTITY_POINT':return self.require(self.ev(a[0]),'unit')
        if s in ['GET_POINTS_ANGLE','GET_POINTS_DIS']:self.ev(a[0]);self.ev(a[1]);return 100
        if s in ['CREATE_PROJECTILE_NEW','CREATE_PROJECTILE_ON_SOCKET']:
            for v in a:self.ev(v)
            p=Entity('projectile');self.created.append(p);return p
        if s=='UNIT_FACE_ANGLE':self.require(self.ev(a[0]),'unit');return 0
        if s=='CURRENT_EXPIRED_TIMER':return self.expired
        if s=='GET_TIMER_REMAINING_COUNT':self.require(self.ev(a[0]),'timer');return 0
        if s=='ADD_MODIFIER':
            owner=self.require(self.ev(a[0]),'unit');b=Entity('buff',resource=self.ev(a[1]),source=self.owner)
            owner.modifiers.append(b);return b
        return super().ev(n)

    def cond(self,n):
        k,a=n['condition_type'],n['args_list']
        if k=='TYPE_IS_EXIST':
            assert a[0]['arg_type']in [100006,100014,100076,100077,100181]
            v=self.ev(a[0]);return isinstance(v,Entity)and v.valid
        if k=='BOOL_NOT':return not self.ev(a[0])
        if k=='OR':return any([self.cond(c)for c in a[0]['args_list']])
        if k in ['STRING_COMPARE','MODIFIER_COMPARE','UNIT_COMPARE','BOOL_COMPARE','FLOAT_COMPARE']:
            x,op,y=[self.ev(v)for v in a]
            return {'==':lambda:x==y,'!=':lambda:x!=y,'<=':lambda:x<=y,'>=':lambda:x>=y,'>':lambda:x>y,'<':lambda:x<y}[op]()
        return super().cond(n)

    def run(self,items):
        for n in items:
            if isinstance(n,int):continue
            if n.get('enable')is False:continue
            k,a=n['action_type'],n['args_list']
            if k=='IF_THEN_ELSE':
                tests=[self.cond(c)for c in a[0]['args_list']]
                self.run(a[1 if all(tests)else 2]['args_list'])
            elif k=='STORAGE_BOX':self.run(a[1]['args_list'])
            elif k=='SET_VARIABLE':self.assign(a[0],self.ev(a[1]))
            elif k=='SET_ENTITY_KV':self.require(self.ev(a[0])).kv[self.ev(a[1])]=self.ev(a[2])
            elif k=='RUN_COUNT_TIMER_NO_SAVE':self.ticks.append((cp(a[3]['args_list']),dict(self.local)))
            elif k in ['CREATE_CHASING_MOVER','CREATE_STRAIGHT_MOVER']:
                self.require(self.ev(a[0]),'projectile')
                for v in a[1:5]:self.ev(v)
                self.callbacks.append((cp(a[5]['args_list']),dict(self.local)))
            elif k=='APPLY_DAMAGE':
                self.require(self.ev(a[0]),'unit');self.require(self.ev(a[1]),'ability');self.require(self.ev(a[2]),'unit')
                self.hits.append(self.ev(a[4]))
            elif k=='PROJECTILE_DELETE':
                p=self.require(self.ev(a[0]),'projectile');p.valid=False;self.deleted.append(p)
            elif k=='DELETE_TIMER':self.require(self.ev(a[0]),'timer').valid=False
            elif k in ['CREATE_SFX_ON_UNIT','CREATE_SFX_ON_UNIT_NEW','FOLLOW_OBJECT_PLAY_3D_SOUND_FOR_PLAYER','PLAY_ANIMATION']:
                pass  # Explicit presentation-only fixture, not visual verification.
            elif k=='PRINT_MESSAGE_ACTION_TO_DIALOG':self.logs.append(self.ev(a[1]))
            elif k=='ADD_BUFF_STACK':self.require(self.ev(a[0]),'buff').stack+=self.ev(a[1])
            elif k=='ADD_MODIFIER':
                expr=cp(n);expr.pop('action_type');expr.update(sub_type='ADD_MODIFIER',arg_type=100076)
                self.ev(expr)
            elif k=='CALL_TRIGGER_FUNC':
                call=a[0];assert call['sub_type']==fix.FUNC
                doc=fix.make_logger(read('global_trigger/function/new/功能执行/英雄主动技能-检查自动施法动作状态.json'))
                params=[p['items'][0]for p in doc['func_param_list']]
                values=[self.ev(v)for v in call['args_list']];self.assert_params(params,values)
                saved=self.local;self.local=dict(zip(params,values))
                self.run(doc['action']);self.local=saved
            else:raise AssertionError('Unsupported action '+str(k))

    def callback(self):
        actions,env=self.callbacks.pop(0);self.local=dict(env);self.run(actions)

    @staticmethod
    def assert_params(params,values):
        if len(params)!=len(values):raise AssertionError('Function parameter mismatch')

    def shot(self,remote=False):
        tid='1644036097'if remote else '893440004'
        self.run(self.doc['trigger_dict'][tid]['action'])
        if remote:
            actions,env=self.ticks.pop(0);self.local=dict(env);self.run(actions)


def read(rel):
    baseline=fix.pub.WORK/fix.PHASE/'original'/rel
    return json.loads((baseline if baseline.exists()else fix.pub.MAP/rel).read_text('utf-8-sig'))


def payload():
    phase=fix.pub.WORK/fix.PHASE
    if not (phase/'manifest.json').exists():return fix.build(fix.pub.MAP)[0]
    manifest=json.loads((phase/'manifest.json').read_text('utf8'))
    return {e['path']:json.loads((phase/'staged'/e['path']).read_text('utf8'))for e in manifest['entries']}


class Tests(unittest.TestCase):
    def test_old_warning_reproduces_empty_buff(self):
        d=read('ability/134222927.json');v=VM(d);v.owner.modifiers=[]
        c=next(n for n in fix.walk(d)if n.get('element_id')==1959489540974493)
        with self.assertRaises(AssertionError):v.cond(c)

    def test_warning_guard_before_dereference(self):
        for oid in [134222927,134260801]:
            d=fix.patch_warning(read(f'ability/{oid}.json'));v=VM(d);v.owner.modifiers=[]
            timer=next(n for n in fix.walk(d['trigger_dict']['1959489540']['action'])if n.get('action_type')=='RUN_LOOP_TIMER')
            v.run(timer['args_list'][3]['args_list']);self.assertEqual(v.hits,[])

    def test_ranged_positive_and_cleanup(self):
        v=VM(fix.patch_ranged(read('ability/134270652.json')));v.shot(True);v.callback()
        self.assertEqual(v.hits,[100.0]);self.assertEqual(len(v.deleted),1)

    def test_ranged_invalid_target_skill_phase_pseudodeath(self):
        for fault in ['target','skill','phase','pseudo','core']:
            v=VM(fix.patch_ranged(read('ability/134270652.json')));v.shot(True)
            if fault=='target':v.target.valid=False
            if fault=='skill':v.skill.valid=False
            if fault=='phase':v.global_values['当前游戏进程阶段']=1
            if fault=='pseudo':v.target.tags.add('已死亡')
            if fault=='core':v.core.valid=False;v.owner.kv['能力循环机制']=Entity('buff')
            v.callback();self.assertEqual(v.hits,[],fault);self.assertEqual(len(v.deleted),1)

    def test_ranged_stale_tick_does_not_create(self):
        d=fix.patch_ranged(read('ability/134270652.json'));v=VM(d)
        v.run(d['trigger_dict']['1644036097']['action']);v.skill.valid=False
        actions,env=v.ticks[0];v.local=env;v.run(actions);self.assertEqual(v.created,[])

    def test_huang_base_and_enhanced_native_numbers_unchanged(self):
        for use_core in [True,False]:
            v=VM(fix.patch_huang(read('ability/134223239.json')))
            if not use_core:v.owner.modifiers=[]
            v.shot();v.callback();self.assertEqual(v.hits,[100.25 if use_core else 100.0])

    def test_huang_stale_target_before_launch_and_after(self):
        for before in [True,False]:
            v=VM(fix.patch_huang(read('ability/134223239.json')))
            if before:v.target.valid=False
            v.shot()
            if before:self.assertEqual(v.callbacks,[])
            else:
                v.target.valid=False;v.callback();self.assertEqual(v.hits,[]);self.assertEqual(len(v.deleted),1)

    def test_huang_same_wave_new_core_and_fake_dead_owner(self):
        for fault in ['core','pseudo']:
            v=VM(fix.patch_huang(read('ability/134223239.json')));v.shot()
            if fault=='core':v.core.valid=False;v.owner.modifiers=[Entity('buff',resource=134242511)]
            else:v.owner.tags.add('已死亡')
            v.callback();self.assertEqual(v.hits,[]);self.assertEqual(len(v.deleted),1)

    def logger(self):
        d=fix.make_logger(read('global_trigger/function/new/功能执行/英雄主动技能-检查自动施法动作状态.json'))
        v=VM(d);v.global_values[fix.PREFIX+'开关']=True
        v.local.update({'执行单位':v.owner,'技能实例':v.skill,'资源名':'孙尚香/test#1',
            '阶段':'获得','目标':v.target,'数值':0.0,'详情':'sample'})
        return d,v

    def test_logger_cap_and_summary_still_count(self):
        d,v=self.logger();v.run(d['action']);v.local['阶段']='伤害调用'
        for _ in range(25):v.run(d['action'])
        self.assertEqual(len(v.logs),9)
        v.local['阶段']='汇总';v.run(d['action'])
        self.assertIn('伤害调用=25',v.logs[-1]);self.assertIn('波次=1',v.logs[-1]);self.assertIn('批次=',v.logs[-1])

    def test_logger_off_filter_invalid_objects(self):
        d,v=self.logger();v.global_values[fix.PREFIX+'开关']=False;v.run(d['action']);self.assertEqual(v.logs,[])
        v.global_values[fix.PREFIX+'开关']=True;v.global_values[fix.PREFIX+'英雄筛选']='another';v.run(d['action']);self.assertEqual(v.logs,[])
        v.global_values[fix.PREFIX+'英雄筛选']='';v.target.valid=False;v.skill.valid=False
        v.run(d['action']);self.assertIn('无/已失效',v.logs[-1]);self.assertIn('等级=0',v.logs[-1])

    def test_same_wave_reobtain_new_batch_and_summary_reset(self):
        d,v=self.logger();v.run(d['action']);first=v.owner.kv['技能追踪/孙尚香/test#1/批次']
        v.local['阶段']='伤害调用';v.run(d['action']);v.local['阶段']='获得';v.run(d['action'])
        self.assertGreater(v.owner.kv['技能追踪/孙尚香/test#1/批次'],first)
        v.local['阶段']='汇总';v.run(d['action']);self.assertIn('伤害调用=0',v.logs[-1])

    def test_buff_conversion_keeps_enabled_options(self):
        d=read('ability/134234889.json');new=fix.instrument_ability(d,'test')
        def active(x):
            if isinstance(x,dict):
                if x.get('enable')is False:return
                yield x
                for v in x.values():yield from active(v)
            elif isinstance(x,list):
                for v in x:yield from active(v)
        old=[n for n in active(d)if n.get('action_type')=='ADD_MODIFIER']
        converted=[n for n in fix.walk(new)if n.get('sub_type')=='ADD_MODIFIER']
        for a in old:
            self.assertTrue(any(n['args_list']==a['args_list']and n.get('op_arg')==a.get('op_arg')and n.get('op_arg_enable')==a.get('op_arg_enable')for n in converted))
        a=old[0];v=VM(new);expr=next(n for n in converted if n['args_list']==a['args_list'])
        self.assertTrue(v.ev(expr).valid)

    def test_passive_effect_reaches_logger_not_only_gain(self):
        d=fix.instrument_ability(read('ability/134234889.json'),'太史慈/信义赴约#134234889')
        v=VM(d);v.global_values[fix.PREFIX+'开关']=True
        def locate(x):
            if isinstance(x,list):
                for i,n in enumerate(x):
                    if isinstance(n,dict)and n.get('action_type')=='SET_VARIABLE'and n['args_list'][1].get('sub_type')=='ADD_MODIFIER':return x[i:i+2]
                    hit=locate(n)
                    if hit:return hit
            elif isinstance(x,dict):
                for n in x.values():
                    hit=locate(n)
                    if hit:return hit
        actions=locate(d['trigger_dict']['892944388']['action']);self.assertIsNotNone(actions)
        v.run(actions);self.assertEqual(len(v.logs),1);self.assertIn('阶段=状态生效',v.logs[0])

    def test_levels_unchanged_and_no_global_gameplay_edit(self):
        out=payload()
        for ids in fix.HEROES.values():
            for oid in ids:
                old=read(f'ability/{oid}.json');new=out[f'ability/{oid}.json']
                for tid,t in old['trigger_dict'].items():
                    if any(e.get('event_type')=='ABILITY_LEVEL_CHANGED'for e in t.get('event',[])):
                        self.assertEqual(t,new['trigger_dict'][tid])
        self.assertEqual([f for f in out if f.startswith('global_trigger/function/')and f.endswith('.json')],[fix.FUNC_FILE])
        self.assertFalse(any(f.startswith('global_trigger/trigger/')for f in out))

    def test_new_element_ids_do_not_add_duplicates(self):
        from collections import Counter
        out=payload()
        for rel,d in out.items():
            if 'trigger_dict'not in d and rel!=fix.FUNC_FILE:continue
            old=read(rel)if (fix.pub.WORK/fix.PHASE/'original'/rel).exists()else {}
            a=Counter(n['element_id']for n in fix.walk(old)if 'element_id'in n)
            b=Counter(n['element_id']for n in fix.walk(d)if 'element_id'in n)
            self.assertTrue(all(c<=max(1,a[k])for k,c in b.items()),rel)


if __name__=='__main__':unittest.main()
