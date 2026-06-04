# Waste Decision Support Tool

This Streamlit app reads the integrated business waste workbook and provides planner-facing dashboards for waste generation, census block group targeting, diversion opportunity, circular-flow screening, and model validation.

## Stakeholder Demo

For the stakeholder prototype, deploy `demo_app.py`. It uses the same app code but only shows the polished dashboards:

- Business heat map
- Census block groups
- Diversion opportunity
- 2025 study vs model

The demo expects the packaged workbook at:

```text
data/fullbusinesslist_waste_integrated.xlsx
```

If that file is missing, the app falls back to the local OneDrive workbook path listed below.

## Run

Double-click `start_app.bat`, or run this from the app folder:

```powershell
..\mergent_enrichment\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\mergent_enrichment\.venv\Scripts\python.exe -m streamlit run app.py --server.port=8507
```

Run the stakeholder demo locally on port `8510`:

```powershell
..\mergent_enrichment\.venv\Scripts\python.exe -m streamlit run demo_app.py --server.port=8510
```

## Streamlit Community Cloud

Keep the GitHub repository private if the code and packaged workbook should not be publicly visible.
Streamlit Community Cloud can deploy from a private GitHub repository after you grant Streamlit access
to private repositories. The deployed app starts private by default and can be made public from Streamlit
Cloud's app sharing settings if you want a broadly shareable stakeholder link.

Use these settings when creating the Streamlit app:

```text
Repository: Waste Generation Decision Support System Prototype
Branch: main
Main file path: demo_app.py
```

The default workbook path is:

```text
C:\Users\tonyg\OneDrive - Cal Poly\MS Project - SLO Environmental Planning DSS\Stage 2 - Data Infrastructure\Outputs\fullbusinesslist_waste_integrated.xlsx
```

## What It Supports

- Business heat map exploration by latitude and longitude.
- Census block group choropleth mapping and rankings for San Luis Obispo County.
- Circular flow screening with landfill allocation, hauling emissions, and material exchange opportunities.
- Jurisdiction filtering using either the source jurisdiction or CalRecycle jurisdiction fields.
- Business group filtering using the normalized or source business group fields.
- Waste stream slicing for landfill, recycle, organics, and diversion.
- Material slicing either layered with the waste stream filter or shown as material total generation.
- CSV exports for filtered businesses and block group rankings.

## Census Boundaries

The Census Block Groups dashboard auto-downloads the 2023 TIGER/Line California block group file from:

```text
https://www2.census.gov/geo/tiger/TIGER2023/BG/tl_2023_06_bg.zip
```

It caches that ZIP in:

```text
waste_heatmap_app\data\tiger
```

The app filters those boundaries to San Luis Obispo County using county FIPS `079`, spatially joins businesses to block group polygons, and ranks block groups using the currently selected waste/material slice.

## Local Caching

The app keeps local generated caches in:

```text
waste_heatmap_app\data\cache
```

These caches speed up repeat sessions by avoiding repeated Excel parsing, repeated full TIGER ZIP reads, and repeated business-to-block-group spatial joins. They can be deleted safely if you want to force a rebuild.

The Circular Flow dashboard can cache road-network distance tables in `data\cache`. Its preferred road-network mode uses the Census TIGER county roads file:

```text
https://www2.census.gov/geo/tiger/TIGER2023/ROADS/tl_2023_06079_roads.zip
```

The dashboard can also cache OpenStreetMap road-network files in:

```text
waste_heatmap_app\data\osm
```

OpenStreetMap mode first looks for `data\osm\slo_county_drive.graphml`. If it does not exist, the app tries to download a drive network from Overpass and save it there. Overpass servers can time out; use Census TIGER mode for the faster practical road-network estimate, or provide a local `.graphml` path in the dashboard's `Road network source` sidebar section.

## Interaction Notes

The app does not load a default map in a fresh session. Users choose `Business heat map` or `Census block groups` first so they can switch directly to the map they need without waiting for an unwanted default map render.

In the Census dashboard, clicking a block group zooms to it and changes the lower table to selected-area drivers. In the business drivers table, clicking a business row opens that business's stream and material breakdown.
