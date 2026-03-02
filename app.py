import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime, date

#1
# חלק א': הגדרות, טעינה וטאב רישום
st.set_page_config(page_title="וולפסון כדורגל", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def load_safe(sheet, cols):
    try:
        df = conn.read(worksheet=sheet, ttl="0")
        df.columns = [c.strip() for c in df.columns]
        for c in cols:
            if c not in df.columns: df[c] = None
        return df.dropna(subset=['name'])
    except: return pd.DataFrame(columns=cols)

# טעינת נתונים
if 'players' not in st.session_state:
    df_db = load_safe("Football_DB", ["name", "rating", "peer_ratings"])
    st.session_state.players = df_db.to_dict('records')

def get_final_rate(p):
    name, self_r = p['name'], float(p.get('rating', 5))
    peers = [float(json.loads(str(v.get('peer_ratings','{}')).replace("'", '"')).get(name, 0)) 
             for v in st.session_state.players if name in json.loads(str(v.get('peer_ratings','{}')).replace("'", '"'))]
    avg = sum(peers)/len(peers) if peers else 0
    return round((self_r + avg)/2, 1) if avg else self_r

st.markdown("<h1 style='text-align:center; color:#60a5fa;'>⚽ ניהול כדורגל וולפסון</h1>", unsafe_allow_html=True)
t_reg, t_split, t_pay, t_db = st.tabs(["📝 רישום", "🏃 חלוקה", "💰 תשלומים", "⚙️ מאגר"])

with t_reg:
    m_date = st.date_input("תאריך המחזור:", date.today()).strftime("%d/%m/%Y")
    h_df = load_safe("arrivals_history", ["name", "phone", "arrival_time", "match_date", "paid", "temp_rating"])
    
    c1, c2 = st.columns(2)
    with c1:
        with st.form("f_reg"):
            u = st.selectbox("שחקן מאגר:", [""] + sorted([p['name'] for p in st.session_state.players]))
            if st.form_submit_button("רשום ✅") and u:
                if not ((h_df['name'] == u) & (h_df['match_date'] == m_date)).any():
                    new = pd.DataFrame([{"name": u, "match_date": m_date, "arrival_time": datetime.now().strftime("%H:%M"), "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                    st.rerun()
    with c2:
        with st.form("f_guest"):
            g, r = st.text_input("שם אורח:"), st.slider("רמה מוערכת:", 1, 10, 5)
            if st.form_submit_button("הוסף אורח ⭐") and g:
                new = pd.DataFrame([{"name": f"⭐ {g}", "match_date": m_date, "temp_rating": r, "paid": "לא"}])
                conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                st.rerun()

    st.write("---")
    daily = h_df[h_df['match_date'] == m_date]
    for i, r in daily.iterrows():
        col_n, col_d = st.columns([5,1])
        col_n.info(f"{r['name']} | {r.get('paid','לא שולם')}")
        if col_d.button("❌", key=f"del_{i}"):
            conn.update(worksheet="arrivals_history", data=h_df.drop(i))
            st.rerun()

#2
# חלק ב': חלוקה, תשלומים ודירוג עמיתים
with t_split:
    if not daily.empty:
        if st.button("בצע חלוקה 🚀", use_container_width=True):
            pool = []
            for n in daily['name']:
                if n.startswith("⭐"):
                    row = daily[daily.name == n].iloc[0]
                    pool.append({'n': n, 'r': float(row.get('temp_rating', 5))})
                else:
                    p = next(x for x in st.session_state.players if x['name'] == n)
                    pool.append({'n': n, 'r': get_final_rate(p)})
            
            pool.sort(key=lambda x: x['r'], reverse=True)
            t1, t2 = pool[::2], pool[1::2]
            cl, cr = st.columns(2)
            for col, team, label in zip([cl, cr], [t1, t2], ["⚪ לבן", "⚫ שחור"]):
                col.subheader(label)
                for p in team: col.code(f"{p['n']} ({p['r']})")

with t_pay:
    unpaid = daily[daily['paid'] != "כן"]
    if not unpaid.empty:
        p_pay = st.selectbox("מי שילם?", unpaid['name'])
        if st.form_submit_button("עדכן ששולם 💰" if 'form' in str(st.session_state) else "סמן ששולם"):
            h_df.loc[(h_df.name == p_pay) & (h_df.match_date == m_date), 'paid'] = "כן"
            conn.update(worksheet="arrivals_history", data=h_df)
            st.rerun()
    st.dataframe(daily[['name', 'paid']], use_container_width=True)

with t_db:
    target = st.selectbox("בחר שחקן לעריכה:", [p['name'] for p in st.session_state.players])
    p_data = next(p for p in st.session_state.players if p['name'] == target)
    with st.form("f_db"):
        new_r = st.slider("דירוג עצמי:", 1, 10, int(p_data.get('rating', 5)))
        peers = json.loads(str(p_data.get('peer_ratings', '{}')).replace("'", '"'))
        for o in st.session_state.players:
            if o['name'] != target:
                peers[o['name']] = st.number_input(f"דירוג ל-{o['name']}:", 0, 10, int(peers.get(o['name'], 0)))
        if st.form_submit_button("שמור שינויים במאגר"):
            all_db = load_safe("Football_DB", [])
            all_db.loc[all_db.name == target, ['rating', 'peer_ratings']] = [new_r, json.dumps(peers)]
            conn.update(worksheet="Football_DB", data=all_db)
            st.success("עודכן!")

#3
