import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const configDir = "D:/codex/project01/deliverables/config-file";
const unitSkillsPath = `${configDir}/config_单位技能配置表.xlsx`;
const descriptionsPath = `${configDir}/config_技能作用描述表.xlsx`;
const emptyAbilityId = "134255698";

const heroSkills = {
  吕布: {
    active: [
      "横扫当前一路前方最多 3 名敌人；每层威势提高本次伤害。",
      "攻击当前目标；若目标是队长/精英，嘲讽 3 秒并降低其攻击。",
      "突击低血队长/精英，消耗全部威势；每层威势提高本次伤害。",
    ],
    passive: [
      "前排时近战受伤 -10%；攻击队长/精英时普攻伤害 +10%。",
      "参与击破队长/精英时获得威势，最多 3 层；每层攻击 +6%。",
      "拥有威势时，降低当前目标区域内敌方小兵攻击；3 层时效果提高。",
    ],
  },
  黄忠: {
    active: [
      "射击当前目标；消耗 1 层蓄势时提高伤害，并短暂降低目标攻速。",
      "穿透当前一路敌人；消耗 1 层蓄势提高伤害，命中队长/精英时降低其攻击。",
      "瞄准低血队长/精英，消耗全部蓄势；每层蓄势提高伤害，并可打断技能。",
    ],
    passive: [
      "后排时普攻速度提高；普攻命中获得蓄势，最多 3 层。",
      "后排时远程受伤降低；一段时间未受近战伤害时，主动技能至少保留 1 层蓄势。",
      "黄忠远程小兵攻速提高；蓄势满层时，小兵对敌方小兵伤害提高。",
    ],
  },
  吕蒙: {
    active: [
      "突袭当前目标并短暂隐身；若触发背刺，伤害提高。",
      "对当前目标斩击 2 次；每次可背刺，第二击对低于 50% 生命目标增伤。",
      "突袭低血队长/精英并隐身；背刺或目标低于 35% 生命时伤害提高。",
    ],
    passive: [
      "侧翼时普攻速度提高；触发背刺时额外造成伤害。",
      "进入隐身后远程受伤降低；侧翼时隐身时间延长。",
      "脱离隐身后短时受伤降低；击败队长/精英时效果延长。",
    ],
  },
  张飞: {
    active: [
      "攻击当前目标并嘲讽 3 秒；有守势时嘲讽时间 +1 秒。",
      "横扫当前一路最多 3 名敌人并击退；消耗 1 层守势时降低目标攻击 3 秒。",
      "获得护盾并嘲讽当前目标 3 秒；消耗全部守势提高护盾。",
    ],
    passive: [
      "前排时近战受伤 -10%；受近战伤害获得守势，最多 3 层，每层近战受伤 -6%。",
      "张飞小兵近战受伤 -10%；张飞拥有守势时额外 -8%。",
      "生命低于 40% 时立即获得 3 层守势，12 秒冷却。",
    ],
  },
  赵云: {
    active: [
      "突击当前目标；消耗 1 层游龙时追加枪影伤害。",
      "攻击当前区域最多 3 名敌人；消耗 2 层游龙时每名敌人受 2 次伤害。",
      "援护最低血友方队长；消耗 1 层游龙时为其提供护盾。",
    ],
    passive: [
      "闪避 +15%；成功闪避时获得游龙，最多 3 层。",
      "侧翼时闪避 +8%，普攻速度 +12%。",
      "消耗游龙后闪避 +7%、普攻速度 +15%，持续 4 秒；3 层游龙时普攻速度 +20%。",
    ],
  },
  夏侯惇: {
    active: [
      "攻击当前目标并获得护盾；拥有刚烈时提高护盾。",
      "获得 2 层刚烈并攻击当前目标；若满 4 层，立即反斩。",
      "反扑当前一路最多 3 名敌人并击退；每层刚烈提高伤害，释放后消耗全部刚烈。",
    ],
    passive: [
      "受近战伤害获得刚烈，最多 4 层；满层时自动反斩。",
      "前排时击退效果 -50%；拥有刚烈时近战受伤 -8%。",
      "触发反斩后，下一次主动技能伤害 +20%。",
    ],
  },
  刘备: {
    active: [
      "治疗最低血友方队长；消耗 1 层仁德时提高治疗量。",
      "为最低血友方队长提供护盾；消耗 1 层仁德时提高护盾。",
      "治疗全体友方队长并清除 1 个普通减益；消耗全部仁德提高治疗量。",
    ],
    passive: [
      "友方队长低于 40% 生命时获得仁德；后排时远程受伤降低。",
      "释放主动后，使最低血友方队长持续恢复 6 秒；有仁德时延长。",
      "友方队长低于 30% 生命时获得护盾，12 秒冷却。",
    ],
  },
  诸葛亮: {
    active: [
      "攻击当前区域最多 4 名敌人并降低攻击 3 秒；消耗 1 层谋略时提高伤害。",
      "攻击当前一路最多 5 名敌人；消耗 1 层谋略时额外降低目标移速 3 秒。",
      "攻击当前区域最多 4 名敌人并眩晕 1 秒；消耗全部谋略提高伤害。",
    ],
    passive: [
      "后排时每 4 秒获得 1 层谋略，最多 3 层。",
      "后排时远程受伤 -12%；拥有谋略时主动法术伤害 +8%。",
      "生命低于 35% 时获得护盾并获得 1 层谋略，12 秒冷却。",
    ],
  },
  司马懿: {
    active: [
      "对指定队长造成 240% 法术伤害，并使其受到司马懿伤害 +12%；定局时强化。",
      "对指定队长造成 120% 法术伤害，并使其伤害 -20%、攻速 -25%，持续 5 秒；定局时强化。",
      "对指定队长造成 300% 法术伤害；目标有鹰视/缚心时提高至 450%；定局时强化。",
    ],
    passive: [
      "每释放 1 次主动技能，获得 1 层筹谋，最多 3 层。",
      "首次低于 45% 生命时，获得 25% 最大生命护盾，持续 8 秒；每波 1 次。",
      "进入定局时，小队远程兵对敌方队长伤害 +25%，持续 6 秒。",
    ],
  },
  甘宁: {
    active: [
      "对指定队长连续射击 3 次，每次 85% 物理伤害；满膛时 5 次、每次 95%。",
      "对指定队长造成 180% 物理伤害，并使其伤害 -20%、攻速 -25%，持续 5 秒；满膛时强化。",
      "对指定队长造成 250% 物理伤害；目标低于 35% 生命时提高至 450%；满膛时强化。",
    ],
    passive: [
      "每普攻命中 3 次获得 1 层火药，最多 3 层。",
      "侧翼时闪避 +8%，攻击速度 +15%。",
      "主动命中队长后，小队近战兵对该队长伤害 +25%，持续 6 秒。",
    ],
  },
  曹仁: {
    active: [
      "对当前目标造成 180% 物理伤害；若目标是队长/精英，嘲讽 3 秒。",
      "攻击当前区域最多 3 名敌人，各造成 120% 物理伤害；守备 >=3 层时，队长/精英攻击 -20%，持续 5 秒。",
      "消耗全部守备，为全军提供护盾；每层守备提供 5% 最大生命护盾，持续 7 秒。",
    ],
    passive: [
      "启用守备：小兵阵亡或每 6 秒获得 1 层，最多 5 层；前排时近战受伤 -10%。",
      "每波首次达到 3 层守备时，所有小兵受伤 -10%，持续本波。",
      "每波首次达到 5 层守备时，全体队长受伤 -10%，小兵受伤 -15%，持续 6 秒。",
    ],
  },
  典韦: {
    active: [
      "对当前目标造成 190% 物理伤害；若目标是队长/精英，攻击 -15%，持续 4 秒。",
      "攻击当前区域最多 3 名敌人，各造成 120% 物理伤害；死战 >=2 层时，每名额外受 60% 物理伤害。",
      "消耗全部死战，攻击低血队长/精英：造成 240% + 每层 45% 物理伤害。",
    ],
    passive: [
      "启用死战：生命降至 75%/50%/25% 时获得层数，最多 3 层；每层攻击 +5%；前排时近战受伤 -8%。",
      "每层死战使控制持续时间 -10%，最多 -30%。",
      "每波首次获得 3 层死战时，清除 1 个减益并受伤 -15%，持续 6 秒。",
    ],
  },
  张辽: {
    active: [
      "对当前目标造成 190% 物理伤害。",
      "攻击震慑目标及区域内最多 2 名额外敌人，各造成 120% 物理伤害；震慑目标额外受 80% 并 +1 层震慑。",
      "消耗全部震慑，对目标造成 260% + 每层 45% 物理伤害；满层为 395%。",
    ],
    passive: [
      "主动命中队长/精英时施加震慑，最多 3 层；每层使其对其他友军伤害 -4%；侧翼时攻击 +10%、远程受伤 -10%。",
      "敌方队长/精英首次达到 3 层震慑时，物理防御 -12，持续 6 秒。",
      "消耗 3 层震慑后，张辽攻击 +15%，本队近战兵对队长/精英伤害 +15%，持续 6 秒。",
    ],
  },
  马超: {
    active: [
      "对当前目标造成 195% 物理伤害；若目标是队长/精英，额外造成 45% 物理伤害。",
      "贯穿当前一路最多 4 名敌人，各造成 115% 物理伤害；冲势 >=2 层时，每名额外受 45% 物理伤害。",
      "消耗全部冲势，攻击低血队长/精英：造成 250% + 每层 45% 物理伤害。",
    ],
    passive: [
      "启用冲势：每波开始和敌方小兵死亡时获得层数，最多 3 层；每层攻击 +4%，满层攻速 +10%；侧翼时攻速 +15%。",
      "每波首次达到 3 层冲势时，马超攻速 +15%，本队近战兵攻速 +10%，持续 6 秒。",
      "消耗 3 层冲势后，目标物防 -12，本队近战兵对该目标伤害 +15%，持续 6 秒。",
    ],
  },
  荀彧: {
    active: [
      "攻击敌方高攻击队长/精英，造成 175% 法术伤害，并使其伤害 -15%，持续 5 秒。",
      "为最低血的至多 2 名友方队长提供 12% 最大生命护盾；政令 >=2 层时受伤 -10%，持续 5 秒。",
      "消耗全部政令，使所有队长攻击 +15%，并清除 1 个普通减益，持续 7 秒。",
    ],
    passive: [
      "启用政令：每波开始 2 层，此后每 8 秒 +1 层，最多 3 层；后排时远程受伤 -12%。",
      "每波首次达到 3 层政令时，所有队长受伤 -8%，持续 6 秒。",
      "消耗 3 层政令后，所有小兵攻速 +15%，对队长/精英伤害 +10%，持续 6 秒。",
    ],
  },
  太史慈: {
    active: [
      "攻击范围内低血队长/精英，造成 190% 物理伤害。",
      "攻击战书目标，造成 170% 物理伤害，物理防御 -12，持续 5 秒，并刷新战书。",
      "战书目标低于 50% 生命时造成 300% 物理伤害；低于 40% 时额外造成 110%。",
    ],
    passive: [
      "启用战书：主动命中队长/精英时施加；太史慈对战书目标伤害 +12%；侧翼时攻速 +10%、远程受伤 -8%。",
      "首次对队长/精英施加战书时，本队近战兵对其伤害 +15%，持续 6 秒。",
      "对同一目标维持战书 6 秒后，清除 1 个减益，攻击 +15%、受伤 -12%，持续 6 秒。",
    ],
  },
  孙尚香: {
    active: [
      "对当前目标造成 180% 物理伤害。",
      "场上有悬剑时，每柄悬剑对其目标造成 90% 物理伤害。",
      "3 柄悬剑集中于同一队长/精英时全部召回，合计造成 375% 物理伤害。",
    ],
    passive: [
      "启用三才游剑：最多 3 柄悬剑；后排时远程受伤 -12%。",
      "同一敌人首次被至少 2 柄悬剑悬停时，物理防御 -10，持续 6 秒。",
      "每波首次 3 柄悬剑分布于至少 2 名敌人时，每柄额外造成 110% 物理伤害。",
    ],
  },
  夏侯渊: {
    active: [
      "对当前目标造成 185% 物理伤害。",
      "攻击猎印目标及同路最多 3 名额外敌人，各造成 115% 物理伤害；猎印目标额外受 80%。",
      "消耗全部猎机，攻击低血队长/精英：造成 250% + 每层 45% 物理伤害。",
    ],
    passive: [
      "启用追猎：猎印结束或目标死亡时获得猎机，最多 3 层；每层对队长/精英伤害 +5%；中后排时攻速 +12%。",
      "每波首次达到 3 层猎机时，夏侯渊攻速 +15%，本队远程兵攻速 +10%，持续 6 秒。",
      "同一队长/精英被猎印锁定满 4 秒时，对其伤害 +20%，本队远程兵对其伤害 +10%，持续 6 秒。",
    ],
  },
};

function buildDescriptionRow(key, abilityId, type, description) {
  return [key, abilityId, type, description, ...Array(10).fill(description)];
}

const unitWorkbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load(unitSkillsPath),
);
const unitSheet = unitWorkbook.worksheets.getItem("config_单位技能配置表");
const unitRows = unitSheet.getRange("A5:J23").values;

const descriptionRows = [];
const skillIdOwners = new Map();
let key = 1;

for (const row of unitRows) {
  const heroName = row[0];
  if (heroName === "玩家") {
    continue;
  }

  const definitions = heroSkills[heroName];
  if (!definitions) {
    throw new Error(`缺少 ${heroName} 的简短技能描述。`);
  }

  const activeIds = row.slice(2, 5);
  const activeEmptyId = row[5];
  const passiveIds = row.slice(6, 9);
  const passiveEmptyId = row[9];

  if (activeEmptyId !== emptyAbilityId || passiveEmptyId !== emptyAbilityId) {
    throw new Error(`${heroName} 的技能4或技能8不是约定的空技能 ID。`);
  }

  for (let index = 0; index < 3; index += 1) {
    const abilityId = activeIds[index];
    if (abilityId === emptyAbilityId || abilityId === null) {
      throw new Error(`${heroName} 的主动技能${index + 1}缺少有效 ID。`);
    }
    if (skillIdOwners.has(abilityId)) {
      throw new Error(`技能 ID ${abilityId} 被重复使用：${skillIdOwners.get(abilityId)} / ${heroName} 主动${index + 1}`);
    }
    skillIdOwners.set(abilityId, `${heroName} 主动${index + 1}`);
    descriptionRows.push(buildDescriptionRow(key, abilityId, "主动", definitions.active[index]));
    key += 1;
  }

  for (let index = 0; index < 3; index += 1) {
    const abilityId = passiveIds[index];
    if (abilityId === emptyAbilityId || abilityId === null) {
      throw new Error(`${heroName} 的被动技能${index + 1}缺少有效 ID。`);
    }
    if (skillIdOwners.has(abilityId)) {
      throw new Error(`技能 ID ${abilityId} 被重复使用：${skillIdOwners.get(abilityId)} / ${heroName} 被动${index + 1}`);
    }
    skillIdOwners.set(abilityId, `${heroName} 被动${index + 1}`);
    descriptionRows.push(buildDescriptionRow(key, abilityId, "被动", definitions.passive[index]));
    key += 1;
  }
}

if (descriptionRows.length !== 108) {
  throw new Error(`预期生成 108 行技能描述，实际生成 ${descriptionRows.length} 行。`);
}

const descriptionWorkbook = await SpreadsheetFile.importXlsx(
  await FileBlob.load(descriptionsPath),
);
const descriptionSheet = descriptionWorkbook.worksheets.getItem("config_技能作用描述表");
const finalRow = 4 + descriptionRows.length;

descriptionSheet.getRange(`A5:N${finalRow}`).values = descriptionRows;
descriptionSheet.getRange(`D2:N${finalRow}`).format.wrapText = true;
descriptionSheet.getRange(`D2:N${finalRow}`).format.columnWidth = 20;
descriptionSheet.getRange(`A5:N${finalRow}`).format.autofitRows();

const checkRange = descriptionSheet.getRange(`A5:N${finalRow}`).values;
if (checkRange.length !== 108 || checkRange.some((row) => row.length !== 14)) {
  throw new Error("技能描述表写入后的行列数不正确。");
}
if (checkRange.some((row) => row[1] === emptyAbilityId || !row[3] || !row[4])) {
  throw new Error("写入结果包含空技能 ID 或缺失描述。");
}

const output = await SpreadsheetFile.exportXlsx(descriptionWorkbook);
await output.save(descriptionsPath);

const reloaded = await SpreadsheetFile.importXlsx(await FileBlob.load(descriptionsPath));
const verification = await reloaded.inspect({
  kind: "table",
  range: "A1:N12",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 14,
  tableMaxCellChars: 120,
});
await fs.writeFile(
  "D:/codex/project01/.tmp/skill-description-config/final-inspect.txt",
  verification.ndjson,
  "utf8",
);

const errors = await reloaded.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
await fs.writeFile(
  "D:/codex/project01/.tmp/skill-description-config/final-errors.txt",
  errors.ndjson,
  "utf8",
);

const previewTop = await reloaded.render({
  sheetName: "config_技能作用描述表",
  range: "A1:E12",
  scale: 1.25,
  format: "png",
});
await fs.writeFile(
  "D:/codex/project01/.tmp/skill-description-config/final-preview-top.png",
  new Uint8Array(await previewTop.arrayBuffer()),
);

const previewBottom = await reloaded.render({
  sheetName: "config_技能作用描述表",
  range: "A101:N112",
  scale: 1.25,
  format: "png",
});
await fs.writeFile(
  "D:/codex/project01/.tmp/skill-description-config/final-preview-bottom.png",
  new Uint8Array(await previewBottom.arrayBuffer()),
);

console.log(JSON.stringify({
  rowsWritten: descriptionRows.length,
  uniqueAbilityIds: skillIdOwners.size,
  finalRow,
  output: descriptionsPath,
}));
