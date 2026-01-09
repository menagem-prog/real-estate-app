import streamlit as st
import pandas as pd
import requests
import os
import ssl
import wikipedia
from datetime import datetime
from geopy.geocoders import Nominatim

# ==========================================
# 🎨 הגדרות עיצוב ופונטים (Google Style)
# ==========================================
st.set_page_config(
    page_title="InvestMap Pro System", 
    page_icon="🏙️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# אתחול משקלים בזיכרון
if 'weights' not in st.session_state:
    st.session_state.weights = {
        'inventory': 2.0,
        'velocity': 1.5,
        'economy': 1.0,
        'demography': 1.0
    }

st.markdown("""
    <style>
    /* ייבוא פונט Assistant של גוגל - נקי, מודרני, קריא */
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Assistant', sans-serif;
        direction: rtl;
    }
    
    /* הסתרת אלמנטים מיותרים */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* --- HERO SECTION --- */
    .hero-container {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        padding: 40px 20px;
        text-align: center;
        border-radius: 0 0 20px 20px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -1px;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        font-weight: 300;
    }

    /* --- חיפוש (מעוצב עם צל) --- */
    .search-wrapper {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        margin-top: -30px; /* עולה על ההירו */
        position: relative;
        z-index: 10;
        width: 80%;
        margin-left: auto;
        margin-right: auto;
    }

    /* --- כרטיסיות מידע --- */
    .metric-card {
        background: white;
        border: 1px solid #f1f5f9;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
    }

    /* --- אזור הזנה (Input) --- */
    .input-section {
        background-color: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 12px;
        padding: 20px;
        margin-top: 20px;
    }

    /* --- כרטיס סיכום (Verdict) --- */
    .verdict-card {
        background: linear-gradient(to left, #ffffff, #f0f9ff);
        border-right: 5px solid #0ea5e9;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-top: 30px;
    }
    
    /* --- כפתורים קטנים --- */
    .small-btn {
        text-decoration: none;
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        transition: 0.2s;
    }
    .small-btn:hover {
        background-color: #0369a1;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

FRED_API_KEY = 'c2964c1b7cc043da6fe8eb79290e2357'

# עקיפת SSL
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# ==========================================
# 🧠 מנוע נתונים (משודרג ויציב)
# ==========================================

@st.cache_data
def get_wiki_data(city, state):
    try:
        wikipedia.set_lang("en")
        search_query = f"{city}, {state}"
        # חיפוש מדויק יותר
        results = wikipedia.search(search_query)
        if not results:
            return "לא נמצא מידע בויקיפדיה.", None
            
        page = wikipedia.page(results[0], auto_suggest=False)
        summary = page.summary.split('.')[0] + '.' + page.summary.split('.')[1] + '.' 
        
        image_url = None
        if page.images:
            for img in page.images:
                if img.endswith('.jpg') or img.endswith('.png'):
                    if "logo" not in img.lower() and "flag" not in img.lower() and "map" not in img.lower():
                        image_url = img
                        break
        return summary, image_url
    except:
        return "תיאור לא זמין זמנית.", None

@st.cache_data
def get_coordinates(city, state):
    try:
        geolocator = Nominatim(user_agent="invest_map_v21")
        location = geolocator.geocode(f"{city}, {state}, USA")
        if location: return location.latitude, location.longitude
    except: return None, None
    return None, None

@st.cache_data
def load_data_local():
    file_path = "us_cities.csv"
    if not os.path.exists(file_path): return None, "קובץ us_cities.csv חסר"
    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip().str.upper()
        df.rename(columns={'STATE_ID': 'STATE_CODE', 'STATE_NAME': 'STATE', 'CITY_ASCII': 'CITY'}, inplace=True)
        for col in ['POPULATION', 'LAT', 'LNG']:
            if col not in df.columns: df[col] = 0
        df = df.dropna(subset=['CITY', 'STATE_CODE'])
        df['search_label'] = df['CITY'] + ", " + df['STATE_CODE'] + " | " + df['COUNTY']
        return df, "Success"
    except Exception as e: return None, str(e)

def get_fred_data(city, county, state, api_key):
    data = {"us_rate": 4.0, "local_rate": None, "pop": 0, "growth": None}
    
    try:
        # אבטלה ארה"ב
        r = requests.get(f"https://api.stlouisfed.org/fred/series/observations?api_key={api_key}&file_type=json&series_id=UNRATE&sort_order=desc&limit=1").json()
        data["us_rate"] = float(r['observations'][0]['value'])

        # אבטלה מקומית
        q = f"Unemployment Rate in {county} County, {state}"
        s_res = requests.get(f"https://api.stlouisfed.org/fred/series/search?api_key={api_key}&file_type=json&search_text={q}&limit=5").json()
        if 'seriess' in s_res:
            for s in s_res['seriess']:
                if "Rate" in s['title']:
                    v_res = requests.get(f"https://api.stlouisfed.org/fred/series/observations?api_key={api_key}&file_type=json&series_id={s['id']}&sort_order=desc&limit=1").json()
                    val = float(v_res['observations'][0]['value'])
                    if val < 30: 
                        data["local_rate"] = val
                        break

        # אוכלוסיה
        pop_q = f"Resident Population in {county} County, {state}"
        p_res = requests.get(f"https://api.stlouisfed.org/fred/series/search?api_key={api_key}&file_type=json&search_text={pop_q}&limit=1").json()
        if 'seriess' in p_res and p_res['seriess']:
            pid = p_res['seriess'][0]['id']
            hist = requests.get(f"https://api.stlouisfed.org/fred/series/observations?api_key={api_key}&file_type=json&series_id={pid}&sort_order=desc&limit=24").json()
            obs = hist['observations']
            if obs:
                data["pop"] = int(float(obs[0]['value']) * 1000)
                if len(obs) >= 12:
                    curr = float(obs[0]['value'])
                    prev = float(obs[-1]['value'])
                    data["growth"] = ((curr - prev) / prev) * 100
    except: pass
    return data

def calculate_score_dynamic(local_unemp, us_unemp, active, sold_city, pop, growth):
    w_inv = st.session_state.weights['inventory']
    w_vel = st.session_state.weights['velocity']
    w_eco = st.session_state.weights['economy']
    w_dem = st.session_state.weights['demography']
    
    score = 5.0
    reasons = []
    
    if pop == 0: pop = 100000

    # 1. מלאי
    inv_rate = (active / pop) * 1000
    if inv_rate > 12: 
        score += 1 * w_inv
        reasons.append(f"✅ שוק מוצף (כוח לקונה) - היצע: {inv_rate:.1f}")
    elif inv_rate < 2: 
        score -= 1 * w_inv
        reasons.append(f"⚠️ מחסור בהיצע (שוק מוכרים) - היצע: {inv_rate:.1f}")

    # 2. ספיגה
    if active > 0:
        abs_rate = (sold_city / active) * 100
        if abs_rate > 50: 
            score -= 1 * w_vel
            reasons.append(f"🔥 נכסים נחטפים ({abs_rate:.0f}% ספיגה)")
        elif abs_rate < 15: 
            score += 1 * w_vel
            reasons.append(f"❄️ שוק איטי ({abs_rate:.0f}% ספיגה)")

    # 3. כלכלה
    if local_unemp:
        gap = local_unemp - us_unemp
        if gap > 0.5: 
            score += 1 * w_eco
            reasons.append(f"📉 אבטלה גבוהה (לחץ מחירים למטה)")
        elif gap < -0.5: 
            score -= 1 * w_eco
            reasons.append(f"📈 כלכלה חזקה (מחירים יציבים/עולים)")

    # 4. דמוגרפיה
    if growth:
        if growth > 1.0: 
            score -= 0.5 * w_dem
            reasons.append(f"🏗️ אזור בצמיחה ({growth:.2f}%)")
        elif growth < 0: 
            score += 0.5 * w_dem
            reasons.append(f"🏚️ הגירה שלילית")

    final_score = max(1.0, min(10.0, score))
    
    if final_score >= 7.5: status, color = "הזדמנות חזקה", "#10b981"
    elif final_score <= 4.0: status, color = "סיכון / שוק יקר", "#ef4444"
    else: status, color = "שוק מאוזן", "#f59e0b"
    
    return final_score, status, color, reasons

# ==========================================
# 🖥️ ממשק משתמש
# ==========================================

# Hero Section
st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">מערכת למיפוי אזורים להשקעה</h1>
        <div class="hero-subtitle">ניתוח שוק נדל"ן מבוסס נתונים ובינה עסקית</div>
    </div>
""", unsafe_allow_html=True)

# Tabs
tab_main, tab_settings, tab_history = st.tabs(["🏠 לוח בקרה", "⚙️ הגדרות אלגוריתם", "📂 טבלת השוואות"])

df, msg = load_data_local()

# --- טאב 1: לוח בקרה ---
with tab_main:
    if df is None:
        st.error(msg)
    else:
        # אזור חיפוש
        st.markdown('<div class="search-wrapper">', unsafe_allow_html=True)
        selected = st.selectbox(
            "בחר אזור",
            df['search_label'].sort_values(),
            index=None,
            placeholder="הקלד שם עיר, מדינה או מחוז...",
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if selected:
            row = df[df['search_label'] == selected].iloc[0]
            city, state, county = row['CITY'], row['STATE_CODE'], row['COUNTY']
            file_pop = int(row['POPULATION'])
            
            # חישובים ברקע
            lat, lng = row.get('LAT'), row.get('LNG')
            if pd.isna(lat) or lat == 0: lat, lng = get_coordinates(city, state)
            
            with st.spinner('מנתח את השוק...'):
                wiki_text, wiki_img = get_wiki_data(city, state)
                fred = get_fred_data(city, county, state, FRED_API_KEY)
            
            # טיפול באוכלוסיה 0 (Fallback)
            pop = fred['pop'] if fred['pop'] > 0 else file_pop
            
            # לינקים
            f_city = city.replace(" ", "-")
            f_county = county.replace(" ", "-")
            link_active = f"https://www.zillow.com/homes/{f_city},-{state}_rb/"
            link_sold_city = f"https://www.zillow.com/{f_city}-{state}/sold/"
            link_sold_county = f"https://www.zillow.com/{f_county}-county-{state}/sold/"

            st.write("")
            
            # --- גריד מידע ---
            col_info, col_visual = st.columns([1, 1])
            
            with col_info:
                st.subheader(f"📍 {city}, {state}")
                st.caption(f"County: {county}")
                
                # תיאור עם סקרולר אם הוא ארוך
                with st.container(height=100):
                    st.write(wiki_text)
                
                st.write("")
                
                # מטריקות
                m1, m2 = st.columns(2)
                m1.metric("אוכלוסיה", f"{pop:,}", f"{fred['growth']:.2f}%" if fred['growth'] else None,
                          help="סה\"כ תושבים. האחוז מציין גידול/קיטון שנתי.")
                
                local_rate = fred['local_rate']
                diff = local_rate - fred['us_rate'] if local_rate else 0
                m2.metric("אבטלה מקומית", f"{local_rate}%" if local_rate else "N/A", f"{diff:+.1f}% vs US", delta_color="inverse",
                          help="אחוז המובטלים. נתון גבוה מהממוצע הארצי עשוי להעיד על שוק חלש אך זול.")

            with col_visual:
                if wiki_img:
                    st.image(wiki_img, use_container_width=True, caption="Wikipedia Source")
                elif lat:
                    st.map(pd.DataFrame({'lat': [lat], 'lon': [lng]}), height=250, zoom=10, use_container_width=True)
                else:
                    st.info("לא נמצאה תמונה או מפה")

            # --- אזור הזנה (Input) ---
            st.markdown('<div class="input-section">', unsafe_allow_html=True)
            st.subheader("🕵️ מחקר שוק בזמן אמת")
            st.caption("יש להיכנס לקישורים, לבדוק את המספרים ב-Zillow ולהזין אותם כאן.")
            
            ic1, ic2, ic3 = st.columns(3)
            with ic1:
                st.markdown(f'<a href="{link_active}" target="_blank" class="small-btn">Active Listings ↗</a>', unsafe_allow_html=True)
                active = st.number_input("כמות Active", min_value=0, value=None, label_visibility="collapsed", key="act", placeholder="הזן מספר...")
            
            with ic2:
                st.markdown(f'<a href="{link_sold_city}" target="_blank" class="small-btn">Sold (City) ↗</a>', unsafe_allow_html=True)
                sold_city = st.number_input("כמות Sold", min_value=0, value=None, label_visibility="collapsed", key="sol", placeholder="הזן מספר...")

            with ic3:
                st.markdown(f'<a href="{link_sold_county}" target="_blank" class="small-btn">Sold (County) ↗</a>', unsafe_allow_html=True)
                sold_county = st.number_input("כמות Sold County", min_value=0, value=None, label_visibility="collapsed", key="cou", placeholder="הזן מספר...")
            
            st.markdown('</div>', unsafe_allow_html=True)

            # --- חישוב תוצאה ---
            if active is not None and sold_city is not None:
                score_val, status_txt, color_hex, reasons = calculate_score_dynamic(
                    local_rate, fred['us_rate'], active, sold_city, pop, fred['growth']
                )
                
                # כרטיס סיכום (Verdict Card)
                st.markdown(f"""
                <div class="verdict-card" style="border-right-color: {color_hex};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h2 style="margin:0; color: #1e293b;">{status_txt}</h2>
                            <p style="margin:0; color: #64748b;">ציון משוקלל המבוסס על האלגוריתם המוגדר</p>
                        </div>
                        <div style="font-size: 3.5rem; font-weight: 800; color: {color_hex};">{score_val}/10</div>
                    </div>
                    <hr style="margin: 15px 0; border-top: 1px solid #e2e8f0;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        {''.join([f'<div style="background:#f8fafc; padding:8px; border-radius:5px; border:1px solid #e2e8f0;">{r}</div>' for r in reasons])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.write("")
                # כפתור שמירה
                if st.button("💾 שמור תוצאות לטבלה", type="primary", use_container_width=True):
                    new_row = {
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "City": city, "State": state, "Score": score_val, "Status": status_txt,
                        "Population": pop, "Unemployment": local_rate,
                        "Active": active, "Sold": sold_city
                    }
                    f = "search_history.csv"
                    df_s = pd.DataFrame([new_row])
                    if not os.path.exists(f): df_s.to_csv(f, index=False, encoding='utf-8-sig')
                    else: df_s.to_csv(f, mode='a', header=False, index=False, encoding='utf-8-sig')
                    st.toast("נשמר בהצלחה!", icon="✅")

# --- טאב 2: הגדרות ---
with tab_settings:
    st.header("⚙️ הגדרות אלגוריתם")
    st.info("כאן ניתן לשנות את הרגישות של המערכת לכל פרמטר.")
    
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.session_state.weights['inventory'] = st.slider("משקל מלאי (Inventory)", 0.5, 3.0, st.session_state.weights['inventory'], 0.1)
        st.session_state.weights['velocity'] = st.slider("משקל קצב מכירה (Velocity)", 0.5, 3.0, st.session_state.weights['velocity'], 0.1)
    with col_w2:
        st.session_state.weights['economy'] = st.slider("משקל כלכלה (Economy)", 0.5, 3.0, st.session_state.weights['economy'], 0.1)
        st.session_state.weights['demography'] = st.slider("משקל דמוגרפיה (Growth)", 0.5, 3.0, st.session_state.weights['demography'], 0.1)

# --- טאב 3: היסטוריה ---
with tab_history:
    st.header("📂 ארכיון ניתוחים")
    if os.path.exists("search_history.csv"):
        df_hist = pd.read_csv("search_history.csv")
        st.dataframe(df_hist, use_container_width=True)
        if st.button("🗑️ נקה היסטוריה"):
            os.remove("search_history.csv")
            st.rerun()
    else:
        st.info("טרם בוצעו שמירות.")