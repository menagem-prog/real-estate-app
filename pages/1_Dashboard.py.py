import streamlit as st
import sys
import pandas as pd
import os
from datetime import datetime

# ייבוא utils
sys.path.append("..") 
import utils

utils.page_setup()
utils.render_header()

API_KEY = 'c2964c1b7cc043da6fe8eb79290e2357'

st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
st.title("Market Dashboard")
st.caption("Advanced Real Estate Market Analysis")

df, msg = utils.load_data()
if df is None:
    st.error(f"Critical Error: {msg}")
    st.stop()

# --- תיקון: חיפוש בתוך מסגרת ---
# במקום ליצור DIV ידני, משתמשים בקונטיינר של סטרימליט
with st.container(border=True):
    selected = st.selectbox(
        "Select Market:",
        df['search_label'].sort_values(),
        index=None,
        placeholder="Start typing city, state or county...",
        label_visibility="collapsed"
    )

if selected:
    row = df[df['search_label'] == selected].iloc[0]
    city, state, county = row['CITY'], row['STATE_CODE'], row['COUNTY']
    file_pop = int(row['POPULATION'])

    lat, lng = row.get('LAT'), row.get('LNG')
    if pd.isna(lat) or lat == 0: lat, lng = utils.get_coords(city, state)
    
    with st.spinner("Analyzing..."):
        wiki_text = utils.get_wiki(city)
        fred = utils.get_fred_data(city, county, state, API_KEY)
    
    pop = fred['pop'] if fred['pop'] > 0 else file_pop
    if pop == 0: pop = 10000

    wiki_link = f"https://en.wikipedia.org/wiki/{city.replace(' ', '_')},_{state}"
    f_city = city.replace(" ", "-")
    link_active = f"https://www.zillow.com/homes/{f_city},-{state}_rb/"
    link_sold_city = f"https://www.zillow.com/{f_city}-{state}/sold/"

    col_info, col_map = st.columns([1.2, 1])
    with col_info:
        st.subheader(f"📍 {city}, {state}")
        st.caption(f"County: {county}")
        st.info(wiki_text)
        st.markdown(f"[📖 Read full article]({wiki_link})")
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Population", f"{pop:,}", f"{fred['growth']:.2f}%" if fred['growth'] else None)
        local_rate = fred['local']
        diff = local_rate - fred['us'] if local_rate else 0
        m2.metric("Unemployment", f"{local_rate}%" if local_rate else "N/A", f"{diff:+.1f}% vs US", delta_color="inverse")

    with col_map:
        if lat: st.map(pd.DataFrame({'lat': [lat], 'lon': [lng]}), height=350, use_container_width=True)
        else: st.warning("No coords")

    st.markdown("### 🕵️ Live Market Data")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**1. Inventory** [🔎 Zillow]({link_active})")
            active = st.number_input("Active Count", min_value=0, value=None, key="act", label_visibility="collapsed")
        with c2:
            st.markdown(f"**2. Velocity** [💰 Sold]({link_sold_city})")
            sold = st.number_input("Sold Count", min_value=0, value=None, key="sld", label_visibility="collapsed")

    if active is not None and sold is not None:
        score, status, color, reasons = utils.calculate_score(fred['local'], fred['us'], active, sold, pop)
        st.markdown(f"""
            <div style="background:white; border-left:8px solid {color}; padding:20px; border-radius:10px; margin-top:20px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div><h2 style="margin:0; color:#333;">{status}</h2><p style="margin:0; color:#666;">Investment Score</p></div>
                    <div style="font-size:3rem; font-weight:800; color:{color};">{score}/10</div>
                </div>
                <hr style="margin:15px 0; border:0; border-top:1px solid #eee;">
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                    {''.join([f'<div style="background:#f9f9f9; padding:8px; border-radius:5px; font-size:0.9rem;">{r}</div>' for r in reasons])}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("💾 Save", type="primary", use_container_width=True):
            new = {"Date": datetime.now().strftime("%Y-%m-%d"), "City": city, "Score": score, "Active": active, "Sold": sold}
            f = "search_history.csv"
            df_new = pd.DataFrame([new])
            if not os.path.exists(f): df_new.to_csv(f, index=False)
            else: df_new.to_csv(f, mode='a', header=False, index=False)
            st.toast("Saved!", icon="✅")