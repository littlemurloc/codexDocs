"""Execute generated UI-only ECA strictly; original business handlers remain boundaries.

This is not an engine renderer or a claim that original gameplay was simulated.
"""
import copy,json,sys,unittest,os
from pathlib import Path
from collections import Counter
import y3_safezone_inner_pages as b
from safezone_ui_fixtures import stage,reference,result_path
if os.environ.get('Y3_INNER_REVIEW_STAGE'):b.WORK=Path(os.environ['Y3_INNER_REVIEW_STAGE'])
else:
    b.WORK=stage('inner')
from test_y3_safezone_skin_switch import Offline as Base
b.PROJECT=reference()

class Offline(Base):
    def __init__(self):
        self.ui=b.load(b.WORK/'candidate'/b.UI)
        self.nodes={n['uid']:n for n in b.walk(self.ui)if'uid'in n}
        self.docs={}
        for name in b.NAMES:
            d=b.load(b.WORK/'candidate'/(b.FD+name+'.json'));self.docs[d['func_id']]=d
        self.docs['7406cccc535611f09fb1a3906fbadb58']=b.load(b.WORK/'candidate'/b.TR)
        self.kvs={};self.visibility={};self.labels={};self.images={};self.enabled={};self.fonts={}
        self.events=[];self.detail_calls=[];self.prefabs={};self.children={};self.paths={};self.saves={};self.created=0;self.registered=[];self.sizes={}
        self.costs={};self.parent_eligible={};self.original_calls=[]
        self.cfg={}
        for tid in [b.TABLE,b.TT]:
            path=next(p for p in (b.PROJECT/b.MAP/'tables').glob('*.json')if b.load(p).get('tid')==tid)
            rows=b.load(path)['table_data']['data'];self.cfg[tid]={int(r[0]):dict(zip(rows[0],r))for r in rows[2:]}
    def instance(self,player,name,parent,serial):
        file={'伙伴元素':b.ROW,'兵种养成主项':b.MAIN,'兵种养成子项':b.SUB,'单位属性条目':b.MAP+'ui/prefab/单位属性条目.json'}[name]
        source=b.WORK/'candidate'/file
        doc=b.load(source if source.exists()else b.PROJECT/file);ins=f'{player}/{serial}'
        def add(n,path):
            key=ins+'/'+path;self.nodes[key]=n;self.prefabs[key]=ins;self.paths[(ins,path)]=key
            for c in n.get('children',[]):add(c,path+'.'+c['name'])
            return key
        root=add(doc['data']['children'][0],name)
        self.children.setdefault((player,parent),[]).append(root)
        return ins,root
    def roster(self,player=1,ids=(1,5)):
        for i in ids:
            ins,root=self.instance(player,'伙伴元素',b.GRID,'hero'+str(i));self.kvs[(ins,b.ROWKEY)]=i
            self.saves[(player,16,i)]={'当前伙伴素材额度':2,'当前升星进度':3,'是否解锁':True,'是否上阵':False}
            self.costs[(player,i)]=3
    def troop(self,player=1,idx=1):
        self.kvs[(player,b.TROOP)]=idx
        ins,root=self.instance(player,'兵种养成主项',b.TG,'main'+str(idx));self.kvs[(ins,'父编号')]=idx
        for i in range(1,6):self.saves[(player,17,i)]={'星级状态':i%4,'材料数量':2}
        grid=self.paths[(ins,'兵种养成主项.grid_view_2')]
        for i in [6,7,8]:
            sub,root=self.instance(player,'兵种养成子项',grid,'sub'+str(i));self.kvs[(sub,'子编号')]=i
            self.saves[(player,17,i)]={'材料数量':i-6,'星级状态':i%3};self.costs[(player,i)]=1
        self.parent_eligible[(player,idx)]=False
    def func(self,fid,args):
        if fid=='79b5b580b2e911f09dbd0d58092045fb':self.original_calls.append([fid,args]);return
        if fid=='d7706c52952511f099a6b572c9c66ac5':self.detail_calls.append(args);return
        if fid=='57e36f6b478f11f08b1f9b08b3b6223a':
            player,unit=args;idx=next(i for i,r in self.cfg[b.TABLE].items()if int(r['单位类型'])==int(unit))
            return self.costs[(player,idx)]
        if fid=='c4dbb439535711f08522a3906fbadb58':return self.costs[tuple(args)]
        if fid=='0ade95b0536711f0b00d31fbfffbed02':return self.parent_eligible[tuple(args)]
        if fid=='c6a02ad1532e11f0ab270beb258c5bd0':return self.saves[(args[0],17,args[1])]['星级状态'],134281252
        if fid=='0a2c78c4cf4511f0ab3d5fd1f5d47d62':return '当前效果'+str(args)
        return super().func(fid,args)
    def call(self,name,player,*args):return self.func(b.FIDS.get(name,name),[player,*args])
    def value(self,x,env):
        if isinstance(x,dict)and'arg_type'in x:
            s=x['sub_type'];a=x['args_list']
            v=lambda i:self.value(a[i],env)
            if s=='GET_UI_COMP_PREFAB':
                assert v(1)in self.prefabs;return self.prefabs[v(1)]
            if s=='GET_UI_PREFAB_CHILD_BY_PATH':
                key=(v(0),v(1));assert key in self.paths,key;return self.paths[key]
            if s=='FOR_EACH_UI_COMP':return env['_each']
            if s=='ITER_TABLE_KEY_INT':return env['_row']
            if s=='CREATE_UI_PREFAB_INSTANCE':
                keys={'e4ac6880-5631-47a8-b184-e3c4074036f7':'兵种养成主项','31f5cdaf-871f-4e93-af4f-e195b83bda8b':'兵种养成子项'}
                self.created+=1;ins,root=self.instance(v(0),keys[v(1)],v(2),'created'+str(self.created));return ins
            if s=='CREATE_UI_COMP':
                self.created+=1;key='new/image/'+str(self.created);self.nodes[key]={'name':'image','type':v(2)}
                self.children.setdefault((v(0),v(1)),[]).append(key);return key
            if s=='GET_DES_ID_BY_ITEM_TYPE':return '说明'+str(v(0))
            if s=='INT_PLUS_ONE':return v(0)+1
            if isinstance(s,str)and s.startswith('GET_PLAYER_SAVE_TABLE_VALUE_'):
                assert a[1]['arg_type']==100247
                assert x['op_arg_enable']==[True,False]
                return self.saves[(v(0),v(1),v(2))][self.value(x['op_arg'][0],env)]
            if s in ['GET_UNIT_NAME_TABLE_VAR_ND','GET_ITEM_NAME_TABLE_VAR_ND','GET_INTEGER_TABLE_VAR_ND','GET_STRING_TABLE_VAR_ND']:
                r=self.cfg[v(0)][int(v(1))][v(2)]
                return r if s=='GET_STRING_TABLE_VAR_ND'else int(r)
            if s=='GET_ITEM_CONF_NAME':return '材料'+str(v(0))
            if s=='GET_ICON_BY_ITEM_TYPE':assert x['arg_type']==100115;return 'icon'+str(v(0))
            if s=='GET_ICON_BY_UNIT_TYPE':assert x['arg_type']==100115;return 'icon'+str(v(0))
            if s=='MATH_OPERATION':
                assert v(1)in ['+','-'];return v(0)+v(2)if v(1)=='+'else v(0)-v(2)
            if s in ['57e36f6b478f11f08b1f9b08b3b6223a','c4dbb439535711f08522a3906fbadb58','0ade95b0536711f0b00d31fbfffbed02','0a2c78c4cf4511f0ab3d5fd1f5d47d62']:
                return self.func(s,[self.value(y,env)for y in a])
        return super().value(x,env)
    def actions(self,actions,env):
        for x in actions:
            if isinstance(x,dict)and x.get('enable')is False:continue
            if x.get('action_type')=='STORAGE_BOX':
                self.actions(x['args_list'][1]['args_list'],env)
            elif x.get('action_type')=='ITER_UI_COMP_DO':
                a=x['args_list'];key=(self.value(a[0],env),self.value(a[1],env))
                prior=env.get('_each')
                for comp in list(self.children.get(key,[])):
                    env['_each']=comp;self.actions(a[2]['args_list'],env)
                env['_each']=prior
            elif x.get('action_type')=='SET_UI_BTN_STATUS_STRING':
                a=x['args_list'];assert a[2]['arg_type']==1001563
                self.labels[(self.value(a[0],env),self.value(a[1],env))]=self.value(a[3],env)
            elif x.get('action_type')=='TRAVERSE_TABLE_NEW':
                a=x['args_list'];table=self.value(a[0],env);rows=self.cfg[table]if isinstance(table,str)else table
                previous=env.get('_row')
                for row in sorted(rows):env['_row']=row;self.actions(a[1]['args_list'],env)
                env['_row']=previous
            elif x.get('action_type')=='FOR_INT_DO_ACTION_NEW':
                a=x['args_list'];name=a[0]['args_list'][0]['items'][1]
                for i in range(self.value(a[1],env),self.value(a[2],env)+1):env[name]=i;self.actions(a[3]['args_list'],env)
            elif x.get('action_type')=='SET_UI_COMP_SIZE':
                a=x['args_list'];self.sizes[(self.value(a[0],env),self.value(a[1],env))]=[self.value(z,env)for z in a[2:]]
            elif x.get('action_type')=='CALL_TRIGGER_FUNC'and x['args_list'][0]['sub_type']=='c6a02ad1532e11f0ab270beb258c5bd0':
                a=x['args_list'];ret=self.func(a[0]['sub_type'],[self.value(z,env)for z in a[0]['args_list']])
                for target,value in zip(a[1:],ret):env[target['args_list'][0]['items'][1]]=value
            elif x.get('action_type')=='CREATE_UI_COMP_EVENT_EX_EX':self.registered.append(x)
            elif x.get('action_type')=='DEL_UI_PREFAB_INS':
                ins=self.value(x['args_list'][0],env)
                for key,children in self.children.items():children[:]=[c for c in children if self.prefabs.get(c)!=ins]
            else:super().actions([x],env)
    def condition(self,x,env):
        if x.get('enable')is False:return True
        if x.get('condition_type')=='STRING_COMPARE':
            a=[self.value(v,env)for v in x['args_list']];assert a[1]=='==';return a[0]==a[2]
        return super().condition(x,env)

class Flow(unittest.TestCase):
    def setUp(self):self.e=Offline()
    def test_first_entry_selects_real_first(self):
        self.e.roster(ids=(5,9));self.e.call(b.NAMES[0],1,0)
        self.assertEqual(self.e.kvs[(1,b.SELECT)],5);self.assertEqual(self.e.detail_calls,[[1,5]])
    def test_select_and_upgrade_shortage(self):
        self.e.roster();self.e.call(b.NAMES[0],1,5)
        self.assertFalse(self.e.enabled[(1,b.uid('roster/upgrade'))])
        self.assertIn('还差 1',self.e.labels[(1,b.uid('roster/reason'))])
        self.e.call(b.NAMES[1],1,1);self.assertFalse(self.e.events)
    def test_upgrade_forwards_original_once(self):
        self.e.roster();self.e.saves[(1,16,5)]['当前伙伴素材额度']=3
        self.e.call(b.NAMES[0],1,5);self.e.call(b.NAMES[1],1,1)
        self.assertEqual(self.e.events,[(1,'1/hero5/伙伴元素.升星bt','upgradePartner')])
    def test_state_is_reread_before_forward(self):
        self.e.roster();self.e.saves[(1,16,5)]['当前伙伴素材额度']=3
        self.e.call(b.NAMES[0],1,5);self.e.saves[(1,16,5)]['当前伙伴素材额度']=0
        self.e.call(b.NAMES[1],1,1);self.assertFalse(self.e.events)
    def test_unlock_label_and_deploy_guard(self):
        self.e.roster();self.e.saves[(1,16,5)]['是否解锁']=False
        self.e.call(b.NAMES[0],1,5);self.e.call(b.NAMES[1],1,2)
        self.assertEqual(self.e.labels[(1,b.uid('roster/upgrade'))],'解锁');self.assertFalse(self.e.events)
    def test_deploy_and_undeploy_label(self):
        self.e.roster();self.e.call(b.NAMES[0],1,5);self.e.call(b.NAMES[1],1,2)
        self.assertEqual(self.e.events[-1][2],'joinBattle')
        self.e.saves[(1,16,5)]['是否上阵']=True;self.e.call(b.NAMES[0],1,5)
        self.assertEqual(self.e.labels[(1,b.uid('roster/deploy'))],'下阵修养')
    def test_rebuild_does_not_hold_stale_row(self):
        self.e.roster();self.e.call(b.NAMES[0],1,5)
        self.e.children[(1,b.GRID)]=[];self.e.roster(ids=(1,));self.e.call(b.NAMES[0],1,5)
        self.assertEqual(self.e.kvs[(1,b.SELECT)],1)
    def test_empty_roster_has_no_detail(self):
        self.e.call(b.NAMES[0],1,0);self.assertFalse(self.e.visibility[(1,b.DETAIL)])
        self.assertFalse(self.e.detail_calls)
    def test_players_independent(self):
        self.e.roster(1);self.e.roster(2);self.e.call(b.NAMES[0],1,5);self.e.call(b.NAMES[0],2,1)
        self.assertEqual(self.e.kvs[(1,b.SELECT)],5);self.assertEqual(self.e.kvs[(2,b.SELECT)],1)
    def test_only_one_selection_mark(self):
        self.e.roster();self.e.call(b.NAMES[0],1,1);self.e.call(b.NAMES[0],1,5)
        self.assertFalse(self.e.visibility[(1,'1/hero1/伙伴元素.选中标记')])
        self.assertTrue(self.e.visibility[(1,'1/hero5/伙伴元素.选中标记')])
    def test_troop_main_uses_ability_condition(self):
        self.e.troop();self.e.call(b.NAMES[2],1)
        key=(1,'1/main1/兵种养成主项.培养条件')
        self.assertIn('全部能力',self.e.labels[key]);self.assertEqual(self.e.fonts[key],(*b.RED[:3],100))
        self.e.parent_eligible[(1,1)]=True;self.e.call(b.NAMES[2],1)
        self.assertIn('已满足',self.e.labels[key])
    def test_material_sufficient_and_shortage_colors(self):
        self.e.troop();self.e.call(b.NAMES[2],1)
        for row,color in [(6,b.RED),(7,b.INK),(8,b.INK)]:
            self.assertEqual(self.e.fonts[(1,f'1/sub{row}/兵种养成子项.上部区域.num')],(*color[:3],100))
        self.assertEqual(self.e.labels[(1,'1/sub6/兵种养成子项.上部区域.num')],'0 / 1')
    def test_troop_retains_selected(self):
        self.e.troop(idx=3);self.e.call(b.NAMES[2],1)
        self.assertEqual(self.e.kvs[(1,b.TROOP)],3)
        self.assertTrue(self.e.visibility[(1,b.uid('troop/chosen/3'))])
    def test_attribute_styling_is_local_to_detail_instances(self):
        self.e.roster();self.e.instance(1,'单位属性条目','2a546ba7-95ab-4f6c-9eda-ca6cabdb310f','attr1')
        self.e.call(b.NAMES[0],1,5)
        self.assertFalse(self.e.visibility[(1,'1/attr1/单位属性条目.image_45')])
        self.assertEqual(self.e.fonts[(1,'1/attr1/单位属性条目.属性数值')],(*b.INK[:3],100))
    def test_actual_troop_constructor_creates_three_abilities_for_each_parent(self):
        for selected in range(1,6):
            e=Offline();e.kvs[(1,b.TROOP)]=selected
            for i in e.cfg[b.TT]:
                e.saves[(1,17,i)]={'星级状态':2,'材料数量':0};e.costs[(1,i)]=1
                if i<=5:e.parent_eligible[(1,i)]=False
            e.func('7406cccc535611f09fb1a3906fbadb58',[1])
            parents=e.children[(1,b.TG)];self.assertEqual(len(parents),1)
            ins=e.prefabs[parents[0]];self.assertEqual(e.kvs[(ins,'父编号')],selected)
            grid=e.paths[(ins,'兵种养成主项.grid_view_2')]
            abilities=e.children[(1,grid)];self.assertEqual(len(abilities),3)
            actual=[e.kvs[(e.prefabs[r],'子编号')]for r in abilities]
            expected=[i for i,row in e.cfg[b.TT].items()if row['归属类型']=='子'and int(row['归属父编号'])==selected]
            self.assertEqual(actual,expected)

class Structure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=b.load(b.WORK/'manifest.json');cls.docs={f['path']:b.load(b.WORK/'candidate'/f['path'])for f in cls.m['files']}
        cls.before={k:b.load(b.WORK/'before'/k)for k in b.INPUTS}
    def test_ui_identity_and_original_event_bindings_retained(self):
        for path in [b.UI,b.ROW,b.MAIN,b.SUB]:
            field='uid'if path==b.UI else'prefab_sub_key'
            before={n[field]:n for n in b.walk(self.before[path])if n.get(field)}
            after={n[field]:n for n in b.walk(self.docs[path])if n.get(field)}
            self.assertTrue(before.keys()<=after.keys())
            tooltip_icons={'314fb553-a2d5-4471-8acf-1d23b928cb66','a6db1ade-f977-4c7b-96c8-e7f0059854a5','e9259f2f-cc9a-415f-a519-a89a034401d5'}
            for key in before:
                if key in tooltip_icons:
                    self.assertFalse(before[key].get('event_list'));self.assertEqual([e['type']for e in after[key]['event_list']],[24,25])
                else:self.assertEqual(before[key].get('event_list'),after[key].get('event_list'))
            if path!=b.UI:self.assertEqual(self.before[path]['key'],self.docs[path]['key'])
    def test_all_existing_prefab_paths_retained(self):
        def paths(n,prefix=''):
            here=prefix+'.'+n['name']if prefix else n['name'];return{here}|set().union(*(paths(c,here)for c in n.get('children',[])))
        for file in [b.ROW,b.MAIN,b.SUB]:
            self.assertTrue(paths(self.before[file]['data'])<=paths(self.docs[file]['data']))
    def test_no_expression_inside_constants(self):
        for path,d in self.docs.items():
            if 'global_trigger'not in path:continue
            for n in b.walk(d):
                if n.get('sub_type')==1 and n.get('arg_type')not in[100021,100022,100030,100028]:
                    self.assertFalse(any(isinstance(a,dict)and'arg_type'in a for a in n.get('args_list',[])),(path,n))
    def test_new_function_ids_and_registration(self):
        for n in b.NAMES:self.assertIn(n+'.json',self.docs[b.FI])
        old=self.docs[b.OLD];sids=range(b.TID+101,b.TID+106)
        for sid in [*sids,b.TID+111,b.TID+112,*range(b.TID+121,b.TID+125)]:
            self.assertIn(sid,old['action']);self.assertIn(str(sid),old['sub_trigger'])
    def test_tooltip_uses_native_optional_ability_slot(self):
        for i in range(1,4):
            d=self.docs[b.OLD]['sub_trigger'][str(b.TID+120+i)]
            tooltip=next(z for z in b.walk(d)if z.get('sub_type')=='49cfc821b67b11edb8aa00fff84eb1b1')
            self.assertEqual(len(tooltip['args_list']),2)
            self.assertEqual(tooltip['op_arg_enable'],[False]*5+[True]+[False]*3)
            self.assertEqual(tooltip['op_arg'][5]['arg_type'],100039)
    def test_new_layer_never_writes_archive_or_currency(self):
        for name in b.NAMES:
            for n in b.walk(self.docs[b.FD+name+'.json']):
                if'action_type'in n:self.assertNotIn(n['action_type'],[
                   'SET_SAVE_DATA','ADD_PLAYER_SAVE_TABLE_VALUE','SET_PLAYER_SAVE_TABLE_VALUE','UPLOAD_SAVE_DATA','REMOVE_PLAYER_SAVE_TABLE_VALUE'])
    def test_unrelated_modules_unchanged(self):
        old=self.before[b.UI];new=self.docs[b.UI]
        # Map page and the complete appearance group (including all eight skins).
        for uid in [b.s.PAGE_IDS[0],b.s.uid('appearance')]:
            self.assertEqual(b.find_uid(old,uid),b.find_uid(new,uid))
        protected=[f for f in self.m['files']if any(x in f['path']for x in ['/archive','/tables/','/editor_table/'])]
        self.assertEqual(protected,[])
    def test_original_business_handlers_unchanged(self):
        before={n['trigger_id']:n for n in b.walk(self.before[b.OLD])if'trigger_id'in n}
        after={n['trigger_id']:n for n in b.walk(self.docs[b.OLD])if'trigger_id'in n}
        for tid in [593396238,926528213,1415479820,1549697549,123634214,1348370981,1784578599,1331593768,117711631,1465037587]:
            self.assertEqual(before[tid],after[tid],tid)
    def test_disabled_troop_buttons_remain_visible(self):
        count=0
        for path in [b.TR,b.TC]:
            for n in b.walk(self.docs[path]):
                if n.get('action_type')=='IF_THEN_ELSE':
                    no=n['args_list'][2]['args_list']
                    disables=[a for a in no if isinstance(a,dict)and a.get('action_type')=='SET_UI_COMP_ENABLE'and a['args_list'][2]==b.boolean(False)]
                    for a in disables:
                        count+=1
                        self.assertTrue(any(v.get('action_type')=='SET_UI_COMP_VISIBLE'and v['args_list'][1]==b.boolean(True)and v['args_list'][2]==a['args_list'][1]for v in no))
        self.assertEqual(count,4)
    def test_generated_api_operand_types_match_native(self):
        for name in b.NAMES:
            for n in b.walk(self.docs[b.FD+name+'.json']):
                if isinstance(n.get('sub_type',''),str) and n.get('sub_type','').startswith('GET_PLAYER_SAVE_TABLE_VALUE_'):
                    self.assertEqual(n['args_list'][1]['arg_type'],100247)
                if n.get('action_type')=='SET_UI_BTN_STATUS_STRING':self.assertEqual(n['args_list'][2]['arg_type'],1001563)
    def test_files_match_manifest(self):
        for f in self.m['files']:self.assertEqual(b.sha((b.WORK/'candidate'/f['path']).read_bytes()),f['after'])
    def test_row_selection_does_not_cover_troop_checkboxes(self):
        row=self.docs[b.ROW]['data']['children'][0]
        names=[n['name']for n in row['children']]
        self.assertLess(names.index('详情bt'),names.index('兵种'))
    def test_native_tab_skin_cannot_restore_old_button_images(self):
        page=b.find_uid(self.docs[b.UI],b.s.PAGE_IDS[1])
        self.assertEqual(b.child(page,'副界面切页')['btn_image'],[134273889,134273889])
    def test_name_plate_has_fixed_layout_size(self):
        row=self.docs[b.ROW]['data']['children'][0]
        plate=b.at(row,'信息.name_bg')
        self.assertFalse(plate['size_adaptive']);self.assertEqual(plate['size']['items'],[238,38])
    def test_dynamic_button_label_updates_all_states(self):
        doc=self.docs[b.FD+b.NAMES[0]+'.json'];groups=[]
        for n in b.walk(doc):
            if n.get('action_type')=='STORAGE_BOX':
                acts=n['args_list'][1]['args_list']
                if acts and all(a.get('action_type')=='SET_UI_BTN_STATUS_STRING'for a in acts):
                    groups.append([a['args_list'][2]['args_list'][0]for a in acts])
        self.assertTrue(groups);self.assertTrue(all(g==[1,2,3,4]for g in groups))
    def test_only_safezone_empty_number_paint_is_replaced(self):
        for path in [b.HR,b.GRID_MOVE]:
            a=self.before[path];z=self.docs[path]
            paints=[n for n in b.walk(a)if n.get('action_type')=='SET_UI_COMP_IMAGE_NEW'and n['args_list'][2].get('sub_type')=='b0cc55c0976511f1b56ba932b2c72647']
            self.assertEqual(len(paints),1)
            target=next(n for n in b.walk(z)if n.get('element_id')==paints[0]['element_id'])
            self.assertEqual(target['args_list'][:2],paints[0]['args_list'][:2]);self.assertEqual(target['args_list'][2],b.lit(100115,999))
        movement=copy.deepcopy(self.docs[b.GRID_MOVE]);original=self.before[b.GRID_MOVE]
        for n in b.walk(movement):
            if n.get('action_type')=='SET_UI_COMP_IMAGE_NEW'and n['args_list'][2]==b.lit(100115,999):
                old=next(v for v in b.walk(original)if v.get('element_id')==n['element_id']);n['args_list'][2]=copy.deepcopy(old['args_list'][2])
        self.assertEqual(movement,original)
    def test_nine_small_slot_labels_preserve_slot_ids(self):
        for i in range(1,10):
            node=b.find_uid(self.docs[b.UI],b.uid('roster/slot/'+str(i)))
            self.assertEqual(node['text']['items'][0],'阵位 '+str(i));self.assertEqual(node['font']['items'][1],16)
    def test_native_grid_layout_keeps_abilities_and_stars_in_view(self):
        def positions(grid,count):
            mode=grid.get('layout_type',2);rows,cols=grid['grid_count']['items']
            cw,ch=grid['grid_size']['items'];sx,sy=grid['grid_space']['items']
            if mode==1:
                self.assertGreater(rows,0,'Native row-bounded layout cannot use zero rows')
                return[(i//rows*(cw+sx),i%rows*(ch+sy),cw,ch)for i in range(count)]
            self.assertEqual(mode,2);self.assertGreater(cols,0)
            return[(i%cols*(cw+sx),i//cols*(ch+sy),cw,ch)for i in range(count)]
        main=self.docs[b.MAIN]['data']['children'][0];g=b.child(main,'grid_view_2')
        points=positions(g,3);w,h=g['size']['items']
        self.assertEqual(len({y for x,y,cw,ch in points}),3)
        self.assertTrue(all(x+cw<=w-8 and y+ch<=h-8 for x,y,cw,ch in points))
        for file in [b.MAIN,b.SUB,b.ROW]:
            for grid in b.walk(self.docs[file]):
                if grid.get('type')==25 and grid.get('name')=='grid_view':
                    ps=positions(grid,5);w,h=grid['size']['items']
                    self.assertEqual(len({y for x,y,cw,ch in ps}),1)
                    self.assertTrue(all(x+cw<=w and y+ch<=h for x,y,cw,ch in ps))
    def test_disabled_troop_upgrade_keeps_nonempty_label(self):
        self.e=Offline();self.e.troop();self.e.call(b.NAMES[2],1)
        self.assertEqual(self.e.labels[(1,'1/main1/兵种养成主项.套装区域.上部区域.激活bt')],'升级')
        for i in [6,7,8]:
            self.assertIn(self.e.labels[(1,f'1/sub{i}/兵种养成子项.上部区域.激活bt')],['激活','升级'])

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]);result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(passed=result.wasSuccessful(),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                manifest_sha256=b.sha((b.WORK/'manifest.json').read_bytes()),
                limits='Strict UI-only ECA execution and preservation checks. Original business calls are boundaries; engine loading and gameplay remain separate.')
    result_path('inner').write_bytes(b.encode(report));sys.exit(0 if result.wasSuccessful()else 1)
