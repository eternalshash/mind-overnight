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


def create_altitude_apogee_indicators(
    current_alt_m: float = 0.0,
    apogee_alt_m: float = 0.0,
    vertical_speed_mps: float = 0.0,
) -> html.Div:
    """
    Generates high-contrast altitude cards displaying current altitude,
    maximum predicted apogee, and climb/dive rate indicators.
    """
    alt_km = current_alt_m / 1000.0
    alt_ft = current_alt_m * 3.28084
    apogee_km = apogee_alt_m / 1000.0
    apogee_ft = apogee_alt_m * 3.28084

    # Climb / Dive status
    if vertical_speed_mps > 15.0:
        vs_text = f"▲ +{vertical_speed_mps:,.0f} m/s (ASCENDING)"
        vs_color = THEME["accent_green"]
    elif vertical_speed_mps < -15.0:
        vs_text = f"▼ {vertical_speed_mps:,.0f} m/s (DESCENT/DIVE)"
        vs_color = THEME["accent_red"]
    else:
        vs_text = f"▶ {vertical_speed_mps:,.0f} m/s (LEVEL CRUISE)"
        vs_color = THEME["accent_cyan"]

    # Exo-atmospheric classification
    exo_badge = "EXO-ATMOSPHERIC" if alt_km >= 100.0 else "ENDO-ATMOSPHERIC"
    exo_color = THEME["accent_purple"] if alt_km >= 100.0 else THEME["accent_cyan"]

    return html.Div(
        [
            dbc.Row(
                [
                    # Current Altitude
                    dbc.Col(
                        html.Div(
                            [
                                html.Small("CURRENT ALTITUDE", style={"color": THEME["text_muted"], "fontSize": "0.68rem"}),
                                html.Div(
                                    f"{alt_km:,.2f} km",
                                    style={
                                        "color": THEME["accent_cyan"],
                                        "fontSize": "1.35rem",
                                        "fontWeight": "800",
                                        "fontFamily": THEME["font_mono"],
                                        "lineHeight": "1.2",
                                    },
                                ),
                                html.Small(f"{alt_ft:,.0f} ft", style={"color": THEME["text_dim"], "fontSize": "0.68rem"}),
                            ],
                            className="p-2 rounded",
                            style={"backgroundColor": "#090d16", "border": f"1px solid {THEME['card_border']}"},
                        ),
                        width=6,
                    ),
                    # Max Apogee
                    dbc.Col(
                        html.Div(
                            [
                                html.Small("MAX APOGEE CEILING", style={"color": THEME["text_muted"], "fontSize": "0.68rem"}),
                                html.Div(
                                    f"{apogee_km:,.2f} km",
                                    style={
                                        "color": THEME["accent_amber"],
                                        "fontSize": "1.35rem",
                                        "fontWeight": "800",
                                        "fontFamily": THEME["font_mono"],
                                        "lineHeight": "1.2",
                                    },
                                ),
                                html.Small(f"{apogee_ft:,.0f} ft", style={"color": THEME["text_dim"], "fontSize": "0.68rem"}),
                            ],
                            className="p-2 rounded",
                            style={"backgroundColor": "#090d16", "border": f"1px solid {THEME['card_border']}"},
                        ),
                        width=6,
                    ),
                ],
                className="g-2 mb-2",
            ),
            # Vertical Rate & Domain Footer
            html.Div(
                [
                    html.Span(vs_text, style={"color": vs_color, "fontWeight": "700", "fontSize": "0.72rem"}),
                    html.Span(" | ", style={"color": THEME["text_dim"]}),
                    html.Span(exo_badge, style={"color": exo_color, "fontWeight": "700", "fontSize": "0.72rem"}),
                ],
                className="text-center p-1 rounded",
                style={"backgroundColor": "rgba(15, 23, 42, 0.6)", "fontFamily": THEME["font_mono"]},
            ),
        ]
    )


def create_trajectory_metrics_cards(
    dist_traveled_km: float = 0.0,
    dist_remaining_km: float = 0.0,
    etof_s: float = 0.0,
    time_remaining_s: float = 0.0,
) -> html.Div:
    """Displays downrange distance, remaining distance to target, and ETOF clocks."""
    def format_clock(seconds: float) -> str:
        s = max(0, int(seconds))
        m, sec = divmod(s, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{sec:02d}"
        return f"{m:02d}:{sec:02d}"

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Small("DISTANCE TRAVELED", style={"color": THEME["text_muted"], "fontSize": "0.66rem"}),
                                html.Div(
                                    f"{dist_traveled_km:,.1f} km",
                                    style={
                                        "color": THEME["text_main"],
                                        "fontWeight": "700",
                                        "fontSize": "1.05rem",
                                        "fontFamily": THEME["font_mono"],
                                    },
                                ),
                                html.Small(f"{dist_traveled_km * 0.539957:.1f} NM", style={"color": THEME["text_dim"], "fontSize": "0.66rem"}),
                            ],
                            className="p-2 rounded text-center",
                            style={"backgroundColor": "#090d16", "border": f"1px solid {THEME['card_border']}"},
                        ),
                        width=6,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Small("REMAINING DISTANCE", style={"color": THEME["text_muted"], "fontSize": "0.66rem"}),
                                html.Div(
                                    f"{dist_remaining_km:,.1f} km",
                                    style={
                                        "color": THEME["accent_amber"],
                                        "fontWeight": "700",
                                        "fontSize": "1.05rem",
                                        "fontFamily": THEME["font_mono"],
                                    },
                                ),
                                html.Small(f"{dist_remaining_km * 0.539957:.1f} NM", style={"color": THEME["text_dim"], "fontSize": "0.66rem"}),
                            ],
                            className="p-2 rounded text-center",
                            style={"backgroundColor": "#090d16", "border": f"1px solid {THEME['card_border']}"},
                        ),
                        width=6,
                    ),
                ],
                className="g-2 mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Small("EST TIME OF FLIGHT (ETOF)", style={"color": THEME["text_muted"], "fontSize": "0.66rem"}),
                                html.Div(
                                    format_clock(etof_s),
                                    style={
                                        "color": THEME["accent_cyan"],
                                        "fontWeight": "700",
                                        "fontSize": "1.05rem",
                                        "fontFamily": THEME["font_mono"],
                                    },
                                ),
                            ],
                            className="p-2 rounded text-center",
                            style={"backgroundColor": "#090d16", "border": f"1px solid {THEME['card_border']}"},
                        ),
                        width=6,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Small("TIME TO IMPACT / INTERCEPT", style={"color": THEME["text_muted"], "fontSize": "0.66rem"}),
                                html.Div(
                                    format_clock(time_remaining_s),
                                    style={
                                        "color": THEME["accent_red"],
                                        "fontWeight": "700",
                                        "fontSize": "1.05rem",
                                        "fontFamily": THEME["font_mono"],
                                    },
                                ),
                            ],
                            className="p-2 rounded text-center",
                            style={"backgroundColor": "#090d16", "border": f"1px solid {THEME['card_border']}"},
                        ),
                        width=6,
                    ),
                ],
                className="g-2",
            ),
        ]
    )


def create_animated_progress_bar(progress_pct: float = 0.0) -> html.Div:
    """Renders a progress bar indicating mission completion from 0 to 100%."""
    pct = max(0.0, min(100.0, float(progress_pct)))
    # Progress color based on completion
    bar_color = "info" if pct < 75 else ("warning" if pct < 90 else "danger")

    return html.Div(
        [
            html.Div(
                [
                    html.Small("TRAJECTORY PROGRESS", style={"color": THEME["text_muted"], "fontSize": "0.68rem", "fontWeight": "700"}),
                    html.Span(
                        f"{pct:.1f}%",
                        style={
                            "color": THEME["accent_cyan"],
                            "fontWeight": "800",
                            "fontFamily": THEME["font_mono"],
                            "fontSize": "0.85rem",
                            "float": "right",
                        },
                    ),
                ],
                className="d-flex justify-content-between mb-1",
            ),
            dbc.Progress(
                value=pct,
                color=bar_color,
                striped=True,
                animated=True,
                style={
                    "height": "16px",
                    "backgroundColor": "#090d16",
                    "border": f"1px solid {THEME['card_border']}",
                    "borderRadius": "4px",
                },
            ),
        ]
    )


# ==============================================================================
# 4. TELEMETRY SIDEBAR CONTAINER
# ==============================================================================
def create_telemetry_sidebar(
    unit_options: Optional[List[Dict[str, str]]] = None,
    selected_unit_id: Optional[str] = None,
    default_track_data: Optional[Dict[str, Any]] = None,
) -> dbc.Card:
    """
    Constructs the dedicated Telemetry Sidebar panel layout.
    """
    if unit_options is None:
        unit_options = [
            {"label": "🔴 TRK-01: Iskander-M Ballistic", "value": "TRK-01"},
            {"label": "🔴 TRK-02: Kinzhal Hypersonic", "value": "TRK-02"},
            {"label": "🔴 TRK-03: Shahed-136 Drone", "value": "TRK-03"},
            {"label": "🔵 INT-01: Patriot PAC-3 MSE", "value": "INT-01"},
            {"label": "🔵 INT-02: Anduril Roadrunner-M", "value": "INT-02"},
        ]

    if not selected_unit_id and unit_options:
        selected_unit_id = unit_options[0]["value"]

    # Initial placeholder data if none provided
    data = default_track_data or {
        "id": selected_unit_id,
        "name": "Iskander-M (9M723)",
        "type": "Ballistic Missile",
        "origin": "Aggressor Complex Alpha",
        "target": "Hardened Command HQ",
        "mach": 5.9,
        "speed_kmh": 7280.0,
        "speed_mps": 2022.0,
        "alt_m": 48500.0,
        "apogee_m": 50000.0,
        "vertical_speed_mps": -320.0,
        "dist_traveled_km": 280.0,
        "dist_remaining_km": 120.0,
        "etof_s": 240.0,
        "time_remaining_s": 65.0,
        "progress_pct": 70.0,
        "phase": "TERMINAL",
        "status": "IN FLIGHT",
        "warhead": "480 kg HE Blast Frag",
        "guidance": "GLONASS / Optical DSMAC",
    }

    sidebar_layout = dbc.Card(
        [
            # Header
            dbc.CardHeader(
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span("● ", style={"color": THEME["accent_green"], "fontSize": "1.1rem"}),
                                html.Strong("TACTICAL TELEMETRY HUD", style={"letterSpacing": "1.5px"}),
                            ],
                            style={"color": THEME["text_main"], "fontFamily": THEME["font_mono"]},
                        ),
                        html.Small("LIVE SENSOR & GUIDANCE STREAM", style={"color": THEME["text_muted"], "fontSize": "0.68rem"}),
                    ],
                    className="d-flex justify-content-between align-items-center",
                ),
                style={"backgroundColor": "#090d16", "borderBottom": f"1px solid {THEME['card_border']}"},
            ),
            # Body
            dbc.CardBody(
                [
                    # 1. Unit Selector Dropdown
                    html.Div(
                        [
                            html.Label(
                                "TARGET TRACK SELECTOR",
                                style={
                                    "color": THEME["text_muted"],
                                    "fontSize": "0.7rem",
                                    "fontWeight": "700",
                                    "letterSpacing": "1px",
                                },
                            ),
                            dcc.Dropdown(
                                id="telemetry-unit-select",
                                options=unit_options,
                                value=selected_unit_id,
                                clearable=False,
                                className="dash-dark-dropdown",
                                style={
                                    "backgroundColor": "#090d16",
                                    "color": "#f8fafc",
                                    "fontFamily": THEME["font_mono"],
                                    "fontSize": "0.82rem",
                                },
                            ),
                        ],
                        className="mb-3",
                    ),
                    # 2. Status & Flight Phase Badges
                    html.Div(
                        id="telemetry-badges-container",
                        children=[
                            html.Div(
                                [
                                    create_flight_phase_badge(data.get("phase", "BOOST")),
                                    html.Div(style={"width": "8px"}),
                                    create_outcome_badge(data.get("status", "IN FLIGHT")),
                                ],
                                className="d-flex justify-content-between align-items-center mb-3",
                            )
                        ],
                    ),
                    # 3. Live Mach Gauge Graph
                    html.Div(
                        [
                            dcc.Graph(
                                id="telemetry-mach-gauge",
                                figure=create_mach_gauge(
                                    mach_val=data.get("mach", 0.0),
                                    unit_name=data.get("name", "Active Track"),
                                    speed_kmh=data.get("speed_kmh", 0.0),
                                    speed_mps=data.get("speed_mps", 0.0),
                                ),
                                config={"displayModeBar": False, "responsive": True},
                                style={"height": "185px"},
                            ),
                            # Digital Speed Readout Tags
                            html.Div(
                                id="telemetry-speed-readout",
                                children=html.Div(
                                    [
                                        html.Span(
                                            f"VEL: {data.get('speed_mps', 0.0):,.0f} m/s",
                                            style={"color": THEME["accent_cyan"], "fontWeight": "700", "marginRight": "12px"},
                                        ),
                                        html.Span(
                                            f"({data.get('speed_kmh', 0.0):,.0f} km/h)",
                                            style={"color": THEME["text_muted"]},
                                        ),
                                    ],
                                    className="text-center pb-2",
                                    style={"fontFamily": THEME["font_mono"], "fontSize": "0.78rem"},
                                ),
                            ),
                        ],
                        className="mb-2 rounded",
                        style={"backgroundColor": "#090d16", "border": f"1px solid {THEME['card_border']}"},
                    ),
                    # 4. Altitude & Apogee Indicators
                    html.Div(
                        id="telemetry-alt-indicators",
                        children=create_altitude_apogee_indicators(
                            current_alt_m=data.get("alt_m", 0.0),
                            apogee_alt_m=data.get("apogee_m", 0.0),
                            vertical_speed_mps=data.get("vertical_speed_mps", 0.0),
                        ),
                        className="mb-3",
                    ),
                    # 5. Animated Progress Bar
                    html.Div(
                        id="telemetry-progress-container",
                        children=create_animated_progress_bar(data.get("progress_pct", 0.0)),
                        className="mb-3",
                    ),
                    # 6. Trajectory Metrics
                    html.Div(
                        id="telemetry-metrics-container",
                        children=create_trajectory_metrics_cards(
                            dist_traveled_km=data.get("dist_traveled_km", 0.0),
                            dist_remaining_km=data.get("dist_remaining_km", 0.0),
                            etof_s=data.get("etof_s", 0.0),
                            time_remaining_s=data.get("time_remaining_s", 0.0),
                        ),
                        className="mb-3",
                    ),
                    # 7. Unit Specifications & Target Data
                    html.Div(
                        id="telemetry-target-info",
                        children=[
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Small("DESIGNATION: ", style={"color": THEME["text_muted"]}),
                                            html.Span(str(data.get("name", "Unknown")), style={"color": THEME["text_main"], "fontWeight": "700"}),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Small("CLASSIFICATION: ", style={"color": THEME["text_muted"]}),
                                            html.Span(str(data.get("type", "Unknown")), style={"color": THEME["accent_cyan"]}),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Small("ASSIGNED TARGET: ", style={"color": THEME["text_muted"]}),
                                            html.Span(str(data.get("target", "Asset Grid")), style={"color": THEME["accent_amber"], "fontWeight": "700"}),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Small("WARHEAD / PAYLOAD: ", style={"color": THEME["text_muted"]}),
                                            html.Span(str(data.get("warhead", "Conventional")), style={"color": THEME["text_dim"]}),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Small("GUIDANCE / SEEKER: ", style={"color": THEME["text_muted"]}),
                                            html.Span(str(data.get("guidance", "INS/GPS/Active Radar")), style={"color": THEME["text_dim"]}),
                                        ]
                                    ),
                                ],
                                className="p-2 rounded",
                                style={
                                    "backgroundColor": "#090d16",
                                    "border": f"1px solid {THEME['card_border']}",
                                    "fontSize": "0.72rem",
                                    "fontFamily": THEME["font_mono"],
                                },
                            )
                        ],
                    ),
                ],
                style={"backgroundColor": THEME["card_bg"], "maxHeight": "calc(100vh - 210px)", "overflowY": "auto"},
            ),
        ],
        style={
            "backgroundColor": THEME["card_bg"],
            "border": f"1px solid {THEME['card_border']}",
            "boxShadow": "0 8px 24px rgba(0,0,0,0.5)",
            "borderRadius": "8px",
        },
    )
    return sidebar_layout


# ==============================================================================
# 5. REAL-TIME BOTTOM TACTICAL MATRIX (DataTable)
# ==============================================================================