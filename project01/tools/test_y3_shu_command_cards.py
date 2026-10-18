"""Execute staged native ECA with bounded engine contracts, not a Y3 game test."""
from __future__ import annotations
import contextlib,copy,json,unittest,zipfile
from pathlib import Path
import y3_shu_command_cards as s
import test_y3_wu_runtime_tables as v
old=v.old
Unit=old.Unit
ORIGINAL_VM=v.VM
DATA={p.relative_to(s.STAGE).as_posix():json.loads(p.read_text('utf8')) for p in s.STAGE.rglob('*') if p.is_file()}
TABLE_FIX=s.WORK.parent/'shu-table-fix-20261018'/'staged'
for p in TABLE_FIX.rglob('*.json'):
    DATA[p.relative_to(TABLE_FIX).as_posix()]=json.loads(p.read_text('utf8'))
FUNCS={doc['func_id']:doc for doc in DATA.values() if isinstance(doc,dict) and doc.get('is_func')}
UPGRADE=s.read('global_trigger/function/new/条件判断/判断蜀国匡扶汉室触发升级.json')
FUNCS[s.UPGRADE]=UPGRADE
ATTRFID=s.find_fid('指定单位属性增减')
SPECS=json.loads((s.WORK/'specs.json').read_text('utf8'))
EXTRA={}

def read(rel):
    if rel in EXTRA:return EXTRA[rel]
    if rel in DATA:return DATA[rel]
    return v.staged(rel)

def original(rel):
    with zipfile.ZipFile(s.WORK/'before-shu.zip') as backup:
        return json.loads(backup.read(rel)) if rel in backup.namelist() else None

class VM(ORIGINAL_VM):
    def execute(self,fid,args):
        if fid=='36487c1f2b4f11f0b8029792acb0a9c5':
            player,resource,amount,set_value=args
            self.w.money[player]=amount if set_value else self.w.money.get(player,0)+amount
            return
        if fid==ATTRFID:
            unit,key,add,amount=args
            assert key=='攻击'
            unit.attributes['attack_phy']=unit.attributes.get('attack_phy',0)+(amount if add else -amount)
            return
        if fid==s.MERGE:
            player,index=args;pool=self.w.pools[player]
            assert pool[index]['技能类型']==s.EX and pool[index]['是否合成']
            self.w.merges.append((player,index))
            carrier=self.w.carriers[player];self.w.card(carrier,s.EX)
            pool[index].update(技能=self.w.handles[carrier.name,s.EX],归属单位=carrier,是否已抽取=True)
            return self.w.handles[carrier.name,s.EX]
        return super().execute(fid,args)
    def ev(self,node):
        if not isinstance(node,dict):return node
        t=node.get('sub_type');args=node.get('args_list',[])
        if t==6 and args and isinstance(args[0],dict) and len(args[0].get('items',[]))==2:
            return {'当前进程所在波次编号':self.w.wave,'当前游戏进程阶段':self.w.phase}.get(args[0]['items'][1],0)
        if t in ('GET_FLOAT_KV','GET_INTEGER_KV','GET_STRING_KV','GET_BOOLEAN_KV'):
            entity,key=[self.ev(x) for x in args]
            if isinstance(entity,tuple):
                defaults={k:v['value'] for k,v in read(f'editor_table/abilityall/{entity[1]}.json')['kv'].items()}
                return self.w.ability_kv.setdefault((entity[0].name,entity[1]),defaults).get(key,'' if t=='GET_STRING_KV' else False if t=='GET_BOOLEAN_KV' else 0)
            if isinstance(entity,int):return self.w.player_kv.setdefault(entity,{}).get(key,False if t=='GET_BOOLEAN_KV' else 0)
        if t=='MATH_OPERATION':
            a,op,c=[self.ev(x) for x in args];return a+c if op=='+' else a-c
        if t=='RANDOM_INT':
            lo,hi=[int(self.ev(x)) for x in args]
            result=self.w.random.pop(0) if self.w.random else lo
            assert lo<=result<=hi,(lo,result,hi)
            self.w.random_ranges.append((lo,hi));return result
        if t=='GET_ABILITY_INT_ATTR':
            a,key=[self.ev(x) for x in args];assert key=='ability_level'
            return self.w.levels.get((a[0].name,a[1]),1)
        if t=='GET_MP_CUR':return self.ev(args[0]).attributes.get('mp_cur',0)
        if t=='GET_ABILITY_BY_AID':
            unit,category,aid=[self.ev(x) for x in args]
            return self.w.handles.get((unit.name,aid)) if unit.card_categories.get(aid)==category else None
        return super().ev(node)
    def cond(self,node):
        if node['condition_type']=='ABILITY_COMPARE':
            x,op,y=[self.ev(n) for n in node['args_list']];return x==y if op=='==' else x!=y
        return super().cond(node)
    def run(self,actions):
        for node in actions:
            if isinstance(node,int):super().run([node]);continue
            t=node['action_type'];args=node['args_list']
            if t=='SET_ENTITY_KV':
                entity,key,value=[self.ev(x) for x in args]
                if isinstance(entity,tuple):
                    defaults={k:v['value'] for k,v in read(f'editor_table/abilityall/{entity[1]}.json')['kv'].items()}
                    self.w.ability_kv.setdefault((entity[0].name,entity[1]),defaults)[key]=value
                elif isinstance(entity,int):self.w.player_kv.setdefault(entity,{})[key]=value
                else:entity.kv[key]=value
            elif t=='SET_ABILITY_LEVEL':
                a,level=[self.ev(x) for x in args];self.w.levels[a[0].name,a[1]]=level
                vm=VM(self.w,a[0],a[1],False);vm.fire('ABILITY_LEVEL_CHANGED')
            elif t=='ADD_CUR_MP':
                unit,amount=[self.ev(x) for x in args]
                unit.attributes['mp_cur']=min(self.w.attr(unit,'mp_max'),max(0,unit.attributes.get('mp_cur',0)+amount))
            else:super().run([node])
    def fire(self,event,eid=None,params=None):
        if event!='SPECIAL_UNIT_EVENT':return super().fire(event,eid,params)
        # Only the owner whose kill fired receives its native special event.
        for tid,tr in self.obj['trigger_dict'].items():
            if int(tid) not in self.registered:continue
            ev=tr['event'][0]
            if ev['event_type']==event and ev['args_list'][1]['args_list']==['ET_KILL_UNIT']:
                if all(self.cond(c) for c in tr['condition']):self.run(tr['action'])

class World(v.World):
    def __init__(self):
        super().__init__();self.wave=0;self.phase=1;self.levels={};self.money={};self.player_kv={}
        self.ability_kv={};self.random=[];self.random_ranges=[];self.merges=[];self.carriers={}
    def card(self,u,aid,add=True,before_lose=False):
        self.carriers[u.player]=u;self.pools.setdefault(u.player,{})
        if add:
            self.serial+=1;self.handles.setdefault((u.name,aid),(u,aid,self.serial))
            u.cards.add(aid);u.card_categories[aid]=3 if aid in s.RESULTS or aid==s.EX else 2
            vm=VM(self,u,aid,False);vm.fire('ABILITY_OBTAIN');self.prewrite_snapshots.append(dict(u.kv))
            index=max(self.pools[u.player],default=0)+1
            self.pools[u.player][index]={'技能':self.handles[u.name,aid],'归属单位':u,'技能类型':aid,'是否已抽取':True,'是否合成':aid in s.RESULTS or aid==s.EX}
        else:
            vm=VM(self,u,aid,False)
            if before_lose:vm.fire('ABILITY_LOSE')
            u.cards.remove(aid);self.handles.pop((u.name,aid),None)
            if not before_lose:vm.fire('ABILITY_LOSE')
        VM(self,u,aid,False).execute(s.FIDS[14],[u])
    def tick(self):
        for oid in (s.CONTROL,s.ARMY,s.b.CONTROL,s.b.ARMY):
            for vm in list(self.buffs.values()):
                if vm.oid==oid:vm.fire('MODIFIER_CYCLE_TRIGGER')
    def contribution(self,u,key,mode='ATTR_BASE'):
        vm=self.buffs.get((u.name,s.ARMY));return vm.contributions.get((key,mode),0) if vm else 0
    def start(self,wave):
        self.wave=wave;self.phase=2;self.emit(s.PHASE,阶段编号=2)
    def kill(self,u):
        vm=self.buffs.get((u.name,s.ARMY))
        if vm:vm.fire('SPECIAL_UNIT_EVENT')

@contextlib.contextmanager
def runtime():
    oldvm,oldread,vr,vfuncs,vvm=old.VM,old.read,v.read,v.FUNCS,v.VM
    old.VM=VM;old.read=read;v.read=read;v.FUNCS={**vfuncs,**FUNCS};v.VM=VM
    try:yield
    finally:old.VM=oldvm;old.read=oldread;v.read=vr;v.FUNCS=vfuncs;v.VM=vvm;EXTRA.clear()

def world():
    w=World();c=Unit('carrier');front=Unit('front',tags={'蜀国','骑兵'},kv={'归属阵型编号':1})
    rear=Unit('rear',tags={'魏国'},kv={'归属阵型编号':7})
    cavalry=Unit('cavalry',tags={'骑兵','枪兵'},kv={'所属英雄':front})
    infantry=Unit('infantry',tags={'刀兵'},kv={'所属英雄':rear})
    front.kv['带领小队']=[cavalry];rear.kv['带领小队']=[infantry]
    w.units=[c,front,rear,cavalry,infantry];w.captains[1]=[front,rear]
    return w,c,front,rear,cavalry,infantry

class ShuCases(unittest.TestCase):
    def setUp(self):self.ctx=runtime();self.ctx.__enter__()
    def tearDown(self):self.ctx.__exit__(None,None,None)
    def test_33_cards_3_events_and_valid_level_owner(self):
        for aid in SPECS:
            doc=read(f'ability/{aid}.json');events={x['event'][0]['event_type']:x for x in doc['trigger_dict'].values()}
            self.assertEqual(set(events),{'ABILITY_OBTAIN','ABILITY_LEVEL_CHANGED','ABILITY_LOSE'})
            self.assertFalse(any(n.get('sub_type')=='ABILITY_OWNER' for n in s.b.walk(events['ABILITY_LEVEL_CHANGED'])))
    def test_every_workbook_basic_field_reaches_a_contribution(self):
        mapping={'力量':('strength','ATTR_BASE'),'敏捷':('agility','ATTR_BASE'),'智力':('intelligence','ATTR_BASE'),
          '生命值':('hp_max','ATTR_BASE'),'攻击力':('attack_phy','ATTR_BASE'),'速度':('ori_speed','ATTR_ALL_RATIO'),
          '攻速':('attack_speed','ATTR_BASE'),'暴击率':('critical_chance','ATTR_BASE'),'暴击伤害':('critical_dmg','ATTR_BASE'),
          '技能伤害':(s.b.SKILL_DAMAGE,'ATTR_BASE'),'所有伤害':('extra_dmg','ATTR_BASE')}
        checked=0
        for aid,spec in SPECS.items():
            if not spec.get('row'):continue
            w,c,f,rear,_,_=world();w.card(c,int(aid));w.tick()
            for raw in spec['base']:
                if raw in (None,'','-') or raw.startswith('金币'):continue
                name,number=raw.split('+');amount=float(number.rstrip('%'));checked+=1
                fields=[(x,'ATTR_ALL_RATIO' if name=='全属性%' else 'ATTR_BASE') for x in ('strength','agility','intelligence')] if name.startswith('全属性') else [mapping[name]]
                for key,mode in fields:self.assertEqual(w.contribution(rear,key,mode),amount,(aid,raw,key))
        self.assertEqual(checked,60)
    def test_all_results_and_terminal_union(self):
        w,c,f,rear,cav,inf=world()
        for aid in s.RESULTS:w.card(c,aid)
        w.card(c,s.EX);w.tick()
        self.assertEqual(w.contribution(f,'extra_dmg'),15+10+20+30+25+25+60+30+15+20+50)
        self.assertEqual(w.contribution(cav,'extra_dmg'),w.contribution(f,'extra_dmg'))
        self.assertEqual(w.contribution(rear,'extra_dmg'),25)
        self.assertEqual(w.contribution(inf,'extra_dmg'),25)
        self.assertEqual(w.contribution(f,'critical_chance'),30)
        self.assertEqual(w.contribution(f,'critical_dmg'),100)
    def test_repeated_refresh_and_life_ratio(self):
        w,c,f,*_=world();f.hp=400;w.card(c,s.EX);w.tick();before=dict(w.buffs[f.name,s.ARMY].contributions)
        for _ in range(4):VM(w,c,s.EX,False).fire('ABILITY_LEVEL_CHANGED');w.tick()
        self.assertEqual(before,w.buffs[f.name,s.ARMY].contributions)
        self.assertAlmostEqual(f.hp/w.attr(f,'hp_max'),.4)
        w.card(c,s.EX,False,True);w.tick()
        self.assertAlmostEqual(f.hp/w.attr(f,'hp_max'),.4)
    def test_first_gain_precedes_pool_record(self):
        w,c,f,*_=world();w.card(c,134280178)
        self.assertNotIn(s.PREFIX+'属性_strength_ATTR_BASE',w.prewrite_snapshots[0])
        self.assertEqual(w.contribution(f,'strength'),15)
    def test_sparse_duplicate_wrong_owner_and_stale_records(self):
        w,c,f,*_=world();w.card(c,134280178);pool=w.pools[1]
        pool[42]={};pool[50]={'技能':None};pool[60]=dict(pool[1])
        other=Unit('other');handle=(other,134280178,900);w.handles[other.name,134280178]=handle
        pool[70]={'技能':handle,'归属单位':other};w.tick()
        self.assertEqual(w.contribution(f,'strength'),15)
        w.card(c,134280178,False,True);w.tick();self.assertFalse(w.has(c,s.CONTROL))
    def test_runtime_rules_initialized_once(self):
        w,c,*_=world();w.card(c,134280178);rules=c.kv[s.RULES];calls=w.function_calls[s.FIDS[13]]
        w.card(c,134273774)
        for _ in range(3):w.tick()
        self.assertIs(c.kv[s.RULES],rules);self.assertEqual(w.function_calls[s.FIDS[13]],calls)
    def test_currency_once_per_player_and_type(self):
        w,c,*_=world();w.card(c,134222904);w.card(c,134230426)
        self.assertEqual(w.money[1],1500)
        w.card(c,134222904,False);w.card(c,134222904)
        self.assertEqual(w.money[1],1500)
        other=Unit('other',player=2);w.card(other,134222904);self.assertEqual(w.money[2],500)
    def test_kill_mana_cap_and_growth_individual(self):
        w,c,f,_,cav,inf=world();w.card(c,134222904);w.card(c,134282587)
        for u in (f,cav,inf):u.attributes.update(mp_max=1000,mp_cur=950)
        w.kill(cav);w.kill(cav);w.kill(cav)
        self.assertEqual(cav.attributes['mp_cur'],1000)
        self.assertEqual(cav.attributes['attack_phy'],3)
        self.assertEqual(f.attributes['mp_cur'],950)
        self.assertNotIn('attack_phy',f.attributes)
        w.start(1);w.tick();self.assertEqual(cav.attributes['attack_phy'],3)
        w.card(c,134282587,False,True);w.kill(cav);self.assertEqual(cav.attributes['attack_phy'],3)
        w.kill(f);self.assertEqual(f.attributes['mp_cur'],970)
    def test_kill_with_zero_mana_and_after_loss(self):
        w,c,f,*_=world();w.card(c,134222904);f.attributes.update(mp_max=0,mp_cur=0)
        w.kill(f);self.assertEqual(f.attributes['mp_cur'],0)
        w.card(c,134222904,False);w.tick();w.kill(f);self.assertEqual(f.attributes['mp_cur'],0)
    def test_wave_reputation_coexists_and_duplicate_event_ignored(self):
        w,c,*_=world();w.card(c,s.BASE);w.card(c,s.LIUBEI);w.card(c,134230426)
        w.ability_kv[c.name,s.BASE]['声望累计']=20;w.random=[17];w.start(1)
        self.assertEqual(w.ability_kv[c.name,s.BASE]['声望累计'],67)
        self.assertEqual(w.levels[c.name,s.BASE],3)
        w.start(1);self.assertEqual(w.ability_kv[c.name,s.BASE]['声望累计'],67)
        w.random=[10];w.start(2);self.assertEqual(w.ability_kv[c.name,s.BASE]['声望累计'],107)
    def test_zhuge_probability_and_cap(self):
        w,c,*_=world();w.card(c,s.BASE);w.card(c,134223259)
        w.random=[11];w.start(1);self.assertEqual(w.levels.get((c.name,s.BASE),1),1)
        w.random=[10];w.start(2);self.assertEqual(w.levels[c.name,s.BASE],2)
        w.levels[c.name,s.BASE]=5;w.random=[];w.start(3);self.assertEqual(w.levels[c.name,s.BASE],5)
        self.assertEqual(w.random,[])
    def test_wave_snapshot_deduplicates(self):
        w,c,*_=world();w.card(c,s.BASE);w.card(c,s.LIUBEI);w.pools[1][100]=dict(w.pools[1][2]);w.start(1)
        self.assertEqual(w.ability_kv[c.name,s.BASE]['声望累计'],30)
    def test_late_control_does_not_retroactively_reward(self):
        w,c,*_=world();w.wave=5;w.phase=2;w.card(c,s.BASE);w.card(c,s.LIUBEI);w.start(5)
        self.assertEqual(w.ability_kv[c.name,s.BASE]['声望累计'],0)
        w.start(6);self.assertEqual(w.ability_kv[c.name,s.BASE]['声望累计'],30)
    def test_terminal_requires_six_results_and_level5(self):
        w,c,*_=world();w.card(c,s.BASE)
        rows=read('tables/军令卡牌技能表.json')['table_data']['data'][2:]
        index=next(int(row[0]) for row in rows if row[1]==s.EX)
        w.pools[1][index]={'技能类型':s.EX,'是否合成':True}
        for aid in s.RESULTS:w.card(c,aid)
        self.assertNotIn(s.EX,c.cards);w.levels[c.name,s.BASE]=5
        VM(w,c,s.BASE,False).fire('ABILITY_LEVEL_CHANGED');w.tick()
        self.assertIn(s.EX,c.cards);self.assertEqual(w.merges,[(1,index)])
        w.tick();self.assertEqual(len(w.merges),1)
    def test_five_results_cannot_grant_terminal(self):
        w,c,*_=world();w.card(c,s.BASE);w.levels[c.name,s.BASE]=5
        for aid in list(s.RESULTS)[:5]:w.card(c,aid)
        w.tick();self.assertNotIn(s.EX,c.cards)
    def test_new_captain_and_soldier_inherit_benefit(self):
        w,c,f,*_=world();w.card(c,134280178)
        new=Unit('new',kv={'所属英雄':f});f.kv['带领小队'].append(new)
        w.tick();self.assertEqual(w.contribution(new,'strength'),15)
    def test_two_players_and_wu_keep_separate_contributions(self):
        w,c,f,*_=world();w.card(c,134280178)
        other=Unit('other',player=2);cap=Unit('cap2',player=2,tags={'蜀国'},kv={'带领小队':[]});w.captains[2]=[cap]
        w.card(other,134218136);self.assertEqual(w.contribution(cap,'intelligence'),5)
        self.assertEqual(w.contribution(f,'intelligence'),0)
        # Instantiate the reviewed Wu runtime alongside the Shu runtime.
        aid=134263404;w.serial+=1;w.handles[c.name,aid]=(c,aid,w.serial);c.cards.add(aid)
        VM(w,c,aid,False).fire('ABILITY_OBTAIN')
        w.pools[1][100]={'技能':w.handles[c.name,aid],'归属单位':c}
        VM(w,c,aid,False).execute(s.d.FIDS[14],[c]);w.tick()
        self.assertEqual(w.contribution(f,'strength'),15)
        self.assertEqual(w.buffs[f.name,s.b.ARMY].contributions['agility','ATTR_BASE'],5)

class StructureCases(unittest.TestCase):
    def test_table_resource_and_expression_have_distinct_encodings(self):
        runtime=s.b.n(100011,'VARIABLE',s.r.tp(['TABLE','持卡快照','local']))
        self.assertEqual(s.r.table(runtime),runtime)
        resource='12345678-1234-5678-1234-567812345678'
        self.assertEqual(s.r.table(resource),s.b.lit(100011,resource))
        with self.assertRaises(TypeError):s.r.table(s.b.f(1))
    def test_reject_bad_literal_instead_of_silently_evaluating_it(self):
        with runtime():
            w,c,*_=world();vm=VM(w,c,s.BASE,False)
            bad=s.b.n(100011,1,s.b.n(100011,'VARIABLE',s.r.tp(['TABLE','持卡快照','local'])))
            with self.assertRaisesRegex(AssertionError,'wrapped as a table constant'):vm.ev(bad)
    def test_no_runtime_table_expression_is_wrapped_as_resource(self):
        for rel,doc in DATA.items():
            for node in s.b.walk(doc):
                if node.get('arg_type')==100011 and node.get('sub_type')==1:
                    self.assertFalse(any(isinstance(x,dict) for x in node.get('args_list',[])),rel)
    def test_existing_reputation_actions_preserved(self):
        for aid in SPECS:
            old_doc=original(f'ability/{aid}.json')
            if old_doc is None:continue
            before=next(iter(old_doc['trigger_dict'].values()))['action']
            after=next(iter(read(f'ability/{aid}.json')['trigger_dict'].values()))['action'][:len(before)]
            strip=lambda x:{k:v for k,v in x.items() if k!='element_id'}
            self.assertEqual([strip(x) for x in before],[strip(x) for x in after])
    def test_route_complete_and_only_base_initially_unlocked(self):
        for rel in ['tables/军令卡牌技能表.json','tables/蜀国temp.json']:
            rows=read(rel)['table_data']['data'][2:];byid={row[1]:row for row in rows}
            self.assertEqual(len(byid),33);self.assertEqual(byid[134283217][9],'桃园结义')
            self.assertEqual(sum(row[5]=='false' for row in rows if row[6]=='桃园结义'),3)
            self.assertEqual(sum(row[5]=='true' for row in rows if row[6]=='桃园结义'),1)
            self.assertEqual([row[1] for row in rows if row[7]=='true'],[s.BASE])
    def test_shared_entry_only_appends_own_refresh(self):
        for rel,doc in DATA.items():
            if rel.endswith(('3选1军略卡牌处理.json','军略3选1-处理合成的新卡牌.json')):
                before=original(rel);calls=[x for x in doc['action'] if x.get('action_type')=='CALL_TRIGGER_FUNC' and x['args_list'][0]['sub_type']==s.FIDS[14]]
                self.assertEqual(len(calls),1);self.assertEqual({**doc,'action':[x for x in doc['action'] if x not in calls]},before)
    def test_ids_links_native_nodes_and_no_wu_residue(self):
        live_ids={doc.get('trigger_id') for p in (s.MAP/'global_trigger').rglob('*.json') if p.relative_to(s.MAP).as_posix() not in DATA and isinstance(doc:=json.loads(p.read_text('utf8')),dict)}
        for rel,doc in DATA.items():
            if not rel.startswith((s.FOLDER,'ability/','modifier/')):continue
            if not isinstance(doc,dict):continue
            if doc.get('is_func'):self.assertNotIn(doc['trigger_id'],live_ids)
            seen=set()
            for node in s.b.walk(doc):
                if 'element_id' in node:self.assertNotIn(node['element_id'],seen);seen.add(node['element_id'])
                if node.get('arg_type')==100177:self.assertIn(node['sub_type'],set(FUNCS)|{ATTRFID,s.MERGE,'36487c1f2b4f11f0b8029792acb0a9c5'})
            text=json.dumps(doc,ensure_ascii=False)
            self.assertNotIn('吴国',text)
            for bad in ('FLOAT_TO_INT','GET_ABILITY_ATTR','"军略阵营", "吴国"'):self.assertNotIn(bad,text)

if __name__=='__main__':unittest.main(verbosity=2)
