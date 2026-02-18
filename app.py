import streamlit as st
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# הגדרות בסיסיות
st.set_page_config(page_title="כדורגל 2026", layout="centered")

# לוגיקה וחיבור לנתונים
conn = st.connection("gsheets", type=GSheetsConnection)
if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 30
    return float(p.get('rating', 5.0)), 2026 - int(p.get('birth_year', 1996))

st.markdown("<h2 style='text-align:center; direction:rtl;'>⚽ וולפסון חולון</h2>", unsafe_allow_html=True)

all_n = sorted([p['name'] for p in st.session_state.players])
selected = st.pills("מי משחק היום?", all_n, selection_mode="multi")

if st.button("חלק קבוצות 🚀", use_container_width=True):
    if selected:
        pool = [{'name': n, 'f': get_stats(n)[0], 'age': get_stats(n)[1]} for n in selected]
        pool.sort(key=lambda x: x['f'], reverse=True)
        t1, t2 = [], []
        for i, p in enumerate(pool):
            if i % 4 == 0 or i % 4 == 3: t1.append(p)
            else: t2.append(p)
        st.session_state.t1, st.session_state.t2 = t1, t2

if 't1' in st.session_state and selected:
    t1, t2 = st.session_state.t1, st.session_state.t2
    avg1 = sum(p['f'] for p in t1)/len(t1) if t1 else 0
    avg2 = sum(p['f'] for p in t2)/len(t2) if t2 else 0

    # בניית ה-HTML בתוך משתנה אחד כדי למנוע שגיאות רינדור
    def gen_team_html(team, title, color, avg):
        cards = "".join([f"""
            <div style="background:#2d3748; border:1px solid #4a5568; border-radius:8px; padding:12px; margin-bottom:8px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                <div style="font-size:18px; font-weight:bold; color:white;">{p['name']}</div>
                <div style="font-size:13px; color:#22c55e;">רמה: {p['f']:.1f} | גיל: {p['age']}</div>
            </div>
        """ for p in team])
        
        return f"""
        <div style="flex:1; min-width:0; display:flex; flex-direction:column;">
            <div style="background:{color}; color:white; text-align:center; padding:12px; border-radius:8px; font-weight:bold; margin-bottom:10px; font-size:20px;">{title}</div>
            {cards}
            <div style="background:#1e293b; color:#60a5fa; text-align:center; padding:10px; border-radius:8px; font-size:14px; margin-top:5px; border:1px solid #334155;">ממוצע: {avg:.1f}</div>
        </div>
        """

    # הזרקת ה-HTML בתוך Component עצמאי (Iframe) למניעת קריסה בסלולר
    full_html = f"""
    <div dir="rtl" style="display:flex; gap:12px; width:100%; font-family:system-ui, -apple-system, sans-serif;">
        {gen_team_html(t1, "⚪ לבן", "#3b82f6", avg1)}
        {gen_team_html(t2, "⚫ שחור", "#4a5568", avg2)}
    </div>
    """
    components.html(full_html, height=600, scrolling=True)

    # מנגנון החלפה מהיר
    st.write("---")
    st.markdown("<h3 style='text-align:right; direction:rtl;'>🔄 החלפת שחקנים</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        m1 = st.selectbox("העבר מהלבן לשחור:", ["--"] + [p['name'] for p in t1], key="sw1")
        if m1 != "--":
            p_obj = next(p for p in st.session_state.t1 if p['name'] == m1)
            st.session_state.t1.remove(p_obj)
            st.session_state.t2.append(p_obj)
            st.rerun()
    with c2:
        m2 = st.selectbox("העבר מהשחור ללבן:", ["--"] + [p['name'] for p in t2], key="sw2")
        if m2 != "--":
            p_obj = next(p for p in st.session_state.t2 if p['name'] == m2)
            st.session_state.t2.remove(p_obj)
            st.session_state.t1.append(p_obj)
            st.rerun()
