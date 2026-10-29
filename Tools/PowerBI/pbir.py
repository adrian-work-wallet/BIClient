"""Helpers for generating Power BI report (PBIR) definition files from Python.

The committed report files are the source of truth. These helpers create new pages and visuals, or restyle
a report in bulk, in the house style. Scripts that use them are throwaway (keep them in the agent's session
workspace, not the repo). Change an existing report with targeted edits: edit the visual.json directly, or
generate only the visuals being changed.

    import sys; sys.path.insert(0, "Tools/PowerBI")
    import pbir as p

    p.settings.measures_table = "Example Measures"
    p.settings.eyebrow = "WORK WALLET  ·  EXAMPLES"
    visuals = [
        p.header(PAGE, "Examples list", "Every example in the selected period."),
        p.date_slicer(PAGE, 956, 300, display="Created on", months=12),
        p.kpi_cards(PAGE, [(p.MS("Examples", "Total examples"), "Examples Trend Label", "Examples Trend Colour")]),
        p.table(PAGE, "table", p.MARGIN, p.BODY_Y, p.CONTENT_W, p.BODY_H, [p.C("Example", "Reference")], "Register"),
    ]
    p.write_page(REPORT_DIR, PAGE, "Examples list", visuals)

Safety: write_page() and apply_theme() refuse to write when the target has uncommitted changes, and
write_page() only writes the visuals it is given. Other visuals on the page are kept unless replace_all=True.

Visual names (folder names) are derived from uuid5(page id + key), so re-running produces the same files.
Output matches Power BI Desktop's saved form, so a Desktop save should leave generated files unchanged.
After any regeneration, check `git diff` shows only the intended changes.
"""
from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from _guard import require_clean

VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json"


@dataclass
class Settings:
    measures_table: str = "Measures"
    eyebrow: str = "WORK WALLET"
    namespace: uuid.UUID = field(default_factory=lambda: uuid.UUID("0b8a3c1e-52f4-4f6e-8d4e-7a1c9e2b3d47"))


settings = Settings()

# ---------------------------------------------------------------------------------------- layout
# 1280 x 720 canvas. Header strip, KPI card row, then the body.
W, H = 1280, 720
MARGIN, GAP = 24, 12
CONTENT_W = W - 2 * MARGIN
HEADER_Y, HEADER_H = 8, 64
SLICER_Y, SLICER_H = 10, 58
KPI_Y, KPI_H = 80, 124
BODY_Y = KPI_Y + KPI_H + GAP
BODY_BOTTOM = H - 16
BODY_H = BODY_BOTTOM - BODY_Y

# Compact rhythm for dense pages (e.g. drillthrough detail pages with many small tables).
COMPACT_TOP, COMPACT_SUMMARY_H, COMPACT_GAP, COMPACT_BOTTOM = 74, 72, 8, 712

# Colours; keep in step with the report theme (good / neutral / bad and text colours).
INK, INK_2, ACCENT = "#1E2B37", "#4A5568", "#C9901A"
GOOD, MID, BAD = "#2E9E6B", "#ECB232", "#D6493A"
SEMIBOLD = "'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif"


def vid(*parts: str) -> str:
    """Stable 20-character visual name."""
    return uuid.uuid5(settings.namespace, "/".join(parts)).hex[:20]


# ------------------------------------------------------------------------------- expressions
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def s(text: str):
    """String literal."""
    return lit("'" + text.replace("'", "''") + "'")


def b(v: bool):
    return lit("true" if v else "false")


def n(v):
    """Double literal (font sizes, widths, percentages)."""
    return lit(f"{v}D")


def i(v):
    """Integer literal (paddings, counts)."""
    return lit(f"{v}L")


def colour(hex_: str):
    return {"solid": {"color": s(hex_)}}


def colour_measure(name: str, entity: str | None = None):
    """'Field value' conditional colour: the measure returns a hex colour string."""
    return {"solid": {"color": {"expr": meas(name, entity)}}}


def col(entity: str, prop: str):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def meas(prop: str, entity: str | None = None):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity or settings.measures_table}}, "Property": prop}}


SUM, MIN = 0, 3
_AGG_NAMES = {SUM: "Sum", MIN: "Min"}


def agg(entity: str, prop: str, fn: int):
    return {"Aggregation": {"Expression": col(entity, prop), "Function": fn}}


def ref(f) -> str:
    """queryRef for a field expression, e.g. 'Table.Column', 'Min(Table.Column)'."""
    if "Column" in f:
        return f"{f['Column']['Expression']['SourceRef']['Entity']}.{f['Column']['Property']}"
    if "Measure" in f:
        return f"{f['Measure']['Expression']['SourceRef']['Entity']}.{f['Measure']['Property']}"
    a = f["Aggregation"]
    return f"{_AGG_NAMES[a['Function']]}({ref(a['Expression'])})"


def proj(f, display: str | None = None, active: bool | None = None):
    """Projection in Desktop's key order: field, queryRef, nativeQueryRef, active, displayName."""
    r = ref(f)
    p = {"field": f, "queryRef": r, "nativeQueryRef": display or r.split(".", 1)[1].rstrip(")")}
    if active is not None:
        p["active"] = active
    if display:
        p["displayName"] = display
    return p


def C(entity: str, prop: str, display: str | None = None):
    """Column projection."""
    return proj(col(entity, prop), display)


def MS(prop: str, display: str | None = None, entity: str | None = None):
    """Measure projection (defaults to the measures table)."""
    return proj(meas(prop, entity), display)


def A(entity: str, prop: str, fn: int, display: str | None = None):
    """Aggregated column projection, e.g. A('Example', 'Reference', MIN) for text cards."""
    return proj(agg(entity, prop, fn), display)


def props(**kw):
    return [{"properties": kw}]


def sel_props(selector, **kw):
    return {"properties": kw, "selector": selector}


DEFAULT = {"id": "default"}
ALL_DATA = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}


def title(text: str, subtitle: str | None = None, size: float | None = None):
    o = {"title": props(show=b(True), text=s(text), **({"fontSize": n(size)} if size else {}))}
    if subtitle:
        o["subTitle"] = props(show=b(True), text=s(subtitle))
    return o


# ----------------------------------------------------------------------------------- visuals
def container(page, key, vtype, x, y, w, h, z, visual_extra, container_objects=None, filters=None, extra=None):
    """Generic visual container. z doubles as tab order. Written in Power BI Desktop's canonical form
    (key order, 'active' flags on hierarchical roles, whole-number positions) so Desktop saves don't churn."""
    v = {"visualType": vtype, **visual_extra}
    if not v.get("objects"):
        v.pop("objects", None)  # Desktop removes empty "objects": {}
    _set_active_flags(v.get("query", {}).get("queryState", {}))
    if container_objects:
        v["visualContainerObjects"] = container_objects
    if "syncGroup" in v:
        v["syncGroup"] = v.pop("syncGroup")
    v["drillFilterOtherVisuals"] = True
    d = {
        "$schema": VC_SCHEMA,
        "name": vid(page, key),
        "position": {k: _num(val) for k, val in {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}.items()},
        "visual": v,
    }
    if filters:
        d["filterConfig"] = {"filters": filters}
    if extra:
        d.update(extra)
    return d


def _num(v):
    """Positions in whole pixels. Desktop writes fractional numbers with up to 17 significant digits
    (e.g. 770.40000000000009) where Python writes 770.4000000000001, so fractions would churn on every save."""
    return int(round(v))


# Desktop marks the expanded level of hierarchical roles: first projection active, the rest inactive.
_ACTIVE_ROLES = ("Category", "Rows", "Columns")


def _set_active_flags(query_state):
    for role in _ACTIVE_ROLES:
        projections = query_state.get(role, {}).get("projections", [])
        for idx, p in enumerate(projections):
            if "active" not in p:
                rebuilt = {k: p[k] for k in ("field", "queryRef", "nativeQueryRef")}
                rebuilt["active"] = idx == 0
                rebuilt.update({k: v for k, v in p.items() if k not in rebuilt})
                projections[idx] = rebuilt


def header(page, heading, subtitle, eyebrow: str | None = None, width=720):
    """Single textbox: small accent eyebrow, 18pt title, 9pt subtitle."""
    def run(text, size, weight=None, colour_=INK, family="Segoe UI"):
        style = {"fontFamily": family, "fontSize": f"{size}pt", "color": colour_}
        if weight:
            style["fontWeight"] = weight
        return {"value": text, "textStyle": style}

    paragraphs = [
        {"textRuns": [run(eyebrow or settings.eyebrow, 8, "bold", ACCENT, "Segoe UI Semibold")]},
        {"textRuns": [run(heading, 18, "bold", INK, "Segoe UI Semibold")]},
        {"textRuns": [run(subtitle, 9, None, INK_2)]},
    ]
    return container(page, "header", "textbox", MARGIN, HEADER_Y, width, HEADER_H, 100,
                     {"objects": {"general": props(paragraphs=paragraphs)}})


def date_slicer(page, x, w, display, months=None, years=None, entity="Date", prop="Slicer Date", sync_group=None):
    """Relative date slicer ('Last N months/years', including today). Defaults to Date[Slicer Date], which counts
    future dates as today, so upcoming (future-dated) records are included too."""
    duration, period, unit = (months, "Months", 2) if months else (years, "Years", 3)
    flt = {"Version": 2, "From": [{"Name": "d", "Entity": entity, "Type": 0}], "Where": [{"Condition": {"Between": {
        "Expression": {"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": prop}},
        "LowerBound": {"DateSpan": {"Expression": {"DateAdd": {"Expression": {"DateAdd": {
            "Expression": {"Now": {}}, "Amount": 1, "TimeUnit": 0}}, "Amount": -duration, "TimeUnit": unit}}, "TimeUnit": 0}},
        "UpperBound": {"DateSpan": {"Expression": {"Now": {}}, "TimeUnit": 0}}}}}]}
    return container(page, "slicer-date", "slicer", x, SLICER_Y, w, SLICER_H, 3000, {
        "query": {"queryState": {"Values": {"projections": [proj(col(entity, prop), display, active=True)]}}},
        "objects": {
            "data": props(mode=s("Relative"), relativeRange=s("Last"), relativeDuration=n(duration), relativePeriod=s(period)),
            "dateRange": props(includeToday=b(True)),
            "general": props(filter={"filter": flt}),
        },
        "syncGroup": {"groupName": sync_group or display, "fieldChanges": True, "filterChanges": True},
    })


def dropdown_slicer(page, key, entity, prop, display, x, w, z=3001):
    """Multi-select dropdown slicer with no saved selection."""
    return container(page, key, "slicer", x, SLICER_Y, w, SLICER_H, z, {
        "query": {"queryState": {"Values": {"projections": [proj(col(entity, prop), display, active=True)]}}},
        "objects": {"data": props(mode=s("Dropdown")), "selection": props(strictSingleSelect=b(False))},
    })


def kpi_cards(page, tiles, y=KPI_Y, h=KPI_H, key="kpis", value_size=18, padding=(10, 2, 14, 10), cell_padding=GAP):
    """One new-style card visual (cardVisual) holding a row of KPI tiles.

    tiles: list of (projection, reference_label_measure, reference_colour_measure[, value_font_size]).
    The reference label is a text measure shown under the value (e.g. '▲ 7% vs previous period');
    its font colour can come from a colour measure. padding = (top, bottom, left, right) of the callout.
    Reference label padding, if ever needed, is paddingTop/paddingBottom/paddingLeft/paddingRight on
    referenceLabel (not the *Margin names used by the padding object; Desktop drops those).
    """
    ref_labels = [sel_props(DEFAULT, backgroundShow=b(False), paddingIndividual=b(True))]
    projections, ref_values = [], []
    values = [sel_props(DEFAULT, fontSize=n(value_size))]
    for tile in tiles:
        p, label_measure, colour_measure_name = tile[:3]
        projections.append(p)
        if len(tile) > 3:
            values.append(sel_props({"metadata": p["queryRef"]}, fontSize=n(tile[3])))
        if label_measure:
            fid = f"field-{uuid.uuid5(settings.namespace, page + key + p['queryRef'])}"
            ref_labels.append({"properties": {"value": {"expr": meas(label_measure)}},
                               "selector": {"data": [{"dataViewWildcard": {"matchingOption": 0}}],
                                            "metadata": p["queryRef"], "id": fid, "order": 0}})
            if colour_measure_name:
                ref_values.append(sel_props({"metadata": p["queryRef"], "id": fid},
                                            valueFontColor=colour_measure(colour_measure_name)))
    objects = {
        # calloutSize = % of each tile given to label + value; the rest holds the reference label.
        "layout": props(orientation=n(2), maxTiles=i(len(tiles)), alignment=s("middle"), cellPadding=i(cell_padding),
                        calloutSize=n(62 if len(ref_labels) > 1 else 100)),
        "padding": [sel_props(DEFAULT, paddingIndividual=b(True), topMargin=i(padding[0]), bottomMargin=i(padding[1]),
                              leftMargin=i(padding[2]), rightMargin=i(padding[3]))],
        "value": values,
        "spacing": [sel_props(DEFAULT, verticalSpacing=i(2))],
        "referenceLabel": ref_labels,
    }
    if ref_values:
        objects["referenceLabelValue"] = ref_values
    return container(page, key, "cardVisual", MARGIN, y, CONTENT_W, h, 2000, {
        "query": {"queryState": {"Data": {"projections": projections}}},
        "objects": objects,
    })


def table(page, key, x, y, w, h, columns, title_text, subtitle=None, sort=None, widths=None, objects=None, z=1000,
          title_size=None, container_extra=None):
    """Table (tableEx). sort: [(field, 'Ascending'|'Descending')]; widths: per-column px or None."""
    q = {"queryState": {"Values": {"projections": columns}}}
    if sort:
        q["sortDefinition"] = {"sort": [{"field": f, "direction": d} for f, d in sort]}
    obj = dict(objects or {})
    if widths:
        obj["columnWidth"] = [sel_props({"metadata": c["queryRef"]}, value=n(wd)) for c, wd in zip(columns, widths) if wd]
    if "columnHeaders" in obj:
        obj["columnHeaders"] = obj.pop("columnHeaders")  # Desktop writes columnHeaders after columnWidth
    co = title(title_text, subtitle, title_size)
    co.update(container_extra or {})
    return container(page, key, "tableEx", x, y, w, h, z, {"query": q, "objects": obj}, co)


def image_grid(width=110, height=20):
    """Table 'grid' settings sizing in-cell images (SVG measures with dataCategory ImageUrl)."""
    return {"grid": props(imageHeight=n(height), imageWidth=n(width))}


def bar_chart(page, key, x, y, w, h, category, value, title_text, subtitle=None, fill=None, top_n=None, z=1100):
    """Horizontal bar chart sorted by value descending; optional Top N filter on the category."""
    objects = {"labels": props(show=b(True)), "categoryAxis": props(maxMarginFactor=i(45)), "legend": props(show=b(False))}
    if fill:
        objects["dataPoint"] = [fill]
    filters = [top_n_filter(category["field"], value["field"], top_n)] if top_n else None
    return container(page, key, "clusteredBarChart", x, y, w, h, z, {
        "query": {"queryState": {"Category": {"projections": [category]}, "Y": {"projections": [value]}},
                  "sortDefinition": {"sort": [{"field": value["field"], "direction": "Descending"}]}},
        "objects": objects,
    }, title(title_text, subtitle), filters=filters)


def top_n_filter(category_field, order_measure_field, count):
    """Visual-level Top N filter on a column, ranked by a measure."""
    cat = category_field["Column"]
    entity, prop = cat["Expression"]["SourceRef"]["Entity"], cat["Property"]
    m = order_measure_field["Measure"]
    order = {"Measure": {"Expression": {"SourceRef": {"Source": "m"}}, "Property": m["Property"]}}
    return {
        "name": vid("topn", entity, prop),
        "field": category_field,
        "type": "TopN",
        "filter": {
            "Version": 2,
            "From": [{"Name": "subquery", "Expression": {"Subquery": {"Query": {
                "Version": 2,
                "From": [{"Name": "c", "Entity": entity, "Type": 0},
                         {"Name": "m", "Entity": m["Expression"]["SourceRef"]["Entity"], "Type": 0}],
                "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": prop}, "Name": "field"}],
                "OrderBy": [{"Direction": 2, "Expression": order}],
                "Top": count}}}, "Type": 2},
                {"Name": "c", "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": prop}}],
                "Table": {"SourceRef": {"Source": "subquery"}}}}}],
        },
    }


def not_blank_filter(entity, prop):
    """Visual-level 'is not blank' filter."""
    return {
        "name": vid("notblank", entity, prop),
        "field": col(entity, prop),
        "type": "Advanced",
        "filter": {"Version": 2, "From": [{"Name": "d", "Entity": entity, "Type": 0}],
                   "Where": [{"Condition": {"Not": {"Expression": {"Comparison": {
                       "ComparisonKind": 0,
                       "Left": {"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": prop}},
                       "Right": {"Literal": {"Value": "null"}}}}}}}]},
        "howCreated": "User",
    }


def score_gradient(measure_name):
    """Fixed 0% (bad) / 50% / 100% (good) colour scale for 0-1 percentage measures: no business thresholds."""
    return {"solid": {"color": {"expr": {"FillRule": {
        "Input": meas(measure_name),
        "FillRule": {"linearGradient3": {
            "min": {"color": s(BAD)["expr"], "value": n(0)["expr"]},
            "mid": {"color": s(MID)["expr"], "value": n(0.5)["expr"]},
            "max": {"color": s(GOOD)["expr"], "value": n(1)["expr"]},
            "nullColoringStrategy": {"strategy": s("noColor")["expr"]}}}}}}}}


def count_gradient(measure_name, low="#FFF6DD", high=BAD):
    """Data-driven light-to-red scale for counts (heatmap cells)."""
    return {"solid": {"color": {"expr": {"FillRule": {
        "Input": meas(measure_name),
        "FillRule": {"linearGradient2": {
            "min": {"color": s(low)["expr"]},
            "max": {"color": s(high)["expr"]},
            "nullColoringStrategy": {"strategy": s("noColor")["expr"]}}}}}}}}


def drillthrough_button(page, key, x, y, w, h, target_page, label_measure):
    """Button that drills through using the current selection; Power BI enables it once a single value is selected.

    label_measure returns e.g. 'Select an item to view details' / 'View X details  ›'.
    Do not overlap it with the table it depends on: a selected visual is drawn on top and hides it.
    """
    states = [(DEFAULT, INK, "#FFFFFF"), ({"id": "hover"}, "#2C3B49", "#FFFFFF"), ({"id": "disabled"}, "#EEF0F3", "#8592A0")]
    return container(page, key, "actionButton", x, y, w, h, 6000, {
        "objects": {
            "icon": [sel_props(DEFAULT, shapeType=s("blank")), {"properties": {"show": b(False)}}],
            "text": [{"properties": {"show": b(True)}}] + [
                sel_props(sel, text={"expr": meas(label_measure)}, fontColor=colour(tc), fontSize=n(9), fontFamily=s(SEMIBOLD))
                for sel, _, tc in states],
            "fill": [{"properties": {"show": b(True)}}] + [
                sel_props(sel, fillColor=colour(fc), transparency=n(0)) for sel, fc, _ in states],
            "outline": [{"properties": {"show": b(False)}}],
            "shape": [sel_props(DEFAULT, roundEdge=i(6))],
        }}, {"visualLink": props(show=b(True), type=s("Drillthrough"), drillthroughSection=s(target_page))},
        extra={"howCreated": "InsertVisualButton"})


def back_button(page, key="back", x=W - MARGIN - 150, y=22, w=150, h=36):
    """Back button for drillthrough pages (top right of the header)."""
    return container(page, key, "actionButton", x, y, w, h, 5000, {
        "objects": {
            "icon": [sel_props(DEFAULT, shapeType=s("back"), lineColor=colour(INK))],
            "text": [sel_props(DEFAULT, show=b(True), text=s("Back"), fontColor=colour(INK), fontSize=n(10))],
            "outline": [sel_props(DEFAULT, show=b(True), lineColor=colour("#C9D1DA"))],
            "fill": [sel_props(DEFAULT, show=b(True), fillColor=colour("#FFFFFF"))],
        }}, {"visualLink": props(show=b(True), type=s("Back"))}, extra={"howCreated": "InsertVisualButton"})


# ------------------------------------------------------------------------------------ files
def write_json(path: Path, obj):
    """CRLF, two-space indent, no final line break: the form Power BI Desktop saves."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8", newline="\r\n")


def write_page(report_dir: Path, page_id: str, display_name: str, visuals: list[dict],
               replace_all: bool = False, allow_dirty: bool = False) -> list[str]:
    """Writes the given visuals to a page and sets its display name. Keeps the page's filters and
    drillthrough binding.

    By default only the given visuals are (over)written, and any other visuals on the page are kept; their
    folder names are returned so the caller can check them. replace_all=True deletes every existing visual and
    clears page-level formatting (the theme supplies page background/outspace). Use it only when deliberately
    rebuilding a whole page. Refuses to run if the page has uncommitted changes, unless allow_dirty=True.
    """
    pdir = Path(report_dir) / "definition" / "pages" / page_id
    require_clean(pdir, allow_dirty)
    page = json.loads((pdir / "page.json").read_text(encoding="utf-8"))
    page["displayName"] = display_name
    if replace_all:
        page.pop("objects", None)
        shutil.rmtree(pdir / "visuals", ignore_errors=True)
    write_json(pdir / "page.json", page)
    for v in visuals:
        write_json(pdir / "visuals" / v["name"] / "visual.json", v)
    generated = {v["name"] for v in visuals}
    kept = sorted(d.name for d in (pdir / "visuals").iterdir() if d.is_dir() and d.name not in generated)
    if kept:
        print(f"{display_name}: kept {len(kept)} existing visual(s) not generated here: {', '.join(kept)}")
    return kept


def apply_theme(report_dir: Path, theme_file: str = "WorkWallet.json", allow_dirty: bool = False):
    """Registers StaticResources/RegisteredResources/<theme_file> as the report's custom theme."""
    report_path = Path(report_dir) / "definition" / "report.json"
    require_clean(report_path, allow_dirty)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["themeCollection"]["customTheme"] = {
        "name": theme_file,
        "reportVersionAtImport": {"visual": "2.4.0", "report": "3.0.0", "page": "2.3.0"},
        "type": "RegisteredResources",
    }
    packages = [p for p in report["resourcePackages"] if p["name"] != "RegisteredResources"]
    packages.append({"name": "RegisteredResources", "type": "RegisteredResources",
                     "items": [{"name": theme_file, "path": theme_file, "type": "CustomTheme"}]})
    report["resourcePackages"] = packages
    write_json(report_path, report)
