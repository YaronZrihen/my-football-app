import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# --- הגדרות דף ---
st.set_page_config(page_title="ניהול כדורגל וולפסון", layout="centered")

# --- עיצוב RTL ועברית ---
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, h4, p, label, .stSelectbox, .stTextInput, .stNumberInput { 
        text-align: right !important; direction: rtl !important; 
    }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; justify-content: flex-end; }
    .stButton button { width: 100%; }
    .arrival-row { 
        background: #f0f2f6; padding: 12px; border-radius: 10px; 
        margin-bottom: 8px; border-right: 5px solid #3b82f6; 
        display: flex; justify-content: space-between; align-items: center;
        flex-direction: row-reverse;
    }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name, expected_cols):
    try:
        df = conn.read(worksheet=name, ttl="0")
        if df is None or df.empty: return pd.DataFrame(columns=expected_cols)
        df.columns = [c.strip() for c in df.columns]
        return df.dropna(subset=['name'])
    except:
        return pd.DataFrame(columns=expected_cols)

# טעינת מאגר שחקנים
df_players = load_sheet("Football_DB", ["name", "birth_year", "rating", "peer_ratings"])
st.session_state.players = df_players.to_dict('records')

st.markdown("<h1 style='text-align: center; color: #3b82f6;'>⚽ וולפסון - ניהול משחק</h1>", unsafe_allow_html=True)

# --- יצירת הטאבים ---
tab_reg, tab_split, tab_pay, tab_db = st.tabs(["📝 רישום", "🏃 חלוקה", "💰 תשלומים", "⚙️ מאגר"])

# --- טאב 1: רישום ומחיקה ---
with tab_reg:
    m_date = st.date_input("תאריך המחזור:", date.today()).strftime("%d/%m/%Y")
    h_df = load_sheet("arrivals_history", ["name", "phone", "arrival_time", "match_date", "paid", "temp_rating"])
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("שחקן מאגר")
        with st.form("f_reg"):
            u_name = st.selectbox("בחר שם:", [""] + sorted([p['name'] for p in st.session_state.players]))
            if st.form_submit_button("רשום ✅") and u_name:
                if not ((h_df['name'] == u_name) & (h_df['match_date'] == m_date)).any():
                    new = pd.DataFrame([{"name": u_name, "match_date": m_date, "arrival_time": datetime.now().strftime("%H:%M"), "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                    st.rerun()
    with col2:
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
    st.subheader(f"רשומים להיום ({len(daily)})")
    for i, row in daily.iterrows():
        c_txt, c_btn = st.columns([0.85, 0.15])
        c_txt.markdown(f"<div class='arrival-row'><span>{row['name']}</span><span>{row.get('arrival_time','')}</span></div>", unsafe_allow_html=True)
        if c_btn.button("❌", key=f"del_{i}"):
            conn.update(worksheet="arrivals_history", data=h_df.drop(i))
            st.rerun()

# --- טאב 2: חלוקת קבוצות ---
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
            t1, t2 = pool[::2], pool[1::2]
            ca, cb = st.columns(2)
            for col, team, label in zip([ca, cb], [t1, t2], ["⚪ לבנים", "⚫ שחורים"]):
                col.markdown(f"### {label}")
                for p in team: col.write(f"🏃 {p['n']} ({p['r']})")

# --- טאב 3: תשלומים ---
with tab_pay:
    st.subheader("מעקב תשלומים")
    unpaid = daily[daily['paid'] != "כן"]
    if not unpaid.empty:
        p_to_pay = st.selectbox("מי שילם?", unpaid['name'].tolist())
        if st.button("סמן כ'שולם' 💰"):
            full_h = load_sheet("arrivals_history", [])
            full_h.loc[(full_h.name == p_to_pay) & (full_h.match_date == m_date), 'paid'] = "כן"
            conn.update(worksheet="arrivals_history", data=full_h)
            st.rerun()
    st.table(daily[['name', 'paid']])

# --- טאב 4: ניהול המאגר ---
with tab_db:
    st.subheader("ניהול המאגר הקבוע")
    st.dataframe(df_players[['name', 'rating']], use_container_width=True)
    with st.form("add_new"):
        st.write("הוספת שחקן חדש ל-Football_DB")
        nn = st.text_input("שם מלא:")
        nr = st.slider("דירוג:", 1, 10, 5)
        if st.form_submit_button("שמור במאגר"):
            new_p = pd.DataFrame([{"name": nn, "rating": nr}])
            conn.update(worksheet="Football_DB", data=pd.concat([df_players, new_p], ignore_index=True))
            st.success("השחקן נוסף!")
            st.rerun()
