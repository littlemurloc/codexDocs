"""Reproduce the actual old attribute parsing failure, then execute its fix."""
import copy,json,sys,unittest
from collections import Counter
import y3_hero_attribute_display_guard as g
from safezone_ui_fixtures import stage,reference,result_path
g.WORK=stage('attributes')
import test_y3_hero_skill_overview as prior
b=g.b;g.PROJECT=reference();b.PROJECT=g.PROJECT

class Offline(prior.Offline):
    def __init__(self):
        super().__init__();self.original=b.load(g.WORK/'before'/b.HD);self.fixed=b.load(g.WORK/'candidate'/b.HD)
        for path in g.paths():
            doc=b.load(g.WORK/'before'/path)
            if doc.get('tid')in [g.ATTR_TID,g.WEIGHT_TID]:
                rows=doc['table_data']['data'];self.cfg[doc['tid']]={int(r[0]):dict(zip(rows[0],r))for r in rows[2:]if r and r[0]}
    def value(self,x,env):
        if isinstance(x,dict)and'arg_type'in x:
            sub=x['sub_type'];a=x['args_list'];v=lambda i:self.value(a[i],env)
            if x['arg_type']==100003 and sub=='VARIABLE'and a:
                marker=a[0].get('items',[])if isinstance(a[0],dict)else a[0]
                if len(marker)==3 and marker[0]=='STRING'and marker[1]in ['单位属性类型数组-字符','单位属性数值数组-字符']:
                    raise AssertionError('This native scalar STRING local requires subtype 2')
            if sub=='GET_STRING_TABLE_VAR_ND'and v(0)==g.ATTR_TID:return self.cfg[v(0)][int(v(1))].get(v(2),'')
            if sub=='GET_LOOP_LIST_INDEX':return env['_list_index']
            if sub==2 and len(a)==2 and isinstance(a[0],dict)and a[0].get('items',[None])[0]=='STRING':return env[a[0]['items'][1]][v(1)-1]
            if sub=='STR_TO_FLOAT':return float(v(0))
            if sub=='GET_UNIT_WRITE_ATTRIBUTE_TABLE_VAR_ND':return self.cfg[g.WEIGHT_TID][int(v(1))][v(2)]
            if sub=='CREATE_UI_PREFAB_INSTANCE'and v(1)=='4a1b6433-ff35-486b-826b-17399ceb7154':
                self.created+=1;ins,_=self.instance(v(0),'单位属性条目',v(2),'attribute'+str(self.created));return ins
            if sub=='GET_UNIT_ATTR_NAME_NEW':return next(r['属性描述']for r in self.cfg[g.WEIGHT_TID].values()if r['属性']==v(0))
            if sub=='FLOAT_TO_STR_NEW':return format(v(0),'.'+str(v(1))+'f')
        return super().value(x,env)
    def actions(self,actions,env):
        for node in actions:
            t=node.get('action_type');a=node.get('args_list',[])
            if t=='SET_VARIABLE_STR_LIST':
                env[a[0]['args_list'][0]['items'][1]]=self.value(a[1],env).split(self.value(a[2],env))
            elif t=='LIST_LOOP':
                key=a[0]['args_list'][0]['items'][1]
                for i in range(1,len(env[key])+1):env['_list_index']=i;self.actions(a[1]['args_list'],env)
            else:super().actions([node],env)
    def condition(self,c,env):
        if c.get('condition_type')=='STRING_COMPARE':
            a=[self.value(x,env)for x in c['args_list']];return a[0]==a[2]if a[1]=='=='else a[0]!=a[2]
        return super().condition(c,env)
    def attributes(self,row,star,original=False):
        doc=self.original if original else self.fixed;env={}
        for members in doc['var_data'][0].values():env.update(copy.deepcopy(members))
        env.update(执行玩家=1,查询伙伴编号=row,伙伴星级=star)
        self.actions([doc['action'][5]],env);return env

class Regression(unittest.TestCase):
    def setUp(self):self.e=Offline()
    def test_original_18_star_reproduces_integer_and_float_failures(self):
        with self.assertRaises(ValueError):self.e.attributes(5,18,original=True)
        node=next(n for n in b.walk(self.e.original)if n.get('element_id')==1574691332000255)
        with self.assertRaises(ValueError):self.e.value(node['args_list'][1],{'单位属性数值数组-字符组':[''],'_list_index':1})
    def test_all_26_heroes_configured_1_to_15_stars_preserve_values(self):
        for row,rec in self.e.cfg[g.ATTR_TID].items():
            for star in range(1,16):
                env=self.e.attributes(row,star)
                self.assertEqual(env['伙伴星级'],star);self.assertEqual(env['属性配置星级'],star)
                self.assertEqual(env['单位属性类型数组-字符'],rec[f'{star}星属性类型数组'])
                self.assertEqual(env['赋值'],float(rec[f'{star}星属性数值数组'].split('-')[-1]))
    def test_above_cap_uses_existing_calculation_tier_without_changing_stars(self):
        for star in [16,18,21,99]:
            env=self.e.attributes(5,star)
            self.assertEqual(env['伙伴星级'],star);self.assertEqual(env['属性配置星级'],15)
            self.assertEqual(env['单位属性数值数组-字符'],self.e.cfg[g.ATTR_TID][5]['15星属性数值数组'])
            self.assertEqual(self.e.labels[(1,g.TITLE)],'主角属性加成（按15星配置）')
    def test_zero_star_has_no_fake_attribute_or_conversion(self):
        self.e.attributes(5,0);self.assertFalse(self.e.children.get((1,'2a546ba7-95ab-4f6c-9eda-ca6cabdb310f')))
    def test_empty_config_does_not_convert_empty_string(self):
        self.e.cfg[g.ATTR_TID][5]['10星属性类型数组']='';self.e.cfg[g.ATTR_TID][5]['10星属性数值数组']=''
        self.e.attributes(5,10);self.assertFalse(self.e.children.get((1,'2a546ba7-95ab-4f6c-9eda-ca6cabdb310f')))
    def test_reselecting_normal_star_resets_high_star_note_and_old_rows(self):
        self.e.attributes(5,18);before=len(self.e.children[(1,'2a546ba7-95ab-4f6c-9eda-ca6cabdb310f')])
        self.assertEqual(before,2)
        self.e.attributes(5,1);self.assertEqual(len(self.e.children[(1,'2a546ba7-95ab-4f6c-9eda-ca6cabdb310f')]),1)
        self.assertEqual(self.e.labels[(1,g.TITLE)],'主角属性加成')
    def test_existing_function_identity_and_other_sections_unchanged(self):
        self.assertEqual(self.e.original['action'][:5],self.e.fixed['action'][:5])
        for field in ['func_id','trigger_id','func_param_list','func_name']:self.assertEqual(self.e.original[field],self.e.fixed[field])
        old=Counter(n['element_id']for n in b.walk(self.e.original)if'element_id'in n)
        new=Counter(n['element_id']for n in b.walk(self.e.fixed)if'element_id'in n)
        self.assertTrue(old.keys()<=new.keys())
        for key,count in new.items():self.assertLessEqual(count,max(1,old[key]))
    def test_single_file_scope_and_no_persistent_writes(self):
        manifest=b.load(g.WORK/'manifest.json');self.assertEqual([f['path']for f in manifest['files']],[b.HD])
        for n in b.walk(self.e.fixed):
            self.assertFalse(any(k in str(n.get('action_type',''))for k in ['SET_SAVE','SAVE_TABLE','UPLOAD_SAVE','UNIT_ADD_ABILITY']))
    def test_guard_reuses_native_string_references_exactly(self):
        old_actions=self.e.original['action'][5]['args_list'][1]['args_list']
        expected=[copy.deepcopy(n['args_list'][1])for n in old_actions if n.get('action_type')=='SET_VARIABLE_STR_LIST']
        guards=[n for n in b.walk(self.e.fixed['action'][5])if n.get('condition_type')=='STRING_COMPARE']
        self.assertEqual([n['args_list'][0]for n in guards],expected)
        self.assertTrue(all(n['args_list'][0]['sub_type']==2 for n in guards))
    def test_strict_model_rejects_previous_failed_string_encoding(self):
        expr=b.ref('STRING','单位属性类型数组-字符')
        with self.assertRaisesRegex(AssertionError,'requires subtype 2'):self.e.value(expr,{'单位属性类型数组-字符':'1-3'})

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    v=dict(passed=result.wasSuccessful(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        manifest_sha256=b.sha((g.WORK/'manifest.json').read_bytes()),scope='actual attribute UI action block; original 18-star failure reproduced; 26x15 configured pairs')
    result_path('attributes').write_bytes(b.encode(v));sys.exit(0 if result.wasSuccessful()else 1)
