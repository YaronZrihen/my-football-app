import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS (שליטה מלאה ב-HTML) ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    .block-container { padding: 10px !important; max-width: 450px !important; }
    
    .main-title { font-size: 20px !important; text-align: center !important; font-weight: bold; color: #60a5fa; margin: 0; }
    .sub-title { font-size: 14px !important; text-align: center !important; color: #cbd5e0; margin-bottom: 10px; }

    /* המבנה של שתי העמודות */
    .teams-container {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        width: 100%;
        margin-top: 10px;
    }
    .team-column {
        flex: 1;
        min-width: 0; /* מונע התרחבות */
    }
    .team-header {
        text-align: center;
        font-weight: bold;
        padding: 5px;
        background: #2d3748;
        border-radius: 5px 5px 0 0;
        font-size: 14px;
        border-bottom: 2px solid #4a5568;
    }
    .player-row {
        background: #1e293b;
        border: 1px solid #334155;
        padding: 4px 6px;
        margin-top: 2px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 3px;
        height: 30px;
    }
    .p-name { font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 75%; }
    .p-score { font-size: 9px; color: #22c55e; font-weight: bold; }
    
    .team-summary {
        background: #0f172a;
        font-size: 10px;
        text-align: center;
        padding: 4px;
        border-radius: 0 0 5px 5px;
        color: #94a3b8;
    }

    /* תיקון כפתור ה-Pills בסלולר */
    div[data-testid="stPills"] button { font-size: 11px !important; padding: 2px 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ---
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
        # יצירת הטבלה ב-HTML טהור
        t1, t2 = st.session_state.t1, st.session_state.t2
        
        # חישוב ממוצעים
        avg_f1 = sum(p['f'] for p in t1)/len(t1) if t1 else 0
        avg_f2 = sum(p['f'] for p in t2)/len(t2) if t2 else 0
        
        html_code = f"""
        <div class="teams-container">
            <div class="team-column">
                <div class="team-header">⚪ לבן</div>
                {''.join([f'<div class="player-row"><span class="p-name">{p["name"]}</span><span class="p-score">{p["f"]:.1f}</span></div>' for p in t1])}
                <div class="team-summary">רמה: {avg_f1:.1f}</div>
            </div>
            <div class="team-column">
                <div class="team-header">⚫ שחור</div>
                {''.join([f'<div class="player-row"><span class="p-name">{p["name"]}</span><span class="p-score">{p["f"]:.1f}</span></div>' for p in t2])}
                <div class="team-summary">רמה: {avg_f2:.1f}</div>
            </div>
        </div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
        
        # כפתורי החלפה מתחת לטבלה (בצורה מסודרת)
        st.write("")
        st.caption("החלפת שחקן (הראשון ברשימה יעבור לקבוצה השנייה):")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 העבר מהלבן", key="mv_w"):
                if t1: st.session_state.t2.append(st.session_state.t1.pop(0))
                st.rerun()
        with c2:
            if st.button("🔄 העבר מהשחור", key="mv_b"):
                if t2: st.session_state.t1.append(st.session_state.t2.pop(0))
                st.rerun()

with tab2:
    for p in st.session_state.players:
        st.markdown(f"**{p['name']}**")

with tab3:
    st.write("לטופס העדכון השתמש בטאב הקודם.")
