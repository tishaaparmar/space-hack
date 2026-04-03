'use client';

import React from 'react';

interface ManeuverTimelineProps {
    maneuvers: any[];
    simTimestamp: string;
}

export default function ManeuverTimeline({ maneuvers, simTimestamp }: ManeuverTimelineProps) {
    if (maneuvers.length === 0) {
        return (
            <div className="w-full h-full bg-gray-900 border border-gray-800 rounded-lg p-4 flex items-center justify-center">
                <span className="text-gray-600 font-mono text-xs italic">No maneuvers recorded yet</span>
            </div>
        );
    }

    // Parse timestamps and build timeline
    const events = maneuvers.map((m, i) => {
        const ts = m.timestamp || '';
        const timeStr = ts.split('T')[1]?.replace('.000Z', '') || `T+${i}`;
        return {
            ...m,
            timeStr,
            index: i,
        };
    });

    // Show last 10 events
    const recent = events.slice(-10);

    return (
        <div className="w-full h-full bg-gray-900 border border-gray-800 rounded-lg p-3 overflow-hidden">
            <h4 className="text-gray-500 font-mono text-xs mb-2 border-b border-gray-800 pb-1 flex items-center gap-2">
                MANEUVER TIMELINE
                <span className="text-[10px] text-gray-600 ml-auto">{simTimestamp}</span>
            </h4>
            
            <div className="flex flex-col gap-1 overflow-y-auto" style={{ maxHeight: 'calc(100% - 28px)' }}>
                {recent.map((evt, i) => {
                    const isEvasion = evt.type !== 'RECOVERY';
                    const dvMs = evt.dv_magnitude_ms || (Math.sqrt(
                        evt.delta_v.x**2 + evt.delta_v.y**2 + evt.delta_v.z**2
                    ) * 1000);
                    
                    return (
                        <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                            {/* Time column */}
                            <span className="text-gray-600 w-16 shrink-0">{evt.timeStr}</span>
                            
                            {/* Type badge */}
                            <span className={`w-10 text-center px-1 py-0.5 rounded text-[8px] font-bold shrink-0 ${
                                isEvasion 
                                    ? 'bg-red-500/20 text-red-400 border border-red-500/30' 
                                    : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                            }`}>
                                {isEvasion ? 'EVD' : 'RCV'}
                            </span>
                            
                            {/* Gantt bar */}
                            <div className="flex-1 h-3 bg-gray-800 rounded overflow-hidden relative">
                                <div 
                                    className={`h-full rounded ${isEvasion ? 'bg-red-500/60' : 'bg-blue-500/60'}`}
                                    style={{ width: `${Math.min(dvMs / 15 * 100, 100)}%` }}
                                />
                                {/* Cooldown indicator */}
                                <div className="absolute right-0 top-0 h-full bg-gray-600/40 rounded-r" 
                                    style={{ width: '20%' }}
                                    title="600s cooldown"
                                />
                            </div>
                            
                            {/* Satellite ID */}
                            <span className="text-gray-400 w-20 truncate shrink-0" title={evt.satellite_id}>
                                {evt.satellite_id?.replace('SAT-','') || '?'}
                            </span>
                            
                            {/* Dv */}
                            <span className={`w-14 text-right shrink-0 ${isEvasion ? 'text-red-400' : 'text-blue-400'}`}>
                                {dvMs.toFixed(1)}m/s
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
