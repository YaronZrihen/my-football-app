import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS (חזרה למקור שלך בלבד) ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span, div { text-align: right !important; direction: rtl; }
    .block-container { padding: 10px !important; }
    .main-title { font-size: 22px !important; text-align: center !important; font-weight: bold; margin-bottom: 15px; color: #60a5fa; }
    
    .database-card { 
        background: #2d3748; border: 1px solid #4a5568; border-radius: 8px; padding: 12px; margin-bottom: 5px;
    }
    
    div[data-testid="stPills"] button { background-color: #4a5568 !important; color: white !important; border-radius: 20px !important; }
    div[data-testid="stPills"] button[aria-checked="true"] { background-color: #60a5fa !important; border: 1px solid white !important; }

    .team-stats {
        background: #1e293b; border-top: 2px solid #4a5568; padding: 8px;
        margin-top: 5px; font-size: 12px; text-align: center; border-radius: 0 0 8px 8px;
    }
    
    /* מניעת גלישה רוחבית בסיסית */
    .stHorizontalBlock { gap: 5px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר (המקור שלך) ---
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

# --- 3. ניווט ---
if 'edit_name' not in st.session_state: st.session_state.edit_name = "🆕 שחקן חדש"

st.markdown("<div class='main-title'>⚽ ניהול כדורגל 2026</div>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון/הרשמה"])

# --- 4. טאב חלוקה ---
with tab1:
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected_names = st.pills("מי משחק?", all_names, selection_mode="multi", key="p_selection")

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
        teams = [{"team": st.session_state.t1, "label": "⚪ לבן", "pfx": "w"}, {"team": st.session_state.t2, "label": "⚫ שחור", "pfx": "b"}]
        
        for col, data in zip([col_w, col_b], teams):
            with col:
                st.markdown(f"<p style='text-align:center; font-weight:bold;'>{data['label']}</p>", unsafe_allow_html=True)
                for i, p in enumerate(data['team']):
                    # כאן התיקון: שימוש ב-Container במקום Column פנימי שגורם ל-Wide
                    with st.container(border=True):
                        st.write(f"**{p['name']}**")
                        cols = st.columns([1, 1])
                        cols[0].write(f"⭐{p['f']:.1f}")
                        if cols[1].button("🔄", key=f"sw_{data['pfx']}_{i}"):
                            if data['pfx'] == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                            else: st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()
                if data['team']:
                    avg_f = sum(p['f'] for p in data['team']) / len(data['team'])
                    st.markdown(f"<div class='team-stats'><b>רמה: {avg_f:.1f}</b></div>", unsafe_allow_html=True)

# --- 5. טאב מאגר ---
with tab2:
    st.subheader("ניהול המאגר")
    for i, p in enumerate(st.session_state.players):
        score, birth = get_player_stats(p['name'])
        with st.container(border=True):
            st.write(f"**{p['name']}** ({2026-birth}) | ציון: {score:.1f}")
            c1, c2 = st.columns(2)
            if c1.button("📝 עריכה", key=f"db_ed_{i}"):
                st.session_state.edit_name = p['name']; st.rerun()
            if c2.button("🗑️", key=f"db_dl_{i}"):
                st.session_state.players.pop(i); save_to_gsheets(); st.rerun()

# --- 6. טאב עדכון/הרשמה ---
with tab3:
    st.subheader("עדכון פרטים")
    all_n = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    choice = st.selectbox("בחר שחקן:", all_n, index=all_n.index(st.session_state.edit_name) if st.session_state.edit_name in all_n else 0)
    p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
    
    with st.form("edit_form"):
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "")
        f_year = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
        roles_list = ["שוער", "בלם", "מגן", "קשר אחורי", "קשר קדמי", "כנף", "חלוץ"]
        f_roles = st.pills("תפקידים:", roles_list, selection_mode="multi")
        f_rate = st.radio("ציון:", range(1, 11), index=int(p_data.get('rating', 5))-1 if p_data else 4, horizontal=True)
        
        if st.form_submit_button("שמור ✅", use_container_width=True):
            if f_name:
                roles_str = ",".join(f_roles) if f_roles else ""
                new_entry = {"name": f_name, "birth_year": f_year, "rating": f_rate, "roles": roles_str}
                if p_data:
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                    st.session_state.players[idx] = new_entry
                else: st.session_state.players.append(new_entry)
                save_to_gsheets(); st.rerun()
