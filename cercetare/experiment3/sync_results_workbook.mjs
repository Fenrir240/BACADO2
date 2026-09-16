import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const [csvPath, workbookPath, nodeModulesPath] = process.argv.slice(2);
if (!csvPath || !workbookPath || !nodeModulesPath) {
  throw new Error(
    "Utilizare: node sync_results_workbook.mjs <csv> <xlsx> <node_modules>",
  );
}

const lockPath = path.join(
  path.dirname(workbookPath),
  `~$${path.basename(workbookPath)}`,
);
try {
  await fs.access(lockPath);
  throw new Error(
    `Fișierul Excel este deschis (${lockPath}). Închide-l în Excel/WPS și reia sincronizarea.`,
  );
} catch (error) {
  if (error?.code !== "ENOENT") throw error;
}

const resolver = createRequire(path.join(nodeModulesPath, "__codex_resolver__.cjs"));
const artifactEntry = resolver.resolve("@oai/artifact-tool");
const { FileBlob, SpreadsheetFile, Workbook } = await import(
  pathToFileURL(artifactEntry).href
);

const csvText = await fs.readFile(csvPath, "utf8");
const csvWorkbook = await Workbook.fromCSV(csvText, { sheetName: "CSV" });
const csvSheet = csvWorkbook.worksheets.getItem("CSV");
const csvValues = csvSheet.getUsedRange().values;
if (!csvValues?.length) throw new Error(`CSV-ul nu conține antet: ${csvPath}`);

const workbookExists = await fs.access(workbookPath).then(() => true, () => false);
const workbook = workbookExists
  ? await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath))
  : Workbook.create();
const sheet = workbook.worksheets.getOrAdd("Rezultate editabile", {
  renameFirstIfOnlyNewSpreadsheet: true,
});

const normalizeHeader = (value) => String(value ?? "")
  .trim()
  .toLocaleLowerCase("ro-RO")
  .normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "");

const observationsByRunId = new Map();
const existingRange = sheet.getUsedRange();
const existingValues = existingRange?.values ?? [];
if (existingValues.length > 1) {
  const existingHeaders = existingValues[0].map(normalizeHeader);
  const existingRunIdIndex = existingHeaders.indexOf("run_id");
  const observationIndex = existingHeaders.findIndex((header) =>
    ["observatii", "observatie", "note", "notes"].includes(header),
  );
  if (existingRunIdIndex >= 0 && observationIndex >= 0) {
    for (const row of existingValues.slice(1)) {
      const runId = String(row[existingRunIdIndex] ?? "").trim();
      if (runId) observationsByRunId.set(runId, row[observationIndex] ?? "");
    }
  }
}

const csvHeaders = csvValues[0].map((value) => String(value ?? "").trim());
const runIdIndex = csvHeaders.indexOf("run_id");
if (runIdIndex < 0) throw new Error("CSV-ul nu conține coloana run_id.");

const headers = [...csvHeaders, "observatii"];
const rows = csvValues.slice(1).map((sourceRow) => {
  const row = [...sourceRow];
  if (typeof row[0] === "string" && row[0].trim()) {
    const parsedDate = new Date(row[0]);
    if (!Number.isNaN(parsedDate.valueOf())) row[0] = parsedDate;
  }
  for (const index of [4, 5, 6]) {
    const parsedNumber = Number(row[index]);
    if (row[index] !== "" && Number.isFinite(parsedNumber)) row[index] = parsedNumber;
  }
  for (const index of [7, 8]) {
    if (typeof row[index] === "string") {
      const normalized = row[index].toLowerCase();
      if (normalized === "true") row[index] = true;
      else if (normalized === "false") row[index] = false;
    }
  }
  const runId = String(row[runIdIndex] ?? "").trim();
  return [...row, observationsByRunId.get(runId) ?? ""];
});

for (const table of [...sheet.tables.items]) table.delete();
if (existingRange) existingRange.clear({ applyTo: "all" });

const lastRow = Math.max(1, rows.length + 1);
sheet.getRange(`A1:N${lastRow}`).values = [headers, ...rows];
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
sheet.getRange(`A1:N${lastRow}`).format = {
  font: { name: "Aptos", size: 10, color: "#172033" },
  verticalAlignment: "top",
};
sheet.getRange("A1:N1").format = {
  fill: "#1F4E78",
  font: { name: "Aptos Display", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
sheet.getRange("A1:N1").format.rowHeight = 34;

if (rows.length) {
  sheet.getRange(`A2:N${lastRow}`).format.rowHeight = 42;
  sheet.getRange(`A2:I${lastRow}`).format.verticalAlignment = "center";
  sheet.getRange(`H2:I${lastRow}`).format.horizontalAlignment = "center";
  sheet.getRange(`J2:N${lastRow}`).format.wrapText = true;
  sheet.getRange(`A2:A${lastRow}`).format.numberFormat = "yyyy-mm-dd hh:mm:ss";
  sheet.getRange(`E2:G${lastRow}`).format.numberFormat = "0.000";
  sheet.getRange(`N2:N${lastRow}`).format = {
    fill: "#FFF2CC",
    font: { name: "Aptos", size: 10, color: "#5F4700" },
    verticalAlignment: "top",
    wrapText: true,
  };
}

const widths = {
  A: 28, B: 23, C: 40, D: 18, E: 16, F: 16, G: 16,
  H: 18, I: 18, J: 48, K: 62, L: 62, M: 42, N: 46,
};
for (const [column, width] of Object.entries(widths)) {
  sheet.getRange(`${column}:${column}`).format.columnWidth = width;
}

const table = sheet.tables.add(`A1:N${lastRow}`, true, "RezultateExperimentEditabile");
table.style = "TableStyleMedium2";
table.showFilterButton = true;
table.showBandedRows = true;

const notes = workbook.worksheets.getOrAdd("Instructiuni");
const notesRange = notes.getUsedRange();
if (notesRange) notesRange.clear({ applyTo: "all" });
notes.showGridLines = false;
notes.getRange("A1:B1").values = [["Registru Excel sincronizat automat", null]];
notes.getRange("A1:B1").format = {
  fill: "#1F4E78",
  font: { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" },
  verticalAlignment: "center",
};
notes.getRange("A1:B1").format.rowHeight = 36;
notes.getRange("A3:B8").values = [
  ["Scop", "Registru editabil al rulărilor din Experimentul 3."],
  ["Sursa", "experiment3/results/rezultate-experiment.csv"],
  ["Actualizare", "Runnerul inserează sau actualizează automat rândurile după run_id."],
  ["Observații", "Scrie numai în coloana galbenă observatii; conținutul ei este păstrat la sincronizare."],
  ["Fișier deschis", "Închide registrul în Excel/WPS înaintea unei rulări, altfel sincronizarea este amânată."],
  ["Salvare", "Folosește Ctrl+S și păstrează formatul Excel Workbook (.xlsx)."],
];
notes.getRange("A3:A8").format = {
  fill: "#D9EAF7",
  font: { bold: true, color: "#17365D" },
  verticalAlignment: "top",
};
notes.getRange("B3:B8").format = { wrapText: true, verticalAlignment: "top" };
notes.getRange("A:A").format.columnWidth = 18;
notes.getRange("B:B").format.columnWidth = 82;
notes.getRange("A3:B8").format.rowHeight = 36;

await fs.mkdir(path.dirname(workbookPath), { recursive: true });
const temporaryPath = path.join(
  path.dirname(workbookPath),
  `.${path.basename(workbookPath)}.${Date.now()}.tmp.xlsx`,
);
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(temporaryPath);
try {
  await fs.copyFile(temporaryPath, workbookPath);
} finally {
  await fs.rm(temporaryPath, { force: true });
  await fs.rm(`${temporaryPath}.inspect.ndjson`, { force: true });
}

console.log(`OUTPUT=${workbookPath}`);
