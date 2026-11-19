"""Check frozen restoration inputs and the native event boundary.

This executes UI ECA only; original economy/save handlers and rendering still
need acceptance in the editor/runtime.
"""
import os,sys,copy,json,unittest
from collections import Counter
import y3_hero_detail_restore as h
from safezone_ui_fixtures import stage,reference,result_path
if not os.environ.get('Y3_HERO_REVIEW_STAGE'):
    h.WORK=stage('detail')
os.environ['Y3_INNER_REVIEW_STAGE']=str(h.WORK)
import test_y3_safezone_inner_pages as old
b=h.b;b.WORK=h.WORK;b.PROJECT=reference();h.PROJECT=b.PROJECT

class Offline(old.Offline):
    def func(self,fid,args):
        if fid=='49cfc821b67b11edb8aa00fff84eb1b1':
            self.original_calls.append([fid,args]);return
        return super().func(fid,args)
    def roster(self,*a,**kw):
        super().roster(*a,**kw)
        for key,row in self.saves.items():
            if key[1]==16:row['带领兵种']='刀兵'
    def value(self,x,env):
        if isinstance(x,dict)and x.get('sub_type')=='GET_TEXTURE_KV':
            unit=self.value(x['args_list'][0],env)
            data=b.load(b.PROJECT/b.MAP/'editor_table/editorunit'/f'{unit}.json')
            return data['kv']['头像']['value']
        return super().value(x,env)
    def actions(self,actions,env):
        for x in actions:
            if isinstance(x,dict)and x.get('action_type')=='SET_UI_COMP_FONT_SIZE':
                a=x['args_list'];key=(self.value(a[0],env),self.value(a[1],env))
                assert key[1]in self.nodes;self.sizes[('font',*key)]=self.value(a[2],env)
            else:super().actions([x],env)
    def click(self,key,player=1):
        comp=b.uid(key);events=self.nodes[comp]['event_list']
        self.dispatch(events[0]['name'],player,comp)
    def dispatch(self,name,player=1,comp=None):
        trigger=b.load(h.WORK/'candidate'/b.OLD);matches=[]
        for sid,sub in trigger['sub_trigger'].items():
            if any(e['event_type']=='TRIGGER_COMPONENT_EVENT'and e['args_list'][0]['args_list']==[name]for e in sub['event']):
                matches.append(sid);self.actions(sub['action'],{'_player':player,'_component':comp})
        assert len(matches)==1,(name,matches)

class Flow(old.Flow):
    def setUp(self):self.e=Offline()
    def test_only_one_selection_mark(self):
        self.e.roster();self.e.call(b.NAMES[0],1,1);self.e.call(b.NAMES[0],1,5)
        self.assertFalse(self.e.visibility[(1,'1/hero1/伙伴元素.整行选中框')])
        self.assertTrue(self.e.visibility[(1,'1/hero5/伙伴元素.整行选中框')])
        self.assertFalse(self.e.visibility[(1,'1/hero5/伙伴元素.选中标记')])
    def test_live_identity_material_and_next_stage(self):
        self.e.roster();self.e.saves[(1,16,5)].update(当前升星进度=7,当前伙伴素材额度=13,是否上阵=True)
        self.e.call(b.NAMES[0],1,5)
        labels=self.e.labels
        self.assertEqual(labels[(1,b.uid('roster/state'))],'7星  |  已上阵')
        self.assertEqual(labels[(1,b.uid('hero/upgrade-level'))],'当前 7星  →  下一阶段 8星')
        self.assertEqual(labels[(1,b.uid('roster/material'))],self.e.cfg[b.TABLE][5]['仆从名称']+'材料  13 / 3')
        self.assertEqual(labels[(1,'1/hero5/伙伴元素.列表星级')],'7星')
        unit=int(self.e.cfg[b.TABLE][5]['单位类型']);meta=b.load(b.PROJECT/b.MAP/'editor_table/editorunit'/f'{unit}.json')
        self.assertEqual(self.e.images[(1,b.uid('hero/portrait'))],meta['kv']['头像']['value'])
        geometry=b.load(h.WORK/'manifest.json')['portrait_geometry']
        self.assertEqual(self.e.sizes[(1,b.uid('hero/portrait'))],[170,geometry[str(unit)]])
    def test_each_skill_click_and_close(self):
        self.e.roster();self.e.call(b.NAMES[0],1,5)
        doc=self.e.nodes['e3911e6a-9735-44c6-a3a2-9d33c8a0aeee']
        for i in range(1,4):
            self.e.click('hero/skill-row/'+str(i))
            self.assertTrue(self.e.visibility[(1,h.POPUP)])
            for j,p in enumerate(doc['children'],1):self.assertEqual(self.e.visibility[(1,p['uid'])],i==j)
            self.assertFalse(self.e.visibility[(1,'fd0111ad-1b15-4c77-b75d-04a280b33ecf')])
            self.e.click('hero/dialog-close');self.assertFalse(self.e.visibility[(1,h.POPUP)])
        self.e.click('hero/skill-row/1');self.e.click('hero/dialog-shade')
        self.assertFalse(self.e.visibility[(1,h.POPUP)])
    def test_troop_dialog_and_forward_original_context(self):
        self.e.roster();self.e.call(b.NAMES[0],1,5);self.e.click('hero/support-entry')
        self.assertTrue(self.e.visibility[(1,h.POPUP)])
        self.assertTrue(self.e.visibility[(1,'fd0111ad-1b15-4c77-b75d-04a280b33ecf')])
        for i,name in enumerate(['刀兵','弓兵','枪兵','盾兵','骑兵']):
            self.e.click('hero/troop/'+str(i))
            self.assertEqual(self.e.events[-1],(1,'1/hero5/伙伴元素.兵种.'+name,'选中兵种'))
            self.assertTrue(self.e.visibility[(1,h.POPUP)])
    def test_selection_closes_old_hero_dialog(self):
        self.e.roster();self.e.call(b.NAMES[0],1,5);self.e.click('hero/skill-row/2')
        self.e.call(b.NAMES[0],1,1);self.assertFalse(self.e.visibility[(1,h.POPUP)])
    def test_attribute_font_is_instance_local(self):
        self.e.roster();self.e.instance(1,'单位属性条目','2a546ba7-95ab-4f6c-9eda-ca6cabdb310f','attr1')
        self.e.call(b.NAMES[0],1,5)
        for key in ['属性名称','属性数值']:self.assertEqual(self.e.sizes[('font',1,'1/attr1/单位属性条目.'+key)],24)

class Structure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=b.load(h.WORK/'manifest.json')
        cls.before={p:b.load(h.WORK/'before'/p)for p in h.OUTPUTS}
        cls.after={p:b.load(h.WORK/'candidate'/p)for p in h.OUTPUTS}
    def test_all_existing_identities_and_prefab_paths_remain(self):
        for path in [b.UI,b.ROW]:
            for field in ['uid','prefab_sub_key']:
                previous={n[field]for n in b.walk(self.before[path])if n.get(field)}
                now=[n[field]for n in b.walk(self.after[path])if n.get(field)]
                self.assertTrue(previous<=set(now));self.assertEqual(len(now),len(set(now)))
        def paths(node,prefix=''):
            name=prefix+'.'+node['name']if prefix else node['name']
            return{name}|set().union(*(paths(c,name)for c in node.get('children',[])))
        self.assertTrue(paths(self.before[b.ROW]['data'])<=paths(self.after[b.ROW]['data']))
    def test_native_business_and_unrelated_handlers_unchanged(self):
        before=self.before[b.OLD]['sub_trigger'];after=self.after[b.OLD]['sub_trigger']
        changed={str(b.TID+120+i)for i in range(1,5)}
        for sid,sub in before.items():
            if sid not in changed:self.assertEqual(sub,after[sid],sid)
        for p in [b.HD,b.HR,b.TR,b.TC,b.MAIN,b.SUB,b.GRID_MOVE]:
            if(h.WORK/'candidate'/p).exists():
                # This is the restoration-stage no-change contract. Comparing
                # against today's map would mix in the later high-star fix.
                baseline=h.WORK/'before'/p
                if not baseline.exists():baseline=stage('inner')/'candidate'/p
                def semantics(x):
                    # Native save adds fake_op=[2] to HR action 17 and
                    # reformats JSON; neither changes the business operands.
                    if isinstance(x,dict):return{k:semantics(v)for k,v in x.items()if k!='fake_op'}
                    if isinstance(x,list):return[semantics(v)for v in x]
                    return x
                self.assertEqual(semantics(b.load(h.WORK/'candidate'/p)),semantics(b.load(baseline)),p)
        # Only operation branches 3..7 may be appended; remove them and compare exactly.
        restored=copy.deepcopy(self.after[h.OPERATE])
        oldids={n['element_id']for n in b.walk(self.before[h.OPERATE])if'element_id'in n}
        def trim(obj):
            if isinstance(obj,dict):
                for v in obj.values():trim(v)
            elif isinstance(obj,list):
                obj[:]=[v for v in obj if not(isinstance(v,dict)and'element_id'in v and v['element_id']not in oldids)]
                for v in obj:trim(v)
        trim(restored);self.assertEqual(restored,self.before[h.OPERATE])
    def test_outer_skins_and_troop_subtree_unchanged(self):
        before={n['uid']:n for n in b.walk(self.before[b.UI])if'uid'in n}
        after={n['uid']:n for n in b.walk(self.after[b.UI])if'uid'in n}
        self.assertEqual(before[b.s.PAGE_IDS[2]],after[b.s.PAGE_IDS[2]])
        root_before=b.find_uid(self.before[b.UI],b.s.SAFE_ROOT);root_after=b.find_uid(self.after[b.UI],b.s.SAFE_ROOT)
        new_by_id={n['uid']:n for n in root_after['children']}
        for n in root_before['children']:
            if n['uid']!=b.s.OLD_PAGES:self.assertEqual(n,new_by_id[n['uid']],n['name'])
    def test_new_controls_have_registered_unique_click_events(self):
        d=self.after[b.OLD]
        for i in range(1,8):self.assertIn(h.NTID+i,d['action']);self.assertIn(str(h.NTID+i),d['sub_trigger'])
        names=[]
        for i in range(1,4):
            row=b.find_uid(self.after[b.UI],b.uid('hero/skill-row/'+str(i)))
            self.assertEqual(row['type'],1);self.assertEqual(len(row['event_list']),1)
            self.assertEqual(row['event_list'][0]['type'],30);names.append(row['event_list'][0]['name'])
        self.assertEqual(len(names),len(set(names)))
    def test_no_new_duplicate_element_ids_or_literal_expressions(self):
        for p in [h.SELECT,h.OPERATE,b.OLD,b.ROUTE]:
            oldcounts=Counter(n['element_id']for n in b.walk(self.before[p])if'element_id'in n)
            counts=Counter(n['element_id']for n in b.walk(self.after[p])if'element_id'in n)
            for key,num in counts.items():self.assertLessEqual(num,max(1,oldcounts[key]),(p,key))
            for n in b.walk(self.after[p]):
                if n.get('sub_type')==1 and n.get('arg_type')not in [100021,100022,100030,100028]:
                    self.assertFalse(any(isinstance(a,dict)and'arg_type'in a for a in n.get('args_list',[])),(p,n))
    def test_image_write_targets_keep_native_image_type(self):
        ui={n['uid']:n for n in b.walk(self.after[b.UI])if'uid'in n}
        for p in [h.SELECT,b.HD]:
            d=self.after[p]if p in self.after else b.load(h.WORK/'before'/p)
            for n in b.walk(d):
                if n.get('action_type')=='SET_UI_COMP_IMAGE_NEW':
                    target=n['args_list'][1]
                    if target.get('sub_type')==1 and target['args_list'][0]in ui:self.assertEqual(ui[target['args_list'][0]]['type'],4)
    def test_layout_reference_proportions_and_fit(self):
        doc=self.after[b.UI]
        for key,expected in [('hero/list-panel',[500,660]),('hero/portrait-mask',[170,185])]:
            self.assertEqual(b.find_uid(doc,b.uid(key))['size']['items'],expected)
        self.assertEqual(b.find_uid(doc,b.DETAIL)['size']['items'],[680,660])
        grid=b.find_uid(doc,b.GRID);self.assertEqual(grid.get('layout_type',2),2);self.assertEqual(grid['grid_count']['items'],[0,1])
        self.assertLessEqual(5*106+4*8+8,570)
        for key in ['hero/detail-title','hero/upgrade-title','hero/upgrade-level','hero/material-icon','hero/dialog','hero/recruit-title']:
            self.assertIsNotNone(b.find_uid(doc,b.uid(key)))
        detail=b.find_uid(doc,b.DETAIL)
        self.assertNotIn('技能列表',[n['name']for n in detail['children']]);self.assertNotIn('属性加成',[n['name']for n in detail['children']])
    def test_esc_and_navigation_close_popup(self):
        trigger=self.after[b.OLD]['sub_trigger'][str(h.NTID+1)]
        self.assertEqual(trigger['event'][0]['event_type'],'KEYBOARD_KEY_UP_EVENT')
        self.assertEqual(self.after[b.ROUTE]['action'][0]['args_list'][2],b.u(h.POPUP))
    def test_retired_hover_close_listeners_and_call_are_removed(self):
        close=self.after[b.OLD]['sub_trigger'][str(b.TID+124)]
        self.assertEqual([x['action_type']for x in close['action']],['SET_UI_COMP_VISIBLE'])
        self.assertEqual([e['args_list'][0]['args_list'][0]for e in close['event']],[h.EVENT+'关闭背景',h.EVENT+'关闭按钮'])
        self.assertTrue(close['valid']);self.assertTrue(self.after[b.OLD]['valid'])

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]);result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(passed=result.wasSuccessful(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                manifest_sha256=b.sha((h.WORK/'manifest.json').read_bytes()),scope='UI-only ECA execution and preservation checks; native rendering pending')
    result_path('detail').write_bytes(b.encode(report));sys.exit(0 if result.wasSuccessful()else 1)
