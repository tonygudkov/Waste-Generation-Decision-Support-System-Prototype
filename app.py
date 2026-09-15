from __future__ import annotations

import io
import json
import hashlib
import html
import os
import re
import urllib.request
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components


APP_DIR = Path(__file__).resolve().parent
TIGER_DIR = APP_DIR / "data" / "tiger"
BOUNDARY_DIR = APP_DIR / "data" / "boundaries"
CACHE_DIR = APP_DIR / "data" / "cache"
OSM_DIR = APP_DIR / "data" / "osm"
EXPORT_DIR = APP_DIR / "outputs"
MEDIA_DIR = APP_DIR / "data" / "media"
TUTORIAL_VIDEO_PATH = MEDIA_DIR / "using_iwma_decision_support_system_prototype.mp4"
CACHE_VERSION = "2026-05-27-cache-v1"

LOCAL_DATA_PATH = (
    r"C:\Users\tonyg\OneDrive - Cal Poly\MS Project - SLO Environmental Planning DSS"
    r"\Stage 2 - Data Infrastructure\Outputs\fullbusinesslist_waste_integrated.xlsx"
)
PACKAGED_DATA_PATH = APP_DIR / "data" / "fullbusinesslist_waste_integrated.xlsx"
DEFAULT_DATA_PATH = str(PACKAGED_DATA_PATH if PACKAGED_DATA_PATH.exists() else LOCAL_DATA_PATH)

DEFAULT_TIGER_YEAR = "2023"
DEFAULT_ZCTA_YEAR = "2020"
DEFAULT_STATE_FIPS = "06"
DEFAULT_COUNTY_FIPS = "079"
DEFAULT_COUNTY_NAME = "San Luis Obispo County"
SLO_COUNTY_GEOID = f"{DEFAULT_STATE_FIPS}{DEFAULT_COUNTY_FIPS}"
SMART1383_SOURCE_COMPANY_ESTIMATE = 8000
SLO_MAP_BOUNDS = {
    "min_lon": -121.8,
    "min_lat": 34.6,
    "max_lon": -119.2,
    "max_lat": 36.1,
}

STREAM_COLUMNS = {
    "disposed": {
        "label": "Landfill",
        "total": "calrecycle_disposed_total_tons",
    },
    "curbside_recycle": {
        "label": "Recycle",
        "total": "calrecycle_curbside_recycle_total_tons",
    },
    "curbside_organics": {
        "label": "Organics",
        "total": "calrecycle_curbside_organics_total_tons",
    },
    "other_diversion": {
        "label": "Diversion",
        "total": "calrecycle_other_diversion_total_tons",
    },
}
STREAM_KEYS = list(STREAM_COLUMNS)
TOTAL_GENERATION_COLUMN = "calrecycle_total_generation_total_tons"

BLOCK_GROUP_METRICS = {
    "Total waste tons": "total_waste_tons",
    "Waste tons per sq mi": "tons_per_sq_mi",
    "Business count": "business_count",
    "Businesses per sq mi": "businesses_per_sq_mi",
    "Average tons per business": "avg_tons_per_business",
}

HEATMAP_VOLUME_METRIC = "Total tons"
HEATMAP_TONS_PER_BUSINESS_METRIC = "Tons per business"
HEATMAP_BUSINESSES_PER_SQ_MI_METRIC = "Businesses per sq mi"
HEATMAP_METRICS = [
    HEATMAP_VOLUME_METRIC,
    HEATMAP_TONS_PER_BUSINESS_METRIC,
    HEATMAP_BUSINESSES_PER_SQ_MI_METRIC,
]

PARETO_CHART_ROWS = 25
PARETO_TABLE_ROWS = 50
VITAL_FEW_THRESHOLD = 80.0
POTENTIAL_TONS_COLUMN = "Modeled Potential Diversion Tons"
DEFAULT_OPPORTUNITY_TON_THRESHOLD = 1.0
DEFAULT_OPPORTUNITY_SHARE_THRESHOLD = 0.0
ORGANICS_CO2E_FACTOR_20_YEAR = 1.0
STUDY_SECTOR_BASIS_ICI_REFUSE_TONS = 34_280.0
STUDY_TABLE_TOTAL_ICI_REFUSE_TONS = 57_705.0
RAW_OPPORTUNITY_MODE = "Raw workbook model"
STUDY_CALIBRATED_OPPORTUNITY_MODE = "Study-calibrated pathway shares"
IWMA_GREEN = "#4f7f3f"
IWMA_BLUE = "#1f5f8b"
IWMA_LIGHT_GREEN = "#82a95a"
IWMA_PURPLE = "#7b589f"
IWMA_GRAY = "#7a817b"
IWMA_CHART_COLORS = [IWMA_GREEN, IWMA_BLUE, IWMA_PURPLE, IWMA_LIGHT_GREEN, IWMA_GRAY]
IWMA_STUDY_MODEL_COLORS = {
    "2025 Study": IWMA_GREEN,
    "Current model": IWMA_BLUE,
    "Dashboard allocation": IWMA_BLUE,
    "Study countywide": IWMA_GREEN,
    "Study mapped-only": IWMA_PURPLE,
}
DEFAULT_TRUCK_KG_CO2E_PER_TON_MILE = 0.2124
DEFAULT_TRUCK_KG_CO2E_PER_VEHICLE_MILE = 4.1
DEFAULT_COLLECTION_TRIPS_PER_YEAR = 52
DEFAULT_COLLECTION_TRUCKLOAD_TONS = 7.0
DEFAULT_DIVERSION_TRIPS_PER_BUSINESS = 1
DEFAULT_ROAD_DISTANCE_MULTIPLIER = 1.25
DEFAULT_ROUTE_OPERATIONS_MULTIPLIER = 1.15
ROAD_DISTANCE_TIGER_MODE = "Road network (Census TIGER)"
ROAD_DISTANCE_OSM_MODE = "Road network (OpenStreetMap)"
ROAD_DISTANCE_ESTIMATE_MODE = "Straight-line estimate"
TIGER_ROUTE_CACHE_COLUMNS = {"business_road_node", "landfill_road_node"}
HAULER_FACILITY_ALLOCATION_MODE = "Hauler facility rules"
DEMO_MODE = os.environ.get("WASTE_DSS_DEMO_MODE", "").strip() == "1"
FULL_DASHBOARD_OPTIONS = [
    "Home",
    "Quick start guide",
    "Data infrastructure",
    "Assumptions",
    "Business heat map",
    "Census block groups",
    "Diversion opportunity",
    "Outreach campaign builder",
    "Circular economy marketplace",
    "Circular flow engine",
    "2025 study vs model",
]
DEMO_DASHBOARD_OPTIONS = [
    "Quick start guide",
    "Business heat map",
    "Census block groups",
    "Diversion opportunity",
    "Assumptions",
    "2025 study vs model",
]
DASHBOARD_OPTIONS = DEMO_DASHBOARD_OPTIONS if DEMO_MODE else FULL_DASHBOARD_OPTIONS
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

DESTINATION_STREAMS = {
    "curbside_recycle": {
        "label": "Curbside recycle",
        "short_label": "Recycle",
        "color": [35, 105, 154, 214],
    },
    "curbside_organics": {
        "label": "Curbside organics",
        "short_label": "Organics",
        "color": [76, 137, 73, 214],
    },
    "third_party_diversion": {
        "label": "Third-party diversion",
        "short_label": "Third-party",
        "color": [123, 88, 159, 214],
    },
    "not_readily_recoverable": {
        "label": "Not readily recoverable",
        "short_label": "Not recoverable",
        "color": [113, 120, 116, 132],
    },
}
DIVERTIBLE_DESTINATIONS = ["curbside_recycle", "curbside_organics", "third_party_diversion"]
IWMA_DESTINATION_COLORS = {
    "Curbside recycle": IWMA_BLUE,
    "Curbside organics": IWMA_GREEN,
    "Third-party diversion": IWMA_PURPLE,
    "Not readily recoverable": IWMA_GRAY,
}
LANDFILL_FACILITIES = [
    {
        "Landfill": "Cold Canyon Landfill",
        "Address": "2268 Carpenter Canyon Road, San Luis Obispo",
        "latitude": 35.1876798,
        "longitude": -120.5958721,
        "default_share": 0.51,
        "color": [35, 105, 154, 226],
        "icon": "◆",
    },
    {
        "Landfill": "Chicago Grade Landfill",
        "Address": "2290 Homestead Road, Templeton",
        "latitude": 35.5212507,
        "longitude": -120.6417408,
        "default_share": 0.315,
        "color": [76, 137, 73, 226],
        "icon": "■",
    },
    {
        "Landfill": "City of Paso Robles Landfill",
        "Address": "9000 CA Highway 46 East, Paso Robles",
        "latitude": 35.6594167,
        "longitude": -120.5339722,
        "default_share": 0.142,
        "color": [123, 88, 159, 226],
        "icon": "▲",
    },
]
LANDFILL_CHART_COLORS = {
    facility["Landfill"]: f"#{facility['color'][0]:02x}{facility['color'][1]:02x}{facility['color'][2]:02x}"
    for facility in LANDFILL_FACILITIES
}
HAULER_FACILITY_RULES = [
    {
        "Hauler Pattern": "Waste Connections",
        "Landfill": "Cold Canyon Landfill",
        "Rule": "Waste Connections trash trucks empty at Cold Canyon Landfill.",
    },
    {
        "Hauler Pattern": "Waste Management / WM",
        "Landfill": "Chicago Grade Landfill",
        "Rule": "Waste Management trash trucks empty at Chicago Grade Landfill.",
    },
    {
        "Hauler Pattern": "Paso Robles Waste",
        "Landfill": "City of Paso Robles Landfill",
        "Rule": "Paso Robles Waste trash trucks empty at Paso Robles Landfill.",
    },
    {
        "Hauler Pattern": "San Miguel Garbage",
        "Landfill": "City of Paso Robles Landfill",
        "Rule": "San Miguel Garbage trash trucks empty at Paso Robles Landfill.",
    },
]
MARKETPLACE_USER_KEYWORDS = {
    "Paper": [
        "packag",
        "shipping",
        "warehouse",
        "wholesale",
        "retail",
        "office",
        "print",
        "mail",
        "education",
    ],
    "Plastic": [
        "manufactur",
        "packag",
        "retail",
        "wholesale",
        "repair",
        "arts",
        "construction",
    ],
    "Metal": [
        "manufactur",
        "fabricat",
        "machine",
        "auto",
        "repair",
        "construction",
        "durable",
        "truck",
    ],
    "Glass": [
        "food",
        "beverage",
        "restaurant",
        "arts",
        "manufactur",
        "retail",
    ],
    "Organics": [
        "food",
        "restaurant",
        "grocery",
        "market",
        "hotel",
        "school",
        "education",
        "landscape",
        "nursery",
        "garden",
        "compost",
        "agric",
    ],
    "C&D": [
        "construction",
        "building",
        "contractor",
        "landscape",
        "repair",
        "architect",
        "wood",
        "lumber",
    ],
    "HHW": [
        "auto",
        "repair",
        "electronics",
        "medical",
        "maintenance",
        "paint",
        "clean",
    ],
    "Other": [
        "manufactur",
        "repair",
        "arts",
        "retail",
        "services",
        "reuse",
    ],
}
LANDFILL_STUDY_BASIS = [
    {"Landfill": "Cold Canyon Landfill", "2019 MSW Tons": 147_110, "Study Countywide Share (%)": 51.0},
    {"Landfill": "Chicago Grade Landfill", "2019 MSW Tons": 90_895, "Study Countywide Share (%)": 31.5},
    {"Landfill": "City of Paso Robles Landfill", "2019 MSW Tons": 41_006, "Study Countywide Share (%)": 14.2},
    {"Landfill": "Other facilities not mapped", "2019 MSW Tons": 9_420, "Study Countywide Share (%)": 3.3},
]

ICI_MATERIAL_GROUP_SHARES = {
    "Paper": 21.6,
    "Plastic": 13.8,
    "Metal": 7.1,
    "Glass": 2.7,
    "Organics": 24.9,
    "C&D": 10.1,
    "HHW": 0.3,
    "Other": 19.5,
}

ICI_PATHWAY_SHARES = {
    "Targeted single-stream": 17.8,
    "Processable organics": 30.8,
    "Potentially donatable food": 3.0,
    "Third-party recyclable outlets": 12.6,
    "HHW/E-waste program": 0.5,
    "Processable as C&D": 6.6,
    "Not readily recoverable": 28.7,
}

STUDY_DIVERSION_PATHWAY_SHARES = {
    "Curbside recycle": 17.8,
    "Curbside organics / food recovery": 33.8,
    "Third-party diversion": 19.7,
    "Not readily recoverable": 28.7,
}
STUDY_DESTINATION_SHARES = {
    "curbside_recycle": 17.8,
    "curbside_organics": 33.8,
    "third_party_diversion": 19.7,
    "not_readily_recoverable": 28.7,
}
STUDY_DIVERTIBLE_SHARE = sum(STUDY_DESTINATION_SHARES[key] for key in DIVERTIBLE_DESTINATIONS)

MATERIAL_GROUPS = {
    "Paper": {
        "uncoated_corrugated_cardboard",
        "paper_bags",
        "newspaper",
        "white_ledger_paper",
        "other_office_paper",
        "magazines_and_catalogs",
        "phone_books_and_directories",
        "other_miscellaneous_paper_compostable",
        "other_miscellaneous_paper_other",
        "remainder_composite_paper_compostable",
        "remainder_composite_paper_other",
    },
    "Glass": {
        "clear_glass_bottles_and_containers",
        "green_glass_bottles_and_containers",
        "brown_glass_bottles_and_containers",
        "other_glass_colored_bottles_and_containers",
        "flat_glass",
        "remainder_composite_glass",
    },
    "Metal": {
        "tin_steel_cans",
        "major_appliances",
        "other_ferrous",
        "aluminum_cans",
        "other_non_ferrous",
        "remainder_composite_metal",
        "brown_goods",
        "computer_related_electronics",
        "other_small_consumer_electronics",
        "video_display_devices",
    },
    "Plastic": {
        "pete_plastic_containers",
        "hdpe_plastic_containers",
        "miscellaneous_plastic_containers",
        "plastic_trash_bags",
        "plastic_grocery_and_other_merchandise_bags",
        "non_bag_commercial_and_industrial_packaging_film",
        "film_products",
        "other_film_other",
        "durable_plastic_items_2_and_5_bulky_rigids",
        "durable_plastic_items_other",
        "remainder_composite_plastic",
    },
    "Organics": {
        "food",
        "leaves_and_grass",
        "prunings_and_trimmings",
        "branches_and_stumps",
        "manures",
        "remainder_composite_organic",
    },
    "C&D": {
        "concrete",
        "asphalt_paving",
        "asphalt_roofing",
        "clean_dimensional_lumber",
        "clean_engineered_wood",
        "clean_pallets_crates",
        "other_wood_waste",
        "gypsum_board",
        "carpet",
        "rock_soil_and_fines",
        "remainder_composite_inerts_and_other",
    },
    "HHW": {
        "paint",
        "vehicle_and_equipment_fluids",
        "used_oil",
        "used_oil_filters",
        "batteries",
        "remainder_composite_household_hazardous",
    },
    "Other": {
        "textiles",
        "ash",
        "treated_medical_waste",
        "bulky_items",
        "tires",
        "remainder_composite_special_waste",
        "mixed_residue",
    },
}

CURBSIDE_RECYCLE_MATERIALS = {
    "uncoated_corrugated_cardboard",
    "paper_bags",
    "newspaper",
    "white_ledger_paper",
    "other_office_paper",
    "magazines_and_catalogs",
    "phone_books_and_directories",
    "clear_glass_bottles_and_containers",
    "green_glass_bottles_and_containers",
    "brown_glass_bottles_and_containers",
    "other_glass_colored_bottles_and_containers",
    "tin_steel_cans",
    "aluminum_cans",
    "pete_plastic_containers",
    "hdpe_plastic_containers",
    "miscellaneous_plastic_containers",
}

CURBSIDE_ORGANICS_MATERIALS = {
    "food",
    "leaves_and_grass",
    "prunings_and_trimmings",
    "branches_and_stumps",
    "manures",
    "other_miscellaneous_paper_compostable",
    "remainder_composite_paper_compostable",
    "remainder_composite_organic",
}

THIRD_PARTY_DIVERSION_MATERIALS = {
    "asphalt_paving",
    "asphalt_roofing",
    "batteries",
    "brown_goods",
    "bulky_items",
    "carpet",
    "clean_dimensional_lumber",
    "clean_engineered_wood",
    "clean_pallets_crates",
    "computer_related_electronics",
    "concrete",
    "durable_plastic_items_2_and_5_bulky_rigids",
    "durable_plastic_items_other",
    "film_products",
    "gypsum_board",
    "major_appliances",
    "non_bag_commercial_and_industrial_packaging_film",
    "other_ferrous",
    "other_film_other",
    "other_non_ferrous",
    "other_small_consumer_electronics",
    "other_wood_waste",
    "paint",
    "plastic_grocery_and_other_merchandise_bags",
    "rock_soil_and_fines",
    "textiles",
    "tires",
    "used_oil",
    "used_oil_filters",
    "vehicle_and_equipment_fluids",
    "video_display_devices",
}

SLO_JURISDICTION_PLACE_NAMES = {
    "Arroyo Grande",
    "Atascadero",
    "Avila Beach",
    "California Valley",
    "Cambria",
    "Cayucos",
    "Grover Beach",
    "Heritage Ranch",
    "Los Osos",
    "Morro Bay",
    "Nipomo",
    "Oceano",
    "Paso Robles",
    "Pismo Beach",
    "San Luis Obispo",
    "San Miguel",
    "San Simeon",
    "Templeton",
}

MATERIAL_COLUMN_RE = re.compile(
    r"^calrecycle_mat_(.+?)_"
    r"(disposed|curbside_recycle|curbside_organics|other_diversion|total_generation)_tons$"
)


st.set_page_config(
    page_title="Waste Decision Support Tool",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 1.5rem;
        }
        div[data-testid="stMetric"] {
            background: #f7f8f6;
            border: 1px solid #dfe4de;
            border-radius: 8px;
            padding: 0.7rem 0.85rem;
        }
        div[data-testid="stMetric"] label {
            color: #415048;
        }
        section[data-testid="stSidebar"] {
            background: #f7f8f6;
        }
        .stDataFrame {
            border: 1px solid #dfe4de;
            border-radius: 8px;
            overflow: hidden;
        }
        .dashboard-loading-overlay {
            position: fixed;
            inset: 0;
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(247, 248, 246, 0.42);
            backdrop-filter: blur(2px);
            pointer-events: none;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading workbook...")
def load_excel_from_path(path_text: str) -> pd.DataFrame:
    path = Path(path_text)
    cache_path = disk_cache_path("workbook", path_signature(path), ".pkl")
    if cache_path.exists():
        return pd.read_pickle(cache_path)

    data = pd.read_excel(path, sheet_name=0)
    write_pickle_cache(data, cache_path)
    return data


@st.cache_data(show_spinner="Loading workbook...")
def load_excel_from_bytes(file_bytes: bytes) -> pd.DataFrame:
    cache_key = hashlib.sha256(file_bytes + CACHE_VERSION.encode("utf-8")).hexdigest()[:24]
    cache_path = disk_cache_path("uploaded_workbook", cache_key, ".pkl")
    if cache_path.exists():
        return pd.read_pickle(cache_path)

    data = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0)
    write_pickle_cache(data, cache_path)
    return data


def path_signature(path: Path) -> str:
    resolved = path.expanduser().resolve()
    stat = resolved.stat()
    payload = f"{CACHE_VERSION}|{resolved}|{stat.st_size}|{stat.st_mtime_ns}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def disk_cache_path(prefix: str, cache_key: str, suffix: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{prefix}_{cache_key}{suffix}"


def write_pickle_cache(data: object, cache_path: Path) -> None:
    temp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    pd.to_pickle(data, temp_path)
    temp_path.replace(cache_path)


def coordinates_signature(coords: pd.DataFrame, extra_key: str) -> str:
    ordered = coords.sort_values("_business_row_id").reset_index(drop=True)
    hashed_rows = pd.util.hash_pandas_object(ordered, index=False).values.tobytes()
    digest = hashlib.sha256()
    digest.update(CACHE_VERSION.encode("utf-8"))
    digest.update(extra_key.encode("utf-8"))
    digest.update(hashed_rows)
    return digest.hexdigest()[:24]


def import_geopandas():
    try:
        import geopandas as gpd
    except ImportError as exc:
        st.error("The census block group dashboard needs the geospatial packages in requirements.txt.")
        st.code(
            r'cd "C:\Users\tonyg\OneDrive\Documents\Grad Project\waste_heatmap_app"' "\n"
            r'& "..\mergent_enrichment\.venv\Scripts\python.exe" -m pip install -r requirements.txt',
            language="powershell",
        )
        st.stop()
    return gpd


def existing_columns(df: pd.DataFrame, candidates: list[str]) -> list[str]:
    return [column for column in candidates if column in df.columns]


def first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    columns = existing_columns(df, candidates)
    return columns[0] if columns else None


def option_values(series: pd.Series) -> list[str]:
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""].unique().tolist()
    return sorted(values, key=str.casefold)


def industry_description_columns(df: pd.DataFrame) -> list[str]:
    return existing_columns(
        df,
        [
            "Primary NAICS Description",
            "Secondary NAICS Description",
            "Primary SIC Description",
            "Secondary SIC Description",
            "Line of Business",
        ],
    )


def combined_option_values(df: pd.DataFrame, columns: list[str]) -> list[str]:
    values = []
    for column in columns:
        if column in df.columns:
            values.append(df[column])
    if not values:
        return []
    return option_values(pd.concat(values, ignore_index=True))


def industry_filter_mask(
    df: pd.DataFrame,
    industry_filter_field: str,
    industry_fields: list[str],
    selected_industries: list[str],
) -> pd.Series:
    if not selected_industries:
        return pd.Series(True, index=df.index)
    selected = {str(value).strip() for value in selected_industries}
    if industry_filter_field == "Any NAICS/SIC description":
        mask = pd.Series(False, index=df.index)
        for column in industry_fields:
            if column in df.columns:
                mask = mask | df[column].fillna("").astype(str).str.strip().isin(selected)
        return mask
    if industry_filter_field in df.columns:
        return df[industry_filter_field].fillna("").astype(str).str.strip().isin(selected)
    return pd.Series(True, index=df.index)


def multifamily_mask(df: pd.DataFrame, business_group_field: str) -> pd.Series:
    candidates = []
    for column in [
        business_group_field,
        "Business Group",
        "SMART1383 Business Group",
        "calrecycle_profile_business_group",
    ]:
        if column and column in df.columns and column not in candidates:
            candidates.append(column)
    mask = pd.Series(False, index=df.index)
    for column in candidates:
        mask = mask | df[column].fillna("").astype(str).str.contains("multifamily", case=False, na=False)
    return mask


def umbrella_metrics_frame(df: pd.DataFrame, business_group_field: str) -> pd.DataFrame:
    """Return the ICI business subset used by aggregate dashboard metrics.

    Multifamily records remain in the underlying planner dataset and in business-level
    displays. They are excluded only where an aggregate represents the commercial/ICI
    planning universe or the ICI waste-characterization study.
    """
    if df.empty:
        return df.copy()
    return df[~multifamily_mask(df, business_group_field)].copy()


def study_validation_frame(df: pd.DataFrame, business_group_field: str) -> pd.DataFrame:
    """Compatibility name for the study-validation subset."""
    return umbrella_metrics_frame(df, business_group_field)


def format_material_name(material_key: str) -> str:
    special = {
        "and": "and",
        "of": "of",
        "hdpe": "HDPE",
        "pete": "PETE",
        "c": "C",
        "d": "D",
        "2": "2",
        "5": "5",
    }
    words = []
    for word in material_key.split("_"):
        words.append(special.get(word, word.capitalize()))
    return " ".join(words).replace("C and D", "C&D")


def discover_material_columns(columns: pd.Index) -> dict[str, dict[str, str]]:
    material_columns: dict[str, dict[str, str]] = {}
    for column in columns:
        match = MATERIAL_COLUMN_RE.match(str(column))
        if not match:
            continue
        material_key, stream_key = match.groups()
        material_columns.setdefault(material_key, {})[stream_key] = str(column)
    return material_columns


def material_group(material_key: str) -> str:
    for group_name, material_keys in MATERIAL_GROUPS.items():
        if material_key in material_keys:
            return group_name
    return "Other"


def numeric_sum(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    if not columns:
        return pd.Series(0.0, index=df.index)
    numeric = df[columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    return numeric.sum(axis=1)


STREAM_FINGERPRINT_COLORS = {
    "Landfill": IWMA_GRAY,
    "Recycle": IWMA_BLUE,
    "Organics": IWMA_GREEN,
    "Diversion": IWMA_PURPLE,
}


def row_stream_tons(row: pd.Series) -> dict[str, float]:
    values = {}
    for stream_config in STREAM_COLUMNS.values():
        label = stream_config["label"]
        column = stream_config["total"]
        values[label] = row_numeric_value(row, column)
    return values


def stream_fingerprint_html(stream_tons: dict[str, float], compact: bool = True) -> str:
    total = sum(max(float(value), 0.0) for value in stream_tons.values())
    if total <= 0:
        return "<div style='font-size:11px;color:#dfe4de;'>No stream tons available</div>"
    segments = []
    labels = []
    for label, value in stream_tons.items():
        share = max(float(value), 0.0) / total * 100
        if share <= 0:
            continue
        color = STREAM_FINGERPRINT_COLORS.get(label, IWMA_GRAY)
        segments.append(
            f"<div title='{html.escape(label)} {share:.1f}%' "
            f"style='height:100%;width:{share:.2f}%;background:{color};'></div>"
        )
        labels.append(f"{label} {share:.0f}%")
    height = "9px" if compact else "16px"
    label_html = "" if compact else "<div style='font-size:0.82rem;color:#5f6762;margin-top:0.3rem;'>" + " | ".join(labels) + "</div>"
    return (
        f"<div style='margin-top:0.35rem;min-width:180px;'>"
        f"<div style='display:flex;overflow:hidden;height:{height};border-radius:999px;background:#edf1ec;'>"
        + "".join(segments)
        + f"</div>{label_html}</div>"
    )


def row_stream_fingerprint_html(row: pd.Series, compact: bool = True) -> str:
    return stream_fingerprint_html(row_stream_tons(row), compact=compact)


def selected_metric(
    df: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
    selected_streams: list[str],
    selected_materials: list[str],
    material_mode: str,
) -> tuple[pd.Series, str, list[str]]:
    if selected_materials and material_mode == "Material totals":
        columns = [
            material_columns[material].get("total_generation")
            for material in selected_materials
            if material_columns.get(material, {}).get("total_generation")
        ]
        label = "Selected material generation"
        return numeric_sum(df, columns), label, columns

    if selected_materials:
        columns = []
        for material in selected_materials:
            for stream in selected_streams:
                column = material_columns.get(material, {}).get(stream)
                if column:
                    columns.append(column)
        material_label = " + ".join(format_material_name(item) for item in selected_materials[:3])
        if len(selected_materials) > 3:
            material_label += f" + {len(selected_materials) - 3} more"
        stream_label = " + ".join(STREAM_COLUMNS[item]["label"] for item in selected_streams)
        return numeric_sum(df, columns), f"{material_label}: {stream_label}", columns

    selected_set = set(selected_streams)
    all_streams_selected = selected_set == set(STREAM_KEYS)
    if all_streams_selected and TOTAL_GENERATION_COLUMN in df.columns:
        return (
            pd.to_numeric(df[TOTAL_GENERATION_COLUMN], errors="coerce").fillna(0),
            "Total generation",
            [TOTAL_GENERATION_COLUMN],
        )

    columns = [
        STREAM_COLUMNS[stream]["total"]
        for stream in selected_streams
        if STREAM_COLUMNS[stream]["total"] in df.columns
    ]
    label = " + ".join(STREAM_COLUMNS[item]["label"] for item in selected_streams)
    return numeric_sum(df, columns), label, columns


def coordinate_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    latitude = first_existing_column(df, ["Latitude", "latitude", "LAT", "lat"])
    longitude = first_existing_column(
        df,
        ["Longitude", "Longtitude", "longitude", "longtitude", "LONGITUDE", "LON", "lon", "lng"],
    )
    return latitude, longitude


def valid_coordinate_mask(df: pd.DataFrame) -> pd.Series:
    # Keeps known bad geocodes from dragging county maps across California.
    return (
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
        & df["latitude"].notna()
        & df["longitude"].notna()
        & (df["latitude"] != 0)
        & (df["longitude"] != 0)
        & df["latitude"].between(SLO_MAP_BOUNDS["min_lat"], SLO_MAP_BOUNDS["max_lat"])
        & df["longitude"].between(SLO_MAP_BOUNDS["min_lon"], SLO_MAP_BOUNDS["max_lon"])
    )


def prepare_business_map_frame(
    filtered: pd.DataFrame,
    latitude_column: str,
    longitude_column: str,
    jurisdiction_field: str,
    business_group_field: str,
    business_column: str | None,
) -> pd.DataFrame:
    map_df = filtered.copy()
    map_df["latitude"] = pd.to_numeric(map_df[latitude_column], errors="coerce")
    map_df["longitude"] = pd.to_numeric(map_df[longitude_column], errors="coerce")
    map_df["selected_waste_tons"] = pd.to_numeric(
        map_df["selected_waste_tons"],
        errors="coerce",
    ).fillna(0)
    map_df = map_df[valid_coordinate_mask(map_df)].copy()

    if business_column:
        map_df["business_name"] = map_df[business_column].fillna("Unnamed business").astype(str)
    else:
        map_df["business_name"] = "Unnamed business"
    map_df["jurisdiction"] = map_df[jurisdiction_field].fillna("Unknown jurisdiction").astype(str)
    map_df["business_group"] = map_df[business_group_field].fillna("Unknown business group").astype(str)
    hauler_source = hauler_display_column(map_df)
    map_df["Hauler"] = (
        map_df[hauler_source].fillna("").astype(str).str.strip()
        if hauler_source
        else ""
    )
    map_df["selected_tons"] = map_df["selected_waste_tons"].map(lambda value: f"{value:,.1f}")
    map_df["point_radius"] = np.clip(
        np.sqrt(map_df["selected_waste_tons"].clip(lower=0)) * 4 + 25,
        25,
        260,
    )
    for stream_config in STREAM_COLUMNS.values():
        column = stream_config["total"]
        label = stream_config["label"]
        output_column = f"{label} Tons"
        map_df[output_column] = (
            pd.to_numeric(map_df[column], errors="coerce").fillna(0)
            if column in map_df.columns
            else 0.0
        )
    map_df["stream_fingerprint"] = map_df.apply(row_stream_fingerprint_html, axis=1)
    map_df["tooltip_title"] = map_df["business_name"]
    map_df["tooltip_body"] = (
        map_df["selected_tons"]
        + " tons<br/>"
        + map_df["jurisdiction"]
        + "<br/>"
        + map_df["business_group"]
        + "<br/><span style='font-size:11px;color:#dfe4de;'>Waste stream fingerprint</span>"
        + map_df["stream_fingerprint"]
    )
    keep_columns = [
        "_business_row_id",
        "latitude",
        "longitude",
        "selected_waste_tons",
        "business_name",
        "jurisdiction",
        "business_group",
        "Hauler",
        "Landfill Tons",
        "Recycle Tons",
        "Organics Tons",
        "Diversion Tons",
        "stream_fingerprint",
        "selected_tons",
        "point_radius",
        "tooltip_title",
        "tooltip_body",
    ]
    return map_df[[column for column in keep_columns if column in map_df.columns]].copy()


def map_component_key(prefix: str, map_df: pd.DataFrame) -> str:
    if map_df.empty:
        return f"{prefix}_empty"
    key_columns = [
        column
        for column in [
            "_business_row_id",
            "latitude",
            "longitude",
            "selected_waste_tons",
            "Selected Opportunity Tons",
            "Diversion Opportunity Tons",
        ]
        if column in map_df.columns
    ]
    signature = map_df[key_columns].copy()
    for column in [
        "latitude",
        "longitude",
        "selected_waste_tons",
        "Selected Opportunity Tons",
        "Diversion Opportunity Tons",
    ]:
        if column in signature.columns:
            signature[column] = pd.to_numeric(signature[column], errors="coerce").round(6)
    hashed = pd.util.hash_pandas_object(signature, index=False).values.tobytes()
    digest = hashlib.sha1(hashed).hexdigest()[:14]
    return f"{prefix}_{len(map_df)}_{digest}"


def zoom_from_bounds(map_df: pd.DataFrame) -> float:
    if map_df.empty:
        return 8
    bounds = [
        float(map_df["longitude"].min()),
        float(map_df["latitude"].min()),
        float(map_df["longitude"].max()),
        float(map_df["latitude"].max()),
    ]
    return zoom_from_total_bounds(bounds)


def zoom_from_total_bounds(bounds: list[float] | tuple[float, float, float, float]) -> float:
    min_lon, min_lat, max_lon, max_lat = bounds
    lon_span = max(abs(float(max_lon) - float(min_lon)), 0.002)
    min_lat = float(np.clip(min_lat, -85.0, 85.0))
    max_lat = float(np.clip(max_lat, -85.0, 85.0))
    min_lat_rad = np.radians(min_lat)
    max_lat_rad = np.radians(max_lat)
    min_y = np.log(np.tan(np.pi / 4 + min_lat_rad / 2))
    max_y = np.log(np.tan(np.pi / 4 + max_lat_rad / 2))
    lat_span = max(abs(max_y - min_y) / (2 * np.pi), 0.002 / 360)

    world_pixels = 512
    usable_width = 900 * 0.92
    usable_height = 650 * 0.92
    zoom_lon = np.log2(usable_width * 360 / (lon_span * world_pixels))
    zoom_lat = np.log2(usable_height / (lat_span * world_pixels))
    return float(np.clip(min(zoom_lon, zoom_lat), 6, 15))


def heat_weight(values: pd.Series, scale: str) -> pd.Series:
    clean = values.clip(lower=0).fillna(0)
    if scale == "Square root":
        return np.sqrt(clean)
    if scale == "Log":
        return np.log1p(clean)
    return clean


def heatmap_grid_source(map_df: pd.DataFrame, heat_metric: str, weight_scale: str) -> pd.DataFrame:
    if map_df.empty:
        return pd.DataFrame(columns=["latitude", "longitude", "heat_metric_value", "heat_weight"])
    cell_degrees = 0.015
    grid = map_df.copy()
    grid["_grid_lat"] = np.floor(grid["latitude"].astype(float) / cell_degrees) * cell_degrees
    grid["_grid_lon"] = np.floor(grid["longitude"].astype(float) / cell_degrees) * cell_degrees
    grouped = (
        grid.groupby(["_grid_lat", "_grid_lon"], dropna=False)
        .agg(
            total_tons=("selected_waste_tons", "sum"),
            business_count=("_business_row_id", "nunique"),
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean"),
        )
        .reset_index()
    )
    lat_miles = 69.0 * cell_degrees
    lon_miles = 69.172 * cell_degrees * np.cos(np.radians(grouped["latitude"].astype(float)))
    grouped["cell_area_sq_mi"] = (lat_miles * lon_miles).clip(lower=0.05)
    grouped["tons_per_business"] = np.where(
        grouped["business_count"] > 0,
        grouped["total_tons"] / grouped["business_count"],
        0.0,
    )
    grouped["businesses_per_sq_mi"] = grouped["business_count"] / grouped["cell_area_sq_mi"]
    metric_column = {
        HEATMAP_VOLUME_METRIC: "total_tons",
        HEATMAP_TONS_PER_BUSINESS_METRIC: "tons_per_business",
        HEATMAP_BUSINESSES_PER_SQ_MI_METRIC: "businesses_per_sq_mi",
    }.get(heat_metric, "total_tons")
    grouped["heat_metric_value"] = pd.to_numeric(grouped[metric_column], errors="coerce").fillna(0.0)
    grouped["heat_weight"] = heat_weight(grouped["heat_metric_value"], weight_scale)
    grouped["tooltip_title"] = heat_metric
    grouped["tooltip_body"] = (
        "Total tons: "
        + grouped["total_tons"].map(lambda value: f"{value:,.1f}")
        + "<br/>Businesses: "
        + grouped["business_count"].map(lambda value: f"{int(value):,}")
        + "<br/>Tons per business: "
        + grouped["tons_per_business"].map(lambda value: f"{value:,.1f}")
        + "<br/>Businesses per sq mi: "
        + grouped["businesses_per_sq_mi"].map(lambda value: f"{value:,.1f}")
    )
    return grouped


def heatmap_jurisdiction_kpis(
    filtered: pd.DataFrame,
    selected_jurisdictions: list[str],
    jurisdiction_field: str,
    material_columns: dict[str, dict[str, str]],
    selected_streams: list[str],
    selected_materials: list[str],
    material_mode: str,
) -> pd.DataFrame:
    if not selected_jurisdictions or jurisdiction_field not in filtered.columns:
        return pd.DataFrame()

    rows = []
    for jurisdiction in selected_jurisdictions:
        subset = filtered[filtered[jurisdiction_field].astype(str) == str(jurisdiction)].copy()
        if subset.empty:
            continue
        tons = float(pd.to_numeric(subset["selected_waste_tons"], errors="coerce").fillna(0).sum())
        businesses = int(subset["_business_row_id"].nunique()) if "_business_row_id" in subset.columns else len(subset)
        material_table = material_driver_table(
            subset,
            material_columns,
            selected_streams,
            selected_materials,
            material_mode,
        )
        top_material = str(material_table.iloc[0]["Material"]) if not material_table.empty else "No material tons"
        rows.append(
            {
                "Jurisdiction": str(jurisdiction),
                "Selected Tons": tons,
                "Mapped Businesses": businesses,
                "Tons per Business": tons / businesses if businesses else 0.0,
                "Top Material": top_material,
            }
        )
    return pd.DataFrame(rows)


def render_heatmap_jurisdiction_cards(summary: pd.DataFrame) -> None:
    if summary.empty:
        return

    cards = []
    for _, row in summary.iterrows():
        cards.append(
            "<div style='border:1px solid #dfe4de;border-radius:8px;"
            "background:#f7f8f6;padding:0.75rem 0.8rem;margin-bottom:0.65rem;'>"
            f"<div style='font-size:0.82rem;color:#6e756f;margin-bottom:0.2rem;'>Jurisdiction</div>"
            f"<div style='font-size:1rem;font-weight:750;color:#2f343f;'>{html.escape(str(row['Jurisdiction']))}</div>"
            f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:0.45rem;margin-top:0.65rem;'>"
            f"<div><div style='font-size:0.72rem;color:#6e756f;'>Tons</div>"
            f"<div style='font-weight:725;color:#2f343f;'>{float(row['Selected Tons']):,.1f}</div></div>"
            f"<div><div style='font-size:0.72rem;color:#6e756f;'>Businesses</div>"
            f"<div style='font-weight:725;color:#2f343f;'>{int(row['Mapped Businesses']):,}</div></div>"
            f"<div><div style='font-size:0.72rem;color:#6e756f;'>Tons/business</div>"
            f"<div style='font-weight:725;color:#2f343f;'>{float(row['Tons per Business']):,.1f}</div></div>"
            f"<div><div style='font-size:0.72rem;color:#6e756f;'>Top material</div>"
            f"<div style='font-weight:725;color:#2f343f;'>{html.escape(str(row['Top Material']))}</div></div>"
            "</div></div>"
        )
    st.markdown("".join(cards), unsafe_allow_html=True)


def business_display_column(df: pd.DataFrame) -> str | None:
    return first_existing_column(
        df,
        [
            "SMART1383 Name",
            "Company Name",
            "Global Name",
            "Immediate Parent Name",
            "Domestic Parent Name",
        ],
    )


def address_display_column(df: pd.DataFrame) -> str | None:
    return first_existing_column(
        df,
        [
            "SMART1383 Address",
            "Physical Address",
            "Mailing Address",
        ],
    )


def hauler_display_column(df: pd.DataFrame) -> str | None:
    return first_existing_column(
        df,
        [
            "SMART1383 Hauler",
            "Hauler",
            "hauler",
            "calrecycle_hauler",
        ],
    )


def normalize_hauler_text(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def hauler_facility_rule(value) -> str:
    hauler = normalize_hauler_text(value)
    if not hauler:
        return ""
    if "waste connections" in hauler:
        return "Cold Canyon Landfill"
    if "waste management" in hauler or hauler == "wm" or hauler.startswith("wm "):
        return "Chicago Grade Landfill"
    if "paso robles waste" in hauler or "san miguel garbage" in hauler:
        return "City of Paso Robles Landfill"
    return ""


def hauler_rule_reference_table() -> pd.DataFrame:
    return pd.DataFrame(HAULER_FACILITY_RULES)


def contact_display_columns(df: pd.DataFrame) -> dict[str, str]:
    candidates = {
        "Phone": ["Phone No", "Phone", "Business Phone", "Telephone", "Contact Phone"],
        "Email": ["Email", "Email Address", "Business Email", "Contact Email"],
        "Website": ["Web Address (URL)", "Website", "Web Address", "URL"],
    }
    columns: dict[str, str] = {}
    for label, names in candidates.items():
        column = first_existing_column(df, names)
        if column:
            columns[label] = column
    return columns


def add_business_contact_fields(output_columns: dict[str, pd.Series], df: pd.DataFrame) -> None:
    hauler_source = hauler_display_column(df)
    if hauler_source:
        output_columns["Hauler"] = df[hauler_source]
    for label, column in contact_display_columns(df).items():
        output_columns[label] = df[column]


def zipcode_display_column(df: pd.DataFrame) -> str | None:
    return first_existing_column(
        df,
        [
            "Physical Zipcode",
            "Mailing Zipcode",
            "SMART1383 Zipcode",
            "Zipcode",
            "ZIP",
            "Zip",
        ],
    )


def census_block_group_url(year: str, state_fips: str) -> str:
    state = state_fips.zfill(2)
    return f"https://www2.census.gov/geo/tiger/TIGER{year}/BG/tl_{year}_{state}_bg.zip"


def default_census_zip_path(year: str, state_fips: str) -> Path:
    state = state_fips.zfill(2)
    return TIGER_DIR / f"tl_{year}_{state}_bg.zip"


def bundled_slo_block_group_path() -> Path:
    """Return the packaged SLO County boundary file, when present.

    The demo must remain usable when the Census download host is unavailable.
    """
    return BOUNDARY_DIR / "slo_county_block_groups_2023.geojson"


def census_zcta_url(year: str) -> str:
    return f"https://www2.census.gov/geo/tiger/GENZ{year}/shp/cb_{year}_us_zcta520_500k.zip"


def default_zcta_zip_path(year: str) -> Path:
    return TIGER_DIR / f"cb_{year}_us_zcta520_500k.zip"


def census_place_url(year: str, state_fips: str) -> str:
    state = state_fips.zfill(2)
    return f"https://www2.census.gov/geo/tiger/TIGER{year}/PLACE/tl_{year}_{state}_place.zip"


def census_roads_url(year: str, state_fips: str, county_fips: str) -> str:
    state = state_fips.zfill(2)
    county = county_fips.zfill(3)
    return f"https://www2.census.gov/geo/tiger/TIGER{year}/ROADS/tl_{year}_{state}{county}_roads.zip"


def default_place_zip_path(year: str, state_fips: str) -> Path:
    state = state_fips.zfill(2)
    return TIGER_DIR / f"tl_{year}_{state}_place.zip"


def default_roads_zip_path(year: str, state_fips: str, county_fips: str) -> Path:
    state = state_fips.zfill(2)
    county = county_fips.zfill(3)
    return TIGER_DIR / f"tl_{year}_{state}{county}_roads.zip"


def ensure_url_zip(path: Path, download_url: str) -> Path:
    TIGER_DIR.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return path

    temp_path = path.with_suffix(".download")
    if temp_path.exists():
        temp_path.unlink()
    try:
        urllib.request.urlretrieve(download_url, temp_path)
        temp_path.replace(path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise
    return path


def ensure_census_block_group_zip(year: str, state_fips: str) -> Path:
    bundled_path = bundled_slo_block_group_path()
    if bundled_path.exists() and bundled_path.stat().st_size > 0:
        return bundled_path
    zip_path = default_census_zip_path(year, state_fips)
    return ensure_url_zip(zip_path, census_block_group_url(year, state_fips))


def ensure_zcta_zip(year: str) -> Path:
    zip_path = default_zcta_zip_path(year)
    return ensure_url_zip(zip_path, census_zcta_url(year))


def ensure_place_zip(year: str, state_fips: str) -> Path:
    zip_path = default_place_zip_path(year, state_fips)
    return ensure_url_zip(zip_path, census_place_url(year, state_fips))


def ensure_census_roads_zip(year: str, state_fips: str, county_fips: str) -> Path:
    zip_path = default_roads_zip_path(year, state_fips, county_fips)
    return ensure_url_zip(zip_path, census_roads_url(year, state_fips, county_fips))


def geopandas_source_path(path_text: str) -> str:
    path = Path(path_text).expanduser().resolve()
    return str(path)


@st.cache_data(show_spinner="Reading census block groups...")
def load_block_groups_from_file(
    path_text: str,
    county_fips: str,
) -> object:
    gpd = import_geopandas()
    source_path = Path(path_text).expanduser().resolve()
    cache_path = disk_cache_path(
        "block_groups",
        hashlib.sha256(
            f"{path_signature(source_path)}|county={county_fips.zfill(3)}".encode("utf-8")
        ).hexdigest()[:24],
        ".geojson",
    )
    if cache_path.exists():
        return gpd.read_file(str(cache_path))

    block_groups = gpd.read_file(geopandas_source_path(path_text))

    if "COUNTYFP" not in block_groups.columns:
        raise ValueError("The boundary file does not include a COUNTYFP field.")
    if "GEOID" not in block_groups.columns:
        raise ValueError("The boundary file does not include a GEOID field.")

    block_groups["COUNTYFP"] = block_groups["COUNTYFP"].astype(str).str.zfill(3)
    block_groups = block_groups[block_groups["COUNTYFP"] == county_fips.zfill(3)].copy()
    if block_groups.empty:
        raise ValueError(f"No block groups were found for county FIPS {county_fips}.")

    if block_groups.crs is None:
        block_groups = block_groups.set_crs("EPSG:4269")

    area_frame = block_groups.to_crs("EPSG:3310")
    block_groups["area_sq_mi"] = area_frame.geometry.area / 2_589_988.110336
    block_groups = block_groups.to_crs("EPSG:4326")

    keep_columns = [
        column
        for column in ["STATEFP", "COUNTYFP", "TRACTCE", "BLKGRPCE", "GEOID", "NAMELSAD", "area_sq_mi", "geometry"]
        if column in block_groups.columns
    ]
    block_groups = block_groups[keep_columns].copy()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        block_groups.to_file(str(cache_path), driver="GeoJSON")
    except Exception:
        pass
    return block_groups


def county_geometry_wkt(block_groups) -> str:
    if hasattr(block_groups.geometry, "union_all"):
        return block_groups.geometry.union_all().wkt
    return block_groups.geometry.unary_union.wkt


@st.cache_data(show_spinner="Reading ZIP Code Tabulation Areas...")
def load_zctas_for_county(path_text: str, county_wkt: str, simplify_tolerance: float) -> object:
    gpd = import_geopandas()
    from shapely import wkt

    source_path = Path(path_text).expanduser().resolve()
    cache_path = disk_cache_path(
        "zcta_boundaries",
        hashlib.sha256(
            f"{path_signature(source_path)}|county={hashlib.sha1(county_wkt.encode('utf-8')).hexdigest()}|tol={simplify_tolerance}".encode(
                "utf-8"
            )
        ).hexdigest()[:24],
        ".geojson",
    )
    if cache_path.exists():
        return gpd.read_file(str(cache_path))

    zctas = gpd.read_file(str(source_path))
    if zctas.crs is None:
        zctas = zctas.set_crs("EPSG:4269")
    zctas = zctas.to_crs("EPSG:4326")
    county = gpd.GeoSeries([wkt.loads(county_wkt)], crs="EPSG:4326")
    zctas = zctas[zctas.intersects(county.iloc[0])].copy()
    name_column = "ZCTA5CE20" if "ZCTA5CE20" in zctas.columns else "GEOID20" if "GEOID20" in zctas.columns else None
    if name_column is None:
        name_column = "GEOID" if "GEOID" in zctas.columns else zctas.columns[0]
    zctas["boundary_name"] = zctas[name_column].astype(str)
    zctas["boundary_type"] = "ZIP / ZCTA"
    if simplify_tolerance > 0:
        zctas["geometry"] = zctas.geometry.simplify(simplify_tolerance, preserve_topology=True)
    zctas = zctas[["boundary_name", "boundary_type", "geometry"]].copy()
    try:
        zctas.to_file(str(cache_path), driver="GeoJSON")
    except Exception:
        pass
    return zctas


@st.cache_data(show_spinner="Reading jurisdiction/community boundaries...")
def load_places_for_county(path_text: str, county_wkt: str, simplify_tolerance: float) -> object:
    gpd = import_geopandas()
    from shapely import wkt

    source_path = Path(path_text).expanduser().resolve()
    cache_path = disk_cache_path(
        "place_boundaries",
        hashlib.sha256(
            f"{path_signature(source_path)}|county={hashlib.sha1(county_wkt.encode('utf-8')).hexdigest()}|tol={simplify_tolerance}".encode(
                "utf-8"
            )
        ).hexdigest()[:24],
        ".geojson",
    )
    if cache_path.exists():
        return gpd.read_file(str(cache_path))

    places = gpd.read_file(str(source_path))
    if places.crs is None:
        places = places.set_crs("EPSG:4269")
    places = places.to_crs("EPSG:4326")
    county = gpd.GeoSeries([wkt.loads(county_wkt)], crs="EPSG:4326")
    places = places[places.intersects(county.iloc[0])].copy()
    if "NAME" in places.columns:
        places = places[places["NAME"].astype(str).isin(SLO_JURISDICTION_PLACE_NAMES)].copy()
        places["boundary_name"] = places["NAME"].astype(str)
    else:
        places["boundary_name"] = "Jurisdiction/community"
    places["boundary_type"] = "Jurisdiction/community"
    if simplify_tolerance > 0:
        places["geometry"] = places.geometry.simplify(simplify_tolerance, preserve_topology=True)
    places = places[["boundary_name", "boundary_type", "geometry"]].copy()
    try:
        places.to_file(str(cache_path), driver="GeoJSON")
    except Exception:
        pass
    return places


def most_common_text(series: pd.Series) -> str:
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]
    if values.empty:
        return ""
    return str(values.value_counts().index[0])


def spatially_join_businesses_to_block_groups(
    map_df: pd.DataFrame,
    block_groups,
    jurisdiction_field: str,
    business_group_field: str,
):
    gpd = import_geopandas()
    points = gpd.GeoDataFrame(
        map_df.copy(),
        geometry=gpd.points_from_xy(map_df["longitude"], map_df["latitude"]),
        crs="EPSG:4326",
    )
    join_columns = ["GEOID", "NAMELSAD", "area_sq_mi", "geometry"]
    joined = gpd.sjoin(
        points,
        block_groups[join_columns],
        how="left",
        predicate="within",
    )
    joined["matched_block_group"] = joined["GEOID"].notna()
    joined["jurisdiction_rollup"] = joined[jurisdiction_field].fillna("").astype(str)
    joined["business_group_rollup"] = joined[business_group_field].fillna("").astype(str)
    return joined


@st.cache_data(show_spinner="Building block group lookup...")
def build_business_block_group_lookup(
    coords: pd.DataFrame,
    _block_groups,
    block_group_cache_key: str,
) -> pd.DataFrame:
    gpd = import_geopandas()
    cache_key = coordinates_signature(coords, block_group_cache_key)
    cache_path = disk_cache_path("business_block_lookup", cache_key, ".pkl")
    if cache_path.exists():
        return pd.read_pickle(cache_path)

    clean_coords = coords.copy()
    clean_coords["latitude"] = pd.to_numeric(clean_coords["latitude"], errors="coerce")
    clean_coords["longitude"] = pd.to_numeric(clean_coords["longitude"], errors="coerce")
    clean_coords = clean_coords[valid_coordinate_mask(clean_coords)].copy()

    if clean_coords.empty:
        lookup = pd.DataFrame(columns=["_business_row_id", "GEOID", "NAMELSAD"])
        write_pickle_cache(lookup, cache_path)
        return lookup

    points = gpd.GeoDataFrame(
        clean_coords,
        geometry=gpd.points_from_xy(clean_coords["longitude"], clean_coords["latitude"]),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(
        points,
        _block_groups[["GEOID", "NAMELSAD", "geometry"]],
        how="left",
        predicate="within",
    )
    lookup = joined[["_business_row_id", "GEOID", "NAMELSAD"]].copy()
    write_pickle_cache(lookup, cache_path)
    return lookup


def attach_block_group_lookup(map_df: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    joined = map_df.merge(lookup, on="_business_row_id", how="left")
    joined["matched_block_group"] = joined["GEOID"].notna()
    joined["jurisdiction_rollup"] = joined["jurisdiction"].fillna("").astype(str)
    joined["business_group_rollup"] = joined["business_group"].fillna("").astype(str)
    return joined


def aggregate_block_groups(joined, block_groups):
    valid = joined[joined["matched_block_group"]].copy()

    if valid.empty:
        block_summary = block_groups.copy()
        block_summary["total_waste_tons"] = 0.0
        block_summary["business_count"] = 0
        block_summary["avg_tons_per_business"] = 0.0
        block_summary["top_jurisdiction"] = ""
        block_summary["top_business_group"] = ""
    else:
        summary = (
            valid.groupby("GEOID")
            .agg(
                total_waste_tons=("selected_waste_tons", "sum"),
                business_count=("selected_waste_tons", "size"),
                avg_tons_per_business=("selected_waste_tons", "mean"),
            )
            .reset_index()
        )
        top_jurisdiction = valid.groupby("GEOID")["jurisdiction_rollup"].agg(most_common_text).reset_index()
        top_business_group = valid.groupby("GEOID")["business_group_rollup"].agg(most_common_text).reset_index()
        summary = summary.merge(top_jurisdiction, on="GEOID", how="left")
        summary = summary.merge(top_business_group, on="GEOID", how="left")
        summary = summary.rename(
            columns={
                "jurisdiction_rollup": "top_jurisdiction",
                "business_group_rollup": "top_business_group",
            }
        )
        block_summary = block_groups.merge(summary, on="GEOID", how="left")

    block_summary["total_waste_tons"] = block_summary["total_waste_tons"].fillna(0.0)
    block_summary["business_count"] = block_summary["business_count"].fillna(0).astype(int)
    block_summary["avg_tons_per_business"] = block_summary["avg_tons_per_business"].fillna(0.0)
    block_summary["top_jurisdiction"] = block_summary["top_jurisdiction"].fillna("")
    block_summary["top_business_group"] = block_summary["top_business_group"].fillna("")

    block_summary["tons_per_sq_mi"] = np.where(
        block_summary["area_sq_mi"] > 0,
        block_summary["total_waste_tons"] / block_summary["area_sq_mi"],
        0.0,
    )
    block_summary["businesses_per_sq_mi"] = np.where(
        block_summary["area_sq_mi"] > 0,
        block_summary["business_count"] / block_summary["area_sq_mi"],
        0.0,
    )
    return block_summary


def add_block_group_top_material_group(
    block_summary: pd.DataFrame,
    filtered: pd.DataFrame,
    block_group_lookup: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
    selected_streams: list[str],
    selected_materials: list[str],
    material_mode: str,
) -> pd.DataFrame:
    if filtered.empty or block_group_lookup.empty or block_summary.empty:
        output = block_summary.copy()
        output["top_material_group"] = ""
        return output

    material_keys = selected_materials or sorted(material_columns)
    rows = []
    for material in material_keys:
        columns = []
        if selected_materials and material_mode == "Material totals":
            column = material_columns.get(material, {}).get("total_generation")
            if column:
                columns.append(column)
        else:
            for stream in selected_streams:
                column = material_columns.get(material, {}).get(stream)
                if column:
                    columns.append(column)
        columns = [column for column in columns if column in filtered.columns]
        if not columns:
            continue
        tons = numeric_sum(filtered, columns)
        if float(tons.sum()) <= 0:
            continue
        rows.append(
            pd.DataFrame(
                {
                    "_business_row_id": filtered["_business_row_id"],
                    "material_group": material_group(material),
                    "tons": tons,
                }
            )
        )

    output = block_summary.copy()
    if not rows:
        output["top_material_group"] = ""
        return output

    material_by_business = pd.concat(rows, ignore_index=True)
    material_by_business = material_by_business[material_by_business["tons"] > 0].copy()
    material_by_business = material_by_business.merge(
        block_group_lookup[["_business_row_id", "GEOID"]],
        on="_business_row_id",
        how="left",
    )
    material_by_business = material_by_business[material_by_business["GEOID"].notna()].copy()
    if material_by_business.empty:
        output["top_material_group"] = ""
        return output

    grouped = (
        material_by_business.groupby(["GEOID", "material_group"], dropna=False)["tons"]
        .sum()
        .reset_index()
        .sort_values(["GEOID", "tons"], ascending=[True, False])
    )
    top_groups = grouped.drop_duplicates("GEOID").set_index("GEOID")["material_group"]
    output["top_material_group"] = output["GEOID"].map(top_groups).fillna("")
    return output


def interpolate_color(start: tuple[int, int, int], end: tuple[int, int, int], amount: float) -> list[int]:
    amount = min(max(float(amount), 0.0), 1.0)
    return [round(start[index] + (end[index] - start[index]) * amount) for index in range(3)]


def metric_color(value: float, cap: float) -> list[int]:
    if value <= 0 or cap <= 0:
        return [229, 233, 229, 78]
    scaled = min(float(value) / cap, 1.0)
    if scaled <= 0.5:
        rgb = interpolate_color((199, 232, 219), (242, 195, 82), scaled / 0.5)
    else:
        rgb = interpolate_color((242, 195, 82), (177, 68, 48), (scaled - 0.5) / 0.5)
    return rgb + [162]


def css_color(color: list[int] | tuple[int, ...]) -> str:
    alpha = color[3] / 255 if len(color) > 3 else 1
    return f"rgba({color[0]}, {color[1]}, {color[2]}, {alpha:.3f})"


def legend_swatch(label: str, color: list[int] | tuple[int, ...], kind: str = "box") -> str:
    escaped_label = html.escape(label)
    background = css_color(color)
    if kind == "dot":
        swatch_style = (
            "width:12px;height:12px;border-radius:50%;"
            f"background:{background};border:1px solid rgba(47,52,63,0.28);"
        )
    elif kind == "line":
        swatch_style = (
            "width:26px;height:4px;border-radius:999px;"
            f"background:{background};border:1px solid rgba(47,52,63,0.18);"
        )
    else:
        swatch_style = (
            "width:15px;height:15px;border-radius:3px;"
            f"background:{background};border:1px solid rgba(47,52,63,0.2);"
        )
    return (
        '<span style="display:inline-flex;align-items:center;gap:0.35rem;'
        'white-space:nowrap;color:#2f343f;font-size:0.88rem;">'
        f'<span style="{swatch_style}"></span>{escaped_label}</span>'
    )


def render_map_legend(
    title: str,
    items: list[tuple[str, list[int] | tuple[int, ...], str]],
    gradient: tuple[str, list[list[int]], str] | None = None,
    note: str | None = None,
) -> None:
    item_html = "".join(legend_swatch(label, color, kind) for label, color, kind in items)
    gradient_html = ""
    if gradient:
        low_label, gradient_colors, high_label = gradient
        stops = ", ".join(css_color(color) for color in gradient_colors)
        gradient_html = (
            '<span style="display:inline-flex;align-items:center;gap:0.45rem;'
            'white-space:nowrap;color:#2f343f;font-size:0.88rem;">'
            f"{html.escape(low_label)}"
            f'<span style="width:136px;height:12px;border-radius:999px;'
            f'background:linear-gradient(90deg,{stops});'
            'border:1px solid rgba(47,52,63,0.18);"></span>'
            f"{html.escape(high_label)}</span>"
        )
    note_html = (
        f'<span style="color:#6e756f;font-size:0.82rem;">{html.escape(note)}</span>'
        if note
        else ""
    )
    legend_html = (
        '<div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;'
        'margin:0.45rem 0 0.75rem 0;padding:0.55rem 0.7rem;'
        'border:1px solid #dfe4de;border-radius:8px;background:#f7f8f6;">'
        f'<span style="font-weight:650;color:#2f343f;font-size:0.9rem;">{html.escape(title)}</span>'
        f"{gradient_html}{item_html}{note_html}"
        "</div>"
    )
    st.markdown(legend_html, unsafe_allow_html=True)


def render_heatmap_legend(metric_label: str, heat_metric: str) -> None:
    render_map_legend(
        "Map legend",
        [("Business point", [27, 96, 86, 150], "dot")],
        gradient=(
            "Lower heat",
            [[255, 255, 178, 210], [254, 204, 92, 220], [253, 141, 60, 225], [189, 0, 38, 225]],
            "Higher heat",
        ),
        note=f"Heat compares {heat_metric.lower()}; business dots and tables still use {metric_label.lower()}.",
    )


def render_block_group_legend(metric_name: str, show_business_points: bool, selected_geoid: str | None) -> None:
    items: list[tuple[str, list[int] | tuple[int, ...], str]] = []
    if show_business_points:
        items.append(("Business point", [28, 79, 96, 110], "dot"))
    if selected_geoid:
        items.append(("Selected outline", [0, 126, 255, 255], "line"))
    render_map_legend(
        "Block group color",
        items,
        gradient=("Lower", [[199, 232, 219, 162], [242, 195, 82, 162], [177, 68, 48, 162]], "Higher"),
        note=metric_name,
    )


def render_diversion_map_legend(selected_destinations: list[str], requested_boundaries: list[str]) -> None:
    items = [
        (destination_label(destination), DESTINATION_STREAMS[destination]["color"], "dot")
        for destination in selected_destinations
        if destination in DESTINATION_STREAMS
    ]
    boundary_items = {
        "Census block groups": ("Block group boundary", [78, 86, 82, 170], "line"),
        "ZIP / ZCTA": ("ZIP / ZCTA boundary", [44, 96, 142, 190], "line"),
        "Jurisdiction/community": ("Jurisdiction/community boundary", [121, 78, 35, 200], "line"),
    }
    for boundary_name in requested_boundaries:
        if boundary_name in boundary_items:
            items.append(boundary_items[boundary_name])
    render_map_legend(
        "Map legend",
        items,
        note="Dot color shows each business's dominant selected opportunity stream.",
    )


def format_metric_value(metric_name: str, value: float) -> str:
    if metric_name in {"Business count"}:
        return f"{value:,.0f}"
    if "per sq mi" in metric_name:
        return f"{value:,.1f}"
    return f"{value:,.1f}"


def style_block_groups(block_summary, metric_name: str, selected_geoid: str | None):
    metric_column = BLOCK_GROUP_METRICS[metric_name]
    styled = block_summary.copy()
    styled["is_selected"] = styled["GEOID"].astype(str) == str(selected_geoid)
    values = pd.to_numeric(styled[metric_column], errors="coerce").fillna(0)
    positive = values[values > 0]
    cap = float(positive.quantile(0.95)) if not positive.empty else 0.0
    if cap <= 0 and not positive.empty:
        cap = float(positive.max())

    colors = [
        metric_color(float(value), cap)
        for value in values
    ]
    colors = [
        color[:3] + [min(color[3] + 35, 205)] if is_selected else color
        for color, is_selected in zip(colors, styled["is_selected"])
    ]
    styled["fill_r"] = [color[0] for color in colors]
    styled["fill_g"] = [color[1] for color in colors]
    styled["fill_b"] = [color[2] for color in colors]
    styled["fill_a"] = [color[3] for color in colors]
    styled["line_r"] = np.where(styled["is_selected"], 0, 69)
    styled["line_g"] = np.where(styled["is_selected"], 126, 79)
    styled["line_b"] = np.where(styled["is_selected"], 255, 72)
    styled["line_a"] = np.where(styled["is_selected"], 255, 120)
    styled["line_width"] = np.where(styled["is_selected"], 5, 1)
    styled["metric_display"] = [
        f"{metric_name}: {format_metric_value(metric_name, value)}"
        for value in values
    ]
    styled["tooltip_title"] = styled.get("NAMELSAD", styled["GEOID"]).fillna(styled["GEOID"]).astype(str)
    styled["tooltip_body"] = (
        "GEOID: "
        + styled["GEOID"].astype(str)
        + "<br/>"
        + styled["metric_display"]
        + "<br/>Selected tons: "
        + styled["total_waste_tons"].map(lambda value: f"{value:,.1f}")
        + "<br/>Businesses: "
        + styled["business_count"].map(lambda value: f"{value:,}")
    )
    return styled


def build_business_heat_map(
    map_df: pd.DataFrame,
    heat_df: pd.DataFrame,
    radius_pixels: int,
    intensity: float,
    threshold: float,
) -> pdk.Deck:
    min_lon = float(map_df["longitude"].min())
    max_lon = float(map_df["longitude"].max())
    min_lat = float(map_df["latitude"].min())
    max_lat = float(map_df["latitude"].max())
    center_lat = float((min_lat + max_lat) / 2)
    center_lon = float((min_lon + max_lon) / 2)
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_from_bounds(map_df),
        pitch=0,
        bearing=0,
    )

    heat_source = heat_df.copy() if heat_df is not None and not heat_df.empty else map_df.copy()
    if "heat_weight" not in heat_source.columns:
        heat_source["heat_weight"] = pd.to_numeric(
            heat_source.get("selected_waste_tons", 0),
            errors="coerce",
        ).fillna(0)

    heat_layer = pdk.Layer(
        "HeatmapLayer",
        data=heat_source,
        get_position="[longitude, latitude]",
        get_weight="heat_weight",
        radiusPixels=radius_pixels,
        intensity=intensity,
        threshold=threshold,
        aggregation="SUM",
    )

    point_layer = pdk.Layer(
        "ScatterplotLayer",
        id="heatmap-business-points",
        data=map_df,
        get_position="[longitude, latitude]",
        get_radius="point_radius",
        radius_min_pixels=2,
        radius_max_pixels=13,
        get_fill_color="[27, 96, 86, 88]",
        get_line_color="[255, 255, 255, 170]",
        line_width_min_pixels=0.5,
        pickable=True,
    )

    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=[heat_layer, point_layer],
        tooltip={
            "html": "<b>{tooltip_title}</b><br/>{tooltip_body}",
            "style": {
                "backgroundColor": "rgba(34, 42, 38, 0.94)",
                "color": "white",
                "fontFamily": "Arial",
                "fontSize": "12px",
            },
        },
    )


def build_block_group_map(
    block_summary,
    metric_name: str,
    map_df: pd.DataFrame,
    show_business_points: bool,
    simplify_tolerance: float,
    selected_geoid: str | None,
) -> pdk.Deck:
    styled_blocks = style_block_groups(block_summary, metric_name, selected_geoid)
    if simplify_tolerance > 0:
        styled_blocks["geometry"] = styled_blocks.geometry.simplify(
            simplify_tolerance,
            preserve_topology=True,
        )
    selected_blocks = styled_blocks[styled_blocks["GEOID"].astype(str) == str(selected_geoid)]
    bounds = selected_blocks.total_bounds if not selected_blocks.empty else styled_blocks.total_bounds
    center_lon = float((bounds[0] + bounds[2]) / 2)
    center_lat = float((bounds[1] + bounds[3]) / 2)
    zoom = zoom_from_total_bounds(bounds)
    if not selected_blocks.empty:
        zoom = float(np.clip(zoom - 0.35, 7, 12.2))
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
        pitch=0,
        bearing=0,
    )

    geojson_columns = [
        "GEOID",
        "NAMELSAD",
        "total_waste_tons",
        "business_count",
        "avg_tons_per_business",
        "tons_per_sq_mi",
        "businesses_per_sq_mi",
        "fill_r",
        "fill_g",
        "fill_b",
        "fill_a",
        "line_r",
        "line_g",
        "line_b",
        "line_a",
        "line_width",
        "tooltip_title",
        "tooltip_body",
        "geometry",
    ]
    geojson = json.loads(styled_blocks[geojson_columns].to_json())

    layers = [
        pdk.Layer(
            "GeoJsonLayer",
            id="block-groups",
            data=geojson,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
            get_fill_color="[properties.fill_r, properties.fill_g, properties.fill_b, properties.fill_a]",
            get_line_color="[properties.line_r, properties.line_g, properties.line_b, properties.line_a]",
            get_line_width="properties.line_width",
            line_width_min_pixels=1,
            line_width_max_pixels=5,
        )
    ]

    if show_business_points and not map_df.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="business-points",
                data=map_df,
                get_position="[longitude, latitude]",
                get_radius="point_radius",
                radius_min_pixels=2,
                radius_max_pixels=5,
                get_fill_color="[28, 79, 96, 82]",
                get_line_color="[255, 255, 255, 105]",
                line_width_min_pixels=0.5,
                pickable=True,
                auto_highlight=True,
            )
        )

    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=layers,
        tooltip={
            "html": "<b>{tooltip_title}</b><br/>{tooltip_body}",
            "style": {
                "backgroundColor": "rgba(34, 42, 38, 0.94)",
                "color": "white",
                "fontFamily": "Arial",
                "fontSize": "12px",
            },
        },
    )


def filtered_business_table(
    filtered: pd.DataFrame,
    business_column: str | None,
    address_column: str | None,
    jurisdiction_field: str,
    business_group_field: str,
    latitude_column: str,
    longitude_column: str,
    include_row_id: bool = False,
) -> pd.DataFrame:
    output_columns: dict[str, pd.Series] = {}

    if include_row_id and "_business_row_id" in filtered.columns:
        output_columns["Business Row ID"] = filtered["_business_row_id"]

    business_source = business_column if business_column in filtered.columns else None
    if business_source is None and "business_name" in filtered.columns:
        business_source = "business_name"
    if business_source:
        output_columns["Business"] = filtered[business_source]

    jurisdiction_source = jurisdiction_field if jurisdiction_field in filtered.columns else None
    if jurisdiction_source is None and "jurisdiction" in filtered.columns:
        jurisdiction_source = "jurisdiction"
    if jurisdiction_source:
        output_columns["Jurisdiction"] = filtered[jurisdiction_source]

    business_group_source = business_group_field if business_group_field in filtered.columns else None
    if business_group_source is None and "business_group" in filtered.columns:
        business_group_source = "business_group"
    if business_group_source:
        output_columns["Business Group"] = filtered[business_group_source]

    if address_column and address_column in filtered.columns:
        output_columns["Address"] = filtered[address_column]

    add_business_contact_fields(output_columns, filtered)

    if "selected_waste_tons" in filtered.columns:
        output_columns["Selected Waste Tons"] = filtered["selected_waste_tons"]

    table = pd.DataFrame(output_columns, index=filtered.index).copy()
    if "Selected Waste Tons" not in table.columns:
        table["Selected Waste Tons"] = 0.0
    return table.sort_values("Selected Waste Tons", ascending=False)


def block_group_ranking_table(block_summary, metric_name: str, include_empty: bool) -> pd.DataFrame:
    metric_column = BLOCK_GROUP_METRICS[metric_name]
    table = block_summary.copy()
    if not include_empty:
        table = table[table["business_count"] > 0]
    columns = [
        column
        for column in [
            "GEOID",
            "NAMELSAD",
            "total_waste_tons",
            "business_count",
            "avg_tons_per_business",
            "area_sq_mi",
            "tons_per_sq_mi",
            "businesses_per_sq_mi",
            "top_material_group",
            "top_jurisdiction",
            "top_business_group",
        ]
        if column in table.columns
    ]
    table = table[columns].copy()
    table = table.rename(
        columns={
            "GEOID": "Block Group GEOID",
            "NAMELSAD": "Block Group",
            "total_waste_tons": "Selected Waste Tons",
            "business_count": "Businesses",
            "avg_tons_per_business": "Avg Tons per Business",
            "area_sq_mi": "Area Sq Mi",
            "tons_per_sq_mi": "Tons per Sq Mi",
            "businesses_per_sq_mi": "Businesses per Sq Mi",
            "top_material_group": "Top Material Group",
            "top_jurisdiction": "Top Jurisdiction",
            "top_business_group": "Top Business Group",
        }
    )
    metric_display_column = {
        "total_waste_tons": "Selected Waste Tons",
        "business_count": "Businesses",
        "avg_tons_per_business": "Avg Tons per Business",
        "tons_per_sq_mi": "Tons per Sq Mi",
        "businesses_per_sq_mi": "Businesses per Sq Mi",
    }[metric_column]
    return table.sort_values(metric_display_column, ascending=False)


def selected_geoid_from_pydeck_event(event) -> str | None:
    try:
        objects = event.selection.get("objects", {})
    except Exception:
        return None

    block_objects = objects.get("block-groups", [])
    business_objects = objects.get("business-points", [])
    selected_object = block_objects[0] if block_objects else business_objects[0] if business_objects else None
    if not selected_object:
        return None

    properties = selected_object.get("properties", selected_object)
    geoid = properties.get("GEOID")
    if geoid is None or pd.isna(geoid) or str(geoid).strip() == "":
        return None
    return str(geoid)


def selected_business_id_from_pydeck_event(event) -> int | None:
    try:
        objects = event.selection.get("objects", {})
    except Exception:
        return None

    business_objects = objects.get("heatmap-business-points", [])
    if not business_objects:
        return None
    selected_object = business_objects[0]
    properties = selected_object.get("properties", selected_object)
    row_id = properties.get("_business_row_id")
    if row_id is None or pd.isna(row_id):
        return None
    try:
        return int(row_id)
    except (TypeError, ValueError):
        return None


def selected_block_group_label(block_summary, selected_geoid: str | None) -> str:
    if not selected_geoid:
        return ""
    selected = block_summary[block_summary["GEOID"].astype(str) == str(selected_geoid)]
    if selected.empty:
        return str(selected_geoid)
    row = selected.iloc[0]
    name = str(row.get("NAMELSAD", "")).strip()
    tract = str(row.get("TRACTCE", "")).strip()
    tract_label = f"Tract {tract[:4]}.{tract[4:]}" if len(tract) == 6 else ""
    geoid_label = f"GEOID {selected_geoid}"
    parts = [part for part in [name, tract_label, geoid_label] if part]
    return " | ".join(parts)


def selected_block_group_metric_row(block_summary, selected_geoid: str | None) -> pd.Series | None:
    if not selected_geoid:
        return None
    selected = block_summary[block_summary["GEOID"].astype(str) == str(selected_geoid)]
    if selected.empty:
        return None
    return selected.iloc[0]


def material_driver_table(
    selected_businesses: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
    selected_streams: list[str],
    selected_materials: list[str],
    material_mode: str,
) -> pd.DataFrame:
    material_keys = selected_materials or sorted(material_columns)
    rows = []
    for material in material_keys:
        columns: list[str] = []
        if selected_materials and material_mode == "Material totals":
            column = material_columns.get(material, {}).get("total_generation")
            if column:
                columns.append(column)
        else:
            for stream in selected_streams:
                column = material_columns.get(material, {}).get(stream)
                if column:
                    columns.append(column)

        if not columns:
            continue

        tons = numeric_sum(selected_businesses, columns).sum()
        if tons <= 0:
            continue

        rows.append(
            {
                "Material Group": material_group(material),
                "Material": format_material_name(material),
                "Selected Waste Tons": float(tons),
            }
        )

    if not rows:
        return pd.DataFrame(columns=["Material Group", "Material", "Selected Waste Tons"])
    return pd.DataFrame(rows).sort_values("Selected Waste Tons", ascending=False)


def compact_chart_label(value: object, max_length: int = 38) -> str:
    text = str(value).strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def pareto_frame(
    raw_table: pd.DataFrame,
    item_column: str,
    value_column: str = "Selected Waste Tons",
) -> pd.DataFrame:
    output_columns = ["Rank", item_column, value_column, "Share of Tons", "Cumulative Share", "Vital Few"]
    if raw_table.empty or item_column not in raw_table.columns or value_column not in raw_table.columns:
        return pd.DataFrame(columns=output_columns)

    table = raw_table.copy()
    table[item_column] = table[item_column].fillna("Unknown").astype(str).str.strip()
    table[item_column] = table[item_column].replace("", "Unknown")
    table[value_column] = pd.to_numeric(table[value_column], errors="coerce").fillna(0)
    table = table[table[value_column] > 0].sort_values(value_column, ascending=False).reset_index(drop=True)
    if table.empty:
        return pd.DataFrame(columns=output_columns)

    total = float(table[value_column].sum())
    table.insert(0, "Rank", np.arange(1, len(table) + 1))
    table["Share of Tons"] = table[value_column] / total * 100 if total > 0 else 0.0
    table["Cumulative Share"] = table["Share of Tons"].cumsum()
    threshold_rows = table.loc[table["Cumulative Share"] >= VITAL_FEW_THRESHOLD, "Rank"]
    threshold_rank = int(threshold_rows.iloc[0]) if not threshold_rows.empty else len(table)
    table["Vital Few"] = table["Rank"] <= threshold_rank
    return table


def material_pareto_table(
    selected_businesses: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
    selected_streams: list[str],
    selected_materials: list[str],
    material_mode: str,
) -> pd.DataFrame:
    return pareto_frame(
        material_driver_table(
            selected_businesses,
            material_columns,
            selected_streams,
            selected_materials,
            material_mode,
        ),
        "Material",
    )


def source_column(df: pd.DataFrame, preferred_column: str | None, fallback_column: str) -> str | None:
    if preferred_column and preferred_column in df.columns:
        return preferred_column
    if fallback_column in df.columns:
        return fallback_column
    return None


def business_group_values(df: pd.DataFrame, business_group_field: str) -> pd.Series:
    group_source = source_column(df, business_group_field, "business_group")
    if group_source:
        values = df[group_source].fillna("Unknown business group").astype(str).str.strip()
        return values.replace("", "Unknown business group")
    return pd.Series("Unknown business group", index=df.index)


def business_pareto_table(
    selected_businesses: pd.DataFrame,
    business_column: str | None,
    jurisdiction_field: str,
    business_group_field: str,
    address_column: str | None,
) -> pd.DataFrame:
    if selected_businesses.empty or "selected_waste_tons" not in selected_businesses.columns:
        return pd.DataFrame()

    table = selected_businesses.copy()
    business_source = source_column(table, business_column, "business_name")
    jurisdiction_source = source_column(table, jurisdiction_field, "jurisdiction")
    address_source = address_column if address_column in table.columns else None
    table["Business"] = (
        table[business_source].fillna("Unnamed business").astype(str).str.strip()
        if business_source
        else "Unnamed business"
    )
    table["Business"] = table["Business"].replace("", "Unnamed business")
    table["Business Group"] = business_group_values(table, business_group_field)
    table["Jurisdiction"] = (
        table[jurisdiction_source].fillna("Unknown jurisdiction").astype(str).str.strip()
        if jurisdiction_source
        else "Unknown jurisdiction"
    )
    table["Address"] = (
        table[address_source].fillna("").astype(str).str.strip()
        if address_source
        else ""
    )
    contact_columns: dict[str, pd.Series] = {}
    add_business_contact_fields(contact_columns, table)
    for label, values in contact_columns.items():
        table[label] = values
    table["Selected Waste Tons"] = pd.to_numeric(
        table["selected_waste_tons"],
        errors="coerce",
    ).fillna(0)

    columns = [
        column
        for column in [
            "Business",
            "Business Group",
            "Jurisdiction",
            "Address",
            "Hauler",
            "Phone",
            "Email",
            "Website",
            "Selected Waste Tons",
        ]
        if column in table.columns
    ]
    return pareto_frame(table[columns], "Business")


def block_group_pareto_label(row: pd.Series) -> str:
    name = str(row.get("NAMELSAD", "")).strip()
    tract = str(row.get("TRACTCE", "")).strip()
    tract_label = f"Tract {tract[:4]}.{tract[4:]}" if len(tract) == 6 else ""
    geoid = str(row.get("GEOID", "")).strip()
    return " | ".join(part for part in [name, tract_label, geoid] if part)


def census_block_group_pareto_table(block_summary: pd.DataFrame) -> pd.DataFrame:
    if block_summary.empty:
        return pd.DataFrame()

    table = block_summary.copy()
    table["Block Group"] = table.apply(block_group_pareto_label, axis=1)
    table["Selected Waste Tons"] = pd.to_numeric(
        table["total_waste_tons"],
        errors="coerce",
    ).fillna(0)
    table["Businesses"] = pd.to_numeric(table["business_count"], errors="coerce").fillna(0).astype(int)
    columns = ["Block Group", "GEOID", "Businesses", "Selected Waste Tons"]
    return pareto_frame(table[columns], "Block Group")


def pareto_chart(pareto: pd.DataFrame, item_column: str, value_column: str = "Selected Waste Tons") -> alt.Chart:
    display = pareto.head(PARETO_CHART_ROWS).copy()
    display["Pareto Item"] = (
        display["Rank"].astype(str)
        + ". "
        + display[item_column].map(lambda value: compact_chart_label(value))
    )

    base = alt.Chart(display).encode(
        x=alt.X(
            "Pareto Item:N",
            sort=None,
            axis=alt.Axis(title=None, labelAngle=-35, labelLimit=130),
        )
    )
    bars = base.mark_bar(opacity=0.8).encode(
        y=alt.Y(
            "Share of Tons:Q",
            title="Share of selected tons",
            scale=alt.Scale(domain=[0, 100]),
        ),
        color=alt.Color(
            "Vital Few:N",
            scale=alt.Scale(domain=[True, False], range=["#2e6f6b", "#b9c9c4"]),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip(f"{item_column}:N", title=item_column),
            alt.Tooltip(f"{value_column}:Q", title="Selected tons", format=",.1f"),
            alt.Tooltip("Share of Tons:Q", title="Share", format=".1f"),
            alt.Tooltip("Cumulative Share:Q", title="Cumulative", format=".1f"),
        ],
    )
    cumulative_line = base.mark_line(color=IWMA_GREEN, point=True, strokeWidth=2).encode(
        y=alt.Y("Cumulative Share:Q", title="Cumulative share", scale=alt.Scale(domain=[0, 100])),
        tooltip=[
            alt.Tooltip(f"{item_column}:N", title=item_column),
            alt.Tooltip("Cumulative Share:Q", title="Cumulative", format=".1f"),
        ],
    )
    threshold = alt.Chart(pd.DataFrame({"Threshold": [VITAL_FEW_THRESHOLD]})).mark_rule(
        color="#5f6762",
        strokeDash=[5, 4],
    ).encode(
        y=alt.Y("Threshold:Q", scale=alt.Scale(domain=[0, 100])),
    )
    return (bars + cumulative_line + threshold).properties(height=330).configure_view(strokeWidth=0)


def render_pareto_panel(
    pareto: pd.DataFrame,
    item_column: str,
    key_prefix: str,
    value_column: str = "Selected Waste Tons",
) -> None:
    if pareto.empty:
        st.warning("No positive tons are available for this Pareto view.")
        return

    total_tons = float(pareto[value_column].sum())
    vital_count = int(pareto["Vital Few"].sum())
    top_share = float(pareto["Share of Tons"].iloc[0])
    left_metric, middle_metric, right_metric = st.columns(3)
    left_metric.metric("Selected tons", f"{total_tons:,.1f}")
    middle_metric.metric("Vital few", f"{vital_count} of {len(pareto):,}")
    right_metric.metric("Top driver share", f"{top_share:,.1f}%")

    st.altair_chart(pareto_chart(pareto, item_column, value_column), width="stretch")
    table_columns = [
        column
        for column in [
            "Rank",
            item_column,
            "GEOID",
            "Business Group",
            "Jurisdiction",
            "Businesses",
            "Address",
            "Hauler",
            "Phone",
            "Email",
            "Website",
            value_column,
            "Share of Tons",
            "Cumulative Share",
            "Vital Few",
        ]
        if column in pareto.columns
    ]
    st.dataframe(
        pareto[table_columns].head(PARETO_TABLE_ROWS),
        width="stretch",
        height=320,
        hide_index=True,
        column_config={
            value_column: st.column_config.NumberColumn(format="%.1f"),
            "Share of Tons": st.column_config.NumberColumn(format="%.1f%%"),
            "Cumulative Share": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    st.download_button(
        "Export Pareto rows",
        data=pareto.to_csv(index=False).encode("utf-8"),
        file_name=f"{key_prefix}_pareto.csv",
        mime="text/csv",
        key=f"{key_prefix}_pareto_export",
    )


def render_vital_few_section(
    source_df: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
    selected_streams: list[str],
    selected_materials: list[str],
    material_mode: str,
    business_column: str | None,
    business_group_field: str,
    jurisdiction_field: str,
    address_column: str | None,
    key_prefix: str,
    block_summary: pd.DataFrame | None = None,
) -> None:
    st.subheader("Vital Few")
    if source_df.empty:
        st.warning("No rows are available for the current Vital Few slice.")
        return

    material_pareto = material_pareto_table(
        source_df,
        material_columns,
        selected_streams,
        selected_materials,
        material_mode,
    )
    business_pareto = business_pareto_table(
        source_df,
        business_column,
        jurisdiction_field,
        business_group_field,
        address_column,
    )
    if block_summary is not None:
        block_pareto = census_block_group_pareto_table(block_summary)
        tabs = st.tabs(["Block Groups", "Businesses", "Materials"])
        with tabs[0]:
            render_pareto_panel(block_pareto, "Block Group", f"{key_prefix}_block_groups")
        with tabs[1]:
            render_pareto_panel(business_pareto, "Business", f"{key_prefix}_businesses")
        with tabs[2]:
            render_pareto_panel(material_pareto, "Material", f"{key_prefix}_materials")
    else:
        tabs = st.tabs(["Materials", "Businesses"])
        with tabs[0]:
            render_pareto_panel(material_pareto, "Material", f"{key_prefix}_materials")
        with tabs[1]:
            render_pareto_panel(business_pareto, "Business", f"{key_prefix}_businesses")


def normalize_landfill_shares(raw_shares: dict[str, float]) -> dict[str, float]:
    positive = {name: max(float(value), 0.0) for name, value in raw_shares.items()}
    total = sum(positive.values())
    if total <= 0:
        equal_share = 1 / len(LANDFILL_FACILITIES)
        return {facility["Landfill"]: equal_share for facility in LANDFILL_FACILITIES}
    return {name: value / total for name, value in positive.items()}


def landfill_assumption_frame(raw_shares: dict[str, float]) -> pd.DataFrame:
    normalized = normalize_landfill_shares(raw_shares)
    frame = pd.DataFrame(LANDFILL_FACILITIES).copy()
    frame["Planning Share"] = frame["Landfill"].map(normalized).fillna(0.0)
    frame["Share Percent"] = frame["Planning Share"] * 100
    frame["color_r"] = frame["color"].map(lambda color: color[0])
    frame["color_g"] = frame["color"].map(lambda color: color[1])
    frame["color_b"] = frame["color"].map(lambda color: color[2])
    frame["color_a"] = frame["color"].map(lambda color: color[3])
    frame["tooltip_title"] = frame["Landfill"]
    frame["tooltip_body"] = (
        frame["Address"]
        + "<br/>Planning share: "
        + frame["Share Percent"].map(lambda value: f"{value:.1f}%")
    )
    return frame


def landfill_distribution_comparison(landfill_summary: pd.DataFrame) -> pd.DataFrame:
    study = pd.DataFrame(LANDFILL_STUDY_BASIS)
    mapped_names = {facility["Landfill"] for facility in LANDFILL_FACILITIES}
    mapped_study_total = study.loc[study["Landfill"].isin(mapped_names), "Study Countywide Share (%)"].sum()
    study["Study Mapped-Only Share (%)"] = np.where(
        study["Landfill"].isin(mapped_names) & (mapped_study_total > 0),
        study["Study Countywide Share (%)"] / mapped_study_total * 100,
        np.nan,
    )

    if landfill_summary.empty:
        dashboard = pd.DataFrame(columns=["Landfill", "Allocated Landfill Tons"])
    else:
        dashboard = landfill_summary[["Landfill", "Allocated Landfill Tons"]].copy()
    dashboard_total = pd.to_numeric(dashboard.get("Allocated Landfill Tons", pd.Series(dtype=float)), errors="coerce").sum()
    dashboard["Dashboard Share (%)"] = np.where(
        dashboard_total > 0,
        pd.to_numeric(dashboard["Allocated Landfill Tons"], errors="coerce").fillna(0) / dashboard_total * 100,
        0.0,
    )

    comparison = study.merge(dashboard, on="Landfill", how="left")
    comparison["Allocated Landfill Tons"] = comparison["Allocated Landfill Tons"].fillna(0.0)
    comparison["Dashboard Share (%)"] = comparison["Dashboard Share (%)"].fillna(0.0)
    comparison["Difference vs Countywide (pp)"] = (
        comparison["Dashboard Share (%)"] - comparison["Study Countywide Share (%)"]
    )
    comparison["Difference vs Mapped-Only (pp)"] = np.where(
        comparison["Study Mapped-Only Share (%)"].notna(),
        comparison["Dashboard Share (%)"] - comparison["Study Mapped-Only Share (%)"],
        np.nan,
    )
    return comparison


def landfill_distribution_chart(comparison: pd.DataFrame) -> alt.Chart:
    chart_data = comparison[comparison["Landfill"] != "Other facilities not mapped"].copy()
    chart_data = chart_data.melt(
        id_vars=["Landfill"],
        value_vars=["Dashboard Share (%)", "Study Countywide Share (%)", "Study Mapped-Only Share (%)"],
        var_name="Share Type",
        value_name="Percent",
    ).dropna(subset=["Percent"])
    chart_data["Share Type"] = chart_data["Share Type"].replace(
        {
            "Dashboard Share (%)": "Dashboard allocation",
            "Study Countywide Share (%)": "Study countywide",
            "Study Mapped-Only Share (%)": "Study mapped-only",
        }
    )
    return (
        alt.Chart(chart_data)
        .mark_bar(opacity=0.86)
        .encode(
            x=alt.X("Landfill:N", title=None, axis=alt.Axis(labelAngle=-24)),
            y=alt.Y("Percent:Q", title="Share of landfill distribution (%)"),
            color=alt.Color(
                "Share Type:N",
                scale=alt.Scale(
                    domain=["Dashboard allocation", "Study countywide", "Study mapped-only"],
                    range=[
                        IWMA_STUDY_MODEL_COLORS["Dashboard allocation"],
                        IWMA_STUDY_MODEL_COLORS["Study countywide"],
                        IWMA_STUDY_MODEL_COLORS["Study mapped-only"],
                    ],
                ),
                title=None,
            ),
            xOffset="Share Type:N",
            tooltip=[
                alt.Tooltip("Landfill:N"),
                alt.Tooltip("Share Type:N"),
                alt.Tooltip("Percent:Q", format=".1f", title="Share (%)"),
            ],
        )
        .properties(height=330)
    )


def haversine_miles(lat1, lon1, lat2: float, lon2: float) -> pd.Series:
    lat1_rad = np.radians(pd.to_numeric(lat1, errors="coerce").astype(float))
    lon1_rad = np.radians(pd.to_numeric(lon1, errors="coerce").astype(float))
    lat2_rad = np.radians(float(lat2))
    lon2_rad = np.radians(float(lon2))
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    return pd.Series(3958.8 * 2 * np.arcsin(np.sqrt(a)), index=getattr(lat1, "index", None))


def import_road_network_packages():
    try:
        import networkx as nx
        import osmnx as ox
    except ImportError as exc:
        raise ImportError(
            "Road-network distances need osmnx and networkx. Install requirements.txt, then rerun the app."
        ) from exc
    return ox, nx


def import_networkx():
    try:
        import networkx as nx
    except ImportError as exc:
        raise ImportError(
            "Road-network distances need networkx. Install requirements.txt, then rerun the app."
        ) from exc
    return nx


def road_network_packages_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("networkx") is not None and importlib.util.find_spec("osmnx") is not None
    except Exception:
        return False


def tiger_road_packages_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("networkx") is not None
    except Exception:
        return False


def road_graph_cache_path() -> Path:
    OSM_DIR.mkdir(parents=True, exist_ok=True)
    return OSM_DIR / "slo_county_drive.graphml"


def tiger_road_graph_key() -> str:
    return f"TIGER_ROADS_{DEFAULT_TIGER_YEAR}_{DEFAULT_STATE_FIPS}{DEFAULT_COUNTY_FIPS}_route_nodes_v2"


def tiger_road_graph_cache_path(roads_zip_path: Path) -> Path:
    return disk_cache_path("tiger_road_graph", path_signature(roads_zip_path), ".pkl")


def iter_line_geometries(geometry):
    if geometry is None or geometry.is_empty:
        return
    if geometry.geom_type == "LineString":
        yield geometry
    elif geometry.geom_type == "MultiLineString":
        for line in geometry.geoms:
            yield line


@st.cache_resource(show_spinner="Loading Census TIGER roads...")
def load_tiger_roads_graph(path_text: str) -> dict[str, object]:
    nx = import_networkx()
    gpd = import_geopandas()
    roads_zip_path = Path(path_text).expanduser().resolve()
    cache_path = tiger_road_graph_cache_path(roads_zip_path)
    if cache_path.exists():
        return pd.read_pickle(cache_path)

    roads = gpd.read_file(str(roads_zip_path))
    if roads.crs is None:
        roads = roads.set_crs("EPSG:4269")
    roads = roads.to_crs("EPSG:3310")

    graph = nx.Graph()
    for geometry in roads.geometry:
        for line in iter_line_geometries(geometry):
            coords = list(line.coords)
            for start, end in zip(coords[:-1], coords[1:]):
                start_node = (round(float(start[0]), 1), round(float(start[1]), 1))
                end_node = (round(float(end[0]), 1), round(float(end[1]), 1))
                if start_node == end_node:
                    continue
                length = float(np.hypot(end_node[0] - start_node[0], end_node[1] - start_node[1]))
                if length <= 0:
                    continue
                graph.add_node(start_node, x=start_node[0], y=start_node[1])
                graph.add_node(end_node, x=end_node[0], y=end_node[1])
                if graph.has_edge(start_node, end_node):
                    graph[start_node][end_node]["length"] = min(graph[start_node][end_node]["length"], length)
                else:
                    graph.add_edge(start_node, end_node, length=length)

    node_rows = [
        {"node": node, "x": data["x"], "y": data["y"]}
        for node, data in graph.nodes(data=True)
    ]
    graph_data = {"graph": graph, "nodes": pd.DataFrame(node_rows)}
    write_pickle_cache(graph_data, cache_path)
    return graph_data


def nearest_tiger_nodes(node_frame: pd.DataFrame, xs: np.ndarray, ys: np.ndarray) -> list[tuple[float, float]]:
    node_x = node_frame["x"].to_numpy(dtype=float)
    node_y = node_frame["y"].to_numpy(dtype=float)
    nodes = node_frame["node"].tolist()
    nearest = []
    for x, y in zip(xs, ys):
        distances = (node_x - float(x)) ** 2 + (node_y - float(y)) ** 2
        nearest.append(nodes[int(np.argmin(distances))])
    return nearest


def normalize_tiger_node(node) -> tuple[float, float] | None:
    if isinstance(node, str):
        try:
            import ast

            node = ast.literal_eval(node)
        except Exception:
            return None
    try:
        if len(node) != 2:
            return None
        return (round(float(node[0]), 1), round(float(node[1]), 1))
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def tiger_route_path_coordinates(
    roads_path_text: str,
    start_node: tuple[float, float],
    end_node: tuple[float, float],
) -> list[list[float]]:
    graph_data = load_tiger_roads_graph(roads_path_text)
    graph = graph_data["graph"]
    nx = import_networkx()
    from pyproj import Transformer

    path_nodes = nx.shortest_path(graph, start_node, end_node, weight="length")
    return tiger_path_nodes_to_coordinates(path_nodes)


def tiger_path_nodes_to_coordinates(path_nodes: list[tuple[float, float]]) -> list[list[float]]:
    if len(path_nodes) < 2:
        return []

    from pyproj import Transformer

    step = max(1, len(path_nodes) // 600)
    sampled_nodes = path_nodes[::step]
    if sampled_nodes[-1] != path_nodes[-1]:
        sampled_nodes.append(path_nodes[-1])
    xs = [node[0] for node in sampled_nodes]
    ys = [node[1] for node in sampled_nodes]
    transformer = Transformer.from_crs("EPSG:3310", "EPSG:4326", always_xy=True)
    lons, lats = transformer.transform(xs, ys)
    return [[float(lon), float(lat)] for lon, lat in zip(lons, lats)]


def tiger_route_geometry_signature(route_source: pd.DataFrame) -> str:
    route_columns = ["flow_key", "business_road_node", "landfill_road_node"]
    available = [column for column in route_columns if column in route_source.columns]
    ordered = route_source[available].copy()
    for column in available:
        ordered[column] = ordered[column].fillna("").astype(str)
    ordered = ordered.sort_values(available).reset_index(drop=True)
    hashed_rows = pd.util.hash_pandas_object(ordered, index=False).values.tobytes()
    return hashlib.sha256(CACHE_VERSION.encode("utf-8") + b"|tiger-route-geometry-v1|" + hashed_rows).hexdigest()[:24]


def build_tiger_route_geometry_lookup(route_source: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"flow_key", "business_road_node", "landfill_road_node"}
    if route_source.empty or not required_columns.issubset(route_source.columns):
        return pd.DataFrame(columns=["flow_key", "path"])

    tiger_source = route_source.copy()
    if "distance_source" in tiger_source.columns:
        tiger_source = tiger_source[tiger_source["distance_source"].astype(str) == ROAD_DISTANCE_TIGER_MODE].copy()
    tiger_source = tiger_source.drop_duplicates("flow_key").copy()
    if tiger_source.empty:
        return pd.DataFrame(columns=["flow_key", "path"])

    cache_path = disk_cache_path("tiger_route_geometry", tiger_route_geometry_signature(tiger_source), ".pkl")
    if cache_path.exists():
        return pd.read_pickle(cache_path)

    roads_zip_path = ensure_census_roads_zip(DEFAULT_TIGER_YEAR, DEFAULT_STATE_FIPS, DEFAULT_COUNTY_FIPS)
    graph_data = load_tiger_roads_graph(str(roads_zip_path))
    graph = graph_data["graph"]
    nx = import_networkx()
    rows = []
    tiger_source["_normalized_business_node"] = tiger_source["business_road_node"].map(normalize_tiger_node)
    tiger_source["_normalized_landfill_node"] = tiger_source["landfill_road_node"].map(normalize_tiger_node)
    tiger_source = tiger_source[
        tiger_source["_normalized_business_node"].notna() & tiger_source["_normalized_landfill_node"].notna()
    ].copy()
    for landfill_node, landfill_rows in tiger_source.groupby("_normalized_landfill_node", dropna=False):
        if landfill_node is None:
            continue
        cutoff = None
        if "road_miles" in landfill_rows.columns:
            max_miles = pd.to_numeric(landfill_rows["road_miles"], errors="coerce").max()
            if pd.notna(max_miles) and max_miles > 0:
                cutoff = float(max_miles) * 1609.344 * 1.02
        try:
            landfill_paths = nx.single_source_dijkstra_path(
                graph,
                landfill_node,
                cutoff=cutoff,
                weight="length",
            )
        except Exception:
            continue
        for _, row in landfill_rows.iterrows():
            path_nodes = landfill_paths.get(row["_normalized_business_node"])
            if not path_nodes or len(path_nodes) < 2:
                continue
            path = tiger_path_nodes_to_coordinates(list(reversed(path_nodes)))
            if len(path) >= 2:
                rows.append({"flow_key": row["flow_key"], "path": path})

    lookup = pd.DataFrame(rows, columns=["flow_key", "path"])
    write_pickle_cache(lookup, cache_path)
    return lookup


def circular_route_html_path(cache_key: str) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORT_DIR / f"circular_flow_tiger_routes_{cache_key}.html"


def default_circular_route_map_path() -> Path:
    return EXPORT_DIR / "circular_flow_tiger_routes_default.html"


def node_click_circular_route_map_path() -> Path:
    return EXPORT_DIR / "circular_flow_tiger_routes_default_node_clicks.html"


def patch_static_circular_route_html(html_text: str) -> str:
    route_marker = '"id": "dominant-tiger-route-paths"'
    route_index = html_text.find(route_marker)
    if route_index >= 0:
        pickable_index = html_text.find('"pickable": true', route_index)
        next_layer_index = html_text.find('"id": "business-points"', route_index)
        if pickable_index >= 0 and (next_layer_index < 0 or pickable_index < next_layer_index):
            html_text = (
                html_text[:pickable_index]
                + '"pickable": false'
                + html_text[pickable_index + len('"pickable": true') :]
            )

    landfill_marker = '"id": "landfill-points"'
    landfill_index = html_text.find(landfill_marker)
    if landfill_index >= 0:
        layer_start = html_text.rfind('    {\n', 0, landfill_index)
        layer_end = html_text.find('    },', landfill_index)
        if layer_start >= 0 and layer_end >= 0:
            layer_text = html_text[layer_start:layer_end]
            layer_text = layer_text.replace(
                '"getFillColor": "@@=[color_r, color_g, color_b, color_a]"',
                '"getFillColor": "@@=[color_r, color_g, color_b, 0]"',
            )
            layer_text = layer_text.replace(
                '"getLineColor": "@@=[255, 255, 255, 230]"',
                '"getLineColor": "@@=[255, 255, 255, 0]"',
            )
            layer_text = layer_text.replace('"getRadius": 1100', '"getRadius": 0')
            layer_text = layer_text.replace('"radiusMaxPixels": 24', '"radiusMaxPixels": 0')
            layer_text = layer_text.replace('"radiusMaxPixels": 22', '"radiusMaxPixels": 0')
            layer_text = layer_text.replace('"radiusMinPixels": 10', '"radiusMinPixels": 0')
            layer_text = layer_text.replace('"radiusMinPixels": 9', '"radiusMinPixels": 0')
            layer_text = layer_text.replace('"pickable": true', '"pickable": false')
            html_text = html_text[:layer_start] + layer_text + html_text[layer_end:]

    html_text = html_text.replace(
        '"getColor": "@@=[255, 255, 255, 245]"',
        '"getColor": "@@=[color_r, color_g, color_b, 255]"',
    )
    html_text = html_text.replace('"getSize": 30', '"getSize": 58')
    html_text = html_text.replace('"getSize": 34', '"getSize": 58')
    for facility in LANDFILL_FACILITIES:
        name = re.escape(facility["Landfill"])
        icon_json = json.dumps(facility["icon"])
        html_text = re.sub(
            rf'("Landfill": "{name}"(?:(?!\n        \}}).)*?"icon": )"[^"]*"',
            lambda match, icon_json=icon_json: match.group(1) + icon_json,
            html_text,
            flags=re.DOTALL,
        )
    return html_text


def ensure_node_click_route_map_html() -> Path | None:
    source_path = default_circular_route_map_path()
    if not source_path.exists():
        return None
    target_path = node_click_circular_route_map_path()
    if target_path.exists() and target_path.stat().st_mtime_ns >= source_path.stat().st_mtime_ns:
        return target_path

    html_text = patch_static_circular_route_html(source_path.read_text(encoding="utf-8"))
    target_path.write_text(html_text, encoding="utf-8")
    return target_path


@st.cache_data(show_spinner=False)
def read_static_html_file(path_text: str, modified_ns: int) -> str:
    return Path(path_text).read_text(encoding="utf-8")


def write_circular_route_map_html(deck: pdk.Deck, cache_key: str) -> Path | None:
    output_path = circular_route_html_path(cache_key)
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path
    try:
        deck.to_html(str(output_path), open_browser=False, notebook_display=False)
        return output_path
    except Exception:
        return None


@st.cache_resource(show_spinner="Loading OpenStreetMap road network...")
def load_slo_drive_graph(local_graph_path: str = ""):
    ox, _nx = import_road_network_packages()
    if local_graph_path:
        user_graph_path = Path(local_graph_path).expanduser().resolve()
        if user_graph_path.exists() and user_graph_path.stat().st_size > 0:
            if hasattr(ox, "load_graphml"):
                return ox.load_graphml(str(user_graph_path))
            return ox.io.load_graphml(str(user_graph_path))
        raise FileNotFoundError(f"The road graph file was not found: {user_graph_path}")

    graph_path = road_graph_cache_path()
    if graph_path.exists() and graph_path.stat().st_size > 0:
        if hasattr(ox, "load_graphml"):
            return ox.load_graphml(str(graph_path))
        return ox.io.load_graphml(str(graph_path))

    OSM_DIR.mkdir(parents=True, exist_ok=True)
    if hasattr(ox, "settings"):
        ox.settings.use_cache = True
        ox.settings.cache_folder = str(OSM_DIR / "http_cache")
        ox.settings.requests_timeout = 300

    north = SLO_MAP_BOUNDS["max_lat"] + 0.08
    south = SLO_MAP_BOUNDS["min_lat"] - 0.08
    east = SLO_MAP_BOUNDS["max_lon"] + 0.08
    west = SLO_MAP_BOUNDS["min_lon"] - 0.08
    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        if hasattr(ox, "settings"):
            ox.settings.overpass_endpoint = endpoint
            ox.settings.overpass_url = endpoint
        try:
            try:
                graph = ox.graph_from_bbox(north, south, east, west, network_type="drive", simplify=True)
            except TypeError:
                graph = ox.graph_from_bbox((north, south, east, west), network_type="drive", simplify=True)
            break
        except Exception as exc:
            last_error = exc
    else:
        raise RuntimeError(
            "OpenStreetMap road network could not be downloaded from the configured Overpass servers. "
            "Try again later, or provide a local GraphML road graph file."
        ) from last_error

    if hasattr(ox, "save_graphml"):
        ox.save_graphml(graph, filepath=str(graph_path))
    else:
        ox.io.save_graphml(graph, filepath=str(graph_path))
    return graph


def road_distance_signature(coords: pd.DataFrame, landfill_frame: pd.DataFrame, local_graph_path: str = "") -> str:
    coord_key = coordinates_signature(coords, "road-distance-businesses-v1")
    landfill_key = hashlib.sha256(
        pd.util.hash_pandas_object(
            landfill_frame[["Landfill", "latitude", "longitude"]].sort_values("Landfill").reset_index(drop=True),
            index=False,
        ).values.tobytes()
    ).hexdigest()[:16]
    graph_key = ""
    if local_graph_path:
        graph_path = Path(local_graph_path).expanduser()
        if graph_path.exists():
            graph_key = path_signature(graph_path)
        else:
            graph_key = str(graph_path)
    return hashlib.sha256(f"{CACHE_VERSION}|{coord_key}|{landfill_key}|{graph_key}".encode("utf-8")).hexdigest()[:24]


def build_osm_road_distance_lookup(
    map_df: pd.DataFrame,
    landfill_frame: pd.DataFrame,
    local_graph_path: str = "",
) -> pd.DataFrame:
    if map_df.empty:
        return pd.DataFrame(columns=["_business_row_id", "Landfill", "road_miles", "distance_source"])

    coords = map_df[["_business_row_id", "latitude", "longitude"]].copy()
    coords["latitude"] = pd.to_numeric(coords["latitude"], errors="coerce")
    coords["longitude"] = pd.to_numeric(coords["longitude"], errors="coerce")
    coords = coords[valid_coordinate_mask(coords)].drop_duplicates("_business_row_id").copy()
    cache_key = road_distance_signature(coords, landfill_frame, local_graph_path)
    cache_path = disk_cache_path("osm_road_distances", cache_key, ".pkl")
    if cache_path.exists():
        return pd.read_pickle(cache_path)

    ox, nx = import_road_network_packages()
    graph = load_slo_drive_graph(local_graph_path)
    try:
        graph_for_distance = ox.convert.to_undirected(graph)
    except Exception:
        graph_for_distance = graph.to_undirected()

    business_nodes = ox.distance.nearest_nodes(
        graph_for_distance,
        X=coords["longitude"].astype(float).to_numpy(),
        Y=coords["latitude"].astype(float).to_numpy(),
    )
    coords = coords.assign(_road_node=business_nodes)

    rows = []
    for _, landfill in landfill_frame.iterrows():
        landfill_node = ox.distance.nearest_nodes(
            graph_for_distance,
            X=float(landfill["longitude"]),
            Y=float(landfill["latitude"]),
        )
        lengths_meters = nx.single_source_dijkstra_path_length(
            graph_for_distance,
            landfill_node,
            weight="length",
        )
        landfill_rows = coords[["_business_row_id", "_road_node"]].copy()
        landfill_rows["Landfill"] = landfill["Landfill"]
        landfill_rows["road_miles"] = landfill_rows["_road_node"].map(lengths_meters) / 1609.344
        landfill_rows["distance_source"] = ROAD_DISTANCE_OSM_MODE
        rows.append(landfill_rows.drop(columns="_road_node"))

    lookup = pd.concat(rows, ignore_index=True)
    lookup = lookup[lookup["road_miles"].notna() & (lookup["road_miles"] > 0)].copy()
    write_pickle_cache(lookup, cache_path)
    return lookup


def build_tiger_road_distance_lookup(map_df: pd.DataFrame, landfill_frame: pd.DataFrame) -> pd.DataFrame:
    if map_df.empty:
        return pd.DataFrame(columns=["_business_row_id", "Landfill", "road_miles", "distance_source"])

    coords = map_df[["_business_row_id", "latitude", "longitude"]].copy()
    coords["latitude"] = pd.to_numeric(coords["latitude"], errors="coerce")
    coords["longitude"] = pd.to_numeric(coords["longitude"], errors="coerce")
    coords = coords[valid_coordinate_mask(coords)].drop_duplicates("_business_row_id").copy()
    cache_key = road_distance_signature(coords, landfill_frame, tiger_road_graph_key())
    cache_path = disk_cache_path("tiger_road_distances", cache_key, ".pkl")
    if cache_path.exists():
        cached_lookup = pd.read_pickle(cache_path)
        if TIGER_ROUTE_CACHE_COLUMNS.issubset(cached_lookup.columns):
            return cached_lookup
        try:
            cache_path.unlink()
        except OSError:
            pass

    roads_zip_path = ensure_census_roads_zip(DEFAULT_TIGER_YEAR, DEFAULT_STATE_FIPS, DEFAULT_COUNTY_FIPS)
    graph_data = load_tiger_roads_graph(str(roads_zip_path))
    graph = graph_data["graph"]
    node_frame = graph_data["nodes"]
    if node_frame.empty:
        raise ValueError("The Census TIGER roads graph did not contain any road nodes.")

    nx = import_networkx()
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True)
    business_x, business_y = transformer.transform(
        coords["longitude"].astype(float).to_numpy(),
        coords["latitude"].astype(float).to_numpy(),
    )
    coords = coords.assign(_road_node=nearest_tiger_nodes(node_frame, business_x, business_y))

    rows = []
    for _, landfill in landfill_frame.iterrows():
        landfill_x, landfill_y = transformer.transform(float(landfill["longitude"]), float(landfill["latitude"]))
        landfill_node = nearest_tiger_nodes(
            node_frame,
            np.array([landfill_x], dtype=float),
            np.array([landfill_y], dtype=float),
        )[0]
        lengths_meters = nx.single_source_dijkstra_path_length(graph, landfill_node, weight="length")
        landfill_rows = coords[["_business_row_id", "_road_node"]].copy()
        landfill_rows["Landfill"] = landfill["Landfill"]
        landfill_rows["road_miles"] = landfill_rows["_road_node"].map(lengths_meters) / 1609.344
        landfill_rows["distance_source"] = ROAD_DISTANCE_TIGER_MODE
        landfill_rows["business_road_node"] = landfill_rows["_road_node"]
        landfill_rows["landfill_road_node"] = [landfill_node] * len(landfill_rows)
        rows.append(landfill_rows.drop(columns="_road_node"))

    lookup = pd.concat(rows, ignore_index=True)
    lookup = lookup[lookup["road_miles"].notna() & (lookup["road_miles"] > 0)].copy()
    write_pickle_cache(lookup, cache_path)
    return lookup


def osm_road_distance_cache_exists(
    map_df: pd.DataFrame,
    landfill_frame: pd.DataFrame,
    local_graph_path: str = "",
) -> bool:
    if map_df.empty:
        return False
    coords = map_df[["_business_row_id", "latitude", "longitude"]].copy()
    coords["latitude"] = pd.to_numeric(coords["latitude"], errors="coerce")
    coords["longitude"] = pd.to_numeric(coords["longitude"], errors="coerce")
    coords = coords[valid_coordinate_mask(coords)].drop_duplicates("_business_row_id").copy()
    if coords.empty:
        return False
    cache_key = road_distance_signature(coords, landfill_frame, local_graph_path)
    return disk_cache_path("osm_road_distances", cache_key, ".pkl").exists()


def tiger_road_distance_cache_exists(map_df: pd.DataFrame, landfill_frame: pd.DataFrame) -> bool:
    if map_df.empty:
        return False
    coords = map_df[["_business_row_id", "latitude", "longitude"]].copy()
    coords["latitude"] = pd.to_numeric(coords["latitude"], errors="coerce")
    coords["longitude"] = pd.to_numeric(coords["longitude"], errors="coerce")
    coords = coords[valid_coordinate_mask(coords)].drop_duplicates("_business_row_id").copy()
    if coords.empty:
        return False
    cache_key = road_distance_signature(coords, landfill_frame, tiger_road_graph_key())
    cache_path = disk_cache_path("tiger_road_distances", cache_key, ".pkl")
    if not cache_path.exists():
        return False
    try:
        cached_lookup = pd.read_pickle(cache_path)
    except Exception:
        return False
    return TIGER_ROUTE_CACHE_COLUMNS.issubset(cached_lookup.columns)


def road_distance_source_frame(data: pd.DataFrame, latitude_column: str, longitude_column: str) -> pd.DataFrame:
    if "_business_row_id" not in data.columns:
        return pd.DataFrame(columns=["_business_row_id", "latitude", "longitude"])
    source = data[["_business_row_id", latitude_column, longitude_column]].rename(
        columns={latitude_column: "latitude", longitude_column: "longitude"}
    )
    source["latitude"] = pd.to_numeric(source["latitude"], errors="coerce")
    source["longitude"] = pd.to_numeric(source["longitude"], errors="coerce")
    source = source[valid_coordinate_mask(source)].drop_duplicates("_business_row_id").copy()
    return source


def estimate_haul_flows(
    map_df: pd.DataFrame,
    landfill_frame: pd.DataFrame,
    allocation_mode: str,
    road_multiplier: float,
    operations_multiplier: float,
    kg_co2e_per_ton_mile: float,
    trips_per_year: int,
    average_truckload_tons: float,
    diversion_trips_per_business: int,
    kg_co2e_per_vehicle_mile: float,
    road_distance_lookup: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if map_df.empty:
        empty_flows = pd.DataFrame(
            columns=[
                "_business_row_id",
                "business_name",
                "Landfill",
                "flow_tons",
                "route_miles",
                "ton_miles",
                "truckload_equivalent_trips",
                "vehicle_miles",
                "co2e_metric_tons",
                "load_co2e_metric_tons",
            ]
        )
        return empty_flows, map_df.copy(), pd.DataFrame()

    business = map_df.copy()
    business["selected_waste_tons"] = pd.to_numeric(business["selected_waste_tons"], errors="coerce").fillna(0)
    business = business[business["selected_waste_tons"] > 0].copy()
    if business.empty:
        return pd.DataFrame(), business, pd.DataFrame()

    flow_frames = []
    for _, landfill in landfill_frame.iterrows():
        straight_miles = haversine_miles(
            business["latitude"],
            business["longitude"],
            float(landfill["latitude"]),
            float(landfill["longitude"]),
        )
        business_flow_columns = [
            "_business_row_id",
            "business_name",
            "jurisdiction",
            "business_group",
            "latitude",
            "longitude",
            "selected_waste_tons",
        ]
        if "Hauler" in business.columns:
            business_flow_columns.append("Hauler")
        frame = business[business_flow_columns].copy()
        frame["Landfill"] = landfill["Landfill"]
        frame["landfill_latitude"] = float(landfill["latitude"])
        frame["landfill_longitude"] = float(landfill["longitude"])
        frame["Planning Share"] = float(landfill["Planning Share"])
        frame["straight_miles"] = straight_miles
        frame["estimated_route_miles"] = straight_miles * float(road_multiplier)
        frame["color_r"] = int(landfill["color_r"])
        frame["color_g"] = int(landfill["color_g"])
        frame["color_b"] = int(landfill["color_b"])
        frame["color_a"] = 155
        flow_frames.append(frame)

    flows = pd.concat(flow_frames, ignore_index=True)
    if road_distance_lookup is not None and not road_distance_lookup.empty:
        flows = flows.merge(road_distance_lookup, on=["_business_row_id", "Landfill"], how="left")
        flows["route_miles"] = pd.to_numeric(flows["road_miles"], errors="coerce").fillna(
            flows["estimated_route_miles"]
        )
        flows["distance_source"] = flows["distance_source"].fillna("Straight-line fallback")
        flows = flows.drop(columns=[column for column in ["road_miles"] if column in flows.columns])
    else:
        flows["route_miles"] = flows["estimated_route_miles"]
        flows["distance_source"] = ROAD_DISTANCE_ESTIMATE_MODE

    if "Hauler" in flows.columns:
        flows["Hauler Facility Rule"] = flows["Hauler"].map(hauler_facility_rule).fillna("")
    else:
        flows["Hauler Facility Rule"] = ""

    inverse_distance = 1 / np.power(flows["route_miles"].clip(lower=0.5), 1.25)
    flows["distance_wasteshed_raw_weight"] = flows["Planning Share"] * inverse_distance
    distance_wasteshed_denominator = flows.groupby("_business_row_id")["distance_wasteshed_raw_weight"].transform("sum")
    flows["distance_wasteshed_weight"] = np.where(
        distance_wasteshed_denominator > 0,
        flows["distance_wasteshed_raw_weight"] / distance_wasteshed_denominator,
        0.0,
    )

    if allocation_mode == HAULER_FACILITY_ALLOCATION_MODE:
        rule_matched = flows["Hauler Facility Rule"].astype(str).str.len() > 0
        flows["allocation_weight"] = np.where(
            rule_matched,
            np.where(flows["Landfill"].astype(str) == flows["Hauler Facility Rule"].astype(str), 1.0, 0.0),
            flows["distance_wasteshed_weight"],
        )
        flows["allocation_source"] = np.where(
            rule_matched,
            "Hauler facility rule",
            "Fallback: distance + wasteshed share",
        )
    elif allocation_mode == "Nearest landfill":
        min_distance = flows.groupby("_business_row_id")["route_miles"].transform("min")
        flows["allocation_weight"] = np.where(flows["route_miles"] == min_distance, 1.0, 0.0)
        flows["allocation_source"] = "Nearest landfill"
    elif allocation_mode == "Wasteshed share only":
        flows["allocation_weight"] = flows["Planning Share"]
        flows["allocation_source"] = "Wasteshed share only"
    else:
        flows["allocation_weight"] = flows["distance_wasteshed_weight"]
        flows["allocation_source"] = "Distance + wasteshed share"

    flows["flow_tons"] = flows["selected_waste_tons"] * flows["allocation_weight"]
    flows = flows[flows["flow_tons"] > 0].copy()
    flows["flow_key"] = flows["_business_row_id"].astype(str) + "|" + flows["Landfill"].astype(str)
    flows["ton_miles"] = flows["flow_tons"] * flows["route_miles"] * float(operations_multiplier)
    flows["service_weeks_per_year"] = int(trips_per_year)
    flows["truckload_equivalent_trips"] = flows["flow_tons"] / max(float(average_truckload_tons), 0.1)
    flows["annual_service_trips"] = flows["truckload_equivalent_trips"]
    flows["vehicle_miles"] = flows["route_miles"] * flows["truckload_equivalent_trips"] * float(operations_multiplier)
    flows["load_co2e_metric_tons"] = flows["ton_miles"] * float(kg_co2e_per_ton_mile) / 1000
    flows["co2e_metric_tons"] = flows["vehicle_miles"] * float(kg_co2e_per_vehicle_mile) / 1000
    flows["line_width"] = np.clip(np.sqrt(flows["flow_tons"]) * 0.35 + 1, 1, 8)
    flows["tooltip_title"] = flows["business_name"] + " to " + flows["Landfill"]
    flows["tooltip_body"] = (
        flows["flow_tons"].map(lambda value: f"{value:,.1f}")
        + " tons<br/>Route miles: "
        + flows["route_miles"].map(lambda value: f"{value:,.1f}")
        + "<br/>Truckload-equivalent trips: "
        + flows["truckload_equivalent_trips"].map(lambda value: f"{value:,.2f}")
        + "<br/>Vehicle miles: "
        + flows["vehicle_miles"].map(lambda value: f"{value:,.0f}")
        + "<br/>Distance source: "
        + flows["distance_source"].fillna("")
        + "<br/>Assignment: "
        + flows["allocation_source"].fillna("")
        + "<br/>CO2e: "
        + flows["co2e_metric_tons"].map(lambda value: f"{value:,.2f}")
        + " metric tons"
    )

    dominant = flows.sort_values(["_business_row_id", "flow_tons"], ascending=[True, False]).drop_duplicates(
        "_business_row_id"
    )
    dominant_business_fields = dominant[
        [
            "_business_row_id",
            "Landfill",
            "route_miles",
            "color_r",
            "color_g",
            "color_b",
            "color_a",
            "allocation_source",
            "Hauler Facility Rule",
        ]
    ].rename(
        columns={
            "route_miles": "dominant_route_miles",
            "allocation_source": "dominant_allocation_source",
            "Hauler Facility Rule": "dominant_hauler_facility_rule",
        }
    )
    business_rollup = business.merge(
        dominant_business_fields,
        on="_business_row_id",
        how="left",
    )
    business_totals = (
        flows.groupby("_business_row_id")
        .agg(
            route_miles=("route_miles", "mean"),
            ton_miles=("ton_miles", "sum"),
            truckload_equivalent_trips=("truckload_equivalent_trips", "sum"),
            vehicle_miles=("vehicle_miles", "sum"),
            co2e_metric_tons=("co2e_metric_tons", "sum"),
            load_co2e_metric_tons=("load_co2e_metric_tons", "sum"),
            distance_source=("distance_source", most_common_text),
            allocation_source=("allocation_source", most_common_text),
        )
        .reset_index()
    )
    business_rollup = business_rollup.merge(business_totals, on="_business_row_id", how="left")
    business_rollup["dominant_route_miles"] = business_rollup["dominant_route_miles"].fillna(
        business_rollup["route_miles"].fillna(0)
    )
    business_rollup["point_radius"] = np.clip(np.sqrt(business_rollup["selected_waste_tons"]) * 4 + 25, 25, 240)
    business_rollup["tooltip_title"] = business_rollup["business_name"]
    business_rollup["tooltip_body"] = (
        "Landfill tons: "
        + business_rollup["selected_waste_tons"].map(lambda value: f"{value:,.1f}")
        + "<br/>Dominant facility: "
        + business_rollup["Landfill"].fillna("")
        + "<br/>Hauler: "
        + (
            business_rollup["Hauler"].fillna("").astype(str)
            if "Hauler" in business_rollup.columns
            else pd.Series("", index=business_rollup.index)
        )
        + "<br/>One-way miles to assumed landfill: "
        + business_rollup["dominant_route_miles"].fillna(0).map(lambda value: f"{value:,.1f}")
        + "<br/>Assignment: "
        + business_rollup["allocation_source"].fillna("")
        + "<br/>Truckload-equivalent trips: "
        + business_rollup["truckload_equivalent_trips"].fillna(0).map(lambda value: f"{value:,.2f}")
        + "<br/>Annual vehicle miles: "
        + business_rollup["vehicle_miles"].fillna(0).map(lambda value: f"{value:,.0f}")
        + "<br/>Estimated CO2e: "
        + business_rollup["co2e_metric_tons"].fillna(0).map(lambda value: f"{value:,.2f}")
        + " metric tons<br/>Distance source: "
        + business_rollup["distance_source"].fillna("")
        + "<br/>"
        + business_rollup["jurisdiction"].fillna("")
    )

    flows["weighted_route_miles"] = flows["route_miles"] * flows["flow_tons"]
    landfill_summary = (
        flows.groupby("Landfill", dropna=False)
        .agg(
            Estimated_Tons=("flow_tons", "sum"),
            Weighted_Route_Miles=("weighted_route_miles", "sum"),
            Ton_Miles=("ton_miles", "sum"),
            Truckload_Equivalent_Trips=("truckload_equivalent_trips", "sum"),
            Vehicle_Miles=("vehicle_miles", "sum"),
            CO2e_Metric_Tons=("co2e_metric_tons", "sum"),
            Load_CO2e_Metric_Tons=("load_co2e_metric_tons", "sum"),
            Businesses=("_business_row_id", "nunique"),
        )
        .reset_index()
        .sort_values("Estimated_Tons", ascending=False)
    )
    landfill_summary["Avg_One_Way_Miles"] = np.where(
        landfill_summary["Estimated_Tons"] > 0,
        landfill_summary["Weighted_Route_Miles"] / landfill_summary["Estimated_Tons"],
        0.0,
    )
    landfill_summary = landfill_summary.drop(columns="Weighted_Route_Miles")
    landfill_summary = landfill_summary.rename(
        columns={
            "Estimated_Tons": "Allocated Landfill Tons",
            "Avg_One_Way_Miles": "Avg One-Way Miles",
            "Ton_Miles": "Annual Ton-Miles",
            "Truckload_Equivalent_Trips": "Truckload-Equivalent Trips",
            "Vehicle_Miles": "Annual Vehicle Miles",
            "CO2e_Metric_Tons": "Truck CO2e (metric tons)",
            "Load_CO2e_Metric_Tons": "Load-based CO2e (metric tons)",
        }
    )
    return flows, business_rollup, landfill_summary


def build_tiger_route_path_flows(display_flows: pd.DataFrame, max_paths: int | None = None) -> pd.DataFrame:
    required_columns = {"business_road_node", "landfill_road_node", "flow_key"}
    if display_flows.empty or not required_columns.issubset(display_flows.columns):
        return pd.DataFrame()

    tiger_flows = display_flows[
        display_flows["distance_source"].astype(str) == ROAD_DISTANCE_TIGER_MODE
    ].copy()
    if max_paths is not None:
        tiger_flows = tiger_flows.head(max_paths).copy()
    if tiger_flows.empty:
        return pd.DataFrame()

    geometry_lookup = build_tiger_route_geometry_lookup(tiger_flows)
    if geometry_lookup.empty:
        return pd.DataFrame()
    return tiger_flows.merge(geometry_lookup, on="flow_key", how="inner")


def build_circular_flow_map(
    business_rollup: pd.DataFrame,
    display_flows: pd.DataFrame,
    landfill_frame: pd.DataFrame,
    route_flows: pd.DataFrame | None = None,
) -> pdk.Deck:
    map_points = pd.concat(
        [
            business_rollup[["latitude", "longitude"]],
            landfill_frame[["latitude", "longitude"]],
        ],
        ignore_index=True,
    )
    center_lat = float((map_points["latitude"].min() + map_points["latitude"].max()) / 2)
    center_lon = float((map_points["longitude"].min() + map_points["longitude"].max()) / 2)
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_from_bounds(map_points),
        pitch=0,
        bearing=0,
    )

    layers = []
    route_keys: set[str] = set()
    route_layer = None
    if route_flows is not None and not route_flows.empty:
        route_flows = route_flows.copy()
        route_keys = set(route_flows["flow_key"].astype(str))
        route_flows["route_line_width"] = np.clip(
            pd.to_numeric(route_flows["line_width"], errors="coerce").fillna(1.0) * 2.25,
            4.0,
            16.0,
        )
        route_flows["route_color_a"] = 244
        route_layer = pdk.Layer(
            "PathLayer",
            id="haul-route-paths",
            data=route_flows,
            get_path="path",
            get_color="[color_r, color_g, color_b, route_color_a]",
            get_width="route_line_width",
            width_min_pixels=4,
            width_max_pixels=16,
            pickable=False,
        )

    line_flows = (
        display_flows[~display_flows["flow_key"].astype(str).isin(route_keys)].copy()
        if route_keys and "flow_key" in display_flows.columns
        else display_flows
    )
    if not line_flows.empty:
        line_flows = line_flows.copy()
        line_flows["connector_line_width"] = np.clip(
            pd.to_numeric(line_flows["line_width"], errors="coerce").fillna(1.0) * 0.35,
            0.35,
            2.0,
        )
        line_flows["connector_color_a"] = 12
        layers.append(
            pdk.Layer(
                "LineLayer",
                id="haul-flow-lines",
                data=line_flows,
                get_source_position="[longitude, latitude]",
                get_target_position="[landfill_longitude, landfill_latitude]",
                get_color="[color_r, color_g, color_b, connector_color_a]",
                get_width="connector_line_width",
                width_min_pixels=0.25,
                width_max_pixels=2,
                pickable=False,
            )
        )
    if route_layer is not None:
        layers.append(route_layer)

    business_layer = pdk.Layer(
        "ScatterplotLayer",
        id="circular-business-points",
        data=business_rollup,
        get_position="[longitude, latitude]",
        get_radius="point_radius",
        radius_min_pixels=3,
        radius_max_pixels=14,
        get_fill_color="[color_r, color_g, color_b, 118]",
        get_line_color="[255, 255, 255, 150]",
        line_width_min_pixels=0.5,
        pickable=True,
        auto_highlight=True,
    )
    landfill_halo_layer = pdk.Layer(
        "TextLayer",
        id="landfill-icon-haloes",
        data=landfill_frame,
        get_position="[longitude, latitude]",
        get_text="icon",
        get_size=72,
        get_color="[255, 255, 255, 245]",
        get_alignment_baseline="'center'",
        get_text_anchor="'middle'",
        pickable=False,
    )
    landfill_icon_layer = pdk.Layer(
        "TextLayer",
        id="landfill-icons",
        data=landfill_frame,
        get_position="[longitude, latitude]",
        get_text="icon",
        get_size=58,
        get_color="[color_r, color_g, color_b, 255]",
        get_alignment_baseline="'center'",
        get_text_anchor="'middle'",
        pickable=True,
        auto_highlight=True,
    )
    layers.extend([business_layer, landfill_halo_layer, landfill_icon_layer])
    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=layers,
        tooltip={
            "html": "<b>{tooltip_title}</b><br/>{tooltip_body}",
            "style": {
                "backgroundColor": "rgba(34, 42, 38, 0.94)",
                "color": "white",
                "fontFamily": "Arial",
                "fontSize": "12px",
            },
        },
    )


def render_circular_flow_legend(landfill_frame: pd.DataFrame, routed_count: int = 0) -> None:
    items = [
        (
            f"{row.get('icon', '■')} {row['Landfill']}",
            [int(row["color_r"]), int(row["color_g"]), int(row["color_b"]), 220],
            "line",
        )
        for _, row in landfill_frame.iterrows()
    ]
    items.append(("Business point", [35, 105, 154, 116], "dot"))
    render_map_legend(
        "Flow legend",
        items,
        note=(
            f"{routed_count:,} displayed flows follow TIGER road paths; faint connectors only appear when route geometry is missing."
            if routed_count > 0
            else "Business colors show dominant modeled landfill. Road lines appear only in TIGER path modes."
        ),
    )


def build_business_material_exchange_rows(
    filtered: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
    selected_materials: list[str],
    area_series: pd.Series,
    business_column: str | None,
    business_group_field: str,
    jurisdiction_field: str,
    min_material_tons: float,
) -> pd.DataFrame:
    if filtered.empty:
        return pd.DataFrame()

    business_source = source_column(filtered, business_column, "business_name")
    group_source = source_column(filtered, business_group_field, "business_group")
    jurisdiction_source = source_column(filtered, jurisdiction_field, "jurisdiction")
    naics_source = first_existing_column(filtered, ["Primary NAICS Description", "Primary SIC Description", "Line of Business"])
    material_keys = selected_materials or sorted(material_columns)
    rows = []
    for material in material_keys:
        disposed_column = material_columns.get(material, {}).get("disposed")
        if not disposed_column or disposed_column not in filtered.columns:
            continue
        tons = pd.to_numeric(filtered[disposed_column], errors="coerce").fillna(0)
        material_rows = pd.DataFrame(
            {
                "_business_row_id": filtered["_business_row_id"],
                "Business": (
                    filtered[business_source].fillna("Unnamed business").astype(str).str.strip()
                    if business_source
                    else "Unnamed business"
                ),
                "Business Group": (
                    filtered[group_source].fillna("Unknown business group").astype(str).str.strip()
                    if group_source
                    else "Unknown business group"
                ),
                "Jurisdiction": (
                    filtered[jurisdiction_source].fillna("Unknown jurisdiction").astype(str).str.strip()
                    if jurisdiction_source
                    else "Unknown jurisdiction"
                ),
                "Industry Description": (
                    filtered[naics_source].fillna("").astype(str).str.strip()
                    if naics_source
                    else ""
                ),
                "Exchange Area": area_series.reindex(filtered.index).fillna("Unknown").astype(str),
                "Material": format_material_name(material),
                "Material Group": material_group(material),
                "Disposed Tons": tons,
            },
            index=filtered.index,
        )
        material_rows = material_rows[material_rows["Disposed Tons"] >= float(min_material_tons)].copy()
        if not material_rows.empty:
            rows.append(material_rows)

    if not rows:
        return pd.DataFrame(
            columns=[
                "_business_row_id",
                "Business",
                "Business Group",
                "Jurisdiction",
                "Industry Description",
                "Exchange Area",
                "Material",
                "Material Group",
                "Disposed Tons",
            ]
        )
    return pd.concat(rows, ignore_index=True)


def build_exchange_opportunity_table(material_rows: pd.DataFrame) -> pd.DataFrame:
    if material_rows.empty:
        return pd.DataFrame(
            columns=[
                "Exchange Area",
                "Material",
                "Material Group",
                "Potential Exchange Tons",
                "Businesses",
                "Business Groups",
                "Top Business Group",
                "Example Businesses",
                "Opportunity Score",
                "Transparency Note",
            ]
        )

    grouped = (
        material_rows.groupby(["Exchange Area", "Material", "Material Group"], dropna=False)
        .agg(
            **{
                "Potential Exchange Tons": ("Disposed Tons", "sum"),
                "Businesses": ("_business_row_id", "nunique"),
                "Business Groups": ("Business Group", "nunique"),
                "Top Business Group": ("Business Group", most_common_text),
            }
        )
        .reset_index()
    )
    examples = (
        material_rows.sort_values("Disposed Tons", ascending=False)
        .groupby(["Exchange Area", "Material"], dropna=False)["Business"]
        .agg(lambda values: ", ".join(pd.Series(values).dropna().astype(str).head(3)))
        .reset_index(name="Example Businesses")
    )
    grouped = grouped.merge(examples, on=["Exchange Area", "Material"], how="left")
    grouped["Opportunity Score"] = (
        grouped["Potential Exchange Tons"]
        * np.log1p(grouped["Businesses"])
        * np.log1p(grouped["Business Groups"])
    )
    grouped["Transparency Note"] = (
        "Assumes businesses disposing this material may also be candidates for reuse/input matching; demand is not observed."
    )
    return grouped.sort_values("Opportunity Score", ascending=False)


def circular_exchange_area_series(
    filtered: pd.DataFrame,
    exchange_geography: str,
    block_group_lookup: pd.DataFrame | None,
    zip_column: str | None,
    jurisdiction_field: str,
) -> pd.Series:
    if exchange_geography == "ZIP code":
        if zip_column and zip_column in filtered.columns:
            return filtered[zip_column].map(clean_zipcode_value).replace("", "Unknown ZIP")
        return pd.Series("Unknown ZIP", index=filtered.index)
    if exchange_geography == "Census block group" and block_group_lookup is not None and not block_group_lookup.empty:
        labels = block_group_lookup.copy()
        labels["Exchange Area"] = (
            labels["NAMELSAD"].fillna("Block group").astype(str)
            + " | GEOID "
            + labels["GEOID"].fillna("").astype(str)
        )
        return filtered["_business_row_id"].map(labels.set_index("_business_row_id")["Exchange Area"]).fillna(
            "Unmatched block group"
        )
    if jurisdiction_field in filtered.columns:
        return filtered[jurisdiction_field].fillna("Unknown jurisdiction").astype(str)
    return pd.Series("Unknown geography", index=filtered.index)


def exchange_area_geoid(area_label: str) -> str | None:
    match = re.search(r"GEOID\s+(\d+)", str(area_label))
    return match.group(1) if match else None


def build_exchange_area_focus_map(
    block_groups,
    selected_exchange_areas: list[str],
    material_rows: pd.DataFrame,
    filtered: pd.DataFrame,
    latitude_column: str,
    longitude_column: str,
) -> pdk.Deck | None:
    area_by_geoid = {
        geoid: area
        for area in selected_exchange_areas
        if (geoid := exchange_area_geoid(area))
    }
    if block_groups is None or block_groups.empty or not area_by_geoid:
        return None

    selected_blocks = block_groups[block_groups["GEOID"].astype(str).isin(area_by_geoid)].copy()
    if selected_blocks.empty:
        return None

    area_summary = (
        material_rows.groupby("Exchange Area", dropna=False)
        .agg(
            exchange_tons=("Disposed Tons", "sum"),
            exchange_businesses=("_business_row_id", "nunique"),
            top_material=("Material", most_common_text),
        )
        .reset_index()
    )
    area_lookup = area_summary.set_index("Exchange Area").to_dict("index")
    selected_blocks["Exchange Area"] = selected_blocks["GEOID"].astype(str).map(area_by_geoid).fillna("")
    selected_blocks["exchange_tons"] = selected_blocks["Exchange Area"].map(
        lambda area: area_lookup.get(area, {}).get("exchange_tons", 0.0)
    )
    selected_blocks["exchange_businesses"] = selected_blocks["Exchange Area"].map(
        lambda area: area_lookup.get(area, {}).get("exchange_businesses", 0)
    )
    selected_blocks["top_material"] = selected_blocks["Exchange Area"].map(
        lambda area: area_lookup.get(area, {}).get("top_material", "")
    )
    selected_blocks["tooltip_title"] = selected_blocks["Exchange Area"]
    selected_blocks["tooltip_body"] = (
        "Potential exchange tons: "
        + selected_blocks["exchange_tons"].map(lambda value: f"{float(value):,.1f}")
        + "<br/>Businesses: "
        + selected_blocks["exchange_businesses"].map(lambda value: f"{int(value):,}")
        + "<br/>Top material: "
        + selected_blocks["top_material"].fillna("").astype(str)
    )
    selected_blocks["fill_r"] = 79
    selected_blocks["fill_g"] = 127
    selected_blocks["fill_b"] = 63
    selected_blocks["fill_a"] = 72
    selected_blocks["line_r"] = 255
    selected_blocks["line_g"] = 188
    selected_blocks["line_b"] = 45
    selected_blocks["line_a"] = 245
    selected_blocks["line_width"] = 5
    selected_blocks["geometry"] = selected_blocks.geometry.simplify(0.00025, preserve_topology=True)

    selected_ids = material_rows.loc[
        material_rows["Exchange Area"].isin(selected_exchange_areas),
        "_business_row_id",
    ].dropna()
    selected_points = filtered[filtered["_business_row_id"].isin(selected_ids)].copy()
    selected_points["latitude"] = pd.to_numeric(selected_points[latitude_column], errors="coerce")
    selected_points["longitude"] = pd.to_numeric(selected_points[longitude_column], errors="coerce")
    selected_points = selected_points[valid_coordinate_mask(selected_points)].copy()
    if not selected_points.empty:
        selected_points["point_radius"] = 70
        point_name_column = source_column(selected_points, business_display_column(selected_points), "Business")
        selected_points["tooltip_title"] = (
            selected_points[point_name_column].fillna("Business").astype(str)
            if point_name_column
            else "Business"
        )
        selected_points["tooltip_body"] = "Selected material-exchange signal"

    bounds = selected_blocks.total_bounds
    view_state = pdk.ViewState(
        latitude=float((bounds[1] + bounds[3]) / 2),
        longitude=float((bounds[0] + bounds[2]) / 2),
        zoom=float(np.clip(zoom_from_total_bounds(bounds) - 0.25, 7, 12)),
        pitch=0,
        bearing=0,
    )

    geojson_columns = [
        "GEOID",
        "NAMELSAD",
        "Exchange Area",
        "exchange_tons",
        "exchange_businesses",
        "top_material",
        "tooltip_title",
        "tooltip_body",
        "fill_r",
        "fill_g",
        "fill_b",
        "fill_a",
        "line_r",
        "line_g",
        "line_b",
        "line_a",
        "line_width",
        "geometry",
    ]
    layers = [
        pdk.Layer(
            "GeoJsonLayer",
            id="selected-exchange-block-groups",
            data=json.loads(selected_blocks[geojson_columns].to_json()),
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
            get_fill_color="[properties.fill_r, properties.fill_g, properties.fill_b, properties.fill_a]",
            get_line_color="[properties.line_r, properties.line_g, properties.line_b, properties.line_a]",
            get_line_width="properties.line_width",
            line_width_min_pixels=2,
            line_width_max_pixels=7,
        )
    ]
    if not selected_points.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                id="selected-exchange-businesses",
                data=selected_points,
                get_position="[longitude, latitude]",
                get_radius="point_radius",
                radius_min_pixels=3,
                radius_max_pixels=9,
                get_fill_color="[31, 95, 139, 140]",
                get_line_color="[255, 255, 255, 190]",
                line_width_min_pixels=0.7,
                pickable=True,
                auto_highlight=True,
            )
        )

    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=layers,
        tooltip={
            "html": "<b>{tooltip_title}</b><br/>{tooltip_body}",
            "style": {
                "backgroundColor": "rgba(34, 42, 38, 0.94)",
                "color": "white",
                "fontFamily": "Arial",
                "fontSize": "12px",
            },
        },
    )


def count_existing_columns(df: pd.DataFrame, predicate) -> int:
    return sum(1 for column in df.columns if predicate(str(column)))


def infrastructure_summary_metrics(
    data: pd.DataFrame,
    filtered: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
) -> dict[str, int]:
    calrecycle_material_columns = count_existing_columns(data, lambda column: column.startswith("calrecycle_mat_"))
    calrecycle_columns = count_existing_columns(data, lambda column: column.startswith("calrecycle_"))
    smart_columns = count_existing_columns(data, lambda column: column.startswith("SMART1383") or column == "source_excel_row")
    mapping_columns = count_existing_columns(
        data,
        lambda column: column.startswith("business_group_mapping_")
        or column in {"Business Group", "Matched Attributes", "Matched Values"},
    )
    mergent_columns = max(len(data.columns) - calrecycle_columns - smart_columns - mapping_columns, 0)
    duns_count = int(data["D-U-N-S@ Number"].notna().sum()) if "D-U-N-S@ Number" in data.columns else 0
    company_count = int(data["Company Name"].notna().sum()) if "Company Name" in data.columns else duns_count
    scaled_count = (
        int(data["calrecycle_status"].astype(str).str.casefold().eq("scaled").sum())
        if "calrecycle_status" in data.columns
        else 0
    )
    suppressed_count = 0
    if "calrecycle_profile_strategy" in data.columns:
        suppressed_count = int(data["calrecycle_profile_strategy"].astype(str).str.contains("countywide", case=False).sum())
    elif "calrecycle_profile_reason" in data.columns:
        suppressed_count = int(data["calrecycle_profile_reason"].astype(str).str.contains("suppressed", case=False).sum())
    employee_count = (
        int(pd.to_numeric(data["calrecycle_employee_count"], errors="coerce").notna().sum())
        if "calrecycle_employee_count" in data.columns
        else 0
    )
    return {
        "source_estimate": SMART1383_SOURCE_COMPANY_ESTIMATE,
        "integrated_rows": len(data),
        "active_rows": len(filtered),
        "workbook_columns": len(data.columns),
        "smart_columns": smart_columns,
        "mergent_columns": mergent_columns,
        "mapping_columns": mapping_columns,
        "calrecycle_columns": calrecycle_columns,
        "calrecycle_material_columns": calrecycle_material_columns,
        "material_categories": len(material_columns),
        "duns_count": duns_count,
        "company_count": company_count,
        "scaled_count": scaled_count,
        "suppressed_count": suppressed_count,
        "employee_count": employee_count,
    }


def infrastructure_source_inventory(
    data: pd.DataFrame,
    filtered: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
) -> pd.DataFrame:
    metrics = infrastructure_summary_metrics(data, filtered, material_columns)
    return pd.DataFrame(
        [
            {
                "Source / module": "SMART1383 database",
                "Scale": f"~{metrics['source_estimate']:,} source companies; {metrics['integrated_rows']:,} in DSS workbook",
                "Attributes in workbook": metrics["smart_columns"],
                "Connection keys": "business name, service address, jurisdiction, hauler, source row",
                "What it enables": "Business spine, outreach lists, jurisdiction slicing, hauler/contact context",
            },
            {
                "Source / module": "Mergent Intellect enrichment",
                "Scale": f"{metrics['company_count']:,} enriched companies; {metrics['duns_count']:,} with D-U-N-S",
                "Attributes in workbook": metrics["mergent_columns"],
                "Connection keys": "matched company identity, D-U-N-S, address, NAICS/SIC",
                "What it enables": "Geocoding, industry classification, employee/sales context, business group mapping",
            },
            {
                "Source / module": "CalRecycle calculator",
                "Scale": f"{metrics['material_categories']:,} material categories by stream",
                "Attributes in workbook": metrics["calrecycle_material_columns"],
                "Connection keys": "business group, jurisdiction profile, employee count",
                "What it enables": "Landfill/recycle/organics/diversion material ton estimates",
            },
            {
                "Source / module": "Suppressed CalRecycle areas",
                "Scale": f"{metrics['suppressed_count']:,} workbook rows use countywide same-group fallback",
                "Attributes in workbook": 2,
                "Connection keys": "suppressed local profile -> countywide same business group profile",
                "What it enables": "Coverage where local jurisdiction/business-group profiles are not publishable",
            },
            {
                "Source / module": "CalRecycle scaling tool",
                "Scale": f"{metrics['scaled_count']:,} scaled rows; {metrics['employee_count']:,} employee counts",
                "Attributes in workbook": metrics["calrecycle_columns"],
                "Connection keys": "employee count, calculator profile, material stream factors",
                "What it enables": "Per-business tonnage estimates and material-level DSS outputs",
            },
        ]
    )


def infrastructure_swimlane_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Swimlane": "Business identity",
                "Primary sources": "SMART1383 + Mergent Intellect",
                "Connection": "Name/address matching, D-U-N-S, physical location",
                "DSS result supported": "Business heat map, filtered business tables, outreach targeting",
            },
            {
                "Swimlane": "Industry classification",
                "Primary sources": "Mergent NAICS/SIC + SMART1383 business group fallback",
                "Connection": "NAICS/SIC mapping evidence and source group fallback",
                "DSS result supported": "Business group slicers, material profile assignment, vital-few rankings",
            },
            {
                "Swimlane": "Waste profile assignment",
                "Primary sources": "CalRecycle calculator + suppressed-area fallback",
                "Connection": "Jurisdiction/business group profile or countywide same-group profile",
                "DSS result supported": "Waste stream and material estimates, study-vs-model comparison",
            },
            {
                "Swimlane": "Per-business scaling",
                "Primary sources": "CalRecycle scaling tool + Mergent employee counts",
                "Connection": "Employee count multiplies profile factors into tons/year",
                "DSS result supported": "Tonnage heat maps, block group rankings, diversion opportunity",
            },
            {
                "Swimlane": "Spatial planning layer",
                "Primary sources": "Mergent coordinates + Census TIGER boundaries/roads",
                "Connection": "Latitude/longitude spatial joins and road graph routing",
                "DSS result supported": "Block group dashboard, circular flow engine, hauling emissions",
            },
        ]
    )


def assumptions_register() -> pd.DataFrame:
    """Living register of active DSS assumptions, transformations, and validation needs."""
    rows = [
        (
            "Data intake", "Source snapshot", "The integrated workbook is the analysis snapshot; the dashboard does not query live SMART1383, Mergent, CalRecycle, or hauler systems.", "Results reflect the workbook version selected in the sidebar.", "Active model rule",
        ),
        (
            "Data intake", "Record grain", "Each integrated workbook row is retained as a business/planner record; the dashboard does not apply an additional de-duplication pass.", "Duplicate or changed source records can affect totals and should be resolved upstream using source row, name, address, and D-U-N-S evidence.", "Validation needed",
        ),
        (
            "Data intake", "Business identity enrichment", "SMART1383 business context is connected to Mergent company, address, industry, employee, and D-U-N-S attributes through the integrated-workbook matching process.", "Uncertain matches should be audited before individual business outreach or compliance use.", "Validation needed",
        ),
        (
            "Data intake", "Missing descriptive fields", "Missing business name, jurisdiction, or business-group values are displayed as 'Unnamed business' or 'Unknown'.", "This prevents failed dashboard rows but does not repair the underlying source data.", "Active model rule",
        ),
        (
            "Data intake", "Numeric parsing", "Dashboard calculations coerce unreadable numeric values to missing and generally treat missing modeled tonnage as zero in aggregate calculations.", "A zero can mean no modeled tonnage or unavailable input; inspect source/status fields when that distinction matters.", "Active model rule",
        ),
        (
            "Classification", "Jurisdiction and business-group selection", "The selected workbook fields are treated as the current planning classification; users can switch among available SMART1383 and CalRecycle fields.", "Changing the selected field can change filters, profiles, and rollups.", "User-selectable",
        ),
        (
            "Classification", "Industry slicing", "Industry filters match exact displayed NAICS/SIC descriptions or line-of-business text, including any selected field when 'Any NAICS/SIC description' is used.", "Industry descriptions are screening context, not a verified operating-process classification.", "Active model rule",
        ),
        (
            "Waste estimation", "Profile basis", "CalRecycle calculator profiles by jurisdiction and business group are treated as representative waste-generation and material-composition factors.", "These are modeled estimates, not measured service-level tonnage for an individual business.", "Planning default",
        ),
        (
            "Waste estimation", "Suppressed-profile coverage", "When a local CalRecycle profile is suppressed, the integrated model uses a countywide profile for the same business group.", "Protects coverage but may not represent the local jurisdiction's actual waste mix.", "Planning default",
        ),
        (
            "Waste estimation", "Per-business scaling", "Profile factors are scaled to businesses using the integrated CalRecycle scaling output and available employee-count context.", "Employee counts and profile factors should be refreshed when business size or operations materially change.", "Planning default",
        ),
        (
            "Waste estimation", "Annual units", "Waste, landfill, diversion, and transport figures are interpreted as annual short tons unless a dashboard label states otherwise.", "Do not compare directly to monthly bills or route tickets without matching time units.", "Active model rule",
        ),
        (
            "Waste estimation", "Material completeness", "Only material/stream columns recognized from the integrated CalRecycle naming pattern are included in material-specific outputs.", "Unrecognized or newly added material columns require a model update before they appear.", "Validation needed",
        ),
        (
            "Spatial processing", "Coordinate source", "Business coordinates supplied in the integrated workbook are used as the business location; no address-level geocoding is performed in the dashboard.", "A point can be inaccurate even when it is within the county envelope.", "Validation needed",
        ),
        (
            "Spatial processing", "Coordinate quality screen", "Mapped records require numeric latitude/longitude, non-zero values, and locations within the configured San Luis Obispo County planning envelope.", "Records outside that envelope remain in non-map calculations but are excluded from maps, spatial joins, and transport-distance estimates.", "Active model rule",
        ),
        (
            "Spatial processing", "Census geography", "Block-group boundaries use Census TIGER/Line 2023 California data filtered to County FIPS 079; ZCTAs use Census 2020 cartographic boundaries.", "Census places/CDPs are a proxy for jurisdiction/community overlays, not legal city, CSD, or sanitary-district boundaries.", "Planning default",
        ),
        (
            "Spatial processing", "Block-group assignment", "Businesses are assigned to the polygon containing their mapped point.", "Boundary-edge points and inaccurate coordinates can be assigned to the wrong geography.", "Validation needed",
        ),
        (
            "Aggregate reporting", "Multifamily treatment", "Multifamily records stay available in business-level displays but are excluded from aggregate ICI metrics, heat intensity, block-group rankings, diversion summaries, and study-validation totals.", "This keeps commercial/ICI comparisons aligned to the study basis while preserving planner visibility.", "Active model rule",
        ),
        (
            "Diversion analysis", "Diversion potential", "Landfill-disposed material tons are mapped to curbside recycle, curbside organics, third-party diversion, or not-readily-recoverable pathways using the dashboard material mapping.", "A mapped pathway is a screening opportunity, not proof of service availability, contamination acceptance, economics, or business participation.", "Planning default",
        ),
        (
            "Diversion analysis", "Thresholding", "The dashboard's minimum opportunity tons and minimum share of landfill controls define which businesses are counted as practical outreach targets.", "Thresholds change target counts and rankings; they do not change the underlying modeled tons.", "User-selectable",
        ),
        (
            "Diversion analysis", "Study-calibrated mode", "Calibrated mode rescales destination totals to the 2025 ICI study pathway shares while preserving the workbook-based rank order within each pathway.", "Use raw mode for the workbook estimate; calibration improves aggregate alignment but is not a business-level measurement.", "Planning default",
        ),
        (
            "Study validation", "ICI comparison denominator", "The validation dashboard compares the model to the 2025 SLO County ICI study sector basis of 34,280 tons and also displays the 57,705-ton table basis where relevant.", "The report contains different denominators; shares are used for calibration and both values are disclosed.", "Active model rule",
        ),
        (
            "Landfill allocation", "Known hauler destinations", "Waste Connections garbage is assigned to Cold Canyon; Waste Management/WM to Chicago Grade; Paso Robles Waste and San Miguel Garbage to the City of Paso Robles Landfill.", "These assignments reflect the County/IWMA-provided operating information and apply only to recognized trash-hauler text.", "Source-provided rule",
        ),
        (
            "Landfill allocation", "Unknown-hauler fallback", "Blank or unrecognized haulers use a distance-and-wasteshed allocation among the three mapped landfills.", "Fallback assignments are explicitly labeled and should be replaced when hauler/facility evidence becomes available.", "Planning default",
        ),
        (
            "Landfill allocation", "Planning shares", "Fallback allocation uses 2019 mapped wasteshed shares: Cold Canyon 51.0%, Chicago Grade 31.5%, and City of Paso Robles 14.2%, normalized across the three mapped facilities.", "The smaller 'other facilities not mapped' share is excluded from this three-landfill fallback; use facility/hauler tonnage when available.", "Planning default",
        ),
        (
            "Transport emissions", "Distance method", "The Diversion opportunity transport extension estimates one-way road miles as straight-line business-to-assigned-landfill distance multiplied by the user-selected road-mile multiplier (default 1.25).", "This is not a stop-by-stop collection-route simulation. Census TIGER and OpenStreetMap road-network options are available in the Circular Flow engine for route-network estimates.", "Planning default",
        ),
        (
            "Transport emissions", "Shared truck payload", "Annual business garbage tons are divided by the user-selected average collection load (default 7 short tons, or 14,000 lb) to allocate truckload-equivalent trips.", "The model does not assign one dedicated weekly truck trip to every business.", "Planning default",
        ),
        (
            "Transport emissions", "Operational route adjustment", "Allocated vehicle miles equal one-way miles × truckload-equivalent trips × the user-selected collection-route adjustment (default 1.15).", "The adjustment approximates collection circulation, staging, and return movement; it does not reproduce actual hauler route sequences.", "Planning default",
        ),
        (
            "Transport emissions", "Vehicle-mile emissions factor", "Truck CO2e equals allocated annual vehicle miles × the user-selected factor (default 4.1 kg CO2e per vehicle-mile), converted to metric tons.", "Replace with fleet-specific fuel, vehicle, telematics, or MOVES factors for operational accounting.", "Planning default",
        ),
        (
            "Circular economy", "Supplier signal", "Potential suppliers are businesses with modeled landfill-disposed tons of selected materials.", "The signal does not establish material quality, ownership, availability, or willingness to exchange.", "Planning default",
        ),
        (
            "Circular economy", "Potential-user signal", "Potential users are inferred from business group, NAICS/SIC descriptions, line-of-business text, and business-name keywords.", "A keyword/industry match is not confirmation of procurement demand or technical compatibility.", "Validation needed",
        ),
    ]
    table = pd.DataFrame(
        rows,
        columns=["Stage", "Assumption / decision", "Implementation", "Effect / validation need", "Status"],
    )
    dashboard_map = {
        "Data intake": "All dashboards; Data infrastructure",
        "Classification": "Business heat map; Census block groups; Diversion opportunity; Outreach campaign builder; Circular economy marketplace; Circular flow engine",
        "Waste estimation": "Home; Business heat map; Census block groups; Diversion opportunity; Outreach campaign builder; Circular economy marketplace; Circular flow engine; 2025 study vs model",
        "Spatial processing": "Business heat map; Census block groups; Diversion opportunity; Circular economy marketplace; Circular flow engine",
        "Aggregate reporting": "Home; Business heat map; Census block groups; Diversion opportunity; 2025 study vs model",
        "Diversion analysis": "Diversion opportunity; Outreach campaign builder; 2025 study vs model",
        "Study validation": "2025 study vs model; Diversion opportunity",
        "Landfill allocation": "Diversion opportunity; Circular flow engine",
        "Transport emissions": "Diversion opportunity; Circular flow engine",
        "Circular economy": "Circular economy marketplace",
    }
    table["Relevant dashboards"] = table["Stage"].map(dashboard_map).fillna("Assumptions")
    return table[
        [
            "Stage",
            "Relevant dashboards",
            "Assumption / decision",
            "Implementation",
            "Effect / validation need",
            "Status",
        ]
    ]


def navigate_to_assumption_dashboard() -> None:
    target = st.session_state.get("assumptions_dashboard_target")
    if target in DASHBOARD_OPTIONS:
        st.session_state.dashboard_view = target


def open_guide_dashboard(target: str) -> None:
    if target in DASHBOARD_OPTIONS:
        st.session_state.dashboard_view = target


def render_quick_start_guide() -> None:
    """Render the planner-facing onboarding page and dashboard launch points."""
    st.markdown(
        """
        <style>
        .guide-hero { background: linear-gradient(118deg, #1f5f8b 0%, #245e63 49%, #4f7f3f 100%); border-radius: 18px; color: white; padding: 32px 34px 30px; margin: 6px 0 22px; box-shadow: 0 12px 28px rgba(31, 95, 139, 0.18); }
        .guide-eyebrow { font-size: 0.76rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #d8ecdb; margin-bottom: 8px; }
        .guide-hero h2 { color: white; margin: 0 0 9px; font-size: 2rem; line-height: 1.14; }
        .guide-hero p { color: #edf7f1; font-size: 1.05rem; max-width: 750px; margin: 0; line-height: 1.55; }
        .guide-section-label { color: #1f5f8b; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; margin: 25px 0 4px; }
        .guide-choice { background: #ffffff; border: 1px solid #dce5df; border-radius: 14px; padding: 19px 19px 14px; min-height: 192px; box-shadow: 0 3px 10px rgba(43, 61, 49, 0.06); }
        .guide-choice-number { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 50%; background: #e8f1e5; color: #386a30; font-weight: 700; font-size: 0.87rem; margin-bottom: 11px; }
        .guide-choice h3 { color: #243d32; font-size: 1.06rem; margin: 0 0 8px; }
        .guide-choice p { color: #5b6960; font-size: 0.9rem; line-height: 1.45; margin: 0; }
        .guide-path { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 12px 0 7px; }
        .guide-step { position: relative; padding: 15px 13px 15px 17px; border-left: 4px solid #82a95a; background: #f7faf6; min-height: 122px; }
        .guide-step strong { color: #264738; display: block; margin-bottom: 5px; font-size: 0.94rem; }
        .guide-step span { color: #627066; font-size: 0.84rem; line-height: 1.36; }
        .guide-use { background: #f6f9fb; border-radius: 12px; padding: 16px 17px; min-height: 130px; border-top: 3px solid #1f5f8b; }
        .guide-use h3 { font-size: 0.97rem; color: #27475f; margin: 0 0 7px; }
        .guide-use p { font-size: 0.87rem; line-height: 1.42; color: #53636c; margin: 0; }
        @media (max-width: 760px) { .guide-hero { padding: 24px 22px; } .guide-hero h2 { font-size: 1.55rem; } .guide-path { grid-template-columns: 1fr; } .guide-choice { min-height: auto; } }
        </style>
        <section class="guide-hero" aria-labelledby="guide-title">
          <div class="guide-eyebrow">San Luis Obispo County · planning support</div>
          <h2 id="guide-title">Turn business waste data into a practical next move.</h2>
          <p>Start with the planning question you need to answer. This tool estimates where waste is generated, what may be divertible, and where a focused conversation could have the greatest value.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("Watch the walkthrough")
    if TUTORIAL_VIDEO_PATH.exists():
        st.video(str(TUTORIAL_VIDEO_PATH), format="video/mp4")
        st.caption("A short walkthrough of the IWMA Decision Support System Prototype and its planner-facing dashboards.")
    else:
        st.info("The tutorial video is not included in this deployment yet.")

    st.markdown("<div class='guide-section-label'>Choose your starting point</div>", unsafe_allow_html=True)
    priority_col, diversion_col, evidence_col = st.columns(3)
    with priority_col:
        st.markdown(
            """<div class="guide-choice"><div class="guide-choice-number">1</div><h3>Find priority places</h3><p>See where modeled tons, business intensity, or concentrated generators point to a useful geographic focus.</p></div>""",
            unsafe_allow_html=True,
        )
        if "Business heat map" in DASHBOARD_OPTIONS:
            st.button("Explore priority places", key="guide_heat", on_click=open_guide_dashboard, args=("Business heat map",), width="stretch")
    with diversion_col:
        st.markdown(
            """<div class="guide-choice"><div class="guide-choice-number">2</div><h3>Build a diversion action</h3><p>Identify businesses and materials with modeled landfill-disposed tons that may have a practical diversion pathway.</p></div>""",
            unsafe_allow_html=True,
        )
        if "Diversion opportunity" in DASHBOARD_OPTIONS:
            st.button("Find diversion opportunities", key="guide_diversion", on_click=open_guide_dashboard, args=("Diversion opportunity",), width="stretch")
    with evidence_col:
        st.markdown(
            """<div class="guide-choice"><div class="guide-choice-number">3</div><h3>Check evidence and limits</h3><p>Review sources, active assumptions, validation needs, and the distinction between model estimates and verified operations.</p></div>""",
            unsafe_allow_html=True,
        )
        if "Assumptions" in DASHBOARD_OPTIONS:
            st.button("Review assumptions", key="guide_assumptions", on_click=open_guide_dashboard, args=("Assumptions",), width="stretch")

    st.markdown("<div class='guide-section-label'>A simple planning workflow</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="guide-path" aria-label="Four-step planning workflow">
          <div class="guide-step"><strong>1. Frame the question</strong><span>Choose a jurisdiction, business group, material, or landfill concern you want to explore.</span></div>
          <div class="guide-step"><strong>2. Find a signal</strong><span>Use maps and ranked drivers to locate a concentrated, high-tonnage, or high-opportunity pattern.</span></div>
          <div class="guide-step"><strong>3. Read the caveat</strong><span>Check the confidence label, assumptions, and whether the number is modeled, source-provided, or needs validation.</span></div>
          <div class="guide-step"><strong>4. Validate and act</strong><span>Confirm promising sites with haulers, businesses, service data, or field outreach before using the result operationally.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='guide-section-label'>How to use the results responsibly</div>", unsafe_allow_html=True)
    use_cols = st.columns(3)
    use_content = [
        ("Use it to prioritize", "Use modeled tons and concentrations to decide where a conversation, site review, or campaign could be most worthwhile."),
        ("Do not treat it as a bill", "Business-level tonnage and diversion results are estimates from profiles and scaling—not measured service-account data."),
        ("Keep the next step human", "The strongest workflow is model signal → operational confirmation → targeted action, with assumptions visible at every step."),
    ]
    for column, (heading, body) in zip(use_cols, use_content):
        with column:
            st.markdown(f"<div class='guide-use'><h3>{heading}</h3><p>{body}</p></div>", unsafe_allow_html=True)

    st.markdown("<div class='guide-section-label'>Dashboard guide</div>", unsafe_allow_html=True)
    dashboard_guide = pd.DataFrame(
        [
            ("Business heat map", "Where are modeled waste signals concentrated?", "Tonnage intensity, business density, and high-volume locations", "Coordinate quality and modeled waste estimates"),
            ("Census block groups", "Which small areas should be compared?", "Block-group rankings and selected-area business drivers", "Point-in-polygon assignment and Census geography"),
            ("Diversion opportunity", "Which businesses or materials warrant outreach?", "Ranked opportunities, pathways, landfill transport, and exports", "Diversion is a screening signal; verify service and material acceptance"),
            ("Assumptions", "What is the model assuming?", "Rules, defaults, validation priorities, and dashboard crosswalk", "A living register; use it alongside planning decisions"),
            ("2025 study vs model", "How does the model compare with the county study?", "Material and pathway gaps, denominators, and diagnostic calibration", "Comparison is diagnostic, not a claim of measured accuracy"),
        ],
        columns=["Dashboard", "Best planning question", "What you get", "Read before acting"],
    )
    dashboard_guide = dashboard_guide[dashboard_guide["Dashboard"].isin(DASHBOARD_OPTIONS)]
    st.dataframe(dashboard_guide, width="stretch", hide_index=True, height=260)
    st.caption("Tip: use the left-side filters first when you already know the jurisdiction, business group, or industry you want to investigate.")


def render_infrastructure_hierarchy(metrics: dict[str, int]) -> None:
    cards = [
        (
            "Source systems",
            [
                ("SMART1383", f"~{metrics['source_estimate']:,} source companies"),
                ("Mergent Intellect", f"{metrics['company_count']:,} enriched companies"),
                ("CalRecycle calculator", f"{metrics['material_categories']:,} material categories"),
            ],
        ),
        (
            "Harmonization",
            [
                ("Business spine", f"{metrics['integrated_rows']:,} integrated rows"),
                ("Identity enrichment", f"{metrics['duns_count']:,} D-U-N-S matches"),
                ("Business group mapping", f"{metrics['mapping_columns']:,} mapping attributes"),
            ],
        ),
        (
            "Waste modeling",
            [
                ("Profile assignment", f"{metrics['scaled_count']:,} scaled rows"),
                ("Suppressed areas", f"{metrics['suppressed_count']:,} fallback rows"),
                ("Material streams", f"{metrics['calrecycle_material_columns']:,} tonnage attributes"),
            ],
        ),
        (
            "DSS outputs",
            [
                ("Maps", "heat, block groups, diversion, circular flow"),
                ("Drivers", "businesses, materials, destinations"),
                ("Planning filters", f"{metrics['active_rows']:,} active rows in current slice"),
            ],
        ),
    ]
    column_html = []
    for title, items in cards:
        item_html = "".join(
            (
                "<div class='infra-card'>"
                f"<div class='infra-card-title'>{html.escape(label)}</div>"
                f"<div class='infra-card-meta'>{html.escape(value)}</div>"
                "</div>"
            )
            for label, value in items
        )
        column_html.append(
            "<div class='infra-column'>"
            f"<div class='infra-column-title'>{html.escape(title)}</div>"
            f"{item_html}"
            "</div>"
        )
    st.markdown(
        """
        <style>
        .infra-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 12px 0 20px 0;
        }
        .infra-column {
            border: 1px solid #dfe4de;
            border-radius: 8px;
            background: #fbfcfa;
            padding: 12px;
            min-height: 260px;
        }
        .infra-column-title {
            font-weight: 700;
            color: #1f5f8b;
            margin-bottom: 10px;
            font-size: 0.95rem;
        }
        .infra-card {
            border-left: 4px solid #4f7f3f;
            background: white;
            border-radius: 6px;
            padding: 10px;
            margin-bottom: 10px;
            box-shadow: 0 1px 2px rgba(30, 40, 30, 0.06);
        }
        .infra-card-title {
            font-weight: 650;
            color: #2f342f;
            margin-bottom: 3px;
        }
        .infra-card-meta {
            color: #606b65;
            font-size: 0.84rem;
            line-height: 1.25rem;
        }
        @media (max-width: 900px) {
            .infra-grid { grid-template-columns: 1fr; }
        }
        </style>
        """
        + "<div class='infra-grid'>"
        + "".join(column_html)
        + "</div>",
        unsafe_allow_html=True,
    )


def material_destination(material_key: str) -> str:
    if material_key in CURBSIDE_RECYCLE_MATERIALS:
        return "curbside_recycle"
    if material_key in CURBSIDE_ORGANICS_MATERIALS:
        return "curbside_organics"
    if material_key in THIRD_PARTY_DIVERSION_MATERIALS:
        return "third_party_diversion"
    return "not_readily_recoverable"


def destination_label(destination: str) -> str:
    return DESTINATION_STREAMS.get(destination, DESTINATION_STREAMS["not_readily_recoverable"])["label"]


def iwma_destination_bar_chart(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    color_column: str = "Destination",
    height: int = 320,
) -> alt.Chart:
    if data.empty:
        return alt.Chart(pd.DataFrame({x_column: [], y_column: [], color_column: []})).mark_bar()

    tooltips = [
        alt.Tooltip(f"{x_column}:N", title=x_column),
        alt.Tooltip(f"{y_column}:Q", title=y_column, format=",.1f"),
    ]
    if color_column in data.columns and color_column != x_column:
        tooltips.insert(1, alt.Tooltip(f"{color_column}:N", title=color_column))
    color_values = (
        data[color_column].dropna().astype(str).unique().tolist()
        if color_column in data.columns
        else []
    )
    color_domain = [label for label in IWMA_DESTINATION_COLORS if label in color_values]
    color_domain.extend(label for label in color_values if label not in color_domain)
    color_range = [IWMA_DESTINATION_COLORS.get(label, IWMA_BLUE) for label in color_domain]

    return (
        alt.Chart(data)
        .mark_bar(opacity=0.9)
        .encode(
            x=alt.X(f"{x_column}:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-30, labelLimit=150)),
            y=alt.Y(f"{y_column}:Q", title=y_column),
            color=alt.Color(
                f"{color_column}:N",
                scale=alt.Scale(
                    domain=color_domain,
                    range=color_range,
                ),
                title=None,
            ),
            tooltip=tooltips,
        )
        .properties(height=height)
    )


def study_alignment_score(group_composition: pd.DataFrame) -> float:
    if group_composition.empty:
        return 0.0
    differences = pd.to_numeric(group_composition.get("Difference (pp)", pd.Series(dtype=float)), errors="coerce")
    total_variation_gap = float(differences.abs().sum()) / 2
    return float(np.clip(100 - total_variation_gap, 0, 100))


def alignment_label(score: float) -> str:
    if score >= 85:
        return "High alignment"
    if score >= 70:
        return "Moderate alignment"
    return "Needs validation"


def confidence_label(kind: str) -> str:
    labels = {
        "source": "high confidence",
        "model": "model estimate",
        "validation": "needs validation",
    }
    return labels.get(kind, "model estimate")


def render_confidence_badge(label: str, kind: str) -> str:
    colors = {
        "source": ("#e9f2e7", IWMA_GREEN),
        "model": ("#e8f0f6", IWMA_BLUE),
        "validation": ("#f2edf7", IWMA_PURPLE),
    }
    background, color = colors.get(kind, colors["model"])
    return (
        f"<span style='display:inline-block;padding:0.18rem 0.55rem;border-radius:999px;"
        f"background:{background};color:{color};font-size:0.78rem;font-weight:650;'>"
        f"{html.escape(label)}</span>"
    )


def render_metric_confidence_labels(rows: list[dict[str, str]]) -> None:
    card_html = "".join(
        "<div style='border:1px solid #dfe4de;border-radius:8px;padding:0.65rem 0.75rem;background:#fff;'>"
        f"<div style='font-weight:650;color:#30342f;margin-bottom:0.25rem;'>{html.escape(row['Metric'])}</div>"
        f"{render_confidence_badge(row['Confidence'], row['Kind'])}"
        f"<div style='font-size:0.82rem;color:#5f6762;margin-top:0.35rem;'>{html.escape(row['Basis'])}</div>"
        "</div>"
        for row in rows
    )
    st.markdown(
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:0.7rem;'>"
        + card_html
        + "</div>",
        unsafe_allow_html=True,
    )


def home_briefing_insights(
    opportunity: pd.DataFrame,
    destination_rollup: pd.DataFrame,
    material_detail: pd.DataFrame,
    business_group_rollup: pd.DataFrame,
    group_composition: pd.DataFrame,
    focused_opportunity: pd.DataFrame,
    organics_tons: float,
    methane_co2e: float,
    alignment_score_value: float,
) -> list[dict[str, str]]:
    insights: list[dict[str, str]] = []
    if not destination_rollup.empty:
        top_destination = destination_rollup.iloc[0]
        insights.append(
            {
                "Title": f"{top_destination['Destination']} is the largest diversion pathway",
                "Value": f"{float(top_destination[POTENTIAL_TONS_COLUMN]):,.1f} modeled tons",
                "Detail": "Use this to choose the first outreach pathway for the current slice.",
                "Kind": "validation",
            }
        )
    if not business_group_rollup.empty:
        top_group = business_group_rollup.iloc[0]
        insights.append(
            {
                "Title": f"{top_group['Business Group']} leads business-group opportunity",
                "Value": f"{float(top_group[POTENTIAL_TONS_COLUMN]):,.1f} modeled tons",
                "Detail": f"{int(top_group['Businesses']):,} businesses in this group contribute to the signal.",
                "Kind": "model",
            }
        )
    if not material_detail.empty:
        top_material = (
            material_detail.groupby(["Material", "Destination"], dropna=False)[POTENTIAL_TONS_COLUMN]
            .sum()
            .reset_index()
            .sort_values(POTENTIAL_TONS_COLUMN, ascending=False)
            .head(1)
        )
        if not top_material.empty:
            row = top_material.iloc[0]
            insights.append(
                {
                    "Title": f"{row['Material']} is the top material signal",
                    "Value": f"{float(row[POTENTIAL_TONS_COLUMN]):,.1f} modeled tons",
                    "Detail": f"Recommended pathway: {row['Destination']}.",
                    "Kind": "validation",
                }
            )
    if not group_composition.empty:
        gap_row = group_composition.sort_values("Abs Difference (pp)", ascending=False).head(1)
        if not gap_row.empty:
            row = gap_row.iloc[0]
            insights.append(
                {
                    "Title": f"{row['Material Group']} is the largest study-alignment gap",
                    "Value": f"{float(row['Difference (pp)']):+.1f} percentage points",
                    "Detail": "This is the first place to audit workbook allocation assumptions.",
                    "Kind": "validation",
                }
            )
    insights.append(
        {
            "Title": "Organics diversion has near-term methane relevance",
            "Value": f"{methane_co2e:,.1f} 20-year CO2e tons",
            "Detail": f"Based on {organics_tons:,.1f} modeled organics tons in landfill.",
            "Kind": "model",
        }
    )
    insights.append(
        {
            "Title": f"{len(focused_opportunity):,} businesses meet the outreach threshold",
            "Value": f"{alignment_score_value:.0f}% study alignment",
            "Detail": "Use the action queue below to turn this into campaign lists.",
            "Kind": "model",
        }
    )
    return insights[:5]


def render_briefing_cards(insights: list[dict[str, str]]) -> None:
    if not insights:
        st.warning("No briefing insights are available for the current slice.")
        return
    card_html = "".join(
        "<div style='border:1px solid #dfe4de;border-radius:8px;padding:0.85rem;background:#fff;'>"
        f"{render_confidence_badge(confidence_label(insight['Kind']), insight['Kind'])}"
        f"<div style='font-size:1rem;font-weight:700;color:#30342f;margin-top:0.55rem;'>"
        f"{html.escape(insight['Title'])}</div>"
        f"<div style='font-size:1.15rem;font-weight:750;color:{IWMA_BLUE};margin-top:0.35rem;'>"
        f"{html.escape(insight['Value'])}</div>"
        f"<div style='font-size:0.86rem;color:#5f6762;margin-top:0.35rem;line-height:1.25rem;'>"
        f"{html.escape(insight['Detail'])}</div>"
        "</div>"
        for insight in insights
    )
    st.markdown(
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:0.8rem;'>"
        + card_html
        + "</div>",
        unsafe_allow_html=True,
    )


def home_sankey_links(stream_totals: pd.DataFrame, opportunity: pd.DataFrame) -> pd.DataFrame:
    rows = []
    stream_tons = dict(zip(stream_totals["Waste Stream"], stream_totals["Tons"])) if not stream_totals.empty else {}
    for stream_label in ["Landfill", "Recycle", "Organics", "Diversion"]:
        tons = float(stream_tons.get(stream_label, 0.0))
        if tons > 0:
            rows.append({"Source": "Total generation", "Target": stream_label, "Tons": tons})

    landfill_destination_labels = {
        "curbside_recycle": "Curbside recycle opportunity",
        "curbside_organics": "Curbside organics opportunity",
        "third_party_diversion": "Third-party diversion opportunity",
        "not_readily_recoverable": "Not readily recoverable",
    }
    for destination, label in landfill_destination_labels.items():
        if destination in opportunity.columns:
            tons = float(pd.to_numeric(opportunity[destination], errors="coerce").fillna(0).sum())
            if tons > 0:
                rows.append({"Source": "Landfill", "Target": label, "Tons": tons})

    passthroughs = {
        "Recycle": "Already in recycle stream",
        "Organics": "Already in organics stream",
        "Diversion": "Existing other diversion",
    }
    for source, target in passthroughs.items():
        tons = float(stream_tons.get(source, 0.0))
        if tons > 0:
            rows.append({"Source": source, "Target": target, "Tons": tons})
    return pd.DataFrame(rows)


def sankey_node_color(label: str) -> str:
    lowered = label.lower()
    if "organics" in lowered:
        return IWMA_GREEN
    if "recycle" in lowered:
        return IWMA_BLUE
    if "third" in lowered or "diversion" in lowered:
        return IWMA_PURPLE
    if "landfill" in lowered or "not readily" in lowered:
        return IWMA_GRAY
    return IWMA_LIGHT_GREEN


def render_svg_sankey(links: pd.DataFrame) -> None:
    if links.empty:
        return
    width = 980
    height = 430
    columns = {
        "Total generation": 80,
        "Landfill": 360,
        "Recycle": 360,
        "Organics": 360,
        "Diversion": 360,
    }
    target_labels = [label for label in links["Target"].unique().tolist() if label not in columns]
    stream_labels = ["Landfill", "Recycle", "Organics", "Diversion"]
    stream_y = {
        label: y
        for label, y in zip(stream_labels, np.linspace(95, height - 95, len(stream_labels)))
        if label in set(links["Source"]).union(set(links["Target"]))
    }
    target_y = {
        label: y
        for label, y in zip(target_labels, np.linspace(55, height - 55, max(len(target_labels), 1)))
    }
    positions = {"Total generation": (80, height / 2)}
    positions.update({label: (360, y) for label, y in stream_y.items()})
    positions.update({label: (710, y) for label, y in target_y.items()})

    max_tons = max(float(links["Tons"].max()), 1.0)
    paths = []
    for _, row in links.iterrows():
        source = row["Source"]
        target = row["Target"]
        if source not in positions or target not in positions:
            continue
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        stroke_width = max(2.0, min(34.0, float(row["Tons"]) / max_tons * 34.0))
        color = sankey_node_color(target)
        paths.append(
            f"<path d='M{x1 + 16},{y1} C{x1 + 145},{y1} {x2 - 145},{y2} {x2 - 16},{y2}' "
            f"fill='none' stroke='{color}' stroke-opacity='0.24' stroke-width='{stroke_width:.2f}' />"
        )

    nodes = []
    for label, (x, y) in positions.items():
        incoming = links.loc[links["Target"] == label, "Tons"].sum()
        outgoing = links.loc[links["Source"] == label, "Tons"].sum()
        tons = float(max(incoming, outgoing))
        node_height = max(20, min(72, tons / max_tons * 72))
        color = sankey_node_color(label)
        label_x = x + 24 if x < 650 else x + 24
        label_anchor = "start"
        tons_text = f"{tons:,.0f} tons" if tons > 0 else ""
        nodes.append(
            f"<rect x='{x - 8}' y='{y - node_height / 2:.1f}' width='16' height='{node_height:.1f}' "
            f"rx='4' fill='{color}' />"
            f"<text x='{label_x}' y='{y - 3:.1f}' text-anchor='{label_anchor}' "
            f"font-size='12' font-weight='700' fill='#30342f'>{html.escape(label)}</text>"
            f"<text x='{label_x}' y='{y + 13:.1f}' text-anchor='{label_anchor}' "
            f"font-size='11' fill='#5f6762'>{html.escape(tons_text)}</text>"
        )

    svg = (
        f"<div style='border:1px solid #dfe4de;border-radius:8px;background:white;padding:0.5rem;'>"
        f"<svg viewBox='0 0 {width} {height}' width='100%' height='430' role='img' "
        f"aria-label='Countywide Sankey flow overview'>"
        + "".join(paths)
        + "".join(nodes)
        + "</svg></div>"
    )
    st.markdown(svg, unsafe_allow_html=True)


def render_countywide_sankey(stream_totals: pd.DataFrame, opportunity: pd.DataFrame) -> None:
    links = home_sankey_links(stream_totals, opportunity)
    if links.empty:
        st.warning("No generation-flow values are available for the current slice.")
        return
    try:
        import plotly.graph_objects as go
    except ImportError:
        render_svg_sankey(links)
        return

    labels = pd.Index(pd.concat([links["Source"], links["Target"]], ignore_index=True).unique()).tolist()
    label_index = {label: index for index, label in enumerate(labels)}
    colors = []
    for label in labels:
        if "organics" in label.lower():
            colors.append(IWMA_GREEN)
        elif "recycle" in label.lower():
            colors.append(IWMA_BLUE)
        elif "third" in label.lower() or "diversion" in label.lower():
            colors.append(IWMA_PURPLE)
        elif "landfill" in label.lower() or "not readily" in label.lower():
            colors.append(IWMA_GRAY)
        else:
            colors.append(IWMA_LIGHT_GREEN)

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node={
                    "pad": 16,
                    "thickness": 16,
                    "line": {"color": "rgba(80, 88, 82, 0.35)", "width": 0.5},
                    "label": labels,
                    "color": colors,
                },
                link={
                    "source": links["Source"].map(label_index),
                    "target": links["Target"].map(label_index),
                    "value": links["Tons"],
                    "color": "rgba(79, 127, 63, 0.22)",
                },
            )
        ]
    )
    fig.update_layout(
        height=420,
        margin={"l": 8, "r": 8, "t": 12, "b": 8},
        font={"size": 12, "color": "#30342f"},
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    st.plotly_chart(fig, width="stretch")


def home_action_queue(
    material_detail: pd.DataFrame,
    min_tons: float = DEFAULT_OPPORTUNITY_TON_THRESHOLD,
) -> pd.DataFrame:
    if material_detail.empty:
        return pd.DataFrame(
            columns=[
                "Recommended Campaign",
                "Preferred Destination",
                "Business Group",
                "Top Jurisdiction",
                "Expected Tons Impacted",
                "Businesses",
                "Confidence",
            ]
        )
    grouped = (
        material_detail.groupby(["Destination", "Material", "Business Group"], dropna=False)
        .agg(
            **{
                "Expected Tons Impacted": (POTENTIAL_TONS_COLUMN, "sum"),
                "Businesses": ("_business_row_id", "nunique"),
                "Top Jurisdiction": ("Jurisdiction", most_common_text),
            }
        )
        .reset_index()
    )
    grouped = grouped[grouped["Expected Tons Impacted"] >= float(min_tons)].copy()
    if grouped.empty:
        return pd.DataFrame()
    grouped["Recommended Campaign"] = (
        grouped["Material"].astype(str)
        + " outreach for "
        + grouped["Business Group"].astype(str)
    )
    grouped["Preferred Destination"] = grouped["Destination"]
    grouped["Confidence"] = "model estimate; validate with hauler/IWMA outreach"
    return grouped[
        [
            "Recommended Campaign",
            "Preferred Destination",
            "Business Group",
            "Top Jurisdiction",
            "Expected Tons Impacted",
            "Businesses",
            "Confidence",
        ]
    ].sort_values("Expected Tons Impacted", ascending=False)


def build_campaign_business_table(
    opportunity: pd.DataFrame,
    material_detail: pd.DataFrame,
    filtered: pd.DataFrame,
    latitude_column: str,
    longitude_column: str,
    selected_material_labels: list[str],
    selected_destinations: list[str],
    selected_business_groups: list[str],
    min_tons: float,
) -> pd.DataFrame:
    if opportunity.empty or material_detail.empty:
        return pd.DataFrame()

    detail = material_detail.copy()
    if selected_material_labels:
        detail = detail[detail["Material"].isin(selected_material_labels)].copy()
    if selected_destinations:
        detail = detail[detail["Destination Key"].isin(selected_destinations)].copy()
    if detail.empty:
        return pd.DataFrame()

    rollup = (
        detail.groupby("_business_row_id", dropna=False)
        .agg(
            **{
                "Campaign Opportunity Tons": (POTENTIAL_TONS_COLUMN, "sum"),
                "Materials": ("Material", lambda values: ", ".join(pd.Series(values).dropna().astype(str).drop_duplicates().head(4))),
                "Preferred Destinations": ("Destination", lambda values: ", ".join(pd.Series(values).dropna().astype(str).drop_duplicates().head(3))),
                "Material Count": ("Material", "nunique"),
            }
        )
        .reset_index()
    )
    top_detail = (
        detail.sort_values(POTENTIAL_TONS_COLUMN, ascending=False)
        .drop_duplicates("_business_row_id")
        .loc[:, ["_business_row_id", "Material", "Destination", "Destination Key"]]
        .rename(
            columns={
                "Material": "Top Campaign Material",
                "Destination": "Top Campaign Destination",
                "Destination Key": "Dominant Destination Key",
            }
        )
    )
    rollup = rollup.merge(top_detail, on="_business_row_id", how="left")

    base_columns = [
        "_business_row_id",
        "Business",
        "Jurisdiction",
        "Business Group",
        "ZIP Code",
        "Hauler",
        "Phone",
        "Website",
        "Address",
        "Landfill Tons",
    ]
    base = opportunity[[column for column in base_columns if column in opportunity.columns]].copy()
    rows = base.merge(rollup, on="_business_row_id", how="inner")

    coords = filtered[["_business_row_id", latitude_column, longitude_column]].rename(
        columns={latitude_column: "latitude", longitude_column: "longitude"}
    )
    rows = rows.merge(coords, on="_business_row_id", how="left")
    rows["latitude"] = pd.to_numeric(rows["latitude"], errors="coerce")
    rows["longitude"] = pd.to_numeric(rows["longitude"], errors="coerce")
    rows = rows[valid_coordinate_mask(rows)].copy()

    if selected_business_groups:
        rows = rows[rows["Business Group"].astype(str).isin(selected_business_groups)].copy()

    rows["Campaign Opportunity Tons"] = pd.to_numeric(
        rows["Campaign Opportunity Tons"],
        errors="coerce",
    ).fillna(0.0)
    if "Landfill Tons" in rows.columns:
        rows["Landfill Tons"] = pd.to_numeric(rows["Landfill Tons"], errors="coerce").fillna(0.0)
    else:
        rows["Landfill Tons"] = 0.0
    rows = rows[rows["Campaign Opportunity Tons"] >= float(min_tons)].copy()
    rows["Campaign Opportunity Share"] = np.where(
        rows["Landfill Tons"] > 0,
        rows["Campaign Opportunity Tons"] / rows["Landfill Tons"] * 100,
        0.0,
    )

    colors = rows["Dominant Destination Key"].map(
        lambda key: DESTINATION_STREAMS.get(key, DESTINATION_STREAMS["not_readily_recoverable"])["color"]
    )
    rows["color_r"] = colors.map(lambda color: color[0])
    rows["color_g"] = colors.map(lambda color: color[1])
    rows["color_b"] = colors.map(lambda color: color[2])
    rows["color_a"] = colors.map(lambda color: color[3])
    rows["point_radius"] = np.clip(np.sqrt(rows["Campaign Opportunity Tons"].clip(lower=0)) * 8 + 35, 35, 320)
    rows["tooltip_title"] = rows["Business"].fillna("Campaign target").astype(str)
    rows["tooltip_body"] = (
        "Campaign tons: "
        + rows["Campaign Opportunity Tons"].map(lambda value: f"{value:,.1f}")
        + "<br/>Share of landfill: "
        + rows["Campaign Opportunity Share"].map(lambda value: f"{value:,.1f}%")
        + "<br/>Top material: "
        + rows["Top Campaign Material"].fillna("")
        + "<br/>Destination: "
        + rows["Top Campaign Destination"].fillna("")
        + "<br/>Business group: "
        + rows["Business Group"].fillna("")
        + "<br/>"
        + rows["Jurisdiction"].fillna("")
    )
    return rows.sort_values("Campaign Opportunity Tons", ascending=False).reset_index(drop=True)


def usable_phone_mask(values: pd.Series) -> pd.Series:
    """Return rows with a plausibly dialable North American business number."""
    return values.fillna("").astype(str).map(lambda value: len(re.sub(r"\D", "", value)) >= 10)


def usable_email_mask(values: pd.Series) -> pd.Series:
    """Return rows with a simple, export-safe business email address."""
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return values.fillna("").astype(str).str.strip().str.fullmatch(pattern, na=False)


def usable_mailing_mask(values: pd.Series) -> pd.Series:
    missing = {"", "nan", "none", "unknown", "n/a"}
    return ~values.fillna("").astype(str).str.strip().str.casefold().isin(missing)


def outreach_channel_exports(campaign_rows: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Create reviewable, channel-specific contact lists without sending outreach."""
    base_columns = [
        "Business", "Campaign Opportunity Tons", "Top Campaign Material",
        "Top Campaign Destination", "Business Group", "Jurisdiction", "Phone",
        "Email", "Website", "Address", "ZIP Code",
    ]
    rows = campaign_rows[[column for column in base_columns if column in campaign_rows.columns]].copy()
    for column in ["Business", "Phone", "Email", "Address"]:
        if column not in rows.columns:
            rows[column] = ""
        rows[column] = rows[column].fillna("").astype(str).str.strip()
    rows["Campaign Opportunity Tons"] = pd.to_numeric(
        rows.get("Campaign Opportunity Tons", pd.Series(0.0, index=rows.index)), errors="coerce"
    ).fillna(0.0)
    rows["Priority"] = np.arange(1, len(rows) + 1)
    rows["Review Status"] = "Pending planner review"

    phone_book = rows.loc[usable_phone_mask(rows["Phone"])].copy()
    phone_book["Suggested Call Topic"] = (
        "Discuss " + phone_book.get("Top Campaign Material", "selected materials").fillna("selected materials")
        + " diversion options"
    )
    phone_book = phone_book.drop_duplicates(subset=["Phone"], keep="first")

    mailing = rows.loc[usable_mailing_mask(rows["Address"])].copy()
    mailing["Mail To"] = mailing["Business"]
    mailing["Address Line 1"] = mailing["Address"]
    mailing["City State ZIP"] = mailing.apply(
        lambda row: ", ".join(
            part for part in [str(row.get("Jurisdiction", "")).strip(), str(row.get("ZIP Code", "")).strip()]
            if part and part.casefold() not in {"nan", "unknown"}
        ),
        axis=1,
    )
    mailing = mailing.drop_duplicates(subset=["Mail To", "Address Line 1"], keep="first")

    email = rows.loc[usable_email_mask(rows["Email"])].copy()
    email["Subject"] = "Waste diversion assistance for your business"
    email["Email Draft"] = (
        "Hello " + email["Business"] + ",\n\n"
        "Our planning team is offering assistance related to "
        + email.get("Top Campaign Material", "waste diversion").fillna("waste diversion")
        + ". Please reply if you would like to discuss available options.\n\n"
        "To stop receiving these outreach emails, reply with unsubscribe."
    )
    email = email.drop_duplicates(subset=["Email"], keep="first")
    return {"phone": phone_book, "mail": mailing, "email": email}


def campaign_geography_label(
    rows: pd.DataFrame,
    geography_level: str,
    block_lookup: pd.DataFrame | None = None,
) -> pd.DataFrame:
    output = rows.copy()
    output["Campaign Geography"] = "Countywide"
    output["Campaign Geography ID"] = "Countywide"
    if geography_level == "Jurisdiction" and "Jurisdiction" in output.columns:
        output["Campaign Geography"] = output["Jurisdiction"].fillna("Unknown jurisdiction").astype(str)
        output["Campaign Geography ID"] = output["Campaign Geography"]
    elif geography_level == "ZIP code" and "ZIP Code" in output.columns:
        output["Campaign Geography"] = output["ZIP Code"].fillna("Unknown ZIP").replace("", "Unknown ZIP").astype(str)
        output["Campaign Geography ID"] = output["Campaign Geography"]
    elif geography_level == "Census block group" and block_lookup is not None and not block_lookup.empty:
        output = output.merge(block_lookup, on="_business_row_id", how="left")
        output["Campaign Geography ID"] = output["GEOID"].fillna("Unmatched block group").astype(str)
        output["Campaign Geography"] = (
            output["NAMELSAD"].fillna("Unmatched block group").astype(str)
            + np.where(output["GEOID"].notna(), " | " + output["GEOID"].astype(str), "")
        )
    return output


def campaign_area_summary(campaign_rows: pd.DataFrame) -> pd.DataFrame:
    if campaign_rows.empty or "Campaign Geography" not in campaign_rows.columns:
        return pd.DataFrame()
    return (
        campaign_rows.groupby("Campaign Geography", dropna=False)
        .agg(
            **{
                "Campaign Opportunity Tons": ("Campaign Opportunity Tons", "sum"),
                "Businesses": ("_business_row_id", "nunique"),
                "Top Material": ("Top Campaign Material", most_common_text),
                "Top Business Group": ("Business Group", most_common_text),
                "Top Destination": ("Top Campaign Destination", most_common_text),
            }
        )
        .reset_index()
        .sort_values("Campaign Opportunity Tons", ascending=False)
    )


def build_campaign_map(
    campaign_rows: pd.DataFrame,
    boundary_layers: list[pdk.Layer] | None = None,
) -> pdk.Deck:
    boundary_layers = boundary_layers or []
    center_lat = float((campaign_rows["latitude"].min() + campaign_rows["latitude"].max()) / 2)
    center_lon = float((campaign_rows["longitude"].min() + campaign_rows["longitude"].max()) / 2)
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_from_bounds(campaign_rows),
        pitch=0,
        bearing=0,
    )
    point_layer = pdk.Layer(
        "ScatterplotLayer",
        id="campaign-target-points",
        data=campaign_rows,
        get_position="[longitude, latitude]",
        get_radius="point_radius",
        radius_min_pixels=4,
        radius_max_pixels=18,
        get_fill_color="[color_r, color_g, color_b, color_a]",
        get_line_color="[255, 255, 255, 180]",
        line_width_min_pixels=0.7,
        pickable=True,
        auto_highlight=True,
    )
    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=boundary_layers + [point_layer],
        tooltip={
            "html": "<b>{tooltip_title}</b><br/>{tooltip_body}",
            "style": {
                "backgroundColor": "rgba(34, 42, 38, 0.94)",
                "color": "white",
                "fontFamily": "Arial",
                "fontSize": "12px",
            },
        },
    )


def marketplace_material_key_lookup(material_columns: dict[str, dict[str, str]]) -> dict[str, str]:
    return {format_material_name(material): material for material in sorted(material_columns)}


def marketplace_material_group_keywords(material_key: str) -> list[str]:
    return MARKETPLACE_USER_KEYWORDS.get(material_group(material_key), MARKETPLACE_USER_KEYWORDS["Other"])


def marketplace_base_business_frame(
    filtered: pd.DataFrame,
    latitude_column: str,
    longitude_column: str,
    business_column: str | None,
    business_group_field: str,
    jurisdiction_field: str,
    zip_column: str | None,
    area_series: pd.Series,
) -> pd.DataFrame:
    business_source = source_column(filtered, business_column, "business_name")
    group_source = source_column(filtered, business_group_field, "business_group")
    jurisdiction_source = source_column(filtered, jurisdiction_field, "jurisdiction")
    industry_columns = industry_description_columns(filtered)
    rows = pd.DataFrame(index=filtered.index)
    rows["_business_row_id"] = filtered["_business_row_id"] if "_business_row_id" in filtered.columns else filtered.index
    rows["Business"] = (
        filtered[business_source].fillna("Unnamed business").astype(str).str.strip()
        if business_source
        else "Unnamed business"
    )
    rows["Business"] = rows["Business"].replace("", "Unnamed business")
    rows["Business Group"] = (
        filtered[group_source].fillna("Unknown business group").astype(str).str.strip()
        if group_source
        else "Unknown business group"
    )
    rows["Jurisdiction"] = (
        filtered[jurisdiction_source].fillna("Unknown jurisdiction").astype(str).str.strip()
        if jurisdiction_source
        else "Unknown jurisdiction"
    )
    rows["ZIP Code"] = (
        filtered[zip_column].map(clean_zipcode_value)
        if zip_column and zip_column in filtered.columns
        else ""
    )
    rows["Marketplace Area"] = area_series.reindex(filtered.index).fillna("Unknown area").astype(str)
    rows["latitude"] = pd.to_numeric(filtered[latitude_column], errors="coerce")
    rows["longitude"] = pd.to_numeric(filtered[longitude_column], errors="coerce")
    contact_columns: dict[str, pd.Series] = {}
    add_business_contact_fields(contact_columns, filtered)
    for label in ["Hauler", "Phone", "Website"]:
        rows[label] = contact_columns.get(label, pd.Series("", index=filtered.index)).reindex(filtered.index).fillna("").astype(str)

    text_parts = [rows["Business"], rows["Business Group"], rows["Jurisdiction"]]
    for column in industry_columns:
        text_parts.append(filtered[column].fillna("").astype(str))
    rows["Industry Evidence"] = (
        pd.concat(text_parts, axis=1)
        .fillna("")
        .astype(str)
        .agg(" | ".join, axis=1)
    )
    rows["_match_text"] = rows["Industry Evidence"].str.lower()
    rows = rows[valid_coordinate_mask(rows)].copy()
    return rows


def build_marketplace_supplier_rows(
    filtered: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
    selected_material_keys: list[str],
    area_series: pd.Series,
    business_column: str | None,
    business_group_field: str,
    jurisdiction_field: str,
    min_supplier_tons: float,
) -> pd.DataFrame:
    supplier_rows = build_business_material_exchange_rows(
        filtered,
        material_columns,
        selected_material_keys,
        area_series,
        business_column,
        business_group_field,
        jurisdiction_field,
        min_supplier_tons,
    )
    if supplier_rows.empty:
        return supplier_rows
    supplier_rows = supplier_rows.rename(columns={"Disposed Tons": "Supplier Tons"})
    supplier_rows["Marketplace Area"] = supplier_rows["Exchange Area"]
    return supplier_rows.sort_values("Supplier Tons", ascending=False)


def build_marketplace_user_rows(
    base_businesses: pd.DataFrame,
    selected_material_keys: list[str],
    selected_user_groups: list[str],
) -> pd.DataFrame:
    if base_businesses.empty:
        return pd.DataFrame()
    rows = []
    selected_user_groups = selected_user_groups or []
    user_source = base_businesses.copy()
    if selected_user_groups:
        user_source = user_source[user_source["Business Group"].astype(str).isin(selected_user_groups)].copy()

    for material_key in selected_material_keys:
        keywords = marketplace_material_group_keywords(material_key)
        material_label = format_material_name(material_key)
        group_label = material_group(material_key)
        keyword_pattern = "|".join(re.escape(keyword) for keyword in keywords)
        matched = user_source[user_source["_match_text"].str.contains(keyword_pattern, na=False)].copy()
        if matched.empty:
            continue
        matched["Material"] = material_label
        matched["Material Group"] = group_label
        matched["Potential User Evidence"] = ", ".join(keywords[:6])
        matched["User Match Score"] = 1.0 + matched["_match_text"].map(
            lambda text, keywords=keywords: sum(1 for keyword in keywords if keyword in text)
        )
        rows.append(matched)
    if not rows:
        return pd.DataFrame()
    users = pd.concat(rows, ignore_index=True)
    return users.sort_values(["User Match Score", "Business"], ascending=[False, True])


def marketplace_match_summary(suppliers: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    if suppliers.empty:
        return pd.DataFrame()
    supplier_summary = (
        suppliers.groupby(["Marketplace Area", "Material", "Material Group"], dropna=False)
        .agg(
            **{
                "Supplier Tons": ("Supplier Tons", "sum"),
                "Supplier Businesses": ("_business_row_id", "nunique"),
                "Top Supplier Group": ("Business Group", most_common_text),
                "Example Suppliers": ("Business", lambda values: ", ".join(pd.Series(values).dropna().astype(str).head(3))),
            }
        )
        .reset_index()
    )
    if users.empty:
        supplier_summary["Potential Users"] = 0
        supplier_summary["Top User Group"] = ""
        supplier_summary["Example Users"] = ""
    else:
        user_summary = (
            users.groupby(["Marketplace Area", "Material"], dropna=False)
            .agg(
                **{
                    "Potential Users": ("_business_row_id", "nunique"),
                    "Top User Group": ("Business Group", most_common_text),
                    "Example Users": ("Business", lambda values: ", ".join(pd.Series(values).dropna().astype(str).head(3))),
                }
            )
            .reset_index()
        )
        supplier_summary = supplier_summary.merge(user_summary, on=["Marketplace Area", "Material"], how="left")
        supplier_summary[["Potential Users", "Top User Group", "Example Users"]] = supplier_summary[
            ["Potential Users", "Top User Group", "Example Users"]
        ].fillna({"Potential Users": 0, "Top User Group": "", "Example Users": ""})
    supplier_summary["Potential Users"] = supplier_summary["Potential Users"].astype(int)
    supplier_summary["Marketplace Score"] = (
        supplier_summary["Supplier Tons"]
        * np.log1p(supplier_summary["Supplier Businesses"])
        * np.log1p(supplier_summary["Potential Users"].clip(lower=0))
    )
    supplier_summary["Transparency Note"] = (
        "Suppliers are businesses with modeled landfill disposal of the material; users are inferred from industry keywords."
    )
    return supplier_summary.sort_values("Marketplace Score", ascending=False)


def marketplace_map_frame(suppliers: pd.DataFrame, users: pd.DataFrame, base_businesses: pd.DataFrame) -> pd.DataFrame:
    supplier_rollup = pd.DataFrame()
    if not suppliers.empty:
        supplier_rollup = (
            suppliers.groupby("_business_row_id", dropna=False)
            .agg(
                **{
                    "Supplier Tons": ("Supplier Tons", "sum"),
                    "Supplier Materials": ("Material", lambda values: ", ".join(pd.Series(values).dropna().astype(str).drop_duplicates().head(4))),
                    "Marketplace Area": ("Marketplace Area", most_common_text),
                }
            )
            .reset_index()
        )
    user_rollup = pd.DataFrame()
    if not users.empty:
        user_rollup = (
            users.groupby("_business_row_id", dropna=False)
            .agg(
                **{
                    "User Materials": ("Material", lambda values: ", ".join(pd.Series(values).dropna().astype(str).drop_duplicates().head(4))),
                    "Potential User Evidence": ("Potential User Evidence", most_common_text),
                    "User Match Score": ("User Match Score", "max"),
                    "Marketplace Area": ("Marketplace Area", most_common_text),
                }
            )
            .reset_index()
        )
    ids = set()
    if not supplier_rollup.empty:
        ids.update(supplier_rollup["_business_row_id"].tolist())
    if not user_rollup.empty:
        ids.update(user_rollup["_business_row_id"].tolist())
    if not ids:
        return pd.DataFrame()
    rows = base_businesses[base_businesses["_business_row_id"].isin(ids)].copy()
    if not supplier_rollup.empty:
        rows = rows.merge(supplier_rollup, on="_business_row_id", how="left", suffixes=("", "_supplier"))
    else:
        rows["Supplier Tons"] = 0.0
        rows["Supplier Materials"] = ""
    if not user_rollup.empty:
        rows = rows.merge(user_rollup, on="_business_row_id", how="left", suffixes=("", "_user"))
    else:
        rows["User Materials"] = ""
        rows["Potential User Evidence"] = ""
        rows["User Match Score"] = 0.0
    rows["Supplier Tons"] = pd.to_numeric(rows.get("Supplier Tons", 0.0), errors="coerce").fillna(0.0)
    rows["User Match Score"] = pd.to_numeric(rows.get("User Match Score", 0.0), errors="coerce").fillna(0.0)
    rows["Marketplace Role"] = np.where(
        (rows["Supplier Tons"] > 0) & (rows["User Match Score"] > 0),
        "Supplier + potential user",
        np.where(rows["Supplier Tons"] > 0, "Likely supplier", "Potential user"),
    )
    role_colors = {
        "Likely supplier": [76, 137, 73, 210],
        "Potential user": [35, 105, 154, 205],
        "Supplier + potential user": [123, 88, 159, 220],
    }
    colors = rows["Marketplace Role"].map(role_colors)
    rows["color_r"] = colors.map(lambda color: color[0])
    rows["color_g"] = colors.map(lambda color: color[1])
    rows["color_b"] = colors.map(lambda color: color[2])
    rows["color_a"] = colors.map(lambda color: color[3])
    rows["point_radius"] = np.clip(
        np.sqrt(rows["Supplier Tons"].clip(lower=0)) * 7 + np.where(rows["User Match Score"] > 0, 42, 35),
        35,
        300,
    )
    rows["tooltip_title"] = rows["Business"]
    rows["tooltip_body"] = (
        "Role: "
        + rows["Marketplace Role"].fillna("")
        + "<br/>Supplier tons: "
        + rows["Supplier Tons"].map(lambda value: f"{value:,.1f}")
        + "<br/>Supplier materials: "
        + rows["Supplier Materials"].fillna("")
        + "<br/>Potential user materials: "
        + rows["User Materials"].fillna("")
        + "<br/>Evidence: "
        + rows["Potential User Evidence"].fillna("")
        + "<br/>Business group: "
        + rows["Business Group"].fillna("")
        + "<br/>"
        + rows["Marketplace Area"].fillna("")
    )
    return rows


def build_marketplace_map(marketplace_points: pd.DataFrame) -> pdk.Deck:
    center_lat = float((marketplace_points["latitude"].min() + marketplace_points["latitude"].max()) / 2)
    center_lon = float((marketplace_points["longitude"].min() + marketplace_points["longitude"].max()) / 2)
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_from_bounds(marketplace_points),
        pitch=0,
        bearing=0,
    )
    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            id="marketplace-points",
            data=marketplace_points,
            get_position="[longitude, latitude]",
            get_radius="point_radius",
            radius_min_pixels=4,
            radius_max_pixels=18,
            get_fill_color="[color_r, color_g, color_b, color_a]",
            get_line_color="[255, 255, 255, 180]",
            line_width_min_pixels=0.7,
            pickable=True,
            auto_highlight=True,
        )
    ]
    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=layers,
        tooltip={
            "html": "<b>{tooltip_title}</b><br/>{tooltip_body}",
            "style": {
                "backgroundColor": "rgba(34, 42, 38, 0.94)",
                "color": "white",
                "fontFamily": "Arial",
                "fontSize": "12px",
            },
        },
    )


def selected_opportunity_series(opportunity: pd.DataFrame, selected_destinations: list[str]) -> pd.Series:
    columns = [column for column in selected_destinations if column in opportunity.columns]
    if not columns:
        return pd.Series(0.0, index=opportunity.index)
    return opportunity[columns].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)


def opportunity_share_series(opportunity: pd.DataFrame, selected_tons: pd.Series) -> pd.Series:
    if "Landfill Tons" in opportunity.columns:
        landfill = pd.to_numeric(opportunity["Landfill Tons"], errors="coerce").fillna(0)
    else:
        landfill = pd.Series(0.0, index=opportunity.index)
    return pd.Series(
        np.where(landfill > 0, selected_tons / landfill * 100, 0.0),
        index=opportunity.index,
    )


def opportunity_focus_mask(
    opportunity: pd.DataFrame,
    selected_destinations: list[str],
    min_tons: float,
    min_share: float,
) -> pd.Series:
    if opportunity.empty:
        return pd.Series(False, index=opportunity.index)
    selected_tons = selected_opportunity_series(opportunity, selected_destinations)
    selected_share = opportunity_share_series(opportunity, selected_tons)
    return (selected_tons >= float(min_tons)) & (selected_share >= float(min_share))


def add_selected_opportunity_columns(
    opportunity: pd.DataFrame,
    selected_destinations: list[str],
) -> pd.DataFrame:
    table = opportunity.copy()
    table["Selected Opportunity Tons"] = selected_opportunity_series(table, selected_destinations)
    table["Selected Opportunity Share"] = opportunity_share_series(table, table["Selected Opportunity Tons"])
    return table


def clean_zipcode_value(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    digits = re.sub(r"\D", "", text)
    return digits[:5] if len(digits) >= 5 else text


def build_diversion_opportunity(
    filtered: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
    selected_materials: list[str],
    business_column: str | None,
    jurisdiction_field: str,
    business_group_field: str,
    address_column: str | None,
    zip_column: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_columns = [
        "_business_row_id",
        "Business",
        "Jurisdiction",
        "Business Group",
        "Address",
        "ZIP Code",
        "Hauler",
        "Phone",
        "Email",
        "Website",
        "Landfill Tons",
        "Diversion Opportunity Tons",
        "Opportunity Rate",
        "Curbside Recycle Tons",
        "Curbside Organics Tons",
        "Third-party Diversion Tons",
        "Not Readily Recoverable Tons",
        "Top Material",
        "Preferred Destination",
        "curbside_recycle",
        "curbside_organics",
        "third_party_diversion",
        "not_readily_recoverable",
    ]
    detail_columns = [
        "_business_row_id",
        "Business",
        "Jurisdiction",
        "Business Group",
        "Material",
        "Destination",
        "Destination Key",
        POTENTIAL_TONS_COLUMN,
    ]
    if filtered.empty:
        return pd.DataFrame(columns=summary_columns), pd.DataFrame(columns=detail_columns)

    material_keys = selected_materials or sorted(material_columns)
    business_source = source_column(filtered, business_column, "business_name")
    jurisdiction_source = source_column(filtered, jurisdiction_field, "jurisdiction")
    group_source = source_column(filtered, business_group_field, "business_group")

    summary = pd.DataFrame(index=filtered.index)
    summary["_business_row_id"] = filtered["_business_row_id"] if "_business_row_id" in filtered.columns else filtered.index
    summary["Business"] = (
        filtered[business_source].fillna("Unnamed business").astype(str).str.strip()
        if business_source
        else "Unnamed business"
    )
    summary["Business"] = summary["Business"].replace("", "Unnamed business")
    summary["Jurisdiction"] = (
        filtered[jurisdiction_source].fillna("Unknown jurisdiction").astype(str).str.strip()
        if jurisdiction_source
        else "Unknown jurisdiction"
    )
    summary["Business Group"] = (
        filtered[group_source].fillna("Unknown business group").astype(str).str.strip()
        if group_source
        else "Unknown business group"
    )
    summary["Address"] = (
        filtered[address_column].fillna("").astype(str).str.strip()
        if address_column and address_column in filtered.columns
        else ""
    )
    summary["ZIP Code"] = (
        filtered[zip_column].map(clean_zipcode_value)
        if zip_column and zip_column in filtered.columns
        else ""
    )
    contact_columns: dict[str, pd.Series] = {}
    add_business_contact_fields(contact_columns, filtered)
    for label in ["Hauler", "Phone", "Email", "Website"]:
        values = contact_columns.get(label, pd.Series("", index=filtered.index))
        summary[label] = values.reindex(filtered.index).fillna("").astype(str).str.strip()
    summary["Landfill Tons"] = (
        pd.to_numeric(filtered["calrecycle_disposed_total_tons"], errors="coerce").fillna(0)
        if "calrecycle_disposed_total_tons" in filtered.columns
        else pd.Series(0.0, index=filtered.index)
    )

    for destination in DESTINATION_STREAMS:
        summary[destination] = 0.0

    detail_frames = []
    for material in material_keys:
        disposed_column = material_columns.get(material, {}).get("disposed")
        if not disposed_column or disposed_column not in filtered.columns:
            continue
        tons = pd.to_numeric(filtered[disposed_column], errors="coerce").fillna(0)
        if float(tons.sum()) <= 0:
            continue
        destination = material_destination(material)
        summary[destination] = summary[destination] + tons
        detail_frames.append(
            pd.DataFrame(
                {
                    "_business_row_id": summary["_business_row_id"],
                    "Business": summary["Business"],
                    "Jurisdiction": summary["Jurisdiction"],
                    "Business Group": summary["Business Group"],
                    "Material": format_material_name(material),
                    "Destination": destination_label(destination),
                    "Destination Key": destination,
                    POTENTIAL_TONS_COLUMN: tons,
                }
            )
        )

    material_detail = (
        pd.concat(detail_frames, ignore_index=True)
        if detail_frames
        else pd.DataFrame(columns=detail_columns)
    )
    material_detail = material_detail[material_detail[POTENTIAL_TONS_COLUMN] > 0].copy()

    summary["Curbside Recycle Tons"] = summary["curbside_recycle"]
    summary["Curbside Organics Tons"] = summary["curbside_organics"]
    summary["Third-party Diversion Tons"] = summary["third_party_diversion"]
    summary["Not Readily Recoverable Tons"] = summary["not_readily_recoverable"]
    summary["Diversion Opportunity Tons"] = summary[
        ["curbside_recycle", "curbside_organics", "third_party_diversion"]
    ].sum(axis=1)
    summary["Opportunity Rate"] = np.where(
        summary["Landfill Tons"] > 0,
        summary["Diversion Opportunity Tons"] / summary["Landfill Tons"] * 100,
        0.0,
    )

    if material_detail.empty:
        summary["Top Material"] = ""
        summary["Preferred Destination"] = ""
    else:
        ranked_detail = material_detail.sort_values(POTENTIAL_TONS_COLUMN, ascending=False)
        top_materials = ranked_detail.drop_duplicates("_business_row_id").set_index("_business_row_id")
        summary["Top Material"] = summary["_business_row_id"].map(top_materials["Material"]).fillna("")
        summary["Preferred Destination"] = summary["_business_row_id"].map(top_materials["Destination"]).fillna("")

    return summary[summary_columns].sort_values("Diversion Opportunity Tons", ascending=False), material_detail


def apply_study_pathway_calibration(
    opportunity: pd.DataFrame,
    material_detail: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    if opportunity.empty:
        return opportunity.copy(), material_detail.copy(), {destination: 1.0 for destination in DESTINATION_STREAMS}

    calibrated = opportunity.copy()
    detail = material_detail.copy()
    total_landfill = float(pd.to_numeric(calibrated["Landfill Tons"], errors="coerce").fillna(0).sum())
    factors: dict[str, float] = {}

    for destination, target_share in STUDY_DESTINATION_SHARES.items():
        if destination not in calibrated.columns:
            factors[destination] = 1.0
            continue
        raw_total = float(pd.to_numeric(calibrated[destination], errors="coerce").fillna(0).sum())
        target_total = total_landfill * target_share / 100
        factors[destination] = target_total / raw_total if raw_total > 0 else 1.0
        calibrated[destination] = calibrated[destination] * factors[destination]

    calibrated["Curbside Recycle Tons"] = calibrated["curbside_recycle"]
    calibrated["Curbside Organics Tons"] = calibrated["curbside_organics"]
    calibrated["Third-party Diversion Tons"] = calibrated["third_party_diversion"]
    calibrated["Not Readily Recoverable Tons"] = calibrated["not_readily_recoverable"]
    calibrated["Diversion Opportunity Tons"] = calibrated[DIVERTIBLE_DESTINATIONS].sum(axis=1)
    calibrated["Opportunity Rate"] = np.where(
        calibrated["Landfill Tons"] > 0,
        calibrated["Diversion Opportunity Tons"] / calibrated["Landfill Tons"] * 100,
        0.0,
    )

    if not detail.empty:
        detail["_calibration_factor"] = detail["Destination Key"].map(factors).fillna(1.0)
        detail[POTENTIAL_TONS_COLUMN] = detail[POTENTIAL_TONS_COLUMN] * detail["_calibration_factor"]
        detail = detail.drop(columns="_calibration_factor")
        ranked_detail = detail.sort_values(POTENTIAL_TONS_COLUMN, ascending=False)
        top_materials = ranked_detail.drop_duplicates("_business_row_id").set_index("_business_row_id")
        calibrated["Top Material"] = calibrated["_business_row_id"].map(top_materials["Material"]).fillna("")
        calibrated["Preferred Destination"] = calibrated["_business_row_id"].map(top_materials["Destination"]).fillna("")

    return calibrated.sort_values("Diversion Opportunity Tons", ascending=False), detail, factors


def apply_opportunity_model_mode(
    opportunity: pd.DataFrame,
    material_detail: pd.DataFrame,
    model_mode: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    if model_mode == STUDY_CALIBRATED_OPPORTUNITY_MODE:
        return apply_study_pathway_calibration(opportunity, material_detail)
    return opportunity.copy(), material_detail.copy(), {destination: 1.0 for destination in DESTINATION_STREAMS}


def opportunity_model_note(model_mode: str) -> str:
    if model_mode == STUDY_CALIBRATED_OPPORTUNITY_MODE:
        return (
            "Calibrated mode adjusts each destination total to the 2025 study pathway shares while keeping the "
            "workbook-based order of businesses within each destination stream."
        )
    return (
        "Raw mode shows the workbook estimates before study scaling."
    )


def diversion_destination_rollup(
    opportunity: pd.DataFrame,
    selected_destinations: list[str],
    min_tons: float,
    min_share: float,
) -> pd.DataFrame:
    rows = []
    for destination in selected_destinations:
        if destination not in opportunity.columns:
            continue
        stream_tons = pd.to_numeric(opportunity[destination], errors="coerce").fillna(0)
        stream_share = opportunity_share_series(opportunity, stream_tons)
        stream_focus = (stream_tons >= float(min_tons)) & (stream_share >= float(min_share))
        rows.append(
            {
                "Destination": destination_label(destination),
                POTENTIAL_TONS_COLUMN: float(stream_tons.sum()),
                "Thresholded Tons": float(stream_tons[stream_focus].sum()),
                "Businesses Above Threshold": int(stream_focus.sum()),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["Destination", POTENTIAL_TONS_COLUMN, "Thresholded Tons", "Businesses Above Threshold"])
    return pd.DataFrame(rows).sort_values(POTENTIAL_TONS_COLUMN, ascending=False)


def diversion_material_rollup(
    material_detail: pd.DataFrame,
    selected_destinations: list[str],
    focus_business_ids: pd.Series | list[int] | None = None,
) -> pd.DataFrame:
    if material_detail.empty:
        return pd.DataFrame(columns=["Material", "Destination", POTENTIAL_TONS_COLUMN, "Businesses"])
    detail = material_detail[material_detail["Destination Key"].isin(selected_destinations)].copy()
    if focus_business_ids is not None:
        detail = detail[detail["_business_row_id"].isin(focus_business_ids)].copy()
    if detail.empty:
        return pd.DataFrame(columns=["Material", "Destination", POTENTIAL_TONS_COLUMN, "Businesses"])
    return (
        detail.groupby(["Material", "Destination"], dropna=False)
        .agg(
            **{
                POTENTIAL_TONS_COLUMN: (POTENTIAL_TONS_COLUMN, "sum"),
                "Businesses": ("_business_row_id", "nunique"),
            }
        )
        .reset_index()
        .sort_values(POTENTIAL_TONS_COLUMN, ascending=False)
    )


def material_group_composition(
    filtered: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
    stream_key: str = "disposed",
) -> pd.DataFrame:
    rows = []
    for material, stream_columns in material_columns.items():
        column = stream_columns.get(stream_key)
        if not column or column not in filtered.columns:
            continue
        rows.append(
            {
                "Material Group": material_group(material),
                "Material": format_material_name(material),
                "Model Tons": float(pd.to_numeric(filtered[column], errors="coerce").fillna(0).sum()),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["Material Group", "Model Tons", "Model Share"])

    material_frame = pd.DataFrame(rows)
    group_frame = (
        material_frame.groupby("Material Group", dropna=False)["Model Tons"]
        .sum()
        .reset_index()
    )
    for group_name in ICI_MATERIAL_GROUP_SHARES:
        if group_name not in group_frame["Material Group"].values:
            group_frame.loc[len(group_frame)] = {"Material Group": group_name, "Model Tons": 0.0}
    total_tons = float(group_frame["Model Tons"].sum())
    group_frame["Model Share"] = np.where(total_tons > 0, group_frame["Model Tons"] / total_tons * 100, 0.0)
    group_frame["2025 Study Share"] = group_frame["Material Group"].map(ICI_MATERIAL_GROUP_SHARES).fillna(0.0)
    group_frame["Study Tons (Sector Basis)"] = (
        group_frame["2025 Study Share"] / 100 * STUDY_SECTOR_BASIS_ICI_REFUSE_TONS
    )
    group_frame["Study Tons (Table Basis)"] = (
        group_frame["2025 Study Share"] / 100 * STUDY_TABLE_TOTAL_ICI_REFUSE_TONS
    )
    group_frame["Difference (pp)"] = group_frame["Model Share"] - group_frame["2025 Study Share"]
    group_frame["Abs Difference (pp)"] = group_frame["Difference (pp)"].abs()
    group_frame["_order"] = group_frame["Material Group"].map(
        {group_name: index for index, group_name in enumerate(ICI_MATERIAL_GROUP_SHARES)}
    ).fillna(len(ICI_MATERIAL_GROUP_SHARES))
    return group_frame.sort_values("_order").drop(columns="_order").reset_index(drop=True)


def material_group_detail_composition(
    filtered: pd.DataFrame,
    material_columns: dict[str, dict[str, str]],
    stream_key: str = "disposed",
) -> pd.DataFrame:
    rows = []
    for material, stream_columns in material_columns.items():
        column = stream_columns.get(stream_key)
        if not column or column not in filtered.columns:
            continue
        rows.append(
            {
                "Material": format_material_name(material),
                "Material Group": material_group(material),
                "Model Tons": float(pd.to_numeric(filtered[column], errors="coerce").fillna(0).sum()),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["Material", "Material Group", "Model Tons", "Model Share"])
    detail = pd.DataFrame(rows)
    total_tons = float(detail["Model Tons"].sum())
    detail["Model Share"] = np.where(total_tons > 0, detail["Model Tons"] / total_tons * 100, 0.0)
    return detail.sort_values("Model Tons", ascending=False).reset_index(drop=True)


def model_pathway_composition(opportunity: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pathway_map = {
        "curbside_recycle": "Curbside recycle",
        "curbside_organics": "Curbside organics / food recovery",
        "third_party_diversion": "Third-party diversion",
        "not_readily_recoverable": "Not readily recoverable",
    }
    total_landfill = (
        float(pd.to_numeric(opportunity["Landfill Tons"], errors="coerce").fillna(0).sum())
        if "Landfill Tons" in opportunity.columns
        else 0.0
    )
    for destination, label in pathway_map.items():
        tons = (
            float(pd.to_numeric(opportunity[destination], errors="coerce").fillna(0).sum())
            if destination in opportunity.columns
            else 0.0
        )
        rows.append(
            {
                "Pathway": label,
                "Model Tons": tons,
                "Model Share": tons / total_landfill * 100 if total_landfill > 0 else 0.0,
                "2025 Study Share": STUDY_DIVERSION_PATHWAY_SHARES[label],
                "Study Tons (Sector Basis)": STUDY_DIVERSION_PATHWAY_SHARES[label]
                / 100
                * STUDY_SECTOR_BASIS_ICI_REFUSE_TONS,
                "Study Tons (Table Basis)": STUDY_DIVERSION_PATHWAY_SHARES[label]
                / 100
                * STUDY_TABLE_TOTAL_ICI_REFUSE_TONS,
            }
        )
    frame = pd.DataFrame(rows)
    frame["Difference (pp)"] = frame["Model Share"] - frame["2025 Study Share"]
    frame["Abs Difference (pp)"] = frame["Difference (pp)"].abs()
    return frame


def comparison_chart(frame: pd.DataFrame, category_column: str) -> alt.Chart:
    chart_data = frame.melt(
        id_vars=[category_column],
        value_vars=["2025 Study Share", "Model Share"],
        var_name="Source",
        value_name="Share",
    )
    chart_data["Source"] = chart_data["Source"].replace(
        {
            "2025 Study Share": "2025 Study",
            "Model Share": "Current model",
        }
    )
    return (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(f"{category_column}:N", sort=None, title=None),
            y=alt.Y("Share:Q", title="Share of landfill tons (%)"),
            color=alt.Color(
                "Source:N",
                scale=alt.Scale(
                    domain=["2025 Study", "Current model"],
                    range=[
                        IWMA_STUDY_MODEL_COLORS["2025 Study"],
                        IWMA_STUDY_MODEL_COLORS["Current model"],
                    ],
                ),
                title=None,
            ),
            tooltip=[
                alt.Tooltip(f"{category_column}:N", title=category_column),
                alt.Tooltip("Source:N"),
                alt.Tooltip("Share:Q", format=".1f", title="Share (%)"),
            ],
            xOffset="Source:N",
        )
        .properties(height=360)
    )


def waste_stream_totals(filtered: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for stream_config in STREAM_COLUMNS.values():
        column = stream_config["total"]
        rows.append(
            {
                "Waste Stream": stream_config["label"],
                "Tons": (
                    float(pd.to_numeric(filtered[column], errors="coerce").fillna(0).sum())
                    if column in filtered.columns
                    else 0.0
                ),
            }
        )
    total = sum(row["Tons"] for row in rows)
    for row in rows:
        row["Share"] = row["Tons"] / total * 100 if total > 0 else 0.0
    return pd.DataFrame(rows)


def business_group_opportunity_rollup(
    opportunity: pd.DataFrame,
    selected_destinations: list[str],
) -> pd.DataFrame:
    if opportunity.empty:
        return pd.DataFrame(columns=["Business Group", POTENTIAL_TONS_COLUMN, "Businesses"])
    table = add_selected_opportunity_columns(opportunity, selected_destinations)
    return (
        table.groupby("Business Group", dropna=False)
        .agg(
            **{
                POTENTIAL_TONS_COLUMN: ("Selected Opportunity Tons", "sum"),
                "Businesses": ("_business_row_id", "nunique"),
            }
        )
        .reset_index()
        .sort_values(POTENTIAL_TONS_COLUMN, ascending=False)
    )


def prepare_diversion_map_frame(
    opportunity: pd.DataFrame,
    filtered: pd.DataFrame,
    latitude_column: str,
    longitude_column: str,
    selected_destinations: list[str],
    show_zero_opportunity: bool,
    min_tons: float = 0.0,
    min_share: float = 0.0,
) -> pd.DataFrame:
    if opportunity.empty or filtered.empty:
        return pd.DataFrame(
            columns=[
                "latitude",
                "longitude",
                "Selected Opportunity Tons",
                "Diversion Opportunity Tons",
                "tooltip_title",
                "tooltip_body",
            ]
        )

    coords = filtered[["_business_row_id", latitude_column, longitude_column]].rename(
        columns={latitude_column: "latitude", longitude_column: "longitude"}
    )
    map_df = opportunity.merge(coords, on="_business_row_id", how="left")
    map_df["latitude"] = pd.to_numeric(map_df["latitude"], errors="coerce")
    map_df["longitude"] = pd.to_numeric(map_df["longitude"], errors="coerce")
    map_df = map_df[valid_coordinate_mask(map_df)].copy()
    map_df = add_selected_opportunity_columns(map_df, selected_destinations)
    if not show_zero_opportunity:
        map_df = map_df[
            (map_df["Selected Opportunity Tons"] >= float(min_tons))
            & (map_df["Selected Opportunity Share"] >= float(min_share))
        ].copy()
    destination_totals = (
        map_df[selected_destinations].copy()
        if selected_destinations
        else pd.DataFrame(index=map_df.index)
    )
    map_df["Dominant Destination Key"] = (
        destination_totals.idxmax(axis=1) if not destination_totals.empty else "not_readily_recoverable"
    )
    colors = map_df["Dominant Destination Key"].map(
        lambda key: DESTINATION_STREAMS.get(key, DESTINATION_STREAMS["not_readily_recoverable"])["color"]
    )
    map_df["color_r"] = colors.map(lambda color: color[0])
    map_df["color_g"] = colors.map(lambda color: color[1])
    map_df["color_b"] = colors.map(lambda color: color[2])
    map_df["color_a"] = colors.map(lambda color: color[3])
    map_df["point_radius"] = np.clip(np.sqrt(map_df["Selected Opportunity Tons"].clip(lower=0)) * 8 + 35, 35, 320)
    map_df["tooltip_title"] = map_df["Business"]
    map_df["tooltip_body"] = (
        "Opportunity: "
        + map_df["Selected Opportunity Tons"].map(lambda value: f"{value:,.1f}")
        + " tons<br/>Landfill: "
        + map_df["Landfill Tons"].map(lambda value: f"{value:,.1f}")
        + " tons<br/>Opportunity share: "
        + map_df["Selected Opportunity Share"].map(lambda value: f"{value:,.1f}%")
        + "<br/>Top material: "
        + map_df["Top Material"].fillna("")
        + "<br/>Preferred: "
        + map_df["Preferred Destination"].fillna("")
        + "<br/>"
        + map_df["Jurisdiction"].fillna("")
    )
    return map_df


def boundary_layer(boundaries, layer_id: str, line_color: list[int], fill_color: list[int]) -> pdk.Layer:
    boundaries = boundaries.copy()
    if "boundary_name" not in boundaries.columns:
        if "NAMELSAD" in boundaries.columns:
            boundaries["boundary_name"] = boundaries["NAMELSAD"].astype(str)
        elif "GEOID" in boundaries.columns:
            boundaries["boundary_name"] = boundaries["GEOID"].astype(str)
        else:
            boundaries["boundary_name"] = "Boundary"
    if "boundary_type" not in boundaries.columns:
        boundaries["boundary_type"] = "Boundary"
    boundaries["tooltip_title"] = boundaries["boundary_name"].astype(str)
    boundaries["tooltip_body"] = boundaries["boundary_type"].astype(str)
    boundary_columns = [
        column
        for column in ["GEOID", "NAMELSAD", "boundary_name", "boundary_type", "tooltip_title", "tooltip_body", "geometry"]
        if column in boundaries.columns
    ]
    geojson = json.loads(boundaries[boundary_columns].to_json())
    return pdk.Layer(
        "GeoJsonLayer",
        id=layer_id,
        data=geojson,
        stroked=True,
        filled=True,
        pickable=True,
        auto_highlight=False,
        get_fill_color=fill_color,
        get_line_color=line_color,
        get_line_width=2,
        line_width_min_pixels=1,
        line_width_max_pixels=3,
    )


def build_diversion_opportunity_map(
    map_df: pd.DataFrame,
    boundary_layers: list[pdk.Layer],
) -> pdk.Deck:
    center_lat = float((map_df["latitude"].min() + map_df["latitude"].max()) / 2)
    center_lon = float((map_df["longitude"].min() + map_df["longitude"].max()) / 2)
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_from_bounds(map_df),
        pitch=0,
        bearing=0,
    )
    point_layer = pdk.Layer(
        "ScatterplotLayer",
        id="diversion-opportunity-points",
        data=map_df,
        get_position="[longitude, latitude]",
        get_radius="point_radius",
        radius_min_pixels=4,
        radius_max_pixels=18,
        get_fill_color="[color_r, color_g, color_b, color_a]",
        get_line_color="[255, 255, 255, 170]",
        line_width_min_pixels=0.6,
        pickable=True,
        auto_highlight=True,
    )
    return pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=view_state,
        layers=boundary_layers + [point_layer],
        tooltip={
            "html": "<b>{tooltip_title}</b><br/>{tooltip_body}",
            "style": {
                "backgroundColor": "rgba(34, 42, 38, 0.94)",
                "color": "white",
                "fontFamily": "Arial",
                "fontSize": "12px",
            },
        },
    )


def row_numeric_value(row: pd.Series, column: str) -> float:
    if column not in row.index:
        return 0.0
    value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").fillna(0).iloc[0]
    return float(value)


def business_stream_breakdown(row: pd.Series) -> pd.DataFrame:
    rows = []
    for stream_key, stream_config in STREAM_COLUMNS.items():
        tons = row_numeric_value(row, stream_config["total"])
        rows.append(
            {
                "Waste Stream": stream_config["label"],
                "Tons": tons,
            }
        )
    total = row_numeric_value(row, TOTAL_GENERATION_COLUMN)
    if total <= 0:
        total = sum(item["Tons"] for item in rows)
    for item in rows:
        item["Share of Generation"] = (item["Tons"] / total * 100) if total > 0 else 0.0
    return pd.DataFrame(rows).sort_values("Tons", ascending=False)


def business_material_breakdown(
    row: pd.Series,
    material_columns: dict[str, dict[str, str]],
    top_n: int = 15,
) -> pd.DataFrame:
    rows = []
    for material, stream_columns in material_columns.items():
        disposed = row_numeric_value(row, stream_columns.get("disposed", ""))
        recycle = row_numeric_value(row, stream_columns.get("curbside_recycle", ""))
        organics = row_numeric_value(row, stream_columns.get("curbside_organics", ""))
        diversion = row_numeric_value(row, stream_columns.get("other_diversion", ""))
        total = row_numeric_value(row, stream_columns.get("total_generation", ""))
        if total <= 0:
            total = disposed + recycle + organics + diversion
        if total <= 0:
            continue
        rows.append(
            {
                "Material": format_material_name(material),
                "Total Generation": total,
                "Landfill": disposed,
                "Recycle": recycle,
                "Organics": organics,
                "Diversion": diversion,
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=["Material", "Total Generation", "Landfill", "Recycle", "Organics", "Diversion"]
        )
    return pd.DataFrame(rows).sort_values("Total Generation", ascending=False).head(top_n)


def business_detail_panel(
    business_row: pd.Series,
    material_columns: dict[str, dict[str, str]],
    business_column: str | None,
    address_column: str | None,
    jurisdiction_field: str,
    business_group_field: str,
) -> None:
    business_name = str(business_row.get(business_column, "Selected business")) if business_column else "Selected business"
    st.markdown(f"**{business_name}**")

    detail_cols = st.columns(4)
    detail_cols[0].metric("Selected Tons", f"{row_numeric_value(business_row, 'selected_waste_tons'):,.1f}")
    detail_cols[1].metric("Total Generation", f"{row_numeric_value(business_row, TOTAL_GENERATION_COLUMN):,.1f}")
    detail_cols[2].metric("Jurisdiction", str(business_row.get(jurisdiction_field, ""))[:28])
    detail_cols[3].metric("Business Group", str(business_row.get(business_group_field, ""))[:28])

    if address_column and pd.notna(business_row.get(address_column)):
        st.caption(str(business_row.get(address_column)))

    st.markdown(row_stream_fingerprint_html(business_row, compact=False), unsafe_allow_html=True)

    stream_table = business_stream_breakdown(business_row)
    material_table = business_material_breakdown(business_row, material_columns)

    stream_tab, material_tab = st.tabs(["Primary waste streams", "Materials within streams"])
    with stream_tab:
        st.dataframe(
            stream_table,
            width="stretch",
            height=220,
            hide_index=True,
            column_config={
                "Tons": st.column_config.NumberColumn(format="%.2f"),
                "Share of Generation": st.column_config.ProgressColumn(
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
            },
        )
    with material_tab:
        st.dataframe(
            material_table,
            width="stretch",
            height=360,
            hide_index=True,
            column_config={
                "Total Generation": st.column_config.NumberColumn(format="%.2f"),
                "Landfill": st.column_config.NumberColumn(format="%.2f"),
                "Recycle": st.column_config.NumberColumn(format="%.2f"),
                "Organics": st.column_config.NumberColumn(format="%.2f"),
                "Diversion": st.column_config.NumberColumn(format="%.2f"),
            },
        )


st.title("Waste Decision Support Tool")
if DEMO_MODE:
    st.caption("Stakeholder demo: heat map, census block groups, diversion opportunity, and study comparison.")

if "selected_block_group_geoid" not in st.session_state:
    st.session_state.selected_block_group_geoid = None
if "block_group_map_reset_nonce" not in st.session_state:
    st.session_state.block_group_map_reset_nonce = 0

with st.sidebar:
    st.header("View")
    dashboard = st.radio(
        "Dashboard",
        DASHBOARD_OPTIONS,
        index=0,
        horizontal=False,
        key="dashboard_view",
    )

    if dashboard is None:
        st.header("Filters")
        st.info("Choose a dashboard above to load its map and filters.")
        st.stop()

    st.header("Filters")

    with st.expander("Data source", expanded=False):
        source_mode = st.radio(
            "Workbook",
            ["Default path", "Upload workbook", "Local path"],
            horizontal=False,
            label_visibility="collapsed",
        )
        if source_mode == "Upload workbook":
            uploaded_file = st.file_uploader("Workbook file", type=["xlsx", "xls"])
            if uploaded_file is None:
                st.stop()
            data = load_excel_from_bytes(uploaded_file.getvalue())
            source_label = uploaded_file.name
        else:
            if source_mode == "Local path":
                path_text = st.text_input("Workbook path", value=DEFAULT_DATA_PATH)
            else:
                path_text = DEFAULT_DATA_PATH
            data = load_excel_from_path(path_text)
            source_label = Path(path_text).name

    jurisdiction_fields = existing_columns(
        data,
        [
            "SMART1383 Jurisdiction",
            "calrecycle_jurisdiction",
            "calrecycle_profile_jurisdiction",
        ],
    )
    business_group_fields = existing_columns(
        data,
        [
            "Business Group",
            "SMART1383 Business Group",
            "calrecycle_profile_business_group",
        ],
    )

    if not jurisdiction_fields:
        st.error("No jurisdiction field was found in the workbook.")
        st.stop()
    if not business_group_fields:
        st.error("No business group field was found in the workbook.")
        st.stop()

    jurisdiction_field = st.selectbox("Jurisdiction field", jurisdiction_fields)
    selected_jurisdictions = st.multiselect(
        "Jurisdiction",
        option_values(data[jurisdiction_field]),
        default=[],
        help="Leave blank to include every jurisdiction.",
    )

    business_group_field = st.selectbox("Business group field", business_group_fields)
    selected_business_groups = st.multiselect(
        "Business group",
        option_values(data[business_group_field]),
        default=[],
        help="Leave blank to include every business group.",
    )

    industry_fields = industry_description_columns(data)
    industry_filter_field = "Any NAICS/SIC description"
    selected_industries: list[str] = []
    if industry_fields:
        with st.expander("Industry details", expanded=False):
            industry_filter_field = st.selectbox(
                "Industry description field",
                ["Any NAICS/SIC description"] + industry_fields,
                help="Use NAICS/SIC descriptions or line of business for a more granular industry slice.",
            )
            industry_options = (
                combined_option_values(data, industry_fields)
                if industry_filter_field == "Any NAICS/SIC description"
                else option_values(data[industry_filter_field])
            )
            selected_industries = st.multiselect(
                "NAICS/SIC description",
                industry_options,
                default=[],
                help="Leave blank to include every industry description.",
            )

    if dashboard in [
        "Home",
        "Quick start guide",
        "Data infrastructure",
        "Assumptions",
        "Diversion opportunity",
        "Outreach campaign builder",
        "Circular economy marketplace",
        "Circular flow engine",
        "2025 study vs model",
    ]:
        selected_streams = ["disposed"] if dashboard == "Circular flow engine" else STREAM_KEYS
        if dashboard == "Diversion opportunity":
            st.caption("Diversion opportunity uses landfill-disposed material estimates.")
        if dashboard == "Outreach campaign builder":
            st.caption("Campaign builder uses landfill-disposed material estimates and its own material selector.")
        if dashboard == "Circular economy marketplace":
            st.caption("Marketplace prototype uses landfill-disposed material estimates and inferred user demand.")
        if dashboard == "Circular flow engine":
            st.caption("Circular flow uses landfill-disposed tons for hauling and exchange screening.")
        if dashboard == "Data infrastructure":
            st.caption("This dashboard documents the source systems and transformations behind the DSS.")
        if dashboard == "Quick start guide":
            st.caption("New here? Use this page to choose a planning question and learn how to read the model outputs.")
        if dashboard == "Assumptions":
            st.caption("This dashboard is the living register of model assumptions, transformations, and validation needs.")
    else:
        selected_streams = st.multiselect(
            "Waste stream type",
            STREAM_KEYS,
            default=STREAM_KEYS,
            format_func=lambda key: STREAM_COLUMNS[key]["label"],
        )
        if not selected_streams:
            selected_streams = STREAM_KEYS

    material_columns = discover_material_columns(data.columns)
    material_keys = sorted(material_columns, key=lambda key: format_material_name(key).casefold())
    selected_materials: list[str] = []
    material_mode = "With stream filter"
    if dashboard in [
        "Home",
        "Data infrastructure",
        "Outreach campaign builder",
        "Circular economy marketplace",
        "2025 study vs model",
    ]:
        st.caption("This dashboard uses all material categories for summary calculations.")
    else:
        material_scope = st.radio(
            "Material type",
            ["All materials", "Specific materials"],
            horizontal=True,
        )
    if dashboard not in [
        "Home",
        "Data infrastructure",
        "Outreach campaign builder",
        "Circular economy marketplace",
        "2025 study vs model",
    ] and material_scope == "Specific materials":
        selected_materials = st.multiselect(
            "Materials",
            material_keys,
            format_func=format_material_name,
        )
        if dashboard == "Circular flow engine":
            material_mode = "With stream filter"
            st.caption("Material slices on this dashboard use landfill-disposed tons.")
        else:
            material_mode = st.radio(
                "Material metric",
                ["With stream filter", "Material totals"],
                horizontal=True,
            )
        if not selected_materials:
            st.info("Choose one or more materials.")
            st.stop()

    if dashboard == "Business heat map":
        st.divider()
        heat_map_metric = st.radio(
            "Heat comparison",
            HEATMAP_METRICS,
            index=0,
            help=(
                "Total tons shows volume hot spots. Tons per business highlights high-intensity businesses. "
                "Businesses per sq mi highlights business density regardless of tonnage."
            ),
        )
        weight_scale = st.selectbox("Heat weight scale", ["Linear", "Square root", "Log"], index=1)
        radius_pixels = st.slider("Heat radius", min_value=20, max_value=140, value=70, step=5)
        intensity = st.slider("Heat intensity", min_value=0.2, max_value=4.0, value=1.4, step=0.1)
        threshold = st.slider("Heat threshold", min_value=0.00, max_value=0.25, value=0.03, step=0.01)
    else:
        heat_map_metric = HEATMAP_VOLUME_METRIC
        weight_scale = "Square root"
        radius_pixels = 70
        intensity = 1.4
        threshold = 0.03

    opportunity_model_mode = RAW_OPPORTUNITY_MODE
    if dashboard == "Home":
        st.divider()
        st.header("Model")
        opportunity_model_mode = st.radio(
            "Opportunity model",
            [RAW_OPPORTUNITY_MODE, STUDY_CALIBRATED_OPPORTUNITY_MODE],
            horizontal=False,
            help="Calibrated mode adjusts stream totals to match the 2025 study shares.",
        )

    block_group_controls = {}
    if dashboard == "Census block groups":
        st.divider()
        st.header("Block Groups")
        boundary_source = st.radio(
            "Boundary source",
            ["Auto-download Census 2023 CA", "Local ZIP or shapefile path"],
            horizontal=False,
        )
        county_fips = st.text_input("County FIPS", value=DEFAULT_COUNTY_FIPS, max_chars=3)
        simplify_tolerance = st.select_slider(
            "Boundary detail",
            options=[0.0, 0.0001, 0.0003, 0.0006, 0.001],
            value=0.0006,
            format_func=lambda value: "Full" if value == 0 else f"{value:g}",
        )
        block_metric_name = st.selectbox(
            "Color and rank by",
            list(BLOCK_GROUP_METRICS),
            index=0,
        )
        show_business_points = st.checkbox("Show business points", value=True)
        include_empty_block_groups = st.checkbox("Include empty block groups", value=False)
        top_n_block_groups = st.slider("Ranked rows", min_value=5, max_value=50, value=15, step=5)

        if boundary_source == "Local ZIP or shapefile path":
            default_path = str(default_census_zip_path(DEFAULT_TIGER_YEAR, DEFAULT_STATE_FIPS))
            boundary_path = st.text_input("Boundary file path", value=default_path)
        else:
            boundary_path = ""

        block_group_controls = {
            "boundary_source": boundary_source,
            "county_fips": county_fips,
            "simplify_tolerance": simplify_tolerance,
            "block_metric_name": block_metric_name,
            "show_business_points": show_business_points,
            "include_empty_block_groups": include_empty_block_groups,
            "top_n_block_groups": top_n_block_groups,
            "boundary_path": boundary_path,
        }

    diversion_controls = {}
    if dashboard == "Diversion opportunity":
        st.divider()
        st.header("Opportunity")
        opportunity_model_mode = st.radio(
            "Opportunity model",
            [RAW_OPPORTUNITY_MODE, STUDY_CALIBRATED_OPPORTUNITY_MODE],
            horizontal=False,
            help="Calibrated mode adjusts stream totals to match the 2025 study shares.",
        )
        selected_destinations = st.multiselect(
            "Preferred destination",
            DIVERTIBLE_DESTINATIONS,
            default=DIVERTIBLE_DESTINATIONS,
            format_func=destination_label,
        )
        if not selected_destinations:
            selected_destinations = DIVERTIBLE_DESTINATIONS
        boundary_layers = st.multiselect(
            "Boundary overlays",
            ["Census block groups", "ZIP / ZCTA", "Jurisdiction/community"],
            default=[],
            help=(
                "ZIP / ZCTA uses the Census 2020 cartographic ZCTA layer; "
                "jurisdiction/community uses Census places and CDPs as a first-pass proxy."
            ),
        )
        show_zero_opportunity = st.checkbox("Show zero-opportunity businesses", value=False)
        min_opportunity_tons = st.slider(
            "Minimum opportunity tons",
            min_value=0.0,
            max_value=50.0,
            value=DEFAULT_OPPORTUNITY_TON_THRESHOLD,
            step=0.5,
            help="Used to count and show practical outreach targets, instead of any tiny modeled positive amount.",
        )
        min_opportunity_share = st.slider(
            "Minimum share of landfill",
            min_value=0.0,
            max_value=50.0,
            value=DEFAULT_OPPORTUNITY_SHARE_THRESHOLD,
            step=0.5,
            format="%.1f%%",
            help="A business must meet this selected-opportunity share to be counted as above threshold.",
        )
        diversion_boundary_detail = st.select_slider(
            "Boundary detail",
            options=[0.0, 0.0001, 0.0003, 0.0006, 0.001],
            value=0.0006,
            format_func=lambda value: "Full" if value == 0 else f"{value:g}",
        )
        top_n_opportunity = st.slider("Ranked rows", min_value=10, max_value=100, value=25, step=5)
        st.divider()
        st.header("Garbage transport")
        st.caption(
            "Known haulers are assigned to their reported landfill: Waste Connections → Cold Canyon; "
            "WM → Chicago Grade; Paso Robles Waste and San Miguel Garbage → Paso Robles Landfill."
        )
        transport_road_multiplier = st.slider(
            "Transport road-mile multiplier",
            min_value=1.0,
            max_value=1.8,
            value=DEFAULT_ROAD_DISTANCE_MULTIPLIER,
            step=0.05,
            help="Converts straight-line distance to a planning estimate of one-way road miles.",
        )
        transport_operations_multiplier = st.slider(
            "Transport route adjustment",
            min_value=1.0,
            max_value=2.0,
            value=DEFAULT_ROUTE_OPERATIONS_MULTIPLIER,
            step=0.05,
            help="Adds collection circulation, staging, and return movement to the one-way landfill distance.",
        )
        transport_truckload_tons = st.number_input(
            "Transport average collection load (tons)",
            min_value=0.5,
            max_value=30.0,
            value=DEFAULT_COLLECTION_TRUCKLOAD_TONS,
            step=0.5,
            format="%.1f",
            help="Annual garbage tons are divided by this shared truck load to allocate vehicle miles and emissions.",
        )
        transport_kg_co2e_per_vehicle_mile = st.number_input(
            "Transport kg CO2e per vehicle-mile",
            min_value=0.1,
            max_value=10.0,
            value=DEFAULT_TRUCK_KG_CO2E_PER_VEHICLE_MILE,
            step=0.05,
            format="%.3f",
        )
        diversion_controls = {
            "selected_destinations": selected_destinations,
            "opportunity_model_mode": opportunity_model_mode,
            "boundary_layers": boundary_layers,
            "show_zero_opportunity": show_zero_opportunity,
            "min_opportunity_tons": min_opportunity_tons,
            "min_opportunity_share": min_opportunity_share,
            "boundary_detail": diversion_boundary_detail,
            "top_n_opportunity": top_n_opportunity,
            "transport_road_multiplier": transport_road_multiplier,
            "transport_operations_multiplier": transport_operations_multiplier,
            "transport_truckload_tons": transport_truckload_tons,
            "transport_kg_co2e_per_vehicle_mile": transport_kg_co2e_per_vehicle_mile,
        }

    campaign_controls = {}
    if dashboard == "Outreach campaign builder":
        st.divider()
        st.header("Campaign")
        campaign_model_mode = st.radio(
            "Opportunity model",
            [RAW_OPPORTUNITY_MODE, STUDY_CALIBRATED_OPPORTUNITY_MODE],
            horizontal=False,
            help="Calibrated mode adjusts stream totals to match the 2025 study shares.",
        )
        campaign_materials = st.multiselect(
            "Campaign materials",
            [format_material_name(material) for material in material_keys],
            default=[],
            help="Leave blank to include every landfill material with a mapped pathway.",
        )
        campaign_destinations = st.multiselect(
            "Destination pathways",
            DIVERTIBLE_DESTINATIONS,
            default=DIVERTIBLE_DESTINATIONS,
            format_func=destination_label,
        )
        if not campaign_destinations:
            campaign_destinations = DIVERTIBLE_DESTINATIONS
        campaign_business_groups = st.multiselect(
            "Campaign business group",
            option_values(data[business_group_field]),
            default=[],
            help="Optional campaign-specific business group filter.",
        )
        campaign_geography = st.selectbox(
            "Campaign geography",
            ["Countywide", "Jurisdiction", "ZIP code", "Census block group"],
            index=1,
        )
        campaign_min_tons = st.slider(
            "Minimum campaign tons",
            min_value=0.0,
            max_value=50.0,
            value=1.0,
            step=0.5,
        )
        campaign_top_n = st.slider("Ranked businesses", min_value=10, max_value=250, value=50, step=10)
        campaign_controls = {
            "opportunity_model_mode": campaign_model_mode,
            "materials": campaign_materials,
            "destinations": campaign_destinations,
            "business_groups": campaign_business_groups,
            "geography": campaign_geography,
            "min_tons": campaign_min_tons,
            "top_n": campaign_top_n,
        }

    marketplace_controls = {}
    if dashboard == "Circular economy marketplace":
        st.divider()
        st.header("Marketplace")
        material_label_lookup = marketplace_material_key_lookup(material_columns)
        marketplace_material_labels = st.multiselect(
            "Marketplace materials",
            list(material_label_lookup),
            default=[],
            help="Leave blank to include every landfill material. Selecting one or a few materials makes the prototype easier to inspect.",
        )
        marketplace_geography = st.selectbox(
            "Marketplace geography",
            ["Jurisdiction", "ZIP code", "Census block group", "Countywide"],
            index=0,
        )
        marketplace_user_groups = st.multiselect(
            "Potential user business group",
            option_values(data[business_group_field]),
            default=[],
            help="Optional. Leave blank to infer potential users from NAICS/SIC and business text.",
        )
        marketplace_min_supplier_tons = st.slider(
            "Minimum supplier tons",
            min_value=0.0,
            max_value=50.0,
            value=1.0,
            step=0.5,
        )
        marketplace_top_n = st.slider("Marketplace rows", min_value=10, max_value=150, value=40, step=10)
        marketplace_controls = {
            "material_lookup": material_label_lookup,
            "material_labels": marketplace_material_labels,
            "geography": marketplace_geography,
            "user_groups": marketplace_user_groups,
            "min_supplier_tons": marketplace_min_supplier_tons,
            "top_n": marketplace_top_n,
        }

    circular_controls = {}
    if dashboard == "Circular flow engine":
        st.divider()
        st.header("Circular Flow")
        allocation_mode = st.selectbox(
            "Landfill allocation",
            [
                HAULER_FACILITY_ALLOCATION_MODE,
                "Distance + wasteshed share",
                "Nearest landfill",
                "Wasteshed share only",
            ],
            index=0,
            help=(
                "Hauler facility rules use the current IWMA operating assumption: Waste Connections to Cold Canyon, "
                "Waste Management to Chicago Grade, and Paso Robles Waste / San Miguel Garbage to Paso Robles. "
                "Unknown haulers fall back to Distance + wasteshed share."
            ),
        )
        road_packages_ready = road_network_packages_available()
        tiger_packages_ready = tiger_road_packages_available()
        distance_options = (
            [ROAD_DISTANCE_TIGER_MODE, ROAD_DISTANCE_OSM_MODE, ROAD_DISTANCE_ESTIMATE_MODE]
            if tiger_packages_ready
            else [ROAD_DISTANCE_ESTIMATE_MODE]
        )
        distance_model = st.selectbox(
            "Distance model",
            distance_options,
            index=0,
            help="Census TIGER is the faster road-network option. OpenStreetMap is more detailed but depends on Overpass or a local GraphML file.",
        )
        if not tiger_packages_ready:
            st.caption("Road-network mode is available after installing the road-distance packages in requirements.txt.")
        elif distance_model == ROAD_DISTANCE_TIGER_MODE:
            st.caption("Census TIGER mode uses official county road lines and avoids Overpass downloads.")
        if distance_model == ROAD_DISTANCE_OSM_MODE and not road_packages_ready:
            st.caption("OpenStreetMap mode also needs osmnx. Install requirements.txt or use Census TIGER.")
        local_graph_path = ""
        if distance_model == ROAD_DISTANCE_OSM_MODE:
            with st.expander("Road network source", expanded=False):
                st.caption(
                    "Leave this blank to use the cached default graph or download from Overpass. "
                    "If Overpass is timing out, provide a local .graphml file here."
                )
                local_graph_path = st.text_input(
                    "Local GraphML path",
                    value="",
                    placeholder=str(road_graph_cache_path()),
                )
        road_multiplier = st.slider(
            "Fallback road multiplier",
            min_value=1.0,
            max_value=1.8,
            value=DEFAULT_ROAD_DISTANCE_MULTIPLIER,
            step=0.05,
            help="Used only for straight-line mode or when a road-network distance is unavailable.",
        )
        operations_multiplier = st.slider(
            "Collection route adjustment",
            min_value=1.0,
            max_value=2.0,
            value=DEFAULT_ROUTE_OPERATIONS_MULTIPLIER,
            step=0.05,
            help=(
                "Planning adjustment for miles not captured by a single one-way path, such as route approach, "
                "collection circulation, staging, and return movement. 1.00 means no added operational mileage."
            ),
        )
        kg_co2e_per_ton_mile = st.number_input(
            "kg CO2e per ton-mile",
            min_value=0.05,
            max_value=1.0,
            value=DEFAULT_TRUCK_KG_CO2E_PER_TON_MILE,
            step=0.01,
            format="%.4f",
            help="Kept as a load-based reference factor for annual haul ton-miles.",
        )
        trips_per_year = st.number_input(
            "Collection weeks per year",
            min_value=1,
            max_value=365,
            value=DEFAULT_COLLECTION_TRIPS_PER_YEAR,
            step=1,
            help=(
                "Default assumes weekly service: landfill, recycle, and organics routes operate 52 weeks/year. "
                "Emissions are still allocated by truckload-equivalent tons, not one full truck trip per business."
            ),
        )
        average_truckload_tons = st.number_input(
            "Average collection load tons",
            min_value=0.5,
            max_value=30.0,
            value=DEFAULT_COLLECTION_TRUCKLOAD_TONS,
            step=0.5,
            format="%.1f",
            help=(
                "Average tons carried by a collection truck when allocating shared route emissions. "
                "Default uses EPA's 7 tons per garbage truck assumption; Seattle truck specs suggest larger capacity bounds."
            ),
        )
        diversion_trips_per_business = st.number_input(
            "Diversion trips per business",
            min_value=0,
            max_value=52,
            value=DEFAULT_DIVERSION_TRIPS_PER_BUSINESS,
            step=1,
            help="Documented assumption for future third-party diversion modeling. The current Circular Engine map uses landfill-disposed tons.",
        )
        kg_co2e_per_vehicle_mile = st.number_input(
            "kg CO2e per vehicle-mile",
            min_value=0.1,
            max_value=10.0,
            value=DEFAULT_TRUCK_KG_CO2E_PER_VEHICLE_MILE,
            step=0.05,
            format="%.3f",
            help="Default approximates a diesel refuse truck at about 2.5 mpg using EPA's diesel CO2 factor.",
        )
        route_display_mode = "Fast live map"
        flow_line_limit = 100
        exchange_geography = st.selectbox(
            "Exchange geography",
            ["Census block group", "ZIP code", "Jurisdiction"],
            index=0,
        )
        min_exchange_tons = st.slider(
            "Minimum material tons",
            min_value=0.0,
            max_value=25.0,
            value=1.0,
            step=0.5,
            help="Minimum disposed tons by business/material before it can count as an exchange signal.",
        )
        top_exchange_rows = st.slider("Exchange rows", min_value=10, max_value=100, value=30, step=5)
        with st.expander("Landfill planning shares", expanded=False):
            st.caption(
                "Defaults are based on the 2019 wasteshed shares for the three mapped landfills. "
                "Shares are normalized automatically and should be replaced with IWMA route/facility tonnage when available."
            )
            landfill_shares = {}
            for facility in LANDFILL_FACILITIES:
                landfill_shares[facility["Landfill"]] = st.slider(
                    facility["Landfill"],
                    min_value=0,
                    max_value=100,
                    value=int(round(float(facility["default_share"]) * 100)),
                    step=5,
                )
        circular_controls = {
            "allocation_mode": allocation_mode,
            "distance_model": distance_model,
            "local_graph_path": local_graph_path,
            "road_multiplier": road_multiplier,
            "operations_multiplier": operations_multiplier,
            "kg_co2e_per_ton_mile": kg_co2e_per_ton_mile,
            "trips_per_year": trips_per_year,
            "average_truckload_tons": average_truckload_tons,
            "diversion_trips_per_business": diversion_trips_per_business,
            "kg_co2e_per_vehicle_mile": kg_co2e_per_vehicle_mile,
            "route_display_mode": route_display_mode,
            "flow_line_limit": flow_line_limit,
            "exchange_geography": exchange_geography,
            "min_exchange_tons": min_exchange_tons,
            "top_exchange_rows": top_exchange_rows,
            "landfill_shares": landfill_shares,
        }


filtered = data.copy()
if "_business_row_id" not in filtered.columns:
    filtered.insert(0, "_business_row_id", np.arange(len(filtered), dtype=np.int64))
    data = filtered.copy()
if selected_jurisdictions:
    filtered = filtered[filtered[jurisdiction_field].astype(str).isin(selected_jurisdictions)]
if selected_business_groups:
    filtered = filtered[filtered[business_group_field].astype(str).isin(selected_business_groups)]
if selected_industries:
    filtered = filtered[
        industry_filter_mask(filtered, industry_filter_field, industry_fields, selected_industries)
    ]

metric_values, metric_label, metric_columns = selected_metric(
    filtered,
    material_columns,
    selected_streams,
    selected_materials,
    material_mode,
)
filtered = filtered.assign(selected_waste_tons=metric_values)
umbrella_filtered = umbrella_metrics_frame(filtered, business_group_field)
study_filtered = umbrella_filtered
multifamily_excluded_rows = len(filtered) - len(umbrella_filtered)
study_excluded_rows = multifamily_excluded_rows

latitude_column, longitude_column = coordinate_columns(filtered)
if latitude_column is None or longitude_column is None:
    st.error("Latitude and longitude columns were not found.")
    st.stop()

business_column = business_display_column(filtered)
address_column = address_display_column(filtered)

map_df = prepare_business_map_frame(
    filtered,
    latitude_column,
    longitude_column,
    jurisdiction_field,
    business_group_field,
    business_column,
)
umbrella_map_df = prepare_business_map_frame(
    umbrella_filtered,
    latitude_column,
    longitude_column,
    jurisdiction_field,
    business_group_field,
    business_column,
)

st.caption(f"Source: {source_label}")
loading_overlay = st.empty()
loading_overlay.markdown(
    """
    <div class="dashboard-loading-overlay"></div>
    """,
    unsafe_allow_html=True,
)

if dashboard == "Home":
    zip_column = zipcode_display_column(filtered)
    raw_opportunity, raw_material_detail = build_diversion_opportunity(
        filtered,
        material_columns,
        [],
        business_column,
        jurisdiction_field,
        business_group_field,
        address_column,
        zip_column,
    )
    opportunity, material_detail, calibration_factors = apply_opportunity_model_mode(
        raw_opportunity,
        raw_material_detail,
        opportunity_model_mode,
    )
    home_opportunity = add_selected_opportunity_columns(opportunity, DIVERTIBLE_DESTINATIONS)
    focus_mask = opportunity_focus_mask(
        opportunity,
        DIVERTIBLE_DESTINATIONS,
        DEFAULT_OPPORTUNITY_TON_THRESHOLD,
        DEFAULT_OPPORTUNITY_SHARE_THRESHOLD,
    )
    focused_opportunity = home_opportunity[focus_mask].copy()
    stream_totals = waste_stream_totals(filtered)
    group_composition = material_group_composition(study_filtered, material_columns)
    business_group_rollup = business_group_opportunity_rollup(opportunity, DIVERTIBLE_DESTINATIONS)
    destination_rollup = diversion_destination_rollup(
        opportunity,
        DIVERTIBLE_DESTINATIONS,
        DEFAULT_OPPORTUNITY_TON_THRESHOLD,
        DEFAULT_OPPORTUNITY_SHARE_THRESHOLD,
    )

    total_generation = float(stream_totals["Tons"].sum()) if not stream_totals.empty else 0.0
    landfill_tons = float(opportunity["Landfill Tons"].sum()) if not opportunity.empty else 0.0
    potential_tons = float(home_opportunity["Selected Opportunity Tons"].sum()) if not home_opportunity.empty else 0.0
    organics_tons = float(opportunity["curbside_organics"].sum()) if "curbside_organics" in opportunity.columns else 0.0
    methane_co2e = organics_tons * ORGANICS_CO2E_FACTOR_20_YEAR
    diversion_rate = potential_tons / landfill_tons * 100 if landfill_tons > 0 else 0.0
    alignment_score_value = study_alignment_score(group_composition)
    briefing_insights = home_briefing_insights(
        opportunity,
        destination_rollup,
        material_detail,
        business_group_rollup,
        group_composition,
        focused_opportunity,
        organics_tons,
        methane_co2e,
        alignment_score_value,
    )
    action_queue = home_action_queue(material_detail)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Mapped businesses", f"{len(map_df):,}")
    metric_cols[1].metric("Landfill tons", f"{landfill_tons:,.1f}")
    metric_cols[2].metric("Potential diversion", f"{potential_tons:,.1f}")
    metric_cols[3].metric("20-year organics CO2e", f"{methane_co2e:,.1f}")

    st.info(
        "Home metrics are screening indicators for IWMA planning. Potential diversion is modeled from landfill "
        "material estimates and should be read with the 2025 study comparison before being used for outreach targeting."
    )
    st.caption(opportunity_model_note(opportunity_model_mode))

    st.subheader("Planner Briefing")
    render_briefing_cards(briefing_insights)

    summary_cols = st.columns(5)
    summary_cols[0].metric("Total modeled generation", f"{total_generation:,.1f}")
    summary_cols[1].metric(
        "Potential diversion rate",
        f"{diversion_rate:,.1f}%",
        help=f"2025 study pathway allocation implies {STUDY_DIVERTIBLE_SHARE:.1f}% potentially divertible ICI refuse.",
    )
    summary_cols[2].metric(
        "Outreach targets",
        f"{len(focused_opportunity):,}",
        help=f"Businesses with at least {DEFAULT_OPPORTUNITY_TON_THRESHOLD:g} modeled potential diversion tons.",
    )
    top_group = business_group_rollup.iloc[0]["Business Group"] if not business_group_rollup.empty else "None"
    summary_cols[3].metric("Top opportunity group", str(top_group))
    summary_cols[4].metric(
        "Study alignment score",
        f"{alignment_score_value:.0f}%",
        help="100% minus half the summed absolute material-group share gaps between the model and the 2025 ICI study.",
    )
    st.progress(
        int(round(alignment_score_value)),
        text=f"{alignment_label(alignment_score_value)} against 2025 ICI material-group shares",
    )

    st.subheader("KPI Confidence Labels")
    render_metric_confidence_labels(
        [
            {
                "Metric": "Mapped businesses",
                "Confidence": confidence_label("source"),
                "Kind": "source",
                "Basis": "Direct workbook rows with latitude/longitude.",
            },
            {
                "Metric": "Landfill tons",
                "Confidence": confidence_label("model"),
                "Kind": "model",
                "Basis": "CalRecycle profile scaling applied to business rows.",
            },
            {
                "Metric": "Potential diversion",
                "Confidence": confidence_label("validation"),
                "Kind": "validation",
                "Basis": "Material pathway crosswalk and study-calibrated option.",
            },
            {
                "Metric": "20-year organics CO2e",
                "Confidence": confidence_label("model"),
                "Kind": "model",
                "Basis": "Modeled organics tons with a planning conversion factor.",
            },
            {
                "Metric": "Study alignment",
                "Confidence": confidence_label("validation"),
                "Kind": "validation",
                "Basis": "Diagnostic score after excluding multifamily rows.",
            },
        ]
    )

    st.subheader("Countywide Flow Overview")
    render_countywide_sankey(stream_totals, opportunity)

    st.subheader("Action Queue")
    if action_queue.empty:
        st.warning("No outreach campaign rows are available for the current slice.")
    else:
        st.dataframe(
            action_queue.head(12),
            width="stretch",
            height=330,
            hide_index=True,
            column_config={
                "Expected Tons Impacted": st.column_config.NumberColumn(format="%.1f"),
                "Businesses": st.column_config.NumberColumn(format="%d"),
            },
        )
        st.download_button(
            "Export action queue",
            data=action_queue.to_csv(index=False).encode("utf-8"),
            file_name="home_action_queue.csv",
            mime="text/csv",
        )

    left_chart, right_chart = st.columns(2)
    with left_chart:
        st.subheader("Waste Stream Baseline")
        st.bar_chart(stream_totals, x="Waste Stream", y="Tons", height=320)
    with right_chart:
        st.subheader("Potential Diversion Split")
        st.altair_chart(
            iwma_destination_bar_chart(destination_rollup, "Destination", POTENTIAL_TONS_COLUMN, height=320),
            width="stretch",
        )

    left_table, right_table = st.columns(2)
    with left_table:
        st.subheader("Landfill Material Composition")
        if study_excluded_rows:
            st.caption(
                f"Study comparison excludes {study_excluded_rows:,} multifamily row(s) from the current slice."
            )
        st.dataframe(
            group_composition[
                ["Material Group", "Model Tons", "Model Share", "2025 Study Share", "Difference (pp)"]
            ],
            width="stretch",
            height=330,
            hide_index=True,
            column_config={
                "Model Tons": st.column_config.NumberColumn(format="%.1f"),
                "Model Share": st.column_config.NumberColumn(format="%.1f%%"),
                "2025 Study Share": st.column_config.NumberColumn(format="%.1f%%"),
                "Difference (pp)": st.column_config.NumberColumn(format="%+.1f"),
            },
        )
    with right_table:
        st.subheader("Business Groups by Diversion")
        st.dataframe(
            business_group_rollup.head(12),
            width="stretch",
            height=330,
            hide_index=True,
            column_config={
                POTENTIAL_TONS_COLUMN: st.column_config.NumberColumn(format="%.1f"),
            },
        )

elif dashboard == "Quick start guide":
    render_quick_start_guide()

elif dashboard == "Data infrastructure":
    metrics = infrastructure_summary_metrics(data, filtered, material_columns)
    inventory = infrastructure_source_inventory(data, filtered, material_columns)
    swimlanes = infrastructure_swimlane_table()

    metric_cols = st.columns(4)
    metric_cols[0].metric("SMART1383 source universe", f"~{metrics['source_estimate']:,}")
    metric_cols[1].metric("Integrated DSS rows", f"{metrics['integrated_rows']:,}")
    metric_cols[2].metric("Workbook attributes", f"{metrics['workbook_columns']:,}")
    metric_cols[3].metric("Current filtered slice", f"{metrics['active_rows']:,}")

    st.info(
        "This page documents how the DSS turns source records into planning outputs. "
        "Counts come from the integrated workbook where possible; SMART1383 is shown as an approximate upstream source size."
    )

    st.subheader("Systems Hierarchy")
    render_infrastructure_hierarchy(metrics)

    source_tab, swimlane_tab, quality_tab = st.tabs(["Source inventory", "DSS swimlanes", "Quality flags"])
    with source_tab:
        st.caption("Source scale, connection fields, and what each source contributes to the DSS.")
        st.dataframe(
            inventory,
            width="stretch",
            height=360,
            hide_index=True,
            column_config={
                "Attributes in workbook": st.column_config.NumberColumn(format="%d"),
            },
        )

    with swimlane_tab:
        st.caption("Each swimlane connects source data to the planning task it supports.")
        st.dataframe(
            swimlanes,
            width="stretch",
            height=330,
            hide_index=True,
        )
        st.markdown(
            """
            **Connection logic**
            - SMART1383 supplies the initial business spine and local service context.
            - Mergent enriches that spine with business identity, location, NAICS/SIC, employees, sales, and D-U-N-S fields.
            - CalRecycle profiles assign waste factors by jurisdiction and business group.
            - Suppressed local profiles fall back to countywide same-group profiles so small-area confidentiality does not create missing DSS rows.
            - The scaling tool converts profile factors into per-business tons, which feed maps, rankings, diversion analysis, and circular-flow routing.
            """
        )

    with quality_tab:
        quality_frames = []
        for column, label in [
            ("calrecycle_status", "CalRecycle scaling status"),
            ("calrecycle_profile_strategy", "Profile assignment strategy"),
            ("business_group_mapping_method", "Business group mapping method"),
        ]:
            if column in data.columns:
                frame = (
                    data[column]
                    .fillna("Missing")
                    .astype(str)
                    .value_counts(dropna=False)
                    .reset_index()
                )
                frame.columns = ["Value", "Rows"]
                frame.insert(0, "Quality flag", label)
                quality_frames.append(frame)
        if quality_frames:
            quality_table = pd.concat(quality_frames, ignore_index=True)
            st.dataframe(
                quality_table,
                width="stretch",
                height=420,
                hide_index=True,
                column_config={"Rows": st.column_config.NumberColumn(format="%d")},
            )
        else:
            st.warning("No quality flag columns were found in the workbook.")

elif dashboard == "Assumptions":
    assumption_table = assumptions_register()
    active_assumptions = assumption_table[assumption_table["Status"] == "Active model rule"]
    planning_defaults = assumption_table[assumption_table["Status"] == "Planning default"]
    validation_needed = assumption_table[assumption_table["Status"] == "Validation needed"]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Documented items", f"{len(assumption_table):,}")
    metric_cols[1].metric("Active model rules", f"{len(active_assumptions):,}")
    metric_cols[2].metric("Planning defaults", f"{len(planning_defaults):,}")
    metric_cols[3].metric("Items needing validation", f"{len(validation_needed):,}")

    st.info(
        "This is a living assumptions register for the DSS—not a claim that every item has been independently "
        "verified. It separates implemented rules from planner defaults and the items that need source-data or "
        "field validation before operational use."
    )
    st.caption(
        "The register covers data intake, processing, spatial analysis, waste and diversion modeling, study "
        "calibration, landfill allocation, transport emissions, and the circular-economy prototype."
    )

    selected_stages = st.multiselect(
        "Show stages",
        assumption_table["Stage"].drop_duplicates().tolist(),
        default=assumption_table["Stage"].drop_duplicates().tolist(),
    )
    selected_statuses = st.multiselect(
        "Show statuses",
        assumption_table["Status"].drop_duplicates().tolist(),
        default=assumption_table["Status"].drop_duplicates().tolist(),
    )
    displayed_assumptions = assumption_table[
        assumption_table["Stage"].isin(selected_stages)
        & assumption_table["Status"].isin(selected_statuses)
    ].copy()

    register_tab, coverage_tab, validation_tab, transport_tab = st.tabs(
        ["Full register", "Dashboard coverage", "Validation priorities", "Transport formula"]
    )
    with register_tab:
        st.dataframe(
            displayed_assumptions,
            width="stretch",
            height=650,
            hide_index=True,
            column_config={
                "Implementation": st.column_config.TextColumn(width="large"),
                "Effect / validation need": st.column_config.TextColumn(width="large"),
            },
        )
        st.download_button(
            "Export assumptions register",
            data=displayed_assumptions.to_csv(index=False).encode("utf-8"),
            file_name="waste_dss_assumptions_register.csv",
            mime="text/csv",
        )
    with coverage_tab:
        st.caption(
            "Use this crosswalk to see which assumptions shape each dashboard. Select a dashboard below to open it directly."
        )
        dashboard_coverage = pd.DataFrame(
            [
                ("Home", "Waste estimation; Aggregate reporting", "Countywide screening totals, KPI confidence, and planning briefings."),
                ("Data infrastructure", "Data intake; Classification; Waste estimation; Spatial processing", "Source inventory, transformation swimlanes, and workbook quality flags."),
                ("Business heat map", "Classification; Waste estimation; Spatial processing; Aggregate reporting", "Mapped tonnage intensity and business-density comparisons."),
                ("Census block groups", "Classification; Waste estimation; Spatial processing; Aggregate reporting", "Point-in-polygon geography, block-group rankings, and map boundary assumptions."),
                ("Diversion opportunity", "Waste estimation; Aggregate reporting; Diversion analysis; Study validation; Landfill allocation; Transport emissions", "Business opportunity ranking, material pathways, known hauler landfill assignment, and garbage transport estimates."),
                ("Outreach campaign builder", "Classification; Waste estimation; Diversion analysis", "Campaign lists built from modeled landfill material opportunity."),
                ("Circular economy marketplace", "Classification; Waste estimation; Spatial processing; Circular economy", "Modeled suppliers and inferred potential users; requires validation before matching businesses."),
                ("Circular flow engine", "Waste estimation; Spatial processing; Landfill allocation; Transport emissions", "Landfill flows, optional road-network routing, facility shares, and hauling emissions."),
                ("2025 study vs model", "Waste estimation; Aggregate reporting; Diversion analysis; Study validation", "ICI study comparison, denominator disclosure, and diagnostic calibration."),
            ],
            columns=["Dashboard", "Relevant assumption stages", "What the assumptions affect"],
        )
        available_coverage = dashboard_coverage[dashboard_coverage["Dashboard"].isin(DASHBOARD_OPTIONS)].copy()
        st.dataframe(available_coverage, width="stretch", height=360, hide_index=True)
        if not available_coverage.empty:
            st.selectbox(
                "Open related dashboard",
                available_coverage["Dashboard"].tolist(),
                key="assumptions_dashboard_target",
            )
            st.button("Open dashboard", on_click=navigate_to_assumption_dashboard)
    with validation_tab:
        st.caption("These items are the clearest priorities for data-quality checks, partner confirmation, or field validation.")
        st.dataframe(
            validation_needed,
            width="stretch",
            height=530,
            hide_index=True,
            column_config={
                "Implementation": st.column_config.TextColumn(width="large"),
                "Effect / validation need": st.column_config.TextColumn(width="large"),
            },
        )
        st.markdown(
            "**Recommended validation sequence:** resolve identity/duplicate questions; verify business coordinates and "
            "business size; obtain hauler/facility and route information; then confirm diversion service and material acceptance."
        )
    with transport_tab:
        st.markdown(
            """
            **Garbage transport calculation used in Diversion opportunity**

            ```text
            assigned landfill = hauler rule, otherwise distance + wasteshed fallback
            estimated one-way road miles = straight-line business-to-landfill miles × road-mile multiplier
            truckload-equivalent trips = annual garbage tons ÷ average collection load
            allocated vehicle miles = one-way road miles × truckload-equivalent trips × route adjustment
            truck CO2e (metric tons) = allocated vehicle miles × kg CO2e per vehicle-mile ÷ 1,000
            ```

            Facility assignment is source-provided for the four recognized hauler names. Distance, payload, route adjustment, and emissions factor remain planning inputs until route, load, and fleet data are supplied by the haulers.
            """
        )

elif dashboard == "Business heat map":
    if heat_map_metric == HEATMAP_VOLUME_METRIC:
        heat_df = umbrella_map_df.copy()
        heat_df["heat_weight"] = heat_weight(heat_df["selected_waste_tons"], weight_scale)
    else:
        heat_df = heatmap_grid_source(umbrella_map_df, heat_map_metric, weight_scale)

    left_metric, middle_metric, right_metric = st.columns(3)
    left_metric.metric("Selected tons", f"{umbrella_filtered['selected_waste_tons'].sum():,.1f}")
    middle_metric.metric("Heat comparison", heat_map_metric)
    right_metric.metric("Selected metric", metric_label)
    if multifamily_excluded_rows:
        st.caption(
            f"Heat intensity and summary tons exclude {multifamily_excluded_rows:,} multifamily business(es). "
            "Their individual map points and business details remain available."
        )

    if map_df.empty:
        st.warning("No mapped businesses match the current slice.")
    else:
        render_heatmap_legend(metric_label, heat_map_metric)
        heatmap_event = None
        if selected_jurisdictions:
            map_col, jurisdiction_col = st.columns([3, 1])
            with map_col:
                heatmap_event = st.pydeck_chart(
                    build_business_heat_map(map_df, heat_df, radius_pixels, intensity, threshold),
                    width="stretch",
                    height=650,
                    key=map_component_key(f"business_heat_map_{heat_map_metric}", map_df),
                    selection_mode="single-object",
                    on_select="rerun",
                )
            with jurisdiction_col:
                st.markdown("**Jurisdiction KPIs**")
                jurisdiction_summary = heatmap_jurisdiction_kpis(
                    umbrella_filtered,
                    selected_jurisdictions,
                    jurisdiction_field,
                    material_columns,
                    selected_streams,
                    selected_materials,
                    material_mode,
                )
                render_heatmap_jurisdiction_cards(jurisdiction_summary)
        else:
            heatmap_event = st.pydeck_chart(
                build_business_heat_map(map_df, heat_df, radius_pixels, intensity, threshold),
                width="stretch",
                height=650,
                key=map_component_key(f"business_heat_map_{heat_map_metric}", map_df),
                selection_mode="single-object",
                on_select="rerun",
            )

        selected_business_id = selected_business_id_from_pydeck_event(heatmap_event)
        if selected_business_id is not None:
            selected_business_match = filtered[
                filtered["_business_row_id"].astype(int) == int(selected_business_id)
            ]
            if not selected_business_match.empty:
                st.divider()
                st.subheader("Selected Business")
                business_detail_panel(
                    selected_business_match.iloc[0],
                    material_columns,
                    business_column,
                    address_column,
                    jurisdiction_field,
                    business_group_field,
                )
        else:
            st.caption("Click a business dot to inspect its stream fingerprint and material profile.")

    st.subheader("Filtered Results")
    table = filtered_business_table(
        filtered,
        business_column,
        address_column,
        jurisdiction_field,
        business_group_field,
        latitude_column,
        longitude_column,
    )
    material_table = material_driver_table(
        filtered,
        material_columns,
        selected_streams,
        selected_materials,
        material_mode,
    )
    if not material_table.empty:
        material_total = float(material_table["Selected Waste Tons"].sum())
        material_table = material_table.reset_index(drop=True)
        material_table.insert(0, "Rank", np.arange(1, len(material_table) + 1))
        material_table["Share of Tons"] = (
            material_table["Selected Waste Tons"] / material_total * 100
            if material_total > 0
            else 0.0
        )

    business_tab, material_tab = st.tabs(["Businesses", "Materials"])
    with business_tab:
        st.dataframe(
            table,
            width="stretch",
            height=360,
            hide_index=True,
        )
        csv_data = table.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Export filtered businesses",
            data=csv_data,
            file_name="filtered_waste_heatmap_rows.csv",
            mime="text/csv",
        )
    with material_tab:
        if material_table.empty:
            st.warning("No material-level tons are available for the current heat-map slice.")
        else:
            st.dataframe(
                material_table,
                width="stretch",
                height=360,
                hide_index=True,
                column_config={
                    "Selected Waste Tons": st.column_config.NumberColumn(format="%.1f"),
                    "Share of Tons": st.column_config.NumberColumn(format="%.1f%%"),
                },
            )
            st.download_button(
                "Export heat-map materials",
                data=material_table.to_csv(index=False).encode("utf-8"),
                file_name="filtered_waste_heatmap_materials.csv",
                mime="text/csv",
            )
    render_vital_few_section(
        filtered,
        material_columns,
        selected_streams,
        selected_materials,
        material_mode,
        business_column,
        business_group_field,
        jurisdiction_field,
        address_column,
        key_prefix="heatmap_vital_few",
    )

elif dashboard == "Census block groups":
    if block_group_controls["boundary_source"] == "Auto-download Census 2023 CA":
        try:
            with st.spinner("Checking Census block group file..."):
                block_group_path = ensure_census_block_group_zip(DEFAULT_TIGER_YEAR, DEFAULT_STATE_FIPS)
        except Exception as exc:
            st.error("The Census block group file could not be downloaded.")
            st.code(census_block_group_url(DEFAULT_TIGER_YEAR, DEFAULT_STATE_FIPS))
            st.exception(exc)
            st.stop()
    else:
        block_group_path = Path(block_group_controls["boundary_path"]).expanduser()

    try:
        block_groups = load_block_groups_from_file(
            str(block_group_path),
            block_group_controls["county_fips"],
        )
    except Exception as exc:
        st.error("The block group boundary file could not be read.")
        st.exception(exc)
        st.stop()

    if map_df.empty:
        st.warning("No mapped businesses match the current slice.")
        st.stop()

    coord_lookup_source = data[["_business_row_id", latitude_column, longitude_column]].rename(
        columns={
            latitude_column: "latitude",
            longitude_column: "longitude",
        }
    )
    block_group_cache_key = "|".join(block_groups["GEOID"].astype(str).sort_values().tolist())
    block_group_lookup = build_business_block_group_lookup(
        coord_lookup_source,
        block_groups,
        block_group_cache_key,
    )
    joined = attach_block_group_lookup(umbrella_map_df, block_group_lookup)
    display_joined = attach_block_group_lookup(map_df, block_group_lookup)
    block_summary = aggregate_block_groups(joined, block_groups)
    block_summary = add_block_group_top_material_group(
        block_summary,
        umbrella_filtered,
        block_group_lookup,
        material_columns,
        selected_streams,
        selected_materials,
        material_mode,
    )

    matched_count = int(joined["matched_block_group"].sum())
    active_block_groups = int((block_summary["business_count"] > 0).sum())
    selected_geoid = st.session_state.selected_block_group_geoid
    if selected_geoid and selected_block_group_metric_row(block_summary, selected_geoid) is None:
        st.session_state.selected_block_group_geoid = None
        selected_geoid = None

    left_metric, middle_metric, right_metric = st.columns(3)
    left_metric.metric("Matched to block groups", f"{matched_count:,}")
    middle_metric.metric("Active block groups", f"{active_block_groups:,}")
    right_metric.metric("Selected tons", f"{umbrella_map_df['selected_waste_tons'].sum():,.1f}")
    if multifamily_excluded_rows:
        st.caption(
            f"Block-group counts, rankings, and tons exclude {multifamily_excluded_rows:,} multifamily business(es). "
            "Individual multifamily points and profiles remain available."
        )

    if selected_geoid:
        selected_label = selected_block_group_label(block_summary, selected_geoid)
        selected_row = selected_block_group_metric_row(block_summary, selected_geoid)
        selected_tons = float(selected_row["total_waste_tons"]) if selected_row is not None else 0.0
        selected_business_count = int(selected_row["business_count"]) if selected_row is not None else 0
        status_col, reset_col = st.columns([0.78, 0.22])
        status_col.info(
            f"{selected_label} | "
            f"{selected_business_count:,} businesses | {selected_tons:,.1f} selected tons"
        )
        if reset_col.button("Reset map", width="stretch"):
            st.session_state.selected_block_group_geoid = None
            st.session_state.block_group_map_reset_nonce += 1
            st.rerun()
    else:
        st.caption(
            "Click a census block group to zoom in and show area-specific drivers below. "
            "Hover over business dots to inspect individual businesses."
        )

    render_block_group_legend(
        block_group_controls["block_metric_name"],
        block_group_controls["show_business_points"],
        selected_geoid,
    )
    block_group_event = st.pydeck_chart(
        build_block_group_map(
            block_summary,
            block_group_controls["block_metric_name"],
            display_joined,
            block_group_controls["show_business_points"],
            float(block_group_controls["simplify_tolerance"]),
            selected_geoid,
        ),
        width="stretch",
        height=650,
        selection_mode="single-object",
        on_select="rerun",
        key=f"block_group_map_{st.session_state.block_group_map_reset_nonce}",
    )

    clicked_geoid = selected_geoid_from_pydeck_event(block_group_event)
    if clicked_geoid and clicked_geoid != st.session_state.selected_block_group_geoid:
        st.session_state.selected_block_group_geoid = clicked_geoid
        st.rerun()

    selected_geoid = st.session_state.selected_block_group_geoid
    if selected_geoid:
        selected_business_ids = display_joined.loc[
            display_joined["GEOID"].astype(str) == str(selected_geoid),
            "_business_row_id",
        ].dropna()
        selected_businesses = filtered[
            filtered["_business_row_id"].isin(selected_business_ids)
        ].copy()

        st.subheader("Selected Block Group Drivers")
        selected_table = filtered_business_table(
            selected_businesses,
            business_column,
            address_column,
            jurisdiction_field,
            business_group_field,
            latitude_column,
            longitude_column,
            include_row_id=True,
        )
        material_drivers = material_driver_table(
            selected_businesses,
            material_columns,
            selected_streams,
            selected_materials,
            material_mode,
        )

        business_tab, material_tab = st.tabs(["Business drivers", "Material drivers"])
        with business_tab:
            if selected_table.empty:
                st.warning("No businesses in the current slice are matched to this block group.")
            else:
                visible_business_columns = [
                    column for column in selected_table.columns if column != "Business Row ID"
                ]
                business_selection = st.dataframe(
                    selected_table,
                    width="stretch",
                    height=360,
                    hide_index=True,
                    column_order=visible_business_columns,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"selected_bg_businesses_{selected_geoid}",
                )
                try:
                    selected_rows = business_selection.selection.get("rows", [])
                except Exception:
                    selected_rows = []
                if selected_rows:
                    selected_row_index = selected_rows[0]
                    selected_business_id = selected_table.iloc[selected_row_index]["Business Row ID"]
                    selected_business_match = selected_businesses[
                        selected_businesses["_business_row_id"] == selected_business_id
                    ]
                    if not selected_business_match.empty:
                        st.divider()
                        st.subheader("Business Waste Profile")
                        business_detail_panel(
                            selected_business_match.iloc[0],
                            material_columns,
                            business_column,
                            address_column,
                            jurisdiction_field,
                            business_group_field,
                        )
                else:
                    st.caption("Click a business row to inspect its primary streams and material profile.")

                csv_data = selected_table.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Export selected block group businesses",
                    data=csv_data,
                    file_name=f"block_group_{selected_geoid}_businesses.csv",
                    mime="text/csv",
                )

        with material_tab:
            if material_drivers.empty:
                st.warning("No material-level tons are available for this selected block group and slice.")
            else:
                st.dataframe(
                    material_drivers,
                    width="stretch",
                    height=360,
                    hide_index=True,
                )
                csv_data = material_drivers.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Export selected block group material drivers",
                    data=csv_data,
                    file_name=f"block_group_{selected_geoid}_material_drivers.csv",
                    mime="text/csv",
                )

        render_vital_few_section(
            selected_businesses,
            material_columns,
            selected_streams,
            selected_materials,
            material_mode,
            business_column,
            business_group_field,
            jurisdiction_field,
            address_column,
            key_prefix=f"selected_block_group_{selected_geoid}_vital_few",
        )
    else:
        st.subheader("Ranked Census Block Groups")
        ranking = block_group_ranking_table(
            block_summary,
            block_group_controls["block_metric_name"],
            block_group_controls["include_empty_block_groups"],
        )
        st.dataframe(
            ranking.head(block_group_controls["top_n_block_groups"]),
            width="stretch",
            height=360,
            hide_index=True,
        )

        csv_data = ranking.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Export block group ranking",
            data=csv_data,
            file_name="block_group_waste_ranking.csv",
            mime="text/csv",
        )
        render_vital_few_section(
            filtered,
            material_columns,
            selected_streams,
            selected_materials,
            material_mode,
            business_column,
            business_group_field,
            jurisdiction_field,
            address_column,
            key_prefix="census_vital_few",
            block_summary=block_summary,
        )
elif dashboard == "Circular flow engine":
    landfill_frame = landfill_assumption_frame(circular_controls["landfill_shares"])
    road_distance_lookup = None
    distance_status = ROAD_DISTANCE_ESTIMATE_MODE
    if circular_controls["distance_model"] in {ROAD_DISTANCE_TIGER_MODE, ROAD_DISTANCE_OSM_MODE}:
        try:
            full_road_source = road_distance_source_frame(data, latitude_column, longitude_column)
            local_graph_path = circular_controls.get("local_graph_path", "")
            if circular_controls["distance_model"] == ROAD_DISTANCE_TIGER_MODE:
                road_cache_ready = tiger_road_distance_cache_exists(full_road_source, landfill_frame)
                mode_note = (
                    "Census TIGER road-network mode caches the full workbook's business-to-landfill distances. "
                    "First run downloads the county roads ZIP and builds a lightweight road graph."
                )
                build_label = "Build TIGER road-distance cache"
            else:
                road_cache_ready = osm_road_distance_cache_exists(full_road_source, landfill_frame, local_graph_path)
                mode_note = (
                    "OpenStreetMap mode caches the full workbook's business-to-landfill distances. "
                    "Use this only when a local GraphML cache is available or Overpass is responsive."
                )
                build_label = "Build OpenStreetMap road-distance cache"
            st.caption(mode_note + " Later slices reuse the cache.")
            build_road_cache = road_cache_ready or st.button(
                build_label,
                help="Downloads/caches the SLO County drive network and computes business-to-landfill road distances. First run can take several minutes.",
            )
            if build_road_cache:
                spinner_text = (
                    "Loading cached road-network distances..."
                    if road_cache_ready
                    else "Building road-network distance cache for all businesses..."
                )
                with st.spinner(spinner_text):
                    if circular_controls["distance_model"] == ROAD_DISTANCE_TIGER_MODE:
                        road_distance_lookup = build_tiger_road_distance_lookup(full_road_source, landfill_frame)
                    else:
                        road_distance_lookup = build_osm_road_distance_lookup(
                            full_road_source,
                            landfill_frame,
                            local_graph_path,
                        )
                if road_distance_lookup is not None and not road_distance_lookup.empty:
                    active_ids = set(map_df["_business_row_id"].dropna().tolist())
                    road_distance_lookup = road_distance_lookup[
                        road_distance_lookup["_business_row_id"].isin(active_ids)
                    ].copy()
                    distance_status = circular_controls["distance_model"]
            else:
                st.info(
                    "Road-network mode is selected, but the road-distance cache has not been built yet. "
                    "Using the straight-line estimate until you build the cache."
                )
            if build_road_cache and (road_distance_lookup is None or road_distance_lookup.empty):
                st.warning("Road-network distances returned no matches, so the dashboard is using the fallback estimate.")
            else:
                pass
        except ImportError as exc:
            st.warning(str(exc))
            st.code(
                r'cd "C:\Users\tonyg\OneDrive\Documents\Grad Project\waste_heatmap_app"' "\n"
                r'& "..\mergent_enrichment\.venv\Scripts\python.exe" -m pip install -r requirements.txt',
                language="powershell",
            )
        except Exception as exc:
            st.warning(
                "Road-network distances could not be calculated, so the dashboard is using the fallback estimate. "
                "If OpenStreetMap timed out, use Census TIGER mode or provide a local GraphML road graph in the sidebar."
            )
            st.caption(str(exc))

    flows, business_rollup, landfill_summary = estimate_haul_flows(
        map_df,
        landfill_frame,
        circular_controls["allocation_mode"],
        circular_controls["road_multiplier"],
        circular_controls["operations_multiplier"],
        circular_controls["kg_co2e_per_ton_mile"],
        circular_controls["trips_per_year"],
        circular_controls["average_truckload_tons"],
        circular_controls["diversion_trips_per_business"],
        circular_controls["kg_co2e_per_vehicle_mile"],
        road_distance_lookup,
    )

    total_landfill_tons = float(map_df["selected_waste_tons"].sum()) if not map_df.empty else 0.0
    total_ton_miles = float(flows["ton_miles"].sum()) if not flows.empty else 0.0
    total_vehicle_miles = float(flows["vehicle_miles"].sum()) if "vehicle_miles" in flows.columns and not flows.empty else 0.0
    total_co2e = float(flows["co2e_metric_tons"].sum()) if not flows.empty else 0.0
    avg_route_miles = (
        float(np.average(flows["route_miles"], weights=flows["flow_tons"]))
        if not flows.empty and float(flows["flow_tons"].sum()) > 0
        else 0.0
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric(
        "Landfill tons/year",
        f"{total_landfill_tons:,.1f}",
        help="Modeled annual landfill-disposed tons for the current sidebar slice.",
    )
    metric_cols[1].metric(
        "Annual haul ton-miles",
        f"{total_ton_miles:,.0f}",
        help=(
            "A hauling workload measure: one ton carried one mile equals one ton-mile. Higher values point to "
            "businesses or areas where landfill hauling has a larger transportation burden. This does not assign "
            "one full weekly truck trip to each business."
        ),
    )
    metric_cols[2].metric(
        "Truck CO2e/year",
        f"{total_co2e:,.1f} mt",
        help=(
            "Metric tons of CO2e estimated from annual vehicle miles. Vehicle miles use truckload-equivalent trips "
            "so one weekly route can serve multiple businesses."
        ),
    )
    metric_cols[3].metric(
        "Annual vehicle miles",
        f"{total_vehicle_miles:,.0f}",
        help="One-way route miles multiplied by truckload-equivalent trips and collection route adjustment.",
    )
    if circular_controls["allocation_mode"] == HAULER_FACILITY_ALLOCATION_MODE and not business_rollup.empty:
        rule_businesses = int((business_rollup["allocation_source"] == "Hauler facility rule").sum())
        fallback_businesses = int(
            (business_rollup["allocation_source"] == "Fallback: distance + wasteshed share").sum()
        )
        rule_tons = float(
            flows.loc[flows["allocation_source"] == "Hauler facility rule", "flow_tons"].sum()
        ) if not flows.empty else 0.0
        st.caption(
            f"Hauler facility rules assigned {rule_businesses:,} mapped businesses "
            f"({rule_tons:,.1f} landfill tons/year). "
            f"{fallback_businesses:,} mapped businesses use the distance + wasteshed fallback."
        )

    st.info(
        "This is a screening model for circular-flow planning. Hauling lines are estimated flows, not verified "
        "truck routes. Replace the planning shares with IWMA facility tonnage or hauler route data when available."
    )
    st.caption(f"Distance source for this run: {distance_status}.")
    with st.expander("How to read these metrics", expanded=False):
        st.markdown(
            """
            - **Landfill tons/year**: modeled annual tons in the landfill stream after the current filters.
            - **Annual haul ton-miles**: a transportation workload metric. One ton carried one mile equals one ton-mile; it is mostly driven by tons and distance, not weekly pickup frequency.
            - **Annual vehicle miles**: estimated hauling mileage after sharing truck trips across businesses by tons.
            - **Truckload-equivalent trips**: selected annual tons divided by the average collection load tons. This prevents one business from being assigned a full weekly truck trip.
            - **Collection weeks/year**: documents weekly service frequency. The default is 52, but route emissions are allocated by truckload-equivalent tons.
            - **Collection route adjustment**: adds planning mileage for collection circulation, staging, and return movement that a single one-way path does not capture.
            - **Truck CO2e/year**: annual vehicle miles converted using the sidebar kg CO2e per vehicle-mile factor.
            - **Avg one-way miles**: ton-weighted distance, so larger waste generators influence the average more.
            - **Map lines**: TIGER road-network mode uses cached county-road paths. Direct connectors only appear when route geometry is unavailable.
            """
        )

    st.subheader("Map Display")
    route_display_mode = st.radio(
        "Route view",
        ["Fast live map", "Top TIGER road paths", "External all-business route map"],
        index=0,
        horizontal=True,
        help=(
            "Fast live map keeps Streamlit responsive. Top TIGER road paths draws a small road-following sample. "
            "External all-business route map gives planners access to the prebuilt full-route HTML file."
        ),
    )
    live_route_limit = circular_controls["flow_line_limit"]
    if route_display_mode == "Top TIGER road paths":
        live_route_limit = st.slider(
            "Live TIGER paths to draw",
            min_value=25,
            max_value=500,
            value=100,
            step=25,
            help="A small sample keeps the Streamlit map interactive. Use the external HTML for all businesses.",
        )
    if route_display_mode == "External all-business route map":
        default_route_map = ensure_node_click_route_map_html()
        if default_route_map is not None and default_route_map.exists():
            file_size_mb = default_route_map.stat().st_size / (1024 * 1024)
            st.success(
                f"Static all-business TIGER route map is available ({file_size_mb:,.1f} MB). "
                "Routes are visible but not clickable; business and landfill nodes remain interactive."
            )
            st.code(str(default_route_map), language="text")
            show_static_map = st.checkbox(
                "Show static route map in dashboard",
                value=True,
                help="Embeds the prebuilt HTML map. It can take a moment because the static file is large.",
            )
            if show_static_map:
                static_html = read_static_html_file(str(default_route_map), default_route_map.stat().st_mtime_ns)
                components.html(static_html, height=720, scrolling=False)
            st.download_button(
                "Download node-click route map HTML",
                data=default_route_map.read_bytes(),
                file_name=default_route_map.name,
                mime="text/html",
                help="Download the HTML file, then open it in your browser. Routes are visible but not clickable; nodes are interactive.",
            )
            st.caption(
                "This is one static PyDeck map, not two overlaid canvases. That is why node interaction works cleanly."
            )
        else:
            st.warning("The all-business route map HTML has not been built yet.")

    if map_df.empty or business_rollup.empty or flows.empty:
        st.warning("No mapped landfill-disposed tons are available for the current slice.")
    else:
        sorted_flows = flows.sort_values("flow_tons", ascending=False)
        if route_display_mode in {"Fast live map", "External all-business route map"}:
            display_flows = sorted_flows.head(0).copy()
        else:
            display_flows = sorted_flows.head(live_route_limit).copy()
        route_flows = pd.DataFrame()
        if distance_status == ROAD_DISTANCE_TIGER_MODE and route_display_mode == "Top TIGER road paths":
            with st.spinner("Loading selected TIGER route paths..."):
                route_flows = build_tiger_route_path_flows(display_flows)
        routed_count = len(route_flows) if not route_flows.empty else 0
        render_circular_flow_legend(landfill_frame, routed_count)
        if route_display_mode == "External all-business route map":
            st.caption("The Streamlit map below stays lightweight; use the HTML download above for the full road-path view.")
        elif routed_count > 0:
            missing_routes = max(len(display_flows) - routed_count, 0)
            route_caption = (
                f"Showing {routed_count:,} cached TIGER road paths. "
                + (
                    f"{missing_routes:,} flows use faint direct connectors because route geometry was unavailable."
                    if missing_routes
                    else "No straight-line connectors are needed for the displayed flows."
                )
            )
            st.caption(route_caption)
        else:
            st.caption(
                "Fast live map shows businesses and landfill facilities without drawing heavy route geometry. "
                "Use the external HTML route map for the full all-business TIGER road-path view."
            )
        circular_deck = build_circular_flow_map(business_rollup, display_flows, landfill_frame, route_flows)
        if routed_count > 0 and route_display_mode == "Top TIGER road paths":
            html_key = tiger_route_geometry_signature(route_flows)
            html_path = write_circular_route_map_html(circular_deck, html_key)
            if html_path is not None:
                st.caption(f"Cached standalone route map: {html_path}")
                try:
                    st.download_button(
                        "Download standalone route map",
                        data=html_path.read_bytes(),
                        file_name=html_path.name,
                        mime="text/html",
                    )
                except OSError:
                    pass
        st.pydeck_chart(
            circular_deck,
            width="stretch",
            height=650,
            key=map_component_key("circular_flow_map", business_rollup),
        )

    hauling_tab, exchange_tab, assumptions_tab = st.tabs(
        ["Hauling emissions", "Material exchange", "Assumptions"]
    )

    with hauling_tab:
        left_chart, right_table = st.columns([0.46, 0.54])
        with left_chart:
            st.subheader("Facility Flow Split")
            st.caption("Allocated annual landfill tons by facility under the selected allocation method.")
            if landfill_summary.empty:
                st.warning("No facility flow summary is available.")
            else:
                flow_chart = (
                    alt.Chart(landfill_summary)
                    .mark_bar(opacity=0.88)
                    .encode(
                        x=alt.X("Landfill:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-25)),
                        y=alt.Y("Allocated Landfill Tons:Q", title="Allocated landfill tons/year"),
                        color=alt.Color(
                            "Landfill:N",
                            scale=alt.Scale(
                                domain=list(LANDFILL_CHART_COLORS.keys()),
                                range=list(LANDFILL_CHART_COLORS.values()),
                            ),
                            title=None,
                        ),
                        tooltip=[
                            alt.Tooltip("Landfill:N"),
                            alt.Tooltip("Allocated Landfill Tons:Q", format=",.1f"),
                            alt.Tooltip("Truck CO2e (metric tons):Q", format=",.1f"),
                        ],
                    )
                    .properties(height=320)
                )
                st.altair_chart(flow_chart, width="stretch")
        with right_table:
            st.subheader("Landfill Summary")
            st.caption("Facility-level totals. Average miles are ton-weighted one-way haul distances.")
            st.dataframe(
                landfill_summary,
                width="stretch",
                height=320,
                hide_index=True,
                column_config={
                    "Allocated Landfill Tons": st.column_config.NumberColumn(
                        "Allocated Landfill Tons",
                        help="Modeled annual landfill tons allocated to this facility.",
                        format="%.1f",
                    ),
                    "Avg One-Way Miles": st.column_config.NumberColumn(
                        "Avg One-Way Miles",
                        help="Ton-weighted one-way haul distance from businesses to this facility.",
                        format="%.1f",
                    ),
                    "Annual Ton-Miles": st.column_config.NumberColumn(
                        "Annual haul ton-miles",
                        help="Facility hauling workload: allocated tons multiplied by distance. It is a load-distance metric, not a count of weekly truck trips.",
                        format="%.0f",
                    ),
                    "Truckload-Equivalent Trips": st.column_config.NumberColumn(
                        "Truckload-Equivalent Trips",
                        help="Allocated tons divided by the assumed average collection load tons.",
                        format="%.2f",
                    ),
                    "Annual Vehicle Miles": st.column_config.NumberColumn(
                        "Annual Vehicle Miles",
                        help="Route miles multiplied by truckload-equivalent trips and collection route adjustment.",
                        format="%.0f",
                    ),
                    "Truck CO2e (metric tons)": st.column_config.NumberColumn(
                        "Truck CO2e (metric tons)",
                        help="Estimated annual truck emissions from annual vehicle miles.",
                        format="%.1f",
                    ),
                    "Load-based CO2e (metric tons)": st.column_config.NumberColumn(
                        "Load-based CO2e (metric tons)",
                        help="Reference estimate from ton-miles and kg CO2e per ton-mile.",
                        format="%.1f",
                    ),
                },
            )

        distribution_comparison = landfill_distribution_comparison(landfill_summary)
        st.subheader("Landfill Distribution vs Study Basis")
        st.caption(
            "Dashboard allocation is the current model split. Study countywide uses the 2019 MSW wasteshed table. "
            "Study mapped-only renormalizes the three mapped SLO County landfills, excluding the smaller off-county/other facilities."
        )
        if distribution_comparison.empty:
            st.warning("No landfill distribution comparison is available.")
        else:
            st.altair_chart(landfill_distribution_chart(distribution_comparison), width="stretch")
            st.dataframe(
                distribution_comparison,
                width="stretch",
                height=245,
                hide_index=True,
                column_config={
                    "2019 MSW Tons": st.column_config.NumberColumn(format="%.0f"),
                    "Allocated Landfill Tons": st.column_config.NumberColumn(format="%.1f"),
                    "Dashboard Share (%)": st.column_config.NumberColumn(format="%.1f"),
                    "Study Countywide Share (%)": st.column_config.NumberColumn(format="%.1f"),
                    "Study Mapped-Only Share (%)": st.column_config.NumberColumn(format="%.1f"),
                    "Difference vs Countywide (pp)": st.column_config.NumberColumn(format="%+.1f"),
                    "Difference vs Mapped-Only (pp)": st.column_config.NumberColumn(format="%+.1f"),
                },
            )

        st.subheader("Business Hauling Drivers")
        st.caption("Businesses ranked by estimated hauling emissions for the current slice.")
        if business_rollup.empty:
            st.warning("No business hauling rows are available.")
        else:
            hauling_table = business_rollup.copy()
            hauling_table = hauling_table.rename(
                columns={
                    "business_name": "Business",
                    "jurisdiction": "Jurisdiction",
                    "business_group": "Business Group",
                    "selected_waste_tons": "Business Landfill Tons",
                    "route_miles": "One-Way Miles",
                    "ton_miles": "Annual Ton-Miles",
                    "truckload_equivalent_trips": "Truckload-Equivalent Trips",
                    "vehicle_miles": "Annual Vehicle Miles",
                    "co2e_metric_tons": "Truck CO2e (metric tons)",
                    "load_co2e_metric_tons": "Load-based CO2e (metric tons)",
                    "distance_source": "Distance Source",
                    "allocation_source": "Assignment Method",
                }
            )
            hauling_columns = [
                column
                for column in [
                    "Business",
                    "Jurisdiction",
                    "Business Group",
                    "Landfill",
                    "Assignment Method",
                    "Business Landfill Tons",
                    "One-Way Miles",
                    "Annual Ton-Miles",
                    "Truckload-Equivalent Trips",
                    "Annual Vehicle Miles",
                    "Truck CO2e (metric tons)",
                    "Load-based CO2e (metric tons)",
                    "Distance Source",
                ]
                if column in hauling_table.columns
            ]
            hauling_table = hauling_table[hauling_columns].sort_values("Truck CO2e (metric tons)", ascending=False)
            st.dataframe(
                hauling_table.head(75),
                width="stretch",
                height=360,
                hide_index=True,
                column_config={
                    "Business Landfill Tons": st.column_config.NumberColumn(
                        "Business Landfill Tons",
                        help="Modeled annual landfill tons for this business after filters.",
                        format="%.1f",
                    ),
                    "One-Way Miles": st.column_config.NumberColumn(
                        "One-Way Miles",
                        help="Estimated one-way distance from the business to the assigned landfill flow.",
                        format="%.1f",
                    ),
                    "Annual Ton-Miles": st.column_config.NumberColumn(
                        "Annual haul ton-miles",
                        help="Business hauling workload: landfill tons multiplied by distance. It should not change much when only truck payload assumptions change.",
                        format="%.0f",
                    ),
                    "Truckload-Equivalent Trips": st.column_config.NumberColumn(
                        "Truckload-Equivalent Trips",
                        help="Business tons divided by the assumed average collection load tons.",
                        format="%.2f",
                    ),
                    "Annual Vehicle Miles": st.column_config.NumberColumn(
                        "Annual Vehicle Miles",
                        help="Estimated vehicle miles allocated to this business after load sharing.",
                        format="%.0f",
                    ),
                    "Truck CO2e (metric tons)": st.column_config.NumberColumn(
                        "Truck CO2e (metric tons)",
                        help="Estimated annual truck emissions from allocated vehicle miles.",
                        format="%.2f",
                    ),
                    "Load-based CO2e (metric tons)": st.column_config.NumberColumn(
                        "Load-based CO2e (metric tons)",
                        help="Reference estimate from ton-miles and kg CO2e per ton-mile.",
                        format="%.2f",
                    ),
                },
            )
            st.download_button(
                "Export hauling drivers",
                data=hauling_table.to_csv(index=False).encode("utf-8"),
                file_name="circular_flow_hauling_drivers.csv",
                mime="text/csv",
            )

    with exchange_tab:
        zip_column = zipcode_display_column(filtered)
        exchange_block_lookup = None
        exchange_block_groups = None
        if circular_controls["exchange_geography"] == "Census block group":
            try:
                with st.spinner("Preparing block group exchange areas..."):
                    block_group_path = ensure_census_block_group_zip(DEFAULT_TIGER_YEAR, DEFAULT_STATE_FIPS)
                    exchange_block_groups = load_block_groups_from_file(str(block_group_path), DEFAULT_COUNTY_FIPS)
                    coord_lookup_source = data[["_business_row_id", latitude_column, longitude_column]].rename(
                        columns={latitude_column: "latitude", longitude_column: "longitude"}
                    )
                    exchange_block_key = "|".join(exchange_block_groups["GEOID"].astype(str).sort_values().tolist())
                    exchange_block_lookup = build_business_block_group_lookup(
                        coord_lookup_source,
                        exchange_block_groups,
                        exchange_block_key,
                    )
            except Exception as exc:
                st.warning("Census block group exchange areas could not be prepared. Falling back to jurisdiction.")
                st.caption(str(exc))
                circular_controls["exchange_geography"] = "Jurisdiction"

        area_series = circular_exchange_area_series(
            filtered,
            circular_controls["exchange_geography"],
            exchange_block_lookup,
            zip_column,
            jurisdiction_field,
        )
        material_rows = build_business_material_exchange_rows(
            filtered,
            material_columns,
            selected_materials,
            area_series,
            business_column,
            business_group_field,
            jurisdiction_field,
            circular_controls["min_exchange_tons"],
        )
        area_options = (
            material_rows.groupby("Exchange Area")["Disposed Tons"].sum().sort_values(ascending=False).index.tolist()
            if not material_rows.empty
            else []
        )
        selected_exchange_areas = st.multiselect(
            "Focus exchange areas",
            area_options,
            default=[],
            help="Leave blank to include every area in the current slice.",
        )
        if selected_exchange_areas and circular_controls["exchange_geography"] == "Census block group":
            focus_map = build_exchange_area_focus_map(
                exchange_block_groups,
                selected_exchange_areas,
                material_rows,
                filtered,
                latitude_column,
                longitude_column,
            )
            if focus_map is not None:
                st.subheader("Focused Exchange Areas")
                st.caption("Selected block groups are highlighted together; blue points are businesses contributing selected material-exchange signals.")
                st.pydeck_chart(
                    focus_map,
                    width="stretch",
                    height=430,
                    key=(
                        "circular_exchange_area_focus_map_"
                        + hashlib.sha256("|".join(sorted(selected_exchange_areas)).encode("utf-8")).hexdigest()[:10]
                    ),
                )
        if selected_exchange_areas:
            material_rows = material_rows[material_rows["Exchange Area"].isin(selected_exchange_areas)].copy()
        exchange_table = build_exchange_opportunity_table(material_rows)

        st.subheader("Top Material Exchange Opportunities")
        st.caption(
            "This is a proximity-and-material signal. It assumes a material discarded by businesses in the same area "
            "could be worth investigating as a shared reuse, collection, or procurement opportunity."
        )
        if exchange_table.empty:
            st.warning("No material exchange signals are available for the current slice.")
        else:
            st.dataframe(
                exchange_table.head(circular_controls["top_exchange_rows"]),
                width="stretch",
                height=430,
                hide_index=True,
                column_config={
                    "Potential Exchange Tons": st.column_config.NumberColumn(format="%.1f"),
                    "Opportunity Score": st.column_config.NumberColumn(format="%.1f"),
                },
            )
            st.download_button(
                "Export exchange opportunities",
                data=exchange_table.to_csv(index=False).encode("utf-8"),
                file_name="material_exchange_opportunities.csv",
                mime="text/csv",
            )

        st.subheader("Business-Material Signals")
        if material_rows.empty:
            st.warning("No business-material rows meet the current threshold.")
        else:
            detail_columns = [
                "Exchange Area",
                "Business",
                "Business Group",
                "Jurisdiction",
                "Industry Description",
                "Material",
                "Material Group",
                "Disposed Tons",
            ]
            st.dataframe(
                material_rows[detail_columns].sort_values("Disposed Tons", ascending=False).head(100),
                width="stretch",
                height=360,
                hide_index=True,
                column_config={"Disposed Tons": st.column_config.NumberColumn(format="%.1f")},
            )

    with assumptions_tab:
        st.subheader("Model Assumptions")
        st.markdown(
            """
            - Landfills are the three SLO County landfill facilities listed by IWMA.
            - Hauler facility allocation assigns known trash haulers to their reported disposal facility and uses the blended planning fallback only for unknown haulers.
            - Census TIGER road-network mode uses official county road lines and caches the results.
            - OpenStreetMap mode is available for a more detailed graph, but it depends on a local GraphML file or Overpass availability.
            - Straight-line mode multiplies business-to-landfill air distance by the fallback road factor.
            - TIGER-routed map lines trace approximate county-road paths for the top displayed flows. Direct connectors are used when route geometry is unavailable.
            - Collection is assumed to operate weekly by default, but businesses are not assigned a full weekly truck trip. Vehicle miles are allocated by truckload-equivalent trips: selected tons divided by average collection load tons.
            - The default average collection load is 7 tons/truck trip. This is a conservative source-backed assumption and can be replaced with IWMA hauler route data.
            - The current Circular Engine map uses landfill-disposed tons. The diversion-trips-per-business control documents the future assumption for third-party diversion routing.
            - Truck CO2e uses annual vehicle miles and the selected kg CO2e per vehicle-mile factor. Ton-mile CO2e is retained as a reference column.
            - The default landfill shares are based on the 2019 wasteshed table for Cold Canyon, Chicago Grade, and City of Paso Robles Landfill.
            - Use IWMA facility tonnage, franchise-hauler route data, or CalRecycle facility reports when available.
            - Material exchange is a screening layer. It does not prove that a business can use another business's discarded material.
            """
        )
        st.subheader("Hauler-to-Landfill Rules")
        st.dataframe(
            hauler_rule_reference_table(),
            width="stretch",
            hide_index=True,
        )
        st.subheader("Trip and Payload Sources")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Assumption": "Average collection load",
                        "Default": f"{circular_controls['average_truckload_tons']:.1f} tons/truck trip",
                        "Use in model": "Annual tons divided by average load gives truckload-equivalent trips.",
                        "Source note": "EPA GHG equivalencies uses 7 tons per garbage truck; Seattle solid waste truck specs imply roughly 8.7-13.1 ton payload bounds for common collection trucks.",
                    },
                    {
                        "Assumption": "Collection frequency",
                        "Default": f"{int(circular_controls['trips_per_year'])} weeks/year",
                        "Use in model": "Documents weekly route service; emissions are load-shared, not one full weekly truck per business.",
                        "Source note": "Planner assumption until IWMA route schedules are available.",
                    },
                    {
                        "Assumption": "Vehicle-mile emissions factor",
                        "Default": f"{circular_controls['kg_co2e_per_vehicle_mile']:.2f} kg CO2e/vehicle-mile",
                        "Use in model": "Annual vehicle miles multiplied by kg CO2e per vehicle-mile.",
                        "Source note": "Derived from EPA diesel CO2 per gallon and refuse-truck fuel-economy literature; replace with MOVES or hauler fleet data when available.",
                    },
                ]
            ),
            width="stretch",
            hide_index=True,
        )
        st.markdown(
            """
            Source links for citation:
            - [EPA Greenhouse Gas Equivalencies Calculator documentation](https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator-calculations-and-references): uses **7 tons per garbage truck** in the garbage-truck equivalency and documents diesel CO2 per gallon.
            - [Seattle Public Utilities solid waste truck specifications](https://www.seattle.gov/Documents/Departments/SPU/Services/Garbage/Truck_Axles_Weights.pdf): empty and gross/full weights imply approximate payload capacity ranges for rear-load, front-load, side-load, and roll-off collection vehicles.
            - [NREL/Waste Management refuse-hauler evaluation](https://www.nrel.gov/docs/fy01osti/29073.pdf): documents real refuse collection operations where each truck services many stops on one route and may unload more than once per day.
            """
        )
        assumption_table = landfill_frame[["Landfill", "Address", "Share Percent", "latitude", "longitude"]].rename(
            columns={"Share Percent": "Planning Share (%)", "latitude": "Latitude", "longitude": "Longitude"}
        )
        st.dataframe(
            assumption_table,
            width="stretch",
            hide_index=True,
            column_config={
                "Planning Share (%)": st.column_config.NumberColumn(format="%.1f"),
                "Latitude": st.column_config.NumberColumn(format="%.6f"),
                "Longitude": st.column_config.NumberColumn(format="%.6f"),
            },
        )
elif dashboard == "Diversion opportunity":
    zip_column = zipcode_display_column(filtered)
    raw_opportunity, raw_material_detail = build_diversion_opportunity(
        filtered,
        material_columns,
        selected_materials,
        business_column,
        jurisdiction_field,
        business_group_field,
        address_column,
        zip_column,
    )
    umbrella_raw_opportunity, umbrella_raw_material_detail = build_diversion_opportunity(
        umbrella_filtered,
        material_columns,
        selected_materials,
        business_column,
        jurisdiction_field,
        business_group_field,
        address_column,
        zip_column,
    )
    selected_model_mode = diversion_controls["opportunity_model_mode"]
    opportunity, material_detail, calibration_factors = apply_opportunity_model_mode(
        raw_opportunity,
        raw_material_detail,
        selected_model_mode,
    )
    umbrella_opportunity, umbrella_material_detail, _ = apply_opportunity_model_mode(
        umbrella_raw_opportunity,
        umbrella_raw_material_detail,
        selected_model_mode,
    )
    selected_destinations = diversion_controls["selected_destinations"]
    min_opportunity_tons = diversion_controls["min_opportunity_tons"]
    min_opportunity_share = diversion_controls["min_opportunity_share"]
    map_opportunity = prepare_diversion_map_frame(
        opportunity,
        filtered,
        latitude_column,
        longitude_column,
        selected_destinations,
        diversion_controls["show_zero_opportunity"],
        min_opportunity_tons,
        min_opportunity_share,
    )

    opportunity_with_selection = add_selected_opportunity_columns(opportunity, selected_destinations)
    umbrella_opportunity_with_selection = add_selected_opportunity_columns(
        umbrella_opportunity,
        selected_destinations,
    )
    focus_mask = opportunity_focus_mask(
        opportunity,
        selected_destinations,
        min_opportunity_tons,
        min_opportunity_share,
    )
    focused_opportunity = opportunity_with_selection[focus_mask].copy()
    umbrella_focus_mask = opportunity_focus_mask(
        umbrella_opportunity,
        selected_destinations,
        min_opportunity_tons,
        min_opportunity_share,
    )
    focused_umbrella_opportunity = umbrella_opportunity_with_selection[umbrella_focus_mask].copy()
    total_landfill = float(umbrella_opportunity["Landfill Tons"].sum()) if not umbrella_opportunity.empty else 0.0
    total_opportunity = float(umbrella_opportunity_with_selection["Selected Opportunity Tons"].sum()) if not umbrella_opportunity.empty else 0.0
    opportunity_rate = (total_opportunity / total_landfill * 100) if total_landfill > 0 else 0.0
    businesses_with_opportunity = int(umbrella_focus_mask.sum()) if not umbrella_opportunity.empty else 0

    # Transport uses the landfill (garbage) stream regardless of the opportunity-material slice.
    # This keeps each business's disposal assignment and hauling burden comparable while the
    # diversion controls are used to screen potential outreach actions.
    transport_source = filtered.copy()
    transport_source["selected_waste_tons"] = pd.to_numeric(
        transport_source.get(STREAM_COLUMNS["disposed"]["total"], 0.0), errors="coerce"
    ).fillna(0.0)
    transport_map_df = prepare_business_map_frame(
        transport_source,
        latitude_column,
        longitude_column,
        jurisdiction_field,
        business_group_field,
        business_column,
    )
    transport_landfill_frame = landfill_assumption_frame(
        {facility["Landfill"]: facility["default_share"] for facility in LANDFILL_FACILITIES}
    )
    transport_flows, transport_business_rollup, transport_landfill_summary = estimate_haul_flows(
        transport_map_df,
        transport_landfill_frame,
        HAULER_FACILITY_ALLOCATION_MODE,
        diversion_controls["transport_road_multiplier"],
        diversion_controls["transport_operations_multiplier"],
        DEFAULT_TRUCK_KG_CO2E_PER_TON_MILE,
        DEFAULT_COLLECTION_TRIPS_PER_YEAR,
        diversion_controls["transport_truckload_tons"],
        DEFAULT_DIVERSION_TRIPS_PER_BUSINESS,
        diversion_controls["transport_kg_co2e_per_vehicle_mile"],
    )
    transport_total_tons = float(transport_flows["flow_tons"].sum()) if not transport_flows.empty else 0.0
    transport_ton_miles = float(transport_flows["ton_miles"].sum()) if not transport_flows.empty else 0.0
    transport_vehicle_miles = float(transport_flows["vehicle_miles"].sum()) if not transport_flows.empty else 0.0
    transport_co2e = float(transport_flows["co2e_metric_tons"].sum()) if not transport_flows.empty else 0.0
    transport_rule_tons = (
        float(transport_flows.loc[transport_flows["allocation_source"] == "Hauler facility rule", "flow_tons"].sum())
        if not transport_flows.empty
        else 0.0
    )
    transport_fallback_tons = max(transport_total_tons - transport_rule_tons, 0.0)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Landfill tons", f"{total_landfill:,.1f}")
    metric_cols[1].metric("Modeled potential diversion", f"{total_opportunity:,.1f}")
    metric_cols[2].metric("Opportunity rate", f"{opportunity_rate:,.1f}%")
    metric_cols[3].metric("Targets above threshold", f"{businesses_with_opportunity:,}")

    st.info(
        "Use this page to find the largest diversion outreach opportunities. "
        "The numbers are planning estimates based on the workbook and county study; confirm priority sites before outreach."
    )
    st.caption(opportunity_model_note(selected_model_mode))
    if multifamily_excluded_rows:
        st.caption(
            f"Diversion summary metrics and material/destination rollups exclude {multifamily_excluded_rows:,} "
            "multifamily business(es). Individual businesses remain visible in the map and business table."
        )

    boundary_layers = []
    requested_boundaries = diversion_controls["boundary_layers"]
    block_groups = None
    county_wkt = ""
    if requested_boundaries:
        try:
            with st.spinner("Checking boundary files..."):
                block_group_path = ensure_census_block_group_zip(DEFAULT_TIGER_YEAR, DEFAULT_STATE_FIPS)
                block_groups = load_block_groups_from_file(str(block_group_path), DEFAULT_COUNTY_FIPS)
                county_wkt = county_geometry_wkt(block_groups)
        except Exception as exc:
            st.warning("Boundary overlays could not be prepared, but the opportunity map can still load.")
            st.exception(exc)
            block_groups = None

    if block_groups is not None and "Census block groups" in requested_boundaries:
        block_layer_frame = block_groups.copy()
        block_layer_frame["boundary_name"] = block_layer_frame.get("NAMELSAD", block_layer_frame["GEOID"]).astype(str)
        block_layer_frame["boundary_type"] = "Census block group"
        if diversion_controls["boundary_detail"] > 0:
            block_layer_frame["geometry"] = block_layer_frame.geometry.simplify(
                diversion_controls["boundary_detail"],
                preserve_topology=True,
            )
        boundary_layers.append(
            boundary_layer(block_layer_frame, "diversion-block-groups", [78, 86, 82, 145], [120, 138, 128, 18])
        )

    if county_wkt and "ZIP / ZCTA" in requested_boundaries:
        try:
            zcta_path = ensure_zcta_zip(DEFAULT_ZCTA_YEAR)
            zctas = load_zctas_for_county(str(zcta_path), county_wkt, diversion_controls["boundary_detail"])
            boundary_layers.append(boundary_layer(zctas, "diversion-zctas", [44, 96, 142, 180], [44, 96, 142, 18]))
        except Exception as exc:
            st.warning("ZIP / ZCTA boundaries could not be loaded. The app will continue without that overlay.")
            st.caption(str(exc))

    if county_wkt and "Jurisdiction/community" in requested_boundaries:
        try:
            place_path = ensure_place_zip(DEFAULT_TIGER_YEAR, DEFAULT_STATE_FIPS)
            places = load_places_for_county(str(place_path), county_wkt, diversion_controls["boundary_detail"])
            boundary_layers.append(
                boundary_layer(places, "diversion-jurisdictions", [121, 78, 35, 190], [121, 78, 35, 20])
            )
            st.caption(
                "Jurisdiction/community overlay uses Census places and CDPs as a first-pass proxy. "
                "Exact CSD and sanitary district boundaries should be swapped in from SLO LAFCO/County GIS when available."
            )
        except Exception as exc:
            st.warning("Jurisdiction/community boundaries could not be loaded.")
            st.exception(exc)

    if map_opportunity.empty:
        st.warning("No mapped businesses have diversion opportunity for the current slice.")
    else:
        render_diversion_map_legend(selected_destinations, requested_boundaries)
        st.pydeck_chart(
            build_diversion_opportunity_map(map_opportunity, boundary_layers),
            width="stretch",
            height=650,
            key=map_component_key("diversion_opportunity_map", map_opportunity),
        )

    destination_rollup = diversion_destination_rollup(
        umbrella_opportunity,
        selected_destinations,
        min_opportunity_tons,
        min_opportunity_share,
    )
    material_rollup = diversion_material_rollup(
        umbrella_material_detail,
        selected_destinations,
        focused_umbrella_opportunity["_business_row_id"] if not focused_umbrella_opportunity.empty else [],
    )
    business_table = focused_opportunity.sort_values(
        "Selected Opportunity Tons",
        ascending=False,
    )

    st.subheader("Diversion Opportunity Drivers")
    business_tab, transport_tab, material_tab, destination_tab, study_tab = st.tabs(
        ["Businesses", "Garbage transport", "Materials", "Destination streams", "Study reference"]
    )
    with business_tab:
        business_columns = [
            "Business",
            "Jurisdiction",
            "Business Group",
            "ZIP Code",
            "Hauler",
            "Phone",
            "Website",
            "Landfill Tons",
            "Selected Opportunity Tons",
            "Selected Opportunity Share",
            "Opportunity Rate",
            "Curbside Recycle Tons",
            "Curbside Organics Tons",
            "Third-party Diversion Tons",
            "Top Material",
            "Preferred Destination",
            "Address",
        ]
        st.dataframe(
            business_table[business_columns].head(diversion_controls["top_n_opportunity"]),
            width="stretch",
            height=380,
            hide_index=True,
            column_config={
                "Landfill Tons": st.column_config.NumberColumn(format="%.1f"),
                "Selected Opportunity Tons": st.column_config.NumberColumn(format="%.1f"),
                "Selected Opportunity Share": st.column_config.NumberColumn(format="%.1f%%"),
                "Opportunity Rate": st.column_config.NumberColumn(format="%.1f%%"),
                "Curbside Recycle Tons": st.column_config.NumberColumn(format="%.1f"),
                "Curbside Organics Tons": st.column_config.NumberColumn(format="%.1f"),
                "Third-party Diversion Tons": st.column_config.NumberColumn(format="%.1f"),
            },
        )
        st.download_button(
            "Export diversion opportunity businesses",
            data=business_table.to_csv(index=False).encode("utf-8"),
            file_name="diversion_opportunity_businesses.csv",
            mime="text/csv",
        )

    with transport_tab:
        st.subheader("Business Garbage Transport and Emissions")
        st.caption(
            "Landfill destinations are assigned by the reported hauler. One-way road miles are estimated from "
            "business-to-facility straight-line distance using the sidebar multiplier; emissions are allocated by "
            "truckload-equivalent annual garbage tons."
        )
        transport_metric_cols = st.columns(4)
        transport_metric_cols[0].metric("Garbage tons/year", f"{transport_total_tons:,.1f}")
        transport_metric_cols[1].metric("Annual haul ton-miles", f"{transport_ton_miles:,.0f}")
        transport_metric_cols[2].metric("Truck CO2e/year", f"{transport_co2e:,.1f} mt")
        transport_metric_cols[3].metric("Annual vehicle miles", f"{transport_vehicle_miles:,.0f}")
        st.caption(
            f"Exact hauler-to-landfill rules assign {transport_rule_tons:,.1f} garbage tons/year. "
            f"{transport_fallback_tons:,.1f} tons/year with an unrecognized or blank hauler use the "
            "distance-and-wasteshed fallback."
        )

        transport_left, transport_right = st.columns([0.45, 0.55])
        with transport_left:
            if transport_landfill_summary.empty:
                st.warning("No mapped garbage transport records are available for the current filters.")
            else:
                st.altair_chart(
                    alt.Chart(transport_landfill_summary)
                    .mark_bar(opacity=0.88)
                    .encode(
                        x=alt.X("Landfill:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-25)),
                        y=alt.Y("Allocated Landfill Tons:Q", title="Assigned garbage tons/year"),
                        color=alt.Color(
                            "Landfill:N",
                            scale=alt.Scale(
                                domain=list(LANDFILL_CHART_COLORS.keys()),
                                range=list(LANDFILL_CHART_COLORS.values()),
                            ),
                            title=None,
                        ),
                        tooltip=[
                            alt.Tooltip("Landfill:N"),
                            alt.Tooltip("Allocated Landfill Tons:Q", format=",.1f"),
                            alt.Tooltip("Truck CO2e (metric tons):Q", format=",.2f"),
                        ],
                    )
                    .properties(height=300),
                    width="stretch",
                )
        with transport_right:
            st.dataframe(
                transport_landfill_summary,
                width="stretch",
                height=340,
                hide_index=True,
                column_config={
                    "Allocated Landfill Tons": st.column_config.NumberColumn(format="%.1f"),
                    "Avg One-Way Miles": st.column_config.NumberColumn(format="%.1f"),
                    "Annual Ton-Miles": st.column_config.NumberColumn(format="%.0f"),
                    "Annual Vehicle Miles": st.column_config.NumberColumn(format="%.0f"),
                    "Truck CO2e (metric tons)": st.column_config.NumberColumn(format="%.2f"),
                },
            )

        transport_table = transport_business_rollup.rename(
            columns={
                "business_name": "Business",
                "jurisdiction": "Jurisdiction",
                "business_group": "Business Group",
                "selected_waste_tons": "Garbage Tons",
                "route_miles": "Estimated One-Way Road Miles",
                "ton_miles": "Annual Ton-Miles",
                "truckload_equivalent_trips": "Truckload-Equivalent Trips",
                "vehicle_miles": "Annual Vehicle Miles",
                "co2e_metric_tons": "Truck CO2e (metric tons)",
                "allocation_source": "Landfill Assignment",
            }
        )
        transport_columns = [
            column
            for column in [
                "Business", "Jurisdiction", "Business Group", "Hauler", "Landfill", "Landfill Assignment",
                "Garbage Tons", "Estimated One-Way Road Miles", "Annual Ton-Miles",
                "Truckload-Equivalent Trips", "Annual Vehicle Miles", "Truck CO2e (metric tons)",
            ]
            if column in transport_table.columns
        ]
        transport_table = transport_table[transport_columns].sort_values(
            "Truck CO2e (metric tons)", ascending=False
        )
        st.subheader("Business Transport Drivers")
        st.dataframe(
            transport_table.head(100), width="stretch", height=380, hide_index=True,
            column_config={
                "Garbage Tons": st.column_config.NumberColumn(format="%.1f"),
                "Estimated One-Way Road Miles": st.column_config.NumberColumn(format="%.1f"),
                "Annual Ton-Miles": st.column_config.NumberColumn(format="%.0f"),
                "Truckload-Equivalent Trips": st.column_config.NumberColumn(format="%.2f"),
                "Annual Vehicle Miles": st.column_config.NumberColumn(format="%.0f"),
                "Truck CO2e (metric tons)": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.download_button(
            "Export business garbage transport",
            data=transport_table.to_csv(index=False).encode("utf-8"),
            file_name="diversion_opportunity_garbage_transport.csv",
            mime="text/csv",
        )

    with material_tab:
        if material_rollup.empty:
            st.warning("No material-level diversion opportunity is available for this slice.")
        else:
            st.altair_chart(
                iwma_destination_bar_chart(
                    material_rollup.head(20),
                    "Material",
                    POTENTIAL_TONS_COLUMN,
                    color_column="Destination",
                    height=360,
                ),
                width="stretch",
            )
            st.dataframe(
                material_rollup.head(60),
                width="stretch",
                height=340,
                hide_index=True,
                column_config={
                    POTENTIAL_TONS_COLUMN: st.column_config.NumberColumn(format="%.1f"),
                },
            )
            st.download_button(
                "Export diversion material drivers",
                data=material_rollup.to_csv(index=False).encode("utf-8"),
                file_name="diversion_opportunity_materials.csv",
                mime="text/csv",
            )

    with destination_tab:
        if selected_model_mode == STUDY_CALIBRATED_OPPORTUNITY_MODE:
            factor_text = ", ".join(
                f"{destination_label(destination)} x {calibration_factors.get(destination, 1.0):.2f}"
                for destination in selected_destinations
            )
            st.caption(f"Study-calibrated stream scaling: {factor_text}.")
        st.dataframe(
            destination_rollup,
            width="stretch",
            height=220,
            hide_index=True,
            column_config={
                POTENTIAL_TONS_COLUMN: st.column_config.NumberColumn(format="%.1f"),
                "Thresholded Tons": st.column_config.NumberColumn(format="%.1f"),
            },
        )
        if not destination_rollup.empty:
            st.altair_chart(
                iwma_destination_bar_chart(destination_rollup, "Destination", POTENTIAL_TONS_COLUMN, height=320),
                width="stretch",
            )

    with study_tab:
        left_study, right_study = st.columns(2)
        with left_study:
            st.markdown("**ICI landfill composition by material group**")
            st.dataframe(
                pd.DataFrame(
                    [{"Material Group": key, "Share of ICI Refuse": value} for key, value in ICI_MATERIAL_GROUP_SHARES.items()]
                ),
                width="stretch",
                hide_index=True,
                column_config={"Share of ICI Refuse": st.column_config.NumberColumn(format="%.1f%%")},
            )
        with right_study:
            st.markdown("**ICI landfill composition by management pathway**")
            st.dataframe(
                pd.DataFrame(
                    [{"Management Pathway": key, "Share of ICI Refuse": value} for key, value in ICI_PATHWAY_SHARES.items()]
                ),
                width="stretch",
                hide_index=True,
                column_config={"Share of ICI Refuse": st.column_config.NumberColumn(format="%.1f%%")},
            )
        st.caption(
            "Reference values come from the attached 2025 San Luis Obispo County ICI waste characterization pages. "
            "The dashboard applies the material pathway mapping to business-level landfill material estimates."
        )

elif dashboard == "Outreach campaign builder":
    zip_column = zipcode_display_column(filtered)
    raw_opportunity, raw_material_detail = build_diversion_opportunity(
        filtered,
        material_columns,
        [],
        business_column,
        jurisdiction_field,
        business_group_field,
        address_column,
        zip_column,
    )
    opportunity, material_detail, calibration_factors = apply_opportunity_model_mode(
        raw_opportunity,
        raw_material_detail,
        campaign_controls["opportunity_model_mode"],
    )
    campaign_geography = campaign_controls["geography"]
    block_lookup = None
    campaign_block_groups = None
    if campaign_geography == "Census block group":
        try:
            with st.spinner("Preparing campaign block groups..."):
                block_group_path = ensure_census_block_group_zip(DEFAULT_TIGER_YEAR, DEFAULT_STATE_FIPS)
                campaign_block_groups = load_block_groups_from_file(str(block_group_path), DEFAULT_COUNTY_FIPS)
                coord_lookup_source = data[["_business_row_id", latitude_column, longitude_column]].rename(
                    columns={latitude_column: "latitude", longitude_column: "longitude"}
                )
                block_group_cache_key = "|".join(campaign_block_groups["GEOID"].astype(str).sort_values().tolist())
                block_lookup = build_business_block_group_lookup(
                    coord_lookup_source,
                    campaign_block_groups,
                    block_group_cache_key,
                )
        except Exception as exc:
            st.warning("Census block groups could not be prepared. The campaign builder is using countywide geography.")
            st.caption(str(exc))
            campaign_geography = "Countywide"

    campaign_rows = build_campaign_business_table(
        opportunity,
        material_detail,
        filtered,
        latitude_column,
        longitude_column,
        campaign_controls["materials"],
        campaign_controls["destinations"],
        campaign_controls["business_groups"],
        campaign_controls["min_tons"],
    )
    campaign_rows = campaign_geography_label(campaign_rows, campaign_geography, block_lookup)
    area_summary = campaign_area_summary(campaign_rows)

    st.subheader("Outreach Campaign Builder")
    st.caption(
        "Build a campaign list from modeled landfill material opportunity. Filters in the sidebar define the material, "
        "destination pathway, business group, geography, and minimum tons threshold."
    )
    st.caption(opportunity_model_note(campaign_controls["opportunity_model_mode"]))

    if campaign_rows.empty:
        st.warning("No businesses match the current campaign settings.")
        st.stop()

    area_options = area_summary["Campaign Geography"].tolist() if not area_summary.empty else []
    selected_campaign_areas = st.multiselect(
        "Focus campaign areas",
        area_options,
        default=[],
        help="Leave blank to include all areas matching the sidebar settings.",
    )
    campaign_display = (
        campaign_rows[campaign_rows["Campaign Geography"].isin(selected_campaign_areas)].copy()
        if selected_campaign_areas
        else campaign_rows.copy()
    )
    display_area_summary = campaign_area_summary(campaign_display)

    total_campaign_tons = float(campaign_display["Campaign Opportunity Tons"].sum())
    total_campaign_businesses = int(campaign_display["_business_row_id"].nunique())
    top_area = (
        display_area_summary.iloc[0]["Campaign Geography"]
        if not display_area_summary.empty
        else "None"
    )
    top_material = most_common_text(campaign_display["Top Campaign Material"]) if not campaign_display.empty else "None"

    metric_cols = st.columns(4)
    metric_cols[0].metric("Campaign tons", f"{total_campaign_tons:,.1f}")
    metric_cols[1].metric("Target businesses", f"{total_campaign_businesses:,}")
    metric_cols[2].metric("Top area", str(top_area)[:30])
    metric_cols[3].metric("Top material", str(top_material)[:30])

    boundary_layers = []
    requested_boundaries = []
    if (
        campaign_geography == "Census block group"
        and campaign_block_groups is not None
        and "Campaign Geography ID" in campaign_display.columns
    ):
        selected_geoids = set(campaign_display["Campaign Geography ID"].dropna().astype(str))
        block_layer_frame = campaign_block_groups[campaign_block_groups["GEOID"].astype(str).isin(selected_geoids)].copy()
        if not block_layer_frame.empty:
            block_layer_frame["boundary_name"] = block_layer_frame.get("NAMELSAD", block_layer_frame["GEOID"]).astype(str)
            block_layer_frame["boundary_type"] = "Campaign block group"
            boundary_layers.append(
                boundary_layer(block_layer_frame, "campaign-block-groups", [35, 105, 154, 210], [76, 137, 73, 22])
            )
            requested_boundaries.append("Census block groups")

    if campaign_display.empty:
        st.warning("No businesses remain after the focus-area selection.")
    else:
        render_diversion_map_legend(campaign_controls["destinations"], requested_boundaries)
        st.pydeck_chart(
            build_campaign_map(campaign_display, boundary_layers),
            width="stretch",
            height=620,
            key=map_component_key("outreach_campaign_map", campaign_display),
        )

    st.subheader("Ranked Campaign Businesses")
    ranked_columns = [
        column
        for column in [
            "Business",
            "Campaign Opportunity Tons",
            "Campaign Opportunity Share",
            "Top Campaign Material",
            "Top Campaign Destination",
            "Materials",
            "Preferred Destinations",
            "Campaign Geography",
            "Business Group",
            "Jurisdiction",
            "ZIP Code",
            "Hauler",
            "Phone",
            "Website",
            "Address",
            "Landfill Tons",
        ]
        if column in campaign_display.columns
    ]
    st.dataframe(
        campaign_display[ranked_columns].head(campaign_controls["top_n"]),
        width="stretch",
        height=410,
        hide_index=True,
        column_config={
            "Campaign Opportunity Tons": st.column_config.NumberColumn(format="%.1f"),
            "Campaign Opportunity Share": st.column_config.NumberColumn(format="%.1f%%"),
            "Landfill Tons": st.column_config.NumberColumn(format="%.1f"),
        },
    )
    st.download_button(
        "Export ranked campaign businesses",
        data=campaign_display[ranked_columns].to_csv(index=False).encode("utf-8"),
        file_name="outreach_campaign_businesses.csv",
        mime="text/csv",
    )

    st.subheader("Outreach Contact Kit")
    st.caption(
        "Exports are generated for the ranked target count above and require planner review before use. "
        "The app does not send messages, scrape contacts, or add people to a mailing list."
    )
    outreach_targets = campaign_display.head(campaign_controls["top_n"]).copy()
    channel_exports = outreach_channel_exports(outreach_targets)
    channel_metrics = st.columns(3)
    channel_metrics[0].metric("Phone-ready businesses", f"{len(channel_exports['phone']):,}")
    channel_metrics[1].metric("Mail-ready businesses", f"{len(channel_exports['mail']):,}")
    channel_metrics[2].metric("Email-ready businesses", f"{len(channel_exports['email']):,}")
    st.caption(
        "Email-ready requires an imported valid business email address. The current packaged workbook has no email field, "
        "so email exports remain empty until an authorized source supplies one."
    )
    contact_tabs = st.tabs(["Phone book", "Mailing list", "Email review list"])
    with contact_tabs[0]:
        phone_book = channel_exports["phone"]
        st.dataframe(phone_book, width="stretch", height=300, hide_index=True)
        st.download_button(
            "Download phone book",
            data=phone_book.to_csv(index=False).encode("utf-8"),
            file_name="outreach_phone_book.csv",
            mime="text/csv",
        )
    with contact_tabs[1]:
        mailing_list = channel_exports["mail"]
        st.dataframe(mailing_list, width="stretch", height=300, hide_index=True)
        st.download_button(
            "Download envelope mailing list",
            data=mailing_list.to_csv(index=False).encode("utf-8"),
            file_name="outreach_envelope_mailing_list.csv",
            mime="text/csv",
        )
    with contact_tabs[2]:
        email_list = channel_exports["email"]
        st.dataframe(email_list, width="stretch", height=300, hide_index=True)
        st.download_button(
            "Download email review list",
            data=email_list.to_csv(index=False).encode("utf-8"),
            file_name="outreach_email_review_list.csv",
            mime="text/csv",
        )

    area_tab, material_tab = st.tabs(["Area summary", "Material summary"])
    with area_tab:
        if display_area_summary.empty:
            st.warning("No area summary is available.")
        else:
            st.dataframe(
                display_area_summary.head(50),
                width="stretch",
                height=320,
                hide_index=True,
                column_config={
                    "Campaign Opportunity Tons": st.column_config.NumberColumn(format="%.1f"),
                    "Businesses": st.column_config.NumberColumn(format="%d"),
                },
            )
            st.download_button(
                "Export campaign area summary",
                data=display_area_summary.to_csv(index=False).encode("utf-8"),
                file_name="outreach_campaign_area_summary.csv",
                mime="text/csv",
            )
    with material_tab:
        material_summary = (
            campaign_display.groupby(["Top Campaign Material", "Top Campaign Destination"], dropna=False)
            .agg(
                **{
                    "Campaign Opportunity Tons": ("Campaign Opportunity Tons", "sum"),
                    "Businesses": ("_business_row_id", "nunique"),
                    "Top Business Group": ("Business Group", most_common_text),
                    "Top Geography": ("Campaign Geography", most_common_text),
                }
            )
            .reset_index()
            .sort_values("Campaign Opportunity Tons", ascending=False)
        )
        st.dataframe(
            material_summary.head(50),
            width="stretch",
            height=320,
            hide_index=True,
            column_config={
                "Campaign Opportunity Tons": st.column_config.NumberColumn(format="%.1f"),
                "Businesses": st.column_config.NumberColumn(format="%d"),
            },
        )
        st.download_button(
            "Export campaign material summary",
            data=material_summary.to_csv(index=False).encode("utf-8"),
            file_name="outreach_campaign_material_summary.csv",
            mime="text/csv",
        )

elif dashboard == "Circular economy marketplace":
    zip_column = zipcode_display_column(filtered)
    selected_marketplace_materials = [
        marketplace_controls["material_lookup"][label]
        for label in marketplace_controls["material_labels"]
        if label in marketplace_controls["material_lookup"]
    ]
    if not selected_marketplace_materials:
        selected_marketplace_materials = sorted(material_columns)

    marketplace_geography = marketplace_controls["geography"]
    marketplace_block_lookup = None
    marketplace_block_groups = None
    if marketplace_geography == "Census block group":
        try:
            with st.spinner("Preparing marketplace block groups..."):
                block_group_path = ensure_census_block_group_zip(DEFAULT_TIGER_YEAR, DEFAULT_STATE_FIPS)
                marketplace_block_groups = load_block_groups_from_file(str(block_group_path), DEFAULT_COUNTY_FIPS)
                coord_lookup_source = data[["_business_row_id", latitude_column, longitude_column]].rename(
                    columns={latitude_column: "latitude", longitude_column: "longitude"}
                )
                block_group_cache_key = "|".join(marketplace_block_groups["GEOID"].astype(str).sort_values().tolist())
                marketplace_block_lookup = build_business_block_group_lookup(
                    coord_lookup_source,
                    marketplace_block_groups,
                    block_group_cache_key,
                )
        except Exception as exc:
            st.warning("Census block group marketplace areas could not be prepared. Falling back to jurisdiction.")
            st.caption(str(exc))
            marketplace_geography = "Jurisdiction"

    area_series = circular_exchange_area_series(
        filtered,
        marketplace_geography,
        marketplace_block_lookup,
        zip_column,
        jurisdiction_field,
    )
    base_businesses = marketplace_base_business_frame(
        filtered,
        latitude_column,
        longitude_column,
        business_column,
        business_group_field,
        jurisdiction_field,
        zip_column,
        area_series,
    )
    supplier_rows = build_marketplace_supplier_rows(
        filtered,
        material_columns,
        selected_marketplace_materials,
        area_series,
        business_column,
        business_group_field,
        jurisdiction_field,
        marketplace_controls["min_supplier_tons"],
    )
    user_rows = build_marketplace_user_rows(
        base_businesses,
        selected_marketplace_materials,
        marketplace_controls["user_groups"],
    )
    match_summary = marketplace_match_summary(supplier_rows, user_rows)

    st.subheader("Circular Economy Marketplace Prototype")
    st.caption(
        "This prototype maps likely material suppliers and potential users. Suppliers are based on modeled landfill "
        "disposal of selected materials; potential users are inferred from business group, NAICS/SIC descriptions, "
        "line of business, and business names."
    )

    area_options = match_summary["Marketplace Area"].tolist() if not match_summary.empty else []
    selected_marketplace_areas = st.multiselect(
        "Focus marketplace areas",
        area_options,
        default=[],
        help="Leave blank to include every marketplace area in the current slice.",
    )
    if selected_marketplace_areas:
        supplier_display = supplier_rows[supplier_rows["Exchange Area"].isin(selected_marketplace_areas)].copy()
        user_display = user_rows[user_rows["Marketplace Area"].isin(selected_marketplace_areas)].copy()
        match_display = match_summary[match_summary["Marketplace Area"].isin(selected_marketplace_areas)].copy()
    else:
        supplier_display = supplier_rows.copy()
        user_display = user_rows.copy()
        match_display = match_summary.copy()

    map_points = marketplace_map_frame(supplier_display, user_display, base_businesses)

    total_supplier_tons = float(supplier_display["Supplier Tons"].sum()) if not supplier_display.empty else 0.0
    supplier_count = int(supplier_display["_business_row_id"].nunique()) if not supplier_display.empty else 0
    user_count = int(user_display["_business_row_id"].nunique()) if not user_display.empty else 0
    viable_area_count = int((match_display["Potential Users"] > 0).sum()) if not match_display.empty else 0
    metric_cols = st.columns(4)
    metric_cols[0].metric("Supplier tons", f"{total_supplier_tons:,.1f}")
    metric_cols[1].metric("Likely suppliers", f"{supplier_count:,}")
    metric_cols[2].metric("Potential users", f"{user_count:,}")
    metric_cols[3].metric("Areas with both", f"{viable_area_count:,}")

    if map_points.empty:
        st.warning("No marketplace suppliers or users match the current settings.")
    else:
        render_map_legend(
            "Marketplace legend",
            [
                ("Likely supplier", [76, 137, 73, 210], "dot"),
                ("Potential user", [35, 105, 154, 205], "dot"),
                ("Supplier + potential user", [123, 88, 159, 220], "dot"),
            ],
            note="Dot role is inferred from modeled material supply and industry-text demand proxies.",
        )
        st.pydeck_chart(
            build_marketplace_map(map_points),
            width="stretch",
            height=640,
            key=map_component_key("circular_marketplace_map", map_points),
        )

    opportunity_tab, supplier_tab, user_tab, assumptions_tab = st.tabs(
        ["Exchange opportunities", "Likely suppliers", "Potential users", "Assumptions"]
    )
    with opportunity_tab:
        if match_display.empty:
            st.warning("No exchange opportunity rows are available.")
        else:
            st.dataframe(
                match_display.head(marketplace_controls["top_n"]),
                width="stretch",
                height=390,
                hide_index=True,
                column_config={
                    "Supplier Tons": st.column_config.NumberColumn(format="%.1f"),
                    "Marketplace Score": st.column_config.NumberColumn(format="%.1f"),
                },
            )
            st.download_button(
                "Export marketplace opportunities",
                data=match_display.to_csv(index=False).encode("utf-8"),
                file_name="circular_marketplace_opportunities.csv",
                mime="text/csv",
            )

    with supplier_tab:
        if supplier_display.empty:
            st.warning("No likely suppliers match the current settings.")
        else:
            supplier_columns = [
                "Business",
                "Supplier Tons",
                "Material",
                "Material Group",
                "Exchange Area",
                "Business Group",
                "Jurisdiction",
                "Industry Description",
            ]
            st.dataframe(
                supplier_display[[column for column in supplier_columns if column in supplier_display.columns]]
                .head(marketplace_controls["top_n"]),
                width="stretch",
                height=390,
                hide_index=True,
                column_config={"Supplier Tons": st.column_config.NumberColumn(format="%.1f")},
            )
            st.download_button(
                "Export likely suppliers",
                data=supplier_display.to_csv(index=False).encode("utf-8"),
                file_name="circular_marketplace_suppliers.csv",
                mime="text/csv",
            )

    with user_tab:
        if user_display.empty:
            st.warning("No potential users match the current settings.")
        else:
            user_columns = [
                "Business",
                "Material",
                "Material Group",
                "Marketplace Area",
                "Business Group",
                "Jurisdiction",
                "Potential User Evidence",
                "User Match Score",
            ]
            st.dataframe(
                user_display[[column for column in user_columns if column in user_display.columns]]
                .head(marketplace_controls["top_n"]),
                width="stretch",
                height=390,
                hide_index=True,
                column_config={"User Match Score": st.column_config.NumberColumn(format="%.1f")},
            )
            st.download_button(
                "Export potential users",
                data=user_display.to_csv(index=False).encode("utf-8"),
                file_name="circular_marketplace_users.csv",
                mime="text/csv",
            )

    with assumptions_tab:
        st.markdown(
            """
            **How this prototype classifies marketplace roles**

            - **Likely suppliers** are businesses with modeled landfill-disposed tons of the selected material.
            - **Potential users** are inferred from business group, NAICS/SIC descriptions, line of business, and business names.
            - The match does not prove that a business can technically use the material; it identifies where planner follow-up may be worthwhile.
            - Marketplace score increases when a geography has more supplier tons, more supplier businesses, and more inferred potential users.
            - The next validation step is to replace keyword demand proxies with confirmed procurement needs, reuse specifications, or SIC/NAICS process rules.
            """
        )
        keyword_rows = [
            {"Material Group": group, "User Keywords": ", ".join(keywords)}
            for group, keywords in MARKETPLACE_USER_KEYWORDS.items()
        ]
        st.dataframe(pd.DataFrame(keyword_rows), width="stretch", hide_index=True)

else:
    zip_column = zipcode_display_column(study_filtered)
    opportunity, material_detail = build_diversion_opportunity(
        study_filtered,
        material_columns,
        [],
        business_column,
        jurisdiction_field,
        business_group_field,
        address_column,
        zip_column,
    )
    group_comparison = material_group_composition(study_filtered, material_columns)
    pathway_comparison = model_pathway_composition(opportunity)
    detail_composition = material_group_detail_composition(study_filtered, material_columns)

    model_landfill = float(opportunity["Landfill Tons"].sum()) if not opportunity.empty else 0.0
    model_organics_share = float(
        group_comparison.loc[group_comparison["Material Group"] == "Organics", "Model Share"].sum()
    )
    study_organics_share = ICI_MATERIAL_GROUP_SHARES["Organics"]
    organics_gap = model_organics_share - study_organics_share
    largest_gap_row = group_comparison.sort_values("Abs Difference (pp)", ascending=False).head(1)
    largest_gap = (
        f"{largest_gap_row.iloc[0]['Material Group']} ({largest_gap_row.iloc[0]['Difference (pp)']:+.1f} pp)"
        if not largest_gap_row.empty
        else "None"
    )
    raw_divertible_share = (
        float(opportunity[DIVERTIBLE_DESTINATIONS].sum(axis=1).sum()) / model_landfill * 100
        if model_landfill > 0 and not opportunity.empty
        else 0.0
    )
    landfill_ton_gap_pct = (
        (model_landfill - STUDY_SECTOR_BASIS_ICI_REFUSE_TONS) / STUDY_SECTOR_BASIS_ICI_REFUSE_TONS * 100
        if STUDY_SECTOR_BASIS_ICI_REFUSE_TONS > 0
        else 0.0
    )
    system_accuracy = max(0.0, 100 - abs(landfill_ton_gap_pct))

    metric_cols = st.columns(7)
    metric_cols[0].metric("Model landfill tons", f"{model_landfill:,.1f}")
    metric_cols[1].metric(
        "System accuracy",
        f"{system_accuracy:.0f}%",
        delta=f"{landfill_ton_gap_pct:+.1f}% tons gap",
        delta_color="inverse",
        help="100% minus the absolute percent difference between model landfill tons and the 34,280-ton ICI study sector basis.",
    )
    metric_cols[2].metric("Study sector basis", f"{STUDY_SECTOR_BASIS_ICI_REFUSE_TONS:,.0f}")
    metric_cols[3].metric("Study table basis", f"{STUDY_TABLE_TOTAL_ICI_REFUSE_TONS:,.0f}")
    metric_cols[4].metric("Raw model divertible", f"{raw_divertible_share:.1f}%")
    metric_cols[5].metric("Study pathway divertible", f"{STUDY_DIVERTIBLE_SHARE:.1f}%")
    metric_cols[6].metric("Organics gap", f"{organics_gap:+.1f} pp")

    st.info(
        "This page compares the workbook's calculated landfill material composition against the 2025 SLO County ICI "
        "waste characterization study. Large gaps are model-diagnostic signals, not planner-facing claims."
    )
    if study_excluded_rows:
        st.caption(
            f"Validation metrics exclude {study_excluded_rows:,} multifamily row(s) from the current slice because "
            "multifamily generators are useful for planning but outside the ICI study basis."
        )
    st.caption(
        f"Full report denominator note: Table 2-4 lists Commercial ICI as "
        f"{STUDY_SECTOR_BASIS_ICI_REFUSE_TONS:,.0f} 2023 tons, while Table 4-2's ICI composition "
        f"table sums to {STUDY_TABLE_TOTAL_ICI_REFUSE_TONS:,.0f} tons. The comparison uses shares for calibration "
        "and shows both ton conversions where useful."
    )
    st.caption(f"Largest material-group composition gap: {largest_gap}.")

    group_tab, pathway_tab, material_tab, note_tab = st.tabs(
        ["Material groups", "Diversion pathways", "Model materials", "Interpretation notes"]
    )
    with group_tab:
        st.altair_chart(comparison_chart(group_comparison, "Material Group"), width="stretch")
        st.dataframe(
            group_comparison[
                [
                    "Material Group",
                    "2025 Study Share",
                    "Model Share",
                    "Difference (pp)",
                    "Model Tons",
                    "Study Tons (Sector Basis)",
                    "Study Tons (Table Basis)",
                ]
            ],
            width="stretch",
            height=330,
            hide_index=True,
            column_config={
                "2025 Study Share": st.column_config.NumberColumn(format="%.1f%%"),
                "Model Share": st.column_config.NumberColumn(format="%.1f%%"),
                "Difference (pp)": st.column_config.NumberColumn(format="%+.1f"),
                "Model Tons": st.column_config.NumberColumn(format="%.1f"),
                "Study Tons (Sector Basis)": st.column_config.NumberColumn(format="%.0f"),
                "Study Tons (Table Basis)": st.column_config.NumberColumn(format="%.0f"),
            },
        )

    with pathway_tab:
        st.altair_chart(comparison_chart(pathway_comparison, "Pathway"), width="stretch")
        st.dataframe(
            pathway_comparison[
                [
                    "Pathway",
                    "2025 Study Share",
                    "Model Share",
                    "Difference (pp)",
                    "Model Tons",
                    "Study Tons (Sector Basis)",
                    "Study Tons (Table Basis)",
                ]
            ],
            width="stretch",
            height=260,
            hide_index=True,
            column_config={
                "2025 Study Share": st.column_config.NumberColumn(format="%.1f%%"),
                "Model Share": st.column_config.NumberColumn(format="%.1f%%"),
                "Difference (pp)": st.column_config.NumberColumn(format="%+.1f"),
                "Model Tons": st.column_config.NumberColumn(format="%.1f"),
                "Study Tons (Sector Basis)": st.column_config.NumberColumn(format="%.0f"),
                "Study Tons (Table Basis)": st.column_config.NumberColumn(format="%.0f"),
            },
        )
        st.caption(
            "Pathway comparison aligns study categories into the dashboard's planning streams: "
            "processable organics plus donatable food are grouped together, and third-party diversion includes "
            "third-party outlets, HHW/e-waste, and C&D processing."
        )

    with material_tab:
        st.dataframe(
            detail_composition.head(40),
            width="stretch",
            height=430,
            hide_index=True,
            column_config={
                "Model Tons": st.column_config.NumberColumn(format="%.1f"),
                "Model Share": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    with note_tab:
        st.markdown(
            """
            **Working hypotheses for current model drift**

            1. The destination stream view is broader than the material group view. Curbside organics includes food, yard waste, composite organics, and compostable paper, while the study's Organics pie slice is a material group.
            2. The workbook appears to spread profile-based material fractions across nearly every positive-landfill business, which creates tiny positive amounts for many materials and destroys real-world sparsity.
            3. The raw model overweights named divertible categories and underweights mixed residue / not-readily-recoverable material. That is why the model's Other share is much lower than the study.
            4. Some crosswalk choices are deliberately optimistic, especially composite organics and compostable paper. Those may need an acceptability factor before they become outreach-ready opportunity.
            5. The model and study may have different scopes, denominators, and years: the full report lists Commercial ICI as 34,280 tons in the sector-basis table, while the ICI composition table sums to 57,705 tons. Until that is reconciled with IWMA/MSW Consultants, percentages are safer than study-derived tonnage.
            """
        )

loading_overlay.empty()
