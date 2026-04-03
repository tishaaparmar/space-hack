'use client';

import React from 'react';

interface FleetDashboardProps {
    satsCount: number;
    debrisCount: number;
    collisionsDetected: number;
    maneuversExecuted: number;
    avgFuel: number;
    recentManeuvers?: any[];
    satellites?: any[];
    fleetStats?: any;
}

function fuelColor(fuel: number): string {
    if (fuel < 5) return '#ef4444';      // red - critical
    if (fuel < 15) return '#f59e0b';     // amber - low
    if (fuel < 30) return '#eab308';     // yellow - moderate
    return '#10b981';                     // green - healthy
}

function statusBadge(status: string) {
    const colors: Record<string, string> = {
        'NOMINAL': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        'DRIFTING': 'bg-amber-500/20 text-amber-400 border-amber-500/30',
        'EOL': 'bg-red-500/20 text-red-400 border-red-500/30',
    };
    return colors[status] || colors['NOMINAL'];
}

export default function FleetDashboard({ 
    satsCount, 
    debrisCount, 
    collisionsDetected, 
    maneuversExecuted,
    avgFuel,
    recentManeuvers = [],
    satellites = [],
    fleetStats = {}
}: FleetDashboardProps) {
    const fleetUptime = fleetStats?.fleet_uptime_pct ?? 100;
    const totalDv = fleetStats?.total_dv_consumed_ms ?? 0;
    const pendingRecovery = fleetStats?.pending_recovery_burns ?? 0;

    // Sort satellites by fuel (lowest first for urgency)
    const sortedSats = [...satellites].sort((a, b) => a.fuel_kg - b.fuel_kg);
    // Show max 8 most critical
    const criticalSats = sortedSats.slice(0, 8);

    return (
        <div className="flex flex-col gap-3 w-full text-slate-300 font-mono text-sm">
            {/* Constellation Status */}
            <div className="bg-gray-800/80 p-3 rounded-lg border border-gray-700 shadow-inner">
                <h3 className="text-gray-400 text-xs mb-2">CONSTELLATION STATUS</h3>
                <div className="flex justify-between items-center mb-1">
                    <span>Active Satellites</span>
                    <span className="text-emerald-400 font-bold">{satsCount}</span>
                </div>
                <div className="flex justify-between items-center mb-1">
                    <span>Tracked Debris</span>
                    <span className="text-amber-400 font-bold">{debrisCount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center">
                    <span>Fleet Uptime</span>
                    <span className={`font-bold ${fleetUptime > 95 ? 'text-emerald-400' : fleetUptime > 80 ? 'text-amber-400' : 'text-red-400'}`}>
                        {fleetUptime.toFixed(1)}%
                    </span>
                </div>
            </div>

            {/* Collision Avoidance */}
            <div className="bg-gray-800/80 p-3 rounded-lg border border-gray-700 shadow-inner">
                <h3 className="text-gray-400 text-xs mb-2">COLLISION AVOIDANCE</h3>
                <div className="flex justify-between items-center mb-1">
                    <span>Active Warnings</span>
                    <span className="text-red-400 font-bold">{collisionsDetected}</span>
                </div>
                <div className="flex justify-between items-center mb-1">
                    <span>Maneuvers Executed</span>
                    <span className="text-blue-400 font-bold">{maneuversExecuted}</span>
                </div>
                <div className="flex justify-between items-center mb-1">
                    <span>Pending Recovery</span>
                    <span className="text-purple-400 font-bold">{pendingRecovery}</span>
                </div>
                <div className="flex justify-between items-center">
                    <span>Total Δv Used</span>
                    <span className="text-cyan-400 font-bold">{totalDv.toFixed(1)} m/s</span>
                </div>
            </div>

            {/* Maneuver Activity */}
            <div className="bg-gray-800/80 p-3 rounded-lg border border-gray-700 shadow-inner">
                <h3 className="text-gray-400 text-xs mb-2">MANEUVER ACTIVITY</h3>
                <div className="flex flex-col gap-1.5 max-h-28 overflow-y-auto">
                    {recentManeuvers.slice().reverse().slice(0, 6).map((m, i) => {
                        const isRecovery = m.type === 'RECOVERY';
                        const borderColor = isRecovery ? 'border-blue-500' : 'border-red-500';
                        const label = isRecovery ? 'RECOVERY' : 'EVASION';
                        const labelColor = isRecovery ? 'text-blue-400' : 'text-red-400';
                        return (
                            <div key={i} className={`text-xs border-l-2 ${borderColor} pl-2 py-0.5 flex flex-col`}>
                                <div className="flex items-center gap-2">
                                    <span className={`${labelColor} font-bold text-[10px] px-1 rounded border ${isRecovery ? 'border-blue-500/30 bg-blue-500/10' : 'border-red-500/30 bg-red-500/10'}`}>{label}</span>
                                    <span className="text-gray-300 font-bold">{m.satellite_id}</span>
                                </div>
                                <span className="text-gray-500">Δv = {(m.dv_magnitude_ms || (Math.sqrt(m.delta_v.x**2 + m.delta_v.y**2 + m.delta_v.z**2) * 1000)).toFixed(2)} m/s | fuel: {(m.fuel_remaining_kg ?? 0).toFixed(1)} kg</span>
                            </div>
                        );
                    })}
                    {recentManeuvers.length === 0 && <span className="text-gray-600 italic">No recent maneuvers</span>}
                </div>
            </div>

            {/* Per-Satellite Fuel Gauges */}
            <div className="bg-gray-800/80 p-3 rounded-lg border border-gray-700 shadow-inner">
                <h3 className="text-gray-400 text-xs mb-2">SATELLITE FUEL STATUS</h3>
                <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto">
                    {criticalSats.map((sat) => {
                        const pct = Math.min((sat.fuel_kg / 50) * 100, 100);
                        return (
                            <div key={sat.id} className="flex items-center gap-2">
                                <span className="text-[10px] text-gray-400 w-24 truncate" title={sat.id}>{sat.id.replace('SAT-','')}</span>
                                <div className="flex-1 bg-gray-700/50 rounded-full h-2 relative overflow-hidden">
                                    <div 
                                        className="h-2 rounded-full transition-all duration-500"
                                        style={{ width: `${pct}%`, backgroundColor: fuelColor(sat.fuel_kg) }}
                                    />
                                </div>
                                <span className="text-[10px] w-12 text-right" style={{ color: fuelColor(sat.fuel_kg) }}>
                                    {sat.fuel_kg.toFixed(1)}
                                </span>
                                <span className={`text-[8px] px-1 rounded border ${statusBadge(sat.status)}`}>
                                    {sat.status === 'DRIFTING' ? 'DFT' : sat.status === 'EOL' ? 'EOL' : 'NOM'}
                                </span>
                            </div>
                        );
                    })}
                    {satellites.length > 8 && (
                        <span className="text-[10px] text-gray-600 text-center">+{satellites.length - 8} more satellites</span>
                    )}
                </div>
                {/* Fleet average bar */}
                <div className="mt-2 pt-2 border-t border-gray-700">
                    <div className="flex justify-between items-center mb-1">
                        <span className="text-[10px] text-gray-500">FLEET AVG</span>
                        <span className="text-xs" style={{ color: fuelColor(avgFuel) }}>{avgFuel.toFixed(1)} kg</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                        <div className="h-2 rounded-full transition-all duration-500" 
                            style={{ width: `${Math.min((avgFuel / 50) * 100, 100)}%`, backgroundColor: fuelColor(avgFuel) }} 
                        />
                    </div>
                </div>
            </div>
            
            <div className="mt-auto bg-red-900/20 p-2 rounded border border-red-900/50 flex items-center justify-center animate-pulse">
                <span className="text-red-500 font-bold uppercase tracking-widest text-xs">System Armed</span>
            </div>
        </div>
    );
}
