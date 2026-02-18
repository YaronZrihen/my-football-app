import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS (שליטה מלאה ב-HTML + Flexbox) ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    .block-container { padding: 8px !important; max-width: 450px !important; }
    
    .main-title { font-size: 20px !important; text-align: center !important; font-weight: bold; color: #60a5fa; margin: 0; }
    .sub-title { font-size: 14px !important; text-align: center !important; color: #cbd5e0; margin-bottom: 10px; }

    .teams-container {
        display: flex;
        justify-content: space-between;
        gap: 4px;
        width: 100%;
    }
    .team-column {
        flex: 1;
        min-width: 0;
    }
    .team-header {
        text-align: center;
        font-weight: bold;
        padding: 4px;
        background: #2d3748;
        border-radius: 5px 5px 0 0;
        font-size: 13px;
        border-bottom: 2px solid #4a5568;
    }
    .player-row {
        background: #1e293b;
        border: 1px solid #334155;
        padding: 0 4px 0 8px;
        margin-top: 2px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 3px;
        height: 32px;
    }
    .p-info { display: flex; flex-direction: column; justify-content: center; overflow: hidden; }
    .p-name { font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-score { font-size: 9px; color: #22c55e; line-height: 1; }
    
    .team-summary {
        background: #0f172a;
        font-size: 10px;
        text-align: center;
        padding: 5px;
        border-radius: 0 0 5px 5px;
        color: #94a3b8;
        border-top: 1px solid #334155;
    }

    /* כפתור החלפה בתוך השורה */
    .stButton button {
        padding: 0 !important;
        height: 24px !important;
        width: 24px !important;
        min-width: 24px !important;
        font-size: 12px !important;
        background-color: #334155 !important;
        border: none !important;
        margin-left: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ---
def safe_get_json(val):
    if not val or pd.isna(val): return {}
    if isinstance(val, dict): return val
    try: return json.loads(str(val))
    except: return {}

conn = st.connection("gsheets", type=GSheetsConnection)
if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

def get_player_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 1995
    r = float(p.get('rating', 5.0))
    pr = safe_get_json(p.get('peer_ratings', '{}'))
    peers = [float(v) for v in pr.values()] if pr else []
    return (r + sum(peers)/len(peers))/2 if peers else r, int(p.get('birth_year', 1995))

# --- 3. ממשק ---
st.markdown("<div class='main-title'>⚽ ניהול קבוצות כדורגל</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>שישי וולפסון חולון</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר", "📝 עדכון"])

with tab1:
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected = st.pills("מי הגיע?", all_names, selection_mode="multi")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            for n in selected:
                s, b = get_player_stats(n)
                pool.append({'name': n, 'f': s, 'age': 2026-b})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        # יצירת מכולה לשתי העמודות
        col_white, col_black = st.columns(2)
        
        teams_config = [
            {"name": "⚪ לבן", "data": st.session_state.t1, "col": col_white, "id": "w"},
            {"name": "⚫ שחור", "data": st.session_state.t2, "col": col_black, "id": "b"}
        ]

        for team in teams_config:
            with team["col"]:
                st.markdown(f"<div class='team-header'>{team['name']}</div>", unsafe_allow_html=True)
                for i, p in enumerate(team["data"]):
                    # שימוש ב-columns פנימיים כדי לשלב כפתור בתוך ה-Flex
                    c_info, c_btn = st.columns([3, 1])
                    with c_info:
                        st.markdown(f"""
                            <div class='player-row'>
                                <div class='p-info'>
                                    <span class='p-name'>{p['name']}</span>
                                    <span class='p-score'>{p['f']:.1f} | {p['age']}</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    with c_btn:
                        if st.button("🔄", key=f"sw_{team['id']}_{i}"):
                            if team['id'] == "w":
                                st.session_state.t2.append(st.session_state.t1.pop(i))
                            else:
                                st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()
                
                # סיכום המאזן למטה
                if team["data"]:
                    avg_f = sum(p['f'] for p in team["data"])/len(team["data"])
                    avg_a = sum(p['age'] for p in team["data"])/len(team["data"])
                    st.markdown(f"""
                        <div class='team-summary'>
                            <b>ממוצע רמה: {avg_f:.1f}</b><br>
                            ממוצע גיל: {avg_a:.1f}
                        </div>
                    """, unsafe_allow_html=True)

with tab2:
    for p in st.session_state.players:
        st.write(p['name'])

with tab3:
    st.write("לטופס העדכון השתמש בטאב הייעודי.")
