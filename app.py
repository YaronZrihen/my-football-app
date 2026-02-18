import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import urllib.parse

# --- 1. עיצוב CSS אגרסיבי למניעת קריסה בטור ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    .block-container { padding: 5px !important; max-width: 500px !important; }
    
    .main-title { font-size: 22px !important; text-align: center !important; font-weight: bold; color: #60a5fa; margin: 5px 0; }
    .sub-title { font-size: 16px !important; text-align: center !important; color: #cbd5e0; margin-bottom: 15px; }

    /* המכולה ששומרת על 2 טורים בכל מצב */
    .flex-container {
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        gap: 6px !important;
        width: 100% !important;
    }
    
    .team-column {
        flex: 1 !important;
        min-width: 0 !important;
    }

    .team-header {
        text-align: center;
        font-weight: bold;
        padding: 8px;
        background: #2d3748;
        border-radius: 6px 6px 0 0;
        font-size: 16px;
        border-bottom: 2px solid #4a5568;
    }

    .player-card {
        background: #1e293b;
        border: 1px solid #334155;
        padding: 8px;
        margin-top: 3px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 4px;
    }

    .p-name-text { 
        font-size: 15px !important; /* הגדלת פונט */
        font-weight: bold;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .p-stats-text { 
        font-size: 12px; 
        color: #22c55e; 
    }

    /* כפתור החלפה ללא מסגרת */
    .swap-icon {
        text-decoration: none !important;
        font-size: 18px !important;
        padding: 0 5px;
        cursor: pointer;
        filter: grayscale(1) brightness(1.5);
    }

    .balance-footer {
        background: #0f172a;
        font-size: 13px;
        text-align: center;
        padding: 8px;
        border-radius: 0 0 6px 6px;
        color: #60a5fa;
        border-top: 1px solid #334155;
        margin-top: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ונתונים ---
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
    pr = json.loads(p.get('peer_ratings', '{}')) if isinstance(p.get('peer_ratings'), str) else {}
    peers = [float(v) for v in pr.values()] if pr else []
    return (r + sum(peers)/len(peers))/2 if peers else r, int(p.get('birth_year', 1995))

# --- 3. ממשק משתמש ---
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
        t1, t2 = st.session_state.t1, st.session_state.t2
        
        # בניית ה-HTML של העמודות
        def build_team_html(team_list, label, team_id):
            avg_f = sum(p['f'] for p in team_list)/len(team_list) if team_list else 0
            avg_a = sum(p['age'] for p in team_list)/len(team_list) if team_list else 0
            
            rows = ""
            for i, p in enumerate(team_list):
                rows += f"""
                <div class="player-card">
                    <div style="display: flex; flex-direction: column;">
                        <span class="p-name-text">{p['name']}</span>
                        <span class="p-stats-text">ציון: {p['f']:.1f} | גיל: {p['age']}</span>
                    </div>
                </div>
                """
            
            footer = f"""
            <div class="balance-footer">
                <b>רמה: {avg_f:.1f}</b><br>גיל: {avg_a:.1f}
            </div>
            """
            return f'<div class="team-column"><div class="team-header">{label}</div>{rows}{footer}</div>'

        # הצגת הטבלה ב-HTML (מונע קריסה לטורים)
        st.markdown(f"""
        <div class="flex-container">
            {build_team_html(t1, "⚪ לבן", "w")}
            {build_team_html(t2, "⚫ שחור", "b")}
        </div>
        """, unsafe_allow_html=True)

        # כפתורי החלפה (מחוץ ל-HTML כדי שיעבדו פונקציונלית ב-Streamlit)
        st.write("")
        st.markdown("<p style='text-align:center; font-size:14px;'>🔄 <b>החלפת שחקנים:</b></p>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            move_w = st.selectbox("מהלבן לשחור:", ["--"] + [p['name'] for p in t1], key="sel_w")
            if move_w != "--":
                idx = next(i for i, p in enumerate(t1) if p['name'] == move_w)
                st.session_state.t2.append(st.session_state.t1.pop(idx))
                st.rerun()
        with col2:
            move_b = st.selectbox("מהשחור ללבן:", ["--"] + [p['name'] for p in t2], key="sel_b")
            if move_b != "--":
                idx = next(i for i, p in enumerate(t2) if p['name'] == move_b)
                st.session_state.t1.append(st.session_state.t2.pop(idx))
                st.rerun()

with tab2:
    st.write("צפייה ברשימת השחקנים...")

with tab3:
    st.write("טופס עדכון שחקנים...")
