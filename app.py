import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS מינימליסטי וקשוח ---
st.set_page_config(page_title="כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    /* ביטול ה-Wide של Streamlit */
    .block-container { max-width: 500px !important; padding: 10px !important; }
    .stApp { background-color: #1a1c23; color: white; direction: rtl; }
    
    /* מכולה ל-2 טורים שתמיד נשארת ברוחב 100% */
    .team-container {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        width: 100%;
    }
    .team-column {
        width: 50%;
    }
    .player-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 5px;
        font-size: 16px;
        font-weight: bold;
    }
    .stats-label {
        font-size: 12px;
        color: #22c55e;
        display: block;
    }
    .header-label {
        text-align: center;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        font-weight: bold;
    }
    .footer-balance {
        text-align: center;
        font-size: 14px;
        color: #60a5fa;
        padding: 10px;
        background: #1e293b;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ---
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

# --- 3. ממשק ---
st.markdown("<h2 style='text-align:center;'>⚽ וולפסון חולון</h2>", unsafe_allow_html=True)

all_n = sorted([p['name'] for p in st.session_state.players])
selected = st.pills("מי משחק?", all_n, selection_mode="multi")

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
    # חישוב ממוצעים
    avg1 = sum(p['f'] for p in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
    avg2 = sum(p['f'] for p in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0

    # יצירת ה-HTML של הטבלה
    def render_col(team, title, color):
        cards = "".join([f"<div class='player-card'>{p['name']}<span class='stats-label'>רמה: {p['f']:.1f} | גיל: {p['age']}</span></div>" for p in team])
        return f"""
        <div class="team-column">
            <div class="header-label" style="background:{color};">{title}</div>
            {cards}
            <div class="footer-balance">רמה: {avg1 if "לבן" in title else avg2:.1f}</div>
        </div>
        """

    # הצגה של שתי העמודות ב-HTML טהור (חסין WIDE)
    st.markdown(f"""
    <div class="team-container">
        {render_col(st.session_state.t1, "⚪ לבן", "#3b82f6")}
        {render_col(st.session_state.t2, "⚫ שחור", "#4a5568")}
    </div>
    """, unsafe_allow_html=True)

    # כפתור החלפה פשוט מתחת
    st.write("---")
    st.markdown("### 🔄 החלפה מהירה")
    col_a, col_b = st.columns(2)
    with col_a:
        m1 = st.selectbox("מהלבן:", ["--"] + [p['name'] for p in st.session_state.t1])
        if m1 != "--":
            p_obj = next(p for p in st.session_state.t1 if p['name'] == m1)
            st.session_state.t1.remove(p_obj)
            st.session_state.t2.append(p_obj)
            st.rerun()
    with col_b:
        m2 = st.selectbox("מהשחור:", ["--"] + [p['name'] for p in st.session_state.t2])
        if m2 != "--":
            p_obj = next(p for p in st.session_state.t2 if p['name'] == m2)
            st.session_state.t2.remove(p_obj)
            st.session_state.t1.append(p_obj)
            st.rerun()
