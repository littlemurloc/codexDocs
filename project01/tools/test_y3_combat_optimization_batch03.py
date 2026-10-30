"""Execute staged ECA display actions with a strict, bounded offline model.

Native timer closure capture, rendering and actual performance remain engine
checks. Unknown actions/expressions fail, missing KV and dead dereferences fail.
"""
import collections
import copy
import itertools
import sys
import unittest
import y3_combat_optimization_batch03 as b
import y3_skill_trace_manager as traces
import y3_recent_work_fixtures as fixtures


class Obj:
    def __init__(self,kind,**props):
        self.kind=kind;self.exists=True;self.kv={};self.props=props


class VM:
    def __init__(self):
        self.vars={};self.queue=[];self.writes=[];self.stats=collections.Counter()
        self.players=[1,2];self.current_timer=None;self.index=None;self.player=None
    def valid(self,obj):
        assert isinstance(obj,Obj) and obj.exists,'Invalid object dereference'
        return obj
    def ev(self,n):
        t,a=n['sub_type'],n['args_list']
        if t in (1,2,6,11,14,'VARIABLE'):
            assert len(a)==1
            if isinstance(a[0],dict) and a[0].get('__tuple__'):
                name=a[0]['items'][1]
                return self.players if name=='playerList' else self.vars[name]
            assert not isinstance(a[0],(dict,list)), 'Nested expression in literal'
            return a[0]
        if t in ('GET_BOOLEAN_KV','GET_INTEGER_KV','GET_TEXTURE_KV','GET_MODIFIER_ENTITY_KV',
                 'GET_TABLE_KV','GET_SCENE_UI_KV'):
            obj,key=self.valid(self.ev(a[0])),self.ev(a[1]);assert key in obj.kv,'Missing KV: '+key
            return obj.kv[key]
        if t=='OWNER_PLAYER':return self.valid(self.ev(a[0])).props['owner']
        if t=='PLAYER_ID_NUMBER':return self.ev(a[0])
        if t=='GET_MOD_STACK':
            self.stats['stack_reads']+=1;return self.valid(self.ev(a[0])).props['stack']
        if t=='MATH_OPERATION':
            x,op,y=[self.ev(v) for v in a];assert op=='-';return x-y
        if t=='ANY_VAR_TO_STR':return str(self.ev(a[0]))
        if t=='UNIT_HAS_TAG':return self.ev(a[1]) in self.valid(self.ev(a[0])).props['tags']
        if t=='ITER_TABLE_KEY_INT':assert self.index is not None;return self.index
        if t=='PICKED_PLAYER':assert self.player is not None;return self.player
        if t=='GET_UI_PREFAB_INSTANCE_TABLE_VAR_ND':
            table,key,col=[self.ev(v) for v in a];assert key in table and col in table[key]
            return table[key][col]
        if t=='GET_UI_PREFAB_CHILD_BY_PATH':
            obj=self.valid(self.ev(a[0]));assert self.ev(a[1])=='image';return obj
        if t=='GET_UI_COMP_IN_SCENE_UI':
            obj=self.valid(self.ev(a[0]));assert self.ev(a[1]).endswith('.bg.积累');return obj
        if t=='CURRENT_EXPIRED_TIMER':return self.current_timer
        if t=='cbedcbf9752611f1b98019023354d96d':
            self.stats['theme_reads']+=1;return self.valid(self.ev(a[0])).props['theme']
        raise AssertionError('Unmodeled expression: '+str(t))
    def cond(self,n):
        t,a=n['condition_type'],n['args_list']
        if t=='TYPE_IS_EXIST':
            value=self.ev(a[0]);assert isinstance(value,Obj)
            return value.exists
        if t=='HAS_KV_ANY':return self.ev(a[1]) in self.valid(self.ev(a[0])).kv
        if t=='IS_UNIT_ALIVE':return self.valid(self.ev(a[0])).props['alive']
        if t=='BOOL_NOT':return not self.ev(a[0])
        if t in ('FLOAT_COMPARE','BOOL_COMPARE','ANY_COMPARE','MODIFIER_COMPARE','PLAYER_COMPARE'):
            x,op,y=[self.ev(v) for v in a]
            if op=='==':return x==y
            if op=='!=':return x!=y
            if op=='<=':return x<=y
            if op=='>':return x>y
            raise AssertionError(op)
        raise AssertionError('Unmodeled condition: '+str(t))
    def run(self,actions):
        for n in actions:
            if n.get('enable') is False:continue
            t,a=n['action_type'],n['args_list']
            if t=='SET_VARIABLE':self.vars[a[0]['args_list'][0]['items'][1]]=self.ev(a[1])
            elif t in ('STORAGE_BOX','IF_THEN_ELSE'):
                # Eager checks, deliberately no assumed condition short circuit.
                yes=all([self.cond(v) for v in a[0]['args_list'] if v.get('enable',True)])
                self.run(a[1 if yes else 2]['args_list'])
            elif t=='SET_ENTITY_KV':self.valid(self.ev(a[0])).kv[self.ev(a[1])]=self.ev(a[2])
            elif t=='RUN_ONCE_TIMER_BY_FRAME_NO_SAVE':
                assert self.ev(a[0])==1
                self.queue.append((a[1]['args_list'],self.vars.copy(),Obj('timer')))
                self.stats['timers']+=1
            elif t=='DELETE_TIMER':self.valid(self.ev(a[0])).exists=False;self.stats['timer_deletes']+=1
            elif t=='TRAVERSE_TABLE_NEW':
                self.stats['traversals']+=1
                table=self.ev(a[0]);assert isinstance(table,dict)
                old=self.index
                for k in list(table):self.index=k;self.run(a[1]['args_list'])
                self.index=old
            elif t=='PICK_PLAYER_DO_ACTION':
                old=self.player
                for p in self.ev(a[0]):self.player=p;self.run(a[1]['args_list'])
                self.player=old
            elif t=='SET_UI_COMP_IMAGE_NEW':
                player,obj,value=[self.ev(v) for v in a];self.valid(obj)
                obj.props.setdefault('images',{})[player]=value
                self.writes.append(('image',obj,player,value))
            elif t=='SET_UI_COMP_TEXT':
                player,obj,value=[self.ev(v) for v in a];self.valid(obj)
                obj.props.setdefault('text',{})[player]=value
                self.writes.append(('text',obj,player,value))
            else:raise AssertionError('Unmodeled action: '+str(t))
    def invoke(self,doc,unit,buff):
        old=self.vars
        self.vars={k:v for values in doc['var_data'][0].values() for k,v in values.items()}
        self.vars.update(执行单位=unit,能力机制=buff)
        self.run(doc['action']);self.vars=old
    def tick(self):
        callbacks,self.queue=self.queue,[]
        for actions,variables,timer in callbacks:
            old=self.vars;self.vars=variables;self.current_timer=timer
            self.run(actions);assert not timer.exists,'One-shot callback failed cleanup'
            self.vars=old


def fixture(points=5,owner=1,stack=1,theme=134268765):
    unit=Obj('unit',owner=owner,tags=set(),alive=True,theme=theme)
    buff=Obj('buff',stack=stack)
    unit.kv['能力循环机制']=buff
    unit.kv['循环机制面板']=Obj('panel')
    unit.kv['能量格数据表']={k:{'能量格子':Obj('cell')} for k in range(1,points+1)}
    return unit,buff


def state(unit,owner=1):
    return (unit.kv['循环机制面板'].props.get('text',{}).get(owner),
        [r['能量格子'].props.get('images',{}).get(owner) for r in unit.kv['能量格数据表'].values()])


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=fixtures.manifest('combat-batch03')
        cls.new=fixtures.document('combat-batch03','staged',b.UI)
        cls.old=fixtures.document('combat-batch03','before',b.UI);cls.cases=0
    def test_display_equivalence_for_all_point_transitions(self):
        # Includes zero, full, drain, overflow and theme changes. Compare rendered
        # cells with actual old ECA and text with the original stack-1 contract.
        for slots,start,end,theme in itertools.product((0,1,5,12),range(0,8),range(0,8),(134268765,134225898)):
            u,m=fixture(slots,stack=start);vm=VM();vm.invoke(self.new,u,m);vm.tick()
            m.props['stack']=end;u.props['theme']=theme;vm.invoke(self.new,u,m);vm.tick()
            reference,rm=fixture(slots,stack=end,theme=theme);old=VM();old.invoke(self.old,reference,rm)
            self.assertEqual(state(u)[1],state(reference)[1]);self.assertEqual(state(u)[0],str(end-1))
            type(self).cases+=1
    def test_same_frame_latest_state_one_timer(self):
        u,m=fixture(12);vm=VM()
        for stack in range(2,11):m.props['stack']=stack;vm.invoke(self.new,u,m)
        self.assertEqual(len(vm.queue),1);self.assertFalse(vm.writes)
        vm.tick();self.assertEqual(state(u)[0],'9');self.assertEqual(len(vm.writes),13)
        self.assertEqual(vm.stats['stack_reads'],1)
    def test_unchanged_state_has_no_traversal_or_writes(self):
        u,m=fixture(stack=4);vm=VM();vm.invoke(self.new,u,m);vm.tick()
        before=(len(vm.writes),vm.stats['traversals']);vm.invoke(self.new,u,m);vm.tick()
        self.assertEqual(before,(len(vm.writes),vm.stats['traversals']))
    def test_one_point_changes_only_one_cell_and_text(self):
        u,m=fixture(12,stack=4);vm=VM();vm.invoke(self.new,u,m);vm.tick();vm.writes=[]
        m.props['stack']=5;vm.invoke(self.new,u,m);vm.tick()
        self.assertEqual(collections.Counter(w[0] for w in vm.writes),{'image':1,'text':1})
    def test_theme_only_changes_filled_cells_without_text(self):
        u,m=fixture(12,stack=4);vm=VM();vm.invoke(self.new,u,m);vm.tick();vm.writes=[]
        u.props['theme']=134231814;vm.invoke(self.new,u,m);vm.tick()
        self.assertEqual(collections.Counter(w[0] for w in vm.writes),{'image':3})
    def test_unit_and_buff_loss_before_callback(self):
        for target in ('unit','buff'):
            u,m=fixture();vm=VM();vm.invoke(self.new,u,m)
            (u if target=='unit' else m).exists=False
            vm.tick();self.assertFalse(vm.writes);self.assertFalse(vm.queue)
    def test_missing_current_or_ui_keys_do_not_dereference(self):
        for key in ('能力循环机制','能量格数据表','循环机制面板'):
            u,m=fixture();vm=VM();vm.invoke(self.new,u,m);del u.kv[key]
            vm.tick();self.assertFalse(vm.writes)
            self.assertFalse(m.kv[b.PREFIX+'待刷新'])
    def test_logical_or_engine_death_skip_presentation(self):
        for logical in (False,True):
            u,m=fixture();vm=VM();vm.invoke(self.new,u,m)
            if logical:u.props['tags'].add('已死亡')
            else:u.props['alive']=False
            vm.tick();self.assertFalse(vm.writes)
    def test_old_callback_cannot_paint_replacement_core(self):
        u,old=fixture();vm=VM();vm.invoke(self.new,u,old)
        new=Obj('buff',stack=5);u.kv['能力循环机制']=new
        vm.invoke(self.new,u,new);vm.tick()
        self.assertEqual(state(u)[0],'4');self.assertEqual(vm.stats['traversals'],1)
    def test_rebuild_invalidates_cache_and_repaints_new_prefabs(self):
        u,m=fixture(stack=4);vm=VM();vm.invoke(self.new,u,m);vm.tick()
        vm.invoke(self.new,u,m)  # already pending during a rebuild
        for r in u.kv['能量格数据表'].values():r['能量格子'].exists=False
        u.kv['能量格数据表'].clear()
        u.kv['能量格数据表'].update(fixture()[0].kv['能量格数据表'])
        m.kv[b.PREFIX+'已绘制']=False
        vm.invoke(self.new,u,m);self.assertEqual(len(vm.queue),1);vm.tick()
        self.assertEqual(state(u)[1],[134268765]*3+[134246678]*2)
    def test_missing_prefab_does_not_poison_cache_and_can_retry(self):
        u,m=fixture();vm=VM();u.kv['能量格数据表'][2]['能量格子'].exists=False
        vm.invoke(self.new,u,m);vm.tick();self.assertFalse(m.kv[b.PREFIX+'已绘制'])
        u.kv['能量格数据表'][2]['能量格子']=Obj('cell');vm.invoke(self.new,u,m);vm.tick()
        self.assertTrue(m.kv[b.PREFIX+'已绘制'])
    def test_multiple_units_capture_independent_context(self):
        fixtures=[fixture(stack=3),fixture(stack=5,theme=134231814)]
        vm=VM()
        for u,m in fixtures:vm.invoke(self.new,u,m)
        vm.tick();self.assertEqual([state(u)[0] for u,_ in fixtures],['2','4'])
        self.assertEqual(vm.stats['timer_deletes'],2)
    def test_npc_recipients_match_original(self):
        u,m=fixture(owner=31,stack=4);old_u,old_m=fixture(owner=31,stack=4)
        vm=VM();vm.invoke(self.new,u,m);vm.tick();prior=VM();prior.invoke(self.old,old_u,old_m)
        for owner in (1,2):self.assertEqual(state(u,owner)[1],state(old_u,owner)[1])
        self.assertEqual(state(u,31)[0],'3')  # original text recipient retained
    def test_ownership_change_invalidates_presentation_cache(self):
        for start,end in ((1,2),(1,31),(31,1)):
            u,m=fixture(owner=start,stack=4);vm=VM();vm.invoke(self.new,u,m);vm.tick()
            u.props['owner']=end;vm.writes=[];vm.invoke(self.new,u,m);vm.tick()
            expected,em=fixture(owner=end,stack=4);old=VM();old.invoke(self.old,expected,em)
            for owner in ([end] if end!=31 else [1,2]):
                self.assertEqual(state(u,owner)[1],state(expected,owner)[1])
            self.assertEqual(state(u,end)[0],'3')
    def test_all_26_text_payloads_match_shared_contract(self):
        sample=next(v for _,v in b.walk(fixtures.document('combat-batch03','before','modifier/134284036.json'),active=True)
                    if v.get('element_id')==1050472449000002)
        for row in self.manifest['entries']:
            if row['kind']!='core':continue
            old=fixtures.document('combat-batch03','before',row['path']);new=fixtures.document('combat-batch03','staged',row['path'])
            p=row['edits'][0]['path'];self.assertEqual(b.at(old,p)['args_list'],sample['args_list'])
            self.assertFalse(b.at(new,p)['enable'])
    def test_only_flags_and_approved_ui_changes(self):
        for row in self.manifest['entries']:
            old=fixtures.document('combat-batch03','before',row['path']);new=fixtures.document('combat-batch03','staged',row['path'])
            self.assertEqual(b.restore(new,row,old),old)
            if row['kind']=='ui':
                actions={v['action_type'] for _,v in b.walk(new,active=True) if 'action_type' in v}
                self.assertLessEqual(actions,{'SET_VARIABLE','SET_ENTITY_KV','STORAGE_BOX','IF_THEN_ELSE',
                    'SET_UI_COMP_TEXT','SET_UI_COMP_IMAGE_NEW','RUN_ONCE_TIMER_BY_FRAME_NO_SAVE',
                    'DELETE_TIMER','TRAVERSE_TABLE_NEW','PICK_PLAYER_DO_ACTION'})
    def test_rebuild_request_is_after_prefab_creation(self):
        old=fixtures.document('combat-batch03','before',b.REBUILD);row=next(r for r in self.manifest['entries'] if r['path']==b.REBUILD)
        new=fixtures.document('combat-batch03','staged',b.REBUILD);edit=row['edits'][0];parent=b.at(new,edit['parent']);i=edit['index']
        self.assertEqual(parent[i-1]['element_id'],1935909566000306)
        self.assertIn(1935909566000395,[v.get('element_id') for _,v in b.walk(parent[:i])])
        self.assertEqual(parent[i]['args_list'][1]['args_list'],[b.PREFIX+'已绘制'])
        self.assertEqual(parent[i+1]['args_list'][0]['sub_type'],b.FID)
    def test_legacy_registry_exact_and_no_extra_random(self):
        total=0
        for row in self.manifest['entries']:
            new=fixtures.document('combat-batch03','staged',row['path'])
            for edit in row.get('legacy_edits',[]):
                node=b.at(new,edit['path']);self.assertFalse(node['enable']);total+=1
                for _,v in b.walk(node):
                    self.assertNotIn('RANDOM',str(v.get('sub_type','')))
        self.assertEqual(total,47)
    def test_unknown_or_malformed_operations_fail(self):
        vm=VM()
        with self.assertRaises(AssertionError):vm.ev(b.ex(100002,'NEW_UNKNOWN_API'))
        with self.assertRaises(AssertionError):vm.ev(b.ex(100011,1,b.ex(100011,'GET_NEW_TABLE')))
        with self.assertRaises(AssertionError):vm.run([dict(action_type='DAMAGE',args_list=[])])
    def test_dynamic_diagnostics_switch_is_exact_and_reversible(self):
        registry=traces.legacy_records()
        for row in self.manifest['entries']:
            if row['path'] not in registry:continue
            doc=fixtures.document('combat-batch03','staged',row['path']);records=registry[row['path']]['logs']
            on,undo=traces.toggle_legacy_registered(doc,records,True)
            off,_=traces.toggle_legacy_registered(on,records,False)
            self.assertEqual(off,doc)
            altered=copy.deepcopy(records);altered[0]['args_list']=[]
            with self.assertRaises(AssertionError):traces.toggle_legacy_registered(doc,altered,True)
    def test_combined_future_trace_toggle_preserves_new_ui_and_gameplay(self):
        ordinary=b.load(b.batch02.REGISTRY)['entries'];legacy=traces.legacy_records()
        staged={r['path'] for r in self.manifest['entries']};total=0
        for rel in dict.fromkeys([*ordinary,*legacy]):
            doc=fixtures.document('combat-batch03','staged',rel) if rel in staged else fixtures.document('combat-batch02','staged',rel)
            on=copy.deepcopy(doc)
            if rel in ordinary:
                on,_=b.batch02.toggle_logs(on,ordinary[rel]['logs'],True);total+=len(ordinary[rel]['logs'])
            if rel in legacy:
                on,_=traces.toggle_legacy_registered(on,legacy[rel]['logs'],True);total+=len(legacy[rel]['logs'])
            off=copy.deepcopy(on)
            if rel in ordinary:off,_=b.batch02.toggle_logs(off,ordinary[rel]['logs'],False)
            if rel in legacy:off,_=traces.toggle_legacy_registered(off,legacy[rel]['logs'],False)
            self.assertEqual(off,doc,rel)
        self.assertEqual(total,1716)
    def test_native_structure_validator_and_local_declarations(self):
        sys.path.insert(0,'C:/Users/littl/.codex/plugins/cache/y3-local/y3-eca/0.1.0')
        from eca_core import validate_structure
        checked=0;warnings=0
        for row in self.manifest['entries']:
            old=fixtures.document('combat-batch03','before',row['path']);doc=fixtures.document('combat-batch03','staged',row['path'])
            pairs=([(old,doc)] if row['kind'] in ('ui','rebuild') else
                   [(old['trigger_dict'][tid],t) for tid,t in doc['trigger_dict'].items()])
            for prior,t in pairs:
                report=validate_structure(t);before=validate_structure(prior)
                self.assertTrue(report['structure_valid'],(row['path'],report['issues']))
                self.assertLessEqual(report['warning_count'],before['warning_count'])
                checked+=1;warnings+=report['warning_count']
                if row['kind']=='ui':
                    names=[name for values in t['var_data'][0].values() for name in values]
                    self.assertEqual(len(names),len(set(names)))
                    self.assertEqual(set(names),set(t['var_data'][1]))
                    self.assertEqual(set(names),set(t['var_data'][2]))
        type(self).native_checked=checked;type(self).native_warnings=warnings
    def test_sparse_integer_rows_keep_original_fill_rules(self):
        u,m=fixture(stack=4);vm=VM()
        u.kv['能量格数据表']={k:{'能量格子':Obj('cell')} for k in (-2,1,3,8)}
        vm.invoke(self.new,u,m);vm.tick()
        self.assertEqual(state(u)[1],[134268765,134268765,134268765,134246678])
    def test_burst_reduction_counts_are_model_only(self):
        u,m=fixture(12);vm=VM()
        vm.invoke(self.new,u,m);vm.tick();vm.writes=[]
        for layer in range(2,11):m.props['stack']=layer;vm.invoke(self.new,u,m)
        vm.tick()
        self.assertEqual(collections.Counter(w[0] for w in vm.writes),{'image':9,'text':1})
        # 9 old events would write 108 images and 9 text values. This counts
        # API operations, and deliberately does not estimate a frame-time gain.


if __name__ == '__main__':
    unittest.main(verbosity=2)
