'use client';

import React, { useState, useEffect } from 'react';
import { AircraftType, Airline } from '@/lib/database';

interface AircraftGeneratorProps {
  isOpen: boolean;
  onClose: () => void;
  onAircraftGenerated: (aircraft: any) => void;
}

interface AircraftData {
  aircraftTypes: AircraftType[];
  airlines: Airline[];
}

export default function AircraftGenerator({ isOpen, onClose, onAircraftGenerated }: AircraftGeneratorProps) {
  const [aircraftData, setAircraftData] = useState<AircraftData | null>(null);
  const [selectedAircraft, setSelectedAircraft] = useState<string>('');
  const [selectedAirline, setSelectedAirline] = useState<string>('');
  const [aircraftSearch, setAircraftSearch] = useState<string>('');
  const [airlineSearch, setAirlineSearch] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  // Load aircraft types and airlines on component mount
  useEffect(() => {
    if (isOpen && !aircraftData) {
      loadAircraftData();
    }
  }, [isOpen]);

  const loadAircraftData = async () => {
    try {
      const response = await fetch('/api/aircraft/types');
      if (!response.ok) {
        throw new Error('Failed to load aircraft data');
      }
      const data = await response.json();
      setAircraftData(data);
    } catch (err) {
      setError('Failed to load aircraft data');
      console.error(err);
    }
  };

  const handleGenerate = async () => {
    if (!selectedAircraft || !selectedAirline) {
      setError('Please select both aircraft type and airline');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/aircraft/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          aircraftType: selectedAircraft,
          airline: selectedAirline,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate aircraft');
      }

      const result = await response.json();
      onAircraftGenerated(result.aircraft);
      onClose();
      
      // Reset form
      setSelectedAircraft('');
      setSelectedAirline('');
      setAircraftSearch('');
      setAirlineSearch('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate aircraft');
    } finally {
      setLoading(false);
    }
  };

  const filteredAircraftTypes = aircraftData?.aircraftTypes.filter(aircraft =>
    aircraft.icao_type.toLowerCase().includes(aircraftSearch.toLowerCase()) ||
    (aircraft.notes?.source?.[0] || '').toLowerCase().includes(aircraftSearch.toLowerCase())
  ) || [];

  const filteredAirlines = aircraftData?.airlines.filter(airline =>
    airline.name.toLowerCase().includes(airlineSearch.toLowerCase()) ||
    airline.icao.toLowerCase().includes(airlineSearch.toLowerCase())
  ) || [];

  const selectedAircraftData = aircraftData?.aircraftTypes.find(at => at.icao_type === selectedAircraft);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-900">Generate New Aircraft</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Aircraft Selection */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Aircraft Type</h3>
            
            <div className="relative">
              <input
                type="text"
                placeholder="Search aircraft by ICAO code or manufacturer..."
                value={aircraftSearch}
                onChange={(e) => setAircraftSearch(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-lg">
              {filteredAircraftTypes.map((aircraft) => (
                <div
                  key={aircraft.icao_type}
                  onClick={() => setSelectedAircraft(aircraft.icao_type)}
                  className={`p-3 cursor-pointer hover:bg-gray-50 border-b border-gray-100 ${
                    selectedAircraft === aircraft.icao_type ? 'bg-blue-50 border-blue-200' : ''
                  }`}
                >
                  <div className="font-medium text-gray-900">{aircraft.icao_type}</div>
                  <div className="text-sm text-gray-600">
                    {aircraft.notes?.source?.[0] || 'Unknown Aircraft'}
                  </div>
                  <div className="text-xs text-gray-500">
                    Wake: {aircraft.wake} | Engines: {aircraft.engines.count} {aircraft.engines.type}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Airline Selection */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Airline</h3>
            
            <div className="relative">
              <input
                type="text"
                placeholder="Search airline by name or ICAO code..."
                value={airlineSearch}
                onChange={(e) => setAirlineSearch(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-lg">
              {filteredAirlines.map((airline) => (
                <div
                  key={airline.icao}
                  onClick={() => setSelectedAirline(`${airline.icao}-${airline.name}`)}
                  className={`p-3 cursor-pointer hover:bg-gray-50 border-b border-gray-100 ${
                    selectedAirline === `${airline.icao}-${airline.name}` ? 'bg-blue-50 border-blue-200' : ''
                  }`}
                >
                  <div className="font-medium text-gray-900">{airline.name}</div>
                  <div className="text-sm text-gray-600">ICAO: {airline.icao}</div>
                  {airline.iata && (
                    <div className="text-xs text-gray-500">IATA: {airline.iata}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Aircraft Details Preview */}
        {selectedAircraftData && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="text-lg font-semibold text-gray-900 mb-3">Aircraft Specifications</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-700">Wake Category:</span>
                <span className="ml-2 text-gray-900">{selectedAircraftData.wake}</span>
              </div>
              <div>
                <span className="font-medium text-gray-700">Engines:</span>
                <span className="ml-2 text-gray-900">{selectedAircraftData.engines.count} {selectedAircraftData.engines.type}</span>
              </div>
              <div>
                <span className="font-medium text-gray-700">MTOW:</span>
                <span className="ml-2 text-gray-900">{selectedAircraftData.mtow_kg?.toLocaleString()} kg</span>
              </div>
              <div>
                <span className="font-medium text-gray-700">Cruise Speed:</span>
                <span className="ml-2 text-gray-900">{selectedAircraftData.cruise_speed_kts} kts</span>
              </div>
              <div>
                <span className="font-medium text-gray-700">Range:</span>
                <span className="ml-2 text-gray-900">{selectedAircraftData.range_nm?.toLocaleString()} nm</span>
              </div>
              <div>
                <span className="font-medium text-gray-700">Ceiling:</span>
                <span className="ml-2 text-gray-900">{selectedAircraftData.ceiling_ft?.toLocaleString()} ft</span>
              </div>
              <div>
                <span className="font-medium text-gray-700">Climb Rate:</span>
                <span className="ml-2 text-gray-900">{selectedAircraftData.climb_rate_fpm?.toLocaleString()} fpm</span>
              </div>
              <div>
                <span className="font-medium text-gray-700">Thrust:</span>
                <span className="ml-2 text-gray-900">{selectedAircraftData.engine_thrust_lbf?.toLocaleString()} lbf</span>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleGenerate}
            disabled={!selectedAircraft || !selectedAirline || loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Generating...' : 'Generate Aircraft'}
          </button>
        </div>
      </div>
    </div>
  );
}
