import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.cwd();
const configDir = path.join(root, "deliverables", "config-file");
const files = ["config_单位列表.xlsx", "config_关卡怪物部署表-关卡1-出怪表.xlsx"];

function compactRows(values) {
  return values
    .map((row, index) => ({ row: index + 1, values: row }))
    .filter(({ values }) => values.some((value) => value !== null && value !== "" && value !== undefined));
}

for (const fileName of files) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(configDir, fileName)));
  const sheet = workbook.worksheets.getItemAt(0);
  const range = fileName.includes("单位列表") ? "A1:S160" : "A1:AY400";
  const values = sheet.getRange(range).values;
  console.log(`FILE=${fileName}`);
  console.log(`SHEET=${sheet.name}`);
  console.log(JSON.stringify(compactRows(values)));
}
