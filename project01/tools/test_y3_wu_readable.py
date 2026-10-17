"""Execute refactored native ECA and compare it with the corrected old graph."""
from __future__ import annotations
import contextlib
import copy
import hashlib
import json
from pathlib import Path
import random
import unittest
import test_y3_wu_command_cards as old
import refactor_y3_wu_cards as r

Native=old.VM
old_read=old.read
FUNCS={}
TABLES={}
for p in r.STAGE.rglob('*.json'):
    doc=json.loads(p.read_text('utf8'))
    if not isinstance(doc,dict):continue
    if doc.get('func_id'):FUNCS[doc['func_id']]=doc
    if doc.get('tid'):TABLES[doc['tid']]=doc['table_data']['data']

def read(rel):
    p=r.STAGE/rel
    return json.loads(p.read_text('utf8')) if p.exists() else old_read(rel)

class Return(Exception):
    def __init__(self,value):self.value=value

class VM(Native):
    missing=set()
    def execute(self,fid,args):
        doc=FUNCS[fid]
        vm=object.__new__(VM)
        vm.w,vm.owner,vm.oid,vm.modifier=self.w,self.owner,doc['trigger_id'],False
        vm.obj=doc;vm.kv={};vm.vars={};vm.contributions={};vm.registered=set();vm.selected=None;vm.params={}
        for values in doc['var_data'][0].values():vm.vars.update(copy.deepcopy(values))
        assert len(args)==len(doc['func_param_list'])
        for spec,arg in zip(doc['func_param_list'],args):vm.vars[spec['items'][0]]=arg
        try:vm.run(doc['action'])
        except Return as result:return result.value
        return None
    def ev(self,v):
        if not isinstance(v,dict):return v
        t=v.get('sub_type');a=v.get('args_list',[])
        if t==6:return self.vars.get(self.variable(v),0)
        if t in FUNCS:return self.execute(t,[self.ev(x) for x in a])
        if t=='GET_TABLE_LENGTH':return len(TABLES[self.ev(a[0])])-2
        if isinstance(t,str) and t.endswith('_TABLE_VAR_ND'):
            data=TABLES[self.ev(a[0])];row=int(self.ev(a[1]));key=self.ev(a[2])
            return data[row+1][data[0].index(key)]
        if t=='STR_JOIN':return ''.join(str(self.ev(x)) for x in a)
        if t=='INT_PLUS_ONE':return self.ev(a[0])+1
        if t in ('GET_STRING_KV','GET_BOOLEAN_KV'):
            entity,key=self.ev(a[0]),self.ev(a[1]);return entity.kv.get(key,'' if t=='GET_STRING_KV' else False)
        if t=='GET_ABILITY_BY_AID':
            u,category,aid=[self.ev(x) for x in a]
            return (u,aid) if aid in u.cards and u.card_categories.get(aid)==category and (u.name,aid) not in self.missing else None
        return super().ev(v)
    def cond(self,node):
        t=node['condition_type'];a=node['args_list']
        if t=='STRING_COMPARE':
            x,op,y=[self.ev(v) for v in a];return x==y if op=='==' else x!=y
        if t=='HAS_KV_ANY':
            entity,key=[self.ev(v) for v in a]
            if isinstance(entity,tuple):return key in read('editor_table/abilityall/'+str(entity[1])+'.json')['kv']
            return key in entity.kv
        return super().cond(node)
    def run(self,actions):
        for a in actions:
            if isinstance(a,int):super().run([a]);continue
            t=a['action_type'];v=a['args_list']
            if t=='CALL_TRIGGER_FUNC':self.execute(v[0]['sub_type'],[self.ev(x) for x in v[0]['args_list']])
            elif t==400342:raise Return(self.ev(v[0]))
            elif t=='STORAGE_BOX':
                self.run(v[1 if all(self.cond(c) for c in v[0]['args_list']) else 2]['args_list'])
            elif t=='FOR_INT_DO_ACTION_NEW':
                name=self.variable(v[0]);start,end=int(self.ev(v[1])),int(self.ev(v[2]))
                for row in range(start,end+1):self.vars[name]=row;self.run(v[3]['args_list'])
            else:super().run([a])

@contextlib.contextmanager
def runtime(new=True):
    old.VM=VM if new else Native;old.read=read if new else old_read
    try:yield
    finally:old.VM=Native;old.read=old_read;VM.missing.clear()

class ExistingCases(old.WuTests):
    def setUp(self):self.env=runtime();self.env.__enter__()
    def tearDown(self):self.env.__exit__(None,None,None)
    def test_all_31_cards_signature_and_no_extra_damage_listener(self):
        w,c,*_=old.world();specs=r.b.load_specs()
        for aid in specs:w.card(c,aid)
        w.tick()
        controller=w.buffs[(c.name,r.b.CONTROL)]
        self.assertEqual(controller.kv[r.COUNT],31)
        self.assertEqual(len(controller.kv[r.APPLIED].split('；'))-1,31)
        for oid in (r.b.CONTROL,r.b.ARMY):
            self.assertFalse(any(n.get('action_type') in ('SET_CUR_DAMAGE','APPLY_DAMAGE') for n in r.b.walk(read(f'modifier/{oid}.json'))))

class RefactorCases(unittest.TestCase):
    def test_missing_new_instance_defers_commit_and_recovers(self):
        with runtime():
            w,c,f,*_=old.world();w.card(c,134263404);w.tick()
            previous=w.buffs[(c.name,r.b.CONTROL)].kv[r.APPLIED]
            VM.missing.add((c.name,134275559));w.card(c,134275559);w.tick()
            self.assertEqual(w.buffs[(c.name,r.b.CONTROL)].kv[r.APPLIED],previous)
            self.assertEqual(w.contribution(f,'extra_dmg'),0)
            self.assertEqual(w.contribution(f,'agility'),5)
            VM.missing.clear();w.tick()
            self.assertEqual(w.contribution(f,'extra_dmg'),10)
    def test_paramless_base_does_not_require_an_instance_in_a_specific_category(self):
        with runtime():
            w,c,f,*_=old.world();VM.missing.add((c.name,r.b.BASE));w.card(c,r.b.BASE)
            w.card(c,134263404);w.tick();self.assertEqual(w.contribution(f,'agility'),5)
    def test_no_recompute_with_unchanged_ownership(self):
        with runtime():
            w,c,f,*_=old.world();w.card(c,134263404);w.tick();version=c.kv[r.b.REV]
            for _ in range(10):w.tick()
            self.assertEqual(c.kv[r.b.REV],version)
            self.assertEqual(w.counts[(f.name,r.b.ARMY)],1)
    def test_native_graph_matches_old_graph_over_card_and_wave_sequences(self):
        ids=list(r.b.load_specs());rng=random.Random(17)
        operations=[('add',aid) for aid in ids]+[('remove',aid) for aid in rng.sample(ids,16)]
        operations += [('add',aid) for aid in rng.sample(ids,20)]
        def run(new):
            history=[]
            with runtime(new):
                w,c,f,rear,archer,infantry=old.world();units=[f,rear,archer,infantry]
                f.hp=375;rear.hp=650
                for count,(op,aid) in enumerate(operations):
                    w.card(c,aid,op=='add',before_lose=op=='remove');w.tick()
                    if count%5==0:
                        rear.kv['归属阵型编号']=1 if count%10 else 8
                        w.emit(r.b.PHASE,阶段编号=2);w.tick()
                    history.append([(dict(w.buffs[(u.name,r.b.ARMY)].contributions),u.hp) for u in units])
                return history
        self.assertEqual(run(False),run(True))
    def test_all_card_ecas_have_three_small_entry_points(self):
        for aid in r.b.load_specs():
            d=read(f'ability/{aid}.json');self.assertEqual(len(d['trigger_dict']),3)
            for t in d['trigger_dict'].values():self.assertEqual(len(t['action']),1)
    def test_no_per_card_id_enumeration_or_copied_scan_in_buffs_and_functions(self):
        ids=set(r.b.load_specs());calls=0
        for rel in ['modifier/134285001.json','modifier/134285002.json']+[str(p.relative_to(r.STAGE)).replace('\\','/') for p in (r.STAGE/r.FOLDER).glob('*.json')]:
            d=read(rel)
            for n in r.b.walk(d):
                if n.get('arg_type')==100039 and n.get('sub_type')==1:
                    self.assertNotIn(n['args_list'][0],ids)
                if n.get('arg_type')==100177 and n.get('sub_type')==r.FIDS[3]:calls+=1
        self.assertEqual(calls,1)
    def test_boolean_and_ability_type_variables_use_native_variable_encoding(self):
        for doc in FUNCS.values():
            for node in r.b.walk(doc):
                args=node.get('args_list',[])
                if node.get('arg_type') not in (100001,100039) or not args:continue
                if isinstance(args[0],dict) and args[0].get('__tuple__'):
                    self.assertEqual(node['sub_type'],'VARIABLE')
    def test_both_new_tables_are_registered_and_existing_registration_is_preserved(self):
        source=json.loads((r.b.MAP/'editor/tableeditorgroupinfo.json').read_text('utf8'))
        registered=r.register_tables(source)
        entries={n['items'][0]:n['items'][1] for n in r.b.walk(registered)
                 if n.get('__tuple__') and len(n.get('items',[]))==2}
        self.assertEqual(entries[r.CARD_TID],'吴国军略_卡牌登记表')
        self.assertEqual(entries[r.FIELD_TID],'吴国军略_收益参数映射表')
        self.assertEqual(registered[:len(source)],source) if len(registered)>len(source) else None
        self.assertEqual(r.register_tables(registered),registered)

def structure():
    manifest=json.loads((r.WORK/'manifest.json').read_text('utf8'));elements=set();triggers=set()
    assert len(manifest) in (48,49)
    function_ids=set(FUNCS)
    for rel,record in manifest.items():
        raw=(r.STAGE/rel).read_bytes();assert hashlib.sha256(raw).hexdigest()==record['after']
        doc=json.loads(raw)
        for node in r.b.walk(doc):
            if 'element_id' in node:
                assert node['element_id'] not in elements,(rel,node['element_id']);elements.add(node['element_id'])
            kind=node.get('action_type',node.get('sub_type'))
            if kind in function_ids:
                f=FUNCS[kind];assert len(node['args_list'])==len(f['func_param_list'])
                for arg,param in zip(node['args_list'],f['func_param_list']):
                    category=next(c for c,v in f['var_data'][0].items() if param['items'][0] in v)
                    assert arg['arg_type']==r.TYPES[category][0],(rel,kind,param,arg)
        for tid,tr in (doc.get('trigger_dict',{}) if isinstance(doc,dict) else {}).items():
            assert int(tid) not in triggers;triggers.add(int(tid))
            if tr.get('p_trigger_id') is not None:
                assert int(tid) in doc['trigger_dict'][str(tr['p_trigger_id'])]['action']
    forbidden=['tables/军令卡牌技能表.json','tables/吴国temp.json','customevent.json','zhlanguage.json','globaltriggervariable.json']
    assert not set(manifest).intersection(forbidden)
    for d in TABLES.values():
        assert len({row[0] for row in d[2:]})==len(d)-2
    print('Structure:',len(manifest),'files;',len(triggers),'embedded triggers;',len(FUNCS),'functions;',len(elements),'unique elements')

if __name__=='__main__':structure();unittest.main(verbosity=2)
