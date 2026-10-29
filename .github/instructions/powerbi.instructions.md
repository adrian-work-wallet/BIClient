---
description: "Use when creating, redesigning or editing the Power BI sample reports and semantic models (.pbip, PBIR visual.json, TMDL measures, report theme), or when publishing them to a Power BI workspace to review changes interactively."
applyTo: "PowerBISamples/**, Tools/PowerBI/**"
---

# Power BI Sample Reports

## Purpose

The samples under `PowerBISamples/` serve two audiences. Every change must work for both:

- **Work Wallet**: demonstrates reporting capabilities to customers.
- **Customers**: a baseline to copy and customise into their own reports, against their own wallet's data.

## Working with any wallet

The samples are developed against a demo wallet, but must not depend on it.

- **Never hard-code wallet data** in measures or visuals: no names, IDs, answer texts, locations or record types.
- **Match statuses and types by code** (see `ReferenceData.md`), not by display name.
- **Use colours the wallet provides** (e.g. grading set colours) rather than fixed thresholds. Where a scale is needed, use a neutral fixed scale (e.g. 0%–100%), not business thresholds.
- **Handle sentinel values.** Scores, potentials and percentages use `-1` for "not scored"; exclude them (`>= 0`) from sums and averages.
- **Handle ties.** `TOPN(1, …)` returns every tied row, so never use it to pick "the" top item. Use the tie-aware leader pattern (`Name (+n tied)`).
- **Don't rely on optional product features.** If a wallet may not use a feature (e.g. flagged answers), give the user a fallback, such as a slicer that switches what is counted.
- **Default filters and slicers may use demo values**, as consumers are expected to reset them. Prefer no saved selection where the page still makes sense.
- **Check edge cases with DAX** before publishing: empty periods, a single item, ties, and data without the optional feature.

## Semantic model conventions

- **Date table**: one calculated, marked `Date` table per model (`tmdl.date_table`).
  - Relate it from a hidden, date-only calculated column on the main table, e.g. `DATE ( YEAR ( x ), MONTH ( x ), DAY ( x ) )`, not from a date/time column.
  - Date slicers, monthly axes (`Date[Year Month]`, sorted by `Month Start`) and previous-period measures all use it.
- **Measures table**: `<Module> Measures`, with display folders: one per topic (e.g. counts, scores, issues), plus Previous Period, Labels, Formatting and Images.
  - Hide helper measures: previous-period values, KPI labels, colours.
  - Give every visible measure a `///` description.
  - Avoid `%` and other symbols in measure names; the model doc generator turns them into `_`.
- **Previous period** is the same number of days immediately before the selected range (`tmdl.previous_period`). Pair it with a label (`pct_change_label` / `pts_change_label`) and a colour (`trend_colour`, setting `higher_is_good=False` for counts of problems).
- **Colours in DAX** come from hidden `Colour Good` / `Colour Bad` / `Colour Neutral` measures (`tmdl.semantic_colours`) that match the theme. Don't scatter hex values through measures.
- **In-cell SVG measures** (bars, badges):
  - Set `dataCategory: ImageUrl`.
  - Escape `#` as `%23` and XML-escape any text.
  - Check colours from data are valid hex (`LEN = 7`) before using them.
- **Tables drop a row when every measure in it is blank.**
  - For rows that must still show, return a placeholder such as `"–"` instead of blank.
  - The reverse also applies: a measure that never returns blank (e.g. one that falls back to a parent-level value) pulls in unrelated dimension rows. Return `BLANK ()` when the row has no facts (`ISEMPTY ( Fact )`).
- **`ISINSCOPE` checks must cover every column a visual might group by**, e.g. both a raw question column and its order-prefixed variant.
- **Long text for KPI tiles** (e.g. a question) is truncated in the measure (`tmdl.truncate_label`, about 45 characters).
- **New tables** need three things:
  - a `ref table` line in `model.tmdl`;
  - their relationships in `relationships.tmdl`;
  - a node on a page in `diagramLayout.json`, so the model doc generator documents them. Edit `diagramLayout.json` additively and keep its existing number formatting.

## Report design conventions

The canvas is 1280 × 720. The constants live in `Tools/PowerBI/pbir.py`.

- **Theme**: `StaticResources/RegisteredResources/WorkWallet.json`.
  - Copy it unchanged from a report that already uses it, register it with `pbir.apply_theme`, and keep every copy identical.
  - Put formatting in the theme, not on individual visuals (page background, card tiles, table headers, slicers).
- **Navigation**: no in-canvas navigation menus. Users switch pages with the Power BI page tabs, Pages pane or app navigation.
- **Header** (`pbir.header`, x 24, y 8, 720 × 64): one textbox holding:
  - an 8pt accent eyebrow (`WORK WALLET  ·  <MODULE>`);
  - an 18pt title;
  - a 9pt grey subtitle saying what the page shows.
- **Slicers**: top right, y 10, height 58, right-aligned to x 1256, 12px apart. Date slicers are about 300 wide and dropdowns about 180.
  - Use relative date slicers on `Date[Date]`, in one sync group per report.
  - Slicers in a sync group share one selection, so give them all the same default period. Otherwise the period a user sees depends on which page they opened first.
- **KPI row** (`pbir.kpi_cards`): one card visual (`cardVisual`) at y 80, height 124, holding four tiles.
  - Each tile shows a label, an 18pt value, and a reference label (a text measure, optionally coloured by a colour measure).
  - Use 13pt for text-valued tiles (names).
- **Body**: y 216 to 704, with 24px side margins and 12px gaps.
- **Dense detail pages** (e.g. drillthrough targets with many tables) use the compact rhythm:
  - summary cards at y 74, height 72, 8px gaps, ending at y 712;
  - 12pt summary values with no wrapping;
  - 9pt titles and 6/10px padding on small tables.
- **Names**: sentence case for page names, visual titles and column display names.
- **Drillthrough**:
  - Keep the target page's drillthrough binding and a Back button (`pbir.back_button`).
  - On the source page, add a drillthrough button (`pbir.drillthrough_button`) whose text comes from a measure: "Select an item…" until one row is selected, then "View X details  ›".
  - Place it outside other visuals (e.g. on the header subtitle line). A selected visual is drawn on top and hides anything overlapping it.
- **Charts and tables**:
  - Rank with visual-level Top N filters (`pbir.top_n_filter`).
  - Use colour scales for heatmap matrices (`score_gradient` for 0–1 percentages, `count_gradient` for counts).
  - Size in-cell images with table `grid` `imageWidth` / `imageHeight`, and make the column about 15px wider than the image.
  - Avoid donut charts and other visuals that become unreadable when a wallet has many categories.

## PBIR formatting lessons

- **Theme objects need a selector for cardVisual.** Every visual-level object in the `cardVisual` section of a theme needs `"$id": "default"`; container objects (`background`, `border`, `dropShadow`, `title`, `padding`) don't.
- **Card visual layout:**
  - Tiles split 50/50 between the callout (label + value) and the reference label by default, which clips the label. Set `layout.calloutSize` (62 with reference labels, 100 without).
  - Pad the callout with the `padding` object, which uses `paddingIndividual` plus `topMargin` / `bottomMargin` / `leftMargin` / `rightMargin`. Set `spacing.verticalSpacing` to 2.
  - Reference label padding uses different property names: `paddingIndividual` plus `paddingTop` / `paddingBottom` / `paddingLeft` / `paddingRight`. Desktop silently drops `*Margin` names on `referenceLabel`.
- **Slicer fonts:** relative date slicer inputs ignore text size settings (they render at about 8pt). Set slicer `items` (and `date`) text to 8pt in the theme so dropdowns match.
- **Drillthrough button:** `visualContainerObjects.visualLink` has `type 'Drillthrough'` and `drillthroughSection` set to the target page name. Style the default, hover and disabled states via selectors `{"id": "default" | "hover" | "disabled"}`.
- **Conditional colour from a measure** ("field value") is `{"solid": {"color": {"expr": {"Measure": …}}}}` (`pbir.colour_measure`).

## Power BI Desktop round-trips

Saving in Power BI Desktop rewrites files into its own form. Expect this after every Desktop save.

### What a Desktop save changes

- **JSON files** (`visual.json`, `page.json`, `report.json`, the theme):
  - The final line break is removed, so git shows whole-file changes that are whitespace only. Use `git diff --ignore-cr-at-eol` to see the real changes.
  - Visual `$schema` versions are bumped (e.g. `visualContainer/2.4.0` → `2.14.0`).
  - `"active": true` is added to `Category`, `Rows` and `Columns` projections. Lower matrix row levels get `false`.
  - Whole numbers lose their `.0` (e.g. `802.0` → `802`).
- **Unsupported properties are silently dropped.** Examples seen so far:
  - `referenceLabel` `*Margin` padding;
  - gauge callout font size;
  - button outline corner radius.

  A dropped property means it is unsupported or misnamed, so fix the generator rather than re-adding it.
- **TMDL**:
  - Table-level properties are reordered (`lineageTag` before `dataCategory`).
  - Measures can move to a different position in the table file.
  - Content is otherwise unchanged.

### How to handle it

- **Commit a Desktop save on its own**, with no other edits (e.g. "Power BI Desktop save (no functional change)"), so later diffs show only real changes.
- **Review a Desktop save structurally**, comparing property by property against the last commit (ignore whitespace and ordering). Then publish it and check the affected pages still render as before.
- **Don't overwrite the user's Desktop edits.** Before regenerating files the user has saved in Desktop, compare them with the last commit. Carry any intentional edits into the build script first.
- **Generate files in Desktop's form** (no final line break, current schema versions, whole-number positions, `active` flags). `pbir.py` and `tmdl.py` already do this, so regenerating after a Desktop save should give no differences.

## Developing interactively in an agent session

The loop: edit files, publish to a dev workspace (seconds), check measures with DAX, then check the rendered pages in the integrated browser.

### One-off setup (by the user)

- Create a dedicated development workspace. A Pro workspace is enough.
- Publish the sample model and report to it once from Power BI Desktop, and set the data source credentials in the service.
- Sign the Azure CLI in to the workspace's tenant: `az login --tenant <tenant> --allow-no-subscriptions`.
- Give the agent the workspace URL, from which it can read the IDs.
- Keep workspace, report and model IDs in the session only. Never commit them.

### Edit, publish, verify

- **Edit**:
  - Write a per-report build script in the session workspace using `pbir.py` / `tmdl.py`, or edit the JSON/TMDL directly.
  - Stable visual names and lineage tags keep diffs to real changes.
  - When files are edited by hand, create them with CRLF line endings and tab-indented TMDL (as Desktop does).
- **Publish** with `Tools/PowerBI/PowerBIDev.ps1`:
  - `Publish-PbiReport` for layout changes (it rebinds the report to the published model).
  - `Publish-PbiSemanticModel` for model changes.
  - Measure-only changes need no refresh.
  - Refresh (`Invoke-PbiRefresh -Wait`) after adding tables, columns or calculated tables.
- **Refresh limits**: Pro workspaces throttle refreshes after many in a day ("exceeded the amount of requests"), so only refresh when needed.
- **Verify measures** with `Invoke-PbiDax`. Use `CALCULATETABLE ( ROW ( … ), <filters> )` to test specific contexts (a date range, one record, ties).

### Checking pages in the browser

- **Open a page**: `https://app.powerbi.com/groups/<workspaceId>/reports/<reportId>/<pageName>?experience=power-bi&chromeless=1`.
  - The user signs in once in the integrated browser.
  - `chromeless=1` hides the service chrome.
- **Filter by URL** to reach a specific record: `&filter=Table/Column eq 'value'`, encoding spaces in names as `_x0020_`.
- **Allow time to render**: wait about 15 seconds after navigating. Reload after each publish, because the browser caches the report.
- **Slicers remember the viewer's last selection** (persistent filters), so a changed default won't show until you click "Reset to default". That button is in the full view; it isn't available with `chromeless=1`.
- **The tab must be visible to render.** If visuals measure zero size or the canvas is blank, ask the user to bring the browser tab into view.
- **Screenshots can be stale.** Confirm results by measuring the live page with `page.evaluate`:
  - element positions (`getBoundingClientRect`) and computed font sizes;
  - card tiles are `.small-multiples-grid-cell-content`, tables are `[role="grid"]`.
- **Full canvas**: `page.setViewportSize({ width: 1700, height: 1000 })` shows the whole canvas.
- **Test interactions** with Playwright: click a table row (`getByText(...).click()`), click buttons, and right-click → Drill through.

### Finishing

- **Regenerate the model docs** after model changes: `dotnet run --project Tools/WorkWallet.BI.PowerBIModelDocGenerator/WorkWallet.BI.PowerBIModelDocGenerator.csproj`. CI runs it with `-- --check`.
- **Update `CHANGELOG.md`** at a high level (the audience is report consumers).
- **Ask the user to open the `.pbip` in Power BI Desktop, refresh and save.** This updates the local data cache and validates the files in Desktop. Then compare the diff before committing.

## Tools

- **`Tools/PowerBI/PowerBIDev.ps1`**: dot-source it, then use:
  - `Get-PbiItems`
  - `Publish-PbiSemanticModel`
  - `Publish-PbiReport`
  - `Export-PbiDefinition` (downloads a published definition)
  - `Invoke-PbiRefresh`
  - `Invoke-PbiDax`
- **`Tools/PowerBI/pbir.py`**: report builders and the layout constants. It covers:
  - header, date and dropdown slicers, the KPI card row, tables, bar charts;
  - Top N and not-blank filters, gradients;
  - drillthrough and Back buttons;
  - `write_page` (keeps page filters and drillthrough bindings) and `apply_theme`.
- **`Tools/PowerBI/tmdl.py`**: the `MeasuresTable` builder, the `Date` table, and the DAX patterns (previous period, change labels, trend colours, tie-aware leader, truncation, semantic colours).
- **`Tools/WorkWallet.BI.PowerBIModelDocGenerator`**: generates `PowerBISamplesModels.md` and `PowerBISamplesModels/*.md` from the TMDL and `diagramLayout.json`. Never edit its output by hand.
- **Prerequisites**: Azure CLI, Python 3, the .NET SDK, and the integrated browser with its Playwright tools.
