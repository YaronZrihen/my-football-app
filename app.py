#1. ייבוא ספריות, הגדרות וחיבור נתונים (Safe Load)

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime, date

# הגדרת דף ממורכז (מבטל את ה-WIDE)
st.set_page_config(page_title="ניהול כדורגל וולפסון")

# CSS להצמדת הכל לימין (RTL) ומרכוז המערכת
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .block-container { max-width: 800px; padding-top: 2rem; }
    h1, h2, h3, h4, p, label, .stSelectbox, .stTextInput, .stNumberInput { 
        text-align: right !important; direction: rtl !important; 
    }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; justify-content: flex-end; }
    .arrival-row { 
        background: #f0f2f6; padding: 15px; border-radius: 10px; 
        margin-bottom: 10px; border-right: 5px solid #3b82f6; 
        display: flex; justify-content: space-between; align-items: center;
        flex-direction: row-reverse;
    }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name, expected_cols):
    try:
        df = conn.read(worksheet=name, ttl="0")
        if df is None or df.empty: return pd.DataFrame(columns=expected_cols)
        df.columns = [c.strip() for c in df.columns]
        return df.dropna(subset=['name'])
    except:
        return pd.DataFrame(columns=expected_cols)

# טעינת המאגר
df_players = load_sheet("Football_DB", ["name", "birth_year", "rating", "peer_ratings"])
st.session_state.players = df_players.to_dict('records')

st.markdown("<h1 style='text-align: center; color: #3b82f6;'>⚽ וולפסון - ניהול משחק</h1>", unsafe_allow_html=True)

# יצירת הטאבים - אלו השמות שחייבים להישאר קבועים
tab_reg, tab_split, tab_pay, tab_db = st.tabs(["📝 רישום", "🏃 חלוקה", "💰 תשלומים", "⚙️ מאגר"])





#2. רישום שחקנים (חברים ומזדמנים) ומחיקה
with tab_reg:
    m_date = st.date_input("תאריך המחזור:", date.today()).strftime("%d/%m/%Y")
    h_df = load_sheet("arrivals_history", ["name", "phone", "arrival_time", "match_date", "paid", "temp_rating"])
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("שחקן מאגר")
        with st.form("f_reg"):
            u_name = st.selectbox("בחר שם:", [""] + sorted([p['name'] for p in st.session_state.players]))
            if st.form_submit_button("רשום ✅") and u_name:
                if not ((h_df['name'] == u_name) & (h_df['match_date'] == m_date)).any():
                    new = pd.DataFrame([{"name": u_name, "match_date": m_date, "arrival_time": datetime.now().strftime("%H:%M"), "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                    st.rerun()

    with c2:
        st.subheader("שחקן אורח")
        with st.form("f_guest"):
            g_name = st.text_input("שם האורח:")
            g_rate = st.slider("רמה (1-10):", 1, 10, 5)
            if st.form_submit_button("הוסף אורח ⭐") and g_name:
                new = pd.DataFrame([{"name": f"⭐ {g_name}", "match_date": m_date, "temp_rating": g_rate, "paid": "לא"}])
                conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                st.rerun()

    st.write("---")
    daily = h_df[h_df['match_date'] == m_date]
    st.subheader(f"רשימת הגעה ({len(daily)})")
    
    for i, row in daily.iterrows():
        c_txt, c_btn = st.columns([0.85, 0.15])
        c_txt.markdown(f"<div class='arrival-row'><span>{row['name']}</span><span>{row.get('arrival_time','')}</span></div>", unsafe_allow_html=True)
        if c_btn.button("❌", key=f"del_{i}"):
            conn.update(worksheet="arrivals_history", data=h_df.drop(i))
            st.rerun()



            

#3. טאב חלוקה וטאב תשלומים (גליון נפרד)
with tab_split:
    st.subheader("חלוקת קבוצות")
    if not daily.empty:
        if st.button("בצע חלוקה 🚀"):
            pool = []
            for n in daily['name']:
                if n.startswith("⭐"):
                    r = daily[daily.name == n].iloc[0].get('temp_rating', 5)
                    pool.append({'n': n, 'r': float(r)})
                else:
                    p = next((x for x in st.session_state.players if x['name'] == n), {'rating': 5})
                    pool.append({'n': n, 'r': float(p.get('rating', 5))})
            
            pool.sort(key=lambda x: x['r'], reverse=True)
            team1, team2 = pool[::2], pool[1::2]
            ca, cb = st.columns(2)
            for col, team, label in zip([ca, cb], [team1, team2], ["⚪ לבנים", "⚫ שחורים"]):
                col.markdown(f"### {label}")
                for p in team: col.write(f"🏃 {p['n']} ({p['r']})")

with tab_pay:
    st.subheader("מעקב תשלומים")
    unpaid = daily[daily['paid'] != "כן"]
    if not unpaid.empty:
        p_to_pay = st.selectbox("מי שילם עכשיו?", unpaid['name'].tolist())
        if st.button("עדכן ששולם 💰"):
            full_h = load_sheet("arrivals_history", [])
            full_h.loc[(full_h.name == p_to_pay) & (full_h.match_date == m_date), 'paid'] = "כן"
            conn.update(worksheet="arrivals_history", data=full_h)
            st.rerun()
    st.table(daily[['name', 'paid']])

with tab_db:
    st.subheader("ניהול מאגר שחקנים קבוע")
    st.dataframe(df_players[['name', 'birth_year', 'rating']], use_container_width=True)
    with st.form("add_new"):
        st.write("הוספת שחקן חדש ל-Football_DB")
        n_name = st.text_input("שם מלא:")
        n_year = st.number_input("שנת לידה:", 1950, 2020, 1990)
        n_rate = st.slider("דירוג:", 1, 10, 5)
        if st.form_submit_button("שמור במאגר"):
            new_p = pd.DataFrame([{"name": n_name, "birth_year": n_year, "rating": n_rate}])
            conn.update(worksheet="Football_DB", data=pd.concat([df_players, new_p], ignore_index=True))
            st.success("השחקן נוסף בהצלחה!")
            st.rerun()
            
            


            
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






