import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime

# --- 1. הגדרות דף ועיצוב CSS (RTL, צפיפות, נעילת עמודות) ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span { text-align: right !important; direction: rtl; }
    .block-container { padding: 5px !important; }

    .main-title { font-size: 18px !important; text-align: center !important; font-weight: bold; margin-bottom: 10px; color: #60a5fa; }
    
    /* כרטיס שחקן במאגר */
    .database-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 5px;
        text-align: right;
    }
    .card-title { font-size: 16px; font-weight: bold; color: #60a5fa; margin-bottom: 2px; }
    .card-detail { font-size: 13px; color: #cbd5e0; margin-bottom: 2px; }

    /* עיצוב כפתורי מאגר 80/20 */
    div[data-testid="column"] button {
        width: 100% !important;
        padding: 4px !important;
        height: 35px !important;
    }

    /* שורת שחקן צפופה בחלוקה */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 2px 8px;
        margin-bottom: 2px;
        display: flex;
        justify-content: flex-start;
        align-items: center;
        height: 26px;
    }
    
    /* רדיו אופקי */
    div[role="radiogroup"] { flex-direction: row !important; gap: 8px !important; justify-content: flex-start; }
    .peer-row { border-bottom: 1px solid #4a5568; padding: 8px 0; }

    /* נעילת 2 עמודות בסלולר */
    .team-section [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר ונתונים ---
def parse_json_safe(val):
    if not val or pd.isna(val): return {}
    if isinstance(val, dict): return val
    try: return json.loads(val)
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
    pr = parse_json_safe(p.get('peer_ratings', '{}'))
    peers = [float(v) for v in pr.values()]
    avg_p = sum(peers)/len(peers) if peers else 0
    final_score = (r + avg_p) / 2 if avg_p > 0 else r
    return final_score, int(p.get('birth_year', 1995))

# --- 3. ניהול ניווט (פתרון השגיאה) ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = "חלוקה"
if 'player_to_edit' not in st.session_state:
    st.session_state.player_to_edit = "🆕 שחקן חדש"

st.markdown("<div class='main-title'>⚽ ניהול כדורגל</div>", unsafe_allow_html=True)

menu_options = ["חלוקה", "מאגר שחקנים", "עדכון/הרשמה"]
try:
    def_idx = menu_options.index(st.session_state.current_page)
except:
    def_idx = 0

menu = st.pills("תפריט", menu_options, index=def_idx)

if menu and menu != st.session_state.current_page:
    st.session_state.current_page = menu
    st.rerun()

# --- 4. דף חלוקה ---
if st.session_state.current_page == "חלוקה":
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected = st.pills(f"מי הגיע? ({len(st.session_state.get('p_sel', []))})", all_names, selection_mode="multi", key="p_sel")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            for n in selected:
                s, b = get_player_stats(n)
                pool.append({'name': n, 'f': s, 'age': 2026 - b})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        st.markdown("<div class='team-section'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        for col, team, label, pfx in zip([c1, c2], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"], ["w", "b"]):
            with col:
                st.markdown(f"<p style='text-align:center;font-size:12px;font-weight:bold;'>{label} ({len(team)})</p>", unsafe_allow_html=True)
                for i, p in enumerate(team):
                    st.markdown(f"<div class='p-box'><span style='font-size:12px;'>{p['name']} <span style='color:#22c55e; font-size:10px;'>({p['f']:.1f})</span></span></div>", unsafe_allow_html=True)
                    if st.button("🔄", key=f"m_{pfx}_{i}"):
                        if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                        else: st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- 5. דף מאגר שחקנים (עריכה ומחיקה 80/20) ---
elif st.session_state.current_page == "מאגר שחקנים":
    st.subheader("🗄️ ניהול שחקנים")
    for i, p in enumerate(st.session_state.players):
        score, birth = get_player_stats(p['name'])
        st.markdown(f"""
            <div class='database-card'>
                <div class='card-title'>{p['name']}</div>
                <div class='card-detail'>גיל: {2026 - birth} | ציון משוקלל: {score:.1f}</div>
                <div class='card-detail'>תפקידים: {p.get('roles', 'לא הוגדר')}</div>
            </div>
        """, unsafe_allow_html=True)
        
        col_edit, col_del = st.columns([4, 1])
        with col_edit:
            if st.button(f"📝 עריכת {p['name']}", key=f"ed_{i}"):
                st.session_state.player_to_edit = p['name']
                st.session_state.current_page = "עדכון/הרשמה"
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"dl_{i}"):
                st.session_state.players.pop(i)
                save_to_gsheets()
                st.rerun()
        st.markdown("---")

# --- 6. דף עדכון/הרשמה (דירוג פתוח) ---
elif st.session_state.current_page == "עדכון/הרשמה":
    st.subheader("📝 עדכון פרטים")
    names_list = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    
    target = st.session_state.player_to_edit
    idx_to_show = names_list.index(target) if target in names_list else 0
    
    choice = st.selectbox("בחר שחקן:", names_list, index=idx_to_show)
    
    with st.form("edit_form"):
        p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "")
        f_year = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
        
        roles_all = ["שוער", "בלם", "מגן", "קשר אחורי", "קשר קדמי", "כנף", "חלוץ"]
        curr_r = p_data.get('roles', "") if p_data else ""
        curr_r_list = curr_r.split(',') if isinstance(curr_r, str) and curr_r else []
        f_roles = st.pills("תפקידים:", roles_all, selection_mode="multi", default=curr_r_list)
        
        f_rate = st.radio("דירוג עצמי (1-10):", range(1, 11), index=int(p_data.get('rating', 5))-1, horizontal=True)
        
        st.write("---")
        st.write("דרג שחקנים אחרים:")
        other_players = [p for p in st.session_state.players if p['name'] != f_name]
        peer_results = {}
        existing_peers = parse_json_safe(p_data.get('peer_ratings', '{}') if p_data else '{}')

        for op in other_players:
            op_name = op['name']
            curr_val = existing_peers.get(op_name, 5)
            st.markdown(f"<div class='peer-row'>", unsafe_allow_html=True)
            peer_results[op_name] = st.radio(f"ציון ל{op_name}:", range(1, 11), index=int(curr_val)-1, horizontal=True, key=f"pr_{op_name}")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.form_submit_button("שמור שינויים ✅", use_container_width=True):
            if f_name:
                updated_entry = {
                    "name": f_name, "birth_year": f_year, "rating": f_rate, 
                    "roles": ",".join(f_roles), "peer_ratings": json.dumps(peer_results)
                }
                if p_data:
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                    st.session_state.players[idx] = updated_entry
                else:
                    st.session_state.players.append(updated_entry)
                save_to_gsheets()
                st.session_state.player_to_edit = f_name
                st.success("הנתונים נשמרו!")
                st.rerun()

# איפוס עריכה כשיוצאים מהדף
if st.session_state.current_page != "עדכון/הרשמה":
    st.session_state.player_to_edit = "🆕 שחקן חדש"
