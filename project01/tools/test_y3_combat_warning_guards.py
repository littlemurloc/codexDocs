"""Regression tests for missing/stale handles; deliberately eager conditions.

This bounded interpreter fails on invalid reads rather than providing engine
values silently. It verifies these guards, not the whole Y3 combat runtime.
"""
from __future__ import annotations
import copy, itertools, json, unittest, zipfile
from dataclasses import dataclass, field
import fix_y3_combat_warning_guards as fix

@dataclass
class Entity:
    valid: bool = True
    kv: dict = field(default_factory=dict)
    running: bool = False
    recorded: object = None
    cast_type: int = 2
    attributes: dict = field(default_factory=dict)

class VM:
    def __init__(self,target=None):
        self.target=target;self.variables={};self.reads=[];self.source=Entity();self.result=None
    @staticmethod
    def valid(x):return isinstance(x,Entity) and x.valid
    def require(self,x):
        assert self.valid(x),'Invalid object dereferenced'
        return x
    def ev(self,n):
        t=n['sub_type'];a=n['args_list']
        if t in (1,2,6,11,'VARIABLE'):
            if a and isinstance(a[0],dict) and a[0].get('__tuple__'):
                return self.variables[a[0]['items'][1]]
            assert len(a)==1
            return a[0]
        if t=='DAMAGE_TARGET_UNIT':return self.target
        if t=='DAMAGE_SOURCE_UNIT':return self.source
        if t=='NONE_UNIT':return None
        if t=='HAS_KV_ANY':return self.ev(a[1]) in self.require(self.ev(a[0])).kv
        if t in ('GET_INTEGER_KV','GET_UNIT_ENTITY_KV'):
            u=self.require(self.ev(a[0]));key=self.ev(a[1]);self.reads.append((t,u,key))
            assert key in u.kv,'Read absent KV: '+key
            return u.kv[key]
        if t=='UNIT_HAS_RUNNING_ABILITY':return self.require(self.ev(a[0])).running
        if t=='GET_UNIT_CUR_RECORD_ABILITY':
            u=self.require(self.ev(a[0]));self.reads.append((t,u));return u.recorded
        if t=='GET_ABILITY_CAST_TYPE':
            ability=self.require(self.ev(a[0]));self.reads.append((t,ability));return ability.cast_type
        if t=='GET_UNIT_ATTR':return self.require(self.ev(a[0])).attributes.get(self.ev(a[2]),0)
        if t=='ARITHMETIC_OPERATION':
            x,op,y=[self.ev(v) for v in a];assert op=='+';return x+y
        raise AssertionError('Unhandled expression '+str(t))
    def cond(self,n):
        t=n['condition_type'];a=n['args_list']
        if t=='TYPE_IS_EXIST':return self.valid(self.ev(a[0]))
        if t=='HAS_KV_ANY':return self.ev(a[1]) in self.require(self.ev(a[0])).kv
        if t=='OR':return any([self.cond(v) for v in a[0]['args_list']])
        if t=='BOOL_NOT':return not self.ev(a[0])
        if t in ('FLOAT_COMPARE','BOOL_COMPARE','ABILITY_CAST_TYPE_COMPARE'):
            x,op,y=[self.ev(v) for v in a];assert op=='==';return x==y
        raise AssertionError('Unhandled condition '+str(t))
    def run(self,actions):
        for n in actions:
            if n.get('enable') is False:continue
            t=n['action_type'];a=n['args_list']
            if t=='SET_VARIABLE':self.variables[a[0]['args_list'][0]['items'][1]]=self.ev(a[1])
            elif t in ('IF_THEN_ELSE','STORAGE_BOX'):
                # No short-circuit assumption: every condition is evaluated.
                result=all([self.cond(v) for v in a[0]['args_list']])
                self.run(a[1 if result else 2]['args_list'])
            # ECA result assignment must not be treated as a control-flow exit.
            elif t==400342:self.result=self.ev(a[0])
            else:raise AssertionError('Unhandled action '+str(t))
    def helper(self,owner):
        self.variables={'施法单位':owner,'当前施法技能':None}
        repaired=fix.WORK.parent/'autocast-return-fix-20261018/staged'/fix.HELPER
        self.run(fix.load(repaired if repaired.exists() else fix.STAGE/fix.HELPER)['action'])
        assert self.result is not None,'No result'
        return self.result

class GuardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=fix.load(fix.WORK/'manifest.json')
        cls.rows=fix.load(fix.WORK/'hero-active-audit.json')
        with zipfile.ZipFile(fix.WORK/'before-warning-fix.zip') as z:
            cls.original={rel:json.loads(z.read(rel)) for rel,row in cls.manifest.items() if row['before'] is not None}
        cls.universe=fix.load(fix.STAGE/fix.UNIVERSE)
        cls.block=cls.universe['sub_trigger'][fix.DAMAGE_TID]['action'][1]

    def test_missing_owner_returns_false_without_dereference(self):
        for owner in (None,Entity(valid=False)):
            vm=VM();self.assertFalse(vm.helper(owner));self.assertFalse(vm.reads)

    def test_idle_allows_cast_without_reading_absent_record(self):
        vm=VM();self.assertTrue(vm.helper(Entity(running=False)));self.assertFalse(vm.reads)

    def test_running_with_missing_or_destroyed_record_is_safe(self):
        for record in (None,Entity(valid=False)):
            vm=VM();self.assertFalse(vm.helper(Entity(running=True,recorded=record)))
            self.assertEqual([x[0] for x in vm.reads],['GET_UNIT_CUR_RECORD_ABILITY'])

    def test_valid_actions_preserve_original_truth_table(self):
        for running,kind in itertools.product([False,True],[1,2,3,4]):
            vm=VM();self.assertEqual(vm.helper(Entity(running=running,recorded=Entity(cast_type=kind))),not running or kind==1)
            reads=[x[0] for x in vm.reads]
            self.assertEqual(reads,['GET_UNIT_CUR_RECORD_ABILITY','GET_ABILITY_CAST_TYPE'] if running else [])

    def test_old_helper_overwrites_idle_and_normal_attack_true_with_false(self):
        old=fix.load(fix.STAGE/fix.HELPER)
        for owner in (Entity(),Entity(running=True,recorded=Entity(cast_type=1))):
            vm=VM();vm.variables={'施法单位':owner,'当前施法技能':None}
            vm.run(old['action']);self.assertIs(vm.result,False)

    def test_result_assignment_continues_to_later_actions(self):
        nodes=fix.Nodes();vm=VM();vm.run([nodes.ret(True),nodes.ret(False)])
        self.assertIs(vm.result,False)

    def test_fixed_helper_has_one_final_result_and_exclusive_idle_branch(self):
        p=fix.WORK.parent/'autocast-return-fix-20261018/staged'/fix.HELPER
        doc=fix.load(p);returns=[path for path,n in fix.walk(doc) if n.get('action_type')==400342]
        self.assertEqual(returns,[('action',2)])
        self.assertEqual(doc['action'][-1]['args_list'][0],fix.var('BOOLEAN','动作状态允许施法'))
        idle=doc['action'][1]['args_list'][1]['args_list'][0]
        self.assertEqual(len(idle['args_list'][1]['args_list']),1)
        self.assertFalse(any(n.get('sub_type')=='GET_UNIT_CUR_RECORD_ABILITY' for _,n in fix.walk(idle['args_list'][1])))

    def test_legacy_autocast_condition_exposes_invalid_record(self):
        sample=next(doc for rel,doc in self.original.items() if rel.startswith('ability/'))
        condition=next(node for _,node in fix.walk(sample) if fix.unsafe_auto_or(node))
        comparison=copy.deepcopy(condition['args_list'][0]['args_list'][1])
        comparison['args_list'][0]['args_list'][0]['args_list'][0]=fix.var('UNIT_ENTITY','施法单位')
        vm=VM();vm.variables['施法单位']=Entity()
        with self.assertRaisesRegex(AssertionError,'Invalid object'):vm.cond(comparison)

    def formation(self,target,vm=None):
        vm=vm or VM();vm.target=target
        vm.source.attributes={'AJN3Yq93EfGmm0dW61iJRe':10,'ArFMkq93EfGSrUdW61iJRQ':20,'GpYBbK93EfGEkEdW61iJRb':40}
        vm.run([self.block]);return vm.variables['站位伤害%加成'],vm

    def test_missing_and_destroyed_targets_have_zero_formation_bonus(self):
        for target in (None,Entity(valid=False),Entity()):
            bonus,vm=self.formation(target);self.assertEqual(bonus,0);self.assertFalse(vm.reads)

    def test_missing_captain_and_absent_keys_are_safe(self):
        for captain in (None,Entity(valid=False),Entity()):
            target=Entity(kv={'归属阵型编号':1,'所属英雄':captain})
            bonus,vm=self.formation(target);self.assertEqual(bonus,10)

    def test_legacy_formation_condition_exposes_empty_captain(self):
        block=self.original[fix.UNIVERSE]['sub_trigger'][fix.DAMAGE_TID]['action'][1]
        vm=VM(Entity(kv={'归属阵型编号':0,'所属英雄':None}))
        with self.assertRaisesRegex(AssertionError,'Invalid object'):vm.run([block])

    def test_all_self_captain_slot_pairs_preserve_or_and_once_per_group(self):
        groups=[({1,4,7},10),({2,5,8},20),({3,6,9},40)]
        for own,hero in itertools.product(range(10),repeat=2):
            target=Entity(kv={'归属阵型编号':own,'所属英雄':Entity(kv={'归属阵型编号':hero})})
            bonus,vm=self.formation(target)
            self.assertEqual(bonus,sum(value for slots,value in groups if own in slots or hero in slots),(own,hero))
            self.assertEqual(sum(x[0]=='GET_INTEGER_KV' for x in vm.reads),2)

    def test_soldier_can_inherit_captain_slot(self):
        bonus,_=self.formation(Entity(kv={'所属英雄':Entity(kv={'归属阵型编号':8})}))
        self.assertEqual(bonus,20)

    def test_next_damage_clears_previous_event_cache(self):
        _,vm=self.formation(Entity(kv={'归属阵型编号':1,'所属英雄':Entity(kv={'归属阵型编号':9})}))
        bonus,vm=self.formation(Entity(),vm);self.assertEqual(bonus,0)
        self.assertEqual(vm.variables[fix.SELF_SLOT],0);self.assertEqual(vm.variables[fix.HERO_SLOT],0)

    def test_entire_hero_active_inventory_checked(self):
        self.assertEqual(len(self.rows),78);self.assertEqual(len({r['hero'] for r in self.rows}),26)
        self.assertEqual(sum(r['fixed_conditions'] for r in self.rows),74)
        self.assertEqual(sum(r['fixed_conditions']==0 for r in self.rows),4)
        self.assertEqual({r['path'] for r in self.rows if r['fixed_conditions']},
                         {p for p in self.manifest if p.startswith('ability/')})

    def test_all_other_hero_fields_and_cast_payloads_exactly_preserved(self):
        for rel,row in self.manifest.items():
            if row['kind']!='hero_autocast':continue
            fixed=fix.load(fix.STAGE/rel);old=self.original[rel]
            for change in row['changes']:
                new=fix.at(fixed,change['path']);before=fix.at(old,change['path'])
                self.assertEqual(new['args_list'][0]['sub_type'],fix.FID)
                new.clear();new.update(copy.deepcopy(before))
            self.assertEqual(fixed,old,rel)

    def test_formation_only_changes_cache_and_read_expressions(self):
        fixed=copy.deepcopy(self.universe);old=self.original[fix.UNIVERSE]
        trigger=fixed['sub_trigger'][fix.DAMAGE_TID];oldtrigger=old['sub_trigger'][fix.DAMAGE_TID]
        block=trigger['action'][1];del block['args_list'][1]['args_list'][1]
        trigger['var_data']=copy.deepcopy(oldtrigger['var_data'])
        target=fix.expr(100006,'DAMAGE_TARGET_UNIT')
        for _,node in fix.walk(block):
            if node.get('sub_type')!=6:continue
            ref=node.get('args_list',[{}])[0]
            if not isinstance(ref,dict) or not ref.get('__tuple__'):continue
            name=ref['items'][1]
            if name not in [fix.SELF_SLOT,fix.HERO_SLOT]:continue
            source=target if name==fix.SELF_SLOT else fix.expr(100006,'GET_UNIT_ENTITY_KV',target,fix.text('所属英雄'))
            node.clear();node.update(fix.expr(100002,'GET_INTEGER_KV',copy.deepcopy(source),fix.text('归属阵型编号')))
        self.assertEqual(fixed,old)

    def test_all_staged_hashes_and_metadata_untouched(self):
        for rel,row in self.manifest.items():self.assertEqual(fix.sha((fix.STAGE/rel).read_bytes()),row['after'])
        for row in self.rows:
            self.assertEqual(fix.sha((fix.MAP/'editor_table/abilityall'/f'{row["id"]}.json').read_bytes()),row['metadata_sha256'])

    def test_migration_is_idempotent_for_hero_conditions(self):
        for rel,row in self.manifest.items():
            if row['kind']!='hero_autocast':continue
            doc=fix.load(fix.STAGE/rel);again,changes=fix.patch_ability(doc)
            self.assertEqual(again,doc);self.assertFalse(changes)

    def test_helper_registration_and_return_declarations(self):
        index=fix.load(fix.STAGE/fix.INDEX);old=self.original[fix.INDEX]
        self.assertEqual({k:v for k,v in index.items() if k!=fix.NAME+'.json'},old)
        helper=fix.load(fix.STAGE/fix.HELPER)
        self.assertEqual(helper['func_id'],fix.FID)
        self.assertEqual(helper['func_rtv_name_list'][0]['items'],['允许自动施法','BOOLEAN'])
        self.assertEqual(helper['var_data'][0]['ABILITY'],{'当前施法技能':0})

if __name__=='__main__':unittest.main(verbosity=2)
