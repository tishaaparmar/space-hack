'use client';

import React from 'react';
import { ComposableMap, Geographies, Geography, Marker, Line } from "react-simple-maps";

const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

interface Satellite {
    id: string;
    lat: number;
    lon: number;
    alt: number;
    fuel_kg: number;
    status: string;
}

interface GroundTrackMapProps {
    satellites: Satellite[];
    debris: [string, number, number, number][]; // id, lat, lon, alt
    activeManeuvers?: any[];
}

export default function GroundTrackMap({ satellites, debris, activeManeuvers = [] }: GroundTrackMapProps) {
    return (
        <div className="w-full h-full bg-[#0a1128] rounded-xl overflow-hidden shadow-[0_0_30px_rgba(0,0,0,0.8)] border border-blue-900/40 relative">
            <h3 className="absolute top-4 left-4 text-blue-400 font-mono text-xs uppercase tracking-widest z-10 bg-black/50 p-1 rounded">Global Ground Track</h3>
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

                {/* Render Debris first so they are under satellites */}
                {debris.map((deb, idx) => {
                    const [id, lat, lon] = deb;
                    return (
                        <Marker key={`deb-${id}-${idx}`} coordinates={[lon, lat]}>
                            <circle r={1.5} fill="#6b7280" opacity={0.6} />
                        </Marker>
                    );
                })}

                {/* Render Maneuvers */}
                {activeManeuvers.map((m, idx) => (
                    <Line
                        key={`maneuver-${m.satellite_id}-${idx}`}
                        from={[m.position_before.lon, m.position_before.lat]}
                        to={[m.position_after.lon, m.position_after.lat]}
                        stroke="#ef4444"
                        strokeWidth={2}
                        strokeLinecap="round"
                        className="animate-pulse"
                    />
                ))}

                {/* Render Satellites */}
                {satellites.map((sat, idx) => {
                    const isManeuvering = activeManeuvers.some(m => m.satellite_id === sat.id);
                    return (
                        <Marker key={`sat-${sat.id}-${idx}`} coordinates={[sat.lon, sat.lat]}>
                            <circle r={4} fill={isManeuvering ? "#ef4444" : "#22d3ee"} className="animate-pulse" />
                            <circle r={8} fill="none" stroke={isManeuvering ? "#ef4444" : "#22d3ee"} strokeWidth={1} opacity={isManeuvering ? 0.8 : 0.5} className="animate-ping" />
                        </Marker>
                    );
                })}
            </ComposableMap>
        </div>
    );
}
