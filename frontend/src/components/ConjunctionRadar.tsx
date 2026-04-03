'use client';

import React from 'react';

type RadarItem = {
    id: string;
    dist: number; // km
    angle: number; // degrees relative to sat heading
};

interface ConjunctionRadarProps {
    satId: string;
    items: RadarItem[];
}

export default function ConjunctionRadar({ satId, items }: ConjunctionRadarProps) {
    const MAX_RADAR_DIST = 50; // 50 km outer ring (realistic conjunction scale)

    // Define colors based on PS risk thresholds
    const getColor = (dist: number) => {
        if (dist < 1.0) return '#ef4444'; // Red — Critical (< 1 km, collision zone is 0.1 km)
        if (dist < 5.0) return '#f59e0b'; // Yellow — Warning (< 5 km)
        return '#22c55e'; // Green — Safe (> 5 km)
    };

    return (
        <div className="flex flex-col items-center bg-gray-900 border border-gray-700 rounded-lg p-4 w-full h-full relative overflow-hidden ring-1 ring-inset ring-white/10 shadow-2xl">
            <h3 className="text-emerald-400 font-mono text-xs uppercase tracking-widest mb-4 z-10">Conjunction Radar: {satId || "NONE"}</h3>
            
            <div className="relative w-64 h-64 border-2 border-emerald-900/50 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.2)]">
                {/* Crosshairs */}
                <div className="absolute w-full h-[1px] bg-emerald-700/30"></div>
                <div className="absolute h-full w-[1px] bg-emerald-700/30"></div>
                
                {/* Distance Rings */}
                <div className="absolute w-48 h-48 border border-emerald-700/40 rounded-full border-dashed"></div>
                <div className="absolute w-32 h-32 border border-emerald-600/50 rounded-full"></div>
                <div className="absolute w-16 h-16 border border-emerald-500/60 rounded-full border-dashed shadow-[0_0_10px_rgba(239,68,68,0.2)]"></div>
                
                {/* Center dot (Satellite) */}
                <div className="absolute w-3 h-3 bg-white rounded-full shadow-[0_0_10px_white] z-10"></div>
                
                {/* Debris Objects */}
                {items.map((item, idx) => {
                    const radiusRatio = Math.min(item.dist / MAX_RADAR_DIST, 1);
                    const R = 128; // Outer radius in pixels
                    
                    const r_px = radiusRatio * R;
                    // angle assumes 0 is top
                    const theta = (item.angle - 90) * (Math.PI / 180);
                    const x = 128 + r_px * Math.cos(theta); // 128 comes from w-64 / 2 (since 1 rem = 16px, w-64 = 256px -> center is 128)
                    const y = 128 + r_px * Math.sin(theta);
                    
                    const color = getColor(item.dist);
                    
                    return (
                        <div 
                            key={idx}
                            title={`Dist: ${item.dist.toFixed(2)} km`}
                            className="absolute w-2 h-2 rounded-full transform -translate-x-1/2 -translate-y-1/2 animate-pulse"
                            style={{ 
                                left: `${x}px`, 
                                top: `${y}px`, 
                                backgroundColor: color,
                                boxShadow: `0 0 8px ${color}`
                            }}
                        />
                    );
                })}
            </div>
            
            <div className="mt-4 flex gap-4 text-xs font-mono">
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_5px_red]"></span> &lt; 1 km</div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500 shadow-[0_0_5px_yellow]"></span> &lt; 5 km</div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_5px_green]"></span> &gt; 5 km</div>
            </div>
        </div>
    );
}
