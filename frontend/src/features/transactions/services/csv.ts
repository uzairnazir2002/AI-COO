export type CsvField = "date" | "amount" | "type" | "category" | "vendor" | "notes" | "location";
export type CsvMapping = Record<CsvField, string>;
export type CsvRawRow = Record<string, string>;

export const csvFields: Array<{ key: CsvField; label: string; required: boolean }> = [
  { key: "date", label: "Date", required: true },
  { key: "amount", label: "Amount", required: true },
  { key: "type", label: "Type", required: true },
  { key: "category", label: "Category", required: true },
  { key: "vendor", label: "Vendor", required: false },
  { key: "notes", label: "Notes", required: false },
  { key: "location", label: "Location", required: false },
];

const defaultCsvMaxBytes = 5 * 1024 * 1024;
export const csvMaxBytes = Number(process.env.NEXT_PUBLIC_CSV_MAX_BYTES || defaultCsvMaxBytes);

function normalizeHeader(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
}

export function parseCsvContent(text: string): { headers: string[]; rows: CsvRawRow[] } {
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length === 0) return { headers: [], rows: [] };
  const headers = lines[0].split(",").map((h) => h.trim());
  const rows = lines.slice(1).map((line) => {
    const cells = line.split(",");
    const row: CsvRawRow = {};
    headers.forEach((header, idx) => {
      row[header] = (cells[idx] ?? "").trim();
    });
    return row;
  });
  return { headers, rows };
}

export function autoDetectMapping(headers: string[]): CsvMapping {
  const normalized = headers.map((h) => ({ original: h, normalized: normalizeHeader(h) }));
  const pick = (...aliases: string[]) => normalized.find((item) => aliases.includes(item.normalized))?.original ?? "";
  return {
    date: pick("date", "transactiondate", "posteddate"),
    amount: pick("amount", "value", "total"),
    type: pick("type", "transactiontype", "kind"),
    category: pick("category", "group", "expensecategory"),
    vendor: pick("vendor", "merchant", "payee", "supplier"),
    notes: pick("notes", "note", "memo", "description"),
    location: pick("location", "branch", "store", "site", "office", "locationcode"),
  };
}

export function mappingToApiPayload(mapping: CsvMapping): Record<string, string> {
  return {
    date: mapping.date,
    amount: mapping.amount,
    type: mapping.type,
    category: mapping.category,
    vendor: mapping.vendor || "",
    notes: mapping.notes || "",
    location: mapping.location || "",
  };
}

