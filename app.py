import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. הגדרות ועיצוב CSS (RTL, עיצוב כרטיסים וכפתורים) ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span { text-align: right !important; direction: rtl; }
    .block-container { padding: 5px !important; }
    .main-title { font-size: 22px !important; text-align: center !important; font-weight: bold; margin-bottom: 15px; color: #60a5fa; }
    
    /* כרטיס שחקן במאגר */
    .database-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 5px;
        text-align: right;
    }
    .card-title { font-size: 18px; font-weight: bold; color: #60a5fa; }
    .card-detail { font-size: 14px; color: #cbd5e0; }

    /* עיצוב כפתורי Pills (בחירת שחקנים) */
    div[data-testid="stPills"] button {
        background-color: #4a5568 !important;
        color: white !important;
        border-radius: 20px !important;
        border: 1px solid #4a5568 !important;
    }
    div[data-testid="stPills"] button[aria-checked="true"] {
        background-color: #60a5fa !important;
        border: 1px solid white !important;
        color: white !important;
    }

    /* עיצוב שורת שחקן בקבוצות */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 4px 10px;
        margin-bottom: 3px;
        font-size: 14px;
    }
    
    /* יישור רדיו (ציון עמיתים) */
    div[role="radiogroup"] { flex-direction: row !important; gap: 10px !important; justify-content: flex-start; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר להגנה על הקוד ---
def safe_split(val):
    if not val or pd.isna(val): return []
    return str(val).split(',')

def safe_get_json(val):
    if not val or pd.isna(val): return {}
    if isinstance(val, dict): return val
    try: return json.loads(str(val))
    except: return {}

# --- 3. חיבור ל-Google Sheets וטעינה ---
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

# --- 4. ניהול ניווט ושחקן נבחר לעריכה ---
if 'edit_name' not in st.session_state:
    st.session_state.edit_name = "🆕 שחקן חדש"

st.markdown("<div class='main-title'>⚽ ניהול כדורגל 2026</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון/הרשמה"])

# --- 5. טאב חלוקה (אלגוריתם חלוקה) ---
with tab1:
    all_names = sorted([p['name'] for p in st.session_state.players])
    
    # בחירת שחקנים באמצעות Pills (כפתורי בחירה)
    selected_players = st.pills(
        f"מי הגיע היום? ({len(st.session_state.get('p_selection', []))})", 
        all_names, 
        selection_mode="multi", 
        key="p_selection"
    )

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected_players:
            pool = []
            curr_y = 2026
            for n in selected_players:
                s, b = get_player_stats(n)
                pool.append({'name': n, 'f': s, 'age': curr_y - b})
            
            # מיון לפי רמה
            pool.sort(key=lambda x: x['f'], reverse=True)
            
            # חלוקת נחש (Snake Draft) לאיזון מקסימלי
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    # הצגת הקבוצות
    if 't1' in st.session_state and selected_players:
        st.write("---")
        c1, c2 = st.columns(2)
        for col, team, label in zip([c1, c2], [st.session_state.t1, st.session_state.t2], ["⚪ קבוצה לבנה", "⚫ קבוצה שחורה"]):
            with col:
                st.markdown(f"<h3 style='text-align:center;'>{label}</h3>", unsafe_allow_html=True)
                for p in team:
                    st.markdown(f"<div class='p-box'>{p['name']} <small>(ציון: {p['f']:.1f})</small></div>", unsafe_allow_html=True)

# --- 6. טאב מאגר שחקנים (ניהול רשימה) ---
with tab2:
    st.subheader("ניהול המאגר")
    curr_year = 2026
    for i, p in enumerate(st.session_state.players):
        score, birth = get_player_stats(p['name'])
        st.markdown(f"""
            <div class='database-card'>
                <div class='card-title'>{p['name']}</div>
                <div class='card-detail'>גיל: {curr_year - birth} | ציון משוקלל: {score:.1f}</div>
                <div class='card-detail'>תפקידים: {p.get('roles', 'לא הוגדר')}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # כפתורי פעולה 80/20 בשורה אחת
        col_edit, col_del = st.columns([4, 1])
        with col_edit:
            if st.button(f"📝 עריכת {p['name']}", key=f"btn_ed_{i}"):
                st.session_state.edit_name = p['name']
                st.info(f"נבחרה העריכה עבור {p['name']}. עבור לטאב 'עדכון/הרשמה'.")
        with col_del:
            if st.button("🗑️", key=f"btn_dl_{i}"):
                st.session_state.players.pop(i)
                save_to_gsheets()
                st.rerun()
        st.markdown("---")

# --- 7. טאב עדכון/הרשמה (טופס ודירוג עמיתים) ---
with tab3:
    st.subheader("עדכון פרטים ורישום")
    all_names_plus_new = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    
    # סנכרון עם בחירת העריכה מהמאגר
    target = st.session_state.get('edit_name', "🆕 שחקן חדש")
    if target not in all_names_plus_new: target = "🆕 שחקן חדש"
    
    choice = st.selectbox("בחר שחקן לעריכה או רישום:", all_names_plus_new, index=all_names_plus_new.index(target))
    
    with st.form("edit_form"):
        p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
        
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "")
        f_year = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
        
        roles_list = ["שוער", "בלם", "מגן", "קשר אחורי", "קשר קדמי", "כנף", "חלוץ"]
        existing_roles = safe_split(p_data.get('roles', '')) if p_data else []
        f_roles = st.multiselect("תפקידים:", roles_list, default=[r for r in existing_roles if r in roles_list])
        
        f_rate = st.radio("ציון עצמי (1-10):", range(1, 11), index=int(p_data.get('rating', 5))-1 if p_data else 4, horizontal=True)
        
        st.write("---")
        st.write("דרג שחקנים אחרים (Peer Rating):")
        other_players = [p for p in st.session_state.players if p['name'] != f_name]
        peer_results = {}
        existing_peers = safe_get_json(p_data.get('peer_ratings', '{}') if p_data else '{}')

        for op in other_players:
            op_name = op['name']
            curr_val = existing_peers.get(op_name, 5)
            peer_results[op_name] = st.radio(f"ציון ל{op_name}:", range(1, 11), index=int(curr_val)-1, horizontal=True, key=f"pr_{op_name}")

        if st.form_submit_button("שמור שינויים במערכת ✅", use_container_width=True):
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
                st.session_state.edit_name = f_name
                st.success(f"הנתונים של {f_name} נשמרו!")
                st.rerun()
