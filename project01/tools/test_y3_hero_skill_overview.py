"""Execute UI display ECA with live-shaped tables and strict object lookup.

No combat or persistent save mutations are simulated as successful here.
"""
import copy,json,sys,unittest,os
from collections import Counter
import y3_hero_skill_overview as m
from safezone_ui_fixtures import stage,reference,result_path
if not os.environ.get('Y3_HERO_OVERVIEW_STAGE'):
    m.WORK=stage('skills')
import test_y3_hero_detail_restore as prior
b=m.b;b.WORK=m.WORK;prior.h.WORK=m.WORK;b.PROJECT=reference();m.PROJECT=b.PROJECT

class Offline(prior.Offline):
    def __init__(self):
        super().__init__();d=b.load(m.WORK/'candidate'/m.FN);self.docs[m.FID]=d
        self.language=b.load(m.WORK/'before'/m.LANG)
        self.abilities={};self.modifiers={}
        for p in(m.WORK/'before'/b.MAP/'editor_table/abilityall').glob('*.json'):self.abilities[int(p.stem)]=b.load(p)
        for p in(m.WORK/'before'/b.MAP/'editor_table/modifierall').glob('*.json'):self.modifiers[int(p.stem)]=b.load(p)
        for file,tid,stringkey in [(m.SKILLS,m.SKILL_TID,True),(m.CORES,m.CORE_TID,False)]:
            data=b.load(m.WORK/'before'/file)['table_data']['data']
            self.cfg[tid]={(str(r[0])if stringkey else int(r[0])):dict(zip(data[0],r))for r in data[2:]if r and r[0]}
    def value(self,x,env):
        if isinstance(x,dict)and'arg_type'in x:
            sub=x['sub_type'];args=x['args_list'];v=lambda i:self.value(args[i],env)
            if sub in ['NONE_ABILITY_KEY','NONE_MODIFIER_KEY']:return 0
            if sub=='ITER_TABLE_KEY_STR':return env['_row']
            if sub in ['GET_ABILITY_NAME_TABLE_VAR_ND','GET_MODIFIER_TABLE_VAR_ND','GET_UNIT_NAME_TABLE_VAR_ND']and v(0)in [m.SKILL_TID,m.CORE_TID]:
                return int(self.cfg[v(0)][v(1)][v(2)]or 0)
            if sub=='GET_ABILITY_CONF_STR_ATTR':
                obj=self.abilities[v(0)];return self.language.get(str(obj[v(1)]),str(obj[v(1)]))
            if sub=='GET_ICON_BY_ABILITY_TYPE':return self.abilities[v(0)]['ability_icon']
            if sub=='GET_ICON_BY_BUFF_TYPE':return self.modifiers[v(0)]['modifier_icon']
            if sub in ['GET_NAME_OF_MODIFIER_KEY','GET_DES_ID_BY_MODIFIER_TYPE']:
                obj=self.modifiers[v(0)];field='name'if sub=='GET_NAME_OF_MODIFIER_KEY'else'description'
                return self.language.get(str(obj[field]),str(obj[field]))
        return super().value(x,env)
    def condition(self,x,env):
        if x['condition_type']in ['UNIT_CLASS_COMPARE','ABILITY_COMPARE']:
            a=[self.value(z,env)for z in x['args_list']];return a[0]==a[2]if a[1]=='=='else a[0]!=a[2]
        if x['condition_type']=='OR':return any(self.condition(c,env)for c in x['args_list'][0]['args_list'])
        return super().condition(x,env)
    def overview(self,player=1,mode=0):return self.func(m.FID,[player,mode])
    def setup_hero(self,row,star=6,unlocked=True):
        self.roster(ids=(row,));self.saves[(1,16,row)].update(当前升星进度=star,是否解锁=unlocked)
        self.call(b.NAMES[0],1,row)
    def expected(self,row):
        unit=int(self.cfg[b.TABLE][row]['单位类型']);r=next(r for r in self.cfg[m.SKILL_TID].values()if int(r['单位类型'])==unit)
        skills=[int(r['技能'+str(k)])for k in m.SLOTS]
        cores=[r for r in self.cfg[m.CORE_TID].values()if any(int(r.get('关联技能'+str(i),0)or 0)in skills for i in [1,2,3])]
        return skills,cores

class Flow(unittest.TestCase):
    def setUp(self):self.e=Offline()
    def test_all_26_heroes_show_six_correct_skills_and_core(self):
        self.assertEqual(len(self.e.cfg[b.TABLE]),26)
        for row in self.e.cfg[b.TABLE]:
            e=Offline();e.setup_hero(row);skills,cores=e.expected(row)
            self.assertEqual(len(set(skills)),6);self.assertEqual(len(cores),1)
            for level,sid in enumerate(skills,1):
                self.assertEqual(e.images[(1,b.uid(f'hero/v2/skill-icon/{level}'))],e.abilities[sid]['ability_icon'])
                self.assertEqual(e.labels[(1,b.uid(f'hero/v2/skill-name/{level}'))],e.language[str(e.abilities[sid]['name'])])
                self.assertEqual(e.labels[(1,b.uid(f'hero/v2/skill-state/{level}'))],f'{level}星已解锁')
            buff=int(cores[0]['能力循环机制BUFF'])
            self.assertEqual(e.labels[(1,b.uid('hero/v2/core-name'))],'核心 · '+e.language[str(e.modifiers[buff]['name'])])
    def test_each_star_threshold_and_locked_hero(self):
        for star in [0,1,2,3,4,5,6,11]:
            e=Offline();e.setup_hero(5,star)
            for level in range(1,7):self.assertEqual(e.labels[(1,b.uid(f'hero/v2/skill-state/{level}'))],f'{level}星'+('已解锁'if star>=level else'未解锁'))
        self.e.setup_hero(5,11,False)
        for level in range(1,7):self.assertIn('未解锁',self.e.labels[(1,b.uid(f'hero/v2/skill-state/{level}'))])
    def test_all_seven_clicks_show_correct_live_detail(self):
        self.e.setup_hero(5,1);skills,cores=self.e.expected(5)
        for level,sid in enumerate(skills,1):
            self.e.click('hero/v2/skill/'+str(level))
            self.assertTrue(self.e.visibility[(1,m.h.POPUP)]);self.assertTrue(self.e.visibility[(1,b.uid(m.EXTRA))])
            self.assertEqual(self.e.labels[(1,b.uid('hero/v2/detail-description'))],self.e.language[str(self.e.abilities[sid]['description'])])
            self.assertEqual(self.e.labels[(1,b.uid('hero/v2/detail-name'))],self.e.language[str(self.e.abilities[sid]['name'])])
            self.assertIn('可预览'if level>1 else'已解锁',self.e.labels[(1,b.uid('hero/v2/detail-state'))])
        self.e.click('hero/v2/core');buff=int(cores[0]['能力循环机制BUFF'])
        self.assertEqual(self.e.labels[(1,b.uid('hero/v2/detail-description'))],self.e.language[str(self.e.modifiers[buff]['description'])])
        self.assertIn('可预览',self.e.labels[(1,b.uid('hero/v2/detail-state'))])
    def test_skill_selection_reloads_current_configuration(self):
        self.e.setup_hero(5);skills,_=self.e.expected(5);sid=skills[0]
        self.e.language[str(self.e.abilities[sid]['description'])]='实时更新后的完整说明'
        self.e.click('hero/v2/skill/1');self.assertEqual(self.e.labels[(1,b.uid('hero/v2/detail-description'))],'实时更新后的完整说明')
    def test_switching_heroes_and_support_clears_stale_explanation(self):
        self.e.roster(ids=(1,5));self.e.call(b.NAMES[0],1,5);self.e.click('hero/v2/core')
        self.e.click('hero/support-entry');self.assertFalse(self.e.visibility[(1,b.uid(m.EXTRA))])
        self.e.click('hero/v2/core');self.e.call(b.NAMES[0],1,1)
        self.assertFalse(self.e.visibility[(1,m.h.POPUP)]);self.assertFalse(self.e.visibility[(1,b.uid(m.EXTRA))])
    def test_normal_attack_and_close_still_reachable(self):
        self.e.setup_hero(5);self.e.click('hero/v2/core');self.e.click('hero/skill-row/3')
        self.assertFalse(self.e.visibility[(1,b.uid(m.EXTRA))])
        self.assertTrue(self.e.visibility[(1,'d9714db5-7101-4050-9581-25b730272654')])
        self.e.click('hero/dialog-close');self.assertFalse(self.e.visibility[(1,m.h.POPUP)])
    def test_missing_core_and_empty_slots_use_safe_fallback(self):
        self.e.setup_hero(5);r=self.e.cfg[m.SKILL_TID]['赵云']
        for key in [1,2,3,5,6,7]:r['技能'+str(key)]=m.EMPTY
        self.e.overview(mode=7);self.assertEqual(self.e.labels[(1,b.uid('hero/v2/detail-state'))],'暂无配置')
        self.e.overview(mode=1);self.assertEqual(self.e.labels[(1,b.uid('hero/v2/detail-name'))],'暂无配置')
    def test_no_selected_hero_does_not_read_save(self):self.e.overview(mode=7);self.assertFalse(self.e.labels)
    def test_preview_does_not_change_save_or_forward_gameplay(self):
        self.e.setup_hero(5,1);saved=copy.deepcopy(self.e.saves)
        for i in range(1,8):self.e.overview(mode=i)
        self.assertEqual(self.e.saves,saved);self.assertFalse(self.e.events)
    def test_original_upgrade_shortage_and_success_boundary(self):
        self.e.setup_hero(5);self.e.call(b.NAMES[1],1,1);self.assertFalse(self.e.events)
        self.e.saves[(1,16,5)]['当前伙伴素材额度']=3;self.e.call(b.NAMES[1],1,1)
        self.assertEqual(self.e.events[-1],(1,'1/hero5/伙伴元素.升星bt','upgradePartner'))

class Structure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.after={p:b.load(m.WORK/'candidate'/p)for p in m.OUTPUTS};cls.before={p:b.load(m.WORK/'before'/p)for p in m.OUTPUTS if p!=m.FN}
    def test_portrait_area_and_square_icons(self):
        d=self.after[b.UI];self.assertEqual(b.find_uid(d,b.uid('hero/portrait-mask'))['size']['items'],[300,420])
        for level in range(1,7):self.assertEqual(b.find_uid(d,b.uid(f'hero/v2/skill-icon/{level}'))['size']['items'],[54,54])
        self.assertEqual(b.find_uid(d,b.uid('hero/portrait')).get('anchor',b.tup(.5,.5))['items'],[.5,.5])
    def test_existing_components_and_layout_outside_detail_preserved(self):
        before={n['uid']:n for n in b.walk(self.before[b.UI])if'uid'in n};after={n['uid']:n for n in b.walk(self.after[b.UI])if'uid'in n}
        self.assertTrue(before.keys()<=after.keys());self.assertEqual(len(after),len([n for n in b.walk(self.after[b.UI])if'uid'in n]))
        for key in [b.GRID,b.s.PAGE_IDS[2],b.uid('hero/list-panel'),'7da52980-11af-4acf-ae4d-6f338b1eb7ba']:self.assertEqual(before[key],after[key])
        self.assertTrue(after[b.uid('hero/skill-row/3')].get('visible',True))
    def test_original_business_handlers_and_unrelated_ui_eca_unchanged(self):
        allowed={str(x)for x in [b.TID+121,b.TID+122,b.TID+123,m.h.NTID+2]}
        for sid,sub in self.before[b.OLD]['sub_trigger'].items():
            if sid not in allowed:self.assertEqual(sub,self.after[b.OLD]['sub_trigger'][sid],sid)
        original=self.before[b.FI];after=self.after[b.FI]
        self.assertEqual({k:v for k,v in after.items()if k!=m.NAME+'.json'},{k:v for k,v in original.items()if k!=m.NAME+'.json'})
    def test_all_new_listeners_registered_and_declared(self):
        ui=self.after[b.UI];events={e['name']for n in b.walk(ui)for e in n.get('event_list',[])if'name'in e}
        root=self.after[b.OLD]
        for i in range(1,8):
            sid=m.BASE+100+i;self.assertIn(sid,root['action']);self.assertIn(m.EVENT+str(i),events)
            self.assertEqual(root['sub_trigger'][str(sid)]['event'][0]['args_list'][0]['args_list'],[m.EVENT+str(i)])
    def test_unique_new_ids_and_no_wrapped_expressions(self):
        for p in [h for h in m.OUTPUTS if'global_trigger'in h and h!=b.FI]:
            before=Counter(n['element_id']for n in b.walk(self.before.get(p,{}))if'element_id'in n)
            counts=Counter(n['element_id']for n in b.walk(self.after[p])if'element_id'in n)
            for key,value in counts.items():self.assertLessEqual(value,max(1,before[key]),(p,key))
            for n in b.walk(self.after[p]):
                if n.get('sub_type')==1 and n.get('arg_type')not in [100021,100022,100030,100028]:
                    self.assertFalse(any(isinstance(x,dict)and'arg_type'in x for x in n.get('args_list',[])))
    def test_new_display_function_has_no_gameplay_or_persistence_writes(self):
        forbidden=['SET_SAVE','SAVE_TABLE','UPLOAD_SAVE','UNIT_ADD_ABILITY','ADD_MODIFIER','TRIGGER_UI_EVENT']
        for n in b.walk(self.after[m.FN]):
            action=n.get('action_type','');self.assertFalse(any(x in str(action)for x in forbidden),action)
    def test_none_resource_types_use_native_expressions(self):
        for n in b.walk(self.after[m.FN]):
            if n.get('arg_type')in [100039,100046]:self.assertFalse(n.get('sub_type')==1 and n.get('args_list')==[0])

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    report=dict(passed=result.wasSuccessful(),tests_run=result.testsRun,errors=len(result.errors),failures=len(result.failures),
        manifest_sha256=b.sha((m.WORK/'manifest.json').read_bytes()),scope='UI ECA and 26-hero metadata coverage; native editor and rendering pending')
    result_path('skills').write_bytes(b.encode(report));sys.exit(0 if result.wasSuccessful()else 1)
