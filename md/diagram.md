⏺ How the system handles 4 aircraft                                                                                                                              
                                                                                                                                                                 
  Key point first: the LLM is NOT event-driven                                                                                                                   
                                                                                                                                                                 
  The old system fired a separate LLM call every time a plane hit a checkpoint. The new system is time-driven — a background loop wakes up every 10 seconds,     
  looks at ALL active aircraft at once, and makes decisions for everyone in a single pass. The LLM (if needed at all) is called once per cycle, not once per     
  aircraft.                                                                                                                                                      

  ---
  The 4-aircraft scenario, step by step

  Say 4 planes spawn simultaneously from N, SE, W, and NE — all heading to CYYZ.

  AC1  (North,    150NM out)   phase=CRUISE
  AC2  (Southeast, 140NM out)  phase=CRUISE
  AC3  (West,      120NM out)  phase=CRUISE
  AC4  (Northeast, 110NM out)  phase=CRUISE

  ---
  t=0–1s — Engine ticks
  Physics runs for all 4 independently every second. Each plane moves, altitude/speed/heading are updated. No decisions yet — they just fly their initial heading
   toward the airport.

  ---
  t=10s — First planning cycle

  The cycle fetches all 4 from DB in one query. Rule Engine checks each:

  - All 4 are CRUISE with no target_altitude_ft → Case 1 fires for all 4

  AC1 → target_altitude_ft=15000, target_speed_kts=280
  AC2 → target_altitude_ft=15000, target_speed_kts=280
  AC3 → target_altitude_ft=15000, target_speed_kts=280
  AC4 → target_altitude_ft=15000, target_speed_kts=280

  LLM not called — rule engine handled all 4. 4 DB writes, done in <1ms.

  ---
  t=10–20min — Standard descent (rule engine only)

  As each plane closes in, the cycle keeps firing rule engine cases:

  AC4 hits 40NM → target_altitude_ft=10000, target_speed_kts=250
  AC3 hits 40NM → same
  AC4 hits 25NM → target_altitude_ft=6000,  target_speed_kts=210
  ...

  Still no LLM. All deterministic.

  ---
  t=~25min — AC4 enters approach zone (~15NM)

  Engine detects zone.boundary_crossed → Redis event → RegistryEventSubscriber adds AC4 to approach queue:
  approach_queue = [AC4]

  Next planning cycle: AC4 is APPROACH, no runway_assigned, 1 aircraft in queue (it's at the front), multiple free runways available.

  Rule Engine Case 3 — AC4 is front of queue → assigns preferred runway:
  AC4 → runway="23L", target_altitude_ft=3000, target_speed_kts=170, target_heading_deg=230
  Registry: 23L → AC4 (locked). Still no LLM.

  ---
  t=~27min — AC3 also enters approach zone

  approach_queue = [AC4, AC3]   (AC4 already has runway, AC3 just joined)

  Planning cycle sees AC3: APPROACH, no runway, multiple free runways, NOT front of queue (AC4 is). Rule engine returns None → hands AC3 to LLM.

  But AC1 and AC2 are still in descent → rule engine handles them normally.

  So this cycle: rule engine handles AC1, AC2, AC4 (AC4 already has runway so rule engine skips it). LLM called once with just AC3.

  LLM sees:
  RUNWAY STATE:
    23L: OCCUPIED by aircraft AC4
    23R: FREE
    05L: FREE  ...

  APPROACH QUEUE: AC4 → AC3

  AIRCRAFT NEEDING DECISIONS:
    [1] AC3 (id=3): APPROACH, 14.2NM, 6000ft, 210kts, runway_assigned=none

  LLM responds:
  {"clearances": [{"aircraft_id": 3, "runway": "23R", "target_altitude_ft": 3000, ...}]}

  Validated against live registry → 23R is free → assigned. AC3 gets ILS for 23R.

  ---
  t=~30min — AC1 and AC2 also enter approach, 23L/23R both occupied

  approach_queue = [AC4, AC3, AC1, AC2]
  free_runways = []   ← AC4 on 23L, AC3 on 23R

  Rule engine sees AC1 and AC2: APPROACH, no runway, zero free runways → returns None for both → both go to LLM.

  LLM is given AC1 and AC2 together with the full state. It issues holds:
  {"clearances": [
    {"aircraft_id": 1, "target_altitude_ft": 4000, "action": "HOLD"},
    {"aircraft_id": 2, "target_altitude_ft": 5000, "action": "HOLD"}
  ]}

  The 1000ft vertical separation between AC1 and AC2 prevents conflicts while they wait.

  ---
  t=~32min — AC4 lands, runway.vacated fires

  RegistryEventSubscriber → release_runway("23L"). Next cycle: 23L is free again. Rule engine picks up AC1 (front of queue after AC4 dequeued) → assigns 23L. AC2
   waits another cycle.

  ---
  Summary

  ┌─────────────────────────────────────────────────┬──────────────────────────────────────────────────┐
  │               When is LLM called?               │              When is it NOT called?              │
  ├─────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ Multiple aircraft competing for the same runway │ Standard descent profile steps                   │
  ├─────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ No free runways (hold sequencing)               │ Initial descent trigger (CRUISE → 15000ft)       │
  ├─────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ Separation conflict resolution                  │ Single free runway → single approaching aircraft │
  ├─────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ Anything the rule engine can't decide cleanly   │ Taxi to gate (first free gate)                   │
  └─────────────────────────────────────────────────┴──────────────────────────────────────────────────┘

  With 4 aircraft the LLM typically gets called 0–1 times per 10s cycle, and when it is called, it handles all the complex cases in one prompt — not 4 separate
  calls. The rule engine silently handles the other 3 aircraft in the same cycle without touching the LLM at all.