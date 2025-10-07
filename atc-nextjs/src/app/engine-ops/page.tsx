'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { AircraftInstance } from '@/types/atc';

interface EngineOpsAircraft extends AircraftInstance {
  sector?: string;
  distance_to_airport_nm?: number;
  vertical_speed_fpm?: number;
  last_event_fired?: string;
  controller?: string;
  phase?: string;
}

export default function EngineOpsPage() {
  const [aircraft, setAircraft] = useState<EngineOpsAircraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [sectorFilter, setSectorFilter] = useState<string>('ENTRY');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Calculate sector based on distance
  const calculateSector = (distance: number | string | undefined): string => {
    if (!distance) return 'UNKNOWN';
    const dist = typeof distance === 'string' ? parseFloat(distance) : distance;
    if (isNaN(dist)) return 'UNKNOWN';
    if (dist > 30) return 'ENTRY';
    if (dist > 10) return 'ENROUTE';
    if (dist > 3) return 'APPROACH';
    return 'RUNWAY';
  };

  // Fetch aircraft data
  const fetchAircraft = async () => {
    try {
      const response = await fetch('/api/aircraft');
      if (!response.ok) {
        throw new Error('Failed to fetch aircraft data');
      }
      const data = await response.json();
      
      // Add computed sector based on distance
      const aircraftWithSectors = data.aircraft.map((ac: EngineOpsAircraft) => ({
        ...ac,
        sector: ac.sector || calculateSector(ac.distance_to_airport_nm)
      }));
      
      // Filter by sector if specified
      const filteredAircraft = sectorFilter === 'ALL' 
        ? aircraftWithSectors 
        : aircraftWithSectors.filter((ac: EngineOpsAircraft) => ac.sector === sectorFilter);
      
      setAircraft(filteredAircraft);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch aircraft');
    } finally {
      setLoading(false);
    }
  };

  // Set up real-time updates
  useEffect(() => {
    if (!autoRefresh) return;

    // Initial fetch
    fetchAircraft();

    // Set up interval for updates
    const interval = setInterval(fetchAircraft, 1000); // Update every second

    // Set up SSE for real-time updates
    const eventSource = new EventSource('/api/events/stream');
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'aircraft.position_updated' || data.type === 'aircraft.created') {
          fetchAircraft(); // Refresh data when aircraft position updates
        }
      } catch (err) {
        console.error('Error parsing SSE data:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
    };

    return () => {
      clearInterval(interval);
      eventSource.close();
    };
  }, [autoRefresh, sectorFilter]);

  // Format distance for display
  const formatDistance = (distance: number | string | undefined) => {
    if (distance === undefined || distance === null) return 'N/A';
    const dist = typeof distance === 'string' ? parseFloat(distance) : distance;
    if (isNaN(dist)) return 'N/A';
    return `${dist.toFixed(1)} NM`;
  };

  // Format altitude for display
  const formatAltitude = (altitude: number | string | undefined) => {
    if (altitude === undefined || altitude === null) return 'N/A';
    const alt = typeof altitude === 'string' ? parseFloat(altitude) : altitude;
    if (isNaN(alt)) return 'N/A';
    return `FL${Math.round(alt / 100)}`;
  };

  // Format speed for display
  const formatSpeed = (speed: number | string | undefined) => {
    if (speed === undefined || speed === null) return 'N/A';
    const spd = typeof speed === 'string' ? parseFloat(speed) : speed;
    if (isNaN(spd)) return 'N/A';
    return `${spd.toFixed(0)} kts`;
  };

  // Format heading for display
  const formatHeading = (heading: number | string | undefined) => {
    if (heading === undefined || heading === null) return 'N/A';
    const hdg = typeof heading === 'string' ? parseFloat(heading) : heading;
    if (isNaN(hdg)) return 'N/A';
    return `${hdg.toFixed(0)}°`;
  };

  // Format vertical speed for display
  const formatVerticalSpeed = (vSpeed: number | string | undefined) => {
    if (vSpeed === undefined || vSpeed === null) return 'N/A';
    const vs = typeof vSpeed === 'string' ? parseFloat(vSpeed) : vSpeed;
    if (isNaN(vs)) return 'N/A';
    const sign = vs >= 0 ? '+' : '';
    return `${sign}${vs.toFixed(0)} fpm`;
  };

  // Get sector color
  const getSectorColor = (sector: string | undefined) => {
    switch (sector) {
      case 'ENTRY': return 'text-blue-400';
      case 'ENROUTE': return 'text-green-400';
      case 'APPROACH': return 'text-yellow-400';
      case 'RUNWAY': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  // Get phase color
  const getPhaseColor = (phase: string | undefined) => {
    switch (phase) {
      case 'CRUISE': return 'text-blue-300';
      case 'DESCENT': return 'text-yellow-300';
      case 'APPROACH': return 'text-orange-300';
      case 'FINAL': return 'text-red-300';
      case 'TOUCHDOWN': return 'text-green-300';
      default: return 'text-gray-300';
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="text-gray-400 hover:text-white mr-4">
                ← Back to ATC
              </Link>
              <h1 className="text-2xl font-bold text-green-400">ENGINE OPS</h1>
              <span className="ml-4 px-3 py-1 bg-blue-600 text-sm rounded-full">
                Real-time Aircraft Monitoring
              </span>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Auto-refresh toggle */}
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm">Auto-refresh</span>
              </label>
              
              {/* Last update time */}
              {lastUpdate && (
                <span className="text-sm text-gray-400">
                  Last: {lastUpdate.toLocaleTimeString()}
                </span>
              )}
              
              {/* Manual refresh */}
              <button
                onClick={fetchAircraft}
                disabled={loading}
                className="px-3 py-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-sm rounded"
              >
                {loading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center space-x-6">
            {/* Sector Filter */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium">Sector:</label>
              <select
                value={sectorFilter}
                onChange={(e) => setSectorFilter(e.target.value)}
                className="bg-gray-700 border border-gray-600 rounded px-3 py-1 text-sm"
              >
                <option value="ENTRY">ENTRY (30-60 NM)</option>
                <option value="ENROUTE">ENROUTE (10-30 NM)</option>
                <option value="APPROACH">APPROACH (3-10 NM)</option>
                <option value="RUNWAY">RUNWAY (0-3 NM)</option>
                <option value="ALL">ALL SECTORS</option>
              </select>
            </div>

            {/* Aircraft Count */}
            <div className="text-sm text-gray-400">
              {aircraft.length} aircraft in {sectorFilter} sector
            </div>

            {/* Error Display */}
            {error && (
              <div className="text-red-400 text-sm">
                Error: {error}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Sector Information Panel */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div style={{ display: 'flex', flexDirection: 'row', gap: '12px', width: '100%' }}>
          {/* ENTRY Sector */}
          <div className="bg-gray-800 rounded-lg border border-blue-500 p-2" style={{ flex: '1', minWidth: '0' }}>
            <h3 className="text-xs font-bold text-blue-400 mb-1">ENTRY</h3>
            <div className="text-xs text-gray-400 space-y-0.5">
              <div>30-60 NM</div>
              <div>FL200-FL600</div>
              <div className="pt-1 text-blue-300 text-xs font-semibold">Fixes:</div>
              <div className="grid grid-cols-2 gap-0.5 text-xs">
                <div>BOXUM (N)</div>
                <div>DUVOS (NE)</div>
                <div>NUBER (E)</div>
                <div>KEDMA (SE)</div>
                <div>PILMU (S)</div>
                <div>VERKO (SW)</div>
                <div>IMEBA (W)</div>
                <div>RAGID (NW)</div>
              </div>
            </div>
          </div>

          {/* ENROUTE Sector */}
          <div className="bg-gray-800 rounded-lg border border-green-500 p-2" style={{ flex: '1', minWidth: '0' }}>
            <h3 className="text-xs font-bold text-green-400 mb-1">ENROUTE</h3>
            <div className="text-xs text-gray-400 space-y-0.5">
              <div>10-30 NM</div>
              <div>FL180-FL350</div>
              <div className="pt-1 text-green-300 text-xs font-semibold">Operations:</div>
              <div>• Descent</div>
              <div>• 280-320 kts</div>
              <div>• -2000 fpm</div>
            </div>
          </div>

          {/* APPROACH Sector */}
          <div className="bg-gray-800 rounded-lg border border-yellow-500 p-2" style={{ flex: '1', minWidth: '0' }}>
            <h3 className="text-xs font-bold text-yellow-400 mb-1">APPROACH</h3>
            <div className="text-xs text-gray-400 space-y-0.5">
              <div>3-10 NM</div>
              <div>SFC-FL180</div>
              <div className="pt-1 text-yellow-300 text-xs font-semibold">Operations:</div>
              <div>• Sequencing</div>
              <div>• 180-220 kts</div>
              <div>• Stabilize 3000</div>
            </div>
          </div>

          {/* RUNWAY Sector */}
          <div className="bg-gray-800 rounded-lg border border-red-500 p-2" style={{ flex: '1', minWidth: '0' }}>
            <h3 className="text-xs font-bold text-red-400 mb-1">RUNWAY</h3>
            <div className="text-xs text-gray-400 space-y-0.5">
              <div>0-3 NM</div>
              <div>SFC-3000 ft</div>
              <div className="pt-1 text-red-300 text-xs font-semibold">Operations:</div>
              <div>• Final approach</div>
              <div>• 140-170 kts</div>
              <div>• Glideslope 3.0°</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        {loading && aircraft.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400 mx-auto mb-4"></div>
              <p className="text-gray-400">Loading aircraft data...</p>
            </div>
          </div>
        ) : aircraft.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">No aircraft in {sectorFilter} sector</div>
            <div className="text-gray-500 text-sm">
              Generate some aircraft to see them here
            </div>
          </div>
        ) : (
          <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
            {/* Table Header */}
            <div className="bg-gray-700 px-6 py-3 border-b border-gray-600">
              <h2 className="text-lg font-semibold text-green-400">
                Live Aircraft Data - {sectorFilter} Sector
              </h2>
              <p className="text-sm text-gray-400 mt-1">
                Real-time updates from Engine (1 Hz tick rate)
              </p>
            </div>

            {/* Table */}
            <div className="overflow-x-auto" style={{ border: '2px solid #9CA3AF' }}>
              <table className="w-full" style={{ borderCollapse: 'collapse', border: '2px solid #9CA3AF' }}>
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Callsign
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Aircraft
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Airline
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      ICAO24
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Position
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Distance
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Altitude
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Speed
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Heading
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      V/S
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Sector
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Phase
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Controller
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Targets
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider" style={{ border: '1px solid #9CA3AF' }}>
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-gray-800">
                  {aircraft.map((ac) => (
                    <tr key={ac.id} className="hover:bg-gray-750 text-xs border-b border-gray-400">
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-sm font-mono text-blue-400">#{ac.id}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-sm font-bold text-white">{ac.callsign}</div>
                        <div className="text-xs text-gray-400 font-mono">{ac.registration}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-sm font-mono text-cyan-400">{ac.aircraft_type?.icao_type || 'N/A'}</div>
                        <div className="text-xs text-gray-400">Wake: {ac.aircraft_type?.wake || 'N/A'}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-sm text-gray-300">{ac.airline?.icao || 'N/A'}</div>
                        <div className="text-xs text-gray-400">{ac.airline?.name?.substring(0, 20) || 'N/A'}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-xs font-mono text-purple-400">{ac.icao24}</div>
                        <div className="text-xs text-gray-500">Squawk: {ac.squawk_code || 'N/A'}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-xs font-mono text-gray-300">
                          {ac.position?.lat?.toFixed(4) || 'N/A'}°N
                        </div>
                        <div className="text-xs font-mono text-gray-300">
                          {ac.position?.lon?.toFixed(4) || 'N/A'}°W
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-sm font-bold text-yellow-400">{formatDistance(ac.distance_to_airport_nm)}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-sm font-bold text-green-400">{formatAltitude(ac.position?.altitude_ft)}</div>
                        <div className="text-xs text-gray-400">{ac.position?.altitude_ft?.toFixed(0)} ft</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-sm font-bold text-blue-400">{formatSpeed(ac.position?.speed_kts)}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-sm font-mono text-orange-400">{formatHeading(ac.position?.heading)}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className={`text-sm font-mono ${(ac.vertical_speed_fpm || 0) > 0 ? 'text-green-400' : (ac.vertical_speed_fpm || 0) < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                          {formatVerticalSpeed(ac.vertical_speed_fpm)}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <span className={`text-sm font-bold ${getSectorColor(ac.sector)}`}>
                          {ac.sector || 'N/A'}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <span className={`text-sm font-bold ${getPhaseColor(ac.phase)}`}>
                          {ac.phase || 'N/A'}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-sm text-gray-300">{ac.controller || 'ENGINE'}</div>
                        <div className="text-xs text-gray-500">{ac.last_event_fired?.substring(0, 15) || 'None'}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <div className="text-xs text-gray-400">
                          <div>ALT: {ac.target_altitude_ft ? `${ac.target_altitude_ft} ft` : 'N/A'}</div>
                          <div>SPD: {ac.target_speed_kts ? `${ac.target_speed_kts} kts` : 'N/A'}</div>
                          <div>HDG: {ac.target_heading_deg ? `${ac.target_heading_deg}°` : 'N/A'}</div>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap" style={{ border: '1px solid #9CA3AF' }}>
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          ac.status === 'active' 
                            ? 'bg-green-900 text-green-300 border border-green-500' 
                            : 'bg-gray-700 text-gray-300 border border-gray-400'
                        }`}>
                          {ac.status || 'active'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Table Footer */}
            <div className="bg-gray-700 px-6 py-3 border-t border-gray-600">
              <div className="flex items-center justify-between text-sm text-gray-400">
                <div>
                  Showing {aircraft.length} aircraft
                </div>
                <div>
                  Engine tick rate: 1 Hz | Updates: Real-time via SSE
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
