'use client';

import React from 'react';

interface FleetDashboardProps {
    satsCount: number;
    debrisCount: number;
    collisionsDetected: number;
    maneuversExecuted: number;
    avgFuel: number;
    recentManeuvers?: any[];
}

export default function FleetDashboard({ 
    satsCount, 
    debrisCount, 
    collisionsDetected, 
    maneuversExecuted,
    avgFuel,
    recentManeuvers = []
}: FleetDashboardProps) {
    return (
        <div className="flex flex-col gap-4 w-full text-slate-300 font-mono text-sm">
            <div className="bg-gray-800/80 p-4 rounded-lg border border-gray-700 shadow-inner">
                <h3 className="text-gray-400 text-xs mb-2">CONSTELLATION STATUS</h3>
                <div className="flex justify-between items-center mb-1">
                    <span>Active Satellites</span>
                    <span className="text-emerald-400 font-bold">{satsCount}</span>
                </div>
                <div className="flex justify-between items-center">
                    <span>Tracked Debris</span>
                    <span className="text-amber-400 font-bold">{debrisCount}</span>
                </div>
            </div>

            <div className="bg-gray-800/80 p-4 rounded-lg border border-gray-700 shadow-inner">
                <h3 className="text-gray-400 text-xs mb-2">COLLISION AVOIDANCE</h3>
                <div className="flex justify-between items-center mb-1">
                    <span>Active Warnings</span>
                    <span className="text-red-400 font-bold">{collisionsDetected}</span>
                </div>
                <div className="flex justify-between items-center">
                    <span>Maneuvers Executed</span>
                    <span className="text-blue-400 font-bold">{maneuversExecuted}</span>
                </div>
            </div>

            <div className="bg-gray-800/80 p-4 rounded-lg border border-gray-700 shadow-inner">
                <h3 className="text-gray-400 text-xs mb-2">MANEUVER ACTIVITY</h3>
                <div className="flex flex-col gap-2 max-h-32 overflow-y-auto">
                    {recentManeuvers.slice().reverse().slice(0, 5).map((m, i) => (
                        <div key={i} className="text-xs border-l-2 border-red-500 pl-2 py-1 items-start flex flex-col">
                            <span className="text-gray-300 font-bold">{m.satellite_id}</span>
                            <span className="text-gray-400">Δv = {(Math.sqrt(m.delta_v.x**2 + m.delta_v.y**2 + m.delta_v.z**2) * 1000).toFixed(2)} m/s</span>
                            <span className="text-red-400/80">{m.reason}</span>
                        </div>
                    ))}
                    {recentManeuvers.length === 0 && <span className="text-gray-600 italic">No recent maneuvers</span>}
                </div>
            </div>

            <div className="bg-gray-800/80 p-4 rounded-lg border border-gray-700 shadow-inner">
                <h3 className="text-gray-400 text-xs mb-2">FLEET HEALTH</h3>
                <div className="flex justify-between items-center mb-2">
                    <span>Average Fuel</span>
                    <span className="text-gray-100">{avgFuel.toFixed(1)} kg</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2.5">
                    <div className="bg-emerald-500 h-2.5 rounded-full" style={{ width: `${Math.min((avgFuel / 50) * 100, 100)}%` }}></div>
                </div>
            </div>
            
            <div className="mt-auto bg-red-900/20 p-3 rounded border border-red-900/50 flex items-center justify-center animate-pulse">
                <span className="text-red-500 font-bold uppercase tracking-widest text-xs">System Armed</span>
            </div>
        </div>
    );
}
