#!/usr/bin/env node

/**
 * Test script to verify distance calculation implementation
 * This script tests the new logic-based calculations
 */

const { calculateDistanceToAirport, calculateSector, generateRealisticPosition } = require('./atc-nextjs/src/utils/geoUtils.ts');

console.log('🧪 Testing Distance Calculation Implementation\n');

// Test 1: Distance calculation accuracy
console.log('1. Testing distance calculation accuracy:');
const testPositions = [
  { lat: 43.6777, lon: -79.6248, expected: 0, name: 'CYYZ VOR (airport center)' },
  { lat: 43.6777, lon: -78.6248, expected: 60, name: '60 NM East' },
  { lat: 44.6777, lon: -79.6248, expected: 60, name: '60 NM North' },
  { lat: 43.1777, lon: -79.6248, expected: 30, name: '30 NM South' },
  { lat: 43.6777, lon: -80.1248, expected: 30, name: '30 NM West' }
];

testPositions.forEach(({ lat, lon, expected, name }) => {
  const calculated = calculateDistanceToAirport(lat, lon);
  const diff = Math.abs(calculated - expected);
  const status = diff < 1 ? '✅' : '❌';
  console.log(`   ${status} ${name}: Expected ~${expected} NM, Got ${calculated.toFixed(2)} NM (diff: ${diff.toFixed(2)})`);
});

// Test 2: Sector calculation
console.log('\n2. Testing sector calculation:');
const testDistances = [
  { distance: 50, expected: 'ENTRY' },
  { distance: 25, expected: 'ENROUTE' },
  { distance: 7, expected: 'APPROACH' },
  { distance: 1, expected: 'RUNWAY' }
];

testDistances.forEach(({ distance, expected }) => {
  const calculated = calculateSector(distance);
  const status = calculated === expected ? '✅' : '❌';
  console.log(`   ${status} ${distance} NM → ${calculated} (expected: ${expected})`);
});

// Test 3: Realistic position generation
console.log('\n3. Testing realistic position generation:');
for (let i = 0; i < 3; i++) {
  const position = generateRealisticPosition('ARRIVAL');
  const recalculatedDistance = calculateDistanceToAirport(position.lat, position.lon);
  const sector = calculateSector(recalculatedDistance);
  
  console.log(`   Aircraft ${i + 1}:`);
  console.log(`     Position: ${position.lat.toFixed(4)}°N, ${position.lon.toFixed(4)}°W`);
  console.log(`     Distance: ${position.distance_to_airport_nm.toFixed(2)} NM (recalculated: ${recalculatedDistance.toFixed(2)} NM)`);
  console.log(`     Sector: ${sector}`);
  console.log(`     Altitude: ${position.altitude_ft} ft`);
  console.log(`     Heading: ${position.heading}°`);
  console.log(`     Speed: ${position.speed_kts} kts`);
  console.log('');
}

console.log('🎯 Test completed! All calculations should now use pure logic instead of hardcoded values.');
