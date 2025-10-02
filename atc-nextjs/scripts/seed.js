#!/usr/bin/env node

const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// Environment configuration
const config = {
  user: process.env.DB_USER || 'postgres',
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'atc_system',
  password: process.env.DB_PASSWORD || 'password',
  port: parseInt(process.env.DB_PORT || '5432'),
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
};

const pool = new Pool(config);

// Get data file paths from environment
const AIRCRAFT_TYPES_PATH = process.env.AIRCRAFT_TYPES_PATH || path.join(__dirname, '..', '..', 'data-pipeline', 'dist', 'aircraft_types.json');
const AIRLINES_PATH = process.env.AIRLINES_PATH || path.join(__dirname, '..', '..', 'data-pipeline', 'dist', 'airlines.json');

async function loadAircraftTypes() {
  try {
    console.log(`📁 Loading aircraft types from: ${AIRCRAFT_TYPES_PATH}`);
    const data = fs.readFileSync(AIRCRAFT_TYPES_PATH, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('❌ Failed to load aircraft types:', error);
    throw error;
  }
}

async function loadAirlines() {
  try {
    console.log(`📁 Loading airlines from: ${AIRLINES_PATH}`);
    const data = fs.readFileSync(AIRLINES_PATH, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('❌ Failed to load airlines:', error);
    throw error;
  }
}

async function seedAircraftTypes(aircraftTypes) {
  const client = await pool.connect();
  
  try {
    console.log(`🌱 Seeding ${aircraftTypes.length} aircraft types...`);
    
    for (const aircraftType of aircraftTypes) {
      // Validate required fields
      if (!aircraftType.icao_type || !aircraftType.wake || !aircraftType.engines) {
        console.warn(`⚠️ Skipping invalid aircraft type: ${JSON.stringify(aircraftType)}`);
        continue;
      }
      
      try {
        await client.query(`
          INSERT INTO aircraft_types (
            icao_type, wake, engines, dimensions, mtow_kg, cruise_speed_kts,
            max_speed_kts, range_nm, ceiling_ft, climb_rate_fpm,
            takeoff_ground_run_ft, landing_ground_roll_ft, engine_thrust_lbf, notes
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
          ON CONFLICT (icao_type) DO UPDATE SET
            wake = EXCLUDED.wake,
            engines = EXCLUDED.engines,
            dimensions = EXCLUDED.dimensions,
            mtow_kg = EXCLUDED.mtow_kg,
            cruise_speed_kts = EXCLUDED.cruise_speed_kts,
            max_speed_kts = EXCLUDED.max_speed_kts,
            range_nm = EXCLUDED.range_nm,
            ceiling_ft = EXCLUDED.ceiling_ft,
            climb_rate_fpm = EXCLUDED.climb_rate_fpm,
            takeoff_ground_run_ft = EXCLUDED.takeoff_ground_run_ft,
            landing_ground_roll_ft = EXCLUDED.landing_ground_roll_ft,
            engine_thrust_lbf = EXCLUDED.engine_thrust_lbf,
            notes = EXCLUDED.notes,
            updated_at = NOW()
        `, [
          aircraftType.icao_type,
          aircraftType.wake,
          JSON.stringify(aircraftType.engines),
          aircraftType.dimensions ? JSON.stringify(aircraftType.dimensions) : null,
          aircraftType.mtow_kg,
          aircraftType.cruise_speed_kts,
          aircraftType.max_speed_kts,
          aircraftType.range_nm,
          aircraftType.ceiling_ft,
          aircraftType.climb_rate_fpm,
          aircraftType.takeoff_ground_run_ft,
          aircraftType.landing_ground_roll_ft,
          aircraftType.engine_thrust_lbf,
          aircraftType.notes ? JSON.stringify(aircraftType.notes) : null
        ]);
      } catch (error) {
        console.warn(`⚠️ Failed to insert aircraft type ${aircraftType.icao_type}:`, error.message);
      }
    }
    
    console.log('✅ Aircraft types seeded successfully');
  } finally {
    client.release();
  }
}

async function seedAirlines(airlines) {
  const client = await pool.connect();
  
  try {
    console.log(`🌱 Seeding ${airlines.length} airlines...`);
    
    for (const airline of airlines) {
      // Validate required fields
      if (!airline.name || !airline.icao) {
        console.warn(`⚠️ Skipping invalid airline: ${JSON.stringify(airline)}`);
        continue;
      }
      
      try {
        await client.query(`
          INSERT INTO airlines (name, icao, iata, country)
          VALUES ($1, $2, $3, $4)
          ON CONFLICT (icao) DO UPDATE SET
            name = EXCLUDED.name,
            iata = EXCLUDED.iata,
            country = EXCLUDED.country,
            updated_at = NOW()
        `, [
          airline.name,
          airline.icao,
          airline.iata || null,
          airline.country || null
        ]);
      } catch (error) {
        console.warn(`⚠️ Failed to insert airline ${airline.icao}:`, error.message);
      }
    }
    
    console.log('✅ Airlines seeded successfully');
  } finally {
    client.release();
  }
}

async function main() {
  try {
    console.log('🌱 Starting database seeding...');
    
    // Load data from files
    const [aircraftTypes, airlines] = await Promise.all([
      loadAircraftTypes(),
      loadAirlines()
    ]);
    
    // Seed the data
    await seedAircraftTypes(aircraftTypes);
    await seedAirlines(airlines);
    
    console.log('🎉 Database seeding completed successfully');
    process.exit(0);
  } catch (error) {
    console.error('💥 Seeding failed:', error);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

if (require.main === module) {
  main();
}

module.exports = { seedAircraftTypes, seedAirlines };
