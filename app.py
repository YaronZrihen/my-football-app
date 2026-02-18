import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS "קשוח" - מונע WIDE ומכריח 2 עמודות ---
st.set_page_config(page_title="כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    /* הגבלת רוחב האפליקציה כולה כדי שלא תימרח */
    .block-container { 
        max-width: 450px !important; 
        padding: 5px !important; 
    }
    
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }

    /* יצירת טבלה חסינת סלולר */
    .game-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed; /* מכריח רוחב עמודות קבוע */
    }

    .team-cell {
        vertical-align: top;
        width: 50%;
        padding: 2px;
    }

    .team-header {
        text-align: center;
        font-weight: bold;
        padding: 10px;
        border-radius: 8px 8px 0 0;
        font-size: 18px;
        color: white;
    }

    .player-row-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 5px;
        margin-bottom: 4px;
        padding: 8px 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 50px;
    }

    .p-name { 
        font-size: 15px; 
        font-weight: bold; 
        color: white; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis;
        flex-grow: 1;
    }

    .p-score-label { 
        font-size: 12px; 
        color: #22c55e; 
        margin-right: 5px;
    }

    /* כפתור החלפה שקוף ונקי */
    .stButton button {
        background-color: transparent !important;
        border: 1px solid #4a5568 !important;
        color: #cbd5e0 !important;
        height: 35px !important;
        width: 35px !important;
        min-width: 35px !important;
        font-size: 16px !important;
        padding: 0 !important;
    }

    .team-footer {
        background: #1e293b;
        text-align: center;
        padding: 8px;
        font-size: 14px;
        color: #60a5fa;
        border-radius: 0 0 8px 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור נתונים ולוגיקה ---
conn = st.connection("gsheets", type=GSheetsConnection)
if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 30
    r = float(p.get('rating', 5.0))
    pr = json.loads(p.get('peer_ratings', '{}')) if isinstance(p.get('peer_ratings'), str) else {}
    peers = [float(v) for v in pr.values()] if pr else []
    score = (r + sum(peers)/len(peers))/2 if peers else r
    return score, 2026 - int(p.get('birth_year', 1996))

# --- 3. ממשק משתמש ---
st.markdown("<h3 style='text-align:center; color:#60a5fa;'>⚽ וולפסון חולון</h3>", unsafe_allow_html=True)

all_n = sorted([p['name'] for p in st.session_state.players])
selected = st.pills("מי משחק?", all_n, selection_mode="multi")

if st.button("חלק קבוצות 🚀", use_container_width=True):
    if selected:
        pool = []
        for n in selected:
            s, a = get_stats(n)
            pool.append({'name': n, 'f': s, 'age': a})
        pool.sort(key=lambda x: x['f'], reverse=True)
        t1, t2 = [], []
        for i, p in enumerate(pool):
            if i % 4 == 0 or i % 4 == 3: t1.append(p)
            else: t2.append(p)
        st.session_state.t1, st.session_state.t2 = t1, t2

if 't1' in st.session_state and selected:
    # יצירת מבנה הטבלה
    t1, t2 = st.session_state.t1, st.session_state.t2
    
    # חישוב ממוצעים
    avg1 = sum(p['f'] for p in t1)/len(t1) if t1 else 0
    avg2 = sum(p['f'] for p in t2)/len(t2) if t2 else 0

    # עמודה 1 (לבן) ועמודה 2 (שחור) בתוך טבלה אחת
    col_w, col_b = st.columns(2)
    
    with col_w:
        st.markdown('<div class="team-header" style="background:#3b82f6;">⚪ לבן</div>', unsafe_allow_html=True)
        for i, p in enumerate(t1):
            c_inner_txt, c_inner_btn = st.columns([0.7, 0.3])
            with c_inner_txt:
                st.markdown(f"""<div class="player-row-box">
                    <div class="p-name">{p['name']}</div>
                    <div class="p-score-label">{p['f']:.1f}</div>
                </div>""", unsafe_allow_html=True)
            with c_inner_btn:
                if st.button("🔄", key=f"w_{i}"):
                    st.session_state.t2.append(st.session_state.t1.pop(i))
                    st.rerun()
        st.markdown(f'<div class="team-footer">רמה: {avg1:.1f}</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="team-header" style="background:#4a5568;">⚫ שחור</div>', unsafe_allow_html=True)
        for i, p in enumerate(t2):
            c_inner_txt, c_inner_btn = st.columns([0.7, 0.3])
            with c_inner_txt:
                st.markdown(f"""<div class="player-row-box">
                    <div class="p-name">{p['name']}</div>
                    <div class="p-score-label">{p['f']:.1f}</div>
                </div>""", unsafe_allow_html=True)
            with c_inner_btn:
                if st.button("🔄", key=f"b_{i}"):
                    st.session_state.t1.append(st.session_state.t2.pop(i))
                    st.rerun()
        st.markdown(f'<div class="team-footer">רמה: {avg2:.1f}</div>', unsafe_allow_html=True)
