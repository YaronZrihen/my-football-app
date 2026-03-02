import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime, date

# הגדרות דף
st.set_page_config(page_title="וולפסון כדורגל - ניהול מלא", layout="wide")

# חיבור לגליון
conn = st.connection("gsheets", type=GSheetsConnection)

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

# טעינת מאגר קבוע
if 'players' not in st.session_state:
    df_db = load_sheet("Football_DB", ["name", "birth_year", "rating", "peer_ratings"])
    st.session_state.players = df_db.to_dict('records')

# פונקציית שקלול ציון (עצמי + ממוצע חברים)
def get_weighted_rating(name, all_players):
    p = next((x for x in all_players if x['name'] == name), None)
    if not p: return 5.0
    self_r = float(p.get('rating', 5))
    peer_scores = []
    for voter in all_players:
        v_peers = json.loads(str(voter.get('peer_ratings','{}')).replace("'", '"'))
        if name in v_peers and float(v_peers[name]) > 0:
            peer_scores.append(float(v_peers[name]))
    if not peer_scores: return self_r
    return round((self_r + (sum(peer_scores)/len(peer_scores))) / 2, 1)

st.markdown("<h1 style='text-align:center;'>⚽ ניהול כדורגל וולפסון</h1>", unsafe_allow_html=True)
t_reg, t_split, t_pay, t_db = st.tabs(["📝 רישום", "🏃 חלוקה", "💰 תשלומים", "⚙️ ניהול מאגר"])

#2. טאב רישום (כולל מזדמנים ומחיקה)
with t_reg:
    m_date = st.date_input("תאריך המחזור:", date.today()).strftime("%d/%m/%Y")
    h_df = load_sheet("arrivals_history", ["name", "phone", "arrival_time", "match_date", "paid", "temp_rating"])
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("רישום מהמאגר")
        with st.form("reg_member"):
            u = st.selectbox("בחר שחקן:", [""] + sorted([p['name'] for p in st.session_state.players]))
            if st.form_submit_button("רשום ✅") and u:
                if not ((h_df['name'] == u) & (h_df['match_date'] == m_date)).any():
                    new = pd.DataFrame([{"name": u, "match_date": m_date, "arrival_time": datetime.now().strftime("%H:%M"), "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                    st.rerun()
    
    with c2:
        st.subheader("רישום שחקן מזדמן")
        with st.form("reg_guest"):
            g = st.text_input("שם האורח:")
            r = st.slider("ציון זמני (1-10):", 1, 10, 5)
            if st.form_submit_button("הוסף אורח ⭐") and g:
                new = pd.DataFrame([{"name": f"⭐ {g}", "match_date": m_date, "temp_rating": r, "paid": "לא"}])
                conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                st.rerun()

    st.write("---")
    daily = h_df[h_df['match_date'] == m_date]
    st.write(f"### רשומים למחזור: {len(daily)}")
    for i, row in daily.iterrows():
        col_n, col_d = st.columns([5,1])
        col_n.info(f"{row['name']} | נרשם ב: {row.get('arrival_time', 'N/A')}")
        if col_d.button("❌", key=f"del_{i}"):
            conn.update(worksheet="arrivals_history", data=h_df.drop(i))
            st.rerun()

#3. טאב חלוקה וטאב תשלומים (גליון נפרד)
with t_split:
    if not daily.empty:
        if st.button("חלק קבוצות 🚀", use_container_width=True):
            pool = []
            for n in daily['name']:
                if n.startswith("⭐"):
                    row = daily[daily.name == n].iloc[0]
                    pool.append({'n': n, 'r': float(row.get('temp_rating', 5))})
                else:
                    pool.append({'n': n, 'r': get_weighted_rating(n, st.session_state.players)})
            
            pool.sort(key=lambda x: x['r'], reverse=True)
            t1, t2 = pool[::2], pool[1::2] # Snake Draft
            cl, cr = st.columns(2)
            for col, team, label in zip([cl, cr], [t1, t2], ["⚪ קבוצה לבנה", "⚫ קבוצה שחורה"]):
                col.subheader(label)
                for p in team: col.code(f"{p['n']} (ציון: {p['r']})")

with t_pay:
    st.subheader("סטטוס תשלומים למחזור זה")
    unpaid = daily[daily['paid'] != "כן"]
    if not unpaid.empty:
        to_pay = st.selectbox("מי שילם עכשיו?", unpaid['name'].tolist())
        if st.button("עדכן כ'שולם' 💰"):
            full_h = load_sheet("arrivals_history", [])
            full_h.loc[(full_h.name == to_pay) & (full_h.match_date == m_date), 'paid'] = "כן"
            conn.update(worksheet="arrivals_history", data=full_h)
            st.rerun()
    st.dataframe(daily[['name', 'paid', 'arrival_time']], use_container_width=True)

#4. טאב ניהול מאגר (דירוג עמיתים מלא)
with t_db:
    st.subheader("עריכת שחקנים ודירוג עמיתים")
    target = st.selectbox("בחר שחקן לעריכה/דירוג:", [p['name'] for p in st.session_state.players])
    p_data = next(p for p in st.session_state.players if p['name'] == target)
    
    with st.form("edit_db"):
        col_y, col_r = st.columns(2)
        new_year = col_y.number_input("שנת לידה:", 1950, 2020, int(p_data.get('birth_year', 1990)))
        new_self = col_r.slider("דירוג עצמי:", 1, 10, int(p_data.get('rating', 5)))
        
        st.write("---")
        st.write("🎯 **דירוג עמיתים (דרג את חברי הקבוצה):**")
        peers = json.loads(str(p_data.get('peer_ratings', '{}')).replace("'", '"'))
        
        for other in st.session_state.players:
            if other['name'] != target:
                peers[other['name']] = st.select_slider(
                    f"הרמה של {other['name']}:", 
                    options=list(range(0, 11)), 
                    value=int(peers.get(other['name'], 0)),
                    key=f"p_{target}_{other['name']}"
                )
        
        if st.form_submit_button("שמור שינויים במאגר 💾"):
            df_all_db = load_sheet("Football_DB", [])
            df_all_db.loc[df_all_db.name == target, ['birth_year', 'rating', 'peer_ratings']] = \
                [new_year, new_self, json.dumps(peers)]
            conn.update(worksheet="Football_DB", data=df_all_db)
            st.success("הנתונים נשמרו!")
            st.rerun()

