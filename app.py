import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS "דורסני" למניעת רווחים ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    
    /* ביטול מרווחים של ה-Container הראשי */
    .block-container { padding: 5px !important; max-width: 100% !important; }

    /* כפיית 2 עמודות צמודות ללא ריווח פנימי */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important;
    }
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 0 !important;
        padding: 0 !important;
    }

    /* כרטיס שחקן דק במיוחד */
    .player-row {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        margin: 2px 0;
        padding: 4px 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 45px;
    }
    .p-info { display: flex; flex-direction: column; overflow: hidden; }
    .p-name { font-size: 14px; font-weight: bold; color: white; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-stats { font-size: 11px; color: #22c55e; }

    /* עיצוב כפתור החלפה מינימליסטי */
    .stButton button {
        padding: 0 !important;
        margin: 0 !important;
        height: 35px !important;
        width: 35px !important;
        min-width: 35px !important;
        background-color: #4a5568 !important;
        border: none !important;
        font-size: 16px !important;
    }

    .team-header {
        text-align: center; font-weight: bold; padding: 6px; 
        border-radius: 4px; margin-bottom: 4px; font-size: 15px;
    }
    .footer-stats {
        background: #1e293b; text-align: center; padding: 4px;
        font-size: 11px; color: #60a5fa; border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except:
        st.session_state.players = []

def get_player_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 30
    r = float(p.get('rating', 5.0))
    pr = json.loads(p.get('peer_ratings', '{}')) if isinstance(p.get('peer_ratings'), str) else {}
    peers = [float(v) for v in pr.values()] if pr else []
    score = (r + sum(peers)/len(peers))/2 if peers else r
    return score, 2026 - int(p.get('birth_year', 1996))

# --- 3. ממשק חלוקה ---
st.markdown("<h3 style='text-align:center;'>⚽ וולפסון חולון</h3>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר", "📝 עדכון"])

with tab1:
    all_n = sorted([p['name'] for p in st.session_state.players])
    selected = st.pills("מי כאן?", all_n, selection_mode="multi")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            for n in selected:
                s, a = get_player_stats(n)
                pool.append({'name': n, 'f': s, 'age': a})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        c1, c2 = st.columns(2)
        
        for col, team, label, tid, color in zip([c1, c2], 
                                              [st.session_state.t1, st.session_state.t2], 
                                              ["⚪ לבן", "⚫ שחור"], ["w", "b"], ["#3b82f6", "#4a5568"]):
            with col:
                st.markdown(f"<div class='team-header' style='background:{color};'>{label}</div>", unsafe_allow_html=True)
                for i, p in enumerate(team):
                    # שורה אחת שכוללת הכל
                    inner_c1, inner_c2 = st.columns([0.75, 0.25])
                    with inner_c1:
                        st.markdown(f"""<div class='player-row'>
                            <div class='p-info'>
                                <span class='p-name'>{p['name']}</span>
                                <span class='p-stats'>{p['f']:.1f} | {p['age']}</span>
                            </div>
                        </div>""", unsafe_allow_html=True)
                    with inner_c2:
                        if st.button("🔄", key=f"s_{tid}_{i}"):
                            if tid == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                            else: st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()
                
                if team:
                    avg = sum(x['f'] for x in team)/len(team)
                    st.markdown(f"<div class='footer-stats'>רמה: {avg:.1f}</div>", unsafe_allow_html=True)

# --- שאר הטאבים נשארים אותו דבר ---
with tab2:
    st.write("רשימת שחקנים...")
with tab3:
    st.write("טופס עדכון...")
