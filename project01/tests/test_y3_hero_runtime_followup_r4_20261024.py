"""Native configuration assertions and bounded lifetime-model regression."""
from pathlib import Path
import collections
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import y3_hero_runtime_followup_r4_20261024 as fix


class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old={p:fix.base.trace.read(fix.WORK/'map3-before'/p) for p in fix.FILES}
        cls.new=fix.build(fix.WORK/'map3-before')

    def test_mark_change_is_only_additive_lifetime_refresh(self):
        old,new=self.old[fix.FILES[0]],self.new[fix.FILES[0]]
        self.assertEqual({k for k in old if old[k]!=new[k]},{'time_change_of_cover'})
        self.assertEqual(old['modifier_cover_type'],4)
        self.assertEqual(old['time_change_of_cover'],2)
        self.assertEqual(new['time_change_of_cover'],1)
        self.assertEqual(new['layer_max'],3)
        self.assertTrue(new['same_origin_cover'])

    def test_bounded_clock_models_refresh_not_keep_old_expiry(self):
        # The official enum defines additive 1=new duration, 2=old duration.
        # This tests the configured policy, not actual native event scheduling.
        def expires(policy):
            expiry=8.0
            for now in [1.0,7.9]:
                if policy==1:expiry=now+8.0
                elif policy!=2:raise AssertionError('Unknown native policy')
            return expiry
        self.assertEqual(expires(self.old[fix.FILES[0]]['time_change_of_cover']),8.0)
        self.assertEqual(expires(self.new[fix.FILES[0]]['time_change_of_cover']),15.9)

    def test_summer_native_command_and_cast_effects_unchanged(self):
        old,new=self.old[fix.FILES[1]],self.new[fix.FILES[1]]
        self.assertEqual(fix.base.one(old,'UNIT_RELEASE_COMMAND'),fix.base.one(new,'UNIT_RELEASE_COMMAND'))
        self.assertEqual(old['trigger_dict']['893440004'],new['trigger_dict']['893440004'])
        self.assertEqual(old['trigger_dict']['225054724'],new['trigger_dict']['225054724'])
        self.assertEqual(old['trigger_group_info'],new['trigger_group_info'])
        oldconds={n['element_id']:n for n in fix.walk(old) if 'condition_type'in n}
        newconds={n['element_id']:n for n in fix.walk(new) if 'condition_type'in n}
        self.assertTrue(all(newconds[k]==v for k,v in oldconds.items()))

    def test_no_new_summer_gameplay_actions_or_kv_changes(self):
        old,new=self.old[fix.FILES[1]],self.new[fix.FILES[1]]
        ids={n['element_id'] for n in fix.walk(old) if 'element_id'in n}
        added=[n for n in fix.walk(new) if 'action_type'in n and n.get('element_id') not in ids]
        self.assertTrue(added)
        self.assertTrue(all(n['action_type'] in ['SET_VARIABLE','IF_THEN_ELSE','PRINT_MESSAGE_ACTION_TO_DIALOG'] for n in added))
        for n in added:
            if n['action_type']=='SET_VARIABLE':self.assertIn('排查4_',str(n['args_list'][0]))

    def test_own_instance_identity_and_distance_are_logged_at_real_command(self):
        doc=self.new[fix.FILES[1]]
        command=fix.base.one(doc,'UNIT_RELEASE_COMMAND')
        parents=[n for n in fix.walk(doc) if isinstance(n.get('args_list'),list) and command in n['args_list']]
        self.assertEqual(len(parents),1)
        actions=parents[0]['args_list'];i=actions.index(command)
        self.assertIn('实际命令上下文',str(actions[i-2]))
        self.assertIn('ABILITY_OWNER',str(actions[i-2]))
        self.assertIn('GET_UNIT_CUR_RECORD_ABILITY',str(actions[i-2]))
        self.assertIn('GET_POINTS_DIS',str(actions[i-1]))

    def test_new_actor_counters_are_declared_and_persistent(self):
        d=self.new[fix.FILES[1]]
        variables=d['variable_dict']['INTEGER']
        names=[n for n in variables if n.startswith('排查4_')]
        self.assertEqual(len(names),4)
        for n in names:self.assertIn(n,d['variable_length_dict'])
        refs=[n['items'] for n in fix.walk(d) if 'items'in n and isinstance(n['items'],list)
              and len(n['items'])==3 and str(n['items'][1]).startswith('排查4_')]
        self.assertTrue(all(x[2]=='actor' for x in refs))

    def test_no_fresh_id_collisions(self):
        existing=set()
        for path in fix.base.trace.files(fix.WORK/'map3-before'):
            if path.suffix!='.json':continue
            try:d=fix.base.trace.read(path)
            except (UnicodeError,ValueError):continue
            existing.update(n['element_id'] for n in fix.walk(d) if 'element_id'in n)
        for path,d in self.new.items():
            old=collections.Counter(n['element_id'] for n in fix.walk(self.old[path]) if 'element_id'in n)
            new=collections.Counter(n['element_id'] for n in fix.walk(d) if 'element_id'in n)
            self.assertTrue(all(v<=max(1,old[k]) for k,v in new.items()))
            self.assertFalse((set(new)-set(old)) & existing)

    def test_trace_registry_unchanged(self):
        registry=fix.base.trace.read(fix.base.trace.REGISTRY)['entries']
        path=fix.FILES[1]
        fix.base.trace.checked_nodes(self.new[path],registry[path]['logs'])


if __name__=='__main__':unittest.main()
