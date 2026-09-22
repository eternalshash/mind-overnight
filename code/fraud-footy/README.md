# ⚽ FRAUD FOOTY ⚽
### 90s Retro Tactical Recon & Defender Vulnerability Engine

Fraud Footy is a full-stack tactical analytics web application built with a vibrant 90s retro arcade & football manager aesthetic. It scans multi-season Sofascore player telemetry against top defensive units to calculate Bayesian difficulty ratings, assess whether forwards are "pocketed", simulate 1v1 matchups on a 2D Retro Bowl style pitch, and award composite **"CERTIFIED THREAT"** vs **"FRAUD ALERT"** badges.

---

## 🌟 Key Features

1. **Authentic 90s Ballon d'Or Trophy**:
   - Canvas-rendered pixel-art Ballon d'Or with simulated 3D facet rotation.
   - Every 5 seconds, an intense golden sparkling/glittering shimmer traverses diagonally across the trophy facets.
   - Interactive: click to accelerate rotation and trigger sparkle bursts.

2. **Live Scraping & Terminal Stream**:
   - Real-time Server-Sent Events (SSE) from `/api/analyze/stream`.
   - ASCII / Pixel progress bar (0% - 100%) and scrolling terminal feed with match-by-match logs.
   - Pre-seeded instant indexing for **Erling Haaland**, **Bukayo Saka**, **Harry Kane**, and **Rayan Cherki**.
   - Automated live scraping with Playwright and Sofascore API for any forward/midfielder, automatically cached to `backend/cache/<id>.json`.

3. **Interactive 2D Retro Bowl Pitch**:
   - Styled after 90s arcade classics (Retro Bowl / Sensible Soccer) with alternating mowed lawn grass stripes, penalty boxes, center circle, and goal areas.
   - Tactical attacker positioning according to role (ST centered in box, RW on right flank, LW on left flank, CAM in central pocket).
   - Preset major club backlines: Arsenal, Man City, Real Madrid, Liverpool, Bayern Munich, Barcelona, Chelsea, Tottenham.
   - Click-to-edit any defender: customize name and quality rating slider (5.5 - 8.5) to test custom defensive configurations.

4. **Composite Fraud Index Scorecard**:
   - Prominent retro arcade badge with animated glow & glitch effects:
     - 🔥 **CERTIFIED THREAT** (overperforming expected standard)
     - 🚨 **FRAUD ALERT** (significantly underperforming vs specific backline)
     - ⚖️ **NEUTRAL / BALANCED**
   - Core metrics: Expected Rating, Global Average, Rating Delta, and -100 to +100 Fraud Meter.
   - 1v1 tactical collision breakdown cards with historical H2H records and scout verdicts (`LETHAL`, `ADVANTAGE`, `CONTAINED`, `POCKETED`, `UNTESTED`).

5. **Bayesian Hardest Defenders & Opponent Club Stats**:
   - Comprehensive tables of all-time hardest defenders ranked with Bayesian shrinkage ($m=3$), plus head-to-head performance across top European clubs.

---

## 🚀 Quickstart Guide

### 1. Backend Service (FastAPI)

```bash
# Navigate to backend directory
cd /Users/schoudhry/Desktop/mind-overnight/code/fraud-footy/backend

# (Optional) Install dependencies if not already installed
pip install -r requirements.txt

# Start the API server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The backend server will run at `http://127.0.0.1:8000`.
- API Documentation: `http://127.0.0.1:8000/docs`

### 2. Frontend Application (React + Vite + Tailwind)

In a separate terminal window:

```bash
# Navigate to project root
cd /Users/schoudhry/Desktop/mind-overnight/code/fraud-footy

# Start the Vite development server
npm run dev
```

Open your browser to `http://localhost:5173`.

---

## 📡 API Endpoints

- `GET /api/teams`: Returns preset club backlines (Arsenal, Man City, Real Madrid, Liverpool, Bayern, Barcelona, Chelsea, Tottenham).
- `GET /api/analyze/stream?query=<name>`: SSE stream yielding `progress`, `log`, and `complete` events with Bayesian ratings.
- `POST /api/compare/backline`: Computes `expected_rating`, `diff_vs_global`, `fraud_index`, `badge`, and 1v1 defender matchup breakdown.
- `GET /api/player/{player_id}`: Retrieves compiled telemetry profile.
