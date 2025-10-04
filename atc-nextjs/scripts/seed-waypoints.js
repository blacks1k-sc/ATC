/**
 * Seed script for CYYZ waypoints, procedures, gates, and taxiways
 * Run this after the main schema migration
 */

const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'atc_system',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || '',
});

async function seedWaypoints() {
  console.log('🌍 Seeding CYYZ waypoints...');
  
  const waypoints = [
    // Arrival waypoints
    { name: 'BOXUM', lat: 43.8667, lon: -79.1167, type: 'ARRIVAL', airport_icao: 'CYYZ', description: 'Initial approach fix for BOXUM FIVE arrival' },
    { name: 'KENNO', lat: 43.7833, lon: -79.3500, type: 'ARRIVAL', airport_icao: 'CYYZ', description: 'Intermediate waypoint on BOXUM FIVE' },
    { name: 'MALTN', lat: 43.7167, lon: -79.5000, type: 'ARRIVAL', airport_icao: 'CYYZ', description: 'Final approach transition waypoint' },
    { name: 'BEFNI', lat: 43.5500, lon: -79.7000, type: 'ARRIVAL', airport_icao: 'CYYZ', description: 'Final approach fix for runway 05' },
    { name: 'BIMKI', lat: 43.4500, lon: -79.5500, type: 'ARRIVAL', airport_icao: 'CYYZ', description: 'Alternative arrival waypoint' },
    { name: 'NAKBO', lat: 43.8000, lon: -79.6500, type: 'ARRIVAL', airport_icao: 'CYYZ', description: 'Downwind entry point' },
    
    // Departure waypoints
    { name: 'DUVOS', lat: 43.9000, lon: -79.8000, type: 'DEPARTURE', airport_icao: 'CYYZ', description: 'Initial departure fix for DUVOS SIX SID' },
    { name: 'LINNG', lat: 43.8500, lon: -80.1000, type: 'DEPARTURE', airport_icao: 'CYYZ', description: 'Enroute waypoint for western departures' },
    { name: 'IMEBA', lat: 43.9500, lon: -79.3000, type: 'DEPARTURE', airport_icao: 'CYYZ', description: 'Initial departure fix for IMEBA TWO SID' },
    { name: 'VERKO', lat: 43.5000, lon: -80.2000, type: 'DEPARTURE', airport_icao: 'CYYZ', description: 'Enroute waypoint for southern departures' },
    { name: 'UDNIK', lat: 44.0000, lon: -79.6000, type: 'DEPARTURE', airport_icao: 'CYYZ', description: 'Northern departure waypoint' }
  ];

  for (const waypoint of waypoints) {
    await pool.query(`
      INSERT INTO waypoints (name, lat, lon, type, airport_icao, description)
      VALUES ($1, $2, $3, $4, $5, $6)
      ON CONFLICT (name) DO UPDATE SET
        lat = EXCLUDED.lat,
        lon = EXCLUDED.lon,
        type = EXCLUDED.type,
        airport_icao = EXCLUDED.airport_icao,
        description = EXCLUDED.description
    `, [waypoint.name, waypoint.lat, waypoint.lon, waypoint.type, waypoint.airport_icao, waypoint.description]);
  }
  
  console.log(`✅ Seeded ${waypoints.length} waypoints`);
}

async function seedProcedures() {
  console.log('📋 Seeding CYYZ procedures...');
  
  const procedures = [
    // STAR procedures (Arrivals)
    {
      name: 'BOXUM FIVE',
      type: 'STAR',
      runway_id: '05',
      airport_icao: 'CYYZ',
      waypoint_sequence: ['BOXUM', 'KENNO', 'MALTN', 'BEFNI'],
      altitude_restrictions: { 'BOXUM': 24000, 'KENNO': 16000, 'MALTN': 10000, 'BEFNI': 4000 },
      speed_restrictions: { 'BOXUM': 280, 'KENNO': 250, 'MALTN': 210, 'BEFNI': 180 },
      description: 'Standard arrival for runway 05 via BOXUM'
    },
    {
      name: 'BIMKI THREE',
      type: 'STAR',
      runway_id: '05',
      airport_icao: 'CYYZ',
      waypoint_sequence: ['BIMKI', 'MALTN', 'BEFNI'],
      altitude_restrictions: { 'BIMKI': 20000, 'MALTN': 10000, 'BEFNI': 4000 },
      speed_restrictions: { 'BIMKI': 280, 'MALTN': 210, 'BEFNI': 180 },
      description: 'Alternate arrival for runway 05 via BIMKI'
    },
    
    // SID procedures (Departures)
    {
      name: 'DUVOS SIX',
      type: 'SID',
      runway_id: '05',
      airport_icao: 'CYYZ',
      waypoint_sequence: ['DUVOS', 'LINNG'],
      altitude_restrictions: { 'DUVOS': 8000, 'LINNG': 15000 },
      speed_restrictions: { 'DUVOS': 250, 'LINNG': 280 },
      description: 'Western departure from runway 05'
    },
    {
      name: 'IMEBA TWO',
      type: 'SID',
      runway_id: '23',
      airport_icao: 'CYYZ',
      waypoint_sequence: ['IMEBA', 'VERKO'],
      altitude_restrictions: { 'IMEBA': 8000, 'VERKO': 15000 },
      speed_restrictions: { 'IMEBA': 250, 'VERKO': 280 },
      description: 'Southern departure from runway 23'
    }
  ];

  for (const procedure of procedures) {
    await pool.query(`
      INSERT INTO procedures (name, type, runway_id, airport_icao, waypoint_sequence, altitude_restrictions, speed_restrictions, description)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      ON CONFLICT (name, airport_icao) DO UPDATE SET
        type = EXCLUDED.type,
        runway_id = EXCLUDED.runway_id,
        waypoint_sequence = EXCLUDED.waypoint_sequence,
        altitude_restrictions = EXCLUDED.altitude_restrictions,
        speed_restrictions = EXCLUDED.speed_restrictions,
        description = EXCLUDED.description
    `, [
      procedure.name,
      procedure.type,
      procedure.runway_id,
      procedure.airport_icao,
      JSON.stringify(procedure.waypoint_sequence),
      JSON.stringify(procedure.altitude_restrictions),
      JSON.stringify(procedure.speed_restrictions),
      procedure.description
    ]);
  }
  
  console.log(`✅ Seeded ${procedures.length} procedures`);
}

async function seedGates() {
  console.log('🚪 Seeding CYYZ gates...');
  
  const gates = [
    { gate_number: 'A1', terminal: 'A', lat: 43.6790, lon: -79.6200, airport_icao: 'CYYZ' },
    { gate_number: 'A2', terminal: 'A', lat: 43.6795, lon: -79.6205, airport_icao: 'CYYZ' },
    { gate_number: 'A5', terminal: 'A', lat: 43.6800, lon: -79.6210, airport_icao: 'CYYZ' },
    { gate_number: 'B5', terminal: 'B', lat: 43.6785, lon: -79.6180, airport_icao: 'CYYZ' },
    { gate_number: 'B6', terminal: 'B', lat: 43.6780, lon: -79.6175, airport_icao: 'CYYZ' },
    { gate_number: 'B10', terminal: 'B', lat: 43.6775, lon: -79.6170, airport_icao: 'CYYZ' },
    { gate_number: 'C10', terminal: 'C', lat: 43.6775, lon: -79.6220, airport_icao: 'CYYZ' },
    { gate_number: 'C12', terminal: 'C', lat: 43.6770, lon: -79.6225, airport_icao: 'CYYZ' },
    { gate_number: 'D12', terminal: 'D', lat: 43.6770, lon: -79.6190, airport_icao: 'CYYZ' },
    { gate_number: 'D15', terminal: 'D', lat: 43.6765, lon: -79.6195, airport_icao: 'CYYZ' }
  ];

  for (const gate of gates) {
    await pool.query(`
      INSERT INTO gates (gate_number, terminal, lat, lon, airport_icao, status)
      VALUES ($1, $2, $3, $4, $5, 'available')
      ON CONFLICT (gate_number) DO UPDATE SET
        terminal = EXCLUDED.terminal,
        lat = EXCLUDED.lat,
        lon = EXCLUDED.lon,
        airport_icao = EXCLUDED.airport_icao
    `, [gate.gate_number, gate.terminal, gate.lat, gate.lon, gate.airport_icao]);
  }
  
  console.log(`✅ Seeded ${gates.length} gates`);
}

async function seedTaxiways() {
  console.log('🛣️ Seeding CYYZ taxiways...');
  
  const taxiways = [
    {
      name: 'A',
      from_point: 'Terminal A',
      to_point: 'Runway 05',
      airport_icao: 'CYYZ',
      length_meters: 1200
    },
    {
      name: 'B',
      from_point: 'Terminal B',
      to_point: 'Runway 05',
      airport_icao: 'CYYZ',
      length_meters: 800
    },
    {
      name: 'C',
      from_point: 'Terminal C',
      to_point: 'Runway 23',
      airport_icao: 'CYYZ',
      length_meters: 1500
    },
    {
      name: 'D',
      from_point: 'Terminal D',
      to_point: 'Runway 23',
      airport_icao: 'CYYZ',
      length_meters: 1000
    }
  ];

  for (const taxiway of taxiways) {
    await pool.query(`
      INSERT INTO taxiways (name, from_point, to_point, airport_icao, length_meters)
      VALUES ($1, $2, $3, $4, $5)
      ON CONFLICT DO NOTHING
    `, [taxiway.name, taxiway.from_point, taxiway.to_point, taxiway.airport_icao, taxiway.length_meters]);
  }
  
  console.log(`✅ Seeded ${taxiways.length} taxiways`);
}

async function main() {
  try {
    console.log('🚀 Starting waypoint seeding...');
    
    await seedWaypoints();
    await seedProcedures();
    await seedGates();
    await seedTaxiways();
    
    console.log('🎉 Waypoint seeding completed successfully!');
    
  } catch (error) {
    console.error('❌ Error during seeding:', error);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

if (require.main === module) {
  main();
}

module.exports = { seedWaypoints, seedProcedures, seedGates, seedTaxiways };
