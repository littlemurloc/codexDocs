"""Execute the staged ECA graph in a bounded offline semantics harness.

This checks card coverage, arithmetic and lifecycle; it is not a Y3 engine test.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import unittest
import y3_wu_command_cards as b

def read(rel):
    fix=b.WORK.parent/'wu-fix-20261017'
    if rel=='modifier/134285001.json' and (fix/'published.json').exists():
        candidate=(fix/'controller-fixed.json').read_bytes()
        record=json.loads((fix/'published.json').read_text('utf8'))
        assert hashlib.sha256(candidate).hexdigest()==record['after']
        return json.loads(candidate)
    return json.loads((b.STAGE/rel).read_text('utf8'))

@dataclass
class Unit:
    name:str
    player:int=1
    tags:set=field(default_factory=set)
    cards:set=field(default_factory=set)
    kv:dict=field(default_factory=dict)
    hp:float=1000.
    alive:bool=True
    attributes:dict=field(default_factory=dict)
    card_categories:dict=field(default_factory=dict)

class World:
    def __init__(self):self.units=[];self.captains={};self.buffs={};self.counts={}
    def has(self,u,bid):return u is not None and (u.name,bid) in self.buffs
    def add(self,u,bid):
        key=(u.name,bid)
        if key in self.buffs:return self.buffs[key]
        vm=VM(self,u,bid,True);self.buffs[key]=vm
        self.counts[key]=self.counts.get(key,0)+1
        vm.fire('OBTAIN_MODIFIER');return vm
    def remove(self,vm):
        if (vm.owner.name,vm.oid) in self.buffs:
            vm.fire('LOSS_MODIFIER');self.buffs.pop((vm.owner.name,vm.oid),None)
    def emit(self,eid,**params):
        for vm in list(self.buffs.values()):vm.fire('RECEIVE_CUSTOM_EVENT',eid,params)
    def tick(self):
        for vm in list(self.buffs.values()):
            if vm.oid==b.CONTROL:vm.fire('MODIFIER_CYCLE_TRIGGER')
        for vm in list(self.buffs.values()):
            if vm.oid==b.ARMY:vm.fire('MODIFIER_CYCLE_TRIGGER')
    def card(self,u,aid,add=True,before_lose=False):
        vm=VM(self,u,aid,False)
        if add:
            # Actual project: normal selections use category 2; the merge
            # function grants these result cards in category 3.
            u.card_categories[aid]=3 if aid in (134250143,134275559,134228375,134273390,134269447,134245355) else 2
            u.cards.add(aid);vm.fire('ABILITY_OBTAIN')
        elif before_lose:
            vm.fire('ABILITY_LOSE');u.cards.remove(aid)
        else:u.cards.remove(aid);vm.fire('ABILITY_LOSE')
    def attr(self,u,key):
        base=u.attributes.get(key,1000. if key=='hp_max' else 0.)
        flat=ratio=0.
        for (name,_),vm in self.buffs.items():
            if name==u.name:
                flat+=vm.contributions.get((key,'ATTR_BASE'),0.)
                ratio+=vm.contributions.get((key,'ATTR_ALL_RATIO'),0.)
        return (base+flat)*(1+ratio/100.)
    def contribution(self,u,key,mode='ATTR_BASE'):
        vm=self.buffs.get((u.name,b.ARMY))
        return vm.contributions.get((key,mode),0.) if vm else 0.

class VM:
    def __init__(self,w,owner,oid,modifier):
        self.w,self.owner,self.oid,self.modifier=w,owner,oid,modifier
        self.obj=read(('modifier/' if modifier else 'ability/')+str(oid)+'.json')
        self.kv={k:v['value'] for k,v in read(('editor_table/modifierall/' if modifier else 'editor_table/abilityall/')+str(oid)+'.json').get('kv',{}).items()}
        self.vars={};self.contributions={};self.registered=set();self.selected=None;self.params={}
    def variable(self,node):
        raw=node['args_list'][0];return (raw['items'] if isinstance(raw,dict) else raw)[1]
    def ev(self,v):
        if not isinstance(v,dict):return v
        if '__tuple__' in v:return v['items']
        t=v.get('sub_type');a=v.get('args_list',[])
        if t in (1,11,2,'VARIABLE'):
            if a and isinstance(a[0],dict) and '__tuple__' in a[0]:return self.vars.get(self.variable(v),0.)
            return self.ev(a[0]) if len(a)==1 else [self.ev(x) for x in a]
        if t=='ABILITY_OWNER' or t=='MODIFIER_OWNER':return self.owner
        if t=='CUR_ABILITY' or t=='CUR_MODIFIER':return self
        if t=='FOR_EACH_SELECTED_UNIT':return self.selected
        if t=='CHECK_HAS_ABILITY_TYPE':return self.ev(a[1]) in self.ev(a[0]).cards
        if t=='UNIT_HAS_MODIFIER':return self.w.has(self.ev(a[0]),self.ev(a[1]))
        if t in ('GET_FLOAT_KV','GET_INTEGER_KV','GET_UNIT_ENTITY_KV','GET_UNIT_GROUP_KV'):
            entity,key=self.ev(a[0]),self.ev(a[1])
            if isinstance(entity,tuple):
                aid=entity[1];return read('editor_table/abilityall/'+str(aid)+'.json')['kv'].get(key,{}).get('value',0.)
            return entity.kv.get(key,[] if t=='GET_UNIT_GROUP_KV' else None if t=='GET_UNIT_ENTITY_KV' else 0.) if entity else None
        if t=='GET_ABILITY_BY_AID':
            u,category,aid=[self.ev(x) for x in a]
            return (u,aid) if aid in u.cards and u.card_categories.get(aid)==category else None
        if t=='ARITHMETIC_OPERATION':
            x,op,y=[self.ev(x) for x in a]
            return x+y if op=='+' else x-y if op=='-' else x*y if op=='*' else x/y
        if t=='GET_UNIT_ATTR':return self.w.attr(self.ev(a[0]),self.ev(a[2]))
        if t=='GET_HP_CUR':return self.ev(a[0]).hp
        if t=='OWNER_PLAYER':return self.ev(a[0]).player
        if t=='6570be50be1a11f1916d7b0e2885c54e':return self.w.captains.get(self.ev(a[0]),[])
        if t=='GET_CUS_EVENT_PARAM':return self.params[self.ev(a[0])]
        if t=='REG_MODIFIER_TRIGGER' or t=='REG_ABILITY_TRIGGER':return self.ev(a[0])
        raise AssertionError('Unhandled expression '+str(t))
    def cond(self,node):
        t=node['condition_type'];a=node['args_list']
        if t=='OR':return any(self.cond(x) for x in a[0]['args_list'])
        if t=='TYPE_IS_EXIST':return self.ev(a[0]) is not None
        if t=='IS_UNIT_ALIVE':return self.ev(a[0]).alive
        if t=='UNIT_HAS_TAG':return self.ev(a[1]) in self.ev(a[0]).tags
        if t in ['FLOAT_COMPARE','UNIT_COMPARE','BOOL_COMPARE']:
            x,op,y=[self.ev(x) for x in a]
            return x==y if op=='==' else x!=y if op=='!=' else x>y if op=='>' else x>=y if op=='>=' else x<y if op=='<' else x<=y
        raise AssertionError('Unhandled condition '+t)
    def run(self,actions):
        for a in actions:
            if isinstance(a,int):
                self.registered.add(a)
                tr=self.obj['trigger_dict'][str(a)]
                self.vars[self.variable(tr['sub_trigger_owner_set_var_action']['args_list'][0])]=a
                continue
            t=a['action_type'];v=a['args_list']
            if t=='SET_ENTITY_KV':self.ev(v[0]).kv[self.ev(v[1])]=self.ev(v[2])
            elif t=='SET_VARIABLE':self.vars[self.variable(v[0])]=self.ev(v[1])
            elif t=='IF_THEN_ELSE':self.run(v[1 if all(self.cond(c) for c in v[0]['args_list']) else 2]['args_list'])
            elif t=='PICK_UNIT_DO_ACTION':
                group=list(self.ev(v[0]));old=self.selected
                for selected in group:self.selected=selected;self.run(v[1]['args_list'])
                self.selected=old
            elif t=='ADD_MODIFIER':self.w.add(self.ev(v[0]),self.ev(v[1]))
            elif t=='REMOVE_BUFF_INS':self.w.remove(self.ev(v[0]))
            elif t=='SET_MODIFIER_OWNER_ATTR':self.ev(v[0]).contributions[(self.ev(v[1]),self.ev(v[2]))]=self.ev(v[3])
            elif t=='CLEAR_MODIFIER_OWNER_ATTR':self.ev(v[0]).contributions.clear()
            elif t=='ADD_CUR_HP':
                u=self.ev(v[0]);u.hp+=self.ev(v[1])
            elif t=='SEND_CUSTOM_EVENT':self.w.emit(self.ev(v[0]),载体单位=self.ev(v[1]))
            elif t=='UNREG_TRIGGER':self.registered.discard(self.ev(v[0]))
            else:raise AssertionError('Unhandled action '+t)
    def fire(self,event,eid=None,params=None):
        old=self.params;self.params=params or {}
        for k,t in self.obj['trigger_dict'].items():
            if t.get('p_trigger_id') is not None and int(k) not in self.registered:continue
            ev=t['event'][0]
            if ev['event_type']!=event:continue
            if event=='RECEIVE_CUSTOM_EVENT' and ev['args_list'][0]['args_list'][0]!=eid:continue
            if all(self.cond(c) for c in t['condition']):self.run(t['action'])
        self.params=old

def world():
    w=World();carrier=Unit('carrier');front=Unit('front',tags={'吴国'},kv={'归属阵型编号':1})
    rear=Unit('rear',tags={'蜀国'},kv={'归属阵型编号':7})
    archer=Unit('archer',tags={'弓兵'},kv={'所属英雄':front})
    infantry=Unit('infantry',tags={'刀兵'},kv={'所属英雄':rear})
    front.kv['带领小队']=[archer];rear.kv['带领小队']=[infantry]
    w.units=[carrier,front,rear,archer,infantry];w.captains[1]=[front,rear]
    return w,carrier,front,rear,archer,infantry

class WuTests(unittest.TestCase):
    def test_each_of_58_excel_fields_reaches_an_actual_buff_contribution(self):
        data=json.loads(b.CATALOG.read_text('utf8'));checked=0
        # Independent spreadsheet-name to engine-attribute mapping.
        mapping={'力量':('strength','ATTR_BASE'),'敏捷':('agility','ATTR_BASE'),'智力':('intelligence','ATTR_BASE'),
                 '生命值':('hp_max','ATTR_BASE'),'生命%':('hp_max','ATTR_ALL_RATIO'),'攻击力':('attack_phy','ATTR_BASE'),
                 '速度':('ori_speed','ATTR_ALL_RATIO'),'攻速':('attack_speed','ATTR_BASE'),
                 '暴击率':('critical_chance','ATTR_BASE'),'暴击伤害':('critical_dmg','ATTR_BASE'),
                 '技能伤害':(b.SKILL_DAMAGE,'ATTR_BASE'),'所有伤害':('extra_dmg','ATTR_BASE')}
        for row in data['rows']:
            if row['faction']!='吴国':continue
            w,carrier,front,rear,archer,infantry=world();aid=row['ids'][0]
            w.card(carrier,aid);w.tick()
            for raw in row['base']:
                if raw in (None,'','-'):continue
                name,val=raw.split('+');value=float(val.rstrip('%'));checked+=1
                keys=[(s,'ATTR_ALL_RATIO' if name.endswith('%') else 'ATTR_BASE') for s in ['strength','agility','intelligence']] if name.startswith('全属性') else [mapping[name]]
                for key,mode in keys:
                    # The non-Wu, non-archer front/rear unit isolates basic effects.
                    if key=='extra_dmg':
                        expected=value+(50 if aid==b.EX else 0) # rear-only EX bonus
                    else:expected=value
                    self.assertEqual(w.contribution(rear,key,mode),expected,(row['row'],raw,key))
                    if key!='extra_dmg':self.assertEqual(w.contribution(archer,key,mode),expected)
        self.assertEqual(checked,58)
    def test_faction_benefits_inherit_to_soldier_not_enemy_or_other_faction(self):
        w,c,f,r,a,i=world();w.card(c,134271490);w.tick()
        self.assertEqual(w.contribution(f,'extra_dmg'),30) # all +10 and Wu passive +20
        self.assertEqual(w.contribution(a,'extra_dmg'),30)
        self.assertEqual(w.contribution(r,'extra_dmg'),10)
        self.assertEqual(w.contribution(i,'extra_dmg'),10)
    def test_ur_and_ex_terminal_tiers_do_not_stack(self):
        w,c,f,r,a,i=world()
        for aid in b.UR:w.card(c,aid)
        w.tick()
        self.assertEqual(c.kv[b.PREFIX+'单卡吴国伤害'],110)
        self.assertEqual(c.kv[b.PREFIX+'套牌吴国伤害'],40)
        self.assertEqual(c.kv[b.PREFIX+'套牌后排伤害'],30)
        w.card(c,b.EX);w.tick()
        self.assertEqual(c.kv[b.PREFIX+'单卡吴国伤害'],140)
        self.assertEqual(c.kv[b.PREFIX+'套牌吴国伤害'],60)
        self.assertEqual(c.kv[b.PREFIX+'套牌后排伤害'],0)
        self.assertEqual(c.kv[b.PREFIX+'套牌弓兵伤害'],0)
        self.assertEqual(c.kv[b.PREFIX+'终极弓兵后排伤害'],50)
    def test_terminal_archer_and_rear_overlap_only_receives_one_50_percent(self):
        w,c,f,r,a,i=world();r.tags.add('弓兵');w.card(c,b.EX);w.tick()
        self.assertEqual(w.contribution(r,'extra_dmg'),50)
    def test_completed_early_sets_retain_benefits(self):
        w,c,*_=world()
        for aid in b.RESULTS:w.card(c,aid)
        self.assertEqual(c.kv[b.PREFIX+'套牌吴国伤害'],70)
        self.assertEqual(c.kv[b.PREFIX+'套牌弓兵伤害'],20)
    def test_normal_selection_after_merge_can_recompute_both_categories(self):
        w,c,f,*_=world()
        w.card(c,134275559)  # merge result, category 3
        w.card(c,134263404)  # next ordinary selection, category 2
        w.tick()
        self.assertEqual(c.kv[b.PREFIX+'套牌吴国伤害'],10)
        self.assertEqual(w.contribution(f,'agility'),5)
        self.assertEqual(w.contribution(f,'extra_dmg'),10)
    def test_duplicate_refresh_level_change_and_hp_ratio(self):
        w,c,f,r,a,i=world();f.hp=400
        w.card(c,134238466);w.tick();expected=w.attr(f,'hp_max')*.4
        self.assertAlmostEqual(f.hp,expected)
        old=dict(w.buffs[(f.name,b.ARMY)].contributions)
        for _ in range(5):w.card(c,134238466);w.tick()
        VM(w,c,134238466,False).fire('ABILITY_LEVEL_CHANGED');w.tick()
        self.assertEqual(w.buffs[(f.name,b.ARMY)].contributions,old)
        self.assertEqual(w.counts[(f.name,b.ARMY)],1)
        self.assertAlmostEqual(f.hp,expected)
    def test_new_soldier_and_captain_receive_current_profile(self):
        w,c,f,r,a,i=world();w.card(c,134263404);w.tick()
        new=Unit('new',kv={'所属英雄':f});f.kv['带领小队'].append(new)
        captain=Unit('newcap',tags={'吴国'},kv={'归属阵型编号':8,'带领小队':[]});w.captains[1].append(captain)
        w.tick();self.assertEqual(w.contribution(new,'agility'),5);self.assertEqual(w.contribution(captain,'agility'),5)
    def test_lose_card_before_engine_removal_then_complete_cleanup(self):
        w,c,f,r,a,i=world();w.card(c,134263404);w.card(c,134234426);w.tick()
        self.assertEqual(w.contribution(f,'agility'),10)
        w.card(c,134263404,False,True);w.tick();self.assertEqual(w.contribution(f,'agility'),5)
        w.card(c,134234426,False,True);w.tick();self.assertFalse(w.has(c,b.CONTROL));self.assertFalse(w.has(f,b.ARMY))
        self.assertEqual(w.contribution(f,'agility'),0)
    def test_players_are_isolated(self):
        w,c,f,r,a,i=world();c2=Unit('carrier2',player=2);f2=Unit('army2',player=2,tags={'吴国'},kv={'带领小队':[]})
        w.captains[2]=[f2];w.card(c,134263404);w.card(c2,134244625);w.tick()
        self.assertEqual(w.contribution(f,'agility'),5);self.assertEqual(w.contribution(f,'strength'),0)
        self.assertEqual(w.contribution(f2,'strength'),5);self.assertEqual(w.contribution(f2,'agility'),0)
    def test_rear_uses_formation_key_and_refreshes_at_next_wave(self):
        w,c,f,r,a,i=world();w.card(c,b.EX);w.tick()
        self.assertEqual(w.contribution(r,'extra_dmg'),50)
        self.assertEqual(w.contribution(i,'extra_dmg'),50)
        self.assertEqual(w.contribution(f,'extra_dmg'),90)
        # Moving a unit does not change the formation KV. A new preparation setup does.
        r.kv['归属阵型编号']=2;w.emit(b.PHASE,阶段编号=2);w.tick()
        self.assertEqual(w.contribution(r,'extra_dmg'),0);self.assertEqual(w.contribution(i,'extra_dmg'),0)
    def test_all_31_cards_signature_and_no_extra_damage_listener(self):
        w,c,*_=world();specs=b.load_specs()
        for aid in specs:w.card(c,aid)
        w.tick();self.assertEqual(w.buffs[(c.name,b.CONTROL)].kv[b.SIGNATURE],2**31-1)
        for rel in ('modifier/'+str(b.ARMY)+'.json','modifier/'+str(b.CONTROL)+'.json'):
            self.assertFalse(any(n.get('action_type') in ['SET_CUR_DAMAGE','APPLY_DAMAGE'] for n in b.walk(read(rel))))

def structure():
    manifest=json.loads((b.WORK/'manifest.json').read_text('utf8'));ids=set();elements=set()
    for rel,m in manifest.items():
        payload=(b.STAGE/rel).read_bytes();assert hashlib.sha256(payload).hexdigest()==m['after']
        if not rel.startswith(('ability/','modifier/')):continue
        d=json.loads(payload);td=d['trigger_dict']
        for k,t in td.items():
            assert t['trigger_id']==int(k) and int(k) not in ids;ids.add(int(k));assert t['valid'] is True
            assert k in d['local_variable']
            if t.get('p_trigger_id') is not None:
                p=td[str(t['p_trigger_id'])];assert int(k) in p['action'];assert t['is_conf']
                assert t['sub_trigger_owner_set_var_action']['args_list'][1]['args_list'][0]['args_list'][0]==int(k)
        for n in b.walk(d):
            if 'element_id' in n:assert n['element_id'] not in elements;elements.add(n['element_id'])
            if n.get('action_type')=='ADD_MODIFIER':
                bid=n['args_list'][1]['args_list'][0]
                assert (b.STAGE/f'editor_table/modifierall/{bid}.json').exists() or (b.MAP/f'editor_table/modifierall/{bid}.json').exists()
    assert not any(r in manifest for r in ['tables/军令卡牌技能表.json','tables/吴国temp.json','globaltriggervariable.json'])
    print('Structural checks:',len(manifest),'files;',len(ids),'unique triggers;',len(elements),'unique elements')

if __name__=='__main__':
    structure();unittest.main(verbosity=2)
