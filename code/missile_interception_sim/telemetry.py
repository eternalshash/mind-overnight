"""
================================================================================
TACTICAL TELEMETRY MODULE: MILITARY HUD & SENSOR SUITE
IAMD Global Defense Simulator
================================================================================
Provides high-fidelity telemetry visualizations:
- High-G / High-Mach live speedometer gauge with subsonic, supersonic, and hypersonic domains
- Altitude & Max Apogee indicators with climb/dive rates
- Flight Phase Badges (BOOST, MIDCOURSE, GLIDE, TERMINAL, LOITER, INTERCEPT)
- Trajectory progress bar and distance/time metrics (ETOF, remaining distance)
- Mission Outcome Badges (IN FLIGHT, DIRECT HIT, INTERCEPTED, DETONATED, MISS)
- Real-time Tactical Air Picture Matrix (dash_table.DataTable)
================================================================================
"""

import math
from typing import Dict, Any, List, Optional
import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# ==============================================================================
# 1. THEME & COLOR PALETTE
# ==============================================================================
THEME = {
    "bg_dark": "#090d16",
    "card_bg": "#0f172a",
    "card_border": "#1e293b",
    "accent_cyan": "#00f0ff",
    "accent_green": "#00e676",
    "accent_amber": "#ffb300",
    "accent_red": "#ff1744",
    "accent_purple": "#d500f9",
    "text_main": "#f8fafc",
    "text_muted": "#94a3b8",
    "text_dim": "#64748b",
    "font_mono": "'SF Mono', Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
}

PHASE_CONFIG = {
    "BOOST": {
        "color": "danger",
        "label": "BOOST PHASE",
        "icon": "🚀",
        "border": "#ff1744",
        "bg": "rgba(255, 23, 68, 0.15)",
        "desc": "Rocket motor active acceleration",
    },
    "MIDCOURSE": {
        "color": "info",
        "label": "MIDCOURSE COAST",
        "icon": "🛰️",
        "border": "#00f0ff",
        "bg": "rgba(0, 240, 255, 0.15)",
        "desc": "Exo/endo atmospheric ballistic coast",
    },
    "GLIDE": {
        "color": "warning",
        "label": "HYPERSONIC GLIDE",
        "icon": "⚡",
        "border": "#ffb300",
        "bg": "rgba(255, 179, 0, 0.15)",
        "desc": "Atmospheric skip & high-lift waverider glide",
    },
    "TERMINAL": {
        "color": "danger",
        "label": "TERMINAL DIVE",
        "icon": "🎯",
        "border": "#d500f9",
        "bg": "rgba(213, 0, 249, 0.15)",
        "desc": "High-velocity seeker terminal homing",
    },
    "LOITER": {
        "color": "success",
        "label": "LOITERING PATROL",
        "icon": "🔄",
        "border": "#00e676",
        "bg": "rgba(0, 230, 118, 0.15)",
        "desc": "Area surveillance / swarm loiter orbit",
    },
    "INTERCEPT": {
        "color": "primary",
        "label": "INTERCEPT CLOSURE",
        "icon": "🛡️",
        "border": "#3d5afe",
        "bg": "rgba(61, 90, 254, 0.2)",
        "desc": "Proportional navigation kinetic closure",
    },
    "STANDBY": {
        "color": "secondary",
        "label": "STANDBY / PAD",
        "icon": "⏱️",
        "border": "#64748b",
        "bg": "rgba(100, 116, 139, 0.15)",
        "desc": "Pre-launch or dormant track",
    },
}

OUTCOME_CONFIG = {
    "IN FLIGHT": {
        "badge_color": "info",
        "label": "AIRBORNE / TRACKING",
        "icon": "📡",
        "glow": "#00f0ff",
        "pulse": True,
    },
    "DIRECT HIT": {
        "badge_color": "success",
        "label": "DIRECT HIT (TARGET DESTROYED)",
        "icon": "💥",
        "glow": "#00e676",
        "pulse": False,
    },
    "INTERCEPTED": {
        "badge_color": "danger",
        "label": "INTERCEPTED / KINETIC KILL",
        "icon": "🛡️",
        "glow": "#ff1744",
        "pulse": False,
    },
    "DETONATED": {
        "badge_color": "warning",
        "label": "WARHEAD DETONATED",
        "icon": "🔥",
        "glow": "#ff9100",
        "pulse": False,
    },
    "MISS": {
        "badge_color": "secondary",
        "label": "ENGAGEMENT MISS / RUNOUT",
        "icon": "⚠️",
        "glow": "#94a3b8",
        "pulse": False,
    },
    "READY": {
        "badge_color": "light",
        "label": "SYSTEM READY",
        "icon": "🟢",
        "glow": "#64748b",
        "pulse": False,
    },
}

# ==============================================================================
# 2. SPEEDOMETER & MACH GAUGE
# ==============================================================================
def create_mach_gauge(
    mach_val: float = 0.0,
    max_mach: float = 12.0,
    unit_name: str = "Active Track",
    speed_kmh: Optional[float] = None,
    speed_mps: Optional[float] = None,
) -> go.Figure:
    """
    Renders an animated military-grade Mach speedometer gauge with
    Subsonic (0-1M), Supersonic (1-5M), and Hypersonic (5M+) sectors.
    """
    mach_clean = float(mach_val) if (mach_val is not None and not math.isnan(mach_val)) else 0.0
    gauge_max = max(max_mach, max(mach_clean * 1.25, 6.0))

    if speed_mps is None:
        # Approximate speed of sound at standard sea-level / mid-altitude ~ 310 m/s
        speed_mps = mach_clean * 310.0
    if speed_kmh is None:
        speed_kmh = speed_mps * 3.6

    # Determine current speed regime label and accent color
    if mach_clean < 1.0:
        regime = "SUBSONIC"
        bar_color = "#00f0ff"
    elif mach_clean < 5.0:
        regime = "SUPERSONIC"
        bar_color = "#ffb300"
    else:
        regime = "HYPERSONIC"
        bar_color = "#ff1744"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=mach_clean,
            number={
                "suffix": " M",
                "font": {
                    "color": bar_color,
                    "size": 34,
                    "family": THEME["font_mono"],
                },
                "valueformat": ".2f",
            },
            title={
                "text": f"<b>VELOCITY MATRIX</b><br><span style='font-size:11px;color:#94a3b8;'>[{regime}]</span>",
                "font": {"color": "#cbd5e1", "size": 13, "family": THEME["font_mono"]},
            },
            gauge={
                "axis": {
                    "range": [0, gauge_max],
                    "tickwidth": 1.5,
                    "tickcolor": "#64748b",
                    "tickfont": {"color": "#94a3b8", "size": 10, "family": THEME["font_mono"]},
                    "nticks": 7,
                },
                "bar": {
                    "color": bar_color,
                    "thickness": 0.26,
                },
                "bgcolor": "#090d16",
                "borderwidth": 1,
                "bordercolor": "#1e293b",
                "steps": [
                    {
                        "range": [0, 1.0],
                        "color": "rgba(0, 240, 255, 0.12)",
                    },  # Subsonic (Cyan)
                    {
                        "range": [1.0, 5.0],
                        "color": "rgba(255, 179, 0, 0.15)",
                    },  # Supersonic (Amber)
                    {
                        "range": [5.0, gauge_max],
                        "color": "rgba(255, 23, 68, 0.22)",
                    },  # Hypersonic (Crimson)
                ],
                "threshold": {
                    "line": {"color": bar_color, "width": 3},
                    "thickness": 0.8,
                    "value": mach_clean,
                },
            },
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": THEME["text_main"]},
        margin=dict(l=22, r=22, t=32, b=12),
        height=185,
    )
    return fig


# ==============================================================================
# 3. BADGES & INDICATOR COMPONENTS
# ==============================================================================
def create_flight_phase_badge(phase_str: str) -> dbc.Badge:
    """Returns a military HUD styled badge indicating flight phase."""
    phase_key = str(phase_str).upper().strip() if phase_str else "UNKNOWN"
    cfg = PHASE_CONFIG.get(phase_key, PHASE_CONFIG["STANDBY"])
    return dbc.Badge(
        [
            html.Span(f"{cfg['icon']} ", style={"marginRight": "4px"}),
            html.Span(cfg["label"], style={"fontWeight": "700", "letterSpacing": "1px"}),
        ],
        color=cfg["color"],
        className="px-3 py-2 text-uppercase",
        style={
            "fontSize": "0.75rem",
            "border": f"1px solid {cfg['border']}",
            "backgroundColor": cfg["bg"],
            "boxShadow": f"0 0 10px {cfg['bg']}",
            "fontFamily": THEME["font_mono"],
        },
    )


def create_outcome_badge(status_str: str) -> dbc.Badge:
    """Returns a mission status badge (IN FLIGHT, DIRECT HIT, INTERCEPTED, etc.)."""
    key = str(status_str).upper().strip() if status_str else "READY"
    cfg = OUTCOME_CONFIG.get(key, OUTCOME_CONFIG["IN FLIGHT"])
    return dbc.Badge(
        [
            html.Span(f"{cfg['icon']} ", style={"marginRight": "5px"}),
            html.Span(cfg["label"], style={"fontWeight": "700", "letterSpacing": "1px"}),
        ],
        color=cfg["badge_color"],
        className="px-3 py-2 text-uppercase",
        style={
            "fontSize": "0.8rem",
            "border": f"1px solid {cfg['glow']}",
            "boxShadow": f"0 0 12px {cfg['glow']}33",
            "fontFamily": THEME["font_mono"],
        },
    )

