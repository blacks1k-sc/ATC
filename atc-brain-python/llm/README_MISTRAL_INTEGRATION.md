# Mistral-7B LLM Integration for ATC Brain

## Overview

This document describes the real LLM integration using **Mistral-7B** via **Ollama** for Air and Ground ATC controllers. The placeholder LLM clients have been replaced with production-ready implementations that:

1. Generate clearances using Mistral-7B via Ollama
2. Validate outputs using strict JSON schemas
3. Apply safety validation before writing to the database
4. Include retry logic for malformed responses
5. Provide safe fallback decisions when LLM or validation fails

---

## Architecture

### New Modules

#### 1. `llm_schemas.py`
Defines minimal dataclass schemas for clearance outputs:

- **`AirClearance`**: For airborne aircraft
  - `action_type`: str (e.g., "VECTORING", "DESCENT_PROFILE", "STAR_ASSIGNMENT", "LANDING_CLEARANCE")
  - `target_altitude_ft`: Optional[int]
  - `target_speed_kts`: Optional[int]
  - `target_heading_deg`: Optional[int]
  - `waypoints`: Optional[List[str]]
  - `runway`: Optional[str]

- **`GroundClearance`**: For surface operations
  - `action_type`: str (e.g., "GATE_ASSIGNMENT", "TAXI_CLEARANCE", "PUSHBACK")
  - `assigned_gate`: Optional[str]
  - `taxi_route`: Optional[List[str]]
  - `runway`: Optional[str]

#### 2. `llm_prompts.py`
Builds compact instruction prompts for the LLM:

- **`build_air_prompt(context: dict) -> str`**
  - Describes Air controller role
  - Includes hard rules (3NM/1000ft separation, runway exclusivity)
  - Requires strict JSON output matching `AirClearance` schema
  - Provides aircraft state and nearby traffic context

- **`build_ground_prompt(context: dict) -> str`**
  - Describes Ground controller role
  - Includes hard rules (gate/taxi conflicts, no invented data)
  - Requires strict JSON output matching `GroundClearance` schema
  - Provides event context and aircraft state

#### 3. `safety_validator.py`
Validates clearances against ATC safety rules:

- **`SafetyValidator` class**
  - `validate_air_clearance()`: Checks:
    - Minimum 3NM lateral OR 1000ft vertical separation
    - Runway exclusivity
    - Returns `False` if clearance violates rules
  
  - `validate_ground_clearance()`: Checks:
    - Gate availability
    - Taxi route conflicts
    - Returns `False` if clearance violates rules

#### 4. Updated `llm_dispatcher.py`

**Modified `AirLLMClient`**:
- Calls Ollama asynchronously via subprocess: `ollama run mistral`
- Parses JSON output safely (handles markdown code blocks, malformed JSON)
- Retries once with "fix JSON only" prompt if parsing fails
- Validates clearance with `SafetyValidator`
- Returns fallback decision if LLM or validation fails
- Marks decision as `validated: True/False`

**Modified `GroundLLMClient`**:
- Same implementation pattern as `AirLLMClient`
- Specialized for ground operations

**Modified `DecisionRouter`**:
- Only writes target fields (altitude, speed, heading, gate, taxi_route) to database when `validated: True`
- Preserves all existing async design patterns
- Stores all clearances (validated and failed) for audit logging

**Modified `LLMDispatcher`**:
- Initializes `SafetyValidator` after database connection
- Passes validator to both LLM clients
- No changes to event loop or subscription logic

---

## How It Works

### Air Clearance Flow

1. **Event Trigger**: `zone.boundary_crossed` or `clearance.completed`
2. **Context Building**: `ContextBuilder` fetches aircraft state, zone info, nearby traffic
3. **Prompt Generation**: `build_air_prompt()` creates compact instruction
4. **LLM Call**: `AirLLMClient._call_ollama()` runs `ollama run mistral` with prompt
5. **JSON Parsing**: Safely parse response, retry once if malformed
6. **Safety Validation**: Check separation and runway rules
7. **Decision Application**: If validated, write to database; otherwise skip and log
8. **Fallback**: If any step fails, return conservative fallback (maintain altitude/speed)

### Ground Clearance Flow

1. **Event Trigger**: `runway.landed` or `runway.vacated`
2. **Context Building**: `ContextBuilder` fetches aircraft state, event type
3. **Prompt Generation**: `build_ground_prompt()` creates compact instruction
4. **LLM Call**: `GroundLLMClient._call_ollama()` runs `ollama run mistral` with prompt
5. **JSON Parsing**: Safely parse response, retry once if malformed
6. **Safety Validation**: Check gate/taxi conflicts
7. **Decision Application**: If validated, write to database; otherwise skip and log
8. **Fallback**: If any step fails, return default gate assignment

---

## Safety Features

### Hard Rules in Prompts
The LLM is explicitly instructed to:
- Maintain 3NM lateral OR 1000ft vertical separation
- Ensure only one aircraft per runway
- Not invent waypoints, gates, or runways
- Output strict JSON only (no explanations)

### Validation Layer
`SafetyValidator` acts as a safety net:
- Verifies separation requirements computationally
- Checks runway/gate/taxi conflicts against database state
- Rejects clearances that violate rules, even if LLM suggests them

### Fallback Decisions
When LLM or validation fails:
- **Air**: Maintain current altitude, reduce speed to 250 knots (conservative holding)
- **Ground**: Assign default gate (C32)
- Fallbacks are marked as `validated: False` and not written to aircraft state

### Retry Logic
- If LLM output is not valid JSON, retry once with explicit "fix JSON" prompt
- Prevents transient parsing errors from causing fallback decisions

---

## Database Impact

### Only Validated Clearances Modify State
`DecisionRouter.apply_decision()` only updates `aircraft_instances` table when `validated: True`:
- **Written fields**: `target_altitude_ft`, `target_speed_kts`, `target_heading_deg`
- **Not written**: If validation fails, aircraft state remains unchanged

### All Clearances Logged
- Both validated and failed clearances are stored in `clearances` table
- Includes `validated` flag, reason, confidence, LLM response
- Enables audit trail and offline analysis

---

## Prerequisites

### Ollama Installation
```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull Mistral-7B model
ollama pull mistral

# Verify installation
ollama run mistral "test"
```

### Python Dependencies
Already included in existing `requirements.txt`:
- `asyncio` (standard library)
- `asyncpg`
- `redis`

---

## Configuration

### Environment Variables
No new environment variables required. Uses existing:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- `EVENT_CHANNEL` (default: `atc:events`)

### Model Selection
To use a different Ollama model, modify `self.model` in `AirLLMClient` and `GroundLLMClient`:

```python
class AirLLMClient:
    def __init__(self, safety_validator: Optional[SafetyValidator] = None):
        self.name = "AirLLM"
        self.model = "mistral"  # Change to "llama3", "codellama", etc.
        self.safety_validator = safety_validator
```

---

## Usage

### Running the LLM Dispatcher
```bash
cd atc-brain-python
python -m llm.llm_dispatcher
```

Or use the existing launcher:
```bash
python launch_llm.py
```

### Monitoring
The dispatcher logs all LLM calls, validation results, and decisions:
```
INFO: Calling Mistral-7B for Air clearance (aircraft 123)
INFO: Generated valid air clearance for aircraft 123: VECTORING
INFO: Applied validated clearance to aircraft 123: VECTORING (updates: ['target_altitude_ft', 'target_speed_kts'])
```

Failed validations:
```
WARNING: SEPARATION VIOLATION: Aircraft 123 too close to 456 (lateral: 2.5NM, vertical: 500ft)
WARNING: Skipping database write for aircraft 123: clearance did not pass validation
```

---

## Performance Considerations

### Latency
- **Ollama call**: 1-5 seconds per LLM invocation (depends on model and hardware)
- **Validation**: <100ms per clearance
- **Total per decision**: 2-7 seconds

### Concurrency
- LLM calls are asynchronous (don't block event loop)
- Multiple aircraft can be processed concurrently
- Each clearance decision is independent

### Scalability
- For high-traffic scenarios, consider:
  - GPU acceleration for Ollama (CUDA/Metal)
  - Caching common clearance patterns
  - Pre-emptive clearance generation
  - Rate limiting LLM calls per tick

---

## Testing

### Manual Test
```python
from llm import AirLLMClient, SafetyValidator
import asyncpg
import asyncio

async def test():
    db_pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        database="atc_system",
        user="postgres",
        password="password"
    )
    
    validator = SafetyValidator(db_pool)
    client = AirLLMClient(validator)
    
    context = {
        "aircraft_id": 1,
        "current_zone": "APPROACH_5",
        "aircraft": {
            "callsign": "UAL123",
            "altitude_ft": 5000,
            "speed_kts": 220,
            "heading": 50,
            "distance_to_airport_nm": 8.5
        },
        "current_zone_aircraft": []
    }
    
    decision = await client.generate_decision(context)
    print(f"Decision: {decision}")
    
    await db_pool.close()

asyncio.run(test())
```

---

## Future Enhancements

### Phase 2: RL Integration
- Tactical RL agent refines LLM strategic decisions
- RL optimizes timing, sequencing, deconfliction
- LLM provides high-level plan, RL provides low-level control

### Phase 3: Trajectory Prediction
- Predict aircraft trajectories 5-10 minutes ahead
- Use predictions as input to LLM context
- Enable proactive conflict detection

### Phase 4: MLOps
- Log all LLM inputs/outputs for training data
- Fine-tune Mistral-7B on ATC-specific corpus
- A/B test different prompt templates
- Monitor LLM validation success rate

---

## Summary

The Mistral-7B integration replaces placeholder LLM clients with production-ready implementations that:

✅ **Generate clearances** using real LLM via Ollama  
✅ **Validate safety** before writing to database  
✅ **Retry malformed** JSON responses  
✅ **Provide fallbacks** when LLM/validation fails  
✅ **Log all decisions** for audit trail  
✅ **Preserve async design** without modifying engine tick loop  

This integration is ready for testing with live aircraft in the ATC-1 system.

