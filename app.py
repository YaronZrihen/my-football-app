import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS (החזרת העיצוב המקורי + חסימת גלישה) ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    /* חסימת גלישה רוחבית מוחלטת - התיקון לנזק ה-Wide */
    html, body, [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
        position: relative;
    }
    .block-container { 
        max-width: 100vw !important; 
        overflow-x: hidden !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    /* הקוד המקורי שלך ללא שינוי */
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span, div { text-align: right !important; direction: rtl; }
    .main-title { font-size: 22px !important; text-align: center !important; font-weight: bold; margin-bottom: 15px; color: #60a5fa; }
    
    .database-card { 
        background: #2d3748; border: 1px solid #4a5568; border-radius: 8px; padding: 12px; margin-bottom: 5px;
        display: flex; flex-direction: column; align-items: flex-start;
    }
    
    div[data-testid="stPills"] button { background-color: #4a5568 !important; color: white !important; border-radius: 20px !important; }
    div[data-testid="stPills"] button[aria-checked="true"] { background-color: #60a5fa !important; border: 1px solid white !important; }

    .p-box {
        background: #2d3748; border: 1px solid #4a5568; border-radius: 4px; padding: 2px 8px;
        margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center; min-height: 35px;
    }
    
    .team-stats {
        background: #1e293b; border-top: 2px solid #4a5568; padding: 8px;
        margin-top: 5px; font-size: 12px; text-align: center; border-radius: 0 0 8px 8px;
    }

    /* הבטחת שתי עמודות צמודות בסלולר כפי שביקשת */
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 5px !important; }
    [data-testid="column"] { flex: 1 !important; min-width: 0 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- כל שאר הקוד שלך נשאר זהה לחלוטין (Copy-Paste מהגרסה התקינה שלך) ---

def safe_split(val):
    if not val or pd.isna(val): return []
    return str(val).split(',')

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
    except:
        st.session_state.players = []

def save_to_gsheets():
    df = pd.DataFrame(st.session_state.players)
    conn.update(data=df)
    st.cache_data.clear()

def get_player_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 1995
    r = float(p.get('rating', 5.0))
    pr = safe_get_json(p.get('peer_ratings', '{}'))
    peers = [float(v) for v in pr.values()] if isinstance(pr, dict) else []
    avg_p = sum(peers)/len(peers) if peers else 0
    final_score = (r + avg_p) / 2 if avg_p > 0 else r
    return final_score, int(p.get('birth_year', 1995))

if 'edit_name' not in st.session_state: st.session_state.edit_name = "🆕 שחקן חדש"

st.markdown("<div class='main-title'>⚽ ניהול כדורגל 2026</div>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון/הרשמה"])

# טאב חלוקה
with tab1:
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected_names = st.pills("בחר שחקנים שהגיעו:", all_names, selection_mode="multi", key="p_selection")
    st.markdown(f"**נבחרו: {len(selected_names) if selected_names else 0} שחקנים**")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected_names:
            pool = []
            for n in selected_names:
                s, b = get_player_stats(n)
                pool.append({'name': n, 'f': s, 'age': 2026 - b})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected_names:
        col_w, col_b = st.columns(2)
        teams_data = [{"team": st.session_state.t1, "label": "⚪ לבן", "pfx": "w"}, {"team": st.session_state.t2, "label": "⚫ שחור", "pfx": "b"}]
        for col, data in zip([col_w, col_b], teams_data):
            with col:
                st.markdown(f"<p style='text-align:center; font-weight:bold;'>{data['label']}</p>", unsafe_allow_html=True)
                for i, p in enumerate(data['team']):
                    c_txt, c_swp = st.columns([4, 1])
                    with c_txt:
                        st.markdown(f"<div class='p-box'><span>{p['name']} ({p['age']})</span><span style='color:#22c55e; font-size:11px; font-weight:bold;'>{p['f']:.1f}</span></div>", unsafe_allow_html=True)
                    with c_swp:
                        if st.button("🔄", key=f"sw_{data['pfx']}_{i}"):
                            if data['pfx'] == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                            else: st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()
                if data['team']:
                    avg_f = sum(p['f'] for p in data['team']) / len(data['team'])
                    avg_a = sum(p['age'] for p in data['team']) / len(data['team'])
                    st.markdown(f"<div class='team-stats'><b>רמה: {avg_f:.1f}</b><br>גיל: {avg_a:.1f}</div>", unsafe_allow_html=True)

# כאן יבוא המשך הקוד של טאב 2 ו-3 שלך (בדיוק כפי שהם אצלך במקור)
