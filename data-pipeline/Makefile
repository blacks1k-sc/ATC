.PHONY: setup fetch build generate clean smoke help

# Default target
help:
	@echo "Available targets:"
	@echo "  setup    - Create virtual environment and install dependencies"
	@echo "  fetch    - Download and cache data from official sources"
	@echo "  build    - Generate aircraft_types.json and airlines.json from global data"
	@echo "  generate - Generate sample_records.jsonl (default: 50 records)"
	@echo "  smoke    - Test API Ninjas integration with a simple query"
	@echo "  clean    - Remove dist/ and cache/ directories"
	@echo "  help     - Show this help message"

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

fetch:
	@echo "Fetching data from official sources..."
	@echo "Note: ICAO 8643 data is now fetched via API Ninjas during build (no separate download needed)"
	.venv/bin/python -c "from src.sources.ourairports import download_ourairports_data; download_ourairports_data()"
	.venv/bin/python -c "from src.sources.airlines import download_airlines_data; download_airlines_data()"
	@echo "Data fetch completed. Files cached in cache/ directory."

build:
	@if [ -z "$$API_NINJAS_KEY" ] || [ "$$API_NINJAS_KEY" = "your_api_key_here" ]; then \
		echo "Error: API_NINJAS_KEY environment variable must be set to a valid API key"; \
		echo "Get your free API key at https://api-ninjas.com/"; \
		echo "Then run: export API_NINJAS_KEY=\"your_real_key\""; \
		exit 1; \
	fi
	.venv/bin/python -m src.emit

generate:
	.venv/bin/python -m src.generate --n 50 --origin CYYZ

smoke:
	.venv/bin/python -c "import os; from src.sources.api_ninjas import fetch_type_by_model_or_manufacturer as f; os.environ['API_NINJAS_KEY']=os.environ.get('API_NINJAS_KEY',''); print('Testing API Ninjas integration...'); result = f('A320', None); print(f'Found {len(result)} aircraft types for A320'); [print(f'  - {t.icao_type}: {t.engines.type} x{t.engines.count}, wake={t.wake}') for t in result]"

clean:
	rm -rf dist/ cache/
