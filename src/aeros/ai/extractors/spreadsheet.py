"""Spreadsheet extractor — handles xlsx, xls, csv, tsv."""

import csv
import io


async def extract_spreadsheet(file_path: str, **kwargs) -> str:
    if file_path.endswith((".csv", ".tsv")):
        return await _extract_csv(file_path)
    return await _extract_excel(file_path)


async def _extract_excel(file_path: str) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(file_path, data_only=True)
    parts = []

    for sheet in wb.sheetnames:
        ws = wb[sheet]
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            if any(c.strip() for c in cells):
                rows.append(" | ".join(cells))
        if rows:
            parts.append(f"Sheet: {sheet}\n" + "\n".join(rows))

    return "\n\n".join(parts) if parts else "[Empty spreadsheet]"


async def _extract_csv(file_path: str) -> str:
    with open(file_path, "r", newline="", encoding="utf-8", errors="replace") as f:
        content = f.read()

    try:
        dialect = csv.Sniffer().sniff(content[:2048])
    except csv.Error:
        dialect = None  # type: ignore[assignment]

    reader = csv.reader(io.StringIO(content), dialect) if dialect else csv.reader(io.StringIO(content))
    rows = []
    for row in reader:
        if any(c.strip() for c in row):
            rows.append(" | ".join(row))

    return "\n".join(rows) if rows else "[Empty CSV]"
