import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS "נועל מסך" ---
st.set_page_config(page_title="כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    /* ביטול גלישה לצדדים ונעילת רוחב */
    html, body, [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
        width: 100vw;
    }
    
    .block-container { 
        max-width: 100% !important; 
        padding-left: 5px !important; 
        padding-right: 5px !important; 
    }

    /* כפיית 2 עמודות צמודות - ללא גלישה */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        gap: 4px !important;
    }
    
    [data-testid="column"] {
        width: calc(50% - 2px) !important; /* בדיוק חצי מסך */
        flex: none !important;
        min-width: 0 !important;
    }

    /* כרטיס שחקן צר וגבוה */
    .p-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 5px;
        height: 60px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        overflow: hidden; /* מונע מהטקסט להרחיב את הכרטיס */
    }

    .p-name { 
        font-size: 14px !important; 
        font-weight: bold; 
        color: white; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; /* חיתוך שם ארוך עם ... */
    }

    .p-stats { font-size: 11px !important; color: #22c55e; }

    /* כפתור החלפה קטן וקבוע */
    [data-testid="column"] button {
        height: 60px !important;
        min-width: 35px !important;
        width: 100% !important;
        background-color: #334155 !important;
        border: none !important;
        padding: 0 !important;
        font-size: 18px !important;
    }

    .team-h { text-align: center; font-weight: bold; padding: 8px; border-radius: 4px 4px 0 0; font-size: 15px; }
    .team-f { background: #1e293b; text-align: center; padding: 5px; border-radius: 0 0 4px 4px; font-size: 11px; color: #60a5fa; }
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
    # עמודות ראשיות (לבן מול שחור)
    c_left, c_right = st.columns(2)
    
    teams = [
        {"col": c_left, "team": st.session_state.t1, "label": "⚪ לבן", "color": "#3b82f6", "id": "t1"},
        {"col": c_right, "team": st.session_state.t2, "label": "⚫ שחור", "color": "#4a5568", "id": "t2"}
    ]

    for conf in teams:
        with conf["col"]:
            st.markdown(f"<div class='team-h' style='background:{conf['color']};'>{conf['label']}</div>", unsafe_allow_html=True)
            for i, p in enumerate(conf["team"]):
                # עמודות פנימיות בתוך כל קבוצה (שם מול כפתור)
                ci1, ci2 = st.columns([0.7, 0.3])
                with ci1:
                    st.markdown(f"""<div class='p-card'>
                        <div class='p-name'>{p['name']}</div>
                        <div class='p-stats'>{p['f']:.1f} | {p['age']}</div>
                    </div>""", unsafe_allow_html=True)
                with ci2:
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
