"""Append literal native diagnostics without rewriting any gameplay expression.

This is a separately approved diagnostic pass, not a replay of the withdrawn
skill-trace repair. No functions, globals, timers or object lookups are added.
"""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import argparse
import hashlib
import json
import shutil

MAP = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')
WORK = Path(__file__).resolve().parents[1] / 'tmp/native-skill-log-20261023'
HEROES = {
    '孙尚香': [134219500, 134251304, 134222169, 134219157, 134219344, 134276381],
    '太史慈': [134259517, 134234889, 134273833, 134255952, 134275696, 134267511],
    '黄忠': [134223239, 134278528, 134280536, 134237143, 134266460, 134236877],
}
CORES = {'孙尚香': 134248740, '太史慈': 134277456, '黄忠': 134242511}
PREFIX = '[技能追踪/简版v1] '
EVENTS = {
    'ABILITY_OBTAIN': '获得入口', 'ABILITY_LEVEL_CHANGED': '等级变化入口',
    'ABILITY_LOSE': '失去入口', 'ABILITY_SP_END': '出手入口',
    'ABILITY_PS_END': '施法结束入口', 'OBTAIN_MODIFIER': '循环建立入口',
    'LOSS_MODIFIER': '循环失去入口', 'MODIFIER_LAYER_CHANGE': '层数变化入口',
}
EFFECTS = {
    'APPLY_DAMAGE': '伤害动作', 'ADD_MODIFIER': '施加状态动作',
    'SET_CUR_DAMAGE': '修改事件伤害动作',
    'SET_BUFF_STACK': '设置层数动作', 'ADD_BUFF_STACK': '增减层数动作',
    'REMOVE_BUFF_INS': '移除状态动作',
}


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=4) + '\n', 'utf8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def strip_logs(value, added_ids):
    if isinstance(value, list):
        return [strip_logs(v, added_ids) for v in value
                if not (isinstance(v, dict) and v.get('element_id') in added_ids)]
    if isinstance(value, dict):
        return {k: strip_logs(v, added_ids) for k, v in value.items()}
    return value


def instrument(source, label, next_id):
    result = deepcopy(source)
    added = []

    def log(message, trigger_id, original_id=None):
        element_id = next(next_id)
        text = f'{PREFIX}{label} | {message} | 触发器={trigger_id}'
        if original_id is not None:
            text += f' | 节点={original_id}'
        added.append({'element_id': element_id, 'message': text})
        return {'action_type': 'PRINT_MESSAGE_ACTION_TO_DIALOG',
                'args_list': [{'arg_type': 100175, 'sub_type': 1, 'args_list': [3]},
                              {'arg_type': 100003, 'sub_type': 1, 'args_list': [text]}],
                'bp': False, 'element_id': element_id, 'enable': True}

    def rewrite(value, trigger_id):
        if isinstance(value, dict):
            if value.get('enable') is False:
                return deepcopy(value)
            return {k: rewrite(v, trigger_id) for k, v in value.items()}
        if not isinstance(value, list):
            return value
        output = []
        for original in value:
            item = rewrite(original, trigger_id)
            kind = original.get('action_type') if isinstance(original, dict) else None
            enabled = isinstance(original, dict) and original.get('enable') is not False
            effect = EFFECTS.get(kind) if enabled else None
            if enabled and kind == 'UNIT_RELEASE_COMMAND':
                args = original.get('args_list', [])
                if len(args) > 1 and args[1].get('sub_type') == 'UNIT_COMMAND_USE_SKILL':
                    effect = '施法命令动作'
            if effect:
                output.append(log(effect + '调用前', trigger_id, original['element_id']))
            output.append(item)
            if effect:
                output.append(log(effect + '已返回', trigger_id, original['element_id']))
        return output

    for tid, trigger in result['trigger_dict'].items():
        trigger['action'] = rewrite(trigger['action'], tid)
        events = [e.get('event_type', '') for e in trigger.get('event', [])]
        if events:
            phase = EVENTS.get(events[0], '事件响应入口/' + events[0])
            trigger['action'].insert(0, log(phase, tid))
    ids = {a['element_id'] for a in added}
    assert strip_logs(result, ids) == source, 'Non-log gameplay change detected'
    assert len(ids) == len(added)
    return result, added


def source_files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts)


def prepare():
    assert MAP.is_dir() and (MAP / 'ability/134219500.json').exists()
    assert not WORK.exists(), 'Do not overwrite an earlier pass or its backups'
    WORK.mkdir(parents=True)
    # Keep a complete map, including native containers, for official recovery.
    backup = WORK / 'map3-before'
    shutil.copytree(MAP, backup, ignore=shutil.ignore_patterns('.git'))
    baseline = {p.relative_to(backup).as_posix(): sha(p) for p in source_files(backup)}
    shutil.copy2(MAP.parents[1] / 'header.project', WORK / 'header.project.before')
    occupied = set()
    for p in source_files(backup):
        if p.suffix not in ('.json', '.txt'):
            continue
        try:
            occupied.update(n['element_id'] for n in walk(read(p)) if 'element_id' in n)
        except (ValueError, UnicodeError):
            continue
    def sequence():
        number = 209996400100000
        while True:
            number += 1
            if number not in occupied:
                occupied.add(number)
                yield number
    next_id = sequence()
    entries = []
    for hero, abilities in HEROES.items():
        specs = [('ability', key, f'{hero}/{star}星' + ('主动' if star % 2 else '被动'))
                 for star, key in enumerate(abilities, 1)]
        specs.append(('modifier', CORES[hero], hero + '/核心循环'))
        for kind, key, title in specs:
            relative = f'{kind}/{key}.json'
            original = read(backup / relative)
            patched, added = instrument(original, title + '#' + str(key), next_id)
            candidate = WORK / 'candidate' / relative
            save(candidate, patched)
            entries.append({'path': relative, 'before': baseline[relative],
                            'after': sha(candidate), 'logs': added})
    manifest = {'map': str(MAP), 'prepared': datetime.now().isoformat(),
                'backup': str(backup), 'entries': entries, 'baseline': baseline,
                'boundary': 'Static literal native diagnostics only; runtime not verified.'}
    save(WORK / 'manifest.json', manifest)
    print(json.dumps({'phase': 'prepared', 'files': len(entries),
                      'logs': sum(len(e['logs']) for e in entries),
                      'backup_files': len(baseline), 'work': str(WORK)}, ensure_ascii=False))


def verify(manifest):
    changes = {e['path']: e for e in manifest['entries']}
    for relative, before in manifest['baseline'].items():
        path = MAP / relative
        assert path.is_file(), 'Missing map file: ' + relative
        expected = changes[relative]['after'] if relative in changes else before
        assert sha(path) == expected, 'Unexpected file content: ' + relative
    current = {p.relative_to(MAP).as_posix() for p in source_files(MAP)}
    assert current == set(manifest['baseline']), 'Unexpected added/deleted files'
    for entry in changes.values():
        ids = {v['element_id'] for v in entry['logs']}
        assert strip_logs(read(MAP / entry['path']), ids) == read(WORK / 'map3-before' / entry['path'])
    return {'files_modified': len(changes), 'unchanged_files': len(current) - len(changes),
            'gameplay_ast_unchanged_after_removing_logs': True}


def publish():
    manifest = read(WORK / 'manifest.json')
    assert not (WORK / 'published.json').exists(), 'Already published'
    for relative, before in manifest['baseline'].items():
        assert sha(MAP / relative) == before, 'Map changed since backup: ' + relative
    for entry in manifest['entries']:
        assert sha(WORK / 'candidate' / entry['path']) == entry['after']
    for entry in manifest['entries']:
        shutil.copy2(WORK / 'candidate' / entry['path'], MAP / entry['path'])
    receipt = verify(manifest)
    receipt['published'] = datetime.now().isoformat()
    save(WORK / 'published.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'publish', 'verify'])
    action = parser.parse_args().action
    if action == 'prepare':
        prepare()
    elif action == 'publish':
        publish()
    else:
        print(json.dumps(verify(read(WORK / 'manifest.json')), ensure_ascii=False))
