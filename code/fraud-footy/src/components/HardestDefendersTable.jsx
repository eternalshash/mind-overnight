import React, { useState } from 'react';

/**
 * Top Hardest Defenders (Bayesian Ranked) & Backline Stats Table Component.
 */
export default function HardestDefendersTable({ hardestDefenders = [], backlineStats = [], onSelectDefender }) {
  const [activeTab, setActiveTab] = useState('defenders'); // 'defenders' | 'clubs'

  const getRatingColor = (rating) => {
    if (rating >= 7.8) return 'text-blue-400';
    if (rating >= 7.2) return 'text-green-400';
    if (rating >= 6.8) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="bg-[#0b0e17] border-2 border-[#1f2638] p-4 rounded-sm font-mono">
      {/* Tab Switcher */}
      <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-4">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('defenders')}
            className={`px-3 py-1 text-xs font-pixel transition-colors ${
              activeTab === 'defenders'
                ? 'bg-yellow-400 text-black font-bold'
                : 'bg-[#151926] text-gray-400 hover:text-white border border-gray-700'
            }`}
          >
            HARDEST DEFENDERS (BAYESIAN)
          </button>
          <button
            onClick={() => setActiveTab('clubs')}
            className={`px-3 py-1 text-xs font-pixel transition-colors ${
              activeTab === 'clubs'
                ? 'bg-yellow-400 text-black font-bold'
                : 'bg-[#151926] text-gray-400 hover:text-white border border-gray-700'
            }`}
          >
            OPPONENT CLUB STATS
          </button>
        </div>

        <span className="text-[10px] text-gray-500 hidden sm:inline">
          {activeTab === 'defenders' ? 'SORTED BY WEIGHTED DIFFICULTY ASCENDING' : 'AVERAGE RATING BY DEFENSIVE UNIT'}
        </span>
      </div>

      {activeTab === 'defenders' ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800 text-[10px] uppercase font-pixel tracking-wider">
                <th className="pb-2.5 font-normal">RANK</th>
                <th className="pb-2.5 font-normal">DEFENDER</th>
                <th className="pb-2.5 font-normal">CLUB</th>
                <th className="pb-2.5 font-normal text-center">GAMES</th>
                <th className="pb-2.5 font-normal text-right">DEF RATING</th>
                <th className="pb-2.5 font-normal text-right">ATT RATING</th>
                <th className="pb-2.5 font-normal text-right">WEIGHTED DIFF</th>
                {onSelectDefender && <th className="pb-2.5 font-normal text-center">ACTION</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-900">
              {hardestDefenders.slice(0, 15).map((def, idx) => (
                <tr key={idx} className="hover:bg-[#131826] transition-colors group">
                  <td className="py-2.5 text-gray-500 font-pixel text-[10px]">#{idx + 1}</td>
                  <td className="py-2.5 font-bold text-white group-hover:text-yellow-300">
                    {def.Defender}
                  </td>
                  <td className="py-2.5 text-gray-400 truncate max-w-[140px]">{def.Defender_Team}</td>
                  <td className="py-2.5 text-center text-gray-300 font-bold">{def.Games}</td>
                  <td className="py-2.5 text-right text-gray-400 font-bold">
                    {def.Defender_Rating?.toFixed(2)}
                  </td>
                  <td className={`py-2.5 text-right font-bold ${getRatingColor(def.Attacker_Rating)}`}>
                    {def.Attacker_Rating?.toFixed(2)}
                  </td>
                  <td className={`py-2.5 text-right font-bold font-pixel text-[10px] ${getRatingColor(def.Weighted_Difficulty)}`}>
                    {def.Weighted_Difficulty?.toFixed(2)}
                  </td>
                  {onSelectDefender && (
                    <td className="py-2.5 text-center">
                      <button
                        onClick={() => onSelectDefender(def)}
                        className="text-[9px] font-pixel px-2 py-0.5 border border-yellow-500/60 text-yellow-300 hover:bg-yellow-400 hover:text-black transition-colors"
                      >
                        TEST
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800 text-[10px] uppercase font-pixel tracking-wider">
                <th className="pb-2.5 font-normal">OPPONENT CLUB</th>
                <th className="pb-2.5 font-normal text-center">ENCOUNTERS</th>
                <th className="pb-2.5 font-normal text-right">BACKLINE AVG</th>
                <th className="pb-2.5 font-normal text-right">ATTACKER AVG</th>
                <th className="pb-2.5 font-normal text-right">DELTA VS GLOBAL</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-900">
              {backlineStats.map((stat, idx) => (
                <tr key={idx} className="hover:bg-[#131826] transition-colors">
                  <td className="py-2.5 font-bold text-white">{stat.team}</td>
                  <td className="py-2.5 text-center text-gray-300">{stat.encounters}</td>
                  <td className="py-2.5 text-right text-gray-400">{stat.defender_avg?.toFixed(2)}</td>
                  <td className={`py-2.5 text-right font-bold ${getRatingColor(stat.attacker_avg)}`}>
                    {stat.attacker_avg?.toFixed(2)}
                  </td>
                  <td className={`py-2.5 text-right font-bold ${
                    stat.diff_vs_global > 0 ? 'text-green-400' :
                    stat.diff_vs_global < 0 ? 'text-red-400' : 'text-gray-400'
                  }`}>
                    {stat.diff_vs_global > 0 ? `+${stat.diff_vs_global.toFixed(2)}` : stat.diff_vs_global?.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
