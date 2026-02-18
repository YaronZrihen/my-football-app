import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS (ביטול WIDE וכפיית פריסה קומפקטית) ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    /* הגדרות בסיס */
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    
    /* צמצום המרווחים של ה-Container הראשי */
    .block-container { 
        padding-top: 1rem !important; 
        padding-bottom: 1rem !important; 
        padding-left: 0.5rem !important; 
        padding-right: 0.5rem !important; 
        max-width: 500px !important; /* הגבלת רוחב כדי שלא יימרח */
    }

    /* כותרות */
    .main-title { font-size: 20px !important; text-align: center !important; font-weight: bold; color: #60a5fa; margin-bottom: 0px; }
    .sub-title { font-size: 14px !important; text-align: center !important; color: #cbd5e0; margin-bottom: 15px; }

    /* הקסם של ה-2 עמודות בסלולר */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
        width: 100% !important;
    }
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 48% !important;
        max-width: 50% !important;
    }

    /* כרטיס שחקן מינימליסטי */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 4px 6px;
        margin-bottom: 3px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 32px;
    }
    .p-name { font-size: 12px; font-weight: 500; white-space: nowrap; overflow: hidden; }
    .p-score { font-size: 10px; color: #22c55e; font-weight: bold; }

    /* כפתור החלפה קטן ומוצמד */
    .stButton button {
        padding: 0px !important;
        height: 28px !important;
        width: 28px !important;
        font-size: 12px !important;
        border-radius: 4px !important;
    }

    .team-label { text-align: center !important; font-size: 15px; font-weight: bold; padding: 5px 0; border-bottom: 1px solid #4a5568; margin-bottom: 5px; }
    .team-stats { background: #1e293b; font-size: 10px; text-align: center; padding: 4px; border-radius: 0 0 5px 5px; margin-top: 2px; }
    
    /* הסתרת רווחים מיותרים ב-Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות נתונים ---
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
    return (r + avg_p) / 2 if avg_p > 0 else r, int(p.get('birth_year', 1995))

# --- 3. ממשק משתמש ---
st.markdown("<div class='main-title'>⚽ ניהול קבוצות כדורגל</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>שישי וולפסון חולון</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר", "📝 עדכון"])

with tab1:
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected_names = st.pills("מי הגיע?", all_names, selection_mode="multi", key="p_selection")

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
        # פריסת עמודות קבועה
        col_w, col_b = st.columns(2)
        teams = [{"t": st.session_state.t1, "l": "⚪ לבן", "id": "w"}, {"t": st.session_state.t2, "l": "⚫ שחור", "id": "b"}]
        
        for col, data in zip([col_w, col_b], teams):
            with col:
                st.markdown(f"<div class='team-label'>{data['l']}</div>", unsafe_allow_html=True)
                for i, p in enumerate(data['t']):
                    # חלוקה פנימית בתוך העמודה: שם/ציון וכפתור
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"<div class='p-box'><span class='p-name'>{p['name']}</span><span class='p-score'>{p['f']:.1f}</span></div>", unsafe_allow_html=True)
                    with c2:
                        if st.button("🔄", key=f"sw_{data['id']}_{i}"):
                            if data['id'] == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                            else: st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()
                
                if data['t']:
                    af = sum(x['f'] for x in data['t'])/len(data['t'])
                    aa = sum(x['age'] for x in data['t'])/len(data['t'])
                    st.markdown(f"<div class='team-stats'>רמה: {af:.1f} | גיל: {aa:.1f}</div>", unsafe_allow_html=True)

    for _ in range(4): st.write("")

# טאב מאגר ועדכון נשארים פונקציונליים כרגיל
with tab2:
    for i, p in enumerate(st.session_state.players):
        score, birth = get_player_stats(p['name'])
        st.markdown(f"<div class='database-card'><b>{p['name']} ({2026-birth})</b><br><small>ציון: {score:.1f}</small></div>", unsafe_allow_html=True)
        if st.button("📝 עריכה", key=f"e_{i}"):
            st.session_state.edit_name = p['name']; st.rerun()

with tab3:
    all_n = ["🆕 חדש"] + sorted([p['name'] for p in st.session_state.players])
    target = st.session_state.get('edit_name', "🆕 חדש")
    choice = st.selectbox("בחר שחקן:", all_n, index=all_n.index(target) if target in all_n else 0)
    p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
    with st.form("f"):
        name = st.text_input("שם:", value=p_data['name'] if p_data else "")
        year = st.number_input("שנה:", 1960, 2020, int(p_data['birth_year']) if p_data else 1990)
        roles = st.pills("תפקידים:", ["שוער", "בלם", "מגן", "קשר", "חלוץ"], selection_mode="multi", default=safe_split(p_data.get('roles', '')) if p_data else [])
        if st.form_submit_button("שמור ✅"):
            entry = {"name": name, "birth_year": year, "rating": p_data.get('rating', 5) if p_data else 5, "roles": ",".join(roles), "peer_ratings": p_data.get('peer_ratings', '{}') if p_data else '{}'}
            if p_data:
                idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                st.session_state.players[idx] = entry
            else: st.session_state.players.append(entry)
            save_to_gsheets(); st.rerun()
