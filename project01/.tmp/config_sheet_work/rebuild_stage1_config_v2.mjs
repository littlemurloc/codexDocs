import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.cwd();
const sourceDir = path.join(root, "deliverables", "config-file");
const outputDir = path.join(root, "outputs", "stage1-monster-config-v0.2");
const previewDir = path.join(root, ".tmp", "config_sheet_work", "previews-v2");
const deploymentFile = "config_关卡怪物部署表-关卡1-出怪表.xlsx";
const unitFile = "config_单位列表.xlsx";

const id = {
  blade: 134258132,
  archer: 134224536,
  spearman: 134231603,
  shield: 134255117,
  cavalry: 134247767,
  strongman: 134222862,
  crossbowCaptain: 134230974,
  spearCaptain: 134267990,
  shieldCaptain: 134233924,
  cavalryCaptain: 134222406,
  lvBu: 134235305,
  zhangFei: 134270097,
  lvMeng: 134235416,
  huangZhong: 134230636,
  zhugeLiang: 134268516,
  zhaoYun: 134229701,
  liuBei: 134245859,
  xiaHouDun: 134236938,
  simaYi: 134262145,
  ganNing: 134232125,
  caoRen: 134267035,
  dianWei: 134249908,
  zhangLiao: 134235822,
  maChao: 134268301,
  xunYu: 134260324,
  taiShiCi: 134264969,
  sunShangXiang: 134219460,
  xiaHouYuan: 134276481,
};

const tag = (tier) => `难度${tier}`;
const squad = (leader, slot, tier, soldier, count) => ({ leader, slot, tier: tag(tier), soldier, count });
const captain = (leader, slot, soldier, count) => squad(leader, slot, 1, soldier, count);
const hero = (leader, slot, tier, soldier, count) => squad(leader, slot, tier, soldier, count);

const smallSquadLeaders = [id.strongman, id.crossbowCaptain, id.spearCaptain, id.shieldCaptain, id.cavalryCaptain];
const frontLeaders = [
  id.strongman, id.spearCaptain, id.shieldCaptain, id.cavalryCaptain,
  id.zhangFei, id.xiaHouDun, id.lvBu, id.zhaoYun, id.ganNing, id.lvMeng,
  id.caoRen, id.dianWei, id.zhangLiao, id.maChao, id.taiShiCi,
];
const rearLeaders = [
  id.crossbowCaptain, id.huangZhong, id.zhugeLiang, id.liuBei, id.simaYi,
  id.xunYu, id.sunShangXiang, id.xiaHouYuan,
];

const unitRows = [
  [1001, true, 134249360, "初级猎人03", 134249360, 3000, 0, 100, 0, 10, 0, 1.00, 120, 2.0, 0, 0, 0, 0],
  [1002, true, 134270627, "刀兵", 134270627, 600, 0, 55, 0, 5, 0, 1.70, 100, 1.0, 10, 10, 0, 0],
  [1003, true, 134281982, "弓兵", 134281982, 450, 0, 65, 0, 3, 0, 1.80, 100, 1.0, 18, 15, 0, 0],
  [1004, true, 134278489, "枪兵", 134278489, 660, 0, 58, 0, 7, 0, 1.68, 100, 1.0, 12, 12, 0, 0],
  [1005, true, 134236300, "盾兵", 134236300, 780, 0, 47, 0, 13, 0, 1.85, 100, 1.0, 14, 12, 0, 0],
  [1006, true, 134278285, "骑兵", 134278285, 620, 0, 70, 0, 5, 0, 1.45, 100, 1.0, 16, 15, 0, 0],
  [1007, true, id.blade, "刀兵", id.blade, 850, 0, 72, 0, 6, 0, 1.65, 100, 1.0, 10, 10, 0, 0],
  [1008, true, id.archer, "弓兵", id.archer, 650, 0, 88, 0, 3, 0, 1.75, 100, 1.0, 18, 15, 0, 0],
  [1009, true, id.spearman, "枪兵", id.spearman, 930, 0, 76, 0, 9, 0, 1.62, 100, 1.0, 12, 12, 0, 0],
  [1010, true, id.shield, "盾兵", id.shield, 1100, 0, 58, 0, 18, 0, 1.90, 100, 1.0, 14, 12, 0, 0],
  [1011, true, id.cavalry, "骑兵", id.cavalry, 860, 0, 92, 0, 7, 0, 1.40, 100, 1.0, 16, 15, 0, 0],
  [1012, true, id.strongman, "力士队长", id.strongman, 3200, 0, 150, 0, 26, 0, 1.85, 100, 1.0, 35, 50, 0, 0],
  [1013, true, id.crossbowCaptain, "弩手队长", id.crossbowCaptain, 2600, 0, 175, 0, 13, 0, 1.65, 100, 1.0, 40, 55, 0, 0],
  [1014, true, id.spearCaptain, "枪兵队长", id.spearCaptain, 3500, 0, 160, 0, 30, 0, 1.75, 100, 1.0, 42, 55, 0, 0],
  [1015, true, id.shieldCaptain, "盾兵队长", id.shieldCaptain, 4300, 0, 125, 0, 42, 0, 1.95, 100, 1.0, 45, 60, 0, 0],
  [1016, true, id.cavalryCaptain, "骑兵队长", id.cavalryCaptain, 3000, 0, 195, 0, 20, 0, 1.45, 100, 1.0, 45, 60, 0, 0],
  [10001, true, id.lvBu, "吕布", id.lvBu, 3300, 340, 250, 25, 20, 2, 1.35, 100, 1.0, 60, 0, 0, 0],
  [10002, true, id.zhangFei, "张飞", id.zhangFei, 4000, 460, 170, 15, 30, 4, 1.45, 100, 1.0, 60, 0, 0, 0],
  [10003, true, id.lvMeng, "吕蒙", id.lvMeng, 2600, 280, 235, 26, 12, 2, 1.15, 100, 1.0, 60, 0, 0, 0],
  [10004, true, id.huangZhong, "黄忠", id.huangZhong, 2300, 230, 255, 28, 9, 1, 1.40, 100, 1.0, 60, 0, 0, 0],
  [10005, true, id.zhugeLiang, "诸葛亮", id.zhugeLiang, 2200, 250, 195, 22, 10, 1, 1.45, 100, 1.0, 60, 0, 0, 0],
  [10006, true, id.zhaoYun, "赵云", id.zhaoYun, 3000, 320, 220, 24, 16, 2, 1.25, 100, 1.0, 60, 0, 0, 0],
  [10007, true, id.liuBei, "刘备", id.liuBei, 2800, 350, 155, 15, 15, 2, 1.50, 100, 1.0, 60, 0, 0, 0],
  [10008, true, id.xiaHouDun, "夏侯惇", id.xiaHouDun, 3800, 440, 180, 16, 32, 4, 1.45, 100, 1.0, 60, 0, 0, 0],
  [10009, true, id.simaYi, "司马懿", id.simaYi, 2100, 230, 205, 25, 9, 1, 1.45, 100, 1.0, 60, 0, 0, 0],
  [10010, true, id.ganNing, "甘宁", id.ganNing, 2750, 290, 240, 27, 14, 2, 1.15, 100, 1.0, 60, 0, 0, 0],
  [10011, true, 134267035, "曹仁", 134267035, 3900, 430, 165, 15, 34, 4, 1.50, 100, 1.0, 60, 0, 0, 0],
  [10012, true, 134249908, "典韦", 134249908, 3600, 400, 230, 23, 25, 3, 1.30, 100, 1.0, 60, 0, 0, 0],
  [10013, true, 134235822, "张辽", 134235822, 3100, 330, 225, 24, 18, 2, 1.25, 100, 1.0, 60, 0, 0, 0],
  [10014, true, 134268301, "马超", 134268301, 3050, 320, 245, 26, 16, 2, 1.20, 100, 1.0, 60, 0, 0, 0],
  [10015, true, 134260324, "荀彧", 134260324, 2550, 300, 170, 16, 13, 2, 1.50, 100, 1.0, 60, 0, 0, 0],
  [10016, true, 134264969, "太史慈", 134264969, 2750, 285, 250, 27, 14, 2, 1.20, 100, 1.0, 60, 0, 0, 0],
  [10017, true, 134219460, "孙尚香", 134219460, 2200, 230, 270, 29, 8, 1, 1.35, 100, 1.0, 60, 0, 0, 0],
  [10018, true, 134276481, "夏侯渊", 134276481, 2450, 250, 265, 28, 11, 1, 1.30, 100, 1.0, 60, 0, 0, 0],
];

const waveCounts = [4, 5, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
const slotsByWave = [
  [2, 8, 5, 1, 3, 7, 9, 4, 6],
  [1, 3, 7, 9, 5, 2, 8, 4, 6],
  [2, 5, 8, 1, 3, 7, 9, 4, 6],
];

function isRangedLeader(leaderId) {
  return rearLeaders.includes(leaderId);
}

function soldierFor(leaderId, groupIndex, difficulty, wave) {
  if (isRangedLeader(leaderId)) return id.archer;
  const cycle = [id.blade, id.spearman, id.shield, id.cavalry];
  return cycle[(groupIndex + difficulty + wave) % cycle.length];
}

function normalTier(difficulty, wave, waveCount) {
  if (difficulty <= 3) return 1;
  if (difficulty <= 6) return wave === waveCount ? 2 : 1;
  if (difficulty <= 9) return wave / waveCount > 0.62 ? 2 : 1;
  if (difficulty <= 12) return wave / waveCount > 0.78 ? 3 : 2;
  return wave / waveCount > 0.56 ? 3 : 2;
}

function selectLeader(difficulty, wave, groupIndex, groupCount, tier) {
  if (difficulty <= 2) {
    return smallSquadLeaders[(wave + groupIndex) % smallSquadLeaders.length];
  }
  if (difficulty <= 4) {
    const pool = [
      ...smallSquadLeaders, id.zhangFei, id.huangZhong, id.zhaoYun,
      id.caoRen, id.dianWei, id.zhangLiao, id.xunYu, id.sunShangXiang, id.xiaHouYuan,
    ];
    return pool[(difficulty * 3 + wave + groupIndex * 2) % pool.length];
  }
  if (difficulty <= 6) {
    const pool = [
      id.zhangFei, id.huangZhong, id.zhaoYun, id.liuBei, id.xiaHouDun, id.zhugeLiang, id.ganNing, id.simaYi,
      id.caoRen, id.dianWei, id.zhangLiao, id.maChao, id.xunYu, id.taiShiCi, id.sunShangXiang, id.xiaHouYuan,
      id.strongman,
    ];
    return pool[(difficulty * 4 + wave + groupIndex * 3) % pool.length];
  }
  const frontPool = frontLeaders;
  const rearPool = rearLeaders;
  const pool = groupIndex % 3 === 1 || groupIndex >= groupCount - 2 ? rearPool : frontPool;
  return pool[(difficulty * 5 + wave * 2 + groupIndex + tier) % pool.length];
}

function groupCountFor(difficulty, wave, waveCount) {
  const progress = wave / waveCount;
  if (difficulty === 1) return wave === 4 ? 2 : 1;
  if (difficulty <= 3) return progress > 0.7 ? 3 : 2;
  if (difficulty <= 5) return progress > 0.75 ? 4 : 3;
  if (difficulty <= 8) return progress > 0.8 ? 5 : 4;
  if (difficulty <= 11) return progress > 0.8 ? 6 : 5;
  if (difficulty <= 13) return progress > 0.82 ? 7 : 6;
  return progress > 0.84 ? 9 : 7;
}

function soldierCountFor(difficulty, wave, waveCount, groupIndex, groupCount) {
  const progress = wave / waveCount;
  let base;
  if (difficulty <= 2) base = 2;
  else if (difficulty <= 4) base = 3;
  else if (difficulty <= 6) base = 4;
  else if (difficulty <= 9) base = 5;
  else if (difficulty <= 12) base = 6;
  else base = 7;

  if (progress > 0.7) base += 1;
  if (progress > 0.92 && difficulty >= 10) base += 1;
  if (groupIndex === groupCount - 1 && difficulty >= 8 && progress > 0.75) base += 1;
  return Math.min(8, base);
}

function buildGenericWave(difficulty, wave, waveCount) {
  const groupCount = groupCountFor(difficulty, wave, waveCount);
  const tier = normalTier(difficulty, wave, waveCount);
  const slots = slotsByWave[(difficulty + wave) % slotsByWave.length];
  const groups = [];
  for (let groupIndex = 0; groupIndex < groupCount; groupIndex += 1) {
    const leader = selectLeader(difficulty, wave, groupIndex, groupCount, tier);
    const effectiveTier = smallSquadLeaders.includes(leader) ? 1 : tier;
    groups.push(squad(
      leader,
      slots[groupIndex],
      effectiveTier,
      soldierFor(leader, groupIndex, difficulty, wave),
      soldierCountFor(difficulty, wave, waveCount, groupIndex, groupCount),
    ));
  }
  return groups;
}

function buildDifficultyOne() {
  return [
    [captain(id.strongman, 2, id.blade, 1)],
    [captain(id.strongman, 2, id.blade, 2)],
    [captain(id.crossbowCaptain, 8, id.archer, 2)],
    [captain(id.strongman, 2, id.blade, 3), captain(id.crossbowCaptain, 8, id.archer, 2)],
  ];
}

function buildWaves() {
  const output = [];
  waveCounts.forEach((waveCount, index) => {
    const difficulty = index + 1;
    const waves = difficulty === 1 ? buildDifficultyOne() : Array.from(
      { length: waveCount },
      (_, waveIndex) => buildGenericWave(difficulty, waveIndex + 1, waveCount),
    );
    waves.forEach((groups, waveIndex) => output.push({ difficulty, wave: waveIndex + 1, groups }));
  });
  return output;
}

const waves = buildWaves();
if (waves.length !== 189) throw new Error(`Expected 189 waves, received ${waves.length}.`);

const knownTypes = new Set(unitRows.map((row) => row[2]));
for (const { difficulty, wave, groups } of waves) {
  if (groups.length < 1 || groups.length > 9) throw new Error(`D${difficulty} W${wave}: invalid group count.`);
  const usedSlots = new Set();
  for (const group of groups) {
    if (!knownTypes.has(group.leader) || !knownTypes.has(group.soldier)) throw new Error(`D${difficulty} W${wave}: unknown unit type.`);
    if (group.slot < 1 || group.slot > 9 || usedSlots.has(group.slot)) throw new Error(`D${difficulty} W${wave}: invalid grid slot.`);
    if (group.count < 1 || group.count > 8) throw new Error(`D${difficulty} W${wave}: invalid soldier count.`);
    usedSlots.add(group.slot);
  }
}

function buildHeaders() {
  const header = ["key", "关卡难度", "波次", "区域名称（说明）", "tips", "是否已刷新"];
  const types = ["int", "int", "int", "string", "string", "bool"];
  const keys = ["key1", null, null, null, null, null];
  for (let index = 1; index <= 9; index += 1) {
    header.push(`怪物队长${index}`, `队长${index}站位编号`, `怪物队长${index}-难度标签`, `怪物${index}`, `怪物${index}-数量`);
    types.push("unit_type", "int", "string", "unit_type", "int");
    keys.push(null, null, null, null, null);
  }
  return { header, types, keys };
}

function waveRow(key, waveData) {
  const row = [key, waveData.difficulty, waveData.wave, `第${waveData.wave}波`, "111", false];
  for (let i = 0; i < 9; i += 1) {
    const group = waveData.groups[i];
    row.push(...(group ? [group.leader, group.slot, group.tier, group.soldier, group.count] : [0, 1, tag(1), 0, 0]));
  }
  return row;
}

function columnName(columnNumber) {
  let number = columnNumber;
  let name = "";
  while (number > 0) {
    const remainder = (number - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    number = Math.floor((number - 1) / 26);
  }
  return name;
}

function setDeploymentLayout(sheet, finalRow) {
  const widths = [8, 10, 8, 16, 8, 10];
  widths.forEach((width, index) => {
    const col = columnName(index + 1);
    sheet.getRange(`${col}2:${col}${finalRow}`).format.columnWidth = width;
  });
  for (let group = 0; group < 9; group += 1) {
    const start = 7 + group * 5;
    [15, 11, 13, 15, 10].forEach((width, offset) => {
      const col = columnName(start + offset);
      sheet.getRange(`${col}2:${col}${finalRow}`).format.columnWidth = width;
    });
  }
  sheet.getRange("A2:AY2").format.wrapText = true;
  sheet.getRange("A2:AY2").format.rowHeight = 30;
}

function setUnitLayout(sheet) {
  const widths = [10, 10, 15, 14, 15, 11, 11, 11, 11, 10, 11, 11, 11, 11, 11, 11, 11, 11];
  widths.forEach((width, index) => {
    const col = columnName(index + 1);
    sheet.getRange(`${col}2:${col}38`).format.columnWidth = width;
  });
  sheet.getRange("A2:R2").format.wrapText = true;
  sheet.getRange("A2:R2").format.rowHeight = 30;
}

async function importWorkbook(fileName) {
  return SpreadsheetFile.importXlsx(await FileBlob.load(path.join(sourceDir, fileName)));
}

async function saveToOutputAndSource(workbook, fileName) {
  const file = await SpreadsheetFile.exportXlsx(workbook);
  const outputPath = path.join(outputDir, fileName);
  await file.save(outputPath);
  await fs.copyFile(outputPath, path.join(sourceDir, fileName));
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const unitWorkbook = await importWorkbook(unitFile);
const unitSheet = unitWorkbook.worksheets.getItemAt(0);
unitSheet.getRange("A5:R38").values = unitRows;
setUnitLayout(unitSheet);
const unitCheck = await unitWorkbook.inspect({
  kind: "table",
  range: "A2:R38",
  include: "values,formulas",
  tableMaxRows: 38,
  tableMaxCols: 18,
  maxChars: 16000,
});
console.log(`UNIT_CHECK\n${unitCheck.ndjson}`);
const unitRender = await unitWorkbook.render({ sheetName: unitSheet.name, range: "A1:R38", scale: 1.2, format: "png" });
await fs.writeFile(path.join(previewDir, "unit-list.png"), new Uint8Array(await unitRender.arrayBuffer()));
await saveToOutputAndSource(unitWorkbook, unitFile);

const deploymentWorkbook = await importWorkbook(deploymentFile);
const deploymentSheet = deploymentWorkbook.worksheets.getItemAt(0);
const { header, types, keys } = buildHeaders();
const finalRow = 4 + waves.length;
deploymentSheet.getRange("A2:AY500").clear({ applyTo: "contents" });
deploymentSheet.getRange("A2:AY2").values = [header];
deploymentSheet.getRange("A3:AY3").values = [types];
deploymentSheet.getRange("A4:AY4").values = [keys];
deploymentSheet.getRange(`A5:AY${finalRow}`).values = waves.map((waveData, index) => waveRow(index + 1, waveData));
setDeploymentLayout(deploymentSheet, finalRow);
const deploymentCheck = await deploymentWorkbook.inspect({
  kind: "table",
  range: `A2:AY${finalRow}`,
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 51,
  maxChars: 18000,
});
console.log(`DEPLOYMENT_CHECK\n${deploymentCheck.ndjson}`);
for (const [name, range] of [
  ["deployment-top", "A1:AY16"],
  ["deployment-mid", "A45:AY60"],
  ["deployment-bottom", `A178:AY${finalRow}`],
]) {
  const preview = await deploymentWorkbook.render({ sheetName: deploymentSheet.name, range, scale: 1.0, format: "png" });
  await fs.writeFile(path.join(previewDir, `${name}.png`), new Uint8Array(await preview.arrayBuffer()));
}
await saveToOutputAndSource(deploymentWorkbook, deploymentFile);

const finalUnit = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(outputDir, unitFile)));
const finalUnitSheet = finalUnit.worksheets.getItemAt(0);
const finalDeployment = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(outputDir, deploymentFile)));
const finalDeploymentSheet = finalDeployment.worksheets.getItemAt(0);
const errorTerm = "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A";
const [unitErrors, deploymentErrors] = await Promise.all([
  finalUnit.inspect({ kind: "match", searchTerm: errorTerm, options: { useRegex: true, maxResults: 100 }, maxChars: 4000 }),
  finalDeployment.inspect({ kind: "match", searchTerm: errorTerm, options: { useRegex: true, maxResults: 100 }, maxChars: 4000 }),
]);
console.log(`UNIT_ERRORS\n${unitErrors.ndjson}`);
console.log(`DEPLOYMENT_ERRORS\n${deploymentErrors.ndjson}`);

const finalRender = await finalDeployment.render({
  sheetName: finalDeploymentSheet.name,
  range: `A178:AY${finalRow}`,
  scale: 1.0,
  format: "png",
});
await fs.writeFile(path.join(previewDir, "deployment-final-bottom.png"), new Uint8Array(await finalRender.arrayBuffer()));
console.log(JSON.stringify({ waves: waves.length, waveCounts, outputDir }));
