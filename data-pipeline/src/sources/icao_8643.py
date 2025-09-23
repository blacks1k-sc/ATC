"""
ICAO 8643 aircraft type data loader with real global CSV sources + fallback to planes.dat.
"""

import csv
import os
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

from ..models import TypeSpec, EngineSpec

# ------------------------------------------------------------------------------
# Paths & constants
# ------------------------------------------------------------------------------
CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

OPENFLIGHTS_PLANES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/planes.dat"
PLANES_CACHE = CACHE_DIR / "planes.dat"

ICAO_8643_URL_ENV = "ICAO_8643_URL"
ICAO_8643_CACHE = CACHE_DIR / "icao_8643.csv"

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


# ------------------------------------------------------------------------------
# Downloads
# ------------------------------------------------------------------------------
def _load_local_csv(path_like: str) -> str:
    """Load a local CSV file and copy it to cache."""
    p = Path(path_like.replace("file://", ""))
    p = p.resolve()
    if not p.exists():
        raise FileNotFoundError(f"Local ICAO 8643 CSV not found: {p}")
    # ensure cached copy lives at CACHE_DIR/icao_8643.csv
    ICAO_8643_CACHE.write_bytes(p.read_bytes())
    logger.info(f"Copied local ICAO 8643 CSV from {p} to {ICAO_8643_CACHE}")
    return str(ICAO_8643_CACHE)


def download_icao_8643_data(url: str) -> str:
    """
    Download ICAO 8643 CSV from the provided URL into cache and return its path.
    Handles both HTTP(S) URLs and local file paths.
    """
    parsed = urlparse(url)
    if parsed.scheme in ("file", ""):
        return _load_local_csv(url)
    
    try:
        logger.info(f"Downloading ICAO 8643 data from: {url}")
        response = requests.get(url, timeout=45)
        response.raise_for_status()
        ICAO_8643_CACHE.write_text(response.text, encoding="utf-8")
        logger.info(f"Cached ICAO 8643 data to {ICAO_8643_CACHE}")
        return str(ICAO_8643_CACHE)
    except Exception as e:
        logger.warning(f"Failed to download ICAO 8643 data: {e}")
        raise


def _download_planes_dat() -> Optional[Path]:
    """
    Download OpenFlights planes.dat into cache and return its path (or None on failure).
    """
    try:
        logger.info(f"Downloading planes.dat from: {OPENFLIGHTS_PLANES_URL}")
        r = requests.get(OPENFLIGHTS_PLANES_URL, timeout=30)
        r.raise_for_status()
        PLANES_CACHE.write_bytes(r.content)
        logger.info(f"Saved planes.dat to {PLANES_CACHE}")
        return PLANES_CACHE
    except Exception as e:
        logger.warning(f"Failed to download planes.dat: {e}")
        return None


# ------------------------------------------------------------------------------
# Fallback loader (planes.dat)
# ------------------------------------------------------------------------------
def _load_types_from_planes_dat() -> List[TypeSpec]:
    """
    Fallback loader using OpenFlights planes.dat (Name, IATA, ICAO).
    Only the ICAO type code (3rd column) is trusted/used.
    Other fields (wake/engines/dimensions/mtow) remain None and will be filtered out.
    This is only used to expand the list of known ICAO type codes.
    """
    if not PLANES_CACHE.exists():
        if _download_planes_dat() is None:
            logger.error("No planes.dat available (download failed).")
            return []

    types: List[TypeSpec] = []
    seen: Set[str] = set()

    with PLANES_CACHE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 3:
                continue
            icao = (row[2] or "").strip().upper()
            if not icao or icao in ("\\N", "NULL"):
                continue
            if icao in seen:
                continue
            seen.add(icao)
            types.append(
                TypeSpec(
                    icao_type=icao,
                    wake=None,  # Will be filtered out - no guessing
                    engines=None,  # Will be filtered out - no guessing
                    dimensions=None,
                    mtow_kg=None,
                )
            )

    logger.info(f"Loaded {len(types)} ICAO type codes from planes.dat (fallback - incomplete data)")
    return types


# ------------------------------------------------------------------------------
# ICAO 8643 CSV loader
# ------------------------------------------------------------------------------
def load_icao_8643_data(csv_path: Optional[str] = None) -> List[TypeSpec]:
    """
    Preferred: load ICAO 8643 CSV (via env URL or cache file).
    Fallback:  load OpenFlights planes.dat for ICAO type codes only.
    """
    # 1) Resolve preferred CSV path
    if csv_path is None:
        url = os.getenv(ICAO_8643_URL_ENV)
        if url:
            try:
                csv_path = download_icao_8643_data(url)
            except Exception:
                csv_path = None  # fall through to cache/fallback
        if csv_path is None and ICAO_8643_CACHE.exists():
            csv_path = str(ICAO_8643_CACHE)

    # 2) If CSV available, parse ICAO 8643 data
    if csv_path and os.path.exists(csv_path):
        logger.info(f"Loading ICAO 8643 data from: {csv_path}")

        types: List[TypeSpec] = []
        seen_types: Set[str] = set()
        skipped = 0

        with open(csv_path, "r", encoding="utf-8") as f:
            sample = f.read(1024)
            f.seek(0)
            delimiter = "," if "," in sample else "\t"
            reader = csv.DictReader(f, delimiter=delimiter)

            for row_num, row in enumerate(reader, 1):
                try:
                    icao_type = _extract_field(row, [
                        "Type Designator", "Type", "Aircraft Type", "AircraftType",
                        "icao_type", "ICAO_Type", "Designator", "TypeDesignator",
                    ])
                    wake = _extract_field(row, [
                        "WTC", "Wake", "Wake Category", "WakeCategory", "wake",
                        "Wake_Category", "WakeCategoryCode", "WakeCode",
                    ])
                    engines_count = _extract_field(row, [
                        "Engines", "Engine Count", "EngineCount", "engines_count",
                        "Engine_Count", "EnginesCount", "NoEngines", "EngineNumber",
                    ])
                    engines_type = _extract_field(row, [
                        "Engine Type", "EngineType", "Engine", "engines_type",
                        "Engine_Type", "EngineCategory", "EngineClass",
                    ])

                    # Validate ICAO type
                    if not icao_type or len(icao_type.strip()) < 3:
                        logger.debug(f"Row {row_num}: Invalid ICAO type: {icao_type}")
                        skipped += 1
                        continue
                    icao_type = icao_type.strip().upper()

                    # Dedup
                    if icao_type in seen_types:
                        skipped += 1
                        continue

                    # Validate wake - must be present and valid
                    if not wake:
                        logger.debug(f"Row {row_num}: Missing wake category for {icao_type}")
                        skipped += 1
                        continue
                    wake = wake.strip().upper()
                    if wake not in {"L", "M", "H", "J"}:
                        logger.debug(f"Row {row_num}: Invalid wake category '{wake}' for {icao_type}")
                        skipped += 1
                        continue

                    # Validate engines count - must be present and valid
                    if not engines_count:
                        logger.debug(f"Row {row_num}: Missing engine count for {icao_type}")
                        skipped += 1
                        continue
                    try:
                        engines_count = int(engines_count)
                        if engines_count < 1:
                            logger.debug(f"Row {row_num}: Invalid engine count {engines_count} for {icao_type}")
                            skipped += 1
                            continue
                    except (ValueError, TypeError):
                        logger.debug(f"Row {row_num}: Invalid engine count '{engines_count}' for {icao_type}")
                        skipped += 1
                        continue

                    # Validate engines type - must be present and valid
                    if not engines_type:
                        logger.debug(f"Row {row_num}: Missing engine type for {icao_type}")
                        skipped += 1
                        continue
                    engines_type_norm = _normalize_engine_type(engines_type.strip().upper())
                    if not engines_type_norm:
                        logger.debug(f"Row {row_num}: Unknown engine type '{engines_type}' for {icao_type}")
                        skipped += 1
                        continue

                    engines = EngineSpec(count=engines_count, type=engines_type_norm)
                    types.append(
                        TypeSpec(
                            icao_type=icao_type,
                            wake=wake,
                            engines=engines,
                            dimensions=None,  # to be enriched by OurAirports
                            mtow_kg=None,     # to be enriched by OurAirports
                        )
                    )
                    seen_types.add(icao_type)

                except Exception as e:
                    logger.debug(f"Row {row_num}: Error: {e}")
                    skipped += 1
                    continue

        logger.info(f"Loaded {len(types)} unique ICAO 8643 types, skipped {skipped} rows")
        return types

    # 3) Fallback to planes.dat if no CSV available
    logger.warning("No ICAO 8643 CSV available. Falling back to planes.dat.")
    types = _load_types_from_planes_dat()
    if not types:
        raise FileNotFoundError(
            "No ICAO 8643 data and planes.dat fallback failed. "
            "Set ICAO_8643_URL or ensure cache/planes.dat is present."
        )
    return types


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _extract_field(row: Dict[str, str], field_names: List[str]) -> Optional[str]:
    """Extract field value using multiple possible field names."""
    for name in field_names:
        if name in row and row[name] and row[name].strip():
            return row[name].strip()
    return None


def _normalize_engine_type(engine_type: str) -> Optional[str]:
    """Normalize engine type to enum values."""
    jet_variants = {"JET", "JET ENGINE", "TURBOJET", "TURBOFAN", "TURBO-FAN", "TURBO-JET", "FANJET"}
    turboprop_variants = {"TURBOPROP", "TURBO-PROP", "TURBOPROPELLER", "PROP", "PROPELLER"}
    piston_variants = {"PISTON", "PISTON ENGINE", "RECIPROCATING", "RECIP"}
    electric_variants = {"ELECTRIC", "ELECTRIC MOTOR", "BATTERY", "HYBRID"}

    if any(v in engine_type for v in jet_variants):
        return "JET"
    if any(v in engine_type for v in turboprop_variants):
        return "TURBOPROP"
    if any(v in engine_type for v in piston_variants):
        return "PISTON"
    if any(v in engine_type for v in electric_variants):
        return "ELECTRIC"
    return "OTHER"


def get_icao_8643_types() -> List[TypeSpec]:
    """Public entrypoint."""
    return load_icao_8643_data()