import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span, div { text-align: right !important; direction: rtl; }
    .block-container { padding: 5px !important; }
    .main-title { font-size: 22px !important; text-align: center !important; font-weight: bold; margin-bottom: 15px; color: #60a5fa; }
    
    .database-card { 
        background: #2d3748; border: 1px solid #4a5568; border-radius: 8px; padding: 12px; margin-bottom: 5px;
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

    [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 5px !important; }
    
    div[data-testid="column"] button {
        background-color: transparent !important;
        color: #60a5fa !important;
        border: none !important;
        padding: 0 !important;
        text-decoration: underline !important;
        font-size: 12px !important;
        height: auto !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר ---
def safe_split(val):
    if not val or pd.isna(val): return []
    return str(val).split(',')

def safe_get_json(val):
    if not val or pd.isna(val): return {}
    if isinstance(val, dict): return val
    try:
        cleaned = str(val).strip()
        return json.loads(cleaned) if cleaned else {}
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
    if not p: return 5.0, 1995, 0
    r = float(p.get('rating', 5.0))
    # שליפת דירוגי עמיתים מכל השחקנים שדירגו את השחקן הזה
    peers_scores = []
    for other_p in st.session_state.players:
        if other_p['name'] == name: continue
        pr = safe_get_json(other_p.get('peer_ratings', '{}'))
        if name in pr:
            peers_scores.append(float(pr[name]))
    
    num_raters = len(peers_scores)
    avg_p = sum(peers_scores)/num_raters if num_raters > 0 else 0
    final_score = (r + avg_p) / 2 if num_raters > 0 else r
    return final_score, int(p.get('birth_year', 1995)), num_raters

# --- 3. ניווט ---
if 'edit_name' not in st.session_state: st.session_state.edit_name = "🆕 שחקן חדש"

st.markdown("<div class='main-title'>⚽ ניהול כדורגל 2026</div>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון/הרשמה"])

# --- 4. טאב חלוקה ---
with tab1:
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected_names = st.pills("מי הגיע?", all_names, selection_mode="multi", key="p_selection")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected_names:
            pool = []
            current_year = 2026
            for n in selected_names:
                s, b, count = get_player_stats(n)
                pool.append({'name': n, 'f': s, 'age': current_year - b, 'raters': count})
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
                    c_txt, c_swp = st.columns([3, 1])
                    with c_txt:
                        # הוספת מספר המדרגים בסוגריים קטנים ליד הציון
                        st.markdown(f"""
                            <div class='p-box'>
                                <span>{p['name']} ({p['age']})</span>
                                <span style='text-align:left;'>
                                    <span style='color:#94a3b8; font-size:10px; margin-left:3px;'>({p['raters']})</span>
                                    <span style='color:#22c55e; font-size:11px; font-weight:bold;'>{p['f']:.1f}</span>
                                </span>
                            </div>
                        """, unsafe_allow_html=True)
                    with c_swp:
                        if st.button("החלף", key=f"sw_{data['pfx']}_{i}"):
                            if data['pfx'] == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                            else: st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()
                if data['team']:
                    avg_f = sum(p['f'] for p in data['team']) / len(data['team'])
                    avg_a = sum(p['age'] for p in data['team']) / len(data['team'])
                    st.markdown(f"<div class='team-stats'><b>רמה: {avg_f:.1f}</b><br>גיל ממוצע: {avg_a:.1f}</div>", unsafe_allow_html=True)

# --- 5. טאב מאגר ---
with tab2:
    st.subheader("ניהול המאגר")
    for i, p in enumerate(st.session_state.players):
        score, birth, count = get_player_stats(p['name'])
        age = 2026 - birth
        st.markdown(f"<div class='database-card'><b>{p['name']}</b> ({age}) | ציון: {score:.1f} <small>({count} מדרגים)</small></div>", unsafe_allow_html=True)
        ce, cd = st.columns([4, 1])
        with ce:
            if st.button(f"📝 עריכה", key=f"db_ed_{i}", use_container_width=True):
                st.session_state.edit_name = p['name']; st.rerun()
        with cd:
            if st.button("🗑️", key=f"db_dl_{i}", use_container_width=True):
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
        f_roles = st.pills("תפקידים:", roles_list, selection_mode="multi", default=safe_split(p_data.get('roles', '')) if p_data else [])
        
        f_rate = st.radio("ציון עצמי (איך אתה מעריך את עצמך):", range(1, 11), index=int(p_data.get('rating', 5))-1 if p_data else 4, horizontal=True)
        
        st.write("---")
        st.write("דירוג עמיתים (דרג שחקנים אחרים):")
        
        # קבלת הדירוגים שניתנו על ידי המשתמש הנוכחי
        peer_res = {}
        exist_p = safe_get_json(p_data.get('peer_ratings', '{}') if p_data else '{}')
        other_p = [p for p in st.session_state.players if p['name'] != f_name]
        
        for op in other_p:
            peer_res[op['name']] = st.radio(
                f"דרג את {op['name']}:", 
                range(1, 11), 
                index=int(exist_p.get(op['name'], 5))-1, 
                horizontal=True, 
                key=f"pr_{f_name}_{op['name']}"
            )

        if st.form_submit_button("שמור ✅", use_container_width=True):
            if f_name:
                new_entry = {
                    "name": f_name, 
                    "birth_year": f_year, 
                    "rating": f_rate, 
                    "roles": ",".join(f_roles), 
                    "peer_ratings": json.dumps(peer_res)
                }
                if p_data:
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                    st.session_state.players[idx] = new_entry
                else:
                    st.session_state.players.append(new_entry)
                
                save_to_gsheets()
                st.session_state.edit_name = f_name
                st.rerun()
