import json
import pathlib
import sys

MAP = pathlib.Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3')


def read(relative):
    return json.loads((MAP / relative).read_bytes())


def walk(value, pointer=''):
    if isinstance(value, dict):
        yield pointer, value
        for key, child in value.items():
            yield from walk(child, pointer + '/' + str(key))
    elif isinstance(value, list):
        for key, child in enumerate(value):
            yield from walk(child, pointer + '/' + str(key))


if sys.argv[1] == 'summary':
    for relative in sys.argv[2:]:
        obj = read(relative)
        print(relative)
        for key, t in obj.get('trigger_dict', {}).items():
            print(key, t.get('name'), t.get('valid'), t.get('enable'),
                  [(n.get('event_type'), n.get('args_list')) for n in t['event']],
                  [n.get('action_type') for n in t['action'] if isinstance(n, dict)])
        print('variables', json.dumps(obj.get('variable_dict', {}), ensure_ascii=False))
        print('locals', json.dumps(obj.get('local_variable', {}), ensure_ascii=False))
elif sys.argv[1] == 'nodes':
    obj = read(sys.argv[2])
    kinds = set(sys.argv[3:])
    for pointer, node in walk(obj):
        if any(node.get(k) in kinds for k in ('action_type', 'sub_type', 'condition_type', 'event_type')):
            print(pointer, json.dumps(node, ensure_ascii=False))
elif sys.argv[1] == 'names':
    lang = read('zhlanguage.json')
    for folder in ('abilityall', 'modifierall'):
        for file in (MAP / 'editor_table' / folder).glob('*.json'):
            obj = json.loads(file.read_bytes())
            name = obj.get('name')
            name = lang.get(str(name), name)
            if any(q in str(name) for q in sys.argv[2:]):
                print(folder, file.stem, name, obj.get('suffix'))
elif sys.argv[1] == 'pointer':
    value = read(sys.argv[2])
    for token in sys.argv[3].strip('/').split('/'):
        value = value[int(token)] if isinstance(value, list) else value[token]
    print(json.dumps(value, ensure_ascii=False, indent=2))
