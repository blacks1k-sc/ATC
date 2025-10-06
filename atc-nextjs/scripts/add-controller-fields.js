#!/usr/bin/env node

/**
 * Migration script to add controller and related fields to aircraft_instances table
 */

const { Pool } = require('pg');

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'atc_system',
  user: process.env.DB_USER || 'nrup',
  password: process.env.DB_PASSWORD || 'password',
});

async function runMigration() {
  console.log('🔄 Adding controller and related fields to aircraft_instances table...');
  
  try {
    await pool.query(`
      ALTER TABLE aircraft_instances 
      ADD COLUMN IF NOT EXISTS controller VARCHAR(20) DEFAULT 'ENGINE',
      ADD COLUMN IF NOT EXISTS phase VARCHAR(20) DEFAULT 'CRUISE',
      ADD COLUMN IF NOT EXISTS last_event_fired VARCHAR(100),
      ADD COLUMN IF NOT EXISTS target_speed_kts INTEGER,
      ADD COLUMN IF NOT EXISTS target_heading_deg INTEGER,
      ADD COLUMN IF NOT EXISTS target_altitude_ft INTEGER,
      ADD COLUMN IF NOT EXISTS vertical_speed_fpm INTEGER,
      ADD COLUMN IF NOT EXISTS distance_to_airport_nm DECIMAL(8,2);
    `);
    
    console.log('✅ Successfully added controller and related fields');
    
    // Update existing aircraft to have ENGINE controller
    const result = await pool.query(`
      UPDATE aircraft_instances 
      SET controller = 'ENGINE' 
      WHERE controller IS NULL;
    `);
    
    console.log(`✅ Updated ${result.rowCount} existing aircraft to ENGINE controller`);
    
  } catch (error) {
    console.error('❌ Migration failed:', error);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

runMigration();
