import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS חסין סלולר ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span, div { text-align: right !important; direction: rtl; }
    .block-container { padding: 10px !important; }
    
    .main-title { font-size: 22px !important; text-align: center !important; font-weight: bold; margin-bottom: 5px; color: #60a5fa; }
    .sub-title { font-size: 16px !important; text-align: center !important; margin-bottom: 20px; color: #cbd5e0; }

    /* כפיית 2 עמודות בסלולר */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 0 !important;
    }

    /* כרטיס שחקן גדול וקריא */
    .p-card-mobile {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 4px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 55px;
    }
    .p-name-main { font-size: 16px !important; font-weight: bold; color: white; display: block; }
    .p-stats-sub { font-size: 12px !important; color: #22c55e; }

    /* עיצוב כפתור החלפה נקי */
    .stButton button {
        border: none !important;
        background-color: #334155 !important;
        color: white !important;
        height: 55px !important;
        width: 100% !important;
        font-size: 18px !important;
    }

    .team-header-box {
        text-align: center; font-weight: bold; padding: 10px; 
        border-radius: 8px 8px 0 0; margin-bottom: 5px; font-size: 18px;
    }
    .stats-footer {
        background: #1e293b; text-align: center; padding: 8px;
        border-radius: 0 0 8px 8px; font-size: 13px; color: #60a5fa;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה וחיבור לנתונים (החלק שחזר) ---
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
    peers = [float(v) for v in pr.values()] if peers else []
    avg_p = sum(peers)/len(peers) if peers else 0
    return (r + avg_p) / 2 if avg_p > 0 else r, int(p.get('birth_year', 1995))

# --- 3. כותרת ---
st.markdown("<div class='main-title'>⚽ ניהול קבוצות כדורגל</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>שישי וולפסון חולון</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר", "📝 עדכון"])

# --- 4. טאב חלוקה ---
with tab1:
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected_names = st.pills("מי הגיע?", all_names, selection_mode="multi")

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
        col_white, col_black = st.columns(2)
        
        teams_data = [
            {"t": st.session_state.t1, "label": "⚪ לבן", "color": "#3b82f6", "id": "w", "col": col_white},
            {"t": st.session_state.t2, "label": "⚫ שחור", "color": "#4a5568", "id": "b", "col": col_black}
        ]

        for team in teams_data:
            with team["col"]:
                st.markdown(f"<div class='team-header-box' style='background:{team['color']};'>{team['label']}</div>", unsafe_allow_html=True)
                for i, p in enumerate(team["t"]):
                    c_txt, c_btn = st.columns([3, 1])
                    with c_txt:
                        st.markdown(f"""<div class='p-card-mobile'>
                            <span class='p-name-main'>{p['name']}</span>
                            <span class='p-stats-sub'>רמה: {p['f']:.1f} | גיל: {p['age']}</span>
                        </div>""", unsafe_allow_html=True)
                    with c_btn:
                        if st.button("🔄", key=f"sw_{team['id']}_{i}"):
                            if team['id'] == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                            else: st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()
                
                if team["t"]:
                    avg_f = sum(x['f'] for x in team["t"]) / len(team["t"])
                    st.markdown(f"<div class='stats-footer'>ממוצע: {avg_f:.1f}</div>", unsafe_allow_html=True)

# --- 5. טאב מאגר ---
with tab2:
    for i, p in enumerate(st.session_state.players):
        score, birth = get_player_stats(p['name'])
        st.markdown(f"**{p['name']}** (בן {2026-birth}) | ציון: {score:.1f}")
        if st.button(f"ערוך את {p['name']}", key=f"ed_btn_{i}"):
            st.session_state.edit_name = p['name']
            st.rerun()
        st.write("---")

# --- 6. טאב עדכון/הרשמה ---
with tab3:
    st.subheader("עדכון פרטים")
    all_n = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    target = st.session_state.get('edit_name', "🆕 שחקן חדש")
    choice = st.selectbox("בחר שחקן:", all_n, index=all_n.index(target) if target in all_n else 0)
    p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
    
    with st.form("edit_form"):
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "")
        f_year = st.number_input("שנת לידה:", 1950, 2020, int(p_data['birth_year']) if p_data else 1990)
        roles_list = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
        f_roles = st.pills("תפקידים:", roles_list, selection_mode="multi", default=p_data.get('roles', '').split(',') if p_data and p_data.get('roles') else [])
        f_rate = st.radio("ציון עצמי:", range(1, 11), index=int(p_data.get('rating', 5))-1 if p_data else 4, horizontal=True)
        
        if st.form_submit_button("שמור ✅", use_container_width=True):
            if f_name:
                new_entry = {"name": f_name, "birth_year": f_year, "rating": f_rate, "roles": ",".join(f_roles), "peer_ratings": p_data.get('peer_ratings', '{}') if p_data else '{}'}
                if p_data:
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                    st.session_state.players[idx] = new_entry
                else: st.session_state.players.append(new_entry)
                save_to_gsheets(); st.rerun()
