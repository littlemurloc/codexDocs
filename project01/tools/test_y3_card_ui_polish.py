"""Native badge-function execution, UI scope preservation and timing checks."""
import copy,json,sys,unittest,zipfile
import y3_card_ui_polish as p
import test_y3_forge_command_cards as h
import y3_recent_work_fixtures as fixtures
f=p.f
FIXTURE=fixtures.load('card-ui')
DATA=FIXTURE['staged']
h.h.FUNCS[p.FID]=DATA[p.NEW]
lookup='328a949b859611f180c31b625ad74320'
h.h.FUNCS.update(FIXTURE['native_helpers'])
class VM(h.VM):
    def execute(self,fid,args):
        if fid==lookup:
            # Existing lookup is pure; this fixture deliberately separates row IDs
            # from resource IDs and never treats the resource ID as a table row.
            value,table,key=args
            return next((row for row,rec in table.items()if rec.get(key)==value),0)
        if fid==p.SET_COUNT:
            self.w.badge_count_calls=getattr(self.w,'badge_count_calls',0)+1
            return (2,5)
        return super().execute(fid,args)
    def ev(self,node):
        if isinstance(node,dict)and node.get('sub_type')==p.SET_COUNT:
            return self.execute(p.SET_COUNT,[self.ev(x)for x in node['args_list']])[node.get('call_rt_index',0)]
        return super().ev(node)
class Cases(h.ForgeCases):
    # Reuse lifecycle setup; expose only the focused cases in the suite below.
    def setUp(self):
        self.forge_vm_before=h.VM;h.VM=VM;super().setUp()
    def tearDown(self):
        super().tearDown();h.VM=self.forge_vm_before
    def badge(self,x,c,aid):return VM(x,c,f.BASE,False).execute(p.FID,[c.player,aid])
    def test_unowned_material_is_zero_not_default_one(self):
        x,c,*_=h.world();self.assertEqual(self.badge(x,c,f.MATERIALS['铜']),'库存：0')
    def test_gain_and_debit_use_current_inventory(self):
        x,c,*_=h.world();aid=f.MATERIALS['铜'];x.choose(c,aid);self.assertEqual(self.badge(x,c,aid),'库存：1');x.choose(c,aid);self.assertEqual(self.badge(x,c,aid),'库存：2')
        x.choose(c,134264424);x.choose(c,aid);self.assertEqual(self.badge(x,c,aid),'库存：0');self.assertEqual(x.player_kv[1][f.COUNT],1)
    def test_other_cards_keep_two_return_progress(self):
        x,c,*_=h.world();self.assertEqual(self.badge(x,c,134264424),'2/5');self.assertEqual(getattr(x,'badge_count_calls',0),2)
    def test_inventory_is_player_isolated(self):
        x,c,*_=h.world();other=h.h.Unit('other',player=2);x.choose(other,f.BASE);x.choose(c,f.MATERIALS['铜'])
        self.assertEqual(self.badge(x,c,f.MATERIALS['铜']),'库存：1');self.assertEqual(self.badge(x,other,f.MATERIALS['铜']),'库存：0')
    def test_ui_renderers_only_replace_two_text_expressions(self):
        tracking=FIXTURE['tracking']
        for path,oldnode in tracking['original_text_nodes'].items():
            doc=copy.deepcopy(DATA[path]);current=next(n for n in f.b.walk(doc)if n.get('element_id')==oldnode['element_id']);current.clear();current.update(oldnode)
            if path==p.SHOW:
                fly=next(n for n in f.b.walk(doc)if n.get('element_id')==tracking['original_fly_call']['element_id']);fly.clear();fly.update(tracking['original_fly_call'])
                for key,change in tracking['timings'].items():
                    element,location=key.split(':',1);import ast
                    loc=ast.literal_eval(location);node=next(n for n in f.b.walk(doc)if n.get('element_id')==int(element))
                    for component in loc[:-1]:node=node[component]
                    node[loc[-1]]=change['before']
            self.assertEqual(doc,FIXTURE['before'][path],path)
    def test_effect_lifetime_reveal_and_frame_cleanup_are_synchronized(self):
        doc=DATA[p.SHOW];nodes={n['element_id']:n for n in f.b.walk(doc)if 'element_id'in n}
        seq=nodes[454042343001455]['args_list'][0]
        self.assertTrue(all(seq['op_arg_enable']))
        self.assertEqual(seq['op_arg'][2]['args_list'][0],.025);self.assertEqual(seq['op_arg'][3]['args_list'][0],.875)
        self.assertEqual(nodes[454042343001470]['args_list'][0]['args_list'][0],.875)
        fly=nodes[454042343002104];self.assertEqual(fly['action_type'],'PLAY_UI_COMP_ANIM_NEW')
        self.assertEqual(fly['op_arg'][1]['args_list'][0],31);self.assertEqual(fly['op_arg'][2]['args_list'][0],2.)
        self.assertTrue(all(fly['op_arg_enable']))
        self.assertEqual(nodes[454042343002121]['args_list'][0]['args_list'][0],16)
        self.assertLessEqual(nodes[454042343002062]['args_list'][6]['args_list'][0],p.HOLD)
    def test_index_types_and_new_function_identity(self):
        self.assertIn('返回军略卡牌右上角文本.json',DATA[p.INDEX]);doc=DATA[p.NEW];self.assertEqual(doc['func_id'],p.FID);self.assertEqual(doc['trigger_id'],p.TID)
        ids=[n['element_id']for n in f.b.walk(doc)if 'element_id'in n];self.assertEqual(len(ids),len(set(ids)))
        for n in f.b.walk(doc):self.assertFalse(n.get('arg_type')in(100003,100011)and n.get('sub_type')==1 and any(isinstance(v,dict)for v in n.get('args_list',[])))

if __name__=='__main__':
    names=[n for n in Cases.__dict__ if n.startswith('test_')];suite=unittest.TestSuite(Cases(n)for n in names)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
