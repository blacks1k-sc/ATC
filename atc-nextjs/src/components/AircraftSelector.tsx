'use client';

import React, { useState, useEffect, useRef } from 'react';

interface AircraftSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  onAircraftGenerated: (aircraft: any) => void;
}

interface AircraftType {
  icao_type: string;
  wake: string;
  engines: {
    count: number;
    type: string;
  };
  mtow_kg: number;
  cruise_speed_kts: number;
  notes?: any;
}

interface Airline {
  name: string;
  icao: string;
  iata: string;
}

export default function AircraftSelector({ isOpen, onClose, onAircraftGenerated }: AircraftSelectorProps) {
  const [aircraftData, setAircraftData] = useState<{ aircraftTypes: AircraftType[], airlines: Airline[] } | null>(null);
  const [selectedAircraft, setSelectedAircraft] = useState<string>('');
  const [selectedAirline, setSelectedAirline] = useState<string>('');
  const [aircraftSearch, setAircraftSearch] = useState<string>('');
  const [airlineSearch, setAirlineSearch] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [showAircraftList, setShowAircraftList] = useState<boolean>(false);
  const [showAirlineList, setShowAirlineList] = useState<boolean>(false);
  
  const aircraftRef = useRef<HTMLDivElement>(null);
  const airlineRef = useRef<HTMLDivElement>(null);

  // Load aircraft data when component opens
  useEffect(() => {
    if (isOpen && !aircraftData) {
      loadAircraftData();
    }
  }, [isOpen]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (aircraftRef.current && !aircraftRef.current.contains(event.target as Node)) {
        setShowAircraftList(false);
      }
      if (airlineRef.current && !airlineRef.current.contains(event.target as Node)) {
        setShowAirlineList(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
      onAircraftGenerated(result);
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
    aircraftSearch === '' || aircraft.icao_type.toLowerCase().includes(aircraftSearch.toLowerCase())
  ) || [];

  // Debug logging
  if (aircraftSearch && filteredAircraftTypes.length === 0) {
    console.log('Search term:', aircraftSearch);
    console.log('Available aircraft:', aircraftData?.aircraftTypes.map(a => a.icao_type));
  }

  const filteredAirlines = aircraftData?.airlines.filter(airline =>
    airlineSearch === '' || 
    airline.name.toLowerCase().includes(airlineSearch.toLowerCase()) ||
    airline.icao.toLowerCase().includes(airlineSearch.toLowerCase())
  ) || [];

  if (!isOpen) return null;

  return (
    <>
    <div 
      className="fixed top-0 left-0 w-full h-full z-[9999] pointer-events-none"
      style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: 9999 }}
      onClick={onClose}
    >
      <div 
        className="absolute bg-gray-900 border border-green-500 rounded-lg p-3 shadow-2xl pointer-events-auto"
        style={{ 
          position: 'absolute', 
          top: '80px', 
          left: '50%', 
          transform: 'translateX(-50%)', 
          width: '400px',
          backgroundColor: '#1f2937',
          border: '1px solid #10b981',
          borderRadius: '8px',
          padding: '12px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          pointerEvents: 'auto'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-green-400">Generate Aircraft</h2>
          <button
            onClick={onClose}
            className="text-green-400 hover:text-green-300 text-xl"
          >
            ×
          </button>
        </div>

        {error && (
          <div className="mb-3 p-2 bg-red-900 border border-red-500 text-red-300 rounded text-sm">
            {error}
          </div>
        )}

        <div className="space-y-3">
          {/* Aircraft Selection */}
          <div className="relative" ref={aircraftRef}>
            <label className="block text-sm font-medium text-green-400 mb-1">
              Aircraft Type
            </label>
            <input
              type="text"
              placeholder="Search aircraft..."
              value={aircraftSearch}
              onChange={(e) => {
                setAircraftSearch(e.target.value);
                setShowAircraftList(true);
              }}
              onFocus={() => setShowAircraftList(true)}
              className="w-full p-2 bg-gray-800 border border-green-500 rounded text-green-400 placeholder-gray-500 focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
            
            {showAircraftList && (
              <div 
                className="absolute z-10 w-full mt-1 bg-gray-800 border border-green-500 rounded overflow-y-auto" 
                style={{ 
                  maxHeight: '200px',
                  overflowY: 'auto',
                  scrollbarWidth: 'thin',
                  scrollbarColor: '#10b981 #1f2937'
                }}
              >
                {filteredAircraftTypes.length === 0 ? (
                  <div className="p-2 text-gray-400 text-sm">
                    No aircraft found. Available: A318, A319, A320, A321, A332, A333, A343, A346, A35K, A359, BE58
                  </div>
                ) : (
                  filteredAircraftTypes.map((aircraft) => (
                    <div
                      key={aircraft.icao_type}
                      onClick={() => {
                        setSelectedAircraft(aircraft.icao_type);
                        setAircraftSearch(aircraft.icao_type);
                        setShowAircraftList(false);
                      }}
                      className="p-2 cursor-pointer hover:bg-gray-700 text-green-400 text-sm border-b border-gray-700"
                    >
                      <div className="font-medium">{aircraft.icao_type}</div>
                      <div className="text-xs text-gray-400">
                        {aircraft.engines.count} {aircraft.engines.type} | Wake: {aircraft.wake}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Airline Selection */}
          <div className="relative" ref={airlineRef}>
            <label className="block text-sm font-medium text-green-400 mb-1">
              Airline
            </label>
            <input
              type="text"
              placeholder="Search airline..."
              value={airlineSearch}
              onChange={(e) => {
                setAirlineSearch(e.target.value);
                setShowAirlineList(true);
              }}
              onFocus={() => setShowAirlineList(true)}
              className="w-full p-2 bg-gray-800 border border-green-500 rounded text-green-400 placeholder-gray-500 focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
            
            {showAirlineList && (
              <div 
                className="absolute z-10 w-full mt-1 bg-gray-800 border border-green-500 rounded overflow-y-auto" 
                style={{ 
                  maxHeight: '200px',
                  overflowY: 'auto',
                  scrollbarWidth: 'thin',
                  scrollbarColor: '#10b981 #1f2937'
                }}
              >
                {filteredAirlines.length === 0 ? (
                  <div className="p-2 text-gray-400 text-sm">
                    No airlines found. Try searching by name or ICAO code.
                  </div>
                ) : (
                  filteredAirlines.map((airline, index) => (
                    <div
                      key={`${airline.icao}-${airline.name}-${index}`}
                      onClick={() => {
                        setSelectedAirline(`${airline.icao}-${airline.name}`);
                        setAirlineSearch(`${airline.icao}-${airline.name}`);
                        setShowAirlineList(false);
                      }}
                      className="p-2 cursor-pointer hover:bg-gray-700 text-green-400 text-sm border-b border-gray-700"
                    >
                      <div className="font-medium">{airline.name}</div>
                      <div className="text-xs text-gray-400">ICAO: {airline.icao}</div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-3 flex justify-end space-x-2">
          <button
            onClick={onClose}
            className="px-3 py-1 text-gray-400 bg-gray-800 border border-gray-600 rounded text-sm hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleGenerate}
            disabled={!selectedAircraft || !selectedAirline || loading}
            className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>
    </div>
    </>
  );
}
