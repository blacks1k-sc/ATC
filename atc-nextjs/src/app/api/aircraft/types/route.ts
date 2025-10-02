import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

export async function GET() {
  try {
    // Load aircraft types and airlines from data pipeline
    const dataPipelinePath = path.join(process.cwd(), '..', 'data-pipeline', 'dist');
    const aircraftTypesPath = path.join(dataPipelinePath, 'aircraft_types.json');
    const airlinesPath = path.join(dataPipelinePath, 'airlines.json');

    const [aircraftTypesData, airlinesData] = await Promise.all([
      fs.readFile(aircraftTypesPath, 'utf-8'),
      fs.readFile(airlinesPath, 'utf-8')
    ]);

    const aircraftTypes = JSON.parse(aircraftTypesData);
    const airlines = JSON.parse(airlinesData);

    // Filter airlines for Canadian/international operations (same logic as generate_canadian.py)
    const canadianKeywords = ["canada", "canadian", "montreal", "toronto", "vancouver", "calgary", "edmonton", "winnipeg", "halifax", "quebec"];
    const internationalMajors = ["AAL", "UAL", "DAL", "BAW", "AFR", "DLH", "KLM", "SWR", "VIR", "QFA", "ANA", "JAL", "CCA", "CES", "CSN", "UAE", "QTR", "ETD"];

    const filteredAirlines = airlines.filter((a: any) =>
      canadianKeywords.some(kw => a.name.toLowerCase().includes(kw)) ||
      internationalMajors.includes(a.icao) ||
      internationalMajors.includes(a.iata)
    );

    // Add some common Canadian ICAO codes if not already present
    const canadianIcaoCodes = ["ACA", "JZA", "TSC", "MPE", "POE", "WJA", "WEN", "FLE"];
    for (const icaoCode of canadianIcaoCodes) {
        if (!filteredAirlines.some((a: any) => a.icao === icaoCode)) {
            const foundAirline = airlines.find((a: any) => a.icao === icaoCode);
            if (foundAirline) {
                filteredAirlines.push(foundAirline);
            }
        }
    }

    return NextResponse.json({
      aircraftTypes,
      airlines: filteredAirlines
    });
  } catch (error) {
    console.error('Error loading aircraft data:', error);
    return NextResponse.json(
      { error: 'Failed to load aircraft data' },
      { status: 500 }
    );
  }
}
