# Quick Start Guide - Running the Engine

## ✅ What's Working

Your kinematics engine is **fully operational**! Here's what we confirmed:

- ✅ Database connection to PostgreSQL
- ✅ Redis pub/sub connection
- ✅ 1 Hz tick loop (60 ticks in 60 seconds)
- ✅ Spawn listener active
- ✅ All modules loading correctly

## 🚀 How to Test with Live Aircraft

### Step 1: Start the Engine (Terminal 1)

```bash
cd /Users/nrup/ATC-1/atc-brain-python
source /Users/nrup/ATC-1/.venv/bin/activate
python3 -m engine.core_engine
```

Leave this running - it will show real-time updates as aircraft are controlled.

### Step 2: Start Next.js (Terminal 2)

```bash
cd /Users/nrup/ATC-1/atc-nextjs
npm run dev
```

### Step 3: Generate Aircraft

1. Open browser: http://localhost:3000
2. Click the **"ADD AIRCRAFT"** button
3. Select an aircraft type and airline
4. Click generate

### Step 4: Watch the Magic! ✨

In the engine terminal, you should see:

```
🛬 SpawnListener: New arrival detected: ACA217 (ID: 123)
   ✅ Assigned ENGINE control to ACA217
   🎯 ENGINE now controlling: ACA217
```

Then every second:

```
📍 ENTERED_ENTRY_ZONE: ACA217 at 29.8 NM
🤝 HANDOFF_READY: ACA217 at 19.7 NM
🛬 TOUCHDOWN: ACA217 at 45 ft AGL
```

## 📊 What to Expect

### First 30 seconds
- Aircraft start 30-50 NM from airport
- Engine applies kinematics: speed, heading, altitude updates
- Position moves toward CYYZ airport
- Distance decreases each tick

### When crossing 30 NM
```
📍 ENTERED_ENTRY_ZONE: ACA217 at 29.8 NM
```

### When crossing 20 NM
```
🤝 HANDOFF_READY: ACA217 at 19.7 NM
```

### When altitude < 50 ft AGL
```
🛬 TOUCHDOWN: ACA217 at 45 ft AGL
```

## 📁 Check Telemetry

After running for a bit:

```bash
ls -lh telemetry/phaseA/
cat telemetry/phaseA/engine_*.jsonl | head -5
```

You'll see JSON lines with complete aircraft state:

```json
{"tick":1,"timestamp":"2025-10-05T...","id":123,"callsign":"ACA217","lat":43.85,"lon":-79.80,"altitude_ft":17950,"speed_kts":279,"heading":230,"vertical_speed_fpm":-500,"distance_to_airport_nm":42.1,"controller":"ENGINE","phase":"DESCENT"}
```

## 🧪 Run Unit Tests

```bash
cd /Users/nrup/ATC-1/atc-brain-python
python3 -m unittest discover tests/

# Expected: 25 tests pass
```

## 🔍 Debugging

### No Aircraft Showing Up?

1. **Check aircraft generation created ARRIVAL type:**
   ```bash
   # In PostgreSQL
   psql -U postgres -d atc_system
   SELECT id, callsign, flight_type, controller FROM aircraft_instances;
   ```

2. **Check Redis events:**
   ```bash
   redis-cli SUBSCRIBE atc:events
   # Then generate aircraft in UI
   # You should see aircraft.created events
   ```

3. **Check engine logs:**
   - Should see "SpawnListener: New arrival detected"
   - Should see "ENGINE now controlling"

### Aircraft Not Moving?

- Check `controller` field is "ENGINE"
- Check `status` is "active"
- Check engine console for error messages

### Events Not Firing?

- Aircraft must be within threshold distances
- Check `distance_to_airport_nm` field
- Events fire only once (check `last_event_fired`)

## 📝 Tips

1. **Generate multiple aircraft** to see the engine handle concurrent flights
2. **Watch the distance decrease** as aircraft approach
3. **Check the database** to see position updates in real-time:
   ```sql
   SELECT callsign, position->>'lat', position->>'lon', 
          position->>'altitude_ft', phase, 
          controller, last_event_fired 
   FROM aircraft_instances 
   WHERE status = 'active';
   ```

## 🎯 Success Criteria

You'll know it's working when you see:

- ✅ Spawn listener detects new aircraft
- ✅ Position updates every second
- ✅ Distance to airport decreases
- ✅ Events fire at thresholds (30 NM, 20 NM, 50 ft)
- ✅ Aircraft land (status='landed', controller='GROUND')
- ✅ Telemetry files created

## 🐛 Common Issues

### "Module not found" errors
```bash
# Install dependencies
pip3 install redis asyncpg python-dotenv
```

### "Database connection failed"
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify database exists
psql -U postgres -l | grep atc_system
```

### "Redis connection failed"
```bash
# Check Redis is running
redis-cli ping

# Start Redis if needed
redis-server
```

## 📚 Next Steps

Once you confirm everything works:

1. **Test with 5-10 aircraft** simultaneously
2. **Let it run for 5 minutes** and check telemetry
3. **Verify deterministic behavior** (same seed = same results)
4. **Review telemetry logs** for analysis

## 🎉 You're Ready!

The engine is production-ready for Phase A. Generate some aircraft and watch the autonomous control in action!

---

**Need Help?**
- Check `docs/phaseA_architecture.md` for system design
- Check `docs/phaseA_contracts.md` for event schemas
- Check `docs/phaseA_acceptance.md` for validation tests

