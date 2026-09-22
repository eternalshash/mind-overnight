"""
Preset teams and major club backlines for Fraud Footy analysis.
"""

PRESET_TEAMS = {
    "arsenal": {
        "id": "arsenal",
        "name": "Arsenal",
        "short_name": "ARS",
        "league": "Premier League",
        "badge_color": "#EF0107",
        "formation": "4-3-3",
        "defenders": [
            {"name": "Jurriën Timber", "position": "LB", "rating": 7.15, "team": "Arsenal"},
            {"name": "Gabriel Magalhães", "position": "LCB", "rating": 7.30, "team": "Arsenal"},
            {"name": "William Saliba", "position": "RCB", "rating": 7.38, "team": "Arsenal"},
            {"name": "Ben White", "position": "RB", "rating": 7.12, "team": "Arsenal"},
        ]
    },
    "man_city": {
        "id": "man_city",
        "name": "Manchester City",
        "short_name": "MCI",
        "league": "Premier League",
        "badge_color": "#6CABDD",
        "formation": "4-3-3",
        "defenders": [
            {"name": "Joško Gvardiol", "position": "LB", "rating": 7.28, "team": "Manchester City"},
            {"name": "Rúben Dias", "position": "LCB", "rating": 7.25, "team": "Manchester City"},
            {"name": "Manuel Akanji", "position": "RCB", "rating": 7.18, "team": "Manchester City"},
            {"name": "Kyle Walker", "position": "RB", "rating": 7.05, "team": "Manchester City"},
        ]
    },
    "real_madrid": {
        "id": "real_madrid",
        "name": "Real Madrid",
        "short_name": "RMA",
        "league": "La Liga",
        "badge_color": "#FEBE10",
        "formation": "4-3-3",
        "defenders": [
            {"name": "Ferland Mendy", "position": "LB", "rating": 7.02, "team": "Real Madrid"},
            {"name": "Antonio Rüdiger", "position": "LCB", "rating": 7.35, "team": "Real Madrid"},
            {"name": "Éder Militão", "position": "RCB", "rating": 7.18, "team": "Real Madrid"},
            {"name": "Dani Carvajal", "position": "RB", "rating": 7.26, "team": "Real Madrid"},
        ]
    },
    "liverpool": {
        "id": "liverpool",
        "name": "Liverpool",
        "short_name": "LIV",
        "league": "Premier League",
        "badge_color": "#C8102E",
        "formation": "4-3-3",
        "defenders": [
            {"name": "Andrew Robertson", "position": "LB", "rating": 7.12, "team": "Liverpool"},
            {"name": "Virgil van Dijk", "position": "LCB", "rating": 7.42, "team": "Liverpool"},
            {"name": "Ibrahima Konaté", "position": "RCB", "rating": 7.22, "team": "Liverpool"},
            {"name": "Trent Alexander-Arnold", "position": "RB", "rating": 7.36, "team": "Liverpool"},
        ]
    },
    "bayern": {
        "id": "bayern",
        "name": "FC Bayern München",
        "short_name": "BAY",
        "league": "Bundesliga",
        "badge_color": "#DC052D",
        "formation": "4-2-3-1",
        "defenders": [
            {"name": "Alphonso Davies", "position": "LB", "rating": 7.16, "team": "FC Bayern München"},
            {"name": "Dayot Upamecano", "position": "LCB", "rating": 7.20, "team": "FC Bayern München"},
            {"name": "Min-jae Kim", "position": "RCB", "rating": 7.19, "team": "FC Bayern München"},
            {"name": "Joshua Kimmich", "position": "RB", "rating": 7.41, "team": "FC Bayern München"},
        ]
    },
    "barcelona": {
        "id": "barcelona",
        "name": "FC Barcelona",
        "short_name": "BAR",
        "league": "La Liga",
        "badge_color": "#A50044",
        "formation": "4-3-3",
        "defenders": [
            {"name": "Alejandro Balde", "position": "LB", "rating": 7.08, "team": "FC Barcelona"},
            {"name": "Pau Cubarsí", "position": "LCB", "rating": 7.24, "team": "FC Barcelona"},
            {"name": "Ronald Araújo", "position": "RCB", "rating": 7.30, "team": "FC Barcelona"},
            {"name": "Jules Koundé", "position": "RB", "rating": 7.25, "team": "FC Barcelona"},
        ]
    },
    "chelsea": {
        "id": "chelsea",
        "name": "Chelsea",
        "short_name": "CHE",
        "league": "Premier League",
        "badge_color": "#034694",
        "formation": "4-2-3-1",
        "defenders": [
            {"name": "Marc Cucurella", "position": "LB", "rating": 7.08, "team": "Chelsea"},
            {"name": "Levi Colwill", "position": "LCB", "rating": 7.12, "team": "Chelsea"},
            {"name": "Wesley Fofana", "position": "RCB", "rating": 7.16, "team": "Chelsea"},
            {"name": "Malo Gusto", "position": "RB", "rating": 7.06, "team": "Chelsea"},
        ]
    },
    "tottenham": {
        "id": "tottenham",
        "name": "Tottenham Hotspur",
        "short_name": "TOT",
        "league": "Premier League",
        "badge_color": "#132257",
        "formation": "4-3-3",
        "defenders": [
            {"name": "Destiny Udogie", "position": "LB", "rating": 7.05, "team": "Tottenham Hotspur"},
            {"name": "Micky van de Ven", "position": "LCB", "rating": 7.22, "team": "Tottenham Hotspur"},
            {"name": "Cristian Romero", "position": "RCB", "rating": 7.28, "team": "Tottenham Hotspur"},
            {"name": "Pedro Porro", "position": "RB", "rating": 7.20, "team": "Tottenham Hotspur"},
        ]
    }
}


def get_all_teams():
    """Return all preset teams."""
    return list(PRESET_TEAMS.values())


def get_team_by_id(team_id: str):
    """Return specific team by ID or key."""
    key = team_id.lower().replace(" ", "_").replace("-", "_")
    return PRESET_TEAMS.get(key)
