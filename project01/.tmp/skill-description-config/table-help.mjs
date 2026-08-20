import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const input = await FileBlob.load(
  "D:/codex/project01/deliverables/config-file/config_技能作用描述表.xlsx",
);
const workbook = await SpreadsheetFile.importXlsx(input);
const help = workbook.help("table", {
  include: "index,examples,notes",
  maxChars: 5000,
});
console.log(help.ndjson);
