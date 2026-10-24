"""Bounded post-damage regression; probes do not simulate engine casting."""
from copy import deepcopy as cp
from pathlib import Path
from types import SimpleNamespace as NS
import collections
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import y3_hero_runtime_followup_r3_20261024 as fix
from test_y3_hero_runtime_followup_20261024 import Frame, unit


class DamageFrame(Frame):
    def __init__(self, *args, lethal=None):
        super().__init__(*args)
        self.lethal, self.damage = lethal, []

    def value(self, n):
        s, args = n.get('sub_type'), n.get('args_list', [])
        if s == 'GET_FLOAT_KV': return self.read(self.value(args[0])).kv[self.value(args[1])]
        if s == 'GET_UNIT_ATTR': return 100.0
        if s == 'ARITHMETIC_OPERATION':
            a, op, b = [self.value(x) for x in args]
            return {'*': lambda: a*b, '/': lambda: a/b}[op]()
        if s == 'GET_ABILITY_TARGET_UNIT_FROM_EVENT': return self.input_target
        if s == 'TARGET_UNIT_IN_ABILITY': return self.input_target
        return super().value(n)

    def run(self, nodes):
        for n in nodes:
            if n.get('enable') is False: continue
            action = n['action_type']
            if action in ('PLAY_ANIMATION', 'CREATE_SFX_ON_UNIT_3'): continue
            if action == 'APPLY_DAMAGE':
                target = self.read(self.value(n['args_list'][2]))
                self.damage.append(target)
                if self.lethal == 'native': target.alive = False
                if self.lethal == 'hero': target.tags.add('已死亡')
                if self.lethal == 'owner': self.owner.tags.add('已死亡')
            else: super().run([n])


class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = {p: fix.base.trace.read(fix.WORK/'map3-before'/p) for p in fix.FILES}
        cls.new = fix.build(fix.WORK/'map3-before')

    def scene(self, new, mode=None, target_dead=False, manual=False):
        owner, target = unit(), unit(team=2, dead=target_dead)
        owner.kv['自动施法'] = not manual
        f = DamageFrame(NS(kv={'伤害系数': 1.75}), owner, lethal=mode)
        f.input_target = target
        f.vars[('UNIT_ENTITY','目标单位','actor')] = unit(team=2) if manual else target
        t=(self.new if new else self.old)[fix.FILES[0]]['trigger_dict']['893440004']
        f.run(t['action'])
        return f, target

    def test_old_lethal_path_still_adds_status_to_fake_dead_hero(self):
        f, target = self.scene(False, 'hero')
        self.assertTrue(target.tags & {'已死亡'})
        self.assertEqual(f.effects, [(target, 134282779)])

    def test_new_skips_status_after_native_death_and_hero_fake_death(self):
        for mode in ['hero','native']:
            f, target = self.scene(True, mode)
            self.assertEqual(f.damage, [target]); self.assertFalse(f.effects)

    def test_live_target_still_takes_damage_and_status(self):
        f, target = self.scene(True)
        self.assertEqual(f.damage, [target]); self.assertEqual(f.effects, [(target,134282779)])

    def test_fake_dead_target_is_excluded_before_damage(self):
        f, _ = self.scene(True, target_dead=True)
        self.assertFalse(f.damage); self.assertFalse(f.effects)

    def test_owner_fake_death_during_damage_prevents_further_state_application(self):
        f, _ = self.scene(True, 'owner')
        self.assertFalse(f.effects)

    def test_manual_input_is_snapshotted_after_existing_manual_target_assignment(self):
        f, target = self.scene(True, manual=True)
        self.assertEqual(f.damage, [target]); self.assertEqual(f.effects, [(target,134282779)])

    def test_summer_probe_sits_at_real_command_not_outside_final_guard(self):
        d=self.new[fix.FILES[1]]
        guard=next(n for n in fix.walk(d) if n.get('element_id')==209996800120006)
        true_actions=guard['args_list'][1]['args_list'][0]['args_list'][1]['args_list']
        self.assertEqual([n['action_type'] for n in true_actions],
                         ['PRINT_MESSAGE_ACTION_TO_DIALOG','UNIT_RELEASE_COMMAND','PRINT_MESSAGE_ACTION_TO_DIALOG'])
        self.assertIn('实际提交命令', str(true_actions[0]))
        self.assertIn('未提交命令',str(guard['args_list'][2]))

    def test_summer_existing_logic_and_native_command_are_not_changed(self):
        old=self.old[fix.FILES[1]]; new=self.new[fix.FILES[1]]
        self.assertEqual(fix.base.one(old,'UNIT_RELEASE_COMMAND'),fix.base.one(new,'UNIT_RELEASE_COMMAND'))
        self.assertEqual(new['variable_dict'],old['variable_dict'])
        extra=set(new['trigger_dict'])-set(old['trigger_dict'])
        self.assertEqual(len(extra),3)
        self.assertEqual({new['trigger_dict'][t]['event'][0]['event_type'] for t in extra},
                         {'ABILITY_CS_START','ABILITY_PS_START','ABILITY_END'})
        self.assertTrue(all(len(new['trigger_dict'][t]['action'])==1 for t in extra))

    def test_zhang_diagnostics_do_not_change_actions_or_conditions(self):
        for path in fix.FILES[2:]:
            original_ids={n['element_id'] for n in fix.walk(self.old[path]) if 'element_id'in n}
            def gameplay(value):
                if isinstance(value,list):
                    return [c for v in value if (c:=gameplay(v)) is not None]
                if not isinstance(value,dict):return value
                if value.get('action_type')=='PRINT_MESSAGE_ACTION_TO_DIALOG':return None
                result={k:gameplay(v) for k,v in value.items()}
                if result.get('action_type')=='IF_THEN_ELSE' and result['element_id'] not in original_ids:
                    self.assertFalse(result['args_list'][1]['args_list'])
                    self.assertFalse(result['args_list'][2]['args_list'])
                    return None
                return result
            self.assertEqual(gameplay(self.old[path]),gameplay(self.new[path]),path)
            old={n['element_id']: n for n in fix.walk(self.old[path]) if 'condition_type'in n}
            new={n['element_id']: n for n in fix.walk(self.new[path]) if 'condition_type'in n}
            self.assertTrue(all(new[k]==v for k,v in old.items()))

    def test_native_dynamic_logs_have_enabled_optional_string_arguments(self):
        count=0
        for doc in self.new.values():
            for n in fix.walk(doc):
                if n.get('action_type')!='PRINT_MESSAGE_ACTION_TO_DIALOG' or fix.PREFIX not in str(n):continue
                arg=n['args_list'][1]
                if arg['sub_type']!='STR_JOIN':continue
                count+=1
                self.assertEqual(len(arg['op_arg']),8)
                self.assertEqual(len(arg['op_arg_enable']),8)
                self.assertTrue(all(v is not None for v,on in zip(arg['op_arg'],arg['op_arg_enable']) if on))
        self.assertGreater(count,0)

    def test_permanent_trace_registry_preserved(self):
        registry=fix.base.trace.read(fix.base.trace.REGISTRY)['entries']
        for path in fix.FILES:
            if path in registry:fix.base.trace.checked_nodes(self.new[path],registry[path]['logs'])


if __name__=='__main__':unittest.main()
