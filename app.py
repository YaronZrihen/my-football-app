import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב CSS "מינימליסטי" ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    .block-container { padding: 5px !important; }
    
    /* הקטנה דרסטית של כותרות */
    h1 { font-size: 18px !important; text-align: center !important; margin-bottom: 10px !important; }
    .small-label { font-size: 12px !important; font-weight: bold; margin-bottom: 3px; display: block; }
    .team-header { text-align: center !important; font-size: 11px !important; font-weight: bold; margin-bottom: 3px; }

    /* נעילת שתי עמודות ב-Grid */
    div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 4px !important;
    }
    div[data-testid="column"] { width: 100% !important; min-width: 0 !important; flex: none !important; }

    /* שורת שחקן סופר-צפופה */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 3px;
        padding: 2px 6px;
        margin-bottom: 2px;
        display: flex;
        justify-content: flex-start;
        align-items: center;
        height: 24px;
        direction: rtl;
    }
    .p-text { font-size: 11.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-score-inline { color: #22c55e; font-size: 10px; margin-right: 3px; opacity: 0.8; }

    /* כפתור 🔄 מזערי */
    .stButton > button[key^="m_"] {
        width: 100% !important;
        height: 18px !important;
        line-height: 1 !important;
        padding: 0 !important;
        font-size: 9px !important;
        margin-bottom: 6px;
        background-color: #3d495d !important;
        border-radius: 2px !important;
    }

    /* טבלת מאזן מיקרוסקופית */
    .stats-table { width: 100%; margin-top: 8px; border-collapse: collapse; background: #2d3748; font-size: 10px; }
    .stats-table td { padding: 2px; text-align: center; border: 1px solid #4a5568; }
    
    /* הסתרת רווחים של Streamlit */
    div[data-testid="stVerticalBlock"] > div { gap: 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. נתונים ולוגיקה ---
if 'players' not in st.session_state:
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

def get_player_info(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 1995
    r = float(p.get('rating', 5.0))
    try:
        pr = json.loads(p.get('peer_ratings', '{}'))
        peers = [float(v) for v in pr.values()]
        avg_p = sum(peers)/len(peers) if peers else 0
    except: avg_p = 0
    return (r + avg_p) / 2 if avg_p > 0 else r, int(p.get('birth_year', 1995))

# --- 3. ממשק חלוקה ---
st.markdown("<h1>⚽ חלוקת קבוצות</h1>", unsafe_allow_html=True)

all_names = sorted([p['name'] for p in st.session_state.players])

# מונה שחקנים בכותרת של הבחירה
count_text = f" ({len(st.session_state.get('temp_selected', []))})" if 'temp_selected' in st.session_state else ""
selected = st.pills(f"מי הגיע?{count_text}", all_names, selection_mode="multi", key="temp_selected")

if st.button("חלק קבוצות 🚀", use_container_width=True):
    if not selected:
        st.warning("בחר שחקנים קודם")
    else:
        pool = []
        current_year = datetime.now().year
        for name in selected:
            score, b_year = get_player_info(name)
            pool.append({'name': name, 'f': score, 'age': current_year - b_year})
        
        pool.sort(key=lambda x: x['f'], reverse=True)
        # חלוקה בשיטת "נחש" לאיזון מקסימלי
        t1, t2 = [], []
        for i, p in enumerate(pool):
            if i % 4 == 0 or i % 4 == 3: t1.append(p)
            else: t2.append(p)
        st.session_state.t1, st.session_state.t2 = t1, t2

if 't1' in st.session_state and selected:
    c1, c2 = st.columns(2)
    
    teams = [(c1, st.session_state.t1, "⚪ לבן", "w"), 
             (c2, st.session_state.t2, "⚫ שחור", "b")]
    
    for col, team, label, pfx in teams:
        with col:
            st.markdown(f"<p class='team-header'>{label} ({len(team)})</p>", unsafe_allow_html=True)
            for i, p in enumerate(team):
                st.markdown(f"""
                    <div class='p-box'>
                        <span class='p-text'>{p['name']} <span class='p-score-inline'>({p['f']:.1f})</span></span>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("🔄", key=f"m_{pfx}_{i}"):
                    if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                    else: st.session_state.t1.append(st.session_state.t2.pop(i))
                    st.rerun()

    # --- 4. מאזן מיניאטורי ---
    s1 = sum(p['f'] for p in st.session_state.t1)
    s2 = sum(p['f'] for p in st.session_state.t2)
    a1 = sum(p['age'] for p in st.session_state.t1) / len(st.session_state.t1) if st.session_state.t1 else 0
    a2 = sum(p['age'] for p in st.session_state.t2) / len(st.session_state.t2) if st.session_state.t2 else 0
    
    st.markdown(f"""
        <table class="stats-table">
            <tr><td><b>כוח</b></td><td>⚪ {s1:.1f}</td><td>⚫ {s2:.1f}</td></tr>
            <tr><td><b>גיל</b></td><td>⚪ {a1:.1f}</td><td>⚫ {a2:.1f}</td></tr>
        </table>
    """, unsafe_allow_html=True)

    # כפתור וואטסאפ
    msg = f"⚽ קבוצות:\n\n⚪ לבן ({len(st.session_state.t1)}):\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1]) + f"\n\n⚫ שחור ({len(st.session_state.t2)}):\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
    st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg)}" style="display:block; text-align:center; background:#22c55e; color:white; padding:6px; border-radius:4px; text-decoration:none; margin-top:10px; font-weight:bold; font-size:12px;">📲 שלח לוואטסאפ</a>', unsafe_allow_html=True)
