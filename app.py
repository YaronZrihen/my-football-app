import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב CSS מעודכן (מאגר משופר) ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span { text-align: right !important; direction: rtl; }
    .block-container { padding: 5px !important; }

    .main-title { font-size: 18px !important; text-align: center !important; font-weight: bold; margin-bottom: 10px; color: #60a5fa; }
    
    /* כרטיס מאגר משופר */
    .database-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 5px;
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
    }
    .card-title { font-size: 16px; font-weight: bold; color: #60a5fa; }
    .card-detail { font-size: 13px; color: #cbd5e0; }

    /* כפתורים בתוך המאגר */
    .db-btns { display: flex; gap: 10px; margin-top: 8px; }
    
    /* נעילת 2 עמודות בסלולר (חלוקה) */
    .team-section [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    .team-section [data-testid="column"] {
        flex: 1 1 50% !important;
        min-width: 45% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ונתונים ---
def parse_peer_ratings(val):
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

def save_data():
    df = pd.DataFrame(st.session_state.players)
    conn.update(data=df)
    st.cache_data.clear()

def get_player_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 1995
    r = float(p.get('rating', 5.0))
    pr = parse_peer_ratings(p.get('peer_ratings', '{}'))
    peers = [float(v) for v in pr.values()]
    avg_p = sum(peers)/len(peers) if peers else 0
    return (r + avg_p) / 2 if avg_p > 0 else r, int(p.get('birth_year', 1995))

# --- 3. תפריט ---
st.markdown("<div class='main-title'>⚽ ניהול כדורגל</div>", unsafe_allow_html=True)
if 'menu_idx' not in st.session_state: st.session_state.menu_idx = "חלוקה"

menu = st.pills("תפריט", ["חלוקה", "מאגר שחקנים", "עדכון/הרשמה"], default=st.session_state.menu_idx)

# --- 4. דף חלוקה ---
if menu == "חלוקה":
    all_names = sorted([p['name'] for p in st.session_state.players])
    sel_count = len(st.session_state.get('p_sel', []))
    selected = st.pills(f"מי הגיע? ({sel_count})", all_names, selection_mode="multi", key="p_sel")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            curr_y = 2026
            for n in selected:
                s, b = get_player_stats(n)
                pool.append({'name': n, 'f': s, 'age': curr_y - b})
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
                    st.markdown(f"<div class='p-box' style='background:#2d3748; border:1px solid #4a5568; border-radius:4px; padding:2px 8px; margin-bottom:2px; height:26px; display:flex; align-items:center;'><span style='font-size:12px;'>{p['name']} <span style='color:#22c55e; font-size:10px;'>({p['f']:.1f})</span></span></div>", unsafe_allow_html=True)
                    if st.button("🔄", key=f"m_{pfx}_{i}"):
                        if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                        else: st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- 5. דף מאגר (עם עריכה ומחיקה לשמאל) ---
elif menu == "מאגר שחקנים":
    st.subheader("🗄️ ניהול שחקנים")
    curr_year = 2026
    for i, p in enumerate(st.session_state.players):
        score, birth = get_player_stats(p['name'])
        age = curr_year - birth
        
        with st.container():
            # מבנה כרטיס עם מחיקה בצד שמאל
            col_content, col_del = st.columns([5, 1])
            with col_content:
                st.markdown(f"""
                    <div class='database-card'>
                        <div class='card-title'>{p['name']}</div>
                        <div class='card-detail'>גיל: {age} | ציון: {score:.1f}</div>
                        <div class='card-detail'>תפקידים: {p.get('roles', 'לא הוגדר')}</div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"📝 ערוך את {p['name']}", key=f"edit_btn_{i}", use_container_width=True):
                    st.session_state.edit_player = p['name']
                    # מעבר אוטומטי לטאב עדכון
                    st.session_state.menu_idx = "עדכון/הרשמה"
                    st.rerun()
            with col_del:
                st.write("") # ריוח קטן
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.players.pop(i)
                    save_data()
                    st.rerun()

# --- 6. דף עדכון/הרשמה ---
elif menu == "עדכון/הרשמה":
    st.subheader("📝 עדכון פרטים")
    names = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    
    # בדיקה אם הגענו מכפתור "עריכה" במאגר
    default_choice = st.session_state.get('edit_player', "🆕 שחקן חדש")
    if default_choice not in names: default_choice = "🆕 שחקן חדש"
    
    choice = st.selectbox("בחר שחקן:", names, index=names.index(default_choice))
    
    with st.form("edit_form"):
        p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "")
        f_year = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
        
        roles_list = ["שוער", "בלם", "מגן", "קשר אחורי", "קשר קדמי", "כנף", "חלוץ"]
        current_roles = p_data.get('roles', []) if p_data else []
        if isinstance(current_roles, str): current_roles = current_roles.split(',')
        f_roles = st.pills("תפקידים:", roles_list, selection_mode="multi", default=current_roles)
        
        f_rate = st.radio("דירוג עצמי (1-10):", options=range(1, 11), 
                         index=int(p_data['rating'])-1 if p_data else 4, horizontal=True)
        
        st.write("---")
        st.write("דרג שחקנים אחרים:")
        other_players = [p for p in st.session_state.players if p['name'] != f_name]
        peer_ratings_input = {}
        existing_peers = parse_peer_ratings(p_data.get('peer_ratings', '{}') if p_data else '{}')

        for op in other_players:
            op_name = op['name']
            current_val = existing_peers.get(op_name, 5)
            st.markdown(f"<div style='border-bottom:1px solid #4a5568; padding:5px 0;'>", unsafe_allow_html=True)
            peer_ratings_input[op_name] = st.radio(f"ציון ל{op_name}:", options=range(1, 11), 
                                                 index=int(current_val)-1, horizontal=True, key=f"pr_{op_name}")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.form_submit_button("שמור שינויים ✅", use_container_width=True):
            if f_name:
                updated_p = {
                    "name": f_name, "birth_year": f_year, "rating": f_rate, 
                    "roles": ",".join(f_roles), "peer_ratings": json.dumps(peer_ratings_input)
                }
                if p_data:
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                    st.session_state.players[idx] = updated_p
                else: st.session_state.players.append(updated_p)
                save_data()
                st.session_state.edit_player = f_name
                st.success("נשמר!")
                st.rerun()
