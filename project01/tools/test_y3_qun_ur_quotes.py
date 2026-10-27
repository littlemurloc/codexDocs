"""Run all 20 existing Qun cases plus complete quote-set leak regressions.

The obsolete function is tested against intentionally contaminated data to
demonstrate the original failure. Inputs come from compact regression fixtures;
no retired publication helper or temporary directory is required.
"""
from __future__ import annotations
import copy,json,unittest
import test_y3_qun_command_cards as h
q=h.q
REL=f'{q.FOLDER}/{q.NAMES[19]}.json'
OLD=copy.deepcopy(h.FIXTURE['legacy_unlock'])
NEW=copy.deepcopy(h.DATA[REL])
generated=q.build_functions(h.FIXTURE['attribute_rules'])[REL]
for key in ('action','var_data','func_comment'):NEW[key]=generated[key]
h.DATA[REL]=NEW;h.FUNCS[q.FIDS[19]]=NEW

def quotes(x):
    # Entire unlocked, unowned, non-result candidate set; no member-ID sampling.
    return {r['技能类型'] for r in x.configs[1].values()
      if r['是否解锁'] and not r['是否已抽取'] and not r['是否合成']}

def contaminate(x,including_subgroup=False):
    for aid in q.UR:
        row=x.configs[1][h.ROW_BY_ID[aid]];row['所属set']='天策营'
        if including_subgroup:row['子归类']='董卓'

class QuoteCases(h.QunCases):
    def assert_no_ur_quotes(self,x):self.assertFalse(quotes(x)&set(q.UR))
    def test_old_function_reproduces_original_quote_leak(self):
        h.FUNCS[q.FIDS[19]]=OLD
        try:
            x,c,*_=h.world();contaminate(x)
            for stage in range(1,5):h.finish(x,c,'黄巾',stage)
            self.assertTrue({q.NORMAL_YELLOW,q.SPECIAL}<=quotes(x))
        finally:h.FUNCS[q.FIDS[19]]=NEW
    def test_corrected_tables_all_stages_keep_terminal_cards_out_of_quotes(self):
        x,c,*_=h.world();self.assert_no_ur_quotes(x)
        for stage in range(1,5):
            for route in ('西凉','黄巾'):
                h.finish(x,c,route,stage);self.assert_no_ur_quotes(x)
        self.assertEqual(c.cards&set(q.UR),set())
        for route in ('西凉','黄巾'):
            self.assertTrue(set(h.SPECS[h.RESULTS[route,5]]['members'])<=quotes(x))
        h.finish(x,c,'黄巾',5);self.assertEqual(c.cards&set(q.UR),{q.SPECIAL})
        h.finish(x,c,'西凉',5);self.assertEqual(c.cards&set(q.UR),{q.SPECIAL})
        self.assertEqual(sum(aid in q.UR for _,aid in x.grants),1)
    def test_wrong_old_group_cannot_unlock_any_terminal_ur(self):
        x,c,*_=h.world();contaminate(x)
        for stage in range(1,5):
            h.finish(x,c,'黄巾',stage);self.assert_no_ur_quotes(x)
        self.assertTrue(set(h.SPECS[h.RESULTS['黄巾',5]]['members'])<=quotes(x))
    def test_terminal_id_exclusion_survives_wrong_subgroup_too(self):
        x,c,*_=h.world();contaminate(x,including_subgroup=True)
        for stage in range(1,5):h.finish(x,c,'黄巾',stage)
        self.assert_no_ur_quotes(x)
    def test_full_quote_collection_completes_special_ending_with_old_bad_groups(self):
        x,c,*_=h.world();contaminate(x)
        # Select all current candidates from the complete eligible set each round.
        for _ in range(4):
            for aid in sorted(quotes(x)):
                self.assertNotIn(aid,q.UR);x.choose(c,aid)
            self.assert_no_ur_quotes(x)
        self.assertEqual(x.player_kv[1][q.STEP+'西凉'],5)
        self.assertEqual(x.player_kv[1][q.STEP+'黄巾'],5)
        self.assertFalse(c.cards&set(q.UR))
        for aid in sorted(quotes(x)):x.choose(c,aid)
        self.assertEqual(c.cards&set(q.UR),{q.SPECIAL})
        self.assertEqual(sum(aid in q.UR for _,aid in x.grants),1)
    def test_bad_or_empty_next_set_does_not_advance_stage(self):
        for value in ('无','','不存在的套牌'):
            x,c,*_=h.world();row=h.ROW_BY_ID[h.RESULTS['黄巾',1]]
            x.configs[1][row]['解锁set']=value
            h.VM(x,c,q.BASE,False).execute(q.FIDS[19],[1,row,'黄巾',1])
            self.assertEqual(x.player_kv[1][q.STEP+'黄巾'],1)
    def test_other_faction_and_result_rows_not_opened(self):
        x,c,*_=h.world();row=h.ROW_BY_ID[h.RESULTS['黄巾',1]]
        template=copy.deepcopy(x.configs[1][h.ROW_BY_ID[h.SPECS[h.RESULTS['黄巾',2]]['members'][0]]])
        for k,field,value in ((900,'升级机制','魏国'),(901,'是否合成',True),(902,'子归类','无')):
            extra=copy.deepcopy(template);extra['技能类型']=900000000+k;extra['是否解锁']=False;extra[field]=value;x.configs[1][k]=extra
        h.VM(x,c,q.BASE,False).execute(q.FIDS[19],[1,row,'黄巾',1])
        for k in (900,901,902):self.assertFalse(x.configs[1][k]['是否解锁'])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(QuoteCases))
    raise SystemExit(not result.wasSuccessful())
