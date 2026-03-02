#1. ייבוא ספריות, הגדרות וחיבור נתונים (Safe Load)

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime, date

st.set_page_config(page_title="ניהול כדורגל וולפסון", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# פונקציה לטעינה בטוחה עם יצירת עמודות חסרות
def load_sheet(name, expected_cols):
    try:
        df = conn.read(worksheet=name, ttl="0")
        if df is None or df.empty: return pd.DataFrame(columns=expected_cols)
        df.columns = [c.strip() for c in df.columns]
        for c in expected_cols:
            if c not in df.columns: df[c] = None
        return df.dropna(subset=['name'])
    except:
        return pd.DataFrame(columns=expected_cols)

# טעינת המאגרים ל-Session State
if 'players' not in st.session_state:
    df_db = load_sheet("Football_DB", ["name", "birth_year", "rating", "peer_ratings"])
    st.session_state.players = df_db.to_dict('records')

# פונקציית שקלול ציון (ממוצע עמיתים + ציון עצמי)
def get_weighted_rating(name, all_players):
    p = next((x for x in all_players if x['name'] == name), None)
    if not p: return 5.0
    self_r = float(p.get('rating', 5))
    peer_scores = []
    for voter in all_players:
        v_peers = json.loads(str(voter.get('peer_ratings','{}')).replace("'", '"'))
        if name in v_peers and float(v_peers[name]) > 0:
            peer_scores.append(float(v_peers[name]))
    return round((self_r + (sum(peer_scores)/len(peer_scores))) / 2, 1) if peer_scores else self_r

st.markdown("<h1 style='text-align:center;'>⚽ ניהול כדורגל וולפסון</h1>", unsafe_allow_html=True)
t_reg, t_split, t_pay, t_db = st.tabs(["📝 רישום", "🏃 חלוקה", "💰 תשלומים", "⚙️ ניהול מאגר"])


#2. טאב רישום (כולל מזדמנים ומחיקה)
with t_reg:
    m_date = st.date_input("תאריך המחזור:", date.today()).strftime("%d/%m/%Y")
    h_df = load_sheet("arrivals_history", ["name", "phone", "arrival_time", "match_date", "paid", "temp_rating"])
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("רישום חבר")
        with st.form("reg_member"):
            u = st.selectbox("בחר שחקן:", [""] + sorted([p['name'] for p in st.session_state.players]))
            u_phone = st.text_input("טלפון:")
            if st.form_submit_button("רשום ✅") and u:
                if not ((h_df['name'] == u) & (h_df['match_date'] == m_date)).any():
                    new = pd.DataFrame([{"name": u, "phone": u_phone, "match_date": m_date, "arrival_time": datetime.now().strftime("%H:%M"), "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

    with col2:
        st.subheader("רישום מזדמן")
        with st.form("reg_guest"):
            g_name = st.text_input("שם האורח:")
            g_rate = st.slider("ציון זמני:", 1, 10, 5)
            if st.form_submit_button("הוסף אורח ⭐") and g_name:
                new = pd.DataFrame([{"name": f"⭐ {g_name}", "match_date": m_date, "temp_rating": g_rate, "paid": "לא"}])
                conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                st.cache_data.clear()
                st.rerun()

    st.write("---")
    daily = h_df[h_df['match_date'] == m_date]
    st.subheader(f"רשימת מתייצבים ({len(daily)})")
    for i, row in daily.iterrows():
        c_n, c_p, c_d = st.columns([4, 2, 1])
        c_n.info(f"**{row['name']}**")
        c_p.write(f"סטטוס: {row['paid']}")
        if c_d.button("❌", key=f"del_{i}"):
            conn.update(worksheet="arrivals_history", data=h_df.drop(i))
            st.cache_data.clear()
            st.rerun()


#3. טאב חלוקה וטאב תשלומים (גליון נפרד)
with t_split:
    if not daily.empty:
        if st.button("בצע חלוקה 🚀", use_container_width=True):
            pool = []
            for n in daily['name']:
                if n.startswith("⭐"):
                    row = daily[daily.name == n].iloc[0]
                    pool.append({'n': n, 'r': float(row.get('temp_rating', 5))})
                else:
                    pool.append({'n': n, 'r': get_weighted_rating(n, st.session_state.players)})
            
            pool.sort(key=lambda x: x['r'], reverse=True)
            t1, t2 = pool[::2], pool[1::2]
            cl, cr = st.columns(2)
            for col, team, label in zip([cl, cr], [t1, t2], ["⚪ לבן", "⚫ שחור"]):
                col.subheader(label)
                for p in team: col.code(f"{p['n']} ({p['r']})")
                    

#4. טאב ניהול תשלומים והיסטוריה
with t_pay:
    st.subheader("עדכון תשלומים")
    unpaid = daily[daily['paid'] != "כן"]
    if not unpaid.empty:
        p_pay = st.selectbox("מי שילם?", unpaid['name'].tolist())
        if st.button("סמן כ'שולם' 💰"):
            full_h = load_sheet("arrivals_history", [])
            full_h.loc[(full_h.name == p_pay) & (full_h.match_date == m_date), 'paid'] = "כן"
            conn.update(worksheet="arrivals_history", data=full_h)
            st.cache_data.clear()
            st.rerun()
    
    st.write("---")
    st.subheader("היסטוריית תשלומים (כל המחזורים)")
    st.dataframe(h_df[['name', 'match_date', 'paid']].sort_values('match_date', ascending=False))

#5. טאב ניהול מאגר (הוספת שחקן חדש ודירוג עמיתים)
with t_db:
    st.subheader("ניהול שחקני המאגר")
    all_names = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    target = st.selectbox("בחר שחקן:", all_names)
    
    with st.form("db_form"):
        if target == "🆕 שחקן חדש":
            new_n = st.text_input("שם מלא:")
            new_y = st.number_input("שנת לידה:", 1950, 2020, 1990)
            new_r = st.slider("דירוג ראשוני:", 1, 10, 5)
            peers = {}
        else:
            p_data = next(p for p in st.session_state.players if p['name'] == target)
            new_n = target
            new_y = st.number_input("שנת לידה:", 1950, 2020, int(p_data.get('birth_year', 1990)))
            new_r = st.slider("דירוג עצמי:", 1, 10, int(p_data.get('rating', 5)))
            peers = json.loads(str(p_data.get('peer_ratings', '{}')).replace("'", '"'))
            st.write("🎯 **דירוג עמיתים:**")
            for other in st.session_state.players:
                if other['name'] != target:
                    peers[other['name']] = st.number_input(f"דירוג ל-{other['name']}:", 0, 10, int(peers.get(other['name'], 0)))

        if st.form_submit_button("שמור שינויים במאגר 💾"):
            db_full = load_sheet("Football_DB", [])
            new_row = {"name": new_n, "birth_year": new_y, "rating": new_r, "peer_ratings": json.dumps(peers)}
            if target == "🆕 שחקן חדש":
                db_full = pd.concat([db_full, pd.DataFrame([new_row])], ignore_index=True)
            else:
                db_full.loc[db_full.name == target, ['birth_year', 'rating', 'peer_ratings']] = [new_y, new_r, json.dumps(peers)]
            conn.update(worksheet="Football_DB", data=db_full)
            st.success("המאגר עודכן!")
            st.cache_data.clear()
            st.rerun()
