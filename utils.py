import streamlit as st
import pandas as pd
import requests
import os
import wikipedia
from geopy.geocoders import Nominatim

# === 1. הגדרות עמוד ועיצוב ===
def page_setup():
    st.set_page_config(
        page_title="Real Estate OS",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    if 'weights' not in st.session_state:
        st.session_state.weights = {
            'inventory': 2.0, 'velocity': 1.5, 'economy': 1.0, 'demography': 1.0
        }

    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;700&display=swap');
        body { font-family: 'Rubik', sans-serif; background-color: #fdfdfd; }
        
        /* תיקון כפתור התפריט */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            z-index: 1000000 !important;
            pointer-events: none;
        }
        header[data-testid="stHeader"] button {
            pointer-events: auto;
            color: #5f6368 !important; 
        }

        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        .block-container { padding-top: 80px !important; }
        
        /* כותרת גוגל */
        .google-header {
            position: fixed; top: 0; left: 0; width: 100%; height: 64px;
            background: white; border-bottom: 1px solid #dadce0;
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 20px 0 80px; /* רווח שמאלי לכפתור */
            z-index: 99999;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .header-logo { font-size: 22px; font-weight: 500; color: #5f6368; display: flex; align-items: center; gap: 8px; }
        .header-user { display: flex; align-items: center; gap: 15px; }
        .user-avatar { width: 32px; height: 32px; background: #1a73e8; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; }
        .user-text { text-align: left; line-height: 1.2; }
        .u-name { font-size: 13px; font-weight: 500; color: #3c4043; }
        .u-email { font-size: 11px; color: #5f6368; }
        </style>
    """, unsafe_allow_html=True)

def render_header():
    # זיהוי משתמש
    email = "guest@investor.com"
    name = "Guest"
    initial = "G"
    try:
        if hasattr(st, "user") and st.user:
            email = st.user.email
        elif hasattr(st, "experimental_user") and st.experimental_user:
            email = st.experimental_user.email
        
        if email != "guest@investor.com":
            name = email.split('@')[0]
            initial = email[0].upper()
    except: pass

    # HTML נקי ללא הזחות (חשוב!)
    st.markdown(f"""<div class="google-header"><div class="header-logo"><span>🏠 Real Estate OS</span></div><div class="header-user"><a href="#" style="text-decoration:none; font-size:20px; color:#5f6368;">⚙️</a><div class="user-text"><div class="u-name">{name}</div><div class="u-email">{email}</div></div><div class="user-avatar" title="{email}">{initial}</div></div></div>""", unsafe_allow_html=True)

# פונקציות נתונים
@st.cache_data
def load_data():
    file_path = "us_cities.csv"
    if not os.path.exists(file_path): return None, "Missing CSV"
    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip().str.upper()
        df.rename(columns={'STATE_ID': 'STATE_CODE', 'STATE_NAME': 'STATE', 'CITY_ASCII': 'CITY'}, inplace=True)
        for col in ['POPULATION', 'LAT', 'LNG']:
            if col not in df.columns: df[col] = 0
        df = df.dropna(subset=['CITY', 'STATE_CODE'])
        df['search_label'] = df['CITY'] + ", " + df['STATE_CODE'] + " | " + df['COUNTY']
        return df, None
    except Exception as e: return None, str(e)

@st.cache_data
def get_coords(city, state):
    try:
        geolocator = Nominatim(user_agent="invest_os_v26")
        loc = geolocator.geocode(f"{city}, {state}, USA")
        if loc: return loc.latitude, loc.longitude
    except: return None, None
    return None, None

@st.cache_data
def get_wiki(city):
    try:
        wikipedia.set_lang("en")
        return wikipedia.summary(f"{city} city", sentences=2)
    except: return "No description available."

def get_fred_data(city, county, state, api_key):
    data = {"local": None, "us": 4.0, "pop": 0, "growth": None}
    try:
        r = requests.get(f"https://api.stlouisfed.org/fred/series/observations?api_key={api_key}&file_type=json&series_id=UNRATE&sort_order=desc&limit=1").json()
        data["us"] = float(r['observations'][0]['value'])
        q = f"Unemployment Rate in {county} County, {state}"
        s = requests.get(f"https://api.stlouisfed.org/fred/series/search?api_key={api_key}&file_type=json&search_text={q}&limit=5").json()
        if 'seriess' in s:
            for item in s['seriess']:
                if "Rate" in item['title']:
                    v = requests.get(f"https://api.stlouisfed.org/fred/series/observations?api_key={api_key}&file_type=json&series_id={item['id']}&sort_order=desc&limit=1").json()
                    val = float(v['observations'][0]['value'])
                    if val < 30: data["local"] = val; break
    except: pass
    return data

def calculate_score(local_rate, us_rate, active, sold, pop):
    w = st.session_state.weights
    score = 5.0
    reasons = []
    if pop == 0: pop = 100000
    inv = (active / pop) * 1000
    if inv > 12: score += 1 * w['inventory']; reasons.append("✅ High Inventory (Buyer's Market)")
    elif inv < 2: score -= 1 * w['inventory']; reasons.append("⚠️ Low Inventory (Seller's Market)")
    if active > 0:
        abs_rate = (sold / active) * 100
        if abs_rate > 50: score -= 1 * w['velocity']; reasons.append("🔥 High Velocity (Fast Sales)")
        elif abs_rate < 15: score += 1 * w['velocity']; reasons.append("❄️ Low Velocity (Slow Sales)")
    if local_rate:
        diff = local_rate - us_rate
        if diff > 0.5: score += 1 * w['economy']; reasons.append("📉 High Unemployment")
        elif diff < -0.5: score -= 1 * w['economy']; reasons.append("📈 Strong Economy")
    final = max(1.0, min(10.0, score))
    status = "Great Opportunity" if final >= 7.5 else "High Risk" if final <= 4 else "Balanced Market"
    color = "#10b981" if final >= 7.5 else "#ef4444" if final <= 4 else "#f59e0b"
    return final, status, color, reasons