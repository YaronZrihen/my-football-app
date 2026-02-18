import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# הגדרות בסיס
st.set_page_config(page_title="כדורגל וולפסון", layout="centered")

# לוגיקה של נתונים
conn = st.connection("gsheets", type=GSheetsConnection)
if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

def get_p_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 30
    return float(p.get('rating', 5.0)), 2026 - int(p.get('birth_year', 1996))

st.markdown("<h2 style='text-align:center;'>⚽ שישי וולפסון חולון</h2>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🏃 חלוקה", "⚙️ ניהול"])

with tab1:
    all_n = sorted([p['name'] for p in st.session_state.players])
    selected = st.pills("מי הגיע?", all_n, selection_mode="multi")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            for n in selected:
                s, a = get_p_stats(n)
                pool.append({'name': n, 'f': s, 'age': a})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        # בחינת נתונים עבור ה-HTML
        t1, t2 = st.session_state.t1, st.session_state.t2
        avg1 = sum(p['f'] for p in t1)/len(t1) if t1 else 0
        avg2 = sum(p['f'] for p in t2)/len(t2) if t2 else 0

        # יצירת ה-HTML בתוך רכיב עצמאי (Iframe) למניעת קריסה בסלולר
        def list_p(team):
            return "".join([f"<div style='background:#1e293b; margin:4px; padding:8px; border-radius:4px; border-right:4px solid #3b82f6;'><div style='font-size:16px; font-weight:bold; color:white;'>{p['name']}</div><div style='font-size:12px; color:#22c55e;'>רמה: {p['f']:.1f} | גיל: {p['age']}</div></div>" for p in team])

        html_content = f"""
        <div dir="rtl" style="display:flex; flex-direction:row; gap:10px; font-family:sans-serif;">
            <div style="flex:1; background:#2d3748; border-radius:8px; overflow:hidden; border:1px solid #4a5568;">
                <div style="background:#3b82f6; color:white; text-align:center; padding:10px; font-weight:bold;">⚪ לבן</div>
                {list_p(t1)}
                <div style="background:#0f172a; color:#60a5fa; text-align:center; padding:10px; font-size:14px; border-top:1px solid #4a5568;">רמה: {avg1:.1f}</div>
            </div>
            <div style="flex:1; background:#2d3748; border-radius:8px; overflow:hidden; border:1px solid #4a5568;">
                <div style="background:#4a5568; color:white; text-align:center; padding:10px; font-weight:bold;">⚫ שחור</div>
                {list_p(t2)}
                <div style="background:#0f172a; color:#60a5fa; text-align:center; padding:10px; font-size:14px; border-top:1px solid #4a5568;">רמה: {avg2:.1f}</div>
            </div>
        </div>
        """
        st.components.v1.html(html_content, height=500, scrolling=True)

        # כפתורי החלפה - הפתרון הכי יציב לסלולר
        st.markdown("---")
        st.subheader("🔄 החלפת שחקן")
        c1, c2 = st.columns(2)
        with c1:
            m1 = st.selectbox("העבר מהלבן:", ["--"] + [p['name'] for p in t1])
            if m1 != "--":
                p_obj = next(p for p in t1 if p['name'] == m1)
                st.session_state.t1.remove(p_obj)
                st.session_state.t2.append(p_obj)
                st.rerun()
        with c2:
            m2 = st.selectbox("העבר מהשחור:", ["--"] + [p['name'] for p in t2])
            if m2 != "--":
                p_obj = next(p for p in t2 if p['name'] == m2)
                st.session_state.t2.remove(p_obj)
                st.session_state.t1.append(p_obj)
                st.rerun()

with tab2:
    st.write("ניהול מאגר שחקנים (בפיתוח)")
