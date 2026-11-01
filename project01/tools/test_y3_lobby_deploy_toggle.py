"""Execute original/fixed lobby ECA. Native UI delivery remains a play check."""
import argparse
import copy
import gzip
import itertools
import json
from pathlib import Path
import sys
import unittest
import fix_y3_lobby_deploy_toggle as fix

SOURCE=json.loads(gzip.decompress(fix.FIXTURE.read_bytes()))
OLD=SOURCE['before'];CAP=SOURCE['capacity'];NEW,_=fix.build(OLD)
UI_FID=next(n['sub_type']for _,n in fix.walk(OLD)if n.get('arg_type')==100177)


class StopLoop(Exception):pass


class VM:
    """Strict save-table actions; only type/index conversion and UI redraw stubbed.

    Iteration order is supplied by each input, not asserted as native sorting.
    Both traversals retain their original enabled optional arguments verbatim.
    """
    def __init__(self,players,limits=None):
        self.players=copy.deepcopy(players);self.limits=limits or {1:5,2:5}
        self.vars={};self.key=None;self.ui=None;self.result=None
        self.writes=[];self.redraws=[];self.cap_calls=[]
    def ev(self,n):
        t,a=n['sub_type'],n['args_list']
        if t in (1,2,6,11,'VARIABLE'):
            x=a[0]
            if isinstance(x,dict)and x.get('__tuple__'):
                name=x['items'][1]
                if name=='英雄队长上阵数量上限':
                    assert len(a)==2;return self.limits[self.ev(a[1])]
                assert len(a)==1;return self.vars[name]
            assert len(a)==1 and not isinstance(x,(dict,list)),'Expression wrapped in literal'
            return x
        if t in ('ca0d6f70383e11ee8046e454e8e29cb0','9384d061198e11ef967be8c829c05699'):
            # Explicit read-only ID/type and player/index doubles for this input.
            return self.ev(a[0])
        if t==CAP['func_id']:
            p,inside=[self.ev(v)for v in a];self.cap_calls.append((p,inside))
            assert inside is False,'This lobby test must not silently model battle groups'
            old=self.vars;self.vars={'执行玩家':p,'是否判断局内':inside,'是否达到上限':False,'count':0}
            self.run(CAP['action']);r=self.result;self.vars=old;return r
        if t=='GET_PLAYER_SAVE_DATA_TABLE_VALUE':
            assert self.ev(a[1])==16;return self.players[self.ev(a[0])]
        if t=='ITER_TABLE_KEY_INT':assert self.key is not None;return self.key
        if t in ('GET_PLAYER_SAVE_TABLE_VALUE_BOOLEAN','GET_PLAYER_SAVE_TABLE_VALUE_UNIT_NAME','GET_PLAYER_SAVE_TABLE_VALUE_INTEGER'):
            assert self.ev(a[1])==16 and n['op_arg_enable'][0]
            return self.players[self.ev(a[0])][self.ev(a[2])][self.ev(n['op_arg'][0])]
        if t=='INT_PLUS_ONE':return self.ev(a[0])+1
        if t=='FOR_EACH_UI_COMP':assert self.ui is not None;return self.ui
        if t=='GET_UI_COMP_PREFAB':self.ev(a[0]);return self.ev(a[1])
        if t=='GET_UNIT_NAME_KV':
            obj=self.ev(a[0]);assert self.ev(a[1])=='绑定英雄单位类型';return obj['unit']
        raise AssertionError('Unmodeled expression: '+str(t))
    def cond(self,n):
        assert n['condition_type']in ('BOOL_COMPARE','UNIT_CLASS_COMPARE','FLOAT_COMPARE')
        x,op,y=[self.ev(v)for v in n['args_list']]
        if op=='==':return x==y
        if op=='!=':return x!=y
        if op=='>=':return x>=y
        raise AssertionError(op)
    def run(self,actions):
        for n in actions:
            if n.get('enable')is False:continue
            t,a=n['action_type'],n['args_list']
            if t=='SET_VARIABLE':self.vars[a[0]['args_list'][0]['items'][1]]=self.ev(a[1])
            elif t in ('IF_THEN_ELSE','STORAGE_BOX'):
                yes=all([self.cond(c)for c in a[0]['args_list']if c.get('enable',True)])
                self.run(a[1 if yes else 2]['args_list'])
            elif t=='TRAVERSE_TABLE_NEW':
                assert n['op_arg_enable']==[True] and n['op_arg'][0]['args_list']==[True]
                table=self.ev(a[0]);old=self.key
                for k in list(table):
                    self.key=k
                    try:self.run(a[1]['args_list'])
                    except StopLoop:break
                self.key=old
            elif t=='BREAK_LOOP':raise StopLoop()
            elif t in ('SET_PLAYER_SAVE_TABLE_VALUE','REMOVE_PLAYER_SAVE_TABLE_VALUE'):
                assert self.ev(a[1])==16 and n['op_arg_enable'][0]
                p,k,field=self.ev(a[0]),self.ev(a[2]),self.ev(n['op_arg'][0])
                if t=='SET_PLAYER_SAVE_TABLE_VALUE':
                    value=self.ev(a[3]);self.players[p][k][field]=value;self.writes.append((p,k,field,value))
                else:self.players[p][k].pop(field,None);self.writes.append((p,k,field,'REMOVE'))
            elif t=='ITER_UI_COMP_DO':
                p=self.ev(a[0]);old=self.ui
                for row in self.players[p].values():
                    self.ui={'unit':row['单位类型']}
                    try:self.run(a[2]['args_list'])
                    except StopLoop:break
                self.ui=old
            elif t=='CALL_TRIGGER_FUNC':
                call=a[0];assert call['sub_type']==UI_FID
                control,p=[self.ev(v)for v in call['args_list']];self.redraws.append((p,control['unit']))
            elif t==400342:self.result=self.ev(a[0]) # set, never an invented early exit
            else:raise AssertionError('Unmodeled action: '+str(t))
    def click(self,doc,hero,player=1,slot=6):
        self.vars={'英雄类型编号':hero,'执行玩家':player,'指定上阵编号':slot,
                   '参战单位类型':0,'被替换单位类型':0}
        self.run(doc['action'])


def rows(count,order=(1,2,3,4,5,6)):
    slots=(1,3,4,7,9,6)
    return {10+7*i:{'单位类型':1000+i,'是否上阵':i<=count,'上阵9宫格':slots[i-1]if i<=count else -1,
                   '星级':i,'无关字段':'保留'}for i in order}


def deployed(vm,player=1):return {r['单位类型']for r in vm.players[player].values()if r['是否上阵']}


class Cases(unittest.TestCase):
    orders_checked=0
    def test_old_bug_is_reproduced(self):
        vm=VM({1:rows(5)});vm.click(OLD,1001)
        self.assertEqual(len(deployed(vm)),3)
        self.assertEqual([v for v in vm.writes if v[2]=='是否上阵'],[(1,24,'是否上阵',False),(1,17,'是否上阵',False)])
    def test_full_five_down_only_selected_for_all_orders(self):
        for order in itertools.permutations((1,2,3,4,5)):
            for selected in range(1,6):
                vm=VM({1:rows(5,order+(6,))});before=copy.deepcopy(vm.players)
                vm.click(NEW,1000+selected)
                self.assertEqual(deployed(vm),{1001,1002,1003,1004,1005}-{1000+selected})
                for key,row in vm.players[1].items():
                    if row['单位类型']!=1000+selected:self.assertEqual(row,before[1][key])
                self.assertEqual(vm.cap_calls,[]);self.assertEqual(vm.redraws,[])
                self.assertEqual(len([v for v in vm.writes if v[2]=='是否上阵']),1)
                type(self).orders_checked+=1
    def test_nonfull_down_matches_original_exactly(self):
        for count in range(1,5):
            for selected in range(1,count+1):
                a,c=VM({1:rows(count)}),VM({1:rows(count)})
                a.click(OLD,1000+selected);c.click(NEW,1000+selected)
                self.assertEqual(a.players,c.players);self.assertEqual(a.writes,c.writes)
    def test_new_hero_at_capacity_keeps_original_replacement(self):
        for order in itertools.permutations((1,2,3,4,5)):
            a,c=VM({1:rows(5,order+(6,))}),VM({1:rows(5,order+(6,))})
            a.click(OLD,1006);c.click(NEW,1006)
            self.assertEqual(a.players,c.players);self.assertEqual(a.writes,c.writes)
            self.assertEqual(a.redraws,c.redraws);self.assertEqual(len(c.redraws),1)
            self.assertEqual(len(deployed(c)),5);self.assertIn(1006,deployed(c))
    def test_nonfull_new_hero_matches_original(self):
        for count in range(5):
            a,c=VM({1:rows(count)}),VM({1:rows(count)})
            a.click(OLD,1006);c.click(NEW,1006)
            self.assertEqual(a.players,c.players);self.assertEqual(a.writes,c.writes)
    def test_down_up_down_has_no_stale_flags(self):
        vm=VM({1:rows(5)})
        for hero,slot,expected in [(1001,6,4),(1001,1,5),(1001,6,4),(1002,6,3)]:
            vm.click(NEW,hero,slot=slot);self.assertEqual(len(deployed(vm)),expected)
    def test_unknown_hero_does_not_evict_or_write(self):
        vm=VM({1:rows(5)});old=copy.deepcopy(vm.players);vm.click(NEW,999999)
        self.assertEqual(vm.players,old);self.assertFalse(vm.writes);self.assertFalse(vm.cap_calls)
    def test_player_isolation_and_configured_limit(self):
        vm=VM({1:rows(5),2:rows(3)},limits={1:5,2:3});second=copy.deepcopy(vm.players[2])
        vm.click(NEW,1001);self.assertEqual(vm.players[2],second)
        first=copy.deepcopy(vm.players[1]);vm.click(NEW,1002,player=2)
        self.assertEqual(len(deployed(vm,2)),2);self.assertEqual(vm.players[1],first)
    def test_exact_inverse_and_unchanged_original_subtrees(self):
        self.assertEqual(fix.restore(NEW,OLD['func_comment']),OLD)
        body=NEW['action'][2]['args_list'][1]['args_list']
        self.assertEqual(body[0]['args_list'][1]['args_list'][0],OLD['action'][1])
        self.assertEqual(body[1],OLD['action'][2])
        for k in ('func_id','trigger_id','func_param_list','func_rtv_name_list','group_id'):
            self.assertEqual(NEW.get(k),OLD.get(k))
    def test_native_structure_and_local_declarations(self):
        sys.path.insert(0,'C:/Users/littl/.codex/plugins/cache/y3-local/y3-eca/0.1.0')
        from eca_core import validate_structure
        r=validate_structure(NEW);self.assertTrue(r['structure_valid'],r);self.assertEqual(r['warning_count'],0)
        for name in fix.NAMES:
            self.assertIs(NEW['var_data'][0]['BOOLEAN'][name],False)
            self.assertEqual(NEW['var_data'][1][name],0);self.assertEqual(NEW['var_data'][2].count(name),1)
        old_actions=[v for _,v in fix.walk(OLD)if v.get('action_type')in ('SET_PLAYER_SAVE_TABLE_VALUE','REMOVE_PLAYER_SAVE_TABLE_VALUE')]
        new_actions=[v for _,v in fix.walk(NEW)if v.get('action_type')in ('SET_PLAYER_SAVE_TABLE_VALUE','REMOVE_PLAYER_SAVE_TABLE_VALUE')]
        self.assertEqual(new_actions,old_actions)
    def test_unknown_expressions_and_missing_fields_fail(self):
        vm=VM({1:rows(5)})
        with self.assertRaises(AssertionError):vm.ev(fix.base.expr(100002,'UNKNOWN_API'))
        with self.assertRaises(AssertionError):vm.ev(fix.base.expr(100011,1,fix.base.expr(100011,'GET_NEW_TABLE')))
        del vm.players[1][17]['是否上阵']
        with self.assertRaises(KeyError):vm.click(NEW,1001)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path);args=p.parse_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    if args.receipt:
        assert args.receipt.resolve()==(fix.WORK/'tests.json').resolve()
        m=fix.check(live=True)
        paths=['tools/fix_y3_lobby_deploy_toggle.py','tools/test_y3_lobby_deploy_toggle.py']
        report=dict(passed=result.wasSuccessful(),tests=result.testsRun,full_capacity_order_cases=Cases.orders_checked,
            manifest_sha256=fix.sha((fix.WORK/'manifest.json').read_bytes()),
            tool_hashes={s:fix.sha((fix.PROJECT/s).read_bytes())for s in paths},
            limits='Read-only type/player conversion and UI redraw doubles; native click delivery and gameplay smoke tests pending')
        args.receipt.write_bytes(fix.encode(report))
    raise SystemExit(not result.wasSuccessful())
