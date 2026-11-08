const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const mapPath = process.argv[2];
if (!mapPath) {
  throw new Error('usage: node tests/test_equipment_item_bar_fix.js MAP_PATH');
}

const files = new Map([
  ['global_trigger/trigger/UI/装备行囊_确认穿戴或交换.json', 8],
  ['global_trigger/trigger/UI/装备行囊_卸下回库.json', 1],
  ['global_trigger/function/new/UI/刷新装备英雄行.json', 4],
  ['global_trigger/trigger/UI/主HUD英雄信息.json', 1],
  ['global_trigger/function/new/功能执行/动态创建玩家新队长单位.json', 1],
  ['global_trigger/function/new/镜像挑战/06_刷新队伍界面.json', 1],
  ['item/134283207.json', 2],
]);

for (const [relativePath, expected] of files) {
  const source = fs.readFileSync(path.join(mapPath, relativePath), 'utf8');
  JSON.parse(source);
  const bars = [...source.matchAll(/"arg_type":\s*100135,\s*"args_list":\s*\[\s*(\d+)\s*\]/g)]
    .map((match) => Number(match[1]));
  assert.equal(bars.length, expected, `${relativePath}: unexpected slot reference count`);
  assert.ok(bars.every((bar) => bar === 1), `${relativePath}: equipment must use item bar 1`);
  process.stdout.write(`${relativePath}: ${bars.length} item-bar references OK\n`);
}
