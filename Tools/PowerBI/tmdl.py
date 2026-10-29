"""Helpers for generating TMDL (semantic model) files from Python: a calculated Date table, a measures
table, and reusable DAX patterns (previous period, trend labels/colours, tie-aware leaders).

The committed TMDL files are the source of truth. Use MeasuresTable / write_date_table to create these
tables for a model that doesn't have them yet. For an existing model, edit the .tmdl directly; the DAX
pattern functions return text you can paste or adapt. Scripts that use these helpers are throwaway (keep
them in the agent's session workspace, not the repo).

    import sys; sys.path.insert(0, "Tools/PowerBI")
    import tmdl as t

    mt = t.MeasuresTable("Example Measures")
    mt.add("Examples", "COUNTROWS ( Example )", fmt="#,0", folder="Examples", desc="Number of examples.")
    mt.add("Examples PP", t.previous_period("[Examples]"), fmt="#,0", folder="Previous Period", hidden=True)
    mt.add("Examples Trend Label", t.pct_change_label("[Examples]", "[Examples PP]"), folder="Labels", hidden=True)
    mt.write(TABLES_DIR)
    t.write_date_table(TABLES_DIR, "MIN ( Example[Created On] )", "MAX ( Example[Created On] )")

Safety: the write functions refuse to replace an existing file unless overwrite=True, and refuse to write
over uncommitted changes unless allow_dirty=True. After overwriting, check `git diff` shows only the
intended changes.

Lineage tags are uuid5-derived from table/object names, so regenerating keeps them stable. Files are written
with CRLF line endings and tab indentation, matching Power BI Desktop. Remember to add 'ref table' lines to
model.tmdl and any relationships to relationships.tmdl for new tables.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from _guard import require_clean

NS = uuid.UUID("6f1c6a3e-6c55-4d0e-9a59-4b6d1f0c2a11")
T = "\t"


def tag(name: str) -> str:
    """Deterministic lineage tag."""
    return str(uuid.uuid5(NS, name))


def _quote(name: str) -> str:
    return f"'{name}'" if any(c in name for c in " -%()") else name


def dax_block(expr: str, indent: int) -> list[str]:
    """Multi-line DAX in TMDL: expression lines indented one level deeper than the property."""
    return [T * indent + line if line.strip() else "" for line in expr.strip("\n").splitlines()]


def measure_lines(table, name, expr, fmt=None, folder=None, hidden=False, desc=None, category=None) -> list[str]:
    out = [f"{T}/// {desc}"] if desc else []
    expr = expr.strip("\n")
    if "\n" in expr:
        out.append(f"{T}measure {_quote(name)} =")
        out.extend(dax_block(expr, 3))
    else:
        out.append(f"{T}measure {_quote(name)} = {expr.strip()}")
    if fmt:
        out.append(f"{T}{T}formatString: {fmt}")
    if hidden:
        out.append(f"{T}{T}isHidden")
    if folder:
        out.append(f"{T}{T}displayFolder: {folder}")
    out.append(f"{T}{T}lineageTag: {tag(table + '/' + name)}")
    if category:
        out.append(f"{T}{T}dataCategory: {category}")
    out.append("")
    return out


def _write(path: Path, text: str, overwrite: bool = False, allow_dirty: bool = False):
    if path.exists():
        if not overwrite:
            raise FileExistsError(
                f"{path} already exists. The committed TMDL is the source of truth: edit it directly, or pass "
                "overwrite=True to replace it (then check git diff shows only the intended changes).")
        require_clean(path, allow_dirty)
    path.write_text(text, encoding="utf-8", newline="\r\n")


class MeasuresTable:
    """A measures-only table (calculated '{ 1 }' with a single hidden column), as Power BI Desktop creates them.

    Avoid '%' and other symbols in measure names: the model doc generator turns them into '_'.
    Use category='ImageUrl' for SVG measures shown as images in tables.
    """

    def __init__(self, name: str):
        self.name = name
        self.lines = [f"table {_quote(name)}", f"{T}lineageTag: {tag(name)}", ""]

    def add(self, name, expr, fmt=None, folder=None, hidden=False, desc=None, category=None):
        self.lines.extend(measure_lines(self.name, name, expr, fmt, folder, hidden, desc, category))

    def render(self) -> str:
        m = self.name
        tail = [
            f"{T}column Value", f"{T}{T}dataType: int64", f"{T}{T}isHidden", f"{T}{T}formatString: 0",
            f"{T}{T}lineageTag: {tag(m + '/Value')}", f"{T}{T}summarizeBy: none", f"{T}{T}isNameInferred",
            f"{T}{T}sourceColumn: [Value]", "", f"{T}{T}annotation SummarizationSetBy = Automatic", "",
            f"{T}partition {_quote(m)} = calculated", f"{T}{T}mode: import", f"{T}{T}source = {{ 1 }}", "",
            f"{T}annotation PBI_Id = {tag(m + '/PBI_Id').replace('-', '')}", "",
        ]
        return "\n".join(self.lines + tail) + "\n"

    def write(self, tables_dir: Path, overwrite: bool = False, allow_dirty: bool = False):
        _write(Path(tables_dir) / f"{self.name}.tmdl", self.render(), overwrite, allow_dirty)


# ------------------------------------------------------------------------------- Date table
def date_table(first_expr: str, last_expr: str,
               comment: str = "Whole calendar years spanning the data, extended to today so relative date slicers always work.") -> str:
    """Calculated, marked Date table: Date (key), Year, Month Number (hidden), Month, Month Start, Year Month,
    Slicer Date.

    first_expr / last_expr: DAX scalars for the earliest/latest dates in the data, e.g. 'MIN ( Fact[Created On] )'.
    Relate it to a date-only column on the fact (e.g. a calculated DATE ( YEAR(..), MONTH(..), DAY(..) ) column),
    not to a date/time column.

    Slicer Date is the field for relative date slicers ('Last 12 months'). Future dates count as today, so the
    slicer also includes upcoming (future-dated) records. TODAY () is evaluated at refresh.
    """
    L = ["table Date", f"{T}lineageTag: {tag('Date')}", f"{T}dataCategory: Time", ""]

    def col(name, expr=None, dtype="dateTime", fmt=None, hidden=False, sort_by=None, key=False, category=None, desc=None):
        if desc:
            L.append(f"{T}/// {desc}")
        L.append(f"{T}column {_quote(name)}" + (f" = {expr}" if expr else ""))
        L.append(f"{T}{T}dataType: {dtype}")
        if key:
            L.append(f"{T}{T}isKey")
        if hidden:
            L.append(f"{T}{T}isHidden")
        if fmt:
            L.append(f"{T}{T}formatString: {fmt}")
        L.append(f"{T}{T}lineageTag: {tag('Date/' + name)}")
        if category:
            L.append(f"{T}{T}dataCategory: {category}")
        L.append(f"{T}{T}summarizeBy: none")
        if not expr:
            L.append(f"{T}{T}isNameInferred")
            L.append(f"{T}{T}sourceColumn: [{name}]")
        if sort_by:
            L.append(f"{T}{T}sortByColumn: {sort_by}")
        L.extend(["", f"{T}{T}annotation SummarizationSetBy = Automatic", ""])

    col("Date", dtype="dateTime", fmt="dd/mm/yyyy", key=True)
    col("Year", "YEAR ( 'Date'[Date] )", dtype="int64", fmt="0", category="Years")
    col("Month Number", "MONTH ( 'Date'[Date] )", dtype="int64", fmt="0", hidden=True, category="MonthOfYear")
    col("Month", 'FORMAT ( \'Date\'[Date], "mmm" )', dtype="string", sort_by="'Month Number'", category="Months")
    col("Month Start", "DATE ( YEAR ( 'Date'[Date] ), MONTH ( 'Date'[Date] ), 1 )", dtype="dateTime", fmt="mmm yyyy")
    col("Year Month", 'FORMAT ( \'Date\'[Date], "mmm yyyy" )', dtype="string", sort_by="'Month Start'")
    col("Slicer Date", "MIN ( 'Date'[Date], TODAY () )", dtype="dateTime", fmt="dd/mm/yyyy",
        desc="Date for relative date slicers: future dates count as today, so 'Last N months' also includes upcoming records.")

    L += [f"{T}partition Date = calculated", f"{T}{T}mode: import", f"{T}{T}source =", *dax_block(f"""
// {comment}
VAR FirstData = {first_expr}
VAR LastData = {last_expr}
VAR FirstDay = DATE ( YEAR ( COALESCE ( FirstData, TODAY () ) ), 1, 1 )
VAR LastDay = DATE ( YEAR ( MAX ( COALESCE ( LastData, TODAY () ), TODAY () ) ), 12, 31 )
RETURN
    CALENDAR ( FirstDay, LastDay )
""", 4), ""]
    return "\n".join(L) + "\n"


def write_date_table(tables_dir: Path, first_expr: str, last_expr: str, overwrite: bool = False,
                     allow_dirty: bool = False, **kw):
    _write(Path(tables_dir) / "Date.tmdl", date_table(first_expr, last_expr, **kw), overwrite, allow_dirty)


# ----------------------------------------------------------------------------- DAX patterns
def previous_period(base: str) -> str:
    """base for the same number of days immediately before the selected 'Date' range (blank if none).
    The selected range is capped at today, so upcoming records included via 'Slicer Date' don't lengthen it."""
    return f"""
VAR FirstDay = MIN ( 'Date'[Date] )
VAR LastDay = MIN ( MAX ( 'Date'[Date] ), TODAY () )
VAR Days = LastDay - FirstDay + 1
RETURN
    CALCULATE ( {base}, DATESBETWEEN ( 'Date'[Date], FirstDay - Days, FirstDay - 1 ) )
"""


def pct_change_label(cur: str, prev: str) -> str:
    """'▲ 7% vs previous period' / 'No earlier period to compare'."""
    return f"""
VAR Cur = {cur}
VAR Prev = {prev}
VAR Change = DIVIDE ( Cur - Prev, Prev )
RETURN
    IF (
        ISBLANK ( Prev ) || Prev = 0,
        "No earlier period to compare",
        IF ( Change >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( Change ), "0%" ) & " vs previous period"
    )
"""


def pts_change_label(cur: str, prev: str) -> str:
    """For 0-1 percentages: '▲ 8.0 pts vs previous period'."""
    return f"""
VAR Cur = {cur}
VAR Prev = {prev}
RETURN
    IF (
        ISBLANK ( Prev ) || ISBLANK ( Cur ),
        "No earlier period to compare",
        IF ( Cur >= Prev, "▲ ", "▼ " ) & FORMAT ( ABS ( Cur - Prev ) * 100, "0.0" ) & " pts vs previous period"
    )
"""


def trend_colour(cur: str, prev: str, higher_is_good: bool = True, zero_is_comparable: bool = False) -> str:
    """Colour for a trend label; needs hidden [Colour Good] / [Colour Bad] / [Colour Neutral] measures.
    Keep it consistent with the matching label: use zero_is_comparable=True with pts_change_label (a previous
    0% is a real score); leave it False with pct_change_label (a % change from 0 can't be calculated)."""
    good, bad = ("[Colour Good]", "[Colour Bad]") if higher_is_good else ("[Colour Bad]", "[Colour Good]")
    no_comparison = "ISBLANK ( Prev ) || ISBLANK ( Cur )" if zero_is_comparable else "ISBLANK ( Prev ) || Prev = 0"
    return f"""
VAR Cur = {cur}
VAR Prev = {prev}
RETURN
    SWITCH (
        TRUE (),
        {no_comparison} || Cur = Prev, [Colour Neutral],
        Cur > Prev, {good},
        {bad}
    )
"""


def leader(values_expr: str, name_col: str, metric: str, order: str = "DESC") -> str:
    """Name of the top (or bottom) item by metric. Ties are reported as 'Name (+n tied)', never picked arbitrarily
    (TOPN returns every tied row, so TOPN(1, ...) based measures are wrong when values tie)."""
    agg = "MAXX" if order == "DESC" else "MINX"
    return f"""
VAR Items = FILTER ( ADDCOLUMNS ( {values_expr}, "@Value", {metric} ), NOT ISBLANK ( [@Value] ) )
VAR Target = {agg} ( Items, [@Value] )
VAR Leaders = FILTER ( Items, [@Value] = Target )
VAR LeaderCount = COUNTROWS ( Leaders )
VAR FirstLeader = MINX ( Leaders, {name_col} )
RETURN
    IF ( LeaderCount > 1, FirstLeader & " (+" & ( LeaderCount - 1 ) & " tied)", FirstLeader )
"""


def truncate_label(measure_ref: str, max_len: int = 45, empty_text: str = "None in this period") -> str:
    """Shortens long text (e.g. a question) so it fits a KPI tile reference label."""
    return f"""
VAR Text = {measure_ref}
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( Text ), "{empty_text}",
        LEN ( Text ) > {max_len}, LEFT ( Text, {max_len - 1} ) & "…",
        Text
    )
"""


def semantic_colours(table: MeasuresTable, good="#2E9E6B", bad="#D6493A", neutral="#4A5568"):
    """Adds hidden Colour Good / Bad / Neutral measures (keep in step with the report theme)."""
    table.add("Colour Good", f'"{good}"', folder="Formatting", hidden=True,
              desc="Semantic colour for favourable changes; matches the theme's 'good' colour.")
    table.add("Colour Bad", f'"{bad}"', folder="Formatting", hidden=True,
              desc="Semantic colour for unfavourable changes; matches the theme's 'bad' colour.")
    table.add("Colour Neutral", f'"{neutral}"', folder="Formatting", hidden=True,
              desc="Semantic colour for no change or no comparison; matches the theme's secondary text colour.")
