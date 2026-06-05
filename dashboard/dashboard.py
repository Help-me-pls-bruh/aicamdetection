"""
SentinelAI - Police Operations Dashboard
Built with Streamlit.
Displays: Live risk map, crime stats, alerts, CCTV feed, historical analysis.
"""

import sys
import os
import time
import base64
import random
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.h3_utils import latlng_to_cell, cell_to_boundary

import streamlit as st

# How often the live map + events refresh (seconds). Lower = faster changes.
REFRESH_SECS = 4

# KL area covered by the hexagon grid (tight around the city so it fills the view).
KL_LAT_RANGE = (3.085, 3.215)
KL_LON_RANGE = (101.605, 101.770)
HEX_RES = 8  # ~0.74 km^2 hexagons (same scale as Uber H3 city tiling)

st.set_page_config(
    page_title="SentinelAI - Crime Prevention",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:5000/api"

RISK_COLORS = {
    "LOW": "#22c55e",
    "MEDIUM": "#eab308",
    "HIGH": "#f97316",
    "CRITICAL": "#ef4444",
}

# Live-map demo levels (3 clear tiers). HIGH is red and intentionally rare.
DEMO_LEVELS = {
    "SAFE":   {"color": "#1e9e57", "z": 0.08},
    "MEDIUM": {"color": "#f5a524", "z": 0.55},
    "HIGH":   {"color": "#e11d48", "z": 0.92},
}

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 18px !important; }
    h1 { font-size: 2.6rem !important; }
    h2 { font-size: 2.1rem !important; }
    h3 { font-size: 1.7rem !important; }
    h4 { font-size: 1.4rem !important; }
    p, label, span, div { font-size: 1.05rem !important; }
    .stButton > button {
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        padding: 0.9rem 1.6rem !important;
        min-height: 56px !important;
        border-radius: 12px !important;
        width: 100% !important;
    }
    .stSelectbox label, .stTextInput label, .stNumberInput label {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
    }
    .stTextInput input, .stNumberInput input {
        font-size: 1.15rem !important;
        min-height: 52px !important;
        padding: 0.7rem !important;
    }
    .stSelectbox div[data-baseweb="select"] {
        min-height: 52px !important;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        min-height: 52px !important;
        font-size: 1.15rem !important;
        line-height: 1.5 !important;
        padding: 0.4rem 0.8rem !important;
        display: flex !important;
        align-items: center !important;
    }
    .stSelectbox div[data-baseweb="select"] input {
        font-size: 1.15rem !important;
    }
    div[data-baseweb="popover"] li {
        font-size: 1.1rem !important;
        min-height: 48px !important;
        padding: 0.6rem 1rem !important;
        line-height: 1.4 !important;
    }
    .stMetric { padding: 0.5rem !important; }
    .stMetric label { font-size: 1.1rem !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 800 !important; }
    [data-testid="stMetricDelta"] { font-size: 1.1rem !important; }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        padding: 1rem 1.5rem !important;
        min-height: 60px !important;
    }
    .stDataFrame { font-size: 1.1rem !important; }
    .stForm { padding: 1.5rem !important; border-radius: 16px !important; }
    .main-header {
        font-size: 2.4rem;
        font-weight: 700;
        color: #1e293b;
        padding: 0.5rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 16px;
        color: white;
        text-align: center;
    }
    .metric-card h3 { margin: 0; font-size: 1.1rem; opacity: 0.9; }
    .metric-card h1 { margin: 0.4rem 0 0 0; font-size: 2.6rem; }
    .alert-critical {
        background: #fef2f2;
        border-left: 6px solid #ef4444;
        padding: 1.2rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
        font-size: 1.15rem;
    }
    .alert-high {
        background: #fff7ed;
        border-left: 6px solid #f97316;
        padding: 1.2rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
        font-size: 1.15rem;
    }
    .risk-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 24px;
        font-weight: 700;
        font-size: 1rem;
    }
    @media (max-width: 768px) {
        html, body, [class*="css"] { font-size: 20px !important; }
        .stButton > button { font-size: 1.3rem !important; min-height: 64px !important; }
        [data-testid="stMetricValue"] { font-size: 2rem !important; }
        .stTabs [data-baseweb="tab"] { font-size: 1.1rem !important; min-height: 56px !important; }
    }
</style>
""", unsafe_allow_html=True)


def _inject_kino_and_theme():
    """Load the KINO display font + branded theme styles."""
    font_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "assets", "Kino-Regular.ttf"
    )
    face = ""
    if os.path.exists(font_path):
        with open(font_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        face = ("@font-face{font-family:'Kino';src:url(data:font/ttf;base64,__B64__)"
                " format('truetype');font-display:swap;}").replace("__B64__", b64)

    css = face + """
    h1, h2, h3, .brand-title { font-family:'Kino', Georgia, serif !important;
        letter-spacing:0.5px; }
    .brand-bar { background:linear-gradient(120deg,#0b1f3a 0%,#13315c 60%,#1d4e89 100%);
        border-radius:16px; padding:1.1rem 1.6rem; margin-bottom:0.4rem;
        display:flex; align-items:center; justify-content:space-between;
        box-shadow:0 6px 20px rgba(11,31,58,0.25); }
    .brand-title { color:#ffffff !important; font-size:3rem !important; margin:0;
        line-height:1.05; }
    .brand-sub { color:#9ec1ff !important; font-size:0.95rem !important;
        letter-spacing:3px; text-transform:uppercase; margin-top:0.3rem; }
    .brand-right { text-align:right; color:#cfe0ff !important;
        font-size:0.95rem !important; line-height:1.6; }
    .live-dot { display:inline-block; width:11px; height:11px; border-radius:50%;
        background:#e11d48; margin-right:7px;
        box-shadow:0 0 0 0 rgba(225,29,72,0.7); animation:pulse 1.4s infinite; }
    @keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(225,29,72,0.6);}
        70%{box-shadow:0 0 0 12px rgba(225,29,72,0);}
        100%{box-shadow:0 0 0 0 rgba(225,29,72,0);} }
    .hex-legend { display:flex; gap:1.2rem; align-items:center; margin:0.4rem 0 0.2rem 0;
        font-size:0.95rem !important; font-weight:600; color:#334155; }
    .sw { display:inline-block; width:15px; height:15px; border-radius:4px;
        margin-right:6px; vertical-align:middle; }
    .ev-card { border-radius:12px; padding:0.7rem 1rem; margin-bottom:0.55rem;
        background:#ffffff; border-left:6px solid #94a3b8;
        box-shadow:0 2px 8px rgba(15,23,42,0.06); }
    .ev-high { border-left-color:#e11d48; background:#fff1f4; }
    .ev-med  { border-left-color:#f5a524; background:#fffaf0; }
    .ev-type { font-weight:800; font-size:1.05rem !important; color:#0f172a; }
    .ev-meta { font-size:0.85rem !important; color:#64748b; }
    .ev-score { float:right; font-weight:800; font-size:1.2rem !important; }
    """
    st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)


_inject_kino_and_theme()


def api_get(endpoint):
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", timeout=5)
        return resp.json()
    except Exception:
        return None


def api_post(endpoint, data=None):
    try:
        resp = requests.post(f"{API_BASE}{endpoint}", json=data or {}, timeout=5)
        return resp.json()
    except Exception:
        return None


def render_header():
    status = api_get("/status")
    if status:
        right = (f'<span class="live-dot"></span>SYSTEM ONLINE &middot; '
                 f'{status.get("zones_loaded", 0):,} zones')
    else:
        right = 'API OFFLINE — run <code>python run.py</code>'
    st.markdown(
        '<div class="brand-bar">'
        '<div><div class="brand-title">SENTINEL AI</div>'
        '<div class="brand-sub">Crime Prevention &amp; Response Platform</div></div>'
        f'<div class="brand-right">{right}<br>'
        f'{datetime.now().strftime("%a %d %b %Y &middot; %H:%M:%S")}</div>'
        '</div>', unsafe_allow_html=True)


def render_metrics():
    stats = api_get("/crimes/stats")
    zones_risk = api_get("/zones/risk")
    raw_alerts = api_get("/alerts?limit=100")
    alerts = raw_alerts if isinstance(raw_alerts, list) else (raw_alerts.get("alerts", []) if raw_alerts else [])
    feedback_stats = api_get("/feedback/stats")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total = stats.get("total_crimes", 0) if stats else 0
        st.metric("Total Crime Records", f"{total:,}")

    with col2:
        recent = stats.get("recent_24h", 0) if stats else 0
        st.metric("Last 24 Hours", recent)

    with col3:
        critical = 0
        high = 0
        if zones_risk and isinstance(zones_risk, list):
            critical = sum(1 for z in zones_risk if z.get("risk_level") == "CRITICAL")
            high = sum(1 for z in zones_risk if z.get("risk_level") == "HIGH")
        st.metric("Critical Zones", critical, delta=f"+{high} High")

    with col4:
        alert_count = len(alerts)
        st.metric("Active Alerts", alert_count)

    with col5:
        accuracy = feedback_stats.get("accuracy", 0) if feedback_stats else 0
        st.metric("Model Accuracy", f"{accuracy:.0%}")


@st.cache_data(show_spinner=False)
def get_kl_hex_grid(res=HEX_RES):
    """
    Build the full set of H3 hexagons that tile the KL area (cached once).
    Returns {h3_index: [[lat,lng], ...] boundary}. The sampling step is smaller
    than a hexagon, so every cell in the area is captured with no gaps — the
    result tiles the whole map exactly like Uber's H3 grid.
    """
    cells = {}
    step = 0.0035
    lat = KL_LAT_RANGE[0]
    while lat <= KL_LAT_RANGE[1]:
        lon = KL_LON_RANGE[0]
        while lon <= KL_LON_RANGE[1]:
            c = latlng_to_cell(lat, lon, res)
            if c and c not in cells:
                b = cell_to_boundary(c)
                if b:
                    cells[c] = b
            lon += step
        lat += step
    return cells


def assign_demo_risk(cell_ids):
    """
    Fast random scoring with a CONTROLLED distribution so it looks realistic:
      - 2-4 HIGH zones (red, rare)
      - 3-5 MEDIUM zones (amber)
      - everything else SAFE (green)
    Re-rolled on every refresh, so the map changes continuously.
    """
    cells = list(cell_ids)
    random.shuffle(cells)
    levels = {}
    n_high = random.randint(2, 4)
    n_med = random.randint(3, 5)
    for c in cells[:n_high]:
        levels[c] = "HIGH"
    for c in cells[n_high:n_high + n_med]:
        levels[c] = "MEDIUM"
    for c in cells[n_high + n_med:]:
        levels[c] = "SAFE"
    return levels, n_high, n_med


def _hex_geojson(grid, cell_ids):
    feats = []
    for c in cell_ids:
        ring = [[p[1], p[0]] for p in grid[c]]  # [lat,lng] -> [lng,lat]
        if len(ring) < 3:
            continue
        ring.append(ring[0])
        feats.append({"type": "Feature", "id": c,
                      "geometry": {"type": "Polygon", "coordinates": [ring]}})
    return {"type": "FeatureCollection", "features": feats}


EVENT_TYPES = [
    ("BURGLARY", "\U0001F3E0"), ("THEFT / SNATCH", "\U0001F45C"),
    ("ROBBERY", "\U0001F4B0"), ("SUSPICIOUS RUNNING", "\U0001F3C3"),
    ("ASSAULT", "⚠️"), ("VEHICLE THEFT", "\U0001F697"),
    ("LOITERING", "\U0001F6B6"), ("VANDALISM", "\U0001FAA7"),
]
KL_PLACES = ["Bukit Bintang", "Chow Kit", "Petaling Street", "KL Sentral",
             "Bangsar", "Ampang", "Setapak", "Cheras", "Wangsa Maju", "Kepong"]


def gen_demo_events(levels):
    """Generate 4-8 live incidents anchored on the HIGH/MEDIUM hexes."""
    has_hot = any(l in ("HIGH", "MEDIUM") for l in levels.values())
    events = []
    for _ in range(random.randint(4, 8)):
        etype, icon = random.choice(EVENT_TYPES)
        lvl = "HIGH" if (has_hot and random.random() < 0.4) else "MEDIUM"
        score = random.randint(78, 96) if lvl == "HIGH" else random.randint(42, 64)
        events.append({
            "type": etype, "icon": icon, "level": lvl, "score": score,
            "place": random.choice(KL_PLACES), "ago": random.randint(1, 180),
        })
    events.sort(key=lambda e: -e["score"])
    return events


@st.fragment(run_every=REFRESH_SECS)
def render_live_map_events():
    """The live hexagon risk map + incident feed. Auto-refreshes on its own."""
    grid = get_kl_hex_grid()
    if not grid:
        st.info("Building hex grid...")
        return
    levels, n_high, n_med = assign_demo_risk(list(grid.keys()))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hexagons Monitored", f"{len(grid):,}")
    c2.metric("High-Risk Zones", n_high)
    c3.metric("Medium-Risk Zones", n_med)
    c4.metric("Last Update", datetime.now().strftime("%H:%M:%S"))

    map_col, ev_col = st.columns([2, 1])

    with map_col:
        st.markdown(
            '<div class="hex-legend">'
            '<span><span class="sw" style="background:#1e9e57"></span>Safe</span>'
            '<span><span class="sw" style="background:#f5a524"></span>Medium</span>'
            '<span><span class="sw" style="background:#e11d48"></span>High Risk</span>'
            '</div>', unsafe_allow_html=True)
        cell_ids = list(grid.keys())
        z = [DEMO_LEVELS[levels[c]]["z"] for c in cell_ids]
        colorscale = [[0.0, "#1e9e57"], [0.25, "#3fb16b"], [0.44, "#f5a524"],
                      [0.6, "#f08a1d"], [0.8, "#e11d48"], [1.0, "#b00d36"]]
        fig = go.Figure(go.Choroplethmapbox(
            geojson=_hex_geojson(grid, cell_ids),
            locations=cell_ids, z=z, featureidkey="id",
            colorscale=colorscale, zmin=0, zmax=1,
            marker_opacity=0.55, marker_line_width=0.6,
            marker_line_color="#5b6b85", showscale=False, hoverinfo="skip",
        ))
        fig.update_layout(
            mapbox_style="carto-positron", mapbox_zoom=12.2,
            mapbox_center={"lat": 3.150, "lon": 101.690},
            height=600, margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with ev_col:
        st.markdown('<span class="live-dot"></span> **LIVE INCIDENT FEED**',
                    unsafe_allow_html=True)
        for e in gen_demo_events(levels):
            cls = "ev-high" if e["level"] == "HIGH" else "ev-med"
            color = "#e11d48" if e["level"] == "HIGH" else "#d97706"
            st.markdown(
                f'<div class="ev-card {cls}">'
                f'<span class="ev-score" style="color:{color}">{e["score"]}%</span>'
                f'<div class="ev-type">{e["icon"]} {e["type"]}</div>'
                f'<div class="ev-meta">{e["place"]} &middot; {e["ago"]}s ago '
                f'&middot; {e["level"]}</div></div>', unsafe_allow_html=True)


def render_alerts_panel():
    st.subheader("Alerts")

    raw = api_get("/alerts?limit=30")
    if not raw:
        st.info("No alerts.")
        return
    alerts = raw if isinstance(raw, list) else raw.get("alerts", [])
    if not alerts:
        st.info("No alerts.")
        return

    for alert in alerts[:15]:
        level = alert.get("risk_level", "LOW")
        css_class = "alert-critical" if level == "CRITICAL" else "alert-high"
        score = alert.get("risk_score", 0)
        zone = alert.get("zone_id", "")
        desc = alert.get("description", "")[:120]
        ts = alert.get("timestamp", "")[:19]

        if level in ("CRITICAL", "HIGH"):
            st.markdown(
                f"""<div class="{css_class}">
                    <strong>{level}</strong> | Zone: {zone} | Risk: {score:.0%}<br>
                    <small>{ts} - {desc}</small>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.caption("Officer Feedback")
    with st.form("feedback_form"):
        col1, col2 = st.columns(2)
        with col1:
            alert_id = st.number_input("Alert ID", min_value=1, step=1)
            zone_id = st.text_input("Zone ID")
        with col2:
            label = st.selectbox("Verdict", ["TRUE_CRIME", "FALSE_ALARM"])
            notes = st.text_input("Notes")

        if st.form_submit_button("Submit Feedback"):
            result = api_post("/feedback", {
                "alert_id": alert_id,
                "zone_id": zone_id,
                "label": label,
                "notes": notes,
            })
            if result:
                st.success(f"Feedback submitted: {label}")


def render_crime_stats():
    st.subheader("Crime Analytics")

    stats = api_get("/crimes/stats")
    if not stats:
        return

    col1, col2 = st.columns(2)

    with col1:
        by_type = stats.get("by_type", [])
        if by_type:
            df_type = pd.DataFrame(by_type)
            fig = px.bar(
                df_type, x="event_type", y="cnt",
                color="cnt", color_continuous_scale="reds",
                title="Crimes by Type",
                labels={"cnt": "Count", "event_type": "Crime Type"},
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        top_zones = stats.get("top_zones", [])
        if top_zones:
            df_zones = pd.DataFrame(top_zones[:10])
            fig = px.bar(
                df_zones, x="zone_id", y="cnt",
                color="cnt", color_continuous_scale="oranges",
                title="Top 10 Crime Zones",
                labels={"cnt": "Incidents", "zone_id": "Zone"},
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


def render_realtime_events():
    st.subheader("Real-Time Events")

    events = api_get("/realtime/events")
    if not events:
        st.info("No active real-time events.")
        return

    df = pd.DataFrame(events)
    display_cols = ["timestamp", "zone_id", "event_type", "confidence_score", "source"]
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(
        df[available].head(20),
        use_container_width=True,
        hide_index=True,
    )


def render_cctv_panel():
    st.subheader("CCTV Control")

    status = api_get("/status")
    cam_active = status.get("camera_active", False) if status else False

    col1, col2, col3 = st.columns(3)
    with col1:
        source_type = st.selectbox("Source", ["Webcam", "RTSP Camera", "Video File"])
    with col2:
        if source_type == "Webcam":
            source = st.number_input("Camera Index", value=0, min_value=0, max_value=5)
        elif source_type == "RTSP Camera":
            source = st.text_input(
                "RTSP URL",
                placeholder="rtsp://user:pass@192.168.0.101:554/stream1",
            )
        else:
            source = st.text_input("Video File Path")
    with col3:
        cam_lat = st.number_input("Camera Lat", value=3.1466, format="%.4f")
        cam_lon = st.number_input("Camera Lon", value=101.7108, format="%.4f")

    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("Start Camera", type="primary"):
            result = api_post("/camera/start", {
                "source": source,
                "lat": cam_lat,
                "lon": cam_lon,
            })
            if result:
                st.success("Camera started!")
                st.rerun()
    with col_stop:
        if st.button("Stop Camera"):
            api_post("/camera/stop")
            st.info("Camera stopped.")
            st.rerun()

    if cam_active:
        st.markdown("**Live Feed:**")
        st.image(f"{API_BASE}/camera/feed", use_container_width=True)

        detections = api_get("/camera/detections")
        if detections:
            dcol1, dcol2, dcol3 = st.columns(3)
            with dcol1:
                st.metric("Persons Detected", detections.get("person_count", 0))
            with dcol2:
                st.metric("Recent Events", len(detections.get("recent_events", [])))
            with dcol3:
                st.metric("Face Matches", len(detections.get("face_matches", [])))

            recent = detections.get("recent_events", [])
            if recent:
                st.markdown("**Recent Detection Events:**")
                for event in recent[-5:]:
                    etype = event.get("event_type", "")
                    conf = event.get("confidence_score", 0)
                    details = event.get("details", "")
                    if etype in ("PERSON_CHASING", "WEAPON_DETECTED", "FACE_MATCH_WANTED"):
                        st.error(f"{etype} ({conf:.0%}) - {details}")
                    elif etype in ("SUSPICIOUS_RUNNING", "ASSAULT"):
                        st.warning(f"{etype} ({conf:.0%}) - {details}")
                    else:
                        st.info(f"{etype} ({conf:.0%}) - {details}")


def render_zone_detail():
    st.subheader("Zone Risk Breakdown")

    all_zones = api_get("/zones") or []
    risk_zones = api_get("/zones/risk") or []

    if not all_zones:
        st.warning("No zones available yet.")
        return

    risk_map = {z["zone_id"]: z for z in risk_zones} if isinstance(risk_zones, list) else {}

    zone_options = []
    for z in all_zones:
        zid = z["zone_id"]
        risk_info = risk_map.get(zid)
        if risk_info:
            level = risk_info.get("risk_level", "LOW")
            risk_pct = risk_info.get("r_zone", 0) * 100
            zone_options.append((f"{zid}  -  {level}  ({risk_pct:.1f}%)", zid))
        else:
            zone_options.append((f"{zid}  -  LOW  (0.0%)", zid))

    zone_options.sort(key=lambda x: -(risk_map.get(x[1], {}).get("r_zone", 0)))

    selected_label = st.selectbox(
        "Select a Zone:",
        options=[opt[0] for opt in zone_options],
        key="zone_detail_select",
    )

    zone_id = next((opt[1] for opt in zone_options if opt[0] == selected_label), None)
    if not zone_id:
        return

    data = api_get(f"/zones/{zone_id}/risk")
    if not data or "error" in data:
        st.error(f"Zone {zone_id} not found.")
        return

    zone = data.get("zone", {})
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("P_spatial (HDBSCAN)", f"{zone.get('p_spatial', 0):.2%}")
    with col2:
        st.metric("P_time (SARIMA)", f"{zone.get('p_time', 0):.2%}")
    with col3:
        st.metric("P_base (Historical)", f"{zone.get('p_base', 0):.2%}")
    with col4:
        level = zone.get("risk_level", "LOW")
        color = RISK_COLORS.get(level, "#gray")
        st.metric("Final Risk R_zone", f"{zone.get('r_zone', 0):.2%}")
        st.markdown(
            f"<span style='color:{color};font-weight:bold;font-size:1.6rem'>{level}</span>",
            unsafe_allow_html=True,
        )

    center_lat = zone.get("center_lat")
    center_lon = zone.get("center_lon")
    if center_lat and center_lon:
        st.markdown(f"### Zone Location: `{zone_id}`")
        st.markdown(f"**Center:** {center_lat:.6f}, {center_lon:.6f}")

        zone_df = pd.DataFrame([{
            "zone_id": zone_id,
            "lat": center_lat,
            "lon": center_lon,
            "risk_level": level,
            "risk_pct": zone.get("r_zone", 0) * 100,
        }])

        fig_map = px.scatter_mapbox(
            zone_df,
            lat="lat",
            lon="lon",
            color="risk_level",
            color_discrete_map=RISK_COLORS,
            size=[40],
            size_max=40,
            hover_name="zone_id",
            hover_data={"risk_pct": ":.1f", "lat": False, "lon": False, "risk_level": True},
            mapbox_style="carto-positron",
            center={"lat": center_lat, "lon": center_lon},
            zoom=15,
            height=400,
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_map, use_container_width=True)

    st.markdown("**Risk Formula:** `R_zone = 0.4 * P_base + 0.6 * P_realtime`")
    st.markdown(f"- P_base = 0.5 * P_spatial + 0.5 * P_time = **{zone.get('p_base', 0):.4f}**")
    st.markdown(f"- P_realtime = **{zone.get('p_realtime', 0):.4f}**")

    history = data.get("risk_history", [])
    if history:
        df_hist = pd.DataFrame(history)
        df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])
        fig = px.line(
            df_hist, x="timestamp", y="r_zone",
            title=f"Risk Score Over Time - {zone_id}",
            labels={"r_zone": "Risk Score", "timestamp": "Time"},
        )
        fig.add_hline(y=0.75, line_dash="dash", line_color="red", annotation_text="CRITICAL")
        fig.add_hline(y=0.55, line_dash="dash", line_color="orange", annotation_text="HIGH")
        fig.add_hline(y=0.30, line_dash="dash", line_color="gold", annotation_text="MEDIUM")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)


def render_citizen_report():
    st.subheader("Citizen Incident Report")

    with st.form("citizen_report"):
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", value=3.1466, format="%.4f")
            lon = st.number_input("Longitude", value=101.7108, format="%.4f")
        with col2:
            event_type = st.selectbox("Crime Type", [
                "THEFT_SNATCH", "ASSAULT", "ROBBERY", "SUSPICIOUS_ACTIVITY",
                "VANDALISM", "VEHICLE_THEFT", "BURGLARY", "DRUG_OFFENSE",
            ])

        if st.form_submit_button("Submit Report", type="primary"):
            result = api_post("/report", {
                "latitude": lat,
                "longitude": lon,
                "event_type": event_type,
            })
            if result and result.get("success"):
                st.success(f"Report submitted! Zone: {result.get('zone_id')}")
            else:
                st.error("Failed to submit report.")


def render_probability_explainer():
    st.subheader("Risk Scoring Explained")

    st.markdown("""
    **How SentinelAI calculates crime risk:**

    **Step 1: Historical Baseline (P_base)**
    - HDBSCAN clusters past crimes into hotspots -> P_spatial
    - SARIMA predicts time-based crime trends -> P_time
    - `P_base = 0.5 * P_spatial + 0.5 * P_time`

    **Step 2: Real-Time Events (P_realtime)**
    - Each event: `P_event = AI_confidence x Reliability_Weight`
    - Per-event decay: `P_event_decayed = P_event x e^(-lambda_category x t)`
    - Combined: `P_combined = 1 - Product(1 - P_event_decayed_i)`
    - Context: `W_context = W_time x W_crowd x W_recency x W_zone`
    - `P_realtime = P_combined x W_context`

    **Step 3: Final Fusion**
    - `R_zone = 0.4 * P_base + 0.6 * P_realtime`

    **Step 4: Continuous Decay (Zone-Level + Per-Event)**
    - Zone: `New Score = (1-0.6) * Previous * e^(-lambda*t) + 0.6 * New Input`
    - Each event type has its own decay rate and active window
    """)

    st.markdown("**Per-Event-Type Decay Intervals:**")
    decay_data = {
        "Event Type": [
            "Suspicious Running", "Loitering", "Crowd Anomaly",
            "Person Chasing", "Weapon Detected", "Face Match (Wanted)",
            "Assault", "Theft/Snatch", "Robbery", "Suspicious Activity",
        ],
        "Decay Rate (lambda)": [0.08, 0.04, 0.05, 0.06, 0.01, 0.005, 0.03, 0.04, 0.03, 0.10],
        "Active Window (sec)": [60, 180, 120, 90, 300, 600, 120, 120, 150, 60],
    }
    st.dataframe(pd.DataFrame(decay_data), hide_index=True, use_container_width=True)

    st.markdown("**Event Reliability Weights:**")
    weights_data = {
        "Event Type": [
            "Suspicious Running", "Loitering", "Crowd Anomaly",
            "Person Chasing", "Weapon Detected", "Face Match (Wanted)",
            "Assault", "Theft/Snatch", "Robbery",
        ],
        "Weight": [0.30, 0.20, 0.50, 0.70, 0.90, 0.95, 0.70, 0.60, 0.75],
    }
    st.dataframe(pd.DataFrame(weights_data), hide_index=True, use_container_width=True)

    st.markdown("**Risk Thresholds:**")
    threshold_data = {
        "Score Range": ["0.00 - 0.30", "0.30 - 0.55", "0.55 - 0.75", "0.75 - 1.00"],
        "Level": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        "Color": ["Green", "Yellow", "Orange", "Red"],
        "Action": [
            "Standard patrol",
            "Elevated awareness",
            "Priority dispatch + public alert",
            "Immediate response + command escalation",
        ],
    }
    st.dataframe(pd.DataFrame(threshold_data), hide_index=True, use_container_width=True)


def _build_hex_geojson(cells):
    """Turn H3 cell boundaries into a GeoJSON FeatureCollection for the map."""
    features = []
    for c in cells:
        boundary = c.get("boundary") or []
        if len(boundary) < 3:
            continue
        ring = [[pt[1], pt[0]] for pt in boundary]  # [lat,lng] -> [lng,lat]
        ring.append(ring[0])                         # close the polygon
        features.append({
            "type": "Feature",
            "id": c["h3_index"],
            "properties": {"h3_index": c["h3_index"]},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    return {"type": "FeatureCollection", "features": features}


def render_patrol_dispatch():
    st.subheader("Patrol Dispatch — H3 Spatial Intelligence")
    st.caption(
        "Uber H3 hexagonal indexing converts each incident into a hex cell, then "
        "recommends the nearest patrol unit. Patrol positions are simulated for "
        "this prototype; the architecture scales to real patrol GPS feeds."
    )

    # ============ ACTIVE INCIDENT / DISPATCH RECOMMENDATION ============
    st.markdown("### Active Incident Dispatch")
    zones = api_get("/zones/risk") or []
    zone_opts = []
    if isinstance(zones, list):
        for z in sorted(zones, key=lambda x: -(x.get("r_zone", 0))):
            zone_opts.append(
                (f"{z['zone_id']}  -  {z.get('risk_level','LOW')} "
                 f"({z.get('r_zone',0)*100:.1f}%)", z["zone_id"])
            )

    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        if zone_opts:
            picked = st.selectbox(
                "Select a high-risk zone to dispatch a patrol:",
                options=[o[0] for o in zone_opts], key="dispatch_zone_select",
            )
            picked_zone = next((o[1] for o in zone_opts if o[0] == picked), None)
        else:
            st.info("No active risk zones yet. Run the demo simulator to create incidents.")
            picked_zone = None
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        dispatch_clicked = st.button("Recommend Patrol", type="primary",
                                     use_container_width=True)

    if dispatch_clicked and picked_zone:
        rec = api_post("/dispatch/recommend", {"zone_id": picked_zone})
        st.session_state["last_dispatch"] = rec

    rec = st.session_state.get("last_dispatch")
    if rec and rec.get("success"):
        np_ = rec["nearest_patrol"]
        risk_pct = rec.get("risk_score", 0) * 100
        st.markdown(
            f"""
            <div style="background:#0f172a;border:2px solid #ef4444;border-radius:16px;
                        padding:1.5rem;color:#f8fafc;">
              <div style="font-size:1.3rem;font-weight:800;color:#ef4444;
                          letter-spacing:1px;">🚨 ACTIVE INCIDENT</div>
              <div style="display:flex;flex-wrap:wrap;gap:2rem;margin-top:1rem;">
                <div><div style="opacity:.7;font-size:.95rem;">Location</div>
                     <div style="font-size:1.3rem;font-weight:700;">
                       {rec.get('zone_id','-')}</div>
                     <div style="opacity:.6;font-size:.85rem;">
                       {rec.get('event_lat',0):.4f}, {rec.get('event_lon',0):.4f}</div></div>
                <div><div style="opacity:.7;font-size:.95rem;">Risk Score</div>
                     <div style="font-size:1.8rem;font-weight:800;color:#f97316;">
                       {risk_pct:.0f}%</div></div>
                <div><div style="opacity:.7;font-size:.95rem;">H3 Cell</div>
                     <div style="font-size:1.05rem;font-family:monospace;">
                       {rec.get('h3_index','-')}</div></div>
                <div><div style="opacity:.7;font-size:.95rem;">Nearest Patrol</div>
                     <div style="font-size:1.4rem;font-weight:800;color:#22c55e;">
                       {np_['name']}</div></div>
                <div><div style="opacity:.7;font-size:.95rem;">Distance</div>
                     <div style="font-size:1.8rem;font-weight:800;">
                       {rec.get('distance_km',0):.1f} km</div></div>
                <div><div style="opacity:.7;font-size:.95rem;">Est. Response</div>
                     <div style="font-size:1.8rem;font-weight:800;color:#38bdf8;">
                       {rec.get('eta_minutes',0):.0f} min</div></div>
              </div>
              <div style="margin-top:1rem;opacity:.75;font-size:.9rem;">
                Coverage zone: <b>{rec.get('covered_by','-')}</b>
                &nbsp;|&nbsp; Hex distance: {rec.get('hex_distance','-')} cells
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif rec and not rec.get("success"):
        st.warning(rec.get("reason", "No dispatch available."))

    st.markdown("---")

    # ============ H3 HOTSPOT HEATMAP + PATROLS ============
    st.markdown("### H3 Crime Hotspot Map")
    intensity = api_get("/h3/intensity?limit=200") or []
    patrols = api_get("/patrols") or []

    if not intensity:
        st.info("No H3 intensity data yet.")
    else:
        geojson = _build_hex_geojson(intensity)
        cell_ids = [c["h3_index"] for c in intensity]
        counts = [c["crime_count"] for c in intensity]

        fig = go.Figure(go.Choroplethmapbox(
            geojson=geojson,
            locations=cell_ids,
            z=counts,
            featureidkey="id",
            colorscale="YlOrRd",
            marker_opacity=0.55,
            marker_line_width=0.4,
            marker_line_color="#64748b",
            colorbar_title="Crimes",
            hovertemplate="H3 %{location}<br>Crimes: %{z}<extra></extra>",
        ))

        if patrols:
            fig.add_trace(go.Scattermapbox(
                lat=[p["latitude"] for p in patrols],
                lon=[p["longitude"] for p in patrols],
                mode="markers+text",
                marker=dict(size=16, color="#2563eb"),
                text=[p["name"].replace("Patrol ", "") for p in patrols],
                textposition="top center",
                textfont=dict(size=13, color="#1e3a8a"),
                hovertext=[f"{p['name']} ({p.get('status','')})" for p in patrols],
                hoverinfo="text",
                name="Patrols",
            ))

        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=11,
            mapbox_center={"lat": 3.155, "lon": 101.705},
            height=600,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"{len(intensity)} active H3 cells • {len(patrols)} patrol units • "
                   "blue markers = patrol positions")

    # ============ PATROL UNITS + RECENT DISPATCHES ============
    colp, cold = st.columns(2)
    with colp:
        st.markdown("### Patrol Units")
        if patrols:
            dfp = pd.DataFrame(patrols)[["name", "status", "latitude", "longitude"]]
            dfp.columns = ["Patrol", "Status", "Lat", "Lon"]
            st.dataframe(dfp, hide_index=True, use_container_width=True)
    with cold:
        st.markdown("### Recent Dispatches")
        dispatches = api_get("/dispatches?limit=15") or []
        if dispatches:
            dfd = pd.DataFrame(dispatches)
            cols = [c for c in ["timestamp", "patrol_name", "zone_id",
                                "distance_km", "eta_minutes"] if c in dfd.columns]
            dfd = dfd[cols].copy()
            if "timestamp" in dfd:
                dfd["timestamp"] = dfd["timestamp"].str[:19]
            st.dataframe(dfd, hide_index=True, use_container_width=True)
        else:
            st.info("No dispatches yet. Recommend a patrol above, or wait for an auto-alert.")


def main():
    render_header()
    st.markdown("---")
    render_metrics()
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Risk Map", "Patrol Dispatch", "CCTV Monitor", "Alerts",
        "Crime Analytics", "Zone Detail", "System Info",
    ])

    with tab1:
        render_live_map_events()

    with tab2:
        render_patrol_dispatch()

    with tab3:
        render_cctv_panel()

    with tab4:
        render_alerts_panel()

    with tab5:
        render_crime_stats()

    with tab6:
        render_zone_detail()
        render_citizen_report()

    with tab7:
        render_probability_explainer()

        st.markdown("---")
        st.subheader("System Architecture")
        st.code("""
    TP-Link CCTV (RTSP)
            |
    YOLOv8 Detection + ByteTrack Tracking
            |
    Behavior Analysis (running, chasing, loitering, fighting)
            |
    DeepFace (wanted criminal matching)
            |
    Probabilistic Fusion Engine
    R_zone = 0.4*P_base + 0.6*P_realtime
            |
    Alert System (HIGH / CRITICAL)
            |
    Uber H3 Spatial Indexing (lat/lon -> hexagon cell)
            |
    Nearest Patrol Search + Coverage Zones
            |
    Dispatch Recommendation (distance + ETA)
            |
    SQLite Database (historical logs)
            |
    Flask API  ->  Streamlit Dashboard (this page)
        """)

        st.markdown("""
        **Why H3 hexagons instead of square grids?**
        Traditional systems divide a city into square cells, where edge and
        diagonal neighbours sit at different distances. Uber's H3 gives every
        hexagon 6 equidistant neighbours, producing more consistent hotspot
        clustering and more realistic patrol coverage zones. Each incident is
        indexed to an H3 cell, then matched to the nearest patrol unit.

        *Prototype note: patrol units use simulated GPS positions. The design
        scales to real patrol feeds — only the data source changes.*
        """)


if __name__ == "__main__":
    main()
