# Aircraft Data Pipeline

A comprehensive data pipeline for collecting, processing, and generating aircraft type information from multiple sources.

## Overview

This pipeline aggregates aircraft specifications from various APIs and fallback sources, normalizes the data, and generates synthetic aircraft records for testing and simulation purposes.

## Features

- **Multi-source data collection**: API Ninjas, AeroDataBox, ICAO 8643, and OpenFlights data
- **Intelligent merging**: Combines data from multiple sources with precedence rules
- **Automatic derivations**: Calculates missing fields like wake categories and climb rates
- **Caching**: HTTP response caching with configurable TTL
- **Rate limiting**: Respects API rate limits with exponential backoff
- **Quality validation**: Ensures minimum data quality standards
- **Synthetic data generation**: Creates realistic aircraft records for testing

## Quick Start

### 1. Setup

```bash
cd data-pipeline
make setup
```

### 2. Configure API Keys

```bash
# Copy environment template
cp env.example .env

# Edit .env with your API keys
# API_NINJAS_KEY=your_api_ninjas_key_here
# AERODATABOX_KEY=your_rapidapi_key_here
```

### 3. Run Pipeline

```bash
# Set environment variables
export $(grep -v '^#' .env | xargs)

# Download fallback data
make fetch

# Build aircraft types database
make build

# Generate synthetic records
make generate
```

## Data Sources

### Primary Sources

1. **API Ninjas** - Primary source for aircraft specifications
   - Endpoint: `https://api.api-ninjas.com/v1/aircraft`
   - Requires: `API_NINJAS_KEY`
   - Provides: Dimensions, weights, speeds, engine info

2. **AeroDataBox** - Secondary source via RapidAPI
   - Endpoint: `https://aerodatabox.p.rapidapi.com/aircrafts/{manufacturer}/{model}`
   - Requires: `AERODATABOX_KEY`, `AERODATABOX_HOST`
   - Provides: Comprehensive aircraft specifications

### Fallback Sources

3. **ICAO 8643** - Wake categories and engine information
   - Local CSV file (if provided via `ICAO_8643_CSV`)
   - Provides: Wake categories, engine counts, engine types

4. **OpenFlights planes.dat** - ICAO type candidates
   - Auto-downloaded from GitHub
   - Provides: ICAO type designators, manufacturer/model guesses

5. **OpenFlights airlines.dat** - Airline information
   - Auto-downloaded from GitHub
   - Provides: Airline codes, names, countries

## Data Processing

### Source Precedence

1. **API Ninjas** (primary)
2. **AeroDataBox** (secondary)
3. **ICAO 8643** (fallback for wake/engines)
4. **Derived calculations** (final fallback)

### Automatic Derivations

- **Wake categories**: Derived from MTOW using ICAO standards
  - Light (L): < 7,000 kg
  - Medium (M): 7,000 - 136,000 kg
  - Heavy (H): ≥ 136,000 kg
  - Super (J): A380 special case

- **Climb rates**: Estimated based on engine type and MTOW
  - Base rates by engine type with MTOW scaling

- **Unit conversions**: Automatic conversion between units
  - lbs ↔ kg, ft ↔ m, nm ↔ km

### Quality Standards

Records must have:
- Wake category
- Engine type
- Maximum takeoff weight (MTOW)

Records missing these fields are excluded from the final dataset.

## Output Files

### `dist/aircraft_types.json`
Normalized aircraft type specifications with fields:
- `icao_type`: ICAO type designator
- `wake`: Wake turbulence category (L/M/H/J)
- `engines`: Engine specification (count, type)
- `dimensions`: Physical dimensions (length, wingspan, height)
- `mtow_kg`: Maximum takeoff weight
- `cruise_speed_kts`, `max_speed_kts`: Speed specifications
- `range_nm`: Range in nautical miles
- `ceiling_ft`: Service ceiling
- `climb_rate_fpm`: Estimated climb rate
- `takeoff_ground_run_ft`, `landing_ground_roll_ft`: Ground performance
- `engine_thrust_lbf`: Engine thrust
- `notes`: Source information

### `dist/airlines.json`
Airline information with fields:
- `icao`: ICAO airline code
- `iata`: IATA airline code
- `name`: Airline name
- `callsign`: Radio callsign
- `country`: Country of registration
- `active`: Active status

### `dist/meta.json`
Build metadata including:
- Build timestamp
- Record counts
- Source information
- Quality criteria

### `dist/sample_records.jsonl`
Synthetic aircraft records (one per line) with fields:
- `id`: Unique aircraft identifier
- `callsign`: Flight callsign
- `aircraft_type`: ICAO type designator
- `airline`: ICAO airline code
- `origin`, `destination`: Airport codes
- `position`: Lat/lon, altitude, heading, speed
- `status`: Flight status
- `timestamp`: Record timestamp

## Configuration

### Environment Variables

```bash
# API Keys
API_NINJAS_KEY=your_api_ninjas_key_here
AERODATABOX_KEY=your_rapidapi_key_here
AERODATABOX_HOST=aerodatabox.p.rapidapi.com

# Fallback Data
ICAO_8643_CSV=cache/icao_8643.csv
PLANES_DAT_URL=https://raw.githubusercontent.com/jpatokal/openflights/master/data/planes.dat

# Performance Tuning
HTTP_TIMEOUT=30
RATE_LIMIT_QPS=2
CACHE_TTL_HOURS=72
```

### Makefile Targets

- `make setup`: Create virtual environment and install dependencies
- `make fetch`: Download fallback data files
- `make build`: Build aircraft types database
- `make generate`: Generate synthetic records
- `make clean`: Remove generated files

## API Keys

### API Ninjas
1. Visit [api-ninjas.com](https://api-ninjas.com/api/aircraft)
2. Sign up for free account
3. Get API key from dashboard
4. Set `API_NINJAS_KEY` in `.env`

### AeroDataBox (RapidAPI)
1. Visit [RapidAPI AeroDataBox](https://rapidapi.com/aerodatabox/api/aerodatabox)
2. Subscribe to plan (free tier available)
3. Get API key from dashboard
4. Set `AERODATABOX_KEY` and `AERODATABOX_HOST` in `.env`

## Development

### Project Structure

```
data-pipeline/
├── README.md
├── .gitignore
├── Makefile
├── requirements.txt
├── env.example
├── cache/                # HTTP/cache files (git-ignored)
├── dist/                 # Outputs (git-ignored)
└── src/
    ├── __init__.py
    ├── models.py         # Pydantic data models
    ├── emit.py           # Main orchestration
    ├── generate.py       # CLI for synthetic data
    ├── sources/
    │   ├── __init__.py
    │   ├── api_ninjas.py
    │   ├── aerodatabox.py
    │   ├── icao_8643.py
    │   └── airlines.py
    └── utils/
        ├── __init__.py
        ├── http.py       # HTTP client with retries
        ├── cache.py      # JSON caching
        ├── derive.py     # Field derivations
        └── merge.py      # Data merging logic
```

### Adding New Sources

1. Create new module in `src/sources/`
2. Implement `fetch_by_model(manufacturer, model)` function
3. Return `TypeSpec` object with available data
4. Add to orchestration in `src/emit.py`

### Testing

```bash
# Test individual components
python -c "from src.sources.api_ninjas import fetch_by_model; print(fetch_by_model('Boeing', '737'))"

# Test full pipeline
make build
make generate --n 10
```

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify keys are set in `.env`
   - Check API key validity and quotas
   - Ensure no extra spaces in `.env` file

2. **No Data Found**
   - Check internet connection
   - Verify API endpoints are accessible
   - Review rate limiting settings

3. **Build Failures**
   - Check Python version (3.8+)
   - Verify all dependencies installed
   - Review error logs for specific issues

4. **Low Quality Results**
   - Increase `RATE_LIMIT_QPS` for better API coverage
   - Provide ICAO 8643 CSV for better fallback data
   - Check manufacturer/model name normalization

### Logs

The pipeline uses Python logging. Set log level for more details:

```bash
export PYTHONPATH=.
python -c "import logging; logging.basicConfig(level=logging.DEBUG); from src.emit import main; main()"
```

## License

This project is part of the ATC simulation system. See main project license for details.
