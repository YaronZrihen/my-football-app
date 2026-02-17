import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json

# --- 1. הגדרות ועיצוב CSS "ברזל" ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    .block-container { padding: 10px !important; }

    /* הכרחת שתי עמודות בכל מצב - דריסה אגרסיבית */
    div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important; /* שתי עמודות שוות */
        gap: 8px !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
    }
    
    div[data-testid="column"] {
        width: 100% !important; /* תופס את כל ה-1fr שלו */
        min-width: 0 !important;
        flex: none !important;
    }

    /* כרטיס שחקן צפוף */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 4px 6px;
        margin-bottom: 2px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 32px;
    }
    .p-name { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-score { font-size: 11px; color: #22c55e; font-weight: bold; }

    /* כפתור 🔄 דק ורחב */
    .stButton > button[key^="m_"] {
        width: 100% !important;
        height: 24px !important;
        line-height: 1 !important;
        padding: 0 !important;
        font-size: 11px !important;
        margin-top: -2px;
        margin-bottom: 10px;
        background-color: #3d495d !important;
        border: 1px solid #4a5568 !important;
    }

    /* טבלת מאזן מסודרת */
    .stats-table {
        width: 100%;
        margin-top: 15px;
        border-collapse: collapse;
        background: #2d3748;
        border-radius: 6px;
        overflow: hidden;
    }
    .stats-table td {
        padding: 8px;
        text-align: center;
        border: 1px solid #4a5568;
        font-size: 14px;
    }
    .stats-table b { color: #22c55e; }

    /* כפתור וואטסאפ */
    .wa-btn {
        display: block;
        text-align: center;
        background: #22c55e;
        color: white !important;
        padding: 10px;
        border-radius: 6px;
        text-decoration: none;
        margin-top: 15px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. טעינת נתונים ---
if 'players' not in st.session_state:
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0
    r = float(p.get('rating', 5.0))
    try:
        pr = json.loads(p.get('peer_ratings', '{}'))
        peers = [float(v) for v in pr.values()]
        avg_p = sum(peers)/len(peers) if peers else 0
    except: avg_p = 0
    return (r + avg_p) / 2 if avg_p > 0 else r

# --- 3. ממשק ראשי ---
st.title("⚽ חלוקת קבוצות")

all_names = [p['name'] for p in st.session_state.players]
selected = st.pills("מי הגיע?", sorted(all_names), selection_mode="multi")

if st.button("חלק קבוצות 🚀", use_container_width=True):
    pool = []
    for name in selected:
        pool.append({'name': name, 'f': get_stats(name)})
    pool.sort(key=lambda x: x['f'], reverse=True)
    st.session_state.t1, st.session_state.t2 = pool[0::2], pool[1::2]

# --- 4. תצוגת הקבוצות בשני טורים ---
if 't1' in st.session_state and selected:
    # מבנה העמודות המוגן ב-Grid
    col_left, col_right = st.columns(2)
    
    teams = [(col_left, st.session_state.t1, "⚪ לבן", "w"), 
             (col_right, st.session_state.t2, "⚫ שחור", "b")]
    
    for col, team, label, pfx in teams:
        with col:
            st.markdown(f"<p style='text-align:center; font-weight:bold; margin-bottom:5px;'>{label}</p>", unsafe_allow_html=True)
            for i, p in enumerate(team):
                # שורת שחקן
                st.markdown(f"""
                    <div class='p-box'>
                        <span class='p-name'>{p['name']}</span>
                        <span class='p-score'>{p['f']:.1f}</span>
                    </div>
                """, unsafe_allow_html=True)
                # כפתור החלפה
                if st.button("🔄", key=f"m_{pfx}_{i}"):
                    if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                    else: st.session_state.t1.append(st.session_state.t2.pop(i))
                    st.rerun()

    # --- 5. מאזן בטבלה צמודה ---
    s1 = sum(p['f'] for p in st.session_state.t1)
    s2 = sum(p['f'] for p in st.session_state.t2)
    
    st.markdown(f"""
        <table class="stats-table">
            <tr>
                <td>לבן: <b>{s1:.1f}</b></td>
                <td>שחור: <b>{s2:.1f}</b></td>
            </tr>
        </table>
    """, unsafe_allow_html=True)

    # --- 6. כפתור וואטסאפ ---
    msg = f"⚽ קבוצות להיום:\n\n⚪ לבן:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1]) + f"\n\n⚫ שחור:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
    st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg)}" class="wa-btn">📲 שלח לוואטסאפ</a>', unsafe_allow_html=True)

# כפתור לרענון המאגר
if st.button("🔄 רענן רשימת שחקנים", key="refresh"):
    st.cache_data.clear()
    st.rerun()
    
