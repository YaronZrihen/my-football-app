import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. הגדרות ועיצוב CSS ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span { text-align: right !important; direction: rtl; }
    .block-container { padding: 5px !important; }
    .main-title { font-size: 22px !important; text-align: center !important; font-weight: bold; margin-bottom: 15px; color: #60a5fa; }
    
    .database-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 5px;
        text-align: right;
    }
    .card-title { font-size: 18px; font-weight: bold; color: #60a5fa; }
    
    /* כפתורי מאגר 80/20 */
    .stButton button { width: 100%; height: 40px; }
    
    /* עיצוב רדיו בשורה */
    div[role="radiogroup"] { flex-direction: row !important; gap: 10px !important; justify-content: flex-start; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ---
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
    pr_raw = p.get('peer_ratings', '{}')
    try:
        pr = json.loads(pr_raw) if isinstance(pr_raw, str) else pr_raw
    except:
        pr = {}
    peers = [float(v) for v in pr.values()] if isinstance(pr, dict) else []
    avg_p = sum(peers)/len(peers) if peers else 0
    return (r + avg_p) / 2 if avg_p > 0 else r, int(p.get('birth_year', 1995))

# --- 3. ניהול ניווט (גרסה יציבה ללא Pills לניווט ראשי) ---
if 'page' not in st.session_state:
    st.session_state.page = "חלוקה"
if 'edit_name' not in st.session_state:
    st.session_state.edit_name = "🆕 שחקן חדש"

st.markdown("<div class='main-title'>⚽ ניהול כדורגל</div>", unsafe_allow_html=True)

# שימוש ב-Tabs במקום Pills לניווט ראשי למניעת שגיאות בשרת
tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון/הרשמה"])

# לוגיקת מעבר בין טאבים (במקרה של עריכה)
# אם לחצו על עריכה, ה-state ישתנה והקוד ידע לאן ללכת

# --- 4. טאב חלוקה ---
with tab1:
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected = st.multiselect(f"מי הגיע? ({len(all_names)})", all_names)

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
        c1, c2 = st.columns(2)
        for col, team, label in zip([c1, c2], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"]):
            with col:
                st.subheader(f"{label} ({len(team)})")
                for p in team:
                    st.markdown(f"<div style='background:#2d3748; padding:5px; border-radius:5px; margin-bottom:2px;'>{p['name']} ({p['f']:.1f})</div>", unsafe_allow_html=True)

# --- 5. טאב מאגר שחקנים ---
with tab2:
    st.subheader("ניהול המאגר")
    for i, p in enumerate(st.session_state.players):
        score, birth = get_player_stats(p['name'])
        st.markdown(f"""
            <div class='database-card'>
                <div class='card-title'>{p['name']}</div>
                <div class='card-detail'>גיל: {2026 - birth} | ציון: {score:.1f}</div>
                <div class='card-detail'>תפקידים: {p.get('roles', '')}</div>
            </div>
        """, unsafe_allow_html=True)
        
        col_edit, col_del = st.columns([4, 1])
        with col_edit:
            # הדרך הכי בטוחה לערוך ב-Tabs
            if st.button(f"📝 עריכת {p['name']}", key=f"ed_{i}"):
                st.session_state.edit_name = p['name']
                st.info(f"השחקן {p['name']} נבחר. עבור ללשונית 'עדכון/הרשמה' לביצוע השינויים.")
        with col_del:
            if st.button("🗑️", key=f"dl_{i}"):
                st.session_state.players.pop(i)
                save_to_gsheets()
                st.rerun()
        st.markdown("---")

# --- 6. טאב עדכון/הרשמה ---
with tab3:
    st.subheader("עדכון פרטים")
    names_list = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    
    # בחירת השחקן (נטען אוטומטית אם נלחץ 'עריכה')
    target = st.session_state.get('edit_name', "🆕 שחקן חדש")
    if target not in names_list: target = "🆕 שחקן חדש"
    
    choice = st.selectbox("בחר שחקן:", names_list, index=names_list.index(target))
    
    with st.form("edit_form"):
        p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "")
        f_year = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
        
        roles_list = ["שוער", "בלם", "מגן", "קשר אחורי", "קשר קדמי", "כנף", "חלוץ"]
        # שימוש ב-multiselect במקום pills למניעת שגיאות גרסה
        f_roles = st.multiselect("תפקידים:", roles_list, default=p_data.get('roles', '').split(',') if p_data and p_data.get('roles') else [])
        
        f_rate = st.radio("ציון עצמי (1-10):", range(1, 11), index=int(p_data.get('rating', 5))-1, horizontal=True)
        
        st.write("---")
        st.write("דירוג שחקנים אחרים:")
        other_players = [p for p in st.session_state.players if p['name'] != f_name]
        peer_results = {}
        
        # טעינת דירוגי עמיתים קיימים
        existing_raw = p_data.get('peer_ratings', '{}') if p_data else '{}'
        try:
            existing_peers = json.loads(existing_raw) if isinstance(existing_raw, str) else existing_raw
        except:
            existing_peers = {}

        for op in other_players:
            op_name = op['name']
            curr_val = existing_peers.get(op_name, 5)
            peer_results[op_name] = st.radio(f"ציון ל{op_name}:", range(1, 11), index=int(curr_val)-1, horizontal=True, key=f"pr_{op_name}")

        if st.form_submit_button("שמור שינויים ✅", use_container_width=True):
            if f_name:
                updated_entry = {
                    "name": f_name, 
                    "birth_year": f_year, 
                    "rating": f_rate, 
                    "roles": ",".join(f_roles), 
                    "peer_ratings": json.dumps(peer_results)
                }
                if p_data:
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                    st.session_state.players[idx] = updated_entry
                else:
                    st.session_state.players.append(updated_entry)
                save_to_gsheets()
                st.session_state.edit_name = f_name
                st.success("הנתונים נשמרו בהצלחה!")
                st.rerun()
