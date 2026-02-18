import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS (אופטימיזציה מקסימלית לרוחב סלולר) ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    .block-container { padding: 5px !important; max-width: 100% !important; }
    
    /* כותרות */
    .main-title { font-size: 20px !important; text-align: center !important; font-weight: bold; color: #60a5fa; margin-bottom: 0; }
    .sub-title { font-size: 14px !important; text-align: center !important; color: #cbd5e0; margin-bottom: 10px; }

    /* כפיית 2 עמודות צמודות ללא ריווח */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important; /* ריווח אפסי בין הקבוצות */
    }
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 48% !important;
        padding: 0 !important;
    }

    /* שורת שחקן קומפקטית במיוחד */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 3px;
        padding: 1px 4px;
        margin-bottom: 2px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 26px; /* גובה מינימלי */
    }
    .p-name { font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70%; }
    .p-score { font-size: 9px; color: #22c55e; font-weight: bold; }

    /* כפתור החלפה מיקרוסקופי */
    .swap-btn button {
        padding: 0px !important;
        min-height: 20px !important;
        height: 22px !important;
        width: 22px !important;
        font-size: 10px !important;
        line-height: 1 !important;
        background-color: transparent !important;
        border: 1px solid #4a5568 !important;
    }

    .team-label { text-align: center !important; font-size: 13px; font-weight: bold; padding: 5px 0; }
    .team-stats { background: #1e293b; font-size: 9px; text-align: center; padding: 2px; border-radius: 0 0 5px 5px; }
    
    /* הסתרת אלמנטים מיותרים בסלולר */
    div[data-testid="stFormSubmitButton"] { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ונתונים ---
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

# --- טאב חלוקה ---
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
        col_w, col_b = st.columns(2)
        teams = [{"t": st.session_state.t1, "l": "⚪ לבן", "id": "w"}, {"t": st.session_state.t2, "l": "⚫ שחור", "id": "b"}]
        
        for col, data in zip([col_w, col_b], teams):
            with col:
                st.markdown(f"<div class='team-label'>{data['l']}</div>", unsafe_allow_html=True)
                for i, p in enumerate(data['t']):
                    row_col, btn_col = st.columns([4, 1])
                    with row_col:
                        st.markdown(f"<div class='p-box'><span class='p-name'>{p['name']}</span><span class='p-score'>{p['f']:.1f}</span></div>", unsafe_allow_html=True)
                    with btn_col:
                        st.markdown("<div class='swap-btn'>", unsafe_allow_html=True)
                        if st.button("🔄", key=f"sw_{data['id']}_{i}"):
                            if data['id'] == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                            else: st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                
                if data['t']:
                    af = sum(x['f'] for x in data['t'])/len(data['t'])
                    aa = sum(x['age'] for x in data['t'])/len(data['t'])
                    st.markdown(f"<div class='team-stats'>רמה: {af:.1f} | גיל: {aa:.1f}</div>", unsafe_allow_html=True)

# --- טאב מאגר (מקוצר) ---
with tab2:
    for i, p in enumerate(st.session_state.players):
        score, birth = get_player_stats(p['name'])
        st.markdown(f"<div class='database-card'><b>{p['name']} ({2026-birth})</b><br><small>ציון: {score:.1f}</small></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([4, 1])
        with c1: 
            if st.button("📝", key=f"e_{i}"): 
                st.session_state.edit_name = p['name']; st.rerun()
        with c2: 
            if st.button("🗑️", key=f"d_{i}"): 
                st.session_state.players.pop(i); save_to_gsheets(); st.rerun()

# --- טאב עדכון ---
with tab3:
    all_n = ["🆕 חדש"] + sorted([p['name'] for p in st.session_state.players])
    target = st.session_state.get('edit_name', "🆕 חדש")
    choice = st.selectbox("בחר שחקן:", all_n, index=all_n.index(target) if target in all_n else 0)
    p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
    
    with st.form("f"):
        name = st.text_input("שם:", value=p_data['name'] if p_data else "")
        year = st.number_input("שנה:", 1960, 2020, int(p_data['birth_year']) if p_data else 1990)
        roles = st.pills("תפקידים:", ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"], selection_mode="multi", default=safe_split(p_data.get('roles', '')) if p_data else [])
        rate = st.radio("ציון:", range(1, 11), index=int(p_data.get('rating', 5))-1 if p_data else 4, horizontal=True)
        if st.form_submit_button("שמור ✅"):
            entry = {"name": name, "birth_year": year, "rating": rate, "roles": ",".join(roles), "peer_ratings": p_data.get('peer_ratings', '{}') if p_data else '{}'}
            if p_data:
                idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                st.session_state.players[idx] = entry
            else: st.session_state.players.append(entry)
            save_to_gsheets(); st.rerun()
