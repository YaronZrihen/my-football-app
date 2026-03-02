import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# הגדרות דף - ממורכז (לא WIDE)
st.set_page_config(page_title="ניהול כדורגל וולפסון")

# CSS להצמדת הכל לימין (RTL)
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .block-container { max-width: 800px; }
    h1, h2, h3, h4, p, label, .stSelectbox, .stTextInput { text-align: right !important; direction: rtl !important; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; justify-content: flex-end; }
    .team-card { background: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name, cols):
    try:
        df = conn.read(worksheet=name, ttl="0")
        df.columns = [c.strip() for c in df.columns]
        return df.dropna(subset=['name'])
    except: return pd.DataFrame(columns=cols)

# טעינת המאגר
df_p = load_sheet("Football_DB", ["name", "rating"])
st.session_state.players = df_p.to_dict('records')

st.markdown("<h1 style='text-align: center;'>⚽ וולפסון - ניהול משחק</h1>", unsafe_allow_html=True)

# יצירת הטאבים - שמות פשוטים למניעת שגיאות
t_reg, t_split, t_pay, t_db = st.tabs(["📝 רישום", "🏃 חלוקה", "💰 תשלומים", "⚙️ מאגר"])

# --- טאב רישום ---
with t_reg:
    m_date = st.date_input("תאריך:", date.today()).strftime("%d/%m/%Y")
    h_df = load_sheet("arrivals_history", ["name", "match_date", "paid", "temp_rating"])
    
    col_a, col_b = st.columns(2)
    with col_a:
        with st.form("f1", clear_on_submit=True):
            st.write("שחקן מאגר")
            u = st.selectbox("בחר:", [""] + sorted([p['name'] for p in st.session_state.players]))
            if st.form_submit_button("רשום ✅") and u:
                new = pd.DataFrame([{"name": u, "match_date": m_date, "paid": "לא"}])
                conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                st.rerun()
    with col_b:
        with st.form("f2", clear_on_submit=True):
            st.write("אורח")
            g = st.text_input("שם:")
            r = st.slider("רמה:", 1, 10, 5)
            if st.form_submit_button("הוסף ⭐") and g:
                new = pd.DataFrame([{"name": f"⭐ {g}", "match_date": m_date, "temp_rating": r, "paid": "לא"}])
                conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                st.rerun()

    daily = h_df[h_df['match_date'] == m_date]
    st.subheader(f"רשומים ({len(daily)})")
    for i, row in daily.iterrows():
        c_n, c_d = st.columns([0.8, 0.2])
        c_n.info(row['name'])
        if c_d.button("❌", key=f"d_{i}"):
            conn.update(worksheet="arrivals_history", data=h_df.drop(i))
            st.rerun()

# --- טאב חלוקה (החלק שביקשת להחזיר) ---
with t_split:
    st.subheader("חלוקת קבוצות")
    if not daily.empty:
        if st.button("בצע חלוקה 🚀", use_container_width=True):
            pool = []
            for n in daily['name']:
                if n.startswith("⭐"):
                    rating = daily[daily.name == n].iloc[0].get('temp_rating', 5)
                else:
                    p_data = next((x for x in st.session_state.players if x['name'] == n), {'rating': 5})
                    rating = p_data.get('rating', 5)
                pool.append({'n': n, 'r': float(rating)})
            
            # מיון וחלוקת זיג-זג (Snake)
            pool.sort(key=lambda x: x['r'], reverse=True)
            t1 = pool[::2]
            t2 = pool[1::2]
            
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown("<div class='team-card'>", unsafe_allow_html=True)
                st.markdown("### ⚪ לבנים")
                for p in t1: st.write(f"🏃 {p['n']} ({p['r']})")
                st.markdown(f"**סה\"כ רמה:** {sum(p['r'] for p in t1)}")
                st.markdown("</div>", unsafe_allow_html=True)
            with c_right:
                st.markdown("<div class='team-card'>", unsafe_allow_html=True)
                st.markdown("### ⚫ שחורים")
                for p in t2: st.write(f"🏃 {p['n']} ({p['r']})")
                st.markdown(f"**סה\"כ רמה:** {sum(p['r'] for p in t2)}")
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.write("אין שחקנים רשומים היום.")

# --- טאב תשלומים ---
with t_pay:
    st.subheader("תשלומים")
    unpaid = daily[daily['paid'] != "כן"]
    if not unpaid.empty:
        p_pay = st.selectbox("מי שילם?", [""] + unpaid['name'].tolist())
        if st.button("עדכן שולם"):
            all_h = load_sheet("arrivals_history", [])
            all_h.loc[(all_h.name == p_pay) & (all_h.match_date == m_date), 'paid'] = "כן"
            conn.update(worksheet="arrivals_history", data=all_h)
            st.rerun()
    st.table(daily[['name', 'paid']])

# --- טאב מאגר ---
with t_db:
    st.subheader("מאגר שחקנים")
    st.dataframe(df_p, use_container_width=True)
    with st.form("f3"):
        nn = st.text_input("שם חדש:")
        nr = st.slider("דירוג:", 1, 10, 5)
        if st.form_submit_button("הוסף למאגר"):
            new_row = pd.DataFrame([{"name": nn, "rating": nr}])
            conn.update(worksheet="Football_DB", data=pd.concat([df_p, new_row], ignore_index=True))
            st.rerun()
