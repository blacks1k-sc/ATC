PY?=python3
VENV=.venv
PIP=$(VENV)/bin/pip
RUN=$(VENV)/bin/python

# Load environment variables if .env exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

setup:
	$(PY) -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

fetch:
	$(RUN) -c "from src.sources.icao_8643 import ensure_fallbacks; ensure_fallbacks()"
	$(RUN) -c "from src.sources.airlines import download_airlines_data; download_airlines_data()"

build:
	$(RUN) -m src.emit

generate:
	$(RUN) -m src.generate --n 50 --origin CYYZ

clean:
	rm -rf dist/ cache/
