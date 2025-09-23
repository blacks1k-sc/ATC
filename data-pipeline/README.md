# ATC Data Pipeline

A Python data pipeline that enriches aircraft types using API Ninjas and OurAirports data, validates with Pydantic, and generates synthetic aircraft records for ATC simulation.

## Features

- **Live API Integration**: Real-time aircraft data enrichment via API Ninjas Aircraft API
- **Intelligent Caching**: Caches API responses locally to minimize network calls and costs
- **Data Derivation**: Automatically derives wake categories and climb rates from MTOW and engine data
- **Validation**: Pydantic models ensure data integrity with robust error handling
- **Synthetic Generation**: Creates realistic aircraft records with unique registrations and ICAO24 codes
- **Geographic Routing**: YYZ-centric route generation with realistic positions
- **Rate Limiting**: Built-in API rate limiting and exponential backoff for reliable operation

## Output Files

- `dist/aircraft_types.json` - Global aircraft type specifications (thousands of types)
- `dist/airlines.json` - Global airline directory (thousands of airlines)
- `dist/sample_records.jsonl` - Synthetic aircraft records (one per line)
- `dist/meta.json` - Build metadata (timestamp, counts)

## Quick Start

```bash
# Setup environment
make setup

# Set your API keys (at least one required)
export API_NINJAS_KEY="YOUR_REAL_KEY"
export AERODATABOX_KEY="your_rapidapi_key_here"
export AERODATABOX_HOST="aerodatabox.p.rapidapi.com"

# Fetch data from official sources (optional - will auto-download if needed)
make fetch

# Build aircraft types and airlines data (uses API Ninjas)
make build

# Generate synthetic records
make generate

# Or generate custom amount
python -m src.generate --n 100 --origin CYYZ --op PASSENGER
```

### Complete Setup Example

```bash
# 1) Activate venv (if not already)
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 2) Set your API keys (at least one required)
export API_NINJAS_KEY="YOUR_REAL_KEY"
export AERODATABOX_KEY="your_rapidapi_key_here"
export AERODATABOX_HOST="aerodatabox.p.rapidapi.com"

# 3) Build data
make clean && make build && make generate
```

## Data Sources

The pipeline enriches aircraft data from multiple sources:

### Aircraft Type Enrichment (Multi-API)
- **Primary**: API Ninjas Aircraft API for real-time aircraft specifications
- **Secondary**: AeroDataBox API as fallback for missing data
- **Cached**: `cache/api_ninjas/` and `cache/aerodatabox/` directories with JSON responses
- **Query Method**: Uses `model=` and `manufacturer=` parameters (never `icao=`)
- **Rate Limiting**: 1-2 requests per second with exponential backoff
- **Fallback**: Comprehensive fallback data for common aircraft types

**⚠️ API Keys Required:**
- **API_NINJAS_KEY** environment variable (primary source)
- **AERODATABOX_KEY** and **AERODATABOX_HOST** environment variables (secondary fallback)
- Get your free API keys at [API Ninjas](https://api-ninjas.com/) and [AeroDataBox](https://rapidapi.com/aerodatabox/api/aerodatabox)
- API calls are cached to minimize costs and improve performance

**Data Enrichment Process:**
1. **Collect ICAO codes** from existing data, planes.dat, and OurAirports
2. **Query API Ninjas** for each ICAO type (cached responses reused)
3. **Query AeroDataBox** to fill gaps in API Ninjas data
4. **Derive missing data** using MTOW and engine information
5. **Enrich with OurAirports** for additional dimensions and specifications
6. **Validate and filter** to ensure complete wake and engine data

**Caching Behavior:**
- API responses cached in `cache/api_ninjas/` and `cache/aerodatabox/` as JSON files
- Cache keys based on manufacturer and model names
- Failed queries cached as empty objects to avoid retries
- Manual cache clearing: `rm -rf cache/api_ninjas/ cache/aerodatabox/`

**Data Derivation:**
- **Wake categories** derived from MTOW: <7t=L, 7-136t=M, >136t=H, special cases=J
- **Climb rates** estimated from engine type and MTOW with realistic scaling
- **Engine types** normalized to JET/TURBOPROP/PISTON/ELECTRIC categories

### OurAirports Aircraft Data
- **Primary**: OurAirports aircraft specifications database
- **Fallback**: Open source aircraft dimension databases
- **Cached**: `cache/ourairports_aircraft.csv`

### Global Airlines
- **Primary**: OurAirports airlines database
- **Fallback**: OpenFlights airlines data
- **Cached**: `cache/airlines.csv`

## Configuration

### Environment Variables

Required and optional configuration:

```bash
# Required: API Ninjas key for aircraft data enrichment
export API_NINJAS_KEY="your_api_key_here"

# Optional: Other data sources
export OURAIRPORTS_AIRCRAFT_CSV="path/to/ourairports_aircraft.csv"
export AIRLINES_CSV="path/to/airlines.csv"

# Optional: Random seed for reproducible generation
export RANDOM_SEED="42"
```

### Data Supply Methods

1. **Automatic Download** (default): Pipeline downloads from official sources
2. **Local CSV Files**: Place CSVs in `cache/` directory and set environment variables
3. **Custom Paths**: Use environment variables to point to any CSV location

### Cache Management

- Data is automatically cached in the `cache/` directory
- Cached files are reused on subsequent runs
- Use `make clean` to remove cached data and force re-download
- Cache files are git-ignored to avoid committing large datasets

## Project Structure

```
data-pipeline/
├── README.md
├── requirements.txt
├── Makefile
├── src/
│   ├── models.py          # Pydantic models
│   ├── sources/           # Data loaders
│   │   ├── icao_8643.py
│   │   ├── ourairports.py
│   │   └── airlines.py
│   ├── utils/             # Helper modules
│   │   ├── registries.py
│   │   ├── randomizers.py
│   │   └── geo.py
│   ├── emit.py            # Data joining and validation
│   └── generate.py        # CLI for synthetic generation
└── dist/                  # Output directory (git-ignored)
```

## Environment Variables

- `RANDOM_SEED`: Set for deterministic generation (default: 42)

## Requirements

- Python 3.8+
- pandas, pydantic, requests, beautifulsoup4, python-slugify, typer, rtoml

## Error Handling

The pipeline includes robust error handling:

- **API Failures**: Automatic retry with exponential backoff for API Ninjas requests
- **Rate Limiting**: Built-in rate limiting to respect API quotas (1-2 req/sec)
- **Cache Fallback**: Failed API queries are cached to avoid repeated failures
- **Data Derivation**: Missing wake categories and climb rates are derived from available data
- **Invalid Data**: Rows with missing or invalid fields are logged and skipped
- **Network Issues**: Automatic fallback to alternative data sources
- **Missing Files**: Graceful degradation with sample data for development
- **Validation Errors**: Pydantic validation ensures data integrity
- **Quality Control**: Pipeline fails if fewer than 10 aircraft types have complete wake/engine data

## New Features

### Multi-API Integration
- **Primary Source**: API Ninjas for real-time aircraft specifications
- **Secondary Fallback**: AeroDataBox to fill gaps in API Ninjas data
- **Model-Based Queries**: Uses `model=` and `manufacturer=` parameters (no more `icao=` calls)
- **Intelligent Caching**: Minimizes API calls and costs with separate cache directories
- **Smart Fallbacks**: Uses OurAirports and derived data when API data is incomplete
- **Rate Limiting**: Respects API quotas with built-in throttling and exponential backoff
- **Engine Inference**: Smart engine count inference when API doesn't provide it
- **Data Merging**: Seamlessly combines data from multiple APIs for comprehensive coverage

### Data Derivation
- **Wake Categories**: Automatically derived from MTOW and ICAO type
- **Climb Rates**: Estimated from engine type and aircraft weight
- **Engine Normalization**: Standardized engine type classification

### Enhanced Output
- **Climb Rate Data**: New `climb_rate_fpm` field in aircraft records
- **Larger Dataset**: More aircraft types through API enrichment
- **Better Coverage**: Improved data completeness through multiple sources

### Testing & Validation
- **Smoke Test**: Built-in API integration testing with `make smoke`
- **Acceptance Criteria**: Validates common aircraft types have complete data

## Performance

- **API Caching**: Responses cached locally to minimize network calls
- **Rate Limiting**: Built-in throttling prevents API quota exhaustion
- **Parallel Processing**: Large datasets are processed efficiently
- **Memory Efficient**: Streaming processing for large files
- **Logging**: Comprehensive logging for debugging and monitoring
