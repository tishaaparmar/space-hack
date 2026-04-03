'use client';

import React, { useMemo } from 'react';
import { ComposableMap, Geographies, Geography, Marker, Line } from "react-simple-maps";

const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// PS Ground Stations
const GROUND_STATIONS = [
    { id: "GS-001", name: "ISTRAC", lat: 13.0333, lon: 77.5167 },
    { id: "GS-002", name: "Svalbard", lat: 78.2297, lon: 15.4077 },
    { id: "GS-003", name: "Goldstone", lat: 35.4266, lon: -116.8900 },
    { id: "GS-004", name: "Punta Arenas", lat: -53.1500, lon: -70.9167 },
    { id: "GS-005", name: "IIT Delhi", lat: 28.5450, lon: 77.1926 },
    { id: "GS-006", name: "McMurdo", lat: -77.8463, lon: 166.6682 },
];

interface Satellite {
    id: string;
    lat: number;
    lon: number;
    alt: number;
    fuel_kg: number;
    status: string;
    drift_km?: number;
}

interface GroundTrackMapProps {
    satellites: Satellite[];
    debris: [string, number, number, number][];
    activeManeuvers?: any[];
    trailingPaths?: Record<string, { lat: number; lon: number }[]>;
    simTimestamp?: string;
}

function computeTerminator(simTimestamp: string): [number, number][] {
    // Approximate terminator line based on simulation time
    // Sub-solar point longitude depends on time of day
    let date: Date;
    try {
        date = new Date(simTimestamp);
    } catch {
        date = new Date();
    }
    
    const dayOfYear = Math.floor(
        (date.getTime() - new Date(date.getFullYear(), 0, 0).getTime()) / 86400000
    );
    // Solar declination (approximate)
    const declination = -23.44 * Math.cos((360 / 365) * (dayOfYear + 10) * (Math.PI / 180));
    
    // Sub-solar longitude based on UTC hour
    const hours = date.getUTCHours() + date.getUTCMinutes() / 60;
    const subSolarLon = (12 - hours) * 15; // 15 degrees per hour
    
    // Generate terminator points
    const points: [number, number][] = [];
    for (let lat = -90; lat <= 90; lat += 2) {
        const latRad = lat * Math.PI / 180;
        const decRad = declination * Math.PI / 180;
        
        // Hour angle at terminator
        const cosH = -Math.tan(latRad) * Math.tan(decRad);
        
        if (cosH >= -1 && cosH <= 1) {
            const H = Math.acos(cosH) * 180 / Math.PI;
            points.push([subSolarLon + H, lat]);
        }
    }
    // Close the polygon by going back on the other side
    for (let lat = 90; lat >= -90; lat -= 2) {
        const latRad = lat * Math.PI / 180;
        const decRad = declination * Math.PI / 180;
        const cosH = -Math.tan(latRad) * Math.tan(decRad);
        if (cosH >= -1 && cosH <= 1) {
            const H = Math.acos(cosH) * 180 / Math.PI;
            points.push([subSolarLon - H, lat]);
        }
    }
    
    return points;
}

function satColor(sat: Satellite): string {
    if (sat.status === 'EOL') return '#ef4444';
    if (sat.status === 'DRIFTING') return '#f59e0b';
    if (sat.fuel_kg < 10) return '#f59e0b';
    return '#22d3ee';
}

export default function GroundTrackMap({ satellites, debris, activeManeuvers = [], trailingPaths = {}, simTimestamp = '' }: GroundTrackMapProps) {
    // Only render a subset of debris to keep SVG performant
    const visibleDebris = useMemo(() => {
        if (debris.length <= 500) return debris;
        const step = Math.ceil(debris.length / 500);
        return debris.filter((_, i) => i % step === 0);
    }, [debris]);

    return (
        <div className="w-full h-full bg-[#0a1128] rounded-xl overflow-hidden shadow-[0_0_30px_rgba(0,0,0,0.8)] border border-blue-900/40 relative">
            <h3 className="absolute top-3 left-4 text-blue-400 font-mono text-xs uppercase tracking-widest z-10 bg-black/60 px-2 py-1 rounded flex items-center gap-3">
                <span>Global Ground Track</span>
                <span className="text-gray-600">|</span>
                <span className="text-emerald-400/70 text-[10px]">{satellites.length} SAT</span>
                <span className="text-gray-500 text-[10px]">{debris.length.toLocaleString()} DEB</span>
            </h3>

            {/* Legend */}
            <div className="absolute bottom-3 left-4 z-10 bg-black/70 px-2 py-1.5 rounded text-[9px] font-mono flex gap-3 items-center">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />SAT</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />DRIFT</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" />EOL</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-gray-500 inline-block" style={{borderRadius:'1px'}} />DEB</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-green-500 inline-block" />GS</span>
            </div>
            
            <ComposableMap projectionConfig={{ scale: 140 }} className="w-full h-full">
                <Geographies geography={geoUrl}>
                    {({ geographies }) =>
                        geographies.map((geo) => (
                            <Geography
                                key={geo.rsmKey}
                                geography={geo}
                                fill="#1c2d42"
                                stroke="#2c4d62"
                                strokeWidth={0.5}
                                style={{
                                    default: { outline: "none" },
                                    hover: { outline: "none" },
                                    pressed: { outline: "none" },
                                }}
                            />
                        ))
                    }
                </Geographies>

                {/* Ground Stations */}
                {GROUND_STATIONS.map((gs) => (
                    <Marker key={gs.id} coordinates={[gs.lon, gs.lat]}>
                        <rect x={-3} y={-3} width={6} height={6} fill="#10b981" opacity={0.8} rx={1} />
                        <text x={8} y={3} fontSize={7} fill="#10b981" opacity={0.7} fontFamily="monospace">{gs.name}</text>
                    </Marker>
                ))}

                {/* Debris */}
                {visibleDebris.map((deb, idx) => {
                    const [id, lat, lon] = deb;
                    return (
                        <Marker key={`deb-${idx}`} coordinates={[lon, lat]}>
                            <circle r={1} fill="#6b7280" opacity={0.4} />
                        </Marker>
                    );
                })}

                {/* Trailing Paths */}
                {Object.entries(trailingPaths).map(([satId, path]) => {
                    if (path.length < 2) return null;
                    return path.slice(0, -1).map((p, i) => {
                        const next = path[i + 1];
                        // Skip if crossing the antimeridian
                        if (Math.abs(p.lon - next.lon) > 90) return null;
                        const opacity = 0.15 + (i / path.length) * 0.4;
                        return (
                            <Line
                                key={`trail-${satId}-${i}`}
                                from={[p.lon, p.lat]}
                                to={[next.lon, next.lat]}
                                stroke="#22d3ee"
                                strokeWidth={1}
                                strokeOpacity={opacity}
                            />
                        );
                    });
                })}

                {/* Maneuver Lines (Evasion=red, Recovery=blue) */}
                {activeManeuvers.map((m, idx) => {
                    const isRecovery = m.type === 'RECOVERY';
                    return (
                        <Line
                            key={`maneuver-${idx}`}
                            from={[m.position_before.lon, m.position_before.lat]}
                            to={[m.position_after.lon, m.position_after.lat]}
                            stroke={isRecovery ? "#3b82f6" : "#ef4444"}
                            strokeWidth={isRecovery ? 1.5 : 2}
                            strokeLinecap="round"
                            className="animate-pulse"
                        />
                    );
                })}

                {/* Satellites */}
                {satellites.map((sat, idx) => {
                    const isManeuvering = activeManeuvers.some(m => m.satellite_id === sat.id);
                    const color = isManeuvering ? '#ef4444' : satColor(sat);
                    return (
                        <Marker key={`sat-${sat.id}`} coordinates={[sat.lon, sat.lat]}>
                            <circle r={3.5} fill={color} className="animate-pulse" />
                            <circle r={7} fill="none" stroke={color} strokeWidth={0.8} opacity={0.4} className="animate-ping" />
                            {/* Show drift indicator for drifting satellites */}
                            {sat.status === 'DRIFTING' && (
                                <circle r={10} fill="none" stroke="#f59e0b" strokeWidth={0.5} strokeDasharray="2,2" opacity={0.6} />
                            )}
                        </Marker>
                    );
                })}
            </ComposableMap>
        </div>
    );
}
