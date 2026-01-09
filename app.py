import streamlit as st
import utils
import os

# הפעלת עיצוב וכותרת
utils.page_setup()
utils.render_header()

# תוכן דף הבית
st.markdown("""
    <div style="text-align: center; padding: 50px 20px;">
        <h1 style="font-size: 3rem; color: #1a73e8; margin-bottom: 10px;">ברוכים הבאים למערכת הנדל"ן</h1>
        <p style="font-size: 1.2rem; color: #5f6368; margin-bottom: 40px;">
            פלטפורמה מתקדמת לניתוח שווקים, איתור הזדמנויות וניהול עסקאות בארה"ב.
        </p>
    </div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

# === המוח לתיקון השגיאה ===
# הקוד בודק איזה קובץ קיים באמת בתיקייה שלך
dashboard_path = None
if os.path.exists("pages/Dashboard.py"):
    dashboard_path = "pages/Dashboard.py"
elif os.path.exists("pages/1_Dashboard.py"):
    dashboard_path = "pages/1_Dashboard.py"
elif os.path.exists("pages/1_🗺️_Dashboard.py"):
    dashboard_path = "pages/1_🗺️_Dashboard.py"

with c1:
    with st.container(border=True):
        st.markdown("### 🗺️ איתור אזורים")
        st.write("ניתוח דמוגרפי וכלכלי למציאת השוק הבא.")
        
        # אם מצאנו את הקובץ - נציג כפתור. אם לא - נציג הודעה ברורה במקום לקרוס
        if dashboard_path:
            st.page_link(dashboard_path, label="עבור לדשבורד", icon="➡️")
        else:
            st.warning("⚠️ לא נמצא קובץ הדשבורד בתיקיית pages")

with c2:
    with st.container(border=True):
        st.markdown("### 📊 ניתוח עסקה")
        st.write("מחשבונים, תשואות ובדיקת כדאיות.")
        st.info("בקרוב")

with c3:
    with st.container(border=True):
        st.markdown("### 🏠 ניהול נכסים")
        st.write("מעקב אחרי פורטפוליו קיים.")
        st.info("בקרוב")