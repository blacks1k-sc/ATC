#!/usr/bin/env node

const fetch = require('node-fetch');

async function testClearFunctionality() {
  try {
    console.log('🧪 Testing Clear All Aircraft functionality...');
    
    // Test 1: Check if server is running
    console.log('1. Checking server health...');
    const healthResponse = await fetch('http://localhost:3000/api/health');
    if (healthResponse.ok) {
      const health = await healthResponse.json();
      console.log('✅ Server is healthy:', health.overall);
    } else {
      console.log('❌ Server is not responding');
      return;
    }
    
    // Test 2: Create a test aircraft
    console.log('2. Creating test aircraft...');
    const createResponse = await fetch('http://localhost:3000/api/aircraft/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        airline: 'ACA',
        aircraftType: 'A320',
        flightType: 'ARRIVAL'
      })
    });
    
    if (createResponse.ok) {
      const createResult = await createResponse.json();
      console.log('✅ Aircraft created:', createResult.event.message);
    } else {
      console.log('❌ Failed to create aircraft');
      return;
    }
    
    // Test 3: Check events before clearing
    console.log('3. Checking events before clearing...');
    const eventsBeforeResponse = await fetch('http://localhost:3000/api/events?limit=5');
    if (eventsBeforeResponse.ok) {
      const eventsBefore = await eventsBeforeResponse.json();
      console.log(`✅ Found ${eventsBefore.events.length} events before clearing`);
    }
    
    // Test 4: Clear all aircraft
    console.log('4. Clearing all aircraft...');
    const clearResponse = await fetch('http://localhost:3000/api/aircraft/clear', {
      method: 'DELETE'
    });
    
    if (clearResponse.ok) {
      const clearResult = await clearResponse.json();
      console.log('✅ Aircraft cleared:', clearResult.message);
      console.log('   Aircraft deleted:', clearResult.deletedCount.aircraftDeleted);
      console.log('   Events deleted:', clearResult.deletedCount.eventsDeleted);
    } else {
      console.log('❌ Failed to clear aircraft');
      const error = await clearResponse.text();
      console.log('Error:', error);
    }
    
    // Test 5: Check events after clearing
    console.log('5. Checking events after clearing...');
    const eventsAfterResponse = await fetch('http://localhost:3000/api/events?limit=5');
    if (eventsAfterResponse.ok) {
      const eventsAfter = await eventsAfterResponse.json();
      console.log(`✅ Found ${eventsAfter.events.length} events after clearing`);
    }
    
    console.log('🎉 Test completed successfully!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

testClearFunctionality();
