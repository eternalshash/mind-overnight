import { useState } from 'react'

const ASCII_BALL = `
                              ▒▒█████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░                           
                          ░░██▓▓░           ░  ░░▒▒░░░▒▒▓▓░                      
                       ░▓▓█              ░          ▒░    ░▒▓░                   
                     █▒▓▒                ░           ▒░      ░▒▓                 
                   ▓▒▓                   ░            ▒░       ░▒▓░              
                 ▓ ▓                     ░             ▒          ░▒             
               ▒▓ ▓                      ░             ░░          ░▒░           
              ▓▒▒ ░                   ░▓░  ░           ░░            ░▓          
             ▒░▒  ░                ░▒         ░██▒     ░░             ░▒         
            ▒░▒                  ▓░              ░▒▒▒▒░░               ░▒        
           ▒░▒    ░░░░         ▒            ░▓▒▓▒░                      ░▒       
          ▓░░▒   ░          ░░           ░▒▒░░                           ░▓      
         ░░ ░  ░                       ░░▒░░░ ░░   ░░ ░                   ░      
         ▓ ░▒ ░                     ░▒░░░   ░░   ░ ░                      ░▓     
         ▒ ░ ▒                 █  ▒░░   ░░░░     ░               ░░░░░░    ░     
        ░░ ░░▒                 ▒▒ ░░              ░       ░░░░░░░░   ░░    ░▓    
        ▓   ░▒                ▒░░░░             ░░    ░░░░░           ░░    ▓    
        ▒ ░ ░▒               ▓░    ░░░░░░░░     ░ ░░░░░                ░    ▓    
        ▓ ░ ░░              ▒░  ░░░             ░░░░                   ░░░  ▓    
        ▓  ░ ░░░           ▓░   ░ ░░░░░░░░░ ░░░░░░░░                   ░ ░  ▓    
        ░░    ░░▒▒░        ░  ░░ ░░        ░░░                        ▒  ░ ░▒    
         ▒        ░░▒▒▒▒▒▒░░  ░ ░      ░░░░     ░    ░                ░ ░  ▒     
         ▓░                    ░░  ░░░▒░ ░░░          ░              ░ ░░ ░▓     
          ▒░      ░░░░░    ░     ░░░ ░░                 ░        ░▒▓░  ░  ▒      
           ▒      ░         ░   ░▒░                     ░▓▓▓█░         ░ ░░      
           ░░     ░░░░░     ░  ░▒                       ░            ░░ ░▒       
            ▒▒░             ░ ░░                       ░            ░░░░▒        
              ▒░            ░ ░▒                     ░░            ░░░▒          
               ▓░          ░░  ░░                   ░░           ░░░░▒           
                ▓▒░       ░░░    ░                 ░░          ░░░  ░            
                  ▒▒░░   ░░       ░▒░           ░░░          ░░░    ░▒░          
                    ░▒░  ░       ▒▓                        ░░░       ░           
                      ░░░░    ░▒▒         ░░░░        ░░░░░░         ░░▓         
                ░▓ ▓▓▒░ ░░░░░░░    ▒▒░░▒░ ░░░░░░░░░░░░░                ░░▒       
      ░▓█▒▒▒░██░▒░▒░░░ ░░     ░░░░░░                                     ░░▓     
     ▒░   ░         ░░ ░░░ ░░░░                                            ░▒    
       ░▒░░   ▒░░ ░        ░  ░ ░░░░░                     ░░░              ░ ░   
       ▓░░░▒▒░░ ░░░░░▒░ ░░░░░░░░ ░░ ░ ░░                 ░░                ░░▒   
       ░▒ ░       ░░  ░ ░░ ░░▒░ ░   ░░    ░░░                ░░░░            ░▓  
        ░░░        ░░░░░░░░░   ░░ ░▒ ░░░  ░  ░░     ░░░  ░░ ░░             ░░▒░  
         ▒         ░ ░░░░ ░░ ░░░   ░ ░░░  ░         ░ ▒░  ░     ░       ░░▒░     
         ░░░░░░ ▒░░░░░  ░    ░░    ▒░░ ░░░░░ ░░     ░░  ░      ░     ░▒▒▓░       
          ▓░░     ░   ░░      ░░░░   ░░░ ░ ░  ░      ░  ░░░░░░░░  ░░▒░           
           ▒▒▓▓▓▒▒░               ░░░  ░░░ ░░        ░░▒░      ░░▒▓              
                 ▒▒░░                ░            ░░░░ ░░░░    ░░                
                  ░                    ░       ░░ ░  ░      ░▒▓▓                 
                 ▓█▓▓▒▒▒▒▒▒░░                     ░░░    ░▒▓▓                    
                           ░░▒▒▒▒▒▒▒▒▒▒░░░     ░░     ░▒▓░                       
                                       ░░▒▒░░   ░░░▒▒▓▓                          
                                            ░▓▓▓▓░░░                             
                                                                           
   
`;

function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query) return;
    
    setLoading(true);
    setError(null);

    try {
      // Calling your local FastAPI backend!
      const response = await fetch(`http://localhost:8000/api/analyze/${query}`);
      if (!response.ok) throw new Error("Player not found or data missing.");
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Helper to color-code ratings
  const getRatingColor = (rating) => {
    if (rating >= 8.0) return 'text-blue-400 border-blue-400';
    if (rating >= 7.0) return 'text-green-400 border-green-400';
    if (rating >= 6.0) return 'text-yellow-400 border-yellow-400';
    return 'text-red-400 border-red-400';
  };

  // STATE 0: Landing Page
  if (!data) {
    return (
      <div className="min-h-screen bg-black text-white font-mono flex flex-col items-center justify-center p-4">
        <h1 className="text-5xl font-bold mb-4 tracking-widest">Fraud Footy</h1>
        <p className="mb-8 text-gray-400">How do your favorite players stack up against certain defenses?</p>
        
        {/* ASCII Animation Placeholder */}
        <pre className={`text-gray-300 mb-8 ${loading ? 'animate-pulse' : ''}`}>
          {ASCII_BALL}
        </pre>

        <form onSubmit={handleSearch} className="w-full max-w-md">
          <label className="block text-xs text-gray-500 mb-2 uppercase tracking-widest">Player Name (Forward or Midfielder)</label>
          <input 
            type="text" 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
            className="w-full bg-black border border-white text-white p-3 font-mono focus:outline-none focus:border-green-500 transition-colors"
            placeholder="e.g. Haaland"
          />
          {error && <p className="text-red-500 mt-4 text-sm">{error}</p>}
          {loading && <p className="text-green-500 mt-4 text-sm animate-pulse">Running Deep Crawl Algorithm...</p>}
        </form>
      </div>
    );
  }

  // STATE 1: The Dashboard
  return (
    <div className="min-h-screen bg-black text-white font-mono p-8">
      <button onClick={() => setData(null)} className="text-gray-500 hover:text-white mb-8 border-b border-gray-500 pb-1">
        [&larr; New Search]
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
        {/* Left Column */}
        <div className="col-span-1">
          <h2 className="text-6xl font-bold uppercase tracking-tighter mb-6 leading-none">
            {data.player_name}
          </h2>
          
          <div className="mb-8">
            <p className="text-gray-500 text-sm mb-2">GLOBAL AVERAGE (2024-2026)</p>
            <div className={`inline-block border-2 px-6 py-4 text-5xl font-bold ${getRatingColor(data.global_average)}`}>
              {data.global_average.toFixed(2)}
            </div>
          </div>
          
          <div className="border border-gray-800 p-4 bg-gray-900/50">
            <p className="text-xs text-gray-500 mb-2 uppercase">Matchups Analyzed</p>
            <p className="text-2xl">{data.total_matchups_analyzed} 1v1 Encounters</p>
          </div>
        </div>

        {/* Right Column */}
        <div className="col-span-2">
          <h3 className="text-xl border-b border-gray-800 pb-2 mb-4 uppercase tracking-widest">Hardest Defenders (Bayesian Ranked)</h3>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-gray-500 text-sm">
                <th className="pb-4 font-normal">DEFENDER</th>
                <th className="pb-4 font-normal">TEAM</th>
                <th className="pb-4 font-normal">GAMES</th>
                <th className="pb-4 font-normal text-right">WEIGHTED DIFF</th>
              </tr>
            </thead>
            <tbody>
              {data.hardest_defenders.map((defender, idx) => (
                <tr key={idx} className="border-t border-gray-900 hover:bg-gray-900/50 transition-colors">
                  <td className="py-4 font-bold">{defender.Defender}</td>
                  <td className="py-4 text-gray-400">{defender.Defender_Team}</td>
                  <td className="py-4 text-center">{defender.Games}</td>
                  <td className={`py-4 text-right font-bold ${getRatingColor(defender.Weighted_Difficulty)}`}>
                    {defender.Weighted_Difficulty.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default App;