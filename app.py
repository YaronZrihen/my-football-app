#1. ייבוא ספריות, הגדרות וחיבור נתונים (Safe Load)

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime, date

# הגדרות דף ו-RTL (ימין לשמאל)
st.set_page_config(page_title="ניהול כדורגל וולפסון", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; }
    div[data-testid="stMarkdownContainer"] p { text-align: right; }
    .arrival-row { background: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 5px; border-right: 5px solid #3b82f6; display: flex; justify-content: space-between; align-items: center; }
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

# טעינת המאגר מגיליון Football_DB
df_players = load_sheet("Football_DB", ["name", "birth_year", "rating", "peer_ratings"])
st.session_state.players = df_players.to_dict('records')

st.title("⚽ ניהול כדורגל וולפסון")
tab_reg, tab_split, tab_pay, tab_db = st.tabs(["📝 רישום למשחק", "🏃 חלוקת קבוצות", "💰 תשלומים", "⚙️ ניהול מאגר"])


#2. רישום שחקנים (חברים ומזדמנים) ומחיקה
with tab_reg:
    m_date = st.date_input("תאריך המחזור:", date.today()).strftime("%d/%m/%Y")
    # טעינת היסטוריה (שם, טלפון, זמן, תאריך, שולם)
    h_df = load_sheet("arrivals_history", ["name", "phone", "arrival_time", "match_date", "paid", "temp_rating"])
    
    col_reg, col_guest = st.columns(2)
    with col_reg:
        st.subheader("רישום חבר מהמאגר")
        with st.form("reg_member"):
            # בחירה מתוך המאגר שנטען מ-Football_DB
            u_name = st.selectbox("בחר שחקן:", [""] + sorted([p['name'] for p in st.session_state.players]))
            if st.form_submit_button("רשום למשחק ✅") and u_name:
                if not ((h_df['name'] == u_name) & (h_df['match_date'] == m_date)).any():
                    new = pd.DataFrame([{"name": u_name, "match_date": m_date, "arrival_time": datetime.now().strftime("%H:%M"), "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                    st.rerun()

    with col_guest:
        st.subheader("רישום שחקן מזדמן")
        with st.form("reg_guest"):
            g_name = st.text_input("שם האורח:")
            g_rate = st.slider("דירוג אורח (1-10):", 1, 10, 5)
            if st.form_submit_button("הוסף אורח ⭐") and g_name:
                new = pd.DataFrame([{"name": f"⭐ {g_name}", "match_date": m_date, "temp_rating": g_rate, "paid": "לא"}])
                conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                st.rerun()

    st.write("---")
    daily = h_df[h_df['match_date'] == m_date]
    st.subheader(f"רשומים למחזור ({len(daily)})")
    for i, row in daily.iterrows():
        c_n, c_d = st.columns([5, 1])
        c_n.markdown(f"<div class='arrival-row'><span>{row['name']}</span> <span>{row.get('arrival_time','')}</span></div>", unsafe_allow_html=True)
        if c_d.button("❌", key=f"del_{i}"):
            conn.update(worksheet="arrivals_history", data=h_df.drop(i))
            st.rerun()
            

#3. טאב חלוקה וטאב תשלומים (גליון נפרד)
with tab_split:
    if not daily.empty:
        if st.button("חלק קבוצות 🚀", use_container_width=True):
            # לוגיקת חלוקה לפי דירוג (מזדמנים מקבלים temp_rating, חברים מקבלים rating מהמאגר)
            pool = []
            for n in daily['name']:
                if n.startswith("⭐"):
                    r = daily[daily.name == n].iloc[0].get('temp_rating', 5)
                    pool.append({'n': n, 'r': float(r)})
                else:
                    p = next(x for x in st.session_state.players if x['name'] == n)
                    pool.append({'n': n, 'r': float(p.get('rating', 5))})
            
            pool.sort(key=lambda x: x['r'], reverse=True)
            t1, t2 = pool[::2], pool[1::2]
            cl, cr = st.columns(2)
            for col, team, label in zip([cl, cr], [t1, t2], ["קבוצה לבנה", "קבוצה שחורה"]):
                col.subheader(label)
                for p in team: col.write(f"🏃 {p['n']} ({p['r']})")

with tab_pay:
    st.subheader("סטטוס תשלומים")
    unpaid = daily[daily['paid'] != "כן"]
    if not unpaid.empty:
        p_pay = st.selectbox("מי שילם?", unpaid['name'].tolist())
        if st.button("סמן כ'שולם' 💰"):
            full_h = load_sheet("arrivals_history", [])
            full_h.loc[(full_h.name == p_pay) & (full_h.match_date == m_date), 'paid'] = "כן"
            conn.update(worksheet="arrivals_history", data=full_h)
            st.rerun()
    st.table(daily[['name', 'paid']])

with tab_db:
    st.subheader("מאגר השחקנים (Football_DB)")
    st.dataframe(df_players[['name', 'birth_year', 'rating']])
    
    with st.form("add_player"):
        st.write("הוספת שחקן חדש למאגר")
        n_name = st.text_input("שם מלא:")
        n_year = st.number_input("שנת לידה:", 1950, 2020, 1990)
        n_rate = st.slider("דירוג:", 1, 10, 5)
        if st.form_submit_button("שמור למאגר"):
            new_p = pd.DataFrame([{"name": n_name, "birth_year": n_year, "rating": n_rate}])
            conn.update(worksheet="Football_DB", data=pd.concat([df_players, new_p], ignore_index=True))
            st.success("שחקן נוסף למאגר!")
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

