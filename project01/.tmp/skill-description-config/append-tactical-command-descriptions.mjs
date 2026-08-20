import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const configDir = "D:/codex/project01/deliverables/config-file";
const commandCardsPath = `${configDir}/config_军令卡牌技能表.xlsx`;
const descriptionsPath = `${configDir}/config_技能作用描述表.xlsx`;

const commandDefinitions = [
  { set: "破军1", type: "被动", description: "队长攻击 +8%，小兵攻击 +4%。" },
  { set: "破军1", type: "被动", description: "击败队长/精英时，全军攻速 +4%，最多 3 层。" },
  { set: "破军1", type: "主动", description: "对 1 名队长/精英造成 3 次真实伤害，共 6% 最大生命。" },
  { set: "破军1", type: "主动", description: "打击指定一路：全体敌人受 4% 真实伤害，队长/精英额外 +2%；防御 -15%，持续 4 秒。" },
  { set: "虎贲2", type: "被动", description: "前排队长及小兵防御 +12%。" },
  { set: "虎贲2", type: "被动", description: "前排队长及小兵最大生命 +10%。" },
  { set: "虎贲2", type: "被动", description: "前排队长首次降至 40% 生命时，本队受伤 -20%，持续 6 秒。" },
  { set: "虎贲2", type: "被动", description: "只要前排队长存活，中后排友军受伤 -5%。" },
  { set: "飞骑2", type: "被动", description: "侧翼队长及小兵移速 +12%，闪避 +8%。" },
  { set: "飞骑2", type: "被动", description: "侧翼队伍攻击敌方中后排时，伤害 +10%。" },
  { set: "飞骑2", type: "主动", description: "打击指定一路最后排敌队，全队各受 5% 真实伤害。" },
  { set: "飞骑2", type: "主动", description: "打击指定一路最后排敌队：各受 8% 真实伤害，攻速 -35%，移速 -30%，持续 5 秒。" },
  { set: "火计1", type: "被动", description: "每波开始，敌方前排灼烧 4 秒，每秒 0.6% 最大生命。" },
  { set: "火计1", type: "被动", description: "灼烧敌人死亡时，同路其余敌人受 2% 真实伤害；每路每波 1 次。" },
  { set: "火计1", type: "主动", description: "指定一路灼烧 5 秒，每秒 1% 最大生命。" },
  { set: "火计1", type: "主动", description: "指定一路灼烧 5 秒，每秒 1.5% 最大生命；其造成伤害 -15%。" },
  { set: "连环2", type: "被动", description: "灼烧且低于 40% 生命的队长/精英，受到伤害 +12%。" },
  { set: "连环2", type: "被动", description: "灼烧队长/精英死亡时，同路敌人防御 -12%，持续 5 秒。" },
  { set: "连环2", type: "主动", description: "锁定一路低血队长/精英：造成 4% 真实伤害，并灼烧 5 秒；若死亡，波及相邻路。" },
  { set: "连环2", type: "主动", description: "锁定一路低血队长/精英：造成 6% 真实伤害，并强化灼烧；死亡时相邻路受 4% 真实伤害，防御 -12%。" },
  { set: "伏兵2", type: "被动", description: "每波前 6 秒，敌方队长/精英攻速 -10%。" },
  { set: "伏兵2", type: "被动", description: "队长/精英首次降至 50% 生命时，造成伤害 -12%，持续本波。" },
  { set: "伏兵2", type: "主动", description: "伏击指定一路：全体敌人受 2% 真实伤害，攻速/移速 -30%，持续 4 秒；队长/精英额外伤害降低。" },
  { set: "伏兵2", type: "主动", description: "强化伏击指定一路：全体敌人受 4% 真实伤害，攻速/移速 -40%，持续 5 秒；队长/精英伤害 -20%。" },
  { set: "屯田1", type: "被动", description: "每次进入备战阶段，获得 1 点军资。" },
  { set: "屯田1", type: "被动", description: "每个备战阶段，第 1 次刷新免费。" },
  { set: "屯田1", type: "被动", description: "每波首次击败精英或 Boss 时，获得 1 点军资。" },
  { set: "屯田1", type: "被动", description: "战前军资 >=5 时，全军最大生命 +8%；军资 >=8 时，最大生命 +12%，攻击 +8%。" },
  { set: "募兵2", type: "被动", description: "每个备战阶段可花 1 军资，为 1 名存活队长补 1 名小兵。" },
  { set: "募兵2", type: "被动", description: "全体小兵最大生命 +12%，攻击 +8%。" },
  { set: "募兵2", type: "被动", description: "满编队伍每波获得攻速 +10%、受伤 -6%。" },
  { set: "募兵2", type: "被动", description: "每次备战最多补 2 名小兵；满编队伍攻速 +15%、受伤 -10%、攻击 +8%。" },
  { set: "军械2", type: "被动", description: "全军攻击 +8%。" },
  { set: "军械2", type: "被动", description: "全军防御 +10%。" },
  { set: "军械2", type: "被动", description: "全军攻速 +10%，普攻暴击率 +5%。" },
  { set: "军械2", type: "被动", description: "每名友军每第 4 次普攻无视目标 30% 防御。" },
];

function buildDescriptionRow(key, abilityId, type, description) {
  return [key, abilityId, type, description, ...Array(10).fill(description)];
}

const commandWorkbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load(commandCardsPath),
);
const commandSheet = commandWorkbook.worksheets.getItem("config_军令卡牌技能表");
const commandRows = commandSheet.getRange("A5:I40").values;

if (commandRows.length !== commandDefinitions.length) {
  throw new Error(`军令卡牌表数量为 ${commandRows.length}，与设计清单 ${commandDefinitions.length} 条不一致。`);
}

const newCommandRows = [];
const commandIds = new Set();
for (let index = 0; index < commandRows.length; index += 1) {
  const card = commandRows[index];
  const definition = commandDefinitions[index];
  const abilityId = card[1];
  const setName = card[4];

  if (!abilityId) {
    throw new Error(`军令卡牌表第 ${index + 5} 行缺少技能类型。`);
  }
  if (setName !== definition.set) {
    throw new Error(`军令卡牌表第 ${index + 5} 行所属 set 为 ${setName}，预期为 ${definition.set}。`);
  }
  if (commandIds.has(abilityId)) {
    throw new Error(`军令卡牌表存在重复技能 ID：${abilityId}。`);
  }

  commandIds.add(abilityId);
  newCommandRows.push({ abilityId, type: definition.type, description: definition.description });
}

const descriptionWorkbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load(descriptionsPath),
);
const descriptionSheet = descriptionWorkbook.worksheets.getItem("config_技能作用描述表");
const existingValues = descriptionSheet.getUsedRange().values;
const existingRows = existingValues.slice(4).filter((row) => row[0] !== null && row[0] !== "");
const existingRowById = new Map(existingRows.map((row, index) => [row[1], index + 5]));
const existingKeys = existingRows.map((row) => Number(row[0])).filter(Number.isFinite);
const maxKey = Math.max(...existingKeys);

const commandsToAppend = [];
const updatedRows = [];
for (const command of newCommandRows) {
  const existingRow = existingRowById.get(command.abilityId);
  if (existingRow) {
    descriptionSheet.getRange(`C${existingRow}:N${existingRow}`).values = [[
      command.type,
      command.description,
      ...Array(10).fill(command.description),
    ]];
    updatedRows.push(existingRow);
  } else {
    commandsToAppend.push(command);
  }
}

const appendRows = commandsToAppend.map((command, index) =>
  buildDescriptionRow(maxKey + index + 1, command.abilityId, command.type, command.description),
);
const startRow = 5 + existingRows.length;
const appendEndRow = startRow + appendRows.length - 1;
const finalEndRow = 4 + existingRows.length + appendRows.length;

if (appendRows.length > 0) {
  descriptionSheet.getRange(`A${startRow}:N${appendEndRow}`).values = appendRows;
}

const changedStartRow = Math.min(...updatedRows, ...(appendRows.length > 0 ? [startRow] : []));
const changedEndRow = Math.max(...updatedRows, ...(appendRows.length > 0 ? [appendEndRow] : []));

descriptionSheet.getRange(`A2:A${finalEndRow}`).format.columnWidth = 8;
descriptionSheet.getRange(`B2:B${finalEndRow}`).format.columnWidth = 16;
descriptionSheet.getRange(`C2:C${finalEndRow}`).format.columnWidth = 10;
descriptionSheet.getRange(`D${changedStartRow}:N${changedEndRow}`).format.wrapText = true;
descriptionSheet.getRange(`D${changedStartRow}:N${changedEndRow}`).format.columnWidth = 20;
descriptionSheet.getRange(`A${changedStartRow}:N${changedEndRow}`).format.autofitRows();

const finalRows = descriptionSheet.getRange(`A5:N${finalEndRow}`).values;
const finalIds = new Set(finalRows.map((row) => row[1]));
if (finalRows.length !== existingRows.length + appendRows.length) {
  throw new Error("技能作用描述表最终行数不正确。");
}
if (finalIds.size !== finalRows.length) {
  throw new Error("技能作用描述表存在重复技能 ID。");
}
if ([...commandIds].some((abilityId) => !finalIds.has(abilityId))) {
  throw new Error("存在军令卡牌技能 ID 未写入描述表。");
}
if (finalRows.some((row) => !row[2] || !row[3] || !row[4])) {
  throw new Error("存在缺少类型标记或描述的技能记录。");
}

const output = await SpreadsheetFile.exportXlsx(descriptionWorkbook);
await output.save(descriptionsPath);

const reloaded = await SpreadsheetFile.importXlsx(await FileBlob.load(descriptionsPath));
const verification = await reloaded.inspect({
  kind: "table",
  range: `A${changedStartRow}:N${changedEndRow}`,
  include: "values,formulas",
  tableMaxRows: 36,
  tableMaxCols: 14,
  tableMaxCellChars: 140,
});
await fs.writeFile(
  "D:/codex/project01/.tmp/skill-description-config/command-append-inspect.txt",
  verification.ndjson,
  "utf8",
);

const errors = await reloaded.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan after tactical command append",
});
await fs.writeFile(
  "D:/codex/project01/.tmp/skill-description-config/command-append-errors.txt",
  errors.ndjson,
  "utf8",
);

const preview = await reloaded.render({
  sheetName: "config_技能作用描述表",
  range: `A${changedStartRow}:E${changedEndRow}`,
  scale: 1.1,
  format: "png",
});
await fs.writeFile(
  "D:/codex/project01/.tmp/skill-description-config/command-append-preview.png",
  new Uint8Array(await preview.arrayBuffer()),
);

console.log(JSON.stringify({
  existingRows: existingRows.length,
  updatedRows: updatedRows.length,
  appendedRows: appendRows.length,
  finalRows: finalRows.length,
  commandSkillIds: commandIds.size,
  changedStartRow,
  changedEndRow,
  output: descriptionsPath,
}));
