import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. נעילת רוחב מוחלטת ב-CSS ---
st.set_page_config(page_title="כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    /* ביטול כל גלישה רוחבית */
    html, body, [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
        position: fixed;
        width: 100%;
        height: 100%;
    }
    
    .block-container { 
        max-width: 100% !important; 
        padding: 5px !important; 
    }

    /* כפיית 2 טורים שאינם זזים */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 4px !important;
        width: 100% !important;
    }
    
    [data-testid="column"] {
        width: 50% !important;
        flex: 1 !important;
        min-width: 0 !important;
    }

    /* כרטיס שחקן שכולל בתוכו את הכל */
    .player-row {
        position: relative;
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 6px;
        margin-bottom: 5px;
        height: 60px;
        display: flex;
        align-items: center;
        padding-right: 10px;
    }

    .p-text {
        display: flex;
        flex-direction: column;
        width: 70%;
        overflow: hidden;
    }

    .p-name { 
        font-size: 16px !important; 
        font-weight: bold; 
        color: white; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
    }

    .p-stats { font-size: 12px !important; color: #22c55e; }

    /* עיצוב כפתור ההחלפה - שיושב בצד שמאל של הכרטיס */
    .stButton button {
        background-color: #4a5568 !important;
        border: none !important;
        color: white !important;
        height: 40px !important;
        width: 40px !important;
        min-width: 40px !important;
        padding: 0 !important;
        font-size: 18px !important;
        border-radius: 4px !important;
    }
    
    .team-h { text-align: center; font-weight: bold; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; }
    .team-f { background: #1e293b; text-align: center; padding: 6px; border-radius: 0 0 6px 6px; font-size: 12px; color: #60a5fa; }
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
st.markdown("<h3 style='text-align:center;'>⚽ וולפסון חולון</h3>", unsafe_allow_html=True)

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
    c_left, c_right = st.columns(2)
    
    teams = [
        {"col": c_left, "team": st.session_state.t1, "label": "⚪ לבן", "color": "#3b82f6", "id": "t1"},
        {"col": c_right, "team": st.session_state.t2, "label": "⚫ שחור", "color": "#4a5568", "id": "t2"}
    ]

    for conf in teams:
        with conf["col"]:
            st.markdown(f"<div class='team-h' style='background:{conf['color']};'>{conf['label']}</div>", unsafe_allow_html=True)
            for i, p in enumerate(conf["team"]):
                # כאן הסוד: שימוש בעמודות עם מרווח מינימלי
                row_col1, row_col2 = st.columns([0.7, 0.3])
                with row_col1:
                    st.markdown(f"""
                        <div class="player-row">
                            <div class="p-text">
                                <span class="p-name">{p['name']}</span>
                                <span class="p-stats">{p['f']:.1f} | {p['age']}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with row_col2:
                    # הכפתור מוצמד ידנית דרך CSS כדי שלא יברח
                    if st.button("🔄", key=f"b_{conf['id']}_{i}"):
                        if conf['id'] == "t1":
                            st.session_state.t2.append(st.session_state.t1.pop(i))
                        else:
                            st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()
            
            if conf["team"]:
                avg = sum(x['f'] for x in conf["team"])/len(conf["team"])
                st.markdown(f"<div class='team-f'>רמה: {avg:.1f}</div>", unsafe_allow_html=True)

    for _ in range(5): st.write("")
