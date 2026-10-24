"""User-approved melee-normal-only descriptions, applied after code overlays."""
import copy
from pathlib import Path
from y3_hero_repair_p1_shared import load

TEXT = {
    134245809: '吕布位于前排时，受到的近战普攻伤害降低10%，不减免技能伤害。吕布攻击队长或精英时，普攻伤害提高10%。',
    134271608: '张飞位于前排时，受到的近战普攻伤害降低10%。受到近战伤害时获得守势，最多3层；每层守势使近战普攻伤害降低6%。上述减伤不包含技能伤害。',
    134283219: '张飞统率的小兵受到的近战普攻伤害降低10%。张飞拥有守势时，小兵受到的近战普攻伤害额外降低8%；不减免技能伤害。',
    134254183: '夏侯惇位于前排时，受到的击退效果降低50%。夏侯惇拥有刚烈时，受到的近战普攻伤害降低8%；不减免技能伤害。',
}


def build(root: Path, overlay=None):
    overlay = overlay or {}
    language = copy.deepcopy(overlay.get('zhlanguage.json'))
    if language is None:
        language = load(root / 'zhlanguage.json')
    table = copy.deepcopy(overlay.get('tables/技能作用描述表.json'))
    if table is None:
        table = load(root / 'tables/技能作用描述表.json')
    for oid, text in TEXT.items():
        obj = load(root / f'editor_table/abilityall/{oid}.json')
        for field in ('desc', 'description'):
            if field in obj:
                key = str(obj[field])
                assert key in language
                language[key] = '<html><body><p>' + text + '</p></body></html>'
    core = load(root / 'editor_table/modifierall/134224490.json')
    for key in {str(core[field]) for field in ('desc', 'description') if field in core}:
        old = language[key]
        phrase = '每层守势使张飞受到的近战伤害降低'
        assert phrase in old
        language[key] = old.replace(phrase, '每层守势使张飞受到的近战普攻伤害降低')
    count = 0
    for row in table['table_data']['data'][2:]:
        if len(row) > 1 and row[1] in TEXT:
            count += 1
            for i in range(3, len(row)):
                if isinstance(row[i], str):
                    row[i] = row[i].replace('近战受伤', '近战普攻受伤')
    assert count == len(TEXT), 'Skill description mapping changed'
    return {'zhlanguage.json': language, 'tables/技能作用描述表.json': table}, [
        {'issue': '40/41-text', 'status': 'candidate', 'skills': list(TEXT),
         'effect': 'Only melee normal attacks receive these reductions; resource acquisition text retained'}]
