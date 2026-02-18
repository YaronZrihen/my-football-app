import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. הגדרות תצוגה ו-CSS חסין סלולר ---
st.set_page_config(page_title="כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    /* הגבלת רוחב הכלים כדי למנוע WIDE */
    .block-container { max-width: 500px !important; padding: 10px !important; }
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }

    /* כפיית שתי עמודות בסלולר - דריסה של Streamlit */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 8px !important;
    }
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 0 !important; /* מונע מהעמודה להתרחב ולשבור שורה */
    }

    /* עיצוב כרטיס שחקן */
    .player-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 6px;
        padding: 8px;
        height: 55px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin-bottom: 4px;
    }
    .p-name { font-size: 16px !important; font-weight: bold; color: white; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-stats { font-size: 12px !important; color: #22c55e; }

    /* עיצוב כפתור החלפה */
    .stButton button {
        height: 55px !important;
        width: 100% !important;
        background-color: #334155 !important;
        border: none !important;
        font-size: 20px !important;
        color: white !important;
        padding: 0 !important;
    }
    
    .team-h { text-align: center; font-weight: bold; padding: 10px; border-radius: 8px 8px 0 0; font-size: 18px; }
    .team-f { background: #1e293b; text-align: center; padding: 8px; border-radius: 0 0 8px 8px; font-size: 13px; color: #60a5fa; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור נתונים ---
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
    return r, 2026 - int(p.get('birth_year', 1996))

# --- 3. ממשק משתמש ---
st.markdown("<h2 style='text-align:center; color:#60a5fa;'>⚽ וולפסון חולון</h2>", unsafe_allow_html=True)

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
    
    configs = [
        {"col": c_left, "team": st.session_state.t1, "label": "⚪ לבן", "color": "#3b82f6", "id": "t1"},
        {"col": c_right, "team": st.session_state.t2, "label": "⚫ שחור", "color": "#4a5568", "id": "t2"}
    ]

    for conf in configs:
        with conf["col"]:
            st.markdown(f"<div class='team-h' style='background:{conf['color']};'>{conf['label']}</div>", unsafe_allow_html=True)
            for i, p in enumerate(conf["team"]):
                # שילוב של טקסט וכפתור באותה שורה בתוך העמודה
                c1, c2 = st.columns([0.7, 0.3])
                with c1:
                    st.markdown(f"""<div class='player-box'>
                        <div class='p-name'>{p['name']}</div>
                        <div class='p-stats'>{p['f']:.1f} | {p['age']}</div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    if st.button("🔄", key=f"btn_{conf['id']}_{i}"):
                        if conf['id'] == "t1":
                            st.session_state.t2.append(st.session_state.t1.pop(i))
                        else:
                            st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()
            
            if conf["team"]:
                avg = sum(x['f'] for x in conf["team"])/len(conf["team"])
                st.markdown(f"<div class='team-f'>ממוצע: {avg:.1f}</div>", unsafe_allow_html=True)
