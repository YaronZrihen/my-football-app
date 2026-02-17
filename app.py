import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב CSS מעודכן (יישור לימין והוספת גיל) ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    .block-container { padding: 10px !important; }
    
    /* יישור כותרות וטקסט כללי לימין */
    h1, h2, h3, h4, h5, p, label, span { text-align: right !important; direction: rtl; }

    /* נעילת שתי עמודות ב-Grid */
    div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 8px !important;
    }
    
    div[data-testid="column"] {
        width: 100% !important;
        min-width: 0 !important;
        flex: none !important;
    }

    /* כרטיס שחקן צפוף */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 4px 8px;
        margin-bottom: 2px;
        display: flex;
        flex-direction: row-reverse; /* לשמירה על סדר שם מימין וציון משמאל */
        justify-content: space-between;
        align-items: center;
        height: 32px;
    }
    .p-name { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: right; flex-grow: 1; }
    .p-score { font-size: 11px; color: #22c55e; font-weight: bold; margin-right: 5px; }

    /* כפתור 🔄 */
    .stButton > button[key^="m_"] {
        width: 100% !important;
        height: 24px !important;
        line-height: 1 !important;
        padding: 0 !important;
        font-size: 11px !important;
        margin-bottom: 10px;
        background-color: #3d495d !important;
    }

    /* טבלת מאזן (כולל גיל) */
    .stats-table {
        width: 100%;
        margin-top: 15px;
        border-collapse: collapse;
        background: #2d3748;
        direction: rtl;
    }
    .stats-table td {
        padding: 6px;
        text-align: center;
        border: 1px solid #4a5568;
        font-size: 13px;
    }
    .stats-table b { color: #22c55e; }
    .stats-header { background: #1a1c23; font-weight: bold; }
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
    
    # חישוב ציון
    r = float(p.get('rating', 5.0))
    try:
        pr = json.loads(p.get('peer_ratings', '{}'))
        peers = [float(v) for v in pr.values()]
        avg_p = sum(peers)/len(peers) if peers else 0
    except: avg_p = 0
    final_score = (r + avg_p) / 2 if avg_p > 0 else r
    
    # חילוץ שנת לידה
    birth_year = int(p.get('birth_year', 1995))
    return final_score, birth_year

# --- 3. ממשק ---
st.title("⚽ חלוקת קבוצות")

all_names = sorted([p['name'] for p in st.session_state.players])
selected = st.pills("מי הגיע?", all_names, selection_mode="multi")

if st.button("חלק קבוצות 🚀", use_container_width=True):
    pool = []
    current_year = datetime.now().year
    for name in selected:
        score, b_year = get_player_info(name)
        pool.append({'name': name, 'f': score, 'age': current_year - b_year})
    
    pool.sort(key=lambda x: x['f'], reverse=True)
    st.session_state.t1, st.session_state.t2 = pool[0::2], pool[1::2]

if 't1' in st.session_state and selected:
    c1, c2 = st.columns(2)
    
    teams = [(c1, st.session_state.t1, "⚪ לבן", "w"), 
             (c2, st.session_state.t2, "⚫ שחור", "b")]
    
    for col, team, label, pfx in teams:
        with col:
            st.markdown(f"<p style='text-align:center; font-weight:bold; margin-bottom:5px;'>{label}</p>", unsafe_allow_html=True)
            for i, p in enumerate(team):
                st.markdown(f"""
                    <div class='p-box'>
                        <span class='p-name'>{p['name']}</span>
                        <span class='p-score'>{p['f']:.1f}</span>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("🔄", key=f"m_{pfx}_{i}"):
                    if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                    else: st.session_state.t1.append(st.session_state.t2.pop(i))
                    st.rerun()

    # --- 4. מאזן מעודכן (כוח + גיל) ---
    s1 = sum(p['f'] for p in st.session_state.t1)
    s2 = sum(p['f'] for p in st.session_state.t2)
    a1 = sum(p['age'] for p in st.session_state.t1) / len(st.session_state.t1) if st.session_state.t1 else 0
    a2 = sum(p['age'] for p in st.session_state.t2) / len(st.session_state.t2) if st.session_state.t2 else 0
    
    st.markdown(f"""
        <table class="stats-table">
            <tr class="stats-header">
                <td>נתון</td>
                <td>⚪ לבן</td>
                <td>⚫ שחור</td>
            </tr>
            <tr>
                <td><b>כוח</b></td>
                <td><b>{s1:.1f}</b></td>
                <td><b>{s2:.1f}</b></td>
            </tr>
            <tr>
                <td><b>גיל ממוצע</b></td>
                <td>{a1:.1f}</td>
                <td>{a2:.1f}</td>
            </tr>
        </table>
    """, unsafe_allow_html=True)

    # וואטסאפ
    msg = f"⚽ קבוצות:\n\n⚪ לבן:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1]) + f"\n\n⚫ שחור:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
    st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg)}" style="display:block; text-align:center; background:#22c55e; color:white; padding:10px; border-radius:6px; text-decoration:none; margin-top:15px; font-weight:bold;">📲 שלח לוואטסאפ</a>', unsafe_allow_html=True)
