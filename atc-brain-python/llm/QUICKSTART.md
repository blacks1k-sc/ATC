# Quick Start Guide: Mistral-7B LLM Integration

## Prerequisites Checklist

### 1. Install Python Dependencies
```bash
cd atc-brain-python
pip install -r requirements.txt
```

### 2. Install Ollama
```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or visit: https://ollama.com/download
```

### 3. Pull Mistral-7B Model
```bash
ollama pull mistral
```

### 4. Verify Ollama Installation
```bash
ollama list
# Should show 'mistral' in the list

ollama run mistral "Hello"
# Should respond with a greeting
```

---

## Quick Start

### 1. Verify Integration
```bash
cd atc-brain-python
python verify_llm_integration.py
```

Expected output:
```
============================================================
Mistral-7B LLM Integration Verification
============================================================

Testing imports...
✓ llm_schemas imported successfully
✓ llm_prompts imported successfully
✓ safety_validator imported successfully
✓ llm_dispatcher imported successfully
✓ llm package exports working correctly

Testing schemas...
✓ AirClearance schema working correctly
✓ GroundClearance schema working correctly

Testing prompts...
✓ Air prompt generated correctly
✓ Ground prompt generated correctly

Checking Ollama installation...
✓ Ollama installed with Mistral model

============================================================
Verification Summary
============================================================
Imports             : ✓ PASS
Schemas             : ✓ PASS
Prompts             : ✓ PASS
Ollama              : ✓ PASS

✅ All verification tests passed!
The LLM integration is ready to use.
```

### 2. Ensure Services Are Running

**PostgreSQL**:
```bash
# Check if PostgreSQL is running
pg_isready

# Or start if needed
# macOS: brew services start postgresql
```

**Redis**:
```bash
# Check if Redis is running
redis-cli ping
# Should respond with: PONG

# Or start if needed
# macOS: brew services start redis
```

**ATC Engine**:
```bash
# The engine should be running and publishing events to Redis
# Check your existing engine launch script
```

### 3. Launch LLM Dispatcher
```bash
cd atc-brain-python
python launch_llm.py
```

Expected output:
```
============================================================
ATC LLM Dispatcher - Mistral-7B Integration
============================================================

✓ Ollama installed with Mistral model

2025-11-22 10:00:00 - INFO - Starting ATC LLM Dispatcher...
2025-11-22 10:00:00 - INFO - Initializing LLM Dispatcher...
2025-11-22 10:00:00 - INFO - Connected to Redis on channel 'atc:events'
2025-11-22 10:00:00 - INFO - Connected to PostgreSQL database
2025-11-22 10:00:00 - INFO - LLM Dispatcher initialized with Mistral-7B via Ollama
2025-11-22 10:00:00 - INFO - LLM Dispatcher running...
2025-11-22 10:00:00 - INFO - Listening for events: zone.boundary_crossed, clearance.completed, runway.landed, runway.vacated
```

---

## What to Expect

### Normal Operation

When aircraft cross zone boundaries:
```
INFO - Calling Air LLM for aircraft 123 (event: zone.boundary_crossed)
INFO - Calling Mistral-7B for Air clearance (aircraft 123)
INFO - Air clearance validation PASSED for aircraft 123 (VECTORING)
INFO - Generated valid air clearance for aircraft 123: VECTORING
INFO - Applied validated clearance to aircraft 123: VECTORING (updates: ['target_altitude_ft', 'target_speed_kts'])
```

### Validation Failures

If clearance violates safety rules:
```
WARNING - SEPARATION VIOLATION: Aircraft 123 too close to 456 (lateral: 2.5NM, vertical: 500ft)
WARNING - Air clearance failed safety validation for aircraft 123
WARNING - Skipping database write for aircraft 123: clearance did not pass validation
```

### LLM Failures

If LLM produces invalid output:
```
WARNING - Invalid JSON from LLM for aircraft 123, retrying with fix prompt
INFO - Generated valid air clearance for aircraft 123: VECTORING (after retry)
```

Or if retry also fails:
```
ERROR - Still invalid JSON after retry for aircraft 123
INFO - Using fallback decision for aircraft 123: maintain altitude/speed
```

---

## Configuration

### Environment Variables

Create or update `.env` file in `atc-brain-python/`:
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=atc_system
DB_USER=postgres
DB_PASSWORD=password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
EVENT_CHANNEL=atc:events
```

### Change Ollama Model

Edit `llm_dispatcher.py` and change `self.model`:
```python
class AirLLMClient:
    def __init__(self, safety_validator: Optional[SafetyValidator] = None):
        self.name = "AirLLM"
        self.model = "llama3"  # Changed from "mistral"
        self.safety_validator = safety_validator
```

Available models:
- `mistral` (default, 7B parameters)
- `llama3` (Meta's Llama 3)
- `codellama` (Code-specialized)
- `mixtral` (Mixture of experts, larger)

---

## Troubleshooting

### "Ollama is not installed"
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### "Mistral model not found"
```bash
# Pull the model
ollama pull mistral
```

### "Failed to connect to Redis"
```bash
# Check Redis is running
redis-cli ping

# Start Redis if needed
brew services start redis  # macOS
sudo systemctl start redis  # Linux
```

### "Failed to connect to database"
```bash
# Check PostgreSQL is running
pg_isready

# Verify connection details in .env file
```

### "LLM calls timing out"
- Ollama might be slow on first run (loading model into memory)
- Check CPU/GPU usage: `top` or `htop`
- Consider using GPU acceleration if available

### "No events received"
- Ensure the ATC engine is running
- Verify engine is publishing to the correct Redis channel (`atc:events`)
- Check Redis: `redis-cli SUBSCRIBE atc:events`

---

## Next Steps

1. **Monitor Performance**: Watch log files for LLM latency and validation success rate
2. **Tune Prompts**: Adjust `llm_prompts.py` to improve LLM output quality
3. **Adjust Validation**: Modify `safety_validator.py` to add more safety checks
4. **Add Metrics**: Integrate Prometheus/Grafana for real-time monitoring
5. **Fine-tune Model**: Collect LLM inputs/outputs for fine-tuning on ATC-specific data

---

## Files Overview

```
atc-brain-python/
├── llm/
│   ├── llm_dispatcher.py        # Main LLM integration (Air/Ground clients)
│   ├── llm_schemas.py           # Clearance schemas (Air/Ground)
│   ├── llm_prompts.py           # Prompt builders
│   ├── safety_validator.py      # Validation logic
│   ├── README_MISTRAL_INTEGRATION.md  # Detailed docs
│   └── QUICKSTART.md            # This file
├── launch_llm.py                # Launcher script
├── verify_llm_integration.py    # Verification script
└── requirements.txt             # Python dependencies
```

---

## Summary

✅ **Prerequisites**: Ollama + Mistral, PostgreSQL, Redis, Python deps  
✅ **Verification**: Run `verify_llm_integration.py`  
✅ **Launch**: Run `python launch_llm.py`  
✅ **Monitor**: Watch logs for LLM calls and validation results  

For detailed documentation, see: **README_MISTRAL_INTEGRATION.md**

