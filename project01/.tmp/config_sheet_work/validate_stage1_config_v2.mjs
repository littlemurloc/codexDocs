import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.cwd();
const sourceDir = path.join(root, "deliverables", "config-file");
const unitFile = "config_单位列表.xlsx";
const deploymentFile = "config_关卡怪物部署表-关卡1-出怪表.xlsx";
const requiredHeroIds = new Set([134267035, 134249908, 134235822, 134268301, 134260324, 134264969, 134219460, 134276481]);

const unitWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(sourceDir, unitFile)));
const unitSheet = unitWorkbook.worksheets.getItemAt(0);
const unitRows = unitSheet.getRange("A5:R38").values;
const unitTypes = new Set(unitRows.map((row) => Number(row[2])));

const deploymentWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(sourceDir, deploymentFile)));
const deploymentSheet = deploymentWorkbook.worksheets.getItemAt(0);
const rows = deploymentSheet.getRange("A5:AY193").values;
const byDifficulty = new Map();
const deployedNewHeroes = new Set();
const tierByDifficulty = new Map();

for (const row of rows) {
  const difficulty = Number(row[1]);
  if (!byDifficulty.has(difficulty)) byDifficulty.set(difficulty, []);
  const activeGroups = [];
  const usedSlots = new Set();
  for (let groupIndex = 0; groupIndex < 9; groupIndex += 1) {
    const start = 6 + groupIndex * 5;
    const leader = Number(row[start]);
    const slot = Number(row[start + 1]);
    const tier = String(row[start + 2]);
    const soldier = Number(row[start + 3]);
    const soldierCount = Number(row[start + 4]);
    if (leader !== 0) {
      if (!unitTypes.has(leader) || !unitTypes.has(soldier)) throw new Error(`Unknown type in D${difficulty}.`);
      if (soldierCount < 1 || soldierCount > 8) throw new Error(`Invalid soldier count in D${difficulty}.`);
      if (slot < 1 || slot > 9 || usedSlots.has(slot)) throw new Error(`Invalid slot in D${difficulty}.`);
      usedSlots.add(slot);
      activeGroups.push({ leader, slot, tier, soldierCount });
      if (requiredHeroIds.has(leader)) deployedNewHeroes.add(leader);
    }
  }
  byDifficulty.get(difficulty).push(activeGroups);
}

const expected = [4, 5, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
const summary = [];
for (let difficulty = 1; difficulty <= 15; difficulty += 1) {
  const waves = byDifficulty.get(difficulty) ?? [];
  if (waves.length !== expected[difficulty - 1]) throw new Error(`D${difficulty} expected ${expected[difficulty - 1]} waves, got ${waves.length}.`);
  const totalGroups = waves.reduce((total, groups) => total + groups.length, 0);
  const totalSoldiers = waves.reduce((total, groups) => total + groups.reduce((subtotal, group) => subtotal + group.soldierCount, 0), 0);
  const maxGroups = Math.max(...waves.map((groups) => groups.length));
  const maxSoldiers = Math.max(...waves.flat().map((group) => group.soldierCount));
  const tiers = [...new Set(waves.flat().map((group) => group.tier))].sort();
  summary.push({ difficulty, waves: waves.length, avgGroups: Number((totalGroups / waves.length).toFixed(2)), avgSoldiers: Number((totalSoldiers / waves.length).toFixed(2)), maxGroups, maxSoldiers, tiers });
}

const errors = await deploymentWorkbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  maxChars: 4000,
});
console.log(JSON.stringify({
  unitCount: unitRows.length,
  waveCount: rows.length,
  deployedNewHeroCount: deployedNewHeroes.size,
  missingNewHeroIds: [...requiredHeroIds].filter((heroId) => !deployedNewHeroes.has(heroId)),
  difficultySummary: summary,
  formulaErrors: errors.ndjson,
}, null, 2));
