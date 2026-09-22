import React from 'react';

/**
 * Fraud Index Scorecard & Matchup Breakdown Component.
 * - Displays composite "CERTIFIED THREAT" / "FRAUD ALERT" badge with retro glow & glitch effects.
 * - Core metrics: Expected Rating, Global Average, Delta, and -100 to +100 Fraud Meter.
 * - Detailed 1v1 cards for each defender in the opposing backline.
 */
export default function FraudScorecard({ matchupData }) {
  if (!matchupData) {
    return (
      <div className="bg-[#0e111a] border-2 border-[#242b3d] p-6 text-center text-gray-500 font-mono">
        Select a squad and run recon to generate Fraud Index scorecard.
      </div>
    );
  }

  const {
    player_name,
    global_average,
    expected_rating,
    diff_vs_global,
    fraud_index,
    badge,
    badge_type,
    summary,
    matchup_breakdown = []
  } = matchupData;

  const isThreat = badge_type === 'threat';
  const isFraud = badge_type === 'fraud';

  // Badge styles
  const getBadgeContainerClass = () => {
    if (isThreat) {
      return 'border-4 border-[#39ff14] bg-[#07240c] shadow-[0_0_30px_rgba(57,255,20,0.4)] animate-threat';
    }
    if (isFraud) {
      return 'border-4 border-[#ff3131] bg-[#2a0808] shadow-[0_0_30px_rgba(255,49,49,0.5)] animate-glitch';
    }
    return 'border-4 border-[#00f0ff] bg-[#061e2b] shadow-[0_0_20px_rgba(0,240,255,0.3)]';
  };

  const getBadgeTextClass = () => {
    if (isThreat) return 'text-[#39ff14] glow-green';
    if (isFraud) return 'text-[#ff3131] glow-red';
    return 'text-[#00f0ff] glow-cyan';
  };

  const getVerdictBadge = (verdict) => {
    switch (verdict) {
      case 'LETHAL':
      case 'ADVANTAGE':
        return 'bg-green-950 text-green-400 border-green-500';
      case 'POCKETED':
      case 'CONTAINED':
        return 'bg-red-950 text-red-400 border-red-500';
      case 'HONORS EVEN':
        return 'bg-blue-950 text-blue-400 border-blue-400';
      default:
        return 'bg-gray-900 text-yellow-400 border-yellow-500/50';
    }
  };

  // Fraud meter position calculation (-100 to 100 mapped to 0% to 100%)
  const meterPercent = Math.min(100, Math.max(0, ((fraud_index + 100) / 200) * 100));

  return (
    <div className="w-full space-y-6">
      {/* 1. Main Composite Retro Badge */}
      <div className={`p-6 text-center rounded-sm transition-all ${getBadgeContainerClass()}`}>
        <div className="flex items-center justify-center gap-2 mb-2">
          <span className="text-xl">{isFraud ? '⚠️' : isThreat ? '⚡' : '🛡️'}</span>
          <h2 className={`text-2xl sm:text-4xl font-pixel tracking-wider ${getBadgeTextClass()}`}>
            {badge === 'CERTIFIED THREAT' ? 'CERTIFIED THREAT' :
             badge === 'FRAUD ALERT' ? 'FRAUD ALERT' : 'BALANCED PAR'}
          </h2>
          <span className="text-xl">{isFraud ? '⚠️' : isThreat ? '⚡' : '🛡️'}</span>
        </div>

        <p className="text-xs sm:text-sm font-mono text-gray-200 max-w-2xl mx-auto mt-2 leading-relaxed bg-black/50 p-2.5 border border-white/10">
          {summary}
        </p>
      </div>

      {/* 2. Core Stats Triad & Fraud Meter */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Expected Rating */}
        <div className="bg-[#0f1422] border-2 border-[#28334d] p-4 text-center">
          <p className="text-[10px] text-gray-400 font-pixel uppercase tracking-wider mb-1">
            EXPECTED RATING
          </p>
          <div className="text-3xl sm:text-4xl font-bold font-mono text-yellow-400 glow-gold">
            {expected_rating?.toFixed(2)}
          </div>
          <p className="text-[10px] text-gray-500 font-mono mt-1">vs this backline</p>
        </div>

        {/* Global Average */}
        <div className="bg-[#0f1422] border-2 border-[#28334d] p-4 text-center">
          <p className="text-[10px] text-gray-400 font-pixel uppercase tracking-wider mb-1">
            GLOBAL BASELINE
          </p>
          <div className="text-3xl sm:text-4xl font-bold font-mono text-white">
            {global_average?.toFixed(2)}
          </div>
          <p className="text-[10px] text-gray-500 font-mono mt-1">all fixtures (2024-2026)</p>
        </div>

        {/* Delta */}
        <div className="bg-[#0f1422] border-2 border-[#28334d] p-4 text-center">
          <p className="text-[10px] text-gray-400 font-pixel uppercase tracking-wider mb-1">
            RATING DELTA
          </p>
          <div className={`text-3xl sm:text-4xl font-bold font-mono ${
            diff_vs_global > 0 ? 'text-green-400 glow-green' :
            diff_vs_global < 0 ? 'text-red-400 glow-red' : 'text-gray-300'
          }`}>
            {diff_vs_global > 0 ? `+${diff_vs_global.toFixed(2)}` : diff_vs_global?.toFixed(2)}
          </div>
          <p className="text-[10px] text-gray-500 font-mono mt-1">expected variance</p>
        </div>

        {/* Fraud Index Score */}
        <div className="bg-[#0f1422] border-2 border-[#28334d] p-4 text-center flex flex-col justify-between">
          <div>
            <p className="text-[10px] text-gray-400 font-pixel uppercase tracking-wider mb-1">
              FRAUD INDEX
            </p>
            <div className={`text-3xl sm:text-4xl font-bold font-pixel ${
              fraud_index > 15 ? 'text-green-400' :
              fraud_index < -15 ? 'text-red-400' : 'text-yellow-400'
            }`}>
              {fraud_index > 0 ? `+${fraud_index}` : fraud_index}
            </div>
          </div>
          
          {/* Visual Retro Gauge */}
          <div className="mt-2">
            <div className="relative w-full h-3 bg-black border border-gray-700 overflow-hidden">
              {/* Background gradient from red to green */}
              <div className="absolute inset-0 bg-gradient-to-r from-red-600 via-yellow-400 to-green-500 opacity-60" />
              {/* Center line (0 point) */}
              <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-white z-10" />
              {/* Needle Indicator */}
              <div
                className="absolute top-0 bottom-0 w-2 -ml-1 bg-white border border-black z-20 shadow"
                style={{ left: `${meterPercent}%` }}
              />
            </div>
            <div className="flex justify-between text-[8px] text-gray-400 font-mono mt-0.5">
              <span>-100 (FRAUD)</span>
              <span>0</span>
              <span>+100 (THREAT)</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. 1v1 Defender Matchup Breakdown Cards */}
      <div className="space-y-3">
        <h3 className="text-xs font-pixel text-yellow-400 flex items-center gap-2 border-b border-gray-800 pb-2">
          <span>⚔️</span>
          <span>1v1 TACTICAL COLLISION BREAKDOWN</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {matchup_breakdown.map((item, idx) => (
            <div
              key={idx}
              className="bg-[#0a0d14] border border-[#22293a] hover:border-yellow-500/60 transition-colors p-3.5 flex flex-col justify-between"
            >
              <div>
                {/* Header: Position & Verdict */}
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] font-pixel text-gray-400 bg-[#161a25] px-1.5 py-0.5 border border-gray-700">
                    {item.position}
                  </span>
                  <span className={`text-[9px] font-pixel px-1.5 py-0.5 border ${getVerdictBadge(item.verdict)}`}>
                    {item.verdict}
                  </span>
                </div>

                {/* Defender Name & Team */}
                <h4 className="text-sm font-bold text-white font-mono leading-tight">
                  {item.defender_name}
                </h4>
                <p className="text-[10px] text-gray-400 font-mono mb-3 truncate">
                  {item.team} (Def: {item.defender_rating.toFixed(1)})
                </p>

                {/* Expected Attacker Rating vs this Defender */}
                <div className="bg-[#121622] p-2 border border-[#1f2638] mb-2.5">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-gray-400">Proj. Rating:</span>
                    <span className="font-bold text-yellow-300">{item.expected_rating.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-[11px] font-mono">
                    <span className="text-gray-500">Delta vs Baseline:</span>
                    <span className={`font-bold ${item.rating_delta >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {item.rating_delta >= 0 ? `+${item.rating_delta.toFixed(2)}` : item.rating_delta.toFixed(2)}
                    </span>
                  </div>
                  {item.has_history && (
                    <div className="flex justify-between text-[10px] text-yellow-400/90 font-mono mt-1 pt-1 border-t border-gray-800">
                      <span>Historical H2H ({item.games_played}G):</span>
                      <span>{item.actual_h2h_rating?.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Scout telemetry comment */}
              <p className="text-[10px] text-gray-400 font-mono leading-tight italic border-t border-gray-800/80 pt-2 mt-1">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
