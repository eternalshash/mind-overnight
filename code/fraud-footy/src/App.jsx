import React, { useState, useEffect, useRef } from 'react';
import BallonDor from './components/BallonDor';
import RetroPitch from './components/RetroPitch';
import FraudScorecard from './components/FraudScorecard';
import TerminalProgress from './components/TerminalProgress';
import HardestDefendersTable from './components/HardestDefendersTable';

const API_BASE = 'http://localhost:8000';

const PRE_INDEXED_STARS = [
  { id: 'haaland', name: 'Erling Haaland', role: 'ST', club: 'Man City', tag: 'CYBORG 9' },
  { id: 'saka', name: 'Bukayo Saka', role: 'RW', club: 'Arsenal', tag: 'STARBOY' },
  { id: 'kane', name: 'Harry Kane', role: 'ST', club: 'Bayern', tag: 'HURRICANE' },
  { id: 'cherki', name: 'Rayan Cherki', role: 'CAM', club: 'Lyon', tag: 'MAESTRO' },
];

export default function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentMessage, setCurrentMessage] = useState('');
  const [terminalLogs, setTerminalLogs] = useState([]);
  const [playerData, setPlayerData] = useState(null);
  const [error, setError] = useState(null);

  // Teams and Tactical Comparison State
  const [presetTeams, setPresetTeams] = useState([]);
  const [selectedTeamId, setSelectedTeamId] = useState('arsenal');
  const [currentBackline, setCurrentBackline] = useState([]);
  const [matchupData, setMatchupData] = useState(null);
  const [comparing, setComparing] = useState(false);

  const eventSourceRef = useRef(null);

  // Load preset teams on startup
  useEffect(() => {
    fetch(`${API_BASE}/api/teams`)
      .then((res) => res.json())
      .then((teams) => {
        setPresetTeams(teams);
        if (teams.length > 0) {
          setSelectedTeamId(teams[0].id);
          setCurrentBackline(teams[0].defenders);
        }
      })
      .catch((err) => {
        console.warn('Backend connection notice for teams:', err);
        // Fallback default teams if backend is just spinning up
        const fallbackTeams = [
          {
            id: 'arsenal',
            name: 'Arsenal',
            defenders: [
              { name: 'Jurriën Timber', position: 'LB', rating: 7.15, team: 'Arsenal' },
              { name: 'Gabriel Magalhães', position: 'LCB', rating: 7.30, team: 'Arsenal' },
              { name: 'William Saliba', position: 'RCB', rating: 7.38, team: 'Arsenal' },
              { name: 'Ben White', position: 'RB', rating: 7.12, team: 'Arsenal' },
            ],
          },
          {
            id: 'man_city',
            name: 'Manchester City',
            defenders: [
              { name: 'Joško Gvardiol', position: 'LB', rating: 7.28, team: 'Manchester City' },
              { name: 'Rúben Dias', position: 'LCB', rating: 7.25, team: 'Manchester City' },
              { name: 'Manuel Akanji', position: 'RCB', rating: 7.18, team: 'Manchester City' },
              { name: 'Kyle Walker', position: 'RB', rating: 7.05, team: 'Manchester City' },
            ],
          },
        ];
        setPresetTeams(fallbackTeams);
        setSelectedTeamId(fallbackTeams[0].id);
        setCurrentBackline(fallbackTeams[0].defenders);
      });
  }, []);

  // When player data or backline changes, run comparison
  useEffect(() => {
    if (!playerData || currentBackline.length === 0) return;

    setComparing(true);
    fetch(`${API_BASE}/api/compare/backline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        player_id: playerData.player_id,
        player_name: playerData.player_name,
        defenders: currentBackline,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('Comparison calculation failed');
        return res.json();
      })
      .then((data) => {
        setMatchupData(data);
        setComparing(false);
      })
      .catch((err) => {
        console.error('Error calculating backline comparison:', err);
        setComparing(false);
      });
  }, [playerData, currentBackline]);

  // Handle Team Selection
  const handleTeamSelect = (teamId) => {
    setSelectedTeamId(teamId);
    const team = presetTeams.find((t) => t.id === teamId);
    if (team) {
      setCurrentBackline([...team.defenders]);
    }
  };

  // Handle updating an individual defender slot
  const handleUpdateDefender = (index, updatedValues) => {
    setCurrentBackline((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], ...updatedValues };
      return next;
    });
  };

  // Swap a specific historical defender into the backline
  const handleDeployDefender = (defenderObj) => {
    setCurrentBackline((prev) => {
      const next = [...prev];
      // Replace slot 2 (RCB) or slot 1 (LCB)
      next[1] = {
        name: defenderObj.Defender,
        position: 'LCB',
        rating: defenderObj.Defender_Rating || 7.2,
        team: defenderObj.Defender_Team || 'Opponent Club',
      };
      return next;
    });
  };

  // Start analysis SSE stream
  const startSearch = (searchTarget) => {
    const term = (searchTarget || query).trim();
    if (!term) return;

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setLoading(true);
    setError(null);
    setProgress(5);
    setCurrentMessage(`Initiating recon on '${term}'...`);
    setTerminalLogs([
      `[SYS_INIT] Dialing Fraud Footy API telemetry gateway...`,
      `[QUERY] Target: "${term}"`,
    ]);

    const es = new EventSource(`${API_BASE}/api/analyze/stream?query=${encodeURIComponent(term)}`);
    eventSourceRef.current = es;

    es.addEventListener('progress', (e) => {
      try {
        const payload = JSON.parse(e.data);
        setProgress(payload.percent);
        setCurrentMessage(payload.message);
      } catch (err) {
        console.error(err);
      }
    });

    es.addEventListener('log', (e) => {
      try {
        const payload = JSON.parse(e.data);
        setTerminalLogs((prev) => [...prev, payload.message]);
      } catch (err) {
        console.error(err);
      }
    });

    es.addEventListener('complete', (e) => {
      try {
        const payload = JSON.parse(e.data);
        setPlayerData(payload);
        setLoading(false);
        es.close();
      } catch (err) {
        console.error('Error parsing complete payload:', err);
        setError('Failed to parse analysis payload.');
        setLoading(false);
        es.close();
      }
    });

    es.addEventListener('error', (e) => {
      try {
        const data = e.data ? JSON.parse(e.data) : null;
        setError(data?.message || 'Recon scan encountered network error or rate limit.');
      } catch {
        setError('Recon scan stream closed or unavailable.');
      }
      setLoading(false);
      es.close();
    });

    es.onerror = () => {
      setLoading(false);
      es.close();
    };
  };

  const handleCancel = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#05060a] text-white flex flex-col justify-between selection:bg-yellow-400 selection:text-black">
      {/* Top Retro Header */}
      <header className="border-b-2 border-[#192233] bg-[#090c14]/90 backdrop-blur sticky top-0 z-40 px-4 py-3">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setPlayerData(null)}>
            <div className="w-8 h-8 bg-black border-2 border-yellow-400 flex items-center justify-center font-pixel text-yellow-300 text-xs shadow-[0_0_10px_rgba(255,215,0,0.5)]">
              FF
            </div>
            <div>
              <h1 className="text-sm sm:text-base font-pixel tracking-wider text-yellow-400 glow-gold leading-none">
                FRAUD FOOTY
              </h1>
              <p className="text-[9px] text-gray-400 font-mono tracking-widest uppercase">
                90s Tactical Recon & Fraud Index Engine
              </p>
            </div>
          </div>

          {/* If viewing player dashboard, show quick controls */}
          {playerData && (
            <div className="flex items-center gap-3">
              <div className="hidden md:flex items-center gap-2 bg-[#121724] px-3 py-1 border border-gray-700 text-xs font-mono">
                <span className="text-gray-400">ACTIVE:</span>
                <span className="text-yellow-300 font-bold">{playerData.player_name}</span>
                <span className="text-gray-500">({playerData.player_position})</span>
                <span className="text-green-400 font-bold ml-1">AVG: {playerData.global_average}</span>
              </div>
              <button
                onClick={() => setPlayerData(null)}
                className="px-3 py-1 bg-black border-2 border-gray-600 hover:border-yellow-400 text-xs font-pixel text-gray-300 hover:text-yellow-300 transition-colors"
              >
                [&larr; NEW SCAN]
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col justify-center">
        {/* VIEW 1: LOADING & TERMINAL PROGRESS */}
        {loading ? (
          <div className="my-8">
            <TerminalProgress
              percent={progress}
              currentMessage={currentMessage}
              logs={terminalLogs}
              onCancel={handleCancel}
            />
          </div>
        ) : !playerData ? (
          /* VIEW 2: 90s RETRO LANDING PAGE WITH BALLON D'OR */
          <div className="flex flex-col items-center justify-center text-center my-auto py-8">
            {/* Animated Rotating & Glittering Ballon d'Or Trophy */}
            <div className="mb-4">
              <BallonDor size={270} interactive={true} />
            </div>

            {/* Title & Tagline */}
            <div className="max-w-2xl mb-8">
              <h2 className="text-2xl sm:text-4xl font-pixel tracking-wider text-yellow-400 glow-gold uppercase mb-3">
                IS YOUR STAR A FRAUD?
              </h2>
              <p className="text-xs sm:text-sm text-gray-400 font-mono leading-relaxed">
                Scan multi-season Sofascore player telemetry against top defensive units.
                Detect pocketed forwards, simulate custom backlines, and calculate the authentic Bayesian Fraud Index.
              </p>
            </div>

            {/* Search Input Box */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                startSearch(query);
              }}
              className="w-full max-w-xl mb-6"
            >
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search any forward or midfielder (e.g. Haaland, Saka...)"
                    className="w-full bg-[#0d111a] border-2 border-gray-700 focus:border-yellow-400 text-white font-mono text-sm px-4 py-3 focus:outline-none transition-colors shadow-inner"
                  />
                  <span className="absolute right-3 top-3 text-xs text-gray-500 font-mono hidden sm:inline">
                    [RETURN]
                  </span>
                </div>
                <button
                  type="submit"
                  className="bg-yellow-400 hover:bg-yellow-300 text-black font-pixel text-xs px-6 py-3 transition-colors shadow-[0_0_15px_rgba(255,215,0,0.4)] whitespace-nowrap cursor-pointer"
                >
                  RUN RECON &gt;&gt;
                </button>
              </div>

              {error && (
                <div className="mt-3 p-2 bg-red-950/80 border border-red-500 text-red-300 text-xs font-mono">
                  {error}
                </div>
              )}
            </form>

            {/* Quick-Select Buttons for Pre-Indexed Stars */}
            <div className="w-full max-w-xl">
              <p className="text-[10px] text-gray-500 font-pixel uppercase tracking-widest mb-3">
                &mdash; INSTANT ACCESS PRE-INDEXED STARS &mdash;
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {PRE_INDEXED_STARS.map((star) => (
                  <button
                    key={star.id}
                    onClick={() => {
                      setQuery(star.name);
                      startSearch(star.id);
                    }}
                    className="bg-[#0f1422] border-2 border-[#222b40] hover:border-yellow-400 p-2.5 text-left transition-all group flex flex-col justify-between"
                  >
                    <div>
                      <span className="text-[8px] font-pixel text-yellow-400/80 group-hover:text-yellow-300 block">
                        {star.tag}
                      </span>
                      <span className="text-xs font-bold text-white font-mono block leading-tight mt-0.5">
                        {star.name}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-[9px] text-gray-400 font-mono mt-2 pt-1 border-t border-gray-800">
                      <span>{star.club}</span>
                      <span className="text-yellow-400 font-bold">{star.role}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* VIEW 3: TACTICAL RECON DASHBOARD */
          <div className="space-y-8 py-2">
            {/* Player Header Banner */}
            <div className="bg-[#0c101a] border-2 border-[#20293d] p-5 rounded-sm flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-black border-2 border-yellow-400 flex flex-col items-center justify-center font-pixel text-yellow-300 shadow-[0_0_15px_rgba(255,215,0,0.3)]">
                  <span className="text-xs">{playerData.player_position}</span>
                  <span className="text-[9px] text-white">ROLE</span>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl sm:text-3xl font-bold font-mono tracking-tight text-white uppercase">
                      {playerData.player_name}
                    </h2>
                    <span className="text-xs font-pixel px-2 py-0.5 bg-yellow-400/20 text-yellow-300 border border-yellow-500/40">
                      {playerData.formation}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 font-mono">
                    {playerData.club || 'Elite Forward'} &bull; Analyzed {playerData.total_matches_analyzed} Matches &bull; {playerData.total_matchups_analyzed} 1v1 Encounters
                  </p>
                </div>
              </div>

              {/* Quick star switchers */}
              <div className="flex items-center gap-1 bg-black/60 p-1 border border-gray-800">
                {PRE_INDEXED_STARS.map((star) => (
                  <button
                    key={star.id}
                    onClick={() => startSearch(star.id)}
                    className={`px-2.5 py-1 text-[10px] font-pixel transition-colors ${
                      playerData.player_id === star.id
                        ? 'bg-yellow-400 text-black font-bold'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    {star.role}: {star.name.split(' ').pop()}
                  </button>
                ))}
              </div>
            </div>

            {/* Tactical Arena: Pitch (Left) & Fraud Scorecard (Right) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left: 2D Interactive Pitch */}
              <div className="lg:col-span-6 xl:col-span-7 space-y-4">
                <RetroPitch
                  attacker={playerData}
                  backline={currentBackline}
                  presetTeams={presetTeams}
                  selectedTeamId={selectedTeamId}
                  onTeamSelect={handleTeamSelect}
                  onUpdateDefender={handleUpdateDefender}
                  matchupData={matchupData}
                />
              </div>

              {/* Right: Fraud Scorecard */}
              <div className="lg:col-span-6 xl:col-span-5">
                <FraudScorecard matchupData={matchupData} />
              </div>
            </div>

            {/* Bottom: Hardest Defenders (Bayesian) & Opponent Stats */}
            <div className="mt-8">
              <HardestDefendersTable
                hardestDefenders={playerData.hardest_defenders}
                backlineStats={playerData.backline_stats}
                onSelectDefender={handleDeployDefender}
              />
            </div>
          </div>
        )}
      </main>

      {/* Retro 90s Footer */}
      <footer className="border-t border-gray-900 bg-black/80 py-3 px-4 text-center text-[10px] font-mono text-gray-500">
        <p>
          FRAUD FOOTY &copy; 2026 // RETRO TACTICAL RECON SUITE // POWERED BY SOFASCORE &amp; BAYESIAN TELEMETRY
        </p>
      </footer>
    </div>
  );
}