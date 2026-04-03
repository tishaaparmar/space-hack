'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import GroundTrackMap from '@/components/GroundTrackMap';
import ConjunctionRadar from '@/components/ConjunctionRadar';
import FleetDashboard from '@/components/FleetDashboard';
import ManeuverTimeline from '@/components/ManeuverTimeline';

const API_BASE = "http://localhost:8000";
const MAX_TRAIL_LENGTH = 45; // ~90 min at 120s steps

export default function Dashboard() {
    const [satellites, setSatellites] = useState<any[]>([]);
    const [debris, setDebris] = useState<any[]>([]);
    const [collisions, setCollisions] = useState(0);
    const [maneuvers, setManeuvers] = useState(0);
    const [running, setRunning] = useState(false);
    const [timeStr, setTimeStr] = useState("");
    const [simTimestamp, setSimTimestamp] = useState("");
    const [maneuversHistory, setManeuversHistory] = useState<any[]>([]);
    const [fleetStats, setFleetStats] = useState<any>({});
    const [radarItems, setRadarItems] = useState<any[]>([]);
    
    // Trailing paths: { satId: [{lat, lon}, ...] }
    const trailingPathsRef = useRef<Record<string, { lat: number; lon: number }[]>>({});
    const [trailingPaths, setTrailingPaths] = useState<Record<string, { lat: number; lon: number }[]>>({});

    useEffect(() => {
        const updateTime = () => setTimeStr(new Date().toISOString().split('T')[1].split('.')[0] + " UTC");
        updateTime();
        const timer = setInterval(updateTime, 1000);
        return () => clearInterval(timer);
    }, []);
    
    const targetSatId = satellites.length > 0 ? satellites[0].id : "";

    const fetchSnapshot = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/visualization/snapshot`);
            const data = await res.json();
            setSatellites(data.satellites || []);
            setDebris(data.debris_cloud || []);
            setManeuversHistory(data.maneuvers || []);
            setFleetStats(data.fleet_stats || {});
            setSimTimestamp(data.timestamp || '');
            
            // Update trailing paths
            const paths = trailingPathsRef.current;
            for (const sat of (data.satellites || [])) {
                if (!paths[sat.id]) paths[sat.id] = [];
                paths[sat.id].push({ lat: sat.lat, lon: sat.lon });
                if (paths[sat.id].length > MAX_TRAIL_LENGTH) {
                    paths[sat.id] = paths[sat.id].slice(-MAX_TRAIL_LENGTH);
                }
            }
            trailingPathsRef.current = paths;
            setTrailingPaths({ ...paths });
            
            // Radar: closest debris to first satellite
            if (data.satellites.length > 0 && data.debris_cloud.length > 0) {
                const sat = data.satellites[0];
                const closeItems = data.debris_cloud.map((d: any) => {
                    const dx = d[2] - sat.lon;
                    const dy = d[1] - sat.lat;
                    const dist = Math.sqrt(dx*dx + dy*dy) * 111.0;
                    const angle = Math.atan2(dy, dx) * (180 / Math.PI);
                    return { id: d[0], dist, angle };
                }).filter((item: any) => item.dist < 50).sort((a: any, b: any) => a.dist - b.dist).slice(0, 15);
                setRadarItems(closeItems);
            }
        } catch (err) {
            console.error("Failed to fetch snapshot", err);
        }
    }, []);

    useEffect(() => {
        const stepSimulation = async () => {
            if (!running) return;
            try {
                const res = await fetch(`${API_BASE}/api/simulate/step`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ step_seconds: 120.0 })
                });
                const data = await res.json();
                setCollisions(prev => prev + (data.collisions_detected || 0));
                setManeuvers(prev => prev + (data.maneuvers_executed || 0));
                fetchSnapshot();
            } catch (err) {
                console.error("Step failed", err);
            }
        };

        fetchSnapshot();

        let interval: NodeJS.Timeout;
        if (running) {
            interval = setInterval(stepSimulation, 1000);
        } else {
            interval = setInterval(fetchSnapshot, 2000);
        }

        return () => clearInterval(interval);
    }, [running, fetchSnapshot]);
    
    const avgFuel = satellites.length > 0 
        ? satellites.reduce((acc, s) => acc + s.fuel_kg, 0) / satellites.length 
        : 50.0;

    return (
        <main className="flex min-h-screen flex-col bg-gray-950 p-3 text-white font-sans selection:bg-emerald-500/30">
            {/* Header */}
            <header className="flex items-center justify-between pb-3 border-b border-gray-800 mb-4">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.4)]">
                        <span className="font-bold text-lg leading-none">A</span>
                    </div>
                    <div>
                        <h1 className="text-xl font-bold tracking-tight text-gray-100">Autonomous Constellation Manager</h1>
                        <p className="text-xs text-emerald-500/80 font-mono tracking-wider">ORBITAL OPERATIONS DASHBOARD</p>
                    </div>
                </div>
                
                <div className="flex items-center gap-4">
                    {/* Sim timestamp */}
                    {simTimestamp && (
                        <div className="flex flex-col text-right font-mono text-xs">
                            <span className="text-gray-500">SIM TIME</span>
                            <span className="text-emerald-400/80">{simTimestamp.replace('T', ' ').replace('.000Z', '')}</span>
                        </div>
                    )}
                    <button 
                        onClick={() => setRunning(!running)}
                        className={`px-6 py-2 rounded font-mono text-sm font-bold uppercase tracking-wide transition-all ${
                            running 
                            ? "bg-red-500/20 text-red-500 border border-red-500/50 hover:bg-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.2)]" 
                            : "bg-emerald-500/20 text-emerald-500 border border-emerald-500/50 hover:bg-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]"
                        }`}
                    >
                        {running ? "HALT SIMULATION" : "RUN SIMULATION"}
                    </button>
                    <div className="flex flex-col text-right font-mono text-xs min-w-[80px]">
                        <span className="text-gray-500">SYSTEM TIME</span>
                        <span className="text-gray-300">{timeStr || "--:--:-- UTC"}</span>
                    </div>
                </div>
            </header>

            {/* Main Content Grid */}
            <div className="flex-1 grid grid-cols-12 gap-4" style={{ minHeight: 0 }}>
                
                {/* Left Panel: Analytics */}
                <div className="col-span-3 flex flex-col gap-3 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 100px)' }}>
                    <FleetDashboard 
                        satsCount={satellites.length}
                        debrisCount={debris.length}
                        collisionsDetected={collisions}
                        maneuversExecuted={maneuvers}
                        avgFuel={avgFuel}
                        recentManeuvers={maneuversHistory}
                        satellites={satellites}
                        fleetStats={fleetStats}
                    />
                </div>

                {/* Center Panel: Ground Track + Timeline */}
                <div className="col-span-6 flex flex-col gap-3">
                    <div className="flex-1 min-h-[400px]">
                        <GroundTrackMap 
                            satellites={satellites} 
                            debris={debris} 
                            activeManeuvers={maneuversHistory}
                            trailingPaths={trailingPaths}
                            simTimestamp={simTimestamp}
                        />
                    </div>
                    {/* Maneuver Timeline below map */}
                    <div className="h-44">
                        <ManeuverTimeline 
                            maneuvers={maneuversHistory}
                            simTimestamp={simTimestamp}
                        />
                    </div>
                </div>

                {/* Right Panel: Radar + Event Log */}
                <div className="col-span-3 flex flex-col h-full gap-3">
                    <div className="flex-1 min-h-[280px]">
                        <ConjunctionRadar satId={targetSatId} items={radarItems} />
                    </div>
                    <div className="h-44 bg-gray-900 border border-gray-800 rounded-lg p-3 font-mono text-xs text-gray-400 overflow-y-auto w-full shadow-inner ring-1 ring-white/5">
                        <h4 className="text-gray-500 mb-2 border-b border-gray-800 pb-1">EVENT LOG</h4>
                        <div className="flex flex-col gap-1">
                            {maneuversHistory.slice().reverse().slice(0, 8).map((m: any, i: number) => {
                                const isRecovery = m.type === 'RECOVERY';
                                return (
                                    <React.Fragment key={`log-${i}`}>
                                        <span className={isRecovery ? "text-blue-400" : "text-red-400"}>
                                            &gt; {m.satellite_id} {isRecovery ? 'recovery burn' : `evaded ${m.debris_id}`}
                                        </span>
                                        <span className="text-gray-600 text-[10px]">
                                            {m.timestamp} | Δv={(m.dv_magnitude_ms || 0).toFixed(2)}m/s | fuel={m.fuel_remaining_kg?.toFixed(1) ?? '?'}kg
                                        </span>
                                    </React.Fragment>
                                );
                            })}
                            <span className="text-emerald-500/70">&gt; System initialized.</span>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}
