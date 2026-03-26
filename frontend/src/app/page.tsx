'use client';

import React, { useEffect, useState, useRef } from 'react';
import GroundTrackMap from '@/components/GroundTrackMap';
import ConjunctionRadar from '@/components/ConjunctionRadar';
import FleetDashboard from '@/components/FleetDashboard';

const API_BASE = "http://localhost:8000";

export default function Dashboard() {
    const [satellites, setSatellites] = useState<any[]>([]);
    const [debris, setDebris] = useState<any[]>([]);
    const [collisions, setCollisions] = useState(0);
    const [maneuvers, setManeuvers] = useState(0);
    const [running, setRunning] = useState(false);
    const [timeStr, setTimeStr] = useState("");
    const [maneuversHistory, setManeuversHistory] = useState<any[]>([]);

    useEffect(() => {
        const updateTime = () => setTimeStr(new Date().toISOString().split('T')[1].split('.')[0] + " UTC");
        updateTime();
        const timer = setInterval(updateTime, 1000);
        return () => clearInterval(timer);
    }, []);
    
    // Select a target satellite for the radar view
    const targetSatId = satellites.length > 0 ? satellites[0].id : "";
    
    // Fake radar items derived from debris in a real scenario we'd get them from the backend
    const [radarItems, setRadarItems] = useState<any[]>([]);

    useEffect(() => {
        const fetchSnapshot = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/visualization/snapshot`);
                const data = await res.json();
                setSatellites(data.satellites || []);
                setDebris(data.debris_cloud || []);
                setManeuversHistory(data.maneuvers || []);
                
                // Demo radar logic: finding closest debris to the target satellite
                if (data.satellites.length > 0 && data.debris_cloud.length > 0) {
                    const sat = data.satellites[0];
                    const closeItems = data.debris_cloud.map((d: any, idx: number) => {
                        const dx = d[2] - sat.lon;
                        const dy = d[1] - sat.lat;
                        const dist = Math.sqrt(dx*dx + dy*dy) * 111.0; // Rough conversion from degrees to km
                        const angle = Math.atan2(dy, dx) * (180 / Math.PI);
                        return { id: d[0], dist, angle };
                    }).filter((item: any) => item.dist < 2000).sort((a: any, b: any) => a.dist - b.dist).slice(0, 5);
                    setRadarItems(closeItems);
                }
            } catch (err) {
                console.error("Failed to fetch snapshot", err);
            }
        };

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

        // Initial fetch
        fetchSnapshot();

        // Step loop
        let interval: NodeJS.Timeout;
        if (running) {
            interval = setInterval(stepSimulation, 1000);
        } else {
            interval = setInterval(fetchSnapshot, 2000);
        }

        return () => clearInterval(interval);
    }, [running]);
    
    const avgFuel = satellites.length > 0 
        ? satellites.reduce((acc, s) => acc + s.fuel_kg, 0) / satellites.length 
        : 50.0;

    return (
        <main className="flex min-h-screen flex-col bg-gray-950 p-4 text-white font-sans selection:bg-emerald-500/30">
            {/* Header */}
            <header className="flex items-center justify-between pb-4 border-b border-gray-800 mb-6">
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
            <div className="flex-1 grid grid-cols-12 gap-6">
                
                {/* Left Panel: Analytics */}
                <div className="col-span-3 flex flex-col gap-6">
                    <FleetDashboard 
                        satsCount={satellites.length}
                        debrisCount={debris.length}
                        collisionsDetected={collisions}
                        maneuversExecuted={maneuvers}
                        avgFuel={avgFuel}
                        recentManeuvers={maneuversHistory}
                    />
                </div>

                {/* Center Panel: Ground Track */}
                <div className="col-span-6 flex flex-col gap-2">
                    <div className="flex-1 min-h-[500px]">
                        <GroundTrackMap satellites={satellites} debris={debris} activeManeuvers={maneuversHistory} />
                    </div>
                </div>

                {/* Right Panel: Radar */}
                <div className="col-span-3 flex flex-col h-full gap-6">
                    <div className="flex-1 min-h-[300px]">
                        <ConjunctionRadar satId={targetSatId} items={radarItems} />
                    </div>
                    <div className="h-48 bg-gray-900 border border-gray-800 rounded-lg p-4 font-mono text-xs text-gray-400 overflow-y-auto w-full shadow-inner ring-1 ring-white/5">
                        <h4 className="text-gray-500 mb-2 border-b border-gray-800 pb-1">EVENT LOG</h4>
                        <div className="flex flex-col gap-1">
                            {maneuversHistory.slice().reverse().slice(0, 5).map((m: any, i: number) => (
                                <React.Fragment key={`log-${i}`}>
                                    <span className="text-blue-400">&gt; Satellite {m.satellite_id} executed avoidance maneuver</span>
                                    <span className="text-blue-400/70">  Δv applied: {(Math.sqrt(m.delta_v.x**2 + m.delta_v.y**2 + m.delta_v.z**2) * 1000).toFixed(2)} m/s</span>
                                    <span className="text-red-400">&gt; Detected imminent collision with {m.debris_id}</span>
                                    <span className="text-gray-600 mb-1 border-b border-gray-800/50 pb-1"></span>
                                </React.Fragment>
                            ))}
                            <span className="text-emerald-500/70">&gt; Ingesting telemetry...</span>
                            <span className="text-emerald-500/70">&gt; System initialized.</span>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}
