"""Read-only checks of the live Y3 wave rewards, scroll, and settlement bindings."""

import argparse
from decimal import Decimal
import json
from pathlib import Path


def walk(data):
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from walk(value)
    elif isinstance(data, list):
        for value in data:
            yield from walk(value)


def child(parent, name):
    result, = (n for n in parent['children'] if n['name'] == name)
    return result


def paths(parent, prefix=''):
    for n in parent.get('children', []):
        path = prefix + n['name']
        yield path
        yield from paths(n, path + '.')


def verify_alignment(resource):
    for n in walk(resource):
        if 'alignment' in n:
            a = n['alignment']
            assert a['__tuple__'] is True and a['items'] in ([1, 8], [2, 8], [4, 8]), n.get('name')


def main(project):
    def read(rel):
        return json.loads((project / rel).read_bytes())

    assert read('header.project')['project_name'] == 'ProjectMonster02'
    m = 'maps/map3/'
    table = 'tables/波次货币奖励表.json'
    reward = read(m + table)
    entry_reward = read('maps/EntryMap/' + table)
    assert reward['table_data'] == entry_reward['table_data'] and reward['tid'] == entry_reward['tid']
    columns, _, *rows = reward['table_data']['data']
    values = [dict(zip(columns, row, strict=True)) for row in rows]
    coverage = {(int(row['难度']), int(row['波次'])) for row in values}
    encounter = read(m + 'tables/关卡怪物部署表-关卡1-出怪表.json')
    expected = {(int(row[1]), int(row[2])) for row in encounter['table_data']['data'][2:] if row[0]}
    assert coverage == expected and len(coverage) == len(values)
    for row in values:
        assert row['关卡编号'] == '1'
        assert 0 < Decimal(row['快档秒数']) < Decimal(row['中档秒数'])
        if int(row['波次']) == 1:
            assert len({Decimal(row[k + '徽章']) for k in ('快', '中', '保底')}) == 1

    wave = read(m + 'global_trigger/function/new/功能执行/处理波次货币奖励.json')
    assert wave['valid'] is True
    grants = [n for n in walk(wave) if n.get('action_type') == 'ROLE_CHANGE_RES']
    assert len(grants) == len({n['args_list'][1]['args_list'][0] for n in grants}) == 3
    kill_currency = [n for n in walk(wave) if n.get('action_type') == 'SET_UNIT_REWARD_RES']
    assert len(kill_currency) == 3 and all(Decimal(str(n['args_list'][-1]['args_list'][0])) == 0 for n in kill_currency)
    whiteboard = read(m + 'ui/动态白板(勿删).json')
    timeline_kind = '战斗_波次奖励卷轴揭晓'
    timeline_id, timeline = next((k, a) for k, a in whiteboard['anim_data'].items() if a.get('anim_name') == timeline_kind)
    assert timeline['max_frame'] == 60 and timeline['f_rt'] == 30 and not timeline['lp']
    widget = child(whiteboard, '波次奖励演出')
    assert widget['visible'] is False
    assert all(not n.get('swallow_touches') and not n.get('event_list') for n in walk(widget) if 'uid' in n)
    track = next(t for t in timeline['dt'] if t['name'] == widget['uid'])
    visibility = next(x for x in track['dt'] if x['tp'] == 5)
    assert visibility['dt']['0']['val'] is True and visibility['dt']['60']['val'] is False
    play, = (n for n in walk(wave) if n.get('action_type') == 'PLAY_UI_COMP_ANIM_NEW'
             and n['args_list'][1]['args_list'] == [timeline_id])
    assert play['op_arg'][1]['args_list'] == [60]

    report = read(m + 'ui/通关记录界面.json')
    verify_alignment(report)
    root = child(report, '通关记录界面')
    panel = child(root, '通关界面')
    assert panel['pos_data'] == child(root, '军帐背景')['pos_data']
    assert panel['pos_data']['items'][:4] == [50, 50, 50, 50]
    names = ('战报波次格', '战报奖励行')
    available = set()
    group = next(n for n in walk(read(m + 'editor/uiprefabtreegroupinfo.json')) if n.get('name') == 'new' and 'group' in n)
    for name in names:
        prefab = read(m + f'ui/prefab/{name}.json')
        verify_alignment(prefab)
        assert prefab['key'] == prefab['data']['prefab_key']
        assert sum(row.get('items') == [prefab['key'], name] for row in group['group']) == 1
        child(prefab['data'], name)
        available.update(paths(prefab['data']))
    eca = read(m + 'global_trigger/trigger/UI/通关结算信息.json')
    report_paths = {n['args_list'][1]['args_list'][0] for n in walk(eca)
                    if n.get('sub_type') == 'GET_UI_PREFAB_CHILD_BY_PATH'
                    and isinstance(n['args_list'][1]['args_list'][0], str)
                    and n['args_list'][1]['args_list'][0].startswith(tuple(k + '.' for k in names))}
    assert len(report_paths) == 6 and report_paths <= available
    button = child(panel, '退出bt')
    listener = eca['sub_trigger']['233571038']
    assert eca['valid'] is True and listener['valid'] is True and listener['is_conf'] and listener['enabled'] is False
    assert eca['action'].count(listener['trigger_id']) == 1
    event = listener['event'][0]['args_list'][0]['args_list'][0]
    assert any(n['name'] == event for n in button['event_list'])
    print(f'PASS: {len(rows)} wave configurations, 3 currency grants, 60-frame scroll, centered report, '
          f'{len(report_paths)} native prefab bindings, one exit registration. Read-only; not an engine test.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    main(parser.parse_args().project.resolve(strict=True))
