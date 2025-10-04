#!/usr/bin/env node

const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// Database connection
const pool = new Pool({
  user: process.env.DB_USER || 'nrup',
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'atc_system',
  password: process.env.DB_PASSWORD || '',
  port: parseInt(process.env.DB_PORT || '5432'),
});

async function migrateWaypoints() {
  console.log('🚀 Starting waypoint migration...');
  
  try {
    // Check if waypoints table exists
    const tableCheck = await pool.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'waypoints'
      );
    `);
    
    if (!tableCheck.rows[0].exists) {
      console.log('📋 Creating waypoints table...');
      
      // Create waypoints table
      await pool.query(`
        CREATE TABLE IF NOT EXISTS waypoints (
          id SERIAL PRIMARY KEY,
          name VARCHAR(10) UNIQUE NOT NULL,
          lat DECIMAL(10, 7) NOT NULL,
          lon DECIMAL(11, 7) NOT NULL,
          description TEXT,
          type VARCHAR(20),
          airport_icao VARCHAR(4),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
      `);
      
      // Create procedures table
      await pool.query(`
        CREATE TABLE IF NOT EXISTS procedures (
          id SERIAL PRIMARY KEY,
          name VARCHAR(50) NOT NULL,
          type VARCHAR(10) NOT NULL,
          runway_id VARCHAR(10),
          airport_icao VARCHAR(4) NOT NULL,
          waypoint_sequence JSONB NOT NULL,
          altitude_restrictions JSONB,
          speed_restrictions JSONB,
          description TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(name, airport_icao)
        );
      `);
      
      // Create gates table
      await pool.query(`
        CREATE TABLE IF NOT EXISTS gates (
          id SERIAL PRIMARY KEY,
          gate_number VARCHAR(10) UNIQUE NOT NULL,
          terminal VARCHAR(5),
          lat DECIMAL(10, 7) NOT NULL,
          lon DECIMAL(11, 7) NOT NULL,
          airport_icao VARCHAR(4) NOT NULL,
          status VARCHAR(20) DEFAULT 'available',
          occupied_by_aircraft_id INTEGER,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
      `);
      
      // Create taxiways table
      await pool.query(`
        CREATE TABLE IF NOT EXISTS taxiways (
          id SERIAL PRIMARY KEY,
          name VARCHAR(10) NOT NULL,
          from_point VARCHAR(50),
          to_point VARCHAR(50),
          path JSONB,
          length_meters DECIMAL(10, 2),
          airport_icao VARCHAR(4) NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
      `);
      
      // Create aircraft_history table
      await pool.query(`
        CREATE TABLE IF NOT EXISTS aircraft_history (
          id SERIAL PRIMARY KEY,
          original_aircraft_id INTEGER,
          icao24 VARCHAR(6) NOT NULL,
          registration VARCHAR(10) NOT NULL,
          callsign VARCHAR(10) NOT NULL,
          aircraft_type_id INTEGER,
          airline_id INTEGER,
          operation_type VARCHAR(10),
          spawn_time TIMESTAMP,
          completion_time TIMESTAMP,
          spawn_location JSONB,
          exit_location JSONB,
          assigned_procedure VARCHAR(50),
          assigned_runway VARCHAR(10),
          assigned_gate VARCHAR(10),
          total_flight_time_seconds INTEGER,
          total_events_logged INTEGER,
          archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
      `);
      
      // Create runway_occupancy table
      await pool.query(`
        CREATE TABLE IF NOT EXISTS runway_occupancy (
          id SERIAL PRIMARY KEY,
          runway_id VARCHAR(10) NOT NULL,
          aircraft_id INTEGER,
          occupancy_type VARCHAR(20),
          occupied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          cleared_at TIMESTAMP,
          is_occupied BOOLEAN DEFAULT TRUE
        );
      `);
      
      console.log('✅ New tables created successfully');
    } else {
      console.log('✅ Waypoints table already exists');
    }
    
    // Check if aircraft_instances table exists and add new columns
    const aircraftTableCheck = await pool.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'aircraft_instances'
      );
    `);
    
    if (aircraftTableCheck.rows[0].exists) {
      console.log('📋 Adding new columns to aircraft_instances...');
      
      // Add new columns one by one
      const newColumns = [
        'assigned_procedure_id INTEGER',
        'current_waypoint_index INTEGER DEFAULT 0',
        'next_waypoint_name VARCHAR(10)',
        'operation_type VARCHAR(10) DEFAULT \'ARRIVAL\'',
        'spawn_gate VARCHAR(10)',
        'assigned_taxiway_route JSONB',
        'go_around_count INTEGER DEFAULT 0',
        'cleared_altitude INTEGER',
        'cleared_speed INTEGER',
        'cleared_heading INTEGER'
      ];
      
      for (const column of newColumns) {
        try {
          await pool.query(`ALTER TABLE aircraft_instances ADD COLUMN IF NOT EXISTS ${column.split(' ')[0]} ${column.split(' ').slice(1).join(' ')};`);
        } catch (error) {
          if (!error.message.includes('already exists')) {
            console.warn(`⚠️  Warning adding column ${column.split(' ')[0]}: ${error.message}`);
          }
        }
      }
      
      console.log('✅ New columns added to aircraft_instances');
    }
    
    // Create indexes
    console.log('📋 Creating indexes...');
    const indexes = [
      'CREATE INDEX IF NOT EXISTS idx_aircraft_operation_type ON aircraft_instances(operation_type);',
      'CREATE INDEX IF NOT EXISTS idx_gates_status ON gates(status);',
      'CREATE INDEX IF NOT EXISTS idx_runway_occupancy ON runway_occupancy(runway_id, is_occupied);',
      'CREATE INDEX IF NOT EXISTS idx_aircraft_history_operation ON aircraft_history(operation_type);'
    ];
    
    for (const index of indexes) {
      try {
        await pool.query(index);
      } catch (error) {
        console.warn(`⚠️  Warning creating index: ${error.message}`);
      }
    }
    
    console.log('✅ Migration completed successfully!');
    
  } catch (error) {
    console.error('❌ Migration failed:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

migrateWaypoints();
