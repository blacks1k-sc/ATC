import { Pool, PoolClient } from 'pg';
import Redis from 'ioredis';

// Environment configuration with defaults
const DB_CONFIG = {
  user: process.env.DB_USER || 'postgres',
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'atc_system',
  password: process.env.DB_PASSWORD || 'password',
  port: parseInt(process.env.DB_PORT || '5432'),
  max: parseInt(process.env.DB_POOL_SIZE || '20'),
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
};


const REDIS_CONFIG = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD,
  retryDelayOnFailover: 100,
  maxRetriesPerRequest: 3,
};

// PostgreSQL connection pool (optional - will be null if DB not available)
export const pool = process.env.SKIP_DB === 'true' ? null : new Pool(DB_CONFIG);

// Redis connection (optional - will be null if Redis not available)
export const redis = process.env.SKIP_REDIS === 'true' ? null : new Redis(REDIS_CONFIG);

// Database health check
export async function checkDatabaseConnection() {
  if (!pool) {
    console.log('Database connection skipped (SKIP_DB=true)');
    return false;
  }
  try {
    const client = await pool.connect();
    await client.query('SELECT 1');
    client.release();
    return true;
  } catch (error) {
    console.error('Database connection failed:', error);
    return false;
  }
}

// Redis health check
export async function checkRedisConnection() {
  if (!redis) {
    console.log('Redis connection skipped (SKIP_REDIS=true)');
    return false;
  }
  try {
    await redis.ping();
    return true;
  } catch (error) {
    console.error('Redis connection failed:', error);
    return false;
  }
}

// Type definitions
export interface AircraftType {
  id: number;
  icao_type: string;
  wake: string;
  engines: {
    count: number;
    type: string;
  };
  dimensions?: {
    length_m: number;
    wingspan_m: number;
    height_m: number;
  };
  mtow_kg: number;
  cruise_speed_kts: number;
  max_speed_kts: number;
  range_nm: number;
  ceiling_ft: number;
  climb_rate_fpm: number;
  takeoff_ground_run_ft: number;
  landing_ground_roll_ft: number;
  engine_thrust_lbf: number;
  notes?: any;
  created_at: Date;
  updated_at: Date;
}

export interface Airline {
  id: number;
  name: string;
  icao: string;
  iata?: string;
  country?: string;
  created_at: Date;
  updated_at: Date;
}

export interface AircraftInstance {
  id: number;
  icao24: string;
  registration: string;
  callsign: string;
  aircraft_type_id: number;
  airline_id: number;
  position: {
    lat: number;
    lon: number;
    altitude_ft: number;
    heading: number;
    speed_kts: number;
  };
  status: string;
  squawk_code?: string;
  flight_plan?: any;
  created_at: Date;
  updated_at: Date;
  // Joined data
  aircraft_type?: AircraftType;
  airline?: Airline;
}

export interface Event {
  id: number;
  timestamp: Date;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL';
  type: string;
  message: string;
  details?: any;
  aircraft_id?: number;
  sector?: string;
  frequency?: string;
  direction?: 'TX' | 'RX' | 'CPDLC' | 'XFER' | 'SYS';
  created_at: Date;
  // Joined data
  aircraft?: AircraftInstance;
}

// Repository classes
export class AircraftTypeRepository {
  constructor(private client: PoolClient) {}

  async findAll(): Promise<AircraftType[]> {
    const result = await this.client.query('SELECT * FROM aircraft_types ORDER BY icao_type');
    return result.rows;
  }

  async findByIcaoType(icaoType: string): Promise<AircraftType | null> {
    const result = await this.client.query('SELECT * FROM aircraft_types WHERE icao_type = $1', [icaoType]);
    return result.rows[0] || null;
  }

  async findById(id: number): Promise<AircraftType | null> {
    const result = await this.client.query('SELECT * FROM aircraft_types WHERE id = $1', [id]);
    return result.rows[0] || null;
  }
}

export class AirlineRepository {
  constructor(private client: PoolClient) {}

  async findAll(): Promise<Airline[]> {
    const result = await this.client.query('SELECT * FROM airlines ORDER BY name');
    return result.rows;
  }

  async findByIcao(icao: string): Promise<Airline | null> {
    const result = await this.client.query('SELECT * FROM airlines WHERE icao = $1', [icao]);
    return result.rows[0] || null;
  }

  async findById(id: number): Promise<Airline | null> {
    const result = await this.client.query('SELECT * FROM airlines WHERE id = $1', [id]);
    return result.rows[0] || null;
  }
}

export class AircraftInstanceRepository {
  constructor(private client: PoolClient) {}

  async create(data: {
    icao24: string;
    registration: string;
    callsign: string;
    aircraft_type_id: number;
    airline_id: number;
    position: any;
    status?: string;
    squawk_code?: string;
    flight_plan?: any;
    flight_type?: string;
    controller?: string;
  }): Promise<AircraftInstance> {
    const result = await this.client.query(`
      INSERT INTO aircraft_instances (
        icao24, registration, callsign, aircraft_type_id, airline_id,
        position, status, squawk_code, flight_plan, flight_type, controller
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
      RETURNING *
    `, [
      data.icao24,
      data.registration,
      data.callsign,
      data.aircraft_type_id,
      data.airline_id,
      JSON.stringify(data.position),
      data.status || 'active',
      data.squawk_code,
      data.flight_plan ? JSON.stringify(data.flight_plan) : null,
      data.flight_type || 'ARRIVAL',
      data.controller || 'ENGINE'
    ]);
    return result.rows[0];
  }

  async findById(id: number): Promise<AircraftInstance | null> {
    const result = await this.client.query(`
      SELECT ai.*, at.*, al.*
      FROM aircraft_instances ai
      LEFT JOIN aircraft_types at ON ai.aircraft_type_id = at.id
      LEFT JOIN airlines al ON ai.airline_id = al.id
      WHERE ai.id = $1
    `, [id]);
    
    if (!result.rows[0]) return null;
    
    const row = result.rows[0];
    return {
      id: row.id,
      icao24: row.icao24,
      registration: row.registration,
      callsign: row.callsign,
      aircraft_type_id: row.aircraft_type_id,
      airline_id: row.airline_id,
      position: row.position,
      status: row.status,
      squawk_code: row.squawk_code,
      flight_plan: row.flight_plan,
      created_at: row.created_at,
      updated_at: row.updated_at,
      aircraft_type: row.icao_type ? {
        id: row.aircraft_type_id,
        icao_type: row.icao_type,
        wake: row.wake,
        engines: row.engines,
        dimensions: row.dimensions,
        mtow_kg: row.mtow_kg,
        cruise_speed_kts: row.cruise_speed_kts,
        max_speed_kts: row.max_speed_kts,
        range_nm: row.range_nm,
        ceiling_ft: row.ceiling_ft,
        climb_rate_fpm: row.climb_rate_fpm,
        takeoff_ground_run_ft: row.takeoff_ground_run_ft,
        landing_ground_roll_ft: row.landing_ground_roll_ft,
        engine_thrust_lbf: row.engine_thrust_lbf,
        notes: row.notes,
        created_at: row.created_at,
        updated_at: row.updated_at
      } : undefined,
      airline: row.name ? {
        id: row.airline_id,
        name: row.name,
        icao: row.icao,
        iata: row.iata,
        country: row.country,
        created_at: row.created_at,
        updated_at: row.updated_at
      } : undefined
    };
  }

  async findByIcao24(icao24: string): Promise<AircraftInstance | null> {
    const result = await this.client.query('SELECT * FROM aircraft_instances WHERE icao24 = $1', [icao24]);
    return result.rows[0] || null;
  }

  async findByCallsign(callsign: string): Promise<AircraftInstance | null> {
    const result = await this.client.query('SELECT * FROM aircraft_instances WHERE callsign = $1', [callsign]);
    return result.rows[0] || null;
  }

  async findAllActive(): Promise<AircraftInstance[]> {
    const result = await this.client.query(`
      SELECT ai.*, at.*, al.*
      FROM aircraft_instances ai
      LEFT JOIN aircraft_types at ON ai.aircraft_type_id = at.id
      LEFT JOIN airlines al ON ai.airline_id = al.id
      WHERE ai.status = 'active'
      ORDER BY ai.created_at DESC
    `);
    
    return result.rows.map(row => ({
      id: row.id,
      icao24: row.icao24,
      registration: row.registration,
      callsign: row.callsign,
      aircraft_type_id: row.aircraft_type_id,
      airline_id: row.airline_id,
      position: row.position,
      status: row.status,
      squawk_code: row.squawk_code,
      flight_plan: row.flight_plan,
      flight_type: row.flight_type,
      controller: row.controller,
      phase: row.phase,
      last_event_fired: row.last_event_fired,
      target_speed_kts: row.target_speed_kts,
      target_heading_deg: row.target_heading_deg,
      target_altitude_ft: row.target_altitude_ft,
      vertical_speed_fpm: row.vertical_speed_fpm,
      distance_to_airport_nm: row.distance_to_airport_nm,
      created_at: row.created_at,
      updated_at: row.updated_at,
      aircraft_type: row.icao_type ? {
        id: row.aircraft_type_id,
        icao_type: row.icao_type,
        wake: row.wake,
        engines: row.engines,
        dimensions: row.dimensions,
        mtow_kg: row.mtow_kg,
        cruise_speed_kts: row.cruise_speed_kts,
        max_speed_kts: row.max_speed_kts,
        range_nm: row.range_nm,
        ceiling_ft: row.ceiling_ft,
        climb_rate_fpm: row.climb_rate_fpm,
        takeoff_ground_run_ft: row.takeoff_ground_run_ft,
        landing_ground_roll_ft: row.landing_ground_roll_ft,
        engine_thrust_lbf: row.engine_thrust_lbf,
        notes: row.notes,
        created_at: row.created_at,
        updated_at: row.updated_at
      } : undefined,
      airline: row.name ? {
        id: row.airline_id,
        name: row.name,
        icao: row.icao,
        iata: row.iata,
        country: row.country,
        created_at: row.created_at,
        updated_at: row.updated_at
      } : undefined
    }));
  }

  async updatePosition(id: number, position: any): Promise<void> {
    await this.client.query(
      'UPDATE aircraft_instances SET position = $1, updated_at = NOW() WHERE id = $2',
      [JSON.stringify(position), id]
    );
  }

  async updateStatus(id: number, status: string): Promise<void> {
    await this.client.query(
      'UPDATE aircraft_instances SET status = $1, updated_at = NOW() WHERE id = $2',
      [status, id]
    );
  }
}

export class EventRepository {
  constructor(private client: PoolClient) {}

  async create(data: {
    level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL';
    type: string;
    message: string;
    details?: any;
    aircraft_id?: number;
    sector?: string;
    frequency?: string;
    direction?: 'TX' | 'RX' | 'CPDLC' | 'XFER' | 'SYS';
  }): Promise<Event> {
    const result = await this.client.query(`
      INSERT INTO events (level, type, message, details, aircraft_id, sector, frequency, direction)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      RETURNING *
    `, [
      data.level,
      data.type,
      data.message,
      data.details ? JSON.stringify(data.details) : null,
      data.aircraft_id,
      data.sector,
      data.frequency,
      data.direction
    ]);
    return result.rows[0];
  }

  async findRecent(limit: number = 100, filters?: {
    level?: string;
    type?: string;
    aircraft_id?: number;
    sector?: string;
  }): Promise<Event[]> {
    let query = `
      SELECT e.*, ai.icao24, ai.callsign, ai.registration
      FROM events e
      LEFT JOIN aircraft_instances ai ON e.aircraft_id = ai.id
      WHERE 1=1
    `;
    const params: any[] = [];
    let paramCount = 0;

    if (filters?.level) {
      paramCount++;
      query += ` AND e.level = $${paramCount}`;
      params.push(filters.level);
    }

    if (filters?.type) {
      paramCount++;
      query += ` AND e.type = $${paramCount}`;
      params.push(filters.type);
    }

    if (filters?.aircraft_id) {
      paramCount++;
      query += ` AND e.aircraft_id = $${paramCount}`;
      params.push(filters.aircraft_id);
    }

    if (filters?.sector) {
      paramCount++;
      query += ` AND e.sector = $${paramCount}`;
      params.push(filters.sector);
    }

    query += ` ORDER BY e.timestamp DESC LIMIT $${paramCount + 1}`;
    params.push(limit);

    const result = await this.client.query(query, params);
    return result.rows;
  }
}

// Database transaction helper
export async function withTransaction<T>(callback: (client: PoolClient) => Promise<T>): Promise<T> {
  if (!pool) {
    throw new Error('Database not available');
  }
  
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await callback(client);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}

// Load aircraft types from data pipeline (legacy function for backward compatibility)
export async function loadAircraftTypes(): Promise<any[]> {
  try {
    const fs = await import('fs');
    const path = await import('path');
    const dataPath = process.env.AIRCRAFT_TYPES_PATH || path.join(process.cwd(), '../data-pipeline/dist/aircraft_types.json');
    const data = fs.readFileSync(dataPath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Failed to load aircraft types:', error);
    return [];
  }
}

// Load airlines from data pipeline (legacy function for backward compatibility)
export async function loadAirlines(): Promise<any[]> {
  try {
    const fs = await import('fs');
    const path = await import('path');
    const dataPath = process.env.AIRLINES_PATH || path.join(process.cwd(), '../data-pipeline/dist/airlines.json');
    const data = fs.readFileSync(dataPath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Failed to load airlines:', error);
    return [];
  }
}
