import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime

# --- 1. עיצוב CSS ---
st.set_page_config(page_title="ניהול כדורגל וולפסון חולון", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;} .stDeployButton {display:none;}
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span, div { text-align: right !important; direction: rtl; }
    .block-container { padding-top: 50px !important; }
    .wolfson-title { font-size: 28px !important; text-align: center !important; color: #60a5fa; font-weight: bold; margin-bottom: 30px; }
    .player-card { background: #2d3748; border: 1px solid #4a5568; border-radius: 12px; padding: 15px; margin-bottom: 15px; }
    .card-header { font-size: 20px; font-weight: bold; color: #f8fafc; border-bottom: 1px solid #4a5568; padding-bottom: 8px; margin-bottom: 10px; }
    .card-row { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 14px; }
    .label { color: #94a3b8; }
    .highlight-value { color: #22c55e; font-weight: bold; }
    .p-box { background: #2d3748; border: 1px solid #4a5568; border-radius: 4px; padding: 2px 8px; margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center; min-height: 35px; }
    .team-stats { background: #1e293b; border-top: 2px solid #4a5568; padding: 10px; margin-top: 10px; font-size: 14px; text-align: center; border-radius: 0 0 8px 8px; }
    .arrival-card { background: #2d3748; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-right: 4px solid #3b82f6; display: flex; justify-content: space-between; align-items: center; }
    .paid-status { color: #22c55e; font-weight: bold; }
    .unpaid-status { color: #ef4444; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר וחיבור נתונים ---
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

# טעינת מאגר שחקנים כללי
if 'players' not in st.session_state:
    try:
        df = conn.read(worksheet="Sheet1", ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

# פונקציית טעינת היסטוריה
def load_arrivals_history():
    try:
        return conn.read(worksheet="arrivals_history", ttl="0").dropna(subset=['name'])
    except:
        return pd.DataFrame(columns=['name', 'phone', 'arrival_time', 'match_date', 'paid'])

def save_players_to_gsheets():
    if not st.session_state.players:
        st.error("⚠️ המאגר ריק. השמירה בוטלה.")
        return
    df = pd.DataFrame(st.session_state.players)
    conn.update(worksheet="Sheet1", data=df)
    st.cache_data.clear()

def get_player_full_stats(p):
    name = p['name']
    birth_year = int(p.get('birth_year', 1900))
    age = 2026 - birth_year
    self_rating = float(p.get('rating', 0))
    peer_scores = []
    for voter in st.session_state.players:
        if voter['name'] == name: continue
        voter_ratings = safe_get_json(voter.get('peer_ratings', '{}'))
        if name in voter_ratings and voter_ratings[name] > 0:
            peer_scores.append(float(voter_ratings[name]))
    count = len(peer_scores)
    avg_peer = sum(peer_scores) / count if count > 0 else 0
    if self_rating > 0 and count > 0: final_score = (self_rating + avg_peer) / 2
    elif self_rating > 0: final_score = self_rating
    elif count > 0: final_score = avg_peer
    else: final_score = 5.0
    return {"final": round(final_score, 1), "age": age, "count": count, "self": self_rating, "peer": round(avg_peer, 1)}

# --- 3. ממשק משתמש וטאבים ---
st.markdown("<div class='wolfson-title'>ניהול כדורגל וולפסון חולון</div>", unsafe_allow_html=True)

if 'edit_name' not in st.session_state: st.session_state.edit_name = "🆕 שחקן חדש"
tab_arrival, tab_split, tab_db, tab_edit = st.tabs(["✅ אישורי הגעה", "🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 רישום/עדכון"])

# --- טאב 1: אישורי הגעה ובקרה ---
with tab_arrival:
    st.subheader("רישום למשחק הקרוב")
    all_p_names = sorted([p['name'] for p in st.session_state.players])
    
    with st.form("arrival_form"):
        u_name = st.selectbox("בחר שם מהמאגר:", [""] + all_p_names)
        u_phone = st.text_input("מספר פלאפון (לבקרה):")
        if st.form_submit_button("אשר הגעה ושמור היסטוריה ✅", use_container_width=True):
            if u_name and u_phone:
                history_df = load_arrivals_history()
                today_str = datetime.now().strftime("%d/%m/%Y")
                if not ((history_df['name'] == u_name) & (history_df['match_date'] == today_str)).any():
                    new_row = pd.DataFrame([{
                        "name": u_name, "phone": u_phone,
                        "arrival_time": datetime.now().strftime("%H:%M:%S"),
                        "match_date": today_str, "paid": "לא"
                    }])
                    updated_h = pd.concat([history_df, new_row], ignore_index=True)
                    conn.update(worksheet="arrivals_history", data=updated_h)
                    st.success(f"נרשמת בהצלחה למחזור {today_str}!")
                    st.cache_data.clear()
                else: st.warning("כבר נרשמת למשחק היום.")
            else: st.error("חובה למלא שם וטלפון.")

    st.write("---")
    st.subheader("בקרת נוכחות ותשלומים")
    h_df = load_arrivals_history()
    if not h_df.empty:
        dates = h_df['match_date'].unique()
        sel_date = st.selectbox("בחר תאריך לצפייה:", dates, index=len(dates)-1)
        daily = h_df[h_df['match_date'] == sel_date]
        st.write(f"רשומים: **{len(daily)}** שחקנים")
        for _, r in daily.iterrows():
            st.markdown(f"""<div class='arrival-card'><div><b>{r['name']}</b><br><small>{r['phone']} | {r['arrival_time']}</small></div>
            <div class='{"paid-status" if r["paid"]=="כן" else "unpaid-status"}'>{"✅ שולם" if r["paid"]=="כן" else "❌ טרם שולם"}</div></div>""", unsafe_allow_html=True)
    else: st.info("אין היסטוריית הגעה.")

# --- טאב 2: חלוקה ---
with tab_split:
    h_df = load_arrivals_history()
    today_str = datetime.now().strftime("%d/%m/%Y")
    today_list = h_df[h_df['match_date'] == today_str]['name'].tolist()
    
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected_names = st.pills("מי הגיע?", all_names, selection_mode="multi", default=today_list)
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
                for i, p in enumerate(team):
                    st.markdown(f"<div class='p-box'><span>{p['name']} ({p['age']})</span><span><b>{p['f']}</b></span></div>", unsafe_allow_html=True)
                if team:
                    avg = sum(x['f'] for x in team)/len(team)
                    st.markdown(f"<div class='team-stats'>רמה ממוצעת: {avg:.1f}</div>", unsafe_allow_html=True)

# --- טאב 3: מאגר שחקנים ---
with tab_db:
    st.write(f"סה\"כ במאגר: **{len(st.session_state.players)}** שחקנים")
    for i, p in enumerate(st.session_state.players):
        s = get_player_full_stats(p)
        roles = safe_split(p.get('roles', ''))
        st.markdown(f"""<div class='player-card'><div class='card-header'>{p['name']}</div>
        <div class='card-row'><span class='label'>גיל:</span><span>{s['age']}</span></div>
        <div class='card-row'><span class='label'>תפקיד:</span><span>{", ".join(roles)}</span></div>
        <div class='card-row'><span class='label'>ציון סופי:</span><span class='highlight-value'>{s['final']}</span></div>
        <div class='card-row'><span class='label'>דירוגים:</span><span>עצמי: {s['self']} | חברים: {s['peer']} ({s['count']})</span></div></div>""", unsafe_allow_html=True)
        if st.button("📝 עריכה", key=f"e_btn_{i}"):
            st.session_state.edit_name = p['name']; st.rerun()

# --- טאב 4: רישום ועדכון ---
with tab_edit:
    all_n = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    choice = st.selectbox("בחר שחקן:", all_n, index=all_n.index(st.session_state.edit_name) if st.session_state.edit_name in all_n else 0)
    p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
    
    with st.form("edit_form"):
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "").strip()
        f_year = st.number_input("שנת לידה:", 1900, 2026, int(p_data['birth_year']) if p_data else 1990)
        roles_opt = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
        f_roles = st.pills("תפקידים:", roles_opt, selection_mode="multi", default=[r for r in safe_split(p_data.get('roles', '')) if r in roles_opt] if p_data else [])
        f_rate = st.radio("ציון עצמי:", [0]+list(range(1,11)), index=int(p_data.get('rating',0)) if p_data else 0, horizontal=True)
        
        st.write("---")
        st.write("דירוג עמיתים:")
        peer_res = {}
        other_players = [p for p in st.session_state.players if p['name'] != (f_name or choice)]
        for idx, op in enumerate(other_players):
            curr_rating = safe_get_json(p_data.get('peer_ratings', '{}') if p_data else '{}').get(op['name'], 0)
            peer_res[op['name']] = st.radio(f"דרג את {op['name']}:", [0]+list(range(1,11)), index=int(curr_rating), horizontal=True, key=f"peer_{idx}")

        if st.form_submit_button("שמור שינויים במאגר הכללי ✅"):
            if f_name:
                existing = [p['name'] for p in st.session_state.players if p['name'] != (p_data['name'] if p_data else None)]
                if f_name in existing: st.error("השם כבר קיים במאגר!")
                else:
                    now = datetime.now().strftime("%d/%m/%Y %H:%M")
                    new_entry = {
                        "name": f_name, "birth_year": f_year, "rating": f_rate,
                        "roles": ",".join(f_roles), "updated_at": now,
                        "peer_ratings": json.dumps({k: v for k, v in peer_res.items() if v > 0})
                    }
                    if p_data:
                        new_entry["created_at"] = p_data.get('created_at', now)
                        st.session_state.players[next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)] = new_entry
                    else:
                        new_entry["created_at"] = now
                        st.session_state.players.append(new_entry)
                    save_players_to_gsheets()
                    st.rerun()

for _ in range(5): st.write("")
