# Phase A - Acceptance Criteria and Validation

## Acceptance Checklist

### ✅ Core Functionality

- [ ] **Engine starts successfully**
  - Connects to PostgreSQL
  - Connects to Redis
  - Loads airport data
  - Starts tick loop at 1 Hz

- [ ] **Spawn detection works**
  - Listens to Redis `aircraft.created` events
  - Filters for `flight_type='ARRIVAL'`
  - Marks arrivals with `controller='ENGINE'`
  - Ignores departures

- [ ] **Aircraft control is deterministic**
  - Same initial state + same random seed → identical results
  - Formulas produce consistent outputs
  - No race conditions or undefined behavior

- [ ] **All active arrivals are processed**
  - Queries DB for `controller='ENGINE' AND flight_type='ARRIVAL'`
  - Processes all returned aircraft each tick
  - No aircraft skipped unintentionally

### ✅ Kinematics Accuracy

- [ ] **Speed tracking**
  - Acceleration limited to ≤ 0.6 kt/s
  - Deceleration limited to ≤ 0.8 kt/s
  - Speed stays within 140-550 kts range
  - Converges smoothly to target speed

- [ ] **Turn rate (bank-limited)**
  - Turn rate ≤ g·tan(25°)/V_m
  - Turn radius R ≈ 2-5 NM at typical speeds
  - Takes shortest path (handles 350°→10° correctly)
  - Converges smoothly to target heading

- [ ] **Vertical motion**
  - Climb rate ≤ 2500 fpm (cruise) or 1800 fpm (approach)
  - Descent rate ≤ 3000 fpm (cruise) or 1800 fpm (approach)
  - Capped at 1800 fpm when distance < 10 NM
  - Follows 3° glideslope when approaching

- [ ] **Position updates**
  - Position changes correctly based on heading and speed
  - 1 NM traveled at 360 kts for 1 second
  - Latitude/longitude calculations accurate to 0.01 NM
  - No teleporting or impossible jumps

- [ ] **Random drift (uncontrolled)**
  - Applied when no targets set
  - Speed drift ≤ ±5 kt per tick
  - Heading drift ≤ ±2° per tick
  - Bounded movement (max 0.5 NM per tick at 250 kts)

### ✅ Event Emission

- [ ] **ENTERED_ENTRY_ZONE**
  - Fires once when distance ≤ 30 NM
  - Appears in database `last_event_fired`
  - Published to Redis `atc:events` channel
  - Never fires twice for same aircraft

- [ ] **HANDOFF_READY**
  - Fires once when distance ≤ 20 NM
  - Appears in database `last_event_fired`
  - Published to Redis `atc:events` channel
  - Never fires twice for same aircraft

- [ ] **TOUCHDOWN**
  - Fires once when altitude < 50 ft AGL
  - Marks aircraft `status='landed'`
  - Sets `controller='GROUND'`
  - Published to Redis `atc:events` channel
  - Engine stops controlling aircraft after touchdown

- [ ] **Position updates**
  - Published every tick for each active aircraft
  - Contains full aircraft state
  - Published to Redis `atc:events` channel

- [ ] **State snapshots**
  - Published every 10 ticks
  - Contains all active aircraft summaries
  - Published to Redis `atc:events` channel

### ✅ Persistence

- [ ] **Database updates**
  - Aircraft state persisted every tick
  - Position updated correctly
  - Vertical speed recorded
  - Phase updated based on distance/altitude
  - `last_event_fired` updated when events fire

- [ ] **Telemetry logging**
  - Snapshots written to `telemetry/phaseA/`
  - Files in JSON Lines format
  - One line per aircraft per tick
  - Contains: tick, timestamp, id, callsign, lat, lon, alt, speed, heading, vs, distance, controller, phase

### ✅ Timing and Performance

- [ ] **1 Hz tick rate**
  - Target: 1.0 second per tick
  - Tolerance: ± 0.05 seconds over 10 minutes
  - Drift compensation implemented
  - Warnings logged if tick > 0.1 seconds

- [ ] **Performance under load**
  - Handles up to 100 active aircraft
  - Average tick duration < 100 ms
  - No memory leaks over 1-hour run
  - Database connection pool stable

### ✅ Error Handling

- [ ] **Database disconnection**
  - Graceful handling if PostgreSQL unavailable
  - Reconnection attempts with backoff
  - Engine continues (degrades) if DB temporarily down

- [ ] **Redis disconnection**
  - Graceful handling if Redis unavailable
  - Events logged locally but not published
  - Engine continues operating

- [ ] **Invalid aircraft data**
  - Skips aircraft with corrupt position data
  - Logs error and continues to next aircraft
  - Doesn't crash engine

- [ ] **Keyboard interrupt**
  - Clean shutdown on Ctrl+C
  - All connections closed
  - Final telemetry flushed
  - Statistics printed

## Validation Tests

### Test 1: 60-Second Simulation

**Setup**:
1. Start PostgreSQL and Redis
2. Run database migration
3. Start Next.js application
4. Generate 3 arrival aircraft

**Execute**:
```bash
cd atc-brain-python
python -m engine.core_engine --test
```

**Expected Results**:
- Engine runs for 60 seconds
- 60 ticks completed (1 Hz)
- All 3 aircraft controlled by ENGINE
- Aircraft move toward airport
- Distance decreases over time
- Events fired appropriately
- Telemetry file created
- Statistics printed on exit

**Success Criteria**:
- ✅ Total ticks: 60 ± 1
- ✅ Avg tick duration: < 100 ms
- ✅ All 3 aircraft processed each tick
- ✅ At least one ENTERED_ENTRY_ZONE event
- ✅ Telemetry file contains 180 lines (3 aircraft × 60 ticks)

### Test 2: Deterministic Replay

**Setup**:
1. Set random seed: `random.seed(42)`
2. Generate 1 arrival aircraft at specific position
3. Run engine for 30 seconds

**Execute Run 1**:
```bash
python -m engine.core_engine --duration 30
```

**Execute Run 2**:
```bash
python -m engine.core_engine --duration 30
```

**Expected Results**:
- Both runs produce identical telemetry
- Same positions at same ticks
- Same events fired at same times

**Success Criteria**:
- ✅ Telemetry files are byte-for-byte identical
- ✅ Aircraft at tick 30 has same position in both runs

### Test 3: Event Deduplication

**Setup**:
1. Generate 1 arrival aircraft at 35 NM from airport
2. Run engine until touchdown

**Expected Results**:
- ENTERED_ENTRY_ZONE fires once (around tick 5-10)
- HANDOFF_READY fires once (around tick 15-20)
- TOUCHDOWN fires once (around tick 40-50)
- Each event appears only once in `last_event_fired`

**Success Criteria**:
- ✅ `last_event_fired` = "ENTERED_ENTRY_ZONE,HANDOFF_READY,TOUCHDOWN"
- ✅ No duplicate events in telemetry
- ✅ No duplicate events published to Redis

### Test 4: Performance Under Load

**Setup**:
1. Generate 50 arrival aircraft
2. Run engine for 5 minutes

**Expected Results**:
- All 50 aircraft processed each tick
- Average tick duration < 100 ms
- No memory growth over time
- Stable database connections

**Success Criteria**:
- ✅ 300 ticks completed (5 minutes)
- ✅ All 50 aircraft present in each state snapshot
- ✅ Avg tick duration: < 100 ms
- ✅ Max tick duration: < 200 ms
- ✅ Memory usage stable (no leaks)

### Test 5: Graceful Degradation

**Setup**:
1. Start engine with 5 aircraft
2. After 30 seconds, stop Redis
3. Continue engine for 30 more seconds
4. Restart Redis
5. Continue engine for 30 more seconds

**Expected Results**:
- Engine continues running when Redis down
- Events logged locally but not published
- Engine reconnects when Redis available
- Event publishing resumes

**Success Criteria**:
- ✅ Engine doesn't crash when Redis stops
- ✅ Aircraft continue updating in database
- ✅ Console logs "Redis unavailable" warnings
- ✅ Engine reconnects when Redis returns

## Unit Test Results

Run unit tests:
```bash
cd atc-brain-python
python -m unittest discover tests/
```

**Expected Output**:
```
test_clip (tests.test_kinematics.TestKinematics) ... ok
test_update_speed_acceleration (tests.test_kinematics.TestKinematics) ... ok
test_update_speed_deceleration (tests.test_kinematics.TestKinematics) ... ok
test_update_heading_right_turn (tests.test_kinematics.TestKinematics) ... ok
...
test_distance_to_airport (tests.test_geo_utils.TestGeoUtils) ... ok
test_bearing_to_point_north (tests.test_geo_utils.TestGeoUtils) ... ok
...

----------------------------------------------------------------------
Ran 25 tests in 0.123s

OK
```

**Success Criteria**:
- ✅ All unit tests pass
- ✅ No errors or warnings
- ✅ Test coverage > 80%

## Metrics to Collect

### Per-Tick Metrics
- Tick number
- Tick duration (ms)
- Active aircraft count
- Events fired this tick
- Database query time (ms)
- Redis publish time (ms)

### Cumulative Metrics
- Total ticks
- Total aircraft processed
- Total events fired
- Average tick duration
- Max tick duration
- Uptime (seconds)

### Aircraft Metrics (per aircraft)
- Distance traveled (NM)
- Altitude change (ft)
- Speed changes (count)
- Heading changes (count)
- Events fired (list)
- Time to touchdown (seconds)

## Acceptance Sign-Off

**Phase A is complete when**:

✅ All checklist items pass  
✅ All 5 validation tests pass  
✅ All unit tests pass  
✅ Telemetry files generated correctly  
✅ Documentation complete  
✅ Code reviewed and merged to branch `ai-atc-brain-v2`  

**Reviewed by**: _____________  
**Date**: _____________  
**Signature**: _____________  

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-05  
**Status**: Ready for Testing

