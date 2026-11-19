"""Strict offline checks for the staged native ECA, not an engine simulator.

Execute the actual generated expression/action trees. Unimplemented native
operations fail rather than silently passing. Rendering/network persistence
and original page widgets still require Y3 runtime acceptance.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

import y3_safezone_skin_switch as b
from safezone_ui_fixtures import stage,reference,namespace,result_path
b.WORK=stage('skin');b.PROJECT=reference()


class Offline:
    def __init__(self):
        self.docs={}
        self.ui=b.load(b.WORK/'candidate'/b.UI)
        self.nodes={n['uid']:n for n in b.walk(self.ui)if 'uid'in n}
        self.cfg={int(row[0]):dict(zip(b.build_table()['table_data']['data'][0],row))
                  for row in b.load(b.WORK/'candidate'/b.TABLE)['table_data']['data'][2:]}
        for name in b.FUNCTION_NAMES:
            d=b.load(b.WORK/'candidate'/(b.FN_DIR+name+'.json'));self.docs[d['func_id']]=d
        self.kvs={};self.saved={};self.visibility={};self.labels={};self.images={};self.enabled={}
        self.fonts={};self.returns=[];self.events=[];self.uploads=[];self.notifications=[]
        self.rows={};self.write_allowed=True;self.save_writes=[]
        self.globals={b.REGISTERED:False};self.registered=[]
        self.trigger=b.load(b.WORK/'candidate'/b.TRIGGER)

    def call(self,name,player,*args):
        return self.func(b.FIDS.get(name,name),[player,*args])

    def func(self,fid,args):
        if fid=='c38cdfb8fb6011efbbdf456182e68a34':
            self.notifications.append(args);return None
        d=self.docs[fid];env={}
        for kind,members in d['var_data'][0].items():env.update(copy.deepcopy(members))
        names=[x['items'][0]for x in d['func_param_list']]
        assert len(names)==len(args),(fid,names,args)
        env.update(zip(names,args));env['_return']=None
        self.actions(d['action'],env)
        return env['_return']

    def value(self,x,env):
        if not isinstance(x,dict):raise AssertionError('Native expression required: '+repr(x))
        if 'condition_type'in x:return self.condition(x,env)
        t=x['arg_type'];s=x['sub_type'];a=x['args_list']
        if s==1:
            if t in [100021,100022]:return a
            assert len(a)==1 and not isinstance(a[0],dict), 'Expression wrapped in a constant'
            return a[0]
        if s in ['VARIABLE',6,2]:
            marker=a[0];items=marker.get('items')if isinstance(marker,dict)else marker
            if len(items)==2:return self.globals[items[1]]
            assert len(items)==3 and items[2]=='local',items
            return env[items[1]]
        def v(i):return self.value(a[i],env)
        if s=='GET_CURRENT_LEVEL':return 'f8f41509-b607-11ef-a1a4-1132d41864c6'
        if s=='TRIGGER_PLAYER':return env['_player']
        if s=='GET_UI_COMP_FROM_EVENT':return env['_component']
        if s=='GET_UI_COMP_NAME':return self.nodes[v(1)]['name']
        if s=='STR_TO_INT':return int(v(0))
        if s=='GET_INTEGER_KV':
            key=(v(0),v(1));assert key in self.kvs,'Missing KV: '+repr(key);return self.kvs[key]
        if s=='GET_BOOLEAN_KV':
            key=(v(0),v(1));assert key in self.kvs;result=self.kvs[key];assert isinstance(result,bool);return result
        if s=='GET_PLAYER_SAVE_DATA_INT_VALUE':return self.saved.get((v(0),v(1)),0)
        if s in ['GET_STRING_TABLE_VAR_ND','GET_INTEGER_TABLE_VAR_ND','GET_FLOAT_TABLE_VAR_ND']:
            assert v(0)==b.TABLE_ID
            result=self.cfg[int(v(1))][v(2)]
            return int(result)if s=='GET_INTEGER_TABLE_VAR_ND'else float(result)if s=='GET_FLOAT_TABLE_VAR_ND'else result
        if s=='GET_UI_COMP_BY_PATH':
            player,root,parts=v(0),v(1),v(2)
            node=self.nodes.get(root)
            for part in parts.split('.'):
                if node is None:return None
                node=next((n for n in node.get('children',[])if n['name']==part),None)
            return node['uid']if node else None
        if s=='GET_UI_COMP_VISIBLE':return self.visibility.get((v(0),v(1)),self.nodes[v(1)].get('visible',True))
        if s=='STR_JOIN':
            result=str(v(0))+str(v(1))
            for arg,on in zip(x.get('op_arg',[]),x.get('op_arg_enable',[])):
                if on:result+=str(self.value(arg,env))
            return result
        if s=='INT_TO_STR':return str(v(0))
        if s=='MATH_OPERATION':
            assert v(1)=='+';return v(0)+v(2)
        if s=='GET_PLAYER_SAVE_DATA_TABLE_VALUE':assert v(1)==16;return self.rows.get(v(0),{})
        if s=='ITER_TABLE_KEY_INT':return env['_row']
        if s in ['GET_PLAYER_SAVE_TABLE_VALUE_INTEGER','GET_PLAYER_SAVE_TABLE_VALUE_UNIT_NAME']:
            assert v(1)==16 and x['op_arg_enable']==[True,False]
            return self.rows[v(0)][v(2)][self.value(x['op_arg'][0],env)]
        if s=='NONE_UNIT_KEY':return None
        if s=='GET_ICON_BY_UNIT_TYPE':assert v(0)is not None;return 'icon:'+str(v(0))
        if s=='GET_UNIT_NAME_BY_TYPE':assert v(0)is not None;return '英雄'+str(v(0))
        if s in self.docs:return self.func(s,[self.value(e,env)for e in a])
        raise AssertionError('Unimplemented expression '+str(s))

    def condition(self,x,env):
        s=x['condition_type'];a=x['args_list']
        if s=='TYPE_IS_EXIST':return self.value(a[0],env)in self.nodes
        if s=='HAS_KV_ANY':return (self.value(a[0],env),self.value(a[1],env))in self.kvs
        if s in ['FLOAT_COMPARE','BOOL_COMPARE','ANY_COMPARE']:
            l,o,r=[self.value(e,env)for e in a]
            if o=='==':return l==r
            if o=='!=':return l!=r
            if o=='>':return l>r
            if o=='<=':return l<=r
            if o=='>=':return l>=r
        raise AssertionError('Unimplemented condition '+str(s))

    def actions(self,actions,env):
        for x in actions:
            if isinstance(x,int):
                assert str(x)in self.trigger['sub_trigger'];self.registered.append(x);continue
            assert isinstance(x,dict)
            s=x['action_type'];a=x['args_list']
            def v(i):return self.value(a[i],env)
            if s=='SET_VARIABLE':
                marker=a[0]['args_list'][0];items=marker['items']
                if len(items)==2:self.globals[items[1]]=v(1)
                else:env[items[1]]=v(1)
            elif s=='IF_THEN_ELSE':
                # Evaluate every condition, rather than granting unproven short-circuit protection.
                checks=[self.condition(c,env)for c in a[0]['args_list']]
                self.actions(a[1 if all(checks)else 2]['args_list'],env)
            elif s=='SET_ENTITY_KV':self.kvs[(v(0),v(1))]=v(2)
            elif s=='SET_UI_COMP_VISIBLE':
                assert v(2)in self.nodes;self.visibility[(v(0),v(2))]=v(1)
            elif s=='SET_UI_COMP_TEXT':assert v(1)in self.nodes;self.labels[(v(0),v(1))]=v(2)
            elif s=='SET_UI_COMP_FONT_COLOR_NORM':
                assert v(1)in self.nodes;self.fonts[(v(0),v(1))]=tuple(v(i)for i in range(2,6))
            elif s=='SET_UI_COMP_IMAGE_NEW':assert v(1)in self.nodes;self.images[(v(0),v(1))]=v(2)
            elif s=='SET_UI_COMP_ENABLE':assert v(1)in self.nodes;self.enabled[(v(0),v(1))]=v(2)
            elif s=='SET_SAVE_DATA':
                assert v(1)==19;self.save_writes.append((v(0),v(1),v(2)))
                if self.write_allowed:self.saved[(v(0),v(1))]=v(2)
            elif s=='UPLOAD_SAVE_DATA':self.uploads.append(v(0))
            elif s=='TRIGGER_UI_EVENT':self.events.append((v(0),v(1),v(2)))
            elif s=='CALL_TRIGGER_FUNC':
                call=a[0];self.func(call['sub_type'],[self.value(e,env)for e in call['args_list']])
            elif s=='TRAVERSE_TABLE_NEW':
                assert x['op_arg_enable']==[True]
                rows=v(0)
                for row in sorted(rows):env['_row']=row;self.actions(a[1]['args_list'],env)
            elif s==400342:env['_return']=v(0)
            else:raise AssertionError('Unimplemented action '+str(s))

    def shown(self,player,key):
        return self.visibility.get((player,b.uid(key)),self.nodes[b.uid(key)].get('visible',True))

    def init(self,player=1):self.call(b.FUNCTION_NAMES[3],player)
    def choose(self,skin,player=1):self.call(b.FUNCTION_NAMES[4],player,2,skin)
    def confirm(self,player=1):self.call(b.FUNCTION_NAMES[4],player,3,0)
    def cancel(self,player=1):self.call(b.FUNCTION_NAMES[4],player,0,0)
    def boot(self):self.actions(self.trigger['action'],{})
    def click(self,key,player=1):
        comp=b.uid(key);events=self.nodes[comp]['event_list'];assert len(events)==1
        name=events[0]['name'];handled=0
        for sid in self.registered:
            sub=self.trigger['sub_trigger'][str(sid)]
            if any(e['event_type']=='TRIGGER_COMPONENT_EVENT'and e['args_list'][0]['args_list']==[name]for e in sub['event']):
                env={'_player':player,'_component':comp};self.actions(sub['action'],env);handled+=1
        assert handled==1,(name,handled)


class TestFlow(unittest.TestCase):
    def setUp(self):self.e=Offline()
    def test_default_does_not_write_save(self):
        self.e.init();self.assertEqual(self.e.kvs[(1,b.CURRENT)],6)
        self.assertFalse(self.e.save_writes);self.assertFalse(self.e.uploads)
    def test_each_of_eight_saved_choices(self):
        for i in range(1,9):
            e=Offline();e.saved[(1,19)]=i;e.init()
            self.assertEqual(e.kvs[(1,b.CURRENT)],i)
            self.assertEqual([j for j in range(1,9)if e.shown(1,'skin/'+str(j))],[i])
    def test_missing_invalid_disabled_saved_choices(self):
        for value in [-100,0,9,100]:
            e=Offline();e.saved[(1,19)]=value;e.init();self.assertEqual(e.kvs[(1,b.CURRENT)],6)
        e=Offline();e.cfg[2]['开放']='0';e.saved[(1,19)]=2;e.init()
        self.assertEqual(e.kvs[(1,b.CURRENT)],6)
        self.assertFalse(e.enabled[(1,b.uid('menu/row/2'))])
    def test_candidate_does_not_apply(self):
        self.e.init();self.e.choose(8)
        self.assertEqual(self.e.kvs[(1,b.CURRENT)],6)
        self.assertEqual(self.e.kvs[(1,b.PENDING)],8)
        self.assertTrue(self.e.shown(1,'confirm'));self.assertFalse(self.e.save_writes)
        self.assertEqual(self.e.labels[(1,b.uid('confirm/change'))],'青玉璧环 → 墨金战阵')
    def test_cancel_and_stale_confirm_do_not_write(self):
        self.e.init();self.e.choose(8);self.e.cancel();self.e.confirm()
        self.assertEqual(self.e.kvs[(1,b.CURRENT)],6);self.assertFalse(self.e.save_writes)
        self.assertFalse(self.e.shown(1,'confirm'))
    def test_confirm_all_pairs_and_duplicate(self):
        for source in range(1,9):
            for target in range(1,9):
                e=Offline();e.saved[(1,19)]=source;e.init();e.choose(target);e.confirm();e.confirm()
                self.assertEqual(e.kvs[(1,b.CURRENT)],target)
                self.assertEqual(len(e.save_writes),0 if source==target else 1)
                self.assertEqual(e.saved[(1,19)],target)
                self.assertEqual([i for i in range(1,9)if e.shown(1,'skin/'+str(i))],[target])
    def test_players_are_independent(self):
        self.e.saved[(2,19)]=3;self.e.init(1);self.e.init(2);self.e.choose(8,1);self.e.confirm(1)
        self.assertEqual(self.e.kvs[(1,b.CURRENT)],8);self.assertEqual(self.e.kvs[(2,b.CURRENT)],3)
        self.assertEqual(self.e.saved[(2,19)],3);self.assertEqual(self.e.uploads,[1])
    def test_missing_template_keeps_old_visuals(self):
        self.e.init();self.e.choose(8);del self.e.nodes[b.uid('skin/8')];self.e.confirm()
        self.assertEqual(self.e.kvs[(1,b.CURRENT)],6);self.assertFalse(self.e.save_writes)
    def test_configuration_disabled_after_selection(self):
        self.e.init();self.e.choose(8);self.e.cfg[8]['开放']='0';self.e.confirm()
        self.assertEqual(self.e.kvs[(1,b.CURRENT)],6);self.assertFalse(self.e.save_writes)
    def test_save_write_failure_is_not_successful_upload(self):
        self.e.init();self.e.write_allowed=False;self.e.choose(8);self.e.confirm()
        self.assertEqual(self.e.kvs[(1,b.CURRENT)],6);self.assertFalse(self.e.uploads)
        self.assertTrue(self.e.notifications)
    def test_reentry_guard_and_uninitialized(self):
        self.e.choose(8);self.assertFalse(self.e.save_writes);self.e.init()
        self.e.kvs[(1,b.BUSY)]=True;self.e.choose(8)
        self.assertEqual(self.e.kvs[(1,b.PENDING)],0)
    def test_real_formation_summary_sparse_and_capacity(self):
        self.e.rows[1]={i*3:{'上阵9宫格':i,'单位类型':100+i}for i in range(1,10)}
        self.e.rows[1][100]={'上阵9宫格':0,'单位类型':999}
        self.e.rows[1][101]={'上阵9宫格':11,'单位类型':999}
        self.e.init();self.assertIn('9 位',self.e.labels[(1,b.uid('party/count'))])
        self.assertTrue(all(self.e.shown(1,'hero/'+str(i))for i in range(1,6)))
        self.e.rows[1]={3:{'上阵9宫格':2,'单位类型':200}};self.e.call(b.FUNCTION_NAMES[1],1)
        self.assertTrue(self.e.shown(1,'hero/1'));self.assertFalse(self.e.shown(1,'hero/2'))
        self.assertIn('1 位',self.e.labels[(1,b.uid('party/count'))])
    def test_routes_and_return_do_not_reset_skin_or_save(self):
        self.e.init();self.e.choose(3);self.e.confirm();saved=list(self.e.save_writes)
        for route in [1,2,3]:
            self.e.call(b.FUNCTION_NAMES[2],1,route)
            self.assertFalse(self.e.shown(1,'summary'))
            self.assertTrue(self.e.visibility[(1,b.PAGE_IDS[route-1])])
            self.assertTrue(self.e.shown(1,'skin/3'));self.assertFalse(self.e.shown(1,'skin/3/start'))
        self.e.call(b.FUNCTION_NAMES[2],1,0)
        self.assertTrue(self.e.shown(1,'summary'));self.assertTrue(self.e.shown(1,'skin/3/start'))
        self.assertEqual(self.e.save_writes,saved)
        self.assertEqual([e[2]for e in self.e.events],['切页1按钮_0','切页3按钮_0','副切页兵种养成按钮'])
    def test_config_name_is_single_source(self):
        self.e.cfg[8]['名称']='墨金测试名';self.e.init();self.e.choose(8)
        self.assertEqual(self.e.labels[(1,b.uid('menu/name/8'))],'墨金测试名')
        self.assertIn('墨金测试名',self.e.labels[(1,b.uid('confirm/change'))])
    def test_native_event_dispatch_from_registered_root(self):
        self.e.boot();self.e.boot();self.assertEqual(len(self.e.registered),11)
        self.e.init();self.e.click('skin/6/style');self.assertTrue(self.e.shown(1,'menu'))
        self.e.click('menu/row/8');self.assertTrue(self.e.shown(1,'confirm'))
        self.assertEqual(self.e.kvs[(1,b.CURRENT)],6)
        self.e.click('confirm/apply');self.assertEqual(self.e.kvs[(1,b.CURRENT)],8)
        self.assertEqual(self.e.save_writes,[(1,19,8)])
    def test_cancel_buttons_through_registered_events(self):
        self.e.boot();self.e.init()
        for key in ['confirm/cancel','confirm/close','menu/outside']:
            self.e.click('skin/6/style');self.e.click('menu/row/8');self.e.click(key)
            self.assertFalse(self.e.shown(1,'confirm'));self.assertEqual(self.e.kvs[(1,b.CURRENT)],6)
        self.assertFalse(self.e.save_writes)
    def test_each_skin_entry_uses_same_single_handler(self):
        self.e.boot();self.e.init()
        for i in range(1,9):
            self.e.call(b.FUNCTION_NAMES[0],1,i)
            self.e.click('skin/'+str(i)+'/style');self.assertTrue(self.e.shown(1,'menu'))
            self.e.click('menu/outside');self.assertFalse(self.e.shown(1,'menu'))


class TestStructure(unittest.TestCase):
    def setUp(self):self.stage=b.WORK/'candidate';self.before=b.WORK/'before'
    def test_old_ui_subtrees_unchanged(self):
        original=b.load(self.before/b.UI);new=b.load(self.stage/b.UI)
        oldnodes={n['uid']:n for n in b.walk(original)if 'uid'in n}
        newnodes={n['uid']:n for n in b.walk(new)if 'uid'in n}
        allowed={'1d9b244d-2452-49e3-9880-c4f831ae921d','407a99f4-b253-4e12-b5e0-2fe174b52f84',
                 '13a75c64-4def-4296-9ad6-b5b6879ed941','6143daa6-d5c5-4728-adef-046b751d98f3',
                 'f1a0dcd1-b813-495c-81f8-13a9fc6bffd9','e8969f05-d6ce-4c7e-9c29-68b91ecbc2e1'}
        for key,old in oldnodes.items():
            a={k:v for k,v in old.items()if k!='children'};z={k:v for k,v in newnodes[key].items()if k!='children'}
            if key in allowed:a['visible']=False
            self.assertEqual(a,z,key)
            self.assertEqual([x['uid']for x in old.get('children',[])],
                [x['uid']for x in newnodes[key].get('children',[])if x['uid']in oldnodes],key)
    def test_old_eca_only_adds_one_initialization_call(self):
        a=b.load(self.before/b.OLD);z=b.load(self.stage/b.OLD);call=z['action'].pop()
        self.assertEqual(a,z);self.assertEqual(call['args_list'][0]['sub_type'],b.FIDS[b.FUNCTION_NAMES[3]])
    def test_archive_existing_slots_identical(self):
        for key in ['archive/archive.json',b.MAP+'archive.json']:
            a=b.load(self.before/key);z=b.load(self.stage/key);slot=z['archive_slots'].pop('19')
            self.assertEqual(a,z);self.assertEqual(slot['type'],2);self.assertEqual(slot['value'],0)
            self.assertEqual(slot['name'],'playerUiSkin')
    def test_global_variable_complete_metadata(self):
        a=b.load(self.before/b.GLOBAL_VARS);z=b.load(self.stage/b.GLOBAL_VARS)
        self.assertIs(z['variable_dict']['BOOLEAN'].pop(b.REGISTERED),False)
        self.assertEqual(z['variable_length_dict'].pop(b.REGISTERED),0)
        self.assertEqual(z['variable_group_info'].pop()['items'][0],b.REGISTERED)
        self.assertEqual(a,z)
    def test_ui_uids_resources_and_cap_geometry(self):
        d=b.load(self.stage/b.UI);nodes=[n for n in b.walk(d)if 'uid'in n]
        counts=Counter(n['uid']for n in nodes);self.assertTrue(all(v==1 for v in counts.values()))
        old={n['uid']for n in b.walk(b.load(self.before/b.UI))if 'uid'in n}
        for n in nodes:
            if n['uid']in old:continue
            w,h=n['size']['items']
            for k,v in n.items():
                if (k.endswith('_picture')or k in ['image','mask_image'])and v is not None:
                    self.assertTrue((b.PROJECT/f'editor_table/editoricon/{v}.json').exists(),(n['name'],k,v))
                if k.endswith('cap_insets'):
                    l,t,r,bt=v['items'];self.assertLess(l+r,w,(n['name'],k));self.assertLess(t+bt,h,(n['name'],k))
            if n['type']in[3,4]and n['uid']not in[b.uid('menu/panel'),b.uid('confirm/panel')]:
                self.assertIs(n['swallow_touches'],False)
        seal=next(n for n in nodes if n['uid']==b.uid('skin/8/start'))
        self.assertEqual(seal['normal_cap_insets']['items'],[0,0,0,0])
        self.assertAlmostEqual(seal['size']['items'][0]/seal['size']['items'][1],317/303)
    def test_literal_native_constants_and_function_links(self):
        functions={d['func_id']for d in namespace()if d.get('func_id')}
        functions.update(b.FIDS.values());ui={n['uid']for n in b.walk(b.load(self.stage/b.UI))if'uid'in n}
        elements=[]
        for p in self.stage.rglob('*.json'):
            if 'global_trigger'not in p.parts:continue
            if p.name=='安全区主界面.json':continue
            for n in b.walk(b.load(p)):
                if 'element_id'in n:elements.append(n['element_id'])
                if 'arg_type'in n and n.get('sub_type')==1:
                    self.assertFalse(any(isinstance(v,dict)and'arg_type'in v for v in n['args_list']))
                    if n['arg_type']==100070:self.assertIn(n['args_list'][0],ui)
                if n.get('arg_type')==100177:self.assertIn(n['sub_type'],functions)
        self.assertEqual(len(elements),len(set(elements)))
    def test_listener_registration_and_declared_ui_events(self):
        d=b.load(self.stage/b.TRIGGER);registered=[x for x in b.walk(d['action'])if x.get('arg_type')==100022]
        refs=[i for x in registered for i in x['args_list']if isinstance(i,int)]
        self.assertEqual(set(refs),{int(i)for i in d['sub_trigger']});self.assertEqual(len(refs),11)
        names={e['name']for n in b.walk(b.load(self.stage/b.UI))if'uid'in n for e in n.get('event_list',[])}
        for s in d['sub_trigger'].values():
            self.assertFalse(s['enabled']);self.assertEqual(s['p_trigger_id'],b.TID)
            for ev in s['event']:
                if ev['event_type']=='TRIGGER_COMPONENT_EVENT':
                    self.assertIn(ev['args_list'][0]['args_list'][0],names)
        self.assertEqual(d['event'][0]['event_type'],'INIT_FINISHED')
        additions=[e['name']for c in b.walk(b.load(self.stage/b.UI))if'uid'in c
                   for e in c.get('event_list',[])if e['name'].startswith(('安全区新外层_','安全区风格_'))]
        self.assertEqual(len(additions),len(set(additions)),'Do not add duplicate UI event names')
    def test_table_and_indices(self):
        table=b.load(self.stage/b.TABLE);rows=table['table_data']['data'][2:]
        self.assertEqual([int(r[0])for r in rows],list(range(1,9)))
        self.assertEqual(sum(int(r[4])for r in rows),1)
        for index in [b.FI,b.TI]:
            a=b.load(self.before/index);z=b.load(self.stage/index)
            self.assertTrue(all(z[k]==v for k,v in a.items()))
            self.assertEqual(len(z.values()),len(set(z.values())))
    def test_no_root_trigger_or_function_identity_collision(self):
        kinds={'trigger_id':{},'func_id':{}}
        records=namespace();known_paths={d['path']for d in records}
        for record in records:
            rel=Path(record['path']);p2=self.stage/rel
            d=b.load(p2)if p2.exists()else record
            for kind in kinds:
                if kind in d:
                    self.assertNotIn(d[kind],kinds[kind],(kind,d[kind],str(rel)));kinds[kind][d[kind]]=str(rel)
        for p in self.stage.rglob('*.json'):
            if p.relative_to(self.stage).as_posix()in known_paths or'global_trigger'not in p.parts:continue
            d=b.load(p)
            for kind in kinds:
                if kind in d:self.assertNotIn(d[kind],kinds[kind]);kinds[kind][d[kind]]=str(p)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(passed=result.wasSuccessful(),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                manifest_sha256=b.sha((b.WORK/'manifest.json').read_bytes()),
                boundary='Offline actual-ECA state transitions and scope/identity checks only; no Y3 render, native page behavior, upload durability or multiplayer network verification')
    result_path('skin').write_bytes(b.encode(report))
    raise SystemExit(0 if result.wasSuccessful()else 1)
