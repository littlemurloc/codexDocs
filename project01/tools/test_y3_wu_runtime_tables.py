"""Offline native-ECA execution with real grant-before-pool-write ordering."""
from __future__ import annotations
import contextlib,copy,functools,hashlib,json,random,unittest
from pathlib import Path
import test_y3_wu_command_cards as old
import y3_wu_runtime_tables as d

Native=old.VM;old_read=old.read
FUNCS={}
LEVEL_FIX=d.WORK.parent/'wu-level-owner-fix-20261018'/'staged'
for p in (d.STAGE/d.r.FOLDER).glob('*.json'):
    doc=json.loads(p.read_text('utf8'));FUNCS[doc['func_id']]=doc
EXTRA={}
@functools.lru_cache(None)
def staged(rel):
    patched=LEVEL_FIX/rel
    if rel.startswith('ability/') and patched.exists():return json.loads(patched.read_text('utf8'))
    p=d.STAGE/rel
    return json.loads(p.read_text('utf8')) if p.exists() else old_read(rel)
def read(rel):return EXTRA.get(rel,staged(rel)) if rel not in EXTRA else EXTRA[rel]
class Returned(Exception):
    def __init__(self,value):self.value=value

class VM(Native):
    def __init__(self,w,owner,oid,modifier):
        super().__init__(w,owner,oid,modifier)
        self.handle=w.handles.get((owner.name,oid)) if not modifier else None
        self.iter_key=None
    def execute(self,fid,args):
        doc=FUNCS[fid];vm=object.__new__(VM)
        vm.w,vm.owner,vm.oid,vm.modifier=self.w,self.owner,doc['trigger_id'],False
        vm.obj=doc;vm.kv={};vm.vars={};vm.contributions={};vm.registered=set();vm.selected=None;vm.params={};vm.handle=None;vm.iter_key=None
        for values in doc['var_data'][0].values():vm.vars.update(copy.deepcopy(values))
        assert len(args)==len(doc['func_param_list'])
        for spec,arg in zip(doc['func_param_list'],args):vm.vars[spec['items'][0]]=arg
        self.w.function_calls[fid]=self.w.function_calls.get(fid,0)+1
        try:vm.run(doc['action'])
        except Returned as result:return result.value
    def ev(self,v):
        if not isinstance(v,dict):return v
        t=v.get('sub_type');a=v.get('args_list',[])
        if t=='ABILITY_OWNER' and getattr(self,'active_event',None)=='ABILITY_LEVEL_CHANGED':
            raise AssertionError('ABILITY_LEVEL_CHANGED does not supply ABILITY_OWNER')
        if t=='GET_ABILITY_OWNER':return self.ev(a[0])[0]
        if t in FUNCS:return self.execute(t,[self.ev(x) for x in a])
        if t=='CUR_ABILITY':return self.handle
        if t==6:return self.vars.get(self.variable(v),0)
        if t=='VARIABLE' and v.get('arg_type')==100011 and a and isinstance(a[0],dict) and a[0].get('items')==['TABLE','卡牌技能池-表']:
            return self.w.pools.get(self.ev(a[1]))
        if t=='9384d061198e11ef967be8c829c05699':return self.ev(a[0])
        if t=='GET_NEW_TABLE':return {}
        if t=='GET_TABLE_LENGTH':return len(self.ev(a[0]))
        if t=='GET_TABLE_KV':return self.ev(a[0]).kv.get(self.ev(a[1]))
        if t=='ITER_TABLE_KEY_INT':return self.iter_key
        if isinstance(t,str) and t.endswith('_TABLE_VAR_ND'):
            table,row,key=[self.ev(x) for x in a]
            return table.get(row,{}).get(key)
        if t=='GET_ABILITY_TABLE_VAR_1D':return self.ev(a[0]).get(self.ev(a[1]))
        if t=='ABILITY_NAME_OF_ABILITY':return self.ev(a[0])[1]
        if t=='ANY_VAR_TO_STR':return str(self.ev(a[0]))
        if t=='STR_JOIN':return ''.join(str(self.ev(x)) for x in a)
        if t=='INT_PLUS_ONE':return self.ev(a[0])+1
        if t in ('GET_STRING_KV','GET_BOOLEAN_KV'):
            entity,key=[self.ev(x) for x in a]
            if isinstance(entity,tuple):return read(f'editor_table/abilityall/{entity[1]}.json')['kv'].get(key,{}).get('value','')
            return entity.kv.get(key,'' if t=='GET_STRING_KV' else False)
        return super().ev(v)
    def fire(self,event,eid=None,params=None):
        previous=getattr(self,'active_event',None);self.active_event=event
        try:return super().fire(event,eid,params)
        finally:self.active_event=previous
    def cond(self,node):
        t=node['condition_type'];a=node['args_list']
        if t=='TYPE_IS_EXIST':
            value=self.ev(a[0])
            if isinstance(value,tuple):return self.w.handles.get((value[0].name,value[1]))==value
            return value is not None
        if t=='STRING_COMPARE':
            x,op,y=[self.ev(v) for v in a];return x==y if op=='==' else x!=y
        if t=='TABLE_HAS_KEY':return self.ev(a[1]) in self.ev(a[0])
        if t=='HAS_KV_ANY':
            entity,key=[self.ev(v) for v in a]
            return key in read(f'editor_table/abilityall/{entity[1]}.json')['kv'] if isinstance(entity,tuple) else key in entity.kv
        return super().cond(node)
    def run(self,actions):
        for a in actions:
            if isinstance(a,int):super().run([a]);continue
            t=a['action_type'];v=a['args_list']
            if t=='CALL_TRIGGER_FUNC':self.execute(v[0]['sub_type'],[self.ev(x) for x in v[0]['args_list']])
            elif t==400342:raise Returned(self.ev(v[0]))
            elif t=='STORAGE_BOX':self.run(v[1 if all(self.cond(c) for c in v[0]['args_list']) else 2]['args_list'])
            elif t=='FOR_INT_DO_ACTION_NEW':
                name=self.variable(v[0]);start,end=int(self.ev(v[1])),int(self.ev(v[2]))
                for row in range(start,end+1):self.vars[name]=row;self.run(v[3]['args_list'])
            elif t=='TRAVERSE_TABLE_NEW':
                table=self.ev(v[0]);previous=self.iter_key
                for key in list(table):self.iter_key=key;self.run(v[1]['args_list'])
                self.iter_key=previous
            elif t=='SET_TABLE_VALUE_ND':
                table,row,key,value=[self.ev(x) for x in v];table.setdefault(row,{})[key]=value
            elif t=='SET_TABLE_VALUE_1D':
                table,key,value=[self.ev(x) for x in v];table[key]=value
            else:super().run([a])

class World(old.World):
    def __init__(self):
        super().__init__();self.pools={};self.handles={};self.serial=0;self.function_calls={}
        self.prewrite_snapshots=[]
    def card(self,u,aid,add=True,before_lose=False):
        self.pools.setdefault(u.player,{})
        if add:
            self.serial+=1
            handle=self.handles.setdefault((u.name,aid),(u,aid,self.serial))
            u.cards.add(aid);vm=VM(self,u,aid,False);vm.fire('ABILITY_OBTAIN')
            self.prewrite_snapshots.append(dict(u.kv))
            pool=self.pools[u.player]
            pool[max(pool,default=0)+1]={'技能':handle,'归属单位':u,'是否已抽取':True}
        else:
            vm=VM(self,u,aid,False)
            if before_lose:vm.fire('ABILITY_LOSE')
            u.cards.remove(aid);self.handles.pop((u.name,aid),None)
            if not before_lose:vm.fire('ABILITY_LOSE')
        VM(self,u,aid,False).execute(d.FIDS[14],[u])

@contextlib.contextmanager
def runtime():
    old.VM=VM;old.read=read
    try:yield
    finally:old.VM=Native;old.read=old_read;EXTRA.clear()

def world():
    base,c,*units=old.world();w=World();w.units=base.units;w.captains=base.captains
    return (w,c,*units)

class ExistingCases(old.WuTests):
    def setUp(self):
        self.env=runtime();self.env.__enter__();self.original_world=old.world;old.world=world_proxy
    def tearDown(self):old.world=self.original_world;self.env.__exit__(None,None,None)
    def test_all_31_cards_signature_and_no_extra_damage_listener(self):
        w,c,*_=world_proxy()
        for aid in d.b.load_specs():w.card(c,aid)
        w.tick();m=w.buffs[(c.name,d.b.CONTROL)]
        self.assertEqual(m.kv[d.r.COUNT],31)
        self.assertEqual(len(m.kv[d.r.APPLIED].split('；'))-1,31)
        for oid in (d.b.CONTROL,d.b.ARMY):
            self.assertFalse(any(n.get('action_type') in ('SET_CUR_DAMAGE','APPLY_DAMAGE') for n in d.b.walk(read(f'modifier/{oid}.json'))))

original_world=old.world
def world_proxy():
    base,c,*units=original_world();w=World();w.units=base.units;w.captains=base.captains
    return (w,c,*units)

class RuntimeCases(unittest.TestCase):
    def test_level_change_uses_current_ability_owner_on_all_31_cards(self):
        for aid in d.b.load_specs():
            doc=read(f'ability/{aid}.json')
            event=next(t for t in doc['trigger_dict'].values() if t['event'][0]['event_type']=='ABILITY_LEVEL_CHANGED')
            self.assertFalse(any(n.get('sub_type')=='ABILITY_OWNER' for n in d.b.walk(event)))
            self.assertEqual(event['action'][0]['args_list'][0]['args_list'],
                             [d.b.n(100006,'GET_ABILITY_OWNER',d.b.ability())])
    def test_level_change_recalculates_without_stacking(self):
        with runtime():
            w,c,f,*_=world_proxy();aid=134263404;w.card(c,aid)
            obj=copy.deepcopy(read(f'editor_table/abilityall/{aid}.json'))
            obj['kv']['属性_agility_ATTR_BASE']['value']=7
            EXTRA[f'editor_table/abilityall/{aid}.json']=obj
            for _ in range(3):VM(w,c,aid,False).fire('ABILITY_LEVEL_CHANGED');w.tick()
            self.assertEqual(w.contribution(f,'agility'),7)
    def test_event_contract_rejects_old_invalid_owner_expression(self):
        with runtime():
            w,c,*_=world_proxy();aid=134263404;w.card(c,aid)
            doc=copy.deepcopy(read(f'ability/{aid}.json'))
            event=next(t for t in doc['trigger_dict'].values() if t['event'][0]['event_type']=='ABILITY_LEVEL_CHANGED')
            event['action'][0]['args_list'][0]['args_list']=[d.b.unit('ABILITY_OWNER')]
            EXTRA[f'ability/{aid}.json']=doc
            with self.assertRaisesRegex(AssertionError,'does not supply'):
                VM(w,c,aid,False).fire('ABILITY_LEVEL_CHANGED')
    def test_gain_before_pool_write_does_not_apply_premature_snapshot(self):
        with runtime():
            w,c,f,*_=world_proxy();w.card(c,134263404)
            self.assertNotIn(d.b.PREFIX+'属性_agility_ATTR_BASE',w.prewrite_snapshots[0])
            self.assertEqual(c.kv[d.b.PREFIX+'属性_agility_ATTR_BASE'],5)
            self.assertEqual(w.contribution(f,'agility'),5)
    def test_rules_are_created_once_and_reused(self):
        with runtime():
            w,c,*_=world_proxy();w.card(c,134263404);rules=c.kv[d.RULES_KEY]
            count=w.function_calls[d.FIDS[13]]
            for aid in [134234426,134275559,134244625]:w.card(c,aid)
            for _ in range(5):w.tick()
            self.assertIs(c.kv[d.RULES_KEY],rules)
            self.assertEqual(w.function_calls[d.FIDS[13]],count)
            self.assertEqual(count,20)
    def test_sparse_quote_duplicate_foreign_and_removed_records_are_filtered(self):
        with runtime():
            w,c,f,*_=world_proxy();w.card(c,134263404);w.card(c,134263404)
            pool=w.pools[1];pool[20]={};pool[40]={'技能':None,'归属单位':c}
            other=old.Unit('other',player=1);other.cards.add(134244625)
            handle=(other,134244625,999);w.handles[other.name,134244625]=handle
            pool[60]={'技能':handle,'归属单位':other,'是否已抽取':True}
            w.tick();self.assertEqual(w.contribution(f,'agility'),5);self.assertEqual(w.contribution(f,'strength'),0)
            self.assertEqual(c.kv[d.b.PREFIX+'属性_strength_ATTR_BASE'],0)
            w.card(c,134263404,False,True);w.tick();self.assertFalse(w.has(c,d.b.CONTROL))
    def test_new_card_needs_no_id_list_or_attribute_mapping_edit(self):
        with runtime():
            aid=199990001
            obj=copy.deepcopy(read('editor_table/abilityall/134263404.json'))
            obj['kv']['属性_agility_ATTR_BASE']['value']=7
            EXTRA[f'editor_table/abilityall/{aid}.json']=obj
            EXTRA[f'ability/{aid}.json']=copy.deepcopy(read('ability/134263404.json'))
            w,c,f,*_=world_proxy();w.card(c,aid);w.tick()
            self.assertEqual(w.contribution(f,'agility'),7)
    def test_two_players_have_independent_rule_tables(self):
        with runtime():
            w,c,*_=world_proxy();c2=old.Unit('carrier2',player=2);w.captains[2]=[]
            w.card(c,134263404);w.card(c2,134244625)
            self.assertIsNot(c.kv[d.RULES_KEY],c2.kv[d.RULES_KEY])
    def test_same_card_type_deduplicates_and_reacquisition_ignores_stale_handle(self):
        with runtime():
            w,c,f,*_=world_proxy();w.card(c,134263404);first=w.handles[c.name,134263404]
            w.card(c,134263404,False);w.card(c,134263404);w.tick()
            self.assertNotEqual(first,w.handles[c.name,134263404])
            self.assertEqual(w.contribution(f,'agility'),5)
            self.assertEqual(w.buffs[c.name,d.b.CONTROL].kv[d.r.COUNT],1)
    def test_missing_pool_does_not_remove_controller_before_records_are_ready(self):
        with runtime():
            w,c,*_=world_proxy();w.pools[1]=None
            w.serial+=1;aid=134263404;w.handles[c.name,aid]=(c,aid,w.serial);c.cards.add(aid)
            VM(w,c,aid,False).fire('ABILITY_OBTAIN');w.tick()
            self.assertTrue(w.has(c,d.b.CONTROL))
            w.pools[1]={9:{'技能':w.handles[c.name,aid],'归属单位':c}}
            VM(w,c,aid,False).execute(d.FIDS[14],[c]);w.tick()
            self.assertEqual(c.kv[d.b.PREFIX+'属性_agility_ATTR_BASE'],5)
    def test_no_rules_or_card_list_preset_uuid_remains(self):
        for p in d.STAGE.rglob('*.json'):
            text=p.read_text('utf8');self.assertNotIn(d.r.CARD_TID,text);self.assertNotIn(d.r.FIELD_TID,text)
        for p in (d.STAGE/d.r.FOLDER).glob('*.json'):
            self.assertFalse(any(n.get('sub_type')=='GET_ABILITY_BY_AID' for n in d.b.walk(json.loads(p.read_text('utf8')))))
    def test_native_variable_types(self):
        for doc in FUNCS.values():
            for node in d.b.walk(doc):
                args=node.get('args_list',[])
                if node.get('arg_type') in (100001,100039,100011) and args and isinstance(args[0],dict) and args[0].get('__tuple__'):
                    self.assertEqual(node['sub_type'],'VARIABLE')

def structure():
    manifest=json.loads((d.WORK/'manifest.json').read_text('utf8'));elements=set();function_ids=set(FUNCS)
    for rel,record in manifest.items():
        if record['after'] is None:continue
        raw=(d.STAGE/rel).read_bytes();assert hashlib.sha256(raw).hexdigest()==record['after']
        doc=json.loads(raw)
        if rel.startswith((d.r.FOLDER+'/','ability/','modifier/')) and rel.endswith('.json'):
            for node in d.b.walk(doc):
                if 'element_id' in node:
                    assert node['element_id'] not in elements,(rel,node['element_id']);elements.add(node['element_id'])
                kind=node.get('sub_type')
                if kind in function_ids:
                    assert len(node['args_list'])==len(FUNCS[kind]['func_param_list']),(rel,kind)
    assert len(FUNCS)==14
    assert sum(v['after'] is None for v in manifest.values())==3
    for rel in ['tables/军令卡牌技能表.json','tables/吴国temp.json','customevent.json','zhlanguage.json','globaltriggervariable.json']:
        assert rel not in manifest
    print('Structure:',len(manifest),'paths;',len(FUNCS),'functions;',len(elements),'unique ECA elements')

if __name__=='__main__':structure();unittest.main(verbosity=2)
