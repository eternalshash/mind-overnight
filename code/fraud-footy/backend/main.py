"""
Fraud Footy FastAPI Backend Server.
Provides SSE streaming player analysis, preset team rosters, and backline comparison math.
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import numpy as np
import re

from teams import get_all_teams, get_team_by_id, PRESET_TEAMS
from scraper import stream_analysis, get_player_data, normalize_name

app = FastAPI(
    title="Fraud Footy API",
    description="90s Retro Football Scouting & Defender Matchup Analytics",
    version="1.0.0"
)

# Enable CORS for localhost:5173 and any frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DefenderInput(BaseModel):
    name: str
    position: Optional[str] = "CB"
    rating: Optional[float] = 7.10
    team: Optional[str] = "Opponent Club"


class CompareRequest(BaseModel):
    player_id: str
    player_name: Optional[str] = None
    defenders: List[DefenderInput]


@app.get("/")
def read_root():
    return {
        "app": "Fraud Footy API",
        "status": "online",
        "endpoints": [
            "/api/teams",
            "/api/analyze/stream?query=<player_name>",
            "/api/compare/backline",
            "/api/player/{player_id}"
        ]
    }


@app.get("/api/teams")
def list_teams():
    """Return presets for major club backlines."""
    return get_all_teams()


@app.get("/api/teams/{team_id}")
def get_team(team_id: str):
    """Return a specific preset club backline."""
    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found.")
    return team


@app.get("/api/analyze/stream")
async def analyze_stream(query: str = Query(..., description="Player name to search and analyze")):
    """
    SSE stream providing live progress and terminal log messages,
    followed by the final comprehensive Bayesian payload.
    """
    return StreamingResponse(
        stream_analysis(query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/player/{player_id}")
def get_player(player_id: str):
    """Retrieve compiled analysis profile for a player."""
    data = get_player_data(player_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Player '{player_id}' not found.")
    return data


def find_defender_in_lookup(defender_name: str, lookup: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fuzzy lookup for defender in historical encounters."""
    norm = normalize_name(defender_name)
    if norm in lookup:
        return lookup[norm]

    # Check last name match
    parts = re.split(r'\s+', defender_name.strip())
    last_name = parts[-1] if parts else defender_name
    last_norm = normalize_name(last_name)

    for k, v in lookup.items():
        if norm in k or k in norm:
            return v
        if len(last_norm) >= 4 and (last_norm in k or k in last_norm):
            return v
    return None


@app.post("/api/compare/backline")
def compare_backline(req: CompareRequest):
    """
    Compares an attacker against a specific 4-5 man backline.
    Calculates expected_rating, diff_vs_global, fraud_index score (-100 to +100),
    badge ('CERTIFIED THREAT' vs 'FRAUD ALERT' vs 'NEUTRAL'), and 1v1 matchups.
    """
    player_info = get_player_data(req.player_id or req.player_name or "haaland")
    if not player_info:
        raise HTTPException(status_code=404, detail="Player data not found.")

    global_avg = player_info.get("global_average", 7.00)
    pos = player_info.get("player_position", "ST").upper()
    lookup = player_info.get("defender_lookup", {})

    defenders = req.defenders
    if not defenders:
        raise HTTPException(status_code=400, detail="At least one defender must be provided.")

    # Tactical weighting based on attacker position and defender slot
    # Default weights
    n_defs = len(defenders)
    weights = [1.0 / n_defs] * n_defs

    # Positional tactical weighting for 4-defender backline [LB, LCB, RCB, RB]
    if n_defs == 4:
        pos_list = [d.position.upper() if d.position else "" for d in defenders]
        if "ST" in pos or "CF" in pos:
            # Striker battles central defenders most
            weights = [0.15, 0.35, 0.35, 0.15]
        elif "RW" in pos or "RM" in pos:
            # Right winger attacks opponent's Left Back (LB) and Left CB (LCB)
            weights = [0.45, 0.30, 0.15, 0.10]
        elif "LW" in pos or "LM" in pos:
            # Left winger attacks opponent's Right Back (RB) and Right CB (RCB)
            weights = [0.10, 0.15, 0.30, 0.45]
        elif "CAM" in pos or "AM" in pos:
            # Attacking midfielder roams central pockets
            weights = [0.20, 0.30, 0.30, 0.20]

    # Normalize weights to sum to 1.0
    w_sum = sum(weights)
    weights = [w / w_sum for w in weights]

    matchup_cards = []
    expected_ratings = []

    for idx, d in enumerate(defenders):
        d_name = d.name.strip()
        d_pos = d.position or "CB"
        d_team = d.team or "Opponent"
        d_rating = float(d.rating if d.rating is not None else 7.10)

        history = find_defender_in_lookup(d_name, lookup)
        weight = weights[idx]

        if history:
            has_history = True
            games = history["Games"]
            h2h_att = history["Attacker_Rating"]
            h2h_def = history["Defender_Rating"]
            exp_rating = history["Weighted_Difficulty"]
            rating_diff = round(exp_rating - global_avg, 2)

            if rating_diff <= -0.30:
                verdict = "POCKETED"
                desc = f"Historical struggle: Held to {h2h_att:.2f} avg across {games} match{'es' if games > 1 else ''}."
            elif rating_diff >= 0.30:
                verdict = "LETHAL"
                desc = f"Dominant record: Tormented {d_name} with {h2h_att:.2f} avg across {games} clash{'es' if games > 1 else ''}."
            elif rating_diff > 0.05:
                verdict = "ADVANTAGE"
                desc = f"Slight edge: Averaging {h2h_att:.2f} vs {d_name}'s {h2h_def:.2f}."
            elif rating_diff < -0.05:
                verdict = "CONTAINED"
                desc = f"Defensive resistance: {d_name} held attacker to {h2h_att:.2f}."
            else:
                verdict = "HONORS EVEN"
                desc = f"Balanced duel: Both rated around {h2h_att:.2f} in {games} clash{'es' if games > 1 else ''}."
        else:
            has_history = False
            games = 0
            h2h_att = None
            h2h_def = d_rating
            # Projection based on defender's tier relative to standard baseline (6.85)
            # Elite defenders reduce expected attacker rating
            baseline_diff = (d_rating - 6.85) * 0.55
            exp_rating = round(float(np.clip(global_avg - baseline_diff, 5.8, 9.2)), 2)
            rating_diff = round(exp_rating - global_avg, 2)

            if rating_diff <= -0.20:
                verdict = "HIGH THREAT DEFENDER"
                desc = f"Elite tier defender ({d_rating:.2f}). Projected to suppress attacker output by {abs(rating_diff):.2f}."
            elif rating_diff >= 0.15:
                verdict = "EXPLOITABLE"
                desc = f"Lower defensive resistance ({d_rating:.2f}). Attacker projected to gain +{rating_diff:.2f} advantage."
            else:
                verdict = "UNTESTED PROJECTION"
                desc = f"No direct historical minutes on record. Projected rating: {exp_rating:.2f} based on defender tier."

        expected_ratings.append(exp_rating)
        matchup_cards.append({
            "defender_name": d_name,
            "position": d_pos,
            "team": d_team,
            "defender_rating": round(d_rating, 2),
            "tactical_weight_pct": round(weight * 100, 1),
            "has_history": has_history,
            "games_played": games,
            "expected_rating": exp_rating,
            "actual_h2h_rating": h2h_att,
            "rating_delta": rating_diff,
            "verdict": verdict,
            "description": desc
        })

    # Weighted backline expectation
    backline_expected = round(sum(r * w for r, w in zip(expected_ratings, weights)), 2)
    diff_vs_global = round(backline_expected - global_avg, 2)

    # Fraud Index scaled -100 to +100
    # +100 = God-tier Certified Threat; -100 = Absolute Fraud
    fraud_index = int(np.clip(round(diff_vs_global * 125), -100, 100))

    if diff_vs_global >= 0.15:
        badge = "CERTIFIED THREAT"
        badge_type = "threat"
        summary = (
            f"CERTIFIED THREAT: {player_info['player_name']} exceeds his standard by {diff_vs_global:+.2f} "
            f"against this unit, forecasting an electric {backline_expected:.2f} match rating!"
        )
    elif diff_vs_global <= -0.15:
        badge = "FRAUD ALERT"
        badge_type = "fraud"
        summary = (
            f"FRAUD ALERT: {player_info['player_name']} drops {diff_vs_global:.2f} points below his global average "
            f"against this setup, indicating severe pocketing danger (Projected: {backline_expected:.2f})!"
        )
    else:
        badge = "NEUTRAL"
        badge_type = "neutral"
        summary = (
            f"BALANCED MATCHUP: Projected rating of {backline_expected:.2f} mirrors {player_info['player_name']}'s "
            f"global baseline ({global_avg:.2f})."
        )

    return {
        "player_id": player_info["player_id"],
        "player_name": player_info["player_name"],
        "player_position": pos,
        "global_average": global_avg,
        "expected_rating": backline_expected,
        "diff_vs_global": diff_vs_global,
        "fraud_index": fraud_index,
        "badge": badge,
        "badge_type": badge_type,
        "summary": summary,
        "defenders_analyzed": len(defenders),
        "matchup_breakdown": matchup_cards
    }
