import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime, date

# --- 1. הגדרות דף ועיצוב CSS ---
st.set_page_config(page_title="ניהול כדורגל וולפסון חולון", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;} .stDeployButton {display:none;}
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span, div { text-align: right !important; direction: rtl; }
    .wolfson-title { font-size: 28px !important; text-align: center !important; color: #60a5fa; font-weight: bold; margin-bottom: 20px; }
    .admin-zone { background: #1e293b; padding: 15px; border-radius: 10px; border: 1px dashed #60a5fa; margin-bottom: 20px; }
    .player-card { background: #2d3748; border: 1px solid #4a5568; border-radius: 12px; padding: 15px; margin-bottom: 15px; }
    .card-header { font-size: 20px; font-weight: bold; color: #f8fafc; border-bottom: 1px solid #4a5568; padding-bottom: 8px; margin-bottom: 10px; }
    .card-row { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 14px; }
    .label { color: #94a3b8; }
    .highlight-value { color: #22c55e; font-weight: bold; }
    .p-box { background: #2d3748; border: 1px solid #4a5568; border-radius: 4px; padding: 5px 10px; margin-bottom: 2px; display: flex; justify-content: space-between; }
    .arrival-card { background: #2d3748; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-right: 4px solid #3b82f6; display: flex; justify-content: space-between; align-items: center; }
    .paid-status { color: #22c55e; font-weight: bold; }
    .unpaid-status { color: #ef4444; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור נתונים ופונקציות עזר ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_split(val):
    if not val or pd.isna(val): return []
    return [s.strip() for s in str(val).split(',') if s.strip()]

def safe_get_json(val):
    if not val or pd.isna(val): return {}
    if isinstance(val, dict): return val
    try:
        cleaned = str(val).strip()
        if cleaned.startswith("'") and cleaned.endswith("'"): cleaned = cleaned[1:-1]
        return json.loads(cleaned) if cleaned else {}
    except: return {}

# טעינת מאגר שחקנים (Sheet1)
if 'players' not in st.session_state:
    try:
        df = conn.read(worksheet="Sheet1", ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

# טעינת היסטוריית הגעה (arrivals_history)
def load_arrivals_history():
    try:
        return conn.read(worksheet="arrivals_history", ttl="0").dropna(subset=['name'])
    except:
        return pd.DataFrame(columns=['name', 'phone', 'arrival_time', 'match_date', 'paid'])

def save_players_to_gsheets():
    df = pd.DataFrame(st.session_state.players)
    conn.update(worksheet="Sheet1", data=df)
    st.cache_data.clear()

def get_player_full_stats(p):
    name = p['name']
    age = 2026 - int(p.get('birth_year', 1990))
    self_rating = float(p.get('rating', 0))
    peer_scores = []
    for voter in st.session_state.players:
        v_ratings = safe_get_json(voter.get('peer_ratings', '{}'))
        if name in v_ratings and v_ratings[name] > 0:
            peer_scores.append(float(v_ratings[name]))
    avg_peer = sum(peer_scores) / len(peer_scores) if peer_scores else 0
    final = round((self_rating + avg_peer) / 2, 1) if (self_rating and avg_peer) else (self_rating or avg_peer or 5.0)
    return {"final": final, "age": age, "self": self_rating, "peer": round(avg_peer, 1), "count": len(peer_scores)}

# --- 3. ממשק משתמש וטאבים ---
st.markdown("<div class='wolfson-title'>ניהול כדורגל וולפסון חולון</div>", unsafe_allow_html=True)

if 'edit_name' not in st.session_state: st.session_state.edit_name = "🆕 שחקן חדש"
tab_arrival, tab_split, tab_db, tab_edit = st.tabs(["✅ אישורי הגעה", "🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 רישום ועדכון"])

# --- טאב 1: אישורי הגעה ---
with tab_arrival:
    with st.expander("🛠️ הגדרות מנהל - תאריך מחזור"):
        m_date = st.date_input("קבע תאריך למחזור הקרוב:", value=date.today())
        m_date_str = m_date.strftime("%d/%m/%Y")
        st.info(f"הרישומים כעת עבור: {m_date_str}")

    st.subheader(f"רישום למחזור {m_date_str}")
    all_p_names = sorted([p['name'] for p in st.session_state.players])
    
    with st.form("arrival_form"):
        u_name = st.selectbox("בחר שם מהמאגר:", [""] + all_p_names)
        u_phone = st.text_input("מספר פלאפון:")
        if st.form_submit_button("אשר הגעה ✅", use_container_width=True):
            if u_name and u_phone:
                h_df = load_arrivals_history()
                if not ((h_df['name'] == u_name) & (h_df['match_date'] == m_date_str)).any():
                    new_row = pd.DataFrame([{"name": u_name, "phone": u_phone, "arrival_time": datetime.now().strftime("%H:%M"), "match_date": m_date_str, "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new_row], ignore_index=True))
                    st.success(f"נרשמת למחזור {m_date_str}!")
                    st.cache_data.clear()
                else: st.warning("אתה כבר רשום למחזור זה.")
            else: st.error("חובה למלא שם וטלפון.")

    st.write("---")
    st.subheader(f"רשימת מתייצבים - {m_date_str}")
    h_df = load_arrivals_history()
    daily = h_df[h_df['match_date'] == m_date_str]
    st.write(f"רשומים: **{len(daily)}** שחקנים")
    for _, r in daily.iterrows():
        st.markdown(f"<div class='arrival-card'><div><b>{r['name']}</b><br><small>{r['phone']}</small></div><div class='{'paid-status' if r['paid']=='כן' else 'unpaid-status'}'>{'שולם' if r['paid']=='כן' else 'לא שולם'}</div></div>", unsafe_allow_html=True)

# --- טאב 2: חלוקה ---
with tab_split:
    h_df = load_arrivals_history()
    today_registered = h_df[h_df['match_date'] == m_date_str]['name'].tolist()
    
    selected_names = st.pills("מי משחק?", all_p_names, selection_mode="multi", default=today_registered)
    st.write(f"נבחרו: **{len(selected_names)}** שחקנים")
    
    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected_names:
            pool = []
            for n in selected_names:
                p = next(x for x in st.session_state.players if x['name'] == n)
                s = get_player_full_stats(p)
                pool.append({'name': n, 'f': s['final'], 'age': s['age']})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected_names:
        c1, c2 = st.columns(2)
        for col, team, label in zip([c1, c2], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"]):
            with col:
                st.markdown(f"<p style='text-align:center; font-weight:bold;'>{label} ({len(team)})</p>", unsafe_allow_html=True)
                for p in team:
                    st.markdown(f"<div class='p-box'><span>{p['name']} ({p['age']})</span><span><b>{p['f']}</b></span></div>", unsafe_allow_html=True)

# --- טאב 3: מאגר שחקנים ---
with tab_db:
    st.write(f"סה\"כ במאגר: **{len(st.session_state.players)}**")
    for i, p in enumerate(st.session_state.players):
        s = get_player_full_stats(p)
        roles = safe_split(p.get('roles', ''))
        st.markdown(f"""<div class='player-card'><div class='card-header'>{p['name']}</div>
        <div class='card-row'><span class='label'>גיל:</span><span>{s['age']}</span></div>
        <div class='card-row'><span class='label'>ציון סופי:</span><span class='highlight-value'>{s['final']}</span></div>
        <div class='card-row'><span class='label'>דירוגים:</span><span>עצמי: {s['self']} | חברים: {s['peer']} ({s['count']})</span></div></div>""", unsafe_allow_html=True)
        if st.button("📝 עריכה", key=f"edit_btn_{i}"):
            st.session_state.edit_name = p['name']; st.rerun()

# --- טאב 4: רישום ועדכון (הקוד המלא לטופס) ---
with tab_edit:
    all_options = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    choice = st.selectbox("בחר שחקן לעדכון או הוסף חדש:", all_options, index=all_options.index(st.session_state.edit_name) if st.session_state.edit_name in all_options else 0)
    p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
    
    with st.form("main_edit_form"):
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "").strip()
        f_year = st.number_input("שנת לידה:", 1900, 2026, int(p_data['birth_year']) if p_data else 1990)
        roles_list = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
        f_roles = st.pills("תפקידים:", roles_list, selection_mode="multi", default=[r for r in safe_split(p_data.get('roles', '')) if r in roles_list] if p_data else [])
        f_rate = st.radio("ציון עצמי (1-10):", [0]+list(range(1,11)), index=int(p_data.get('rating',0)) if p_data else 0, horizontal=True)
        
        st.write("---")
        st.subheader("דירוג עמיתים (דרג את חבריך לקבוצה):")
        peer_results = {}
        others = [p for p in st.session_state.players if p['name'] != (f_name or choice)]
        for idx, op in enumerate(others):
            curr_v = safe_get_json(p_data.get('peer_ratings', '{}') if p_data else '{}').get(op['name'], 0)
            peer_results[op['name']] = st.radio(f"דרג את {op['name']}:", [0]+list(range(1,11)), index=int(curr_v), horizontal=True, key=f"p_rate_{idx}")

        if st.form_submit_button("שמור שינויים במאגר ✅", use_container_width=True):
            if f_name:
                now = datetime.now().strftime("%d/%m/%Y %H:%M")
                new_entry = {
                    "name": f_name, "birth_year": f_year, "rating": f_rate,
                    "roles": ",".join(f_roles), "updated_at": now,
                    "peer_ratings": json.dumps({k: v for k, v in peer_results.items() if v > 0})
                }
                if p_data:
                    new_entry["created_at"] = p_data.get('created_at', now)
                    st.session_state.players[next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)] = new_entry
                else:
                    new_entry["created_at"] = now
                    st.session_state.players.append(new_entry)
                save_players_to_gsheets()
                st.session_state.edit_name = f_name
                st.rerun()
