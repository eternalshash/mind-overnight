import React, { useState } from 'react';

/**
 * 2D Retro Bowl / Sensible Soccer Style Pitch Component.
 * - Alternating lawn grass stripes & retro pixel pitch markings.
 * - Dynamic attacker positioning based on tactical role (ST, RW, LW, CAM).
 * - Opponent backline tokens (LB, LCB, RCB, RB).
 * - Club presets selector.
 * - Interactive click-to-edit defender name and rating.
 */
export default function RetroPitch({
  attacker,
  backline,
  presetTeams,
  selectedTeamId,
  onTeamSelect,
  onUpdateDefender,
  matchupData
}) {
  const [editingIndex, setEditingIndex] = useState(null);
  const [editName, setEditName] = useState('');
  const [editRating, setEditRating] = useState(7.0);

  const handleStartEdit = (index) => {
    const def = backline[index];
    if (!def) return;
    setEditingIndex(index);
    setEditName(def.name);
    setEditRating(def.rating || 7.1);
  };

  const handleSaveEdit = () => {
    if (editingIndex !== null) {
      onUpdateDefender(editingIndex, {
        name: editName.trim() || 'Custom Defender',
        rating: parseFloat(editRating) || 7.0
      });
      setEditingIndex(null);
    }
  };

  // Attacker coordinates based on tactical role
  const getAttackerCoords = (pos = 'ST') => {
    const p = pos.toUpperCase();
    if (p.includes('RW') || p.includes('RM')) return { left: '78%', top: '34%' };
    if (p.includes('LW') || p.includes('LM')) return { left: '22%', top: '34%' };
    if (p.includes('CAM') || p.includes('AM')) return { left: '50%', top: '40%' };
    return { left: '50%', top: '24%' }; // Default ST
  };

  const attackerCoords = getAttackerCoords(attacker?.player_position || 'ST');

  // Defender horizontal slots
  const defenderPositions = [
    { slot: 'LB', left: '16%', top: '70%' },
    { slot: 'LCB', left: '38%', top: '73%' },
    { slot: 'RCB', left: '62%', top: '73%' },
    { slot: 'RB', left: '84%', top: '70%' },
  ];

  return (
    <div className="w-full bg-[#0d1017] border-2 border-[#242b3d] p-4 rounded-sm">
      {/* Header controls: Opponent Selector */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-[#1f2637]">
        <div className="flex items-center gap-2">
          <span className="text-xs text-yellow-400 font-pixel">OPPONENT UNIT:</span>
          <select
            value={selectedTeamId || ''}
            onChange={(e) => onTeamSelect(e.target.value)}
            className="bg-[#141824] border-2 border-yellow-500/60 text-yellow-300 font-mono text-sm px-3 py-1 focus:outline-none focus:border-yellow-400 cursor-pointer"
          >
            {presetTeams.map((team) => (
              <option key={team.id} value={team.id} className="bg-[#10141f] text-white">
                {team.name} ({team.defenders.map((d) => d.name.split(' ').pop()).join(' - ')})
              </option>
            ))}
          </select>
        </div>

        <div className="text-xs text-gray-400 font-mono flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 bg-yellow-400 border border-black inline-block" /> ATTACKER ({attacker?.player_position || 'ST'})
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 bg-red-500 border border-black inline-block" /> BACKLINE (CLICK TO EDIT)
          </span>
        </div>
      </div>

      {/* 2D Retro Bowl Style Pitch Canvas */}
      <div className="relative w-full aspect-[16/10] sm:aspect-[16/9] bg-[#1d6b24] overflow-hidden border-4 border-[#124417] shadow-2xl select-none">
        {/* Retro Grass Stripes */}
        <div className="absolute inset-0 flex flex-col pointer-events-none">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className={`w-full flex-1 ${i % 2 === 0 ? 'bg-[#22772a]' : 'bg-[#1b6222]'}`}
            />
          ))}
        </div>

        {/* Pitch Markings (White Pixel Lines) */}
        <div className="absolute inset-0 pointer-events-none border-4 border-white/80 m-2">
          {/* Top Goal Box (Penalty area facing attacker) */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/5 h-1/4 border-b-2 border-x-2 border-white/80">
            {/* 6 Yard Box */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-1/2 border-b-2 border-x-2 border-white/80" />
            {/* Penalty Spot */}
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 w-2 h-2 bg-white rounded-full shadow" />
          </div>

          {/* Penalty Arc */}
          <div className="absolute top-[25%] left-1/2 -translate-x-1/2 w-28 h-12 border-b-2 border-white/70 rounded-b-full" />

          {/* Halfway Line & Center Circle */}
          <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-white/80" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 border-2 border-white/80 rounded-full">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 bg-white rounded-full" />
          </div>

          {/* Corner arcs */}
          <div className="absolute top-0 left-0 w-4 h-4 border-r-2 border-b-2 border-white/70 rounded-br-full" />
          <div className="absolute top-0 right-0 w-4 h-4 border-l-2 border-b-2 border-white/70 rounded-bl-full" />
          <div className="absolute bottom-0 left-0 w-4 h-4 border-r-2 border-t-2 border-white/70 rounded-tr-full" />
          <div className="absolute bottom-0 right-0 w-4 h-4 border-l-2 border-t-2 border-white/70 rounded-tl-full" />
        </div>

        {/* Retro Bowl Attack Direction Indicator */}
        <div className="absolute top-3 left-4 text-[11px] text-yellow-300 font-pixel tracking-wider bg-black/60 px-2 py-1 border border-yellow-500/50 flex items-center gap-1.5">
          <span>&uarr; ATTACK VECTOR</span>
        </div>

        {/* Attacker Token */}
        <div
          className="absolute -translate-x-1/2 -translate-y-1/2 z-20 flex flex-col items-center cursor-default transition-all duration-500"
          style={{ left: attackerCoords.left, top: attackerCoords.top }}
        >
          <div className="relative group">
            {/* Pulsing Aura */}
            <div className="absolute -inset-1.5 bg-yellow-400/30 rounded-full blur-sm animate-pulse" />
            
            {/* Retro Helmet / Jersey Token */}
            <div className="relative w-11 h-11 bg-black border-2 border-yellow-400 rounded-full flex flex-col items-center justify-center shadow-lg transform transition-transform group-hover:scale-110">
              <span className="text-[9px] font-pixel text-yellow-300">
                {attacker?.player_position || 'ST'}
              </span>
              <span className="text-[10px] font-bold text-white font-mono leading-none">
                {attacker?.global_average ? attacker.global_average.toFixed(1) : '7.0'}
              </span>
            </div>
          </div>

          {/* Attacker Name Badge */}
          <div className="mt-1 bg-black/90 border border-yellow-400/80 px-2 py-0.5 rounded shadow text-center whitespace-nowrap">
            <p className="text-[10px] sm:text-xs font-pixel text-yellow-300 tracking-wide uppercase">
              {attacker?.player_name || 'ATTACKER'}
            </p>
            <p className="text-[9px] text-gray-400 font-mono">
              GLOBAL: {attacker?.global_average?.toFixed(2) || '7.00'}
            </p>
          </div>
        </div>

        {/* Opponent Backline Defenders */}
        {backline.map((def, idx) => {
          const pos = defenderPositions[idx] || { slot: 'DEF', left: `${20 + idx * 20}%`, top: '72%' };
          const matchup = matchupData?.matchup_breakdown?.[idx];
          const hasHistory = matchup?.has_history;

          return (
            <div
              key={idx}
              onClick={() => handleStartEdit(idx)}
              className="absolute -translate-x-1/2 -translate-y-1/2 z-20 flex flex-col items-center cursor-pointer group"
              style={{ left: pos.left, top: pos.top }}
              title={`Click to modify ${def.name}`}
            >
              {/* Tactical Collision Line towards Attacker */}
              <div className="relative">
                {/* Status ring */}
                <div className={`absolute -inset-1 rounded-full blur-xs transition-all ${
                  matchup?.verdict === 'POCKETED' ? 'bg-red-600/40' :
                  matchup?.verdict === 'LETHAL' ? 'bg-green-500/40' : 'bg-blue-500/20'
                } group-hover:scale-125`} />

                {/* Defender Token Badge */}
                <div className="relative w-10 h-10 bg-[#161a24] border-2 border-red-500 group-hover:border-yellow-400 rounded-full flex flex-col items-center justify-center shadow-lg transition-transform group-hover:scale-110">
                  <span className="text-[8px] font-pixel text-red-400 group-hover:text-yellow-300">
                    {pos.slot}
                  </span>
                  <span className="text-[10px] font-bold text-white font-mono leading-none">
                    {def.rating ? Number(def.rating).toFixed(1) : '7.0'}
                  </span>
                </div>

                {/* History Indicator Pin */}
                {hasHistory && (
                  <span className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-400 border border-black rounded-full flex items-center justify-center text-[7px] text-black font-bold" title="Direct 1v1 encounters on record">
                    !
                  </span>
                )}
              </div>

              {/* Defender Name Tag */}
              <div className="mt-1 bg-black/90 border border-[#333d54] group-hover:border-yellow-400 px-2 py-0.5 rounded shadow text-center whitespace-nowrap transition-colors max-w-[90px] sm:max-w-[120px] truncate">
                <p className="text-[9px] sm:text-[10px] font-bold text-gray-200 font-mono truncate">
                  {def.name}
                </p>
                <div className="flex items-center justify-center gap-1 text-[8px] text-gray-400 font-mono">
                  <span>DEF: {Number(def.rating).toFixed(1)}</span>
                  {matchup?.actual_h2h_rating && (
                    <span className="text-yellow-400 font-bold">
                      H2H: {matchup.actual_h2h_rating.toFixed(1)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Edit Defender Modal */}
      {editingIndex !== null && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-[#121622] border-2 border-yellow-400 p-5 max-w-sm w-full font-mono text-white shadow-2xl">
            <div className="flex justify-between items-center border-b border-gray-700 pb-2 mb-4">
              <h4 className="text-xs font-pixel text-yellow-300">
                EDIT DEFENDER [{defenderPositions[editingIndex]?.slot}]
              </h4>
              <button
                onClick={() => setEditingIndex(null)}
                className="text-gray-400 hover:text-white text-sm"
              >
                [X]
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Defender Name</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full bg-black border border-gray-600 text-white p-2 text-sm focus:border-yellow-400 focus:outline-none"
                  placeholder="e.g. William Saliba"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>Defender Quality Rating:</span>
                  <span className="text-yellow-300 font-bold">{Number(editRating).toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="5.5"
                  max="8.5"
                  step="0.05"
                  value={editRating}
                  onChange={(e) => setEditRating(parseFloat(e.target.value))}
                  className="w-full accent-yellow-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-gray-500">
                  <span>5.5 (Vulnerable)</span>
                  <span>7.0 (Solid)</span>
                  <span>8.5 (Wall)</span>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-gray-800">
                <button
                  onClick={() => setEditingIndex(null)}
                  className="px-3 py-1 text-xs border border-gray-600 text-gray-300 hover:text-white"
                >
                  CANCEL
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="px-4 py-1 text-xs bg-yellow-500 hover:bg-yellow-400 text-black font-bold font-pixel"
                >
                  APPLY RECON
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
