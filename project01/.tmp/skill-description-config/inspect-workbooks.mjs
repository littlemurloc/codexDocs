import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const baseDir = "D:/codex/project01/deliverables/config-file";
const outputDir = "D:/codex/project01/.tmp/skill-description-config";
const files = [
  "config_单位技能配置表.xlsx",
  "config_军令卡牌技能表.xlsx",
  "config_技能作用描述表.xlsx",
];

for (const fileName of files) {
  const input = await FileBlob.load(`${baseDir}/${fileName}`);
  const workbook = await SpreadsheetFile.importXlsx(input);
  const summary = await workbook.inspect({
    kind: "workbook,sheet,table,computedStyle",
    maxChars: 14000,
    tableMaxRows: 80,
    tableMaxCols: 20,
    tableMaxCellChars: 160,
  });
  await fs.writeFile(
    `${outputDir}/${fileName}.inspect.txt`,
    summary.ndjson,
    "utf8",
  );

  const sheet = workbook.worksheets.getItemAt(0);
  const used = sheet.getUsedRange();
  const address = used.address ?? "A1:Z100";
  const preview = await workbook.render({
    sheetName: sheet.name,
    range: address,
    scale: 1.5,
    format: "png",
  });
  await fs.writeFile(
    `${outputDir}/${fileName}.png`,
    new Uint8Array(await preview.arrayBuffer()),
  );
  console.log(`${fileName}\t${sheet.name}\t${address}`);
}
