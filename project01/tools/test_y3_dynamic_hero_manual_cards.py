"""Strict registration-body regression; not native card drawing/casting acceptance."""
import copy,gzip,json,sys,unittest
import y3_dynamic_hero_manual_cards as r
import test_y3_main_hud_hero_layout as b
h=r.h
FIXTURE_BYTES=(h.ROOT/'tests/fixtures/y3-main-hud-heroes/dynamic-registration.json.gz').read_bytes()
assert h.sha(FIXTURE_BYTES)=='a069c5368eac33a34940846c850213951db6c050a4f5162209daaefec1903d14','Registration sample changed; inspect provenance first'
FIXTURE=json.loads(gzip.decompress(FIXTURE_BYTES))
BEFORE=FIXTURE['before'];CANDIDATE=FIXTURE['after']
assert r.patched(BEFORE)==CANDIDATE,'Pure patch must reproduce the tested publication'
for rel in [h.HUD,h.TRIG,h.FN1]:b.OUT[rel]=FIXTURE['support'][rel]
b.FUNCTIONS[h.FID1]=b.OUT[h.FN1]

class RegistrationVM(b.VM):
    def expr(self,n):
        s=n.get('sub_type');raw=n.get('args_list',[])
        if s=='FOR_EACH_SELECTED_ABILITY':return self.ability
        if s=='ABILITY_NAME_OF_ABILITY':return self.expr(raw[0]).ability_key
        if s=='GET_TABLE_LENGTH':return len(self.expr(raw[0]))
        if s=='GET_ABILITY_TABLE_VAR_ND':return self.expr(raw[0])[self.expr(raw[1])][self.expr(raw[2])]
        return super().expr(n)
    def actions(self,acts):
        for n in acts:
            if isinstance(n,dict)and n.get('action_type')=='SET_TABLE_VALUE_ND':
                table,row,key,value=[self.expr(x)for x in n['args_list']]
                # Native startup creates an appended row by its first field write.
                # Missing fields on reads still fail; no blanket default values.
                if row not in table:
                    assert row==len(table)+1,'Only contiguous append is modeled'
                    table[row]={}
                table[row][key]=value;continue
            if isinstance(n,dict)and n.get('action_type')=='ITER_ABILITY_DO':
                unit=self.expr(n['args_list'][0]);self.ability=None
                self.assert_slot=n['args_list'][1]['args_list'];assert self.assert_slot==[3]
                for a in unit.skills.values():
                    self.ability=a;self.actions(n['args_list'][2]['args_list'])
            else:super().actions([n])

def entry(u,a,locked=True,drawn=False):
    return {'技能':a,'归属单位':u,'是否已抽取':drawn,'是否上锁':locked,'归属单位名称':u.name,'技能释放类型':2}

def world():
    w=b.World(2)
    for u in w.units:
        for i,a in u.skills.items():a.ability_key=200+i
    u=w.units[0];w.cards[w.p]={i:entry(u,a)for i,a in u.skills.items()}
    return w

def register(w,u,p=None):
    # Execute the actual staged registration block with its real local
    # declarations. Earlier creation/grant actions are outside this test double.
    d=dict(trigger_id=CANDIDATE['trigger_id'],var_data=copy.deepcopy(CANDIDATE['var_data']),
      func_param_list=[h.tuple_('执行玩家',True),h.tuple_('玩家队伍单位',True)],action=[CANDIDATE['action'][-2]])
    RegistrationVM(w).run(d,[p or w.p,u])

class TestDynamicManualCards(unittest.TestCase):
    def test_01_reproduces_missing_dynamic_registration(self):
        def writes(d):return [n for n in h.walk(d)if n.get('action_type')=='SET_TABLE_VALUE_ND'and n['args_list'][2].get('args_list')==['技能']and any(x.get('items')==['TABLE','卡牌技能池-表']for x in h.walk(n['args_list'][0]))]
        self.assertEqual(writes(BEFORE),[])
        self.assertTrue(writes(FIXTURE['support'][h.REBIND]))
        self.assertEqual(len(writes(CANDIDATE)),1)

    def test_02_append_rows_preserves_startup_heroes(self):
        w=world();old={k:dict(v)for k,v in w.cards[w.p].items()};u=w.units[1]
        u.skills[3].ability_key=134255698;register(w,u)
        self.assertEqual(len(w.cards[w.p]),5)
        for k,v in old.items():self.assertEqual(w.cards[w.p][k],v)
        rows=list(w.cards[w.p].values())[3:]
        self.assertEqual([x['技能']for x in rows],[u.skills[1],u.skills[2]])
        for row in rows:self.assertEqual(set(row),{'技能','归属单位','是否已抽取','是否上锁','归属单位名称','技能释放类型'});self.assertTrue(row['是否上锁'])

    def test_03_native_toggle_unlocks_new_hero_rows_only(self):
        w=world();u=w.units[1];register(w,u);w.refresh(u)
        pane=w.visible_panes()[0]
        self.assertTrue(w.emit(h.eventname(2,'自动施法'),w.path(pane,'自动战斗')))
        self.assertFalse(u.kv['自动施法'])
        manual=[v for v in w.cards[w.p].values()if not v['是否上锁']and not v['是否已抽取']and v['技能释放类型']==2]
        self.assertEqual(len(manual),3);self.assertTrue(all(v['归属单位']is u for v in manual))
        self.assertTrue(all(v['是否上锁']for v in w.cards[w.p].values()if v['归属单位']is w.units[0]))
        w.emit(h.eventname(2,'自动施法'),w.path(pane,'自动战斗'))
        self.assertTrue(all(v['是否上锁']for v in w.cards[w.p].values()))

    def test_04_reregister_does_not_reset_draw_or_lock_state(self):
        w=world();u=w.units[1];register(w,u)
        w.cards[w.p][4]['是否已抽取']=True;w.cards[w.p][4]['是否上锁']=False
        before={k:dict(v)for k,v in w.cards[w.p].items()};register(w,u)
        self.assertEqual(w.cards[w.p],before)

    def test_05_same_ability_type_different_instance_is_not_deduplicated(self):
        w=world();register(w,w.units[1]);self.assertEqual(len(w.cards[w.p]),6)
        register(w,w.units[1]);self.assertEqual(len(w.cards[w.p]),6)

    def test_06_removed_or_foreign_hero_cannot_append(self):
        w=world();before={k:dict(v)for k,v in w.cards[w.p].items()}
        u=w.units[1];w.groups[w.p].remove(u);register(w,u);self.assertEqual(w.cards[w.p],before)
        u.owner=w.p2;w.groups[w.p].add(u);register(w,u);self.assertEqual(w.cards[w.p],before)
        u.valid=False;register(w,u);self.assertEqual(w.cards[w.p],before)

    def test_07_initially_manual_hero_is_registered_unlocked(self):
        w=world();u=w.units[1];u.kv['自动施法']=False;register(w,u)
        self.assertTrue(all(not v['是否上锁']for v in list(w.cards[w.p].values())[3:]))

    def test_08_null_or_empty_skill_is_ignored(self):
        w=world();u=w.units[1];u.skills[2]=None;u.skills[3].ability_key=134255698
        register(w,u);self.assertEqual(len(w.cards[w.p]),4)

    def test_09_registration_is_after_grants_and_before_hud_refresh(self):
        self.assertEqual(CANDIDATE['action'][:-2],BEFORE['action'][:-1])
        self.assertEqual(CANDIDATE['action'][-1],BEFORE['action'][-1])
        self.assertFalse(any(n.get('sub_type')=='GET_NEW_TABLE'for n in h.walk(CANDIDATE['action'][-2])))

if __name__=='__main__':unittest.main(verbosity=2)
