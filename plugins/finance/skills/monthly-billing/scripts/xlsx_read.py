"""Read-only .xlsx access with the standard library (zipfile + xml), shaped like the small part of openpyxl the
billing script uses: load_workbook(path, data_only) -> wb.sheetnames, wb[name] -> ws.cell(r, c).value, ws["A1"],
ws[row], ws.iter_rows(min_row=), ws.max_row, ws.max_column; plus the column-letter helpers.

data_only=True gives the values cached in the file (what a Google Sheets export holds); data_only=False gives
formulas as "=..." and plain values otherwise. Shared formulas are expanded for each cell.
"""
import re
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "pr": "http://schemas.openxmlformats.org/package/2006/relationships"}
REF = re.compile(r"(\$?)([A-Z]{1,3})(\$?)(\d+)")


def column_index_from_string(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def get_column_letter(n):
    s = ""
    while n:
        n, rem = divmod(n - 1, 26)
        s = chr(65 + rem) + s
    return s


def coordinate_from_string(a1):
    m = re.fullmatch(r"\$?([A-Z]{1,3})\$?(\d+)", a1)
    if not m:
        raise ValueError(f"not a cell reference: {a1}")
    return m.group(1), int(m.group(2))


class Cell:
    __slots__ = ("row", "column", "value")

    def __init__(self, row, column, value=None):
        self.row, self.column, self.value = row, column, value

    @property
    def column_letter(self):
        return get_column_letter(self.column)

    @property
    def coordinate(self):
        return f"{self.column_letter}{self.row}"


class Worksheet:
    def __init__(self, title, cells):
        self.title = title
        self._cells = cells  # (row, col) -> value
        self.max_row = max((r for r, _ in cells), default=1)
        self.max_column = max((c for _, c in cells), default=1)

    def cell(self, row, column):
        return Cell(row, column, self._cells.get((row, column)))

    def __getitem__(self, key):
        if isinstance(key, int):  # a whole row, like openpyxl's ws[1]
            return tuple(self.cell(key, c) for c in range(1, self.max_column + 1))
        col, row = coordinate_from_string(key)
        return self.cell(row, column_index_from_string(col))

    def iter_rows(self, min_row=1, max_row=None, values_only=False):
        for r in range(min_row, (max_row or self.max_row) + 1):
            row = self[r]
            yield tuple(c.value for c in row) if values_only else row


class Workbook:
    def __init__(self, sheets):
        self._sheets = sheets  # ordered name -> Worksheet
        self.sheetnames = list(sheets)

    def __getitem__(self, name):
        return self._sheets[name]


def _number(text):
    try:
        f = float(text)
    except ValueError:
        return text
    return int(f) if f.is_integer() and not re.search(r"[.eE]", text) else f


def _shift(formula, drow, dcol):
    """Move the relative references of a shared formula by (drow, dcol); $-anchored parts stay."""
    def move(m):
        c_abs, col, r_abs, row = m.groups()
        col = col if c_abs else get_column_letter(column_index_from_string(col) + dcol)
        row = row if r_abs else str(int(row) + drow)
        return f"{c_abs}{col}{r_abs}{row}"
    out, quoted = [], False
    for part in re.split(r'("[^"]*")', formula):  # leave string literals alone
        out.append(part if part.startswith('"') else REF.sub(move, part))
    return "".join(out)


def load_workbook(path, data_only=False):
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        strings = []
        if "xl/sharedStrings.xml" in names:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                strings.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        rels = {}
        for rel in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).findall("pr:Relationship", NS):
            target = rel.get("Target").lstrip("/")
            rels[rel.get("Id")] = target if target.startswith("xl/") else "xl/" + target
        sheets = {}
        for sh in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", NS).findall("m:sheet", NS):
            path_in_zip = rels[sh.get(f"{{{NS['r']}}}id")]
            sheets[sh.get("name")] = Worksheet(sh.get("name"), _cells(z.read(path_in_zip), strings, data_only))
    return Workbook(sheets)


def _cells(xml, strings, data_only):
    cells, shared = {}, {}
    root = ET.fromstring(xml)
    for c in root.iter(f"{{{NS['m']}}}c"):
        col, row = coordinate_from_string(c.get("r"))
        col = column_index_from_string(col)
        t = c.get("t", "n")
        f, v = c.find("m:f", NS), c.find("m:v", NS)
        formula = None
        if f is not None:
            if f.get("t") == "shared":
                si = f.get("si")
                if f.text:  # the master cell of a shared formula
                    shared[si] = (f.text, row, col)
                    formula = f.text
                elif si in shared:
                    text, r0, c0 = shared[si]
                    formula = _shift(text, row - r0, col - c0)
            elif f.text:
                formula = f.text
        if formula is not None and not data_only:
            cells[(row, col)] = "=" + formula
            continue
        if t == "inlineStr":
            value = "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
        elif v is None or v.text is None:
            continue
        elif t == "s":
            value = strings[int(v.text)]
        elif t in ("str", "e"):
            value = v.text
        elif t == "b":
            value = v.text == "1"
        else:
            value = _number(v.text)
        cells[(row, col)] = value
    return cells
