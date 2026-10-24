"""One-operand shared-team classification fix; no hero regeneration."""
import argparse
import json
import shutil

import y3_hero_runtime_followup_20261024 as base
import y3_hero_runtime_followup_r5_20261024 as previous
from y3_hero_repair_p1_shared import TEAM, patch_player_membership

ROOT = base.ROOT
WORK = previous.WORK.parent/'hero-followup-20261024-r6'
FILES = [TEAM]
PREFIX = '[技能排查/20261024-r6] '
LOG = previous.LOG.parent/'littlemurloc_2026_10_24_11_06_12.log'


def build(root):
    return {TEAM: patch_player_membership(base.trace.read(root/TEAM))}


def configure():
    base.WORK, base.FILES, base.build, base.PREFIX = WORK, FILES, build, PREFIX


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','publish','verify'])
    action=parser.parse_args().action
    configure()
    if action=='prepare':
        base.prepare();shutil.copy2(LOG,WORK/'runtime-before.log')
    elif action=='publish':base.publish()
    else:
        result=base.verify()
        doc=base.trace.read(ROOT/TEAM)
        assert doc.get('valid') is True
        assert patch_player_membership(doc)==doc
        result['function_valid']=True
        base.trace.save(WORK/'editor-verified.json',result)
        print(json.dumps(result))
