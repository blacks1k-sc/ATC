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
const AIRLINES_PATH = process.env.AIRLINES_PATH || path.join(__dirname, '..', '..', 'data-pipeline', 'dist', 'airlines.json');

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

function isValidAirline(airline) {
  // Check if airline has valid ICAO code (3 characters, alphanumeric)
  if (!airline.icao || airline.icao.length !== 3 || !/^[A-Z0-9]{3}$/.test(airline.icao)) {
    return false;
  }
  
  // Check if airline has valid IATA code (2 characters, alphanumeric) or no IATA
  if (airline.iata && airline.iata !== '-' && airline.iata !== '\\N' && airline.iata.length > 2) {
    return false;
  }
  
  // Check if airline has a valid name
  if (!airline.name || airline.name === 'Unknown' || airline.name === 'Private flight') {
    return false;
  }
  
  // Skip airlines with invalid ICAO codes
  const invalidIcaoCodes = ['N/A', 'YYY', 'OTN', 'SMS', 'MFT', 'NCO', 'TYR', 'BUZ'];
  if (invalidIcaoCodes.includes(airline.icao)) {
    return false;
  }
  
  return true;
}

async function seedValidAirlines() {
  const client = await pool.connect();
  
  try {
    console.log('🌱 Loading airlines...');
    const allAirlines = await loadAirlines();
    
    // Filter to only valid airlines
    const validAirlines = allAirlines.filter(isValidAirline);
    console.log(`📊 Found ${validAirlines.length} valid airlines out of ${allAirlines.length} total`);
    
    // Clear existing airlines
    await client.query('DELETE FROM airlines');
    console.log('🗑️ Cleared existing airlines');
    
    console.log(`🌱 Seeding ${validAirlines.length} valid airlines...`);
    
    let successCount = 0;
    let errorCount = 0;
    
    for (const airline of validAirlines) {
      try {
        await client.query(`
          INSERT INTO airlines (name, icao, iata, country)
          VALUES ($1, $2, $3, $4)
        `, [
          airline.name,
          airline.icao,
          airline.iata && airline.iata !== '-' && airline.iata !== '\\N' ? airline.iata : null,
          airline.country || null
        ]);
        successCount++;
      } catch (error) {
        console.warn(`⚠️ Failed to insert airline ${airline.icao}:`, error.message);
        errorCount++;
      }
    }
    
    console.log(`✅ Successfully inserted ${successCount} airlines`);
    if (errorCount > 0) {
      console.log(`⚠️ Failed to insert ${errorCount} airlines`);
    }
    
  } finally {
    client.release();
  }
}

async function main() {
  try {
    console.log('🌱 Starting valid airline seeding...');
    await seedValidAirlines();
    console.log('🎉 Valid airline seeding completed successfully');
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

module.exports = { seedValidAirlines };
