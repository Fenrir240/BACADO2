import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const here = path.dirname(fileURLToPath(import.meta.url));
const sourcePath = path.resolve(here, "../../results/rezultate-experiment.csv");
const outputPath = path.resolve(here, "../../results/rezultate-experiment-editabil.xlsx");
const csvText = await fs.readFile(sourcePath, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Rezultate editabile" });
const sheet = workbook.worksheets.getItem("Rezultate editabile");

sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
sheet.getRange("A1").values = [["timestamp_utc"]];
sheet.getUsedRange().format = {
  font: { name: "Aptos", size: 10, color: "#172033" },
  verticalAlignment: "top",
};
sheet.getRange("A1:M1").format = {
  fill: "#1F4E78",
  font: { name: "Aptos Display", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
sheet.getRange("A1:M1").format.rowHeight = 34;
sheet.getRange("A2:M4").format.rowHeight = 42;
sheet.getRange("A2:I4").format.verticalAlignment = "center";
sheet.getRange("J2:M4").format.wrapText = true;
sheet.getRange("A2:A4").format.numberFormat = "yyyy-mm-dd hh:mm:ss";
sheet.getRange("E2:G4").format.numberFormat = "0.000";
sheet.getRange("H2:I4").format.horizontalAlignment = "center";

const widths = {
  A: 28, B: 23, C: 40, D: 18, E: 16, F: 16, G: 16,
  H: 18, I: 18, J: 48, K: 62, L: 62, M: 42,
};
for (const [column, width] of Object.entries(widths)) {
  sheet.getRange(`${column}:${column}`).format.columnWidth = width;
}

const table = sheet.tables.add("A1:M4", true, "RezultateExperimentEditabile");
table.style = "TableStyleMedium2";
table.showFilterButton = true;
table.showBandedRows = true;

const notes = workbook.worksheets.add("Instructiuni");
notes.showGridLines = false;
notes.getRange("A1").values = [["Copie Excel complet editabila"]];
notes.getRange("A1:B1").format = {
  fill: "#1F4E78",
  font: { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" },
  verticalAlignment: "center",
};
notes.getRange("A1:B1").format.rowHeight = 36;
notes.getRange("A3:B7").values = [
  ["Scop", "Fisier Excel independent, editabil si compatibil cu WPS Office."],
  ["Sursa", "experiment2/results/rezultate-experiment.csv"],
  ["Editare", "Modifica liber foaia Rezultate editabile. Nu exista protectie sau parola."],
  ["Actualizare", "Rularile viitoare actualizeaza CSV-ul original, nu aceasta copie .xlsx."],
  ["Salvare", "In WPS Office foloseste Ctrl+S si pastreaza formatul Excel Workbook (.xlsx)."],
];
notes.getRange("A3:A7").format = {
  fill: "#D9EAF7",
  font: { bold: true, color: "#17365D" },
  verticalAlignment: "top",
};
notes.getRange("B3:B7").format = { wrapText: true, verticalAlignment: "top" };
notes.getRange("A:A").format.columnWidth = 18;
notes.getRange("B:B").format.columnWidth = 82;
notes.getRange("A3:B7").format.rowHeight = 36;

const check = await workbook.inspect({
  kind: "table",
  range: "Rezultate editabile!A1:M4",
  include: "values,formulas",
  tableMaxRows: 5,
  tableMaxCols: 13,
  maxChars: 5000,
});
console.log(check.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const preview = await workbook.render({
  sheetName: "Rezultate editabile",
  range: "A1:I4",
  scale: 1.5,
  format: "png",
});
await fs.writeFile(path.join(here, "preview.png"), new Uint8Array(await preview.arrayBuffer()));
const notesPreview = await workbook.render({
  sheetName: "Instructiuni",
  range: "A1:B7",
  scale: 1.5,
  format: "png",
});
await fs.writeFile(path.join(here, "preview-instructiuni.png"), new Uint8Array(await notesPreview.arrayBuffer()));

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`OUTPUT=${outputPath}`);
