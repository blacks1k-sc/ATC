#!/usr/bin/env node

/**
 * Add sector field to aircraft_instances table
 */

const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'atc_system',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'password',
});

async function addSectorField() {
  const client = await pool.connect();
  
  try {
    console.log('🔧 Adding sector field to aircraft_instances table...');
    
    // Add sector column
    await client.query(`
      ALTER TABLE aircraft_instances 
      ADD COLUMN IF NOT EXISTS sector VARCHAR(20);
    `);
    
    console.log('✅ Sector field added successfully');
    
    // Verify the column exists
    const result = await client.query(`
      SELECT column_name, data_type 
      FROM information_schema.columns 
      WHERE table_name = 'aircraft_instances' 
      AND column_name = 'sector';
    `);
    
    if (result.rows.length > 0) {
      console.log('✅ Verified: sector column exists');
      console.log('   Type:', result.rows[0].data_type);
    } else {
      console.log('⚠️  Warning: Could not verify sector column');
    }
    
  } catch (error) {
    console.error('❌ Error adding sector field:', error);
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

addSectorField()
  .then(() => {
    console.log('\n✅ Migration complete');
    process.exit(0);
  })
  .catch((error) => {
    console.error('\n❌ Migration failed:', error);
    process.exit(1);
  });


