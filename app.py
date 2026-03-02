import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# הגדרת דף - ממורכז (ביטול WIDE)
st.set_page_config(page_title="ניהול כדורגל וולפסון", layout="centered")

# CSS חזק ל-RTL ויישור לימין
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, h4, p, label, .stSelectbox, .stTextInput, .stNumberInput { 
        text-align: right !important; direction: rtl !important; 
    }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; justify-content: flex-end; }
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    .arrival-row { 
        background: #f8fafc; padding: 12px; border-radius: 10px; 
        margin-bottom: 8px; border-right: 5px solid #3b82f6; 
        display: flex; justify-content: space-between; align-items: center;
        flex-direction: row-reverse; border: 1px solid #e2e8f0;
    }
    .team-box { background: #ffffff; padding: 20px; border-radius: 12px; border: 2px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# חיבור לגליון
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name, expected_cols):
    try:
        df = conn.read(worksheet=name, ttl="0")
        if df is None or df.empty: return pd.DataFrame(columns=expected_cols)
        df.columns = [c.strip() for c in df.columns]
        return df.dropna(subset=['name'])
    except:
        return pd.DataFrame(columns=expected_cols)

# --- ניהול זיכרון (Session State) ---
if 'players_list' not in st.session_state:
    df_p = load_sheet("Football_DB", ["name", "rating"])
    st.session_state.players_list = df_p.to_dict('records')

if 'final_teams' not in st.session_state:
    st.session_state.final_teams = None

st.markdown("<h1 style='text-align: center; color: #1e40af;'>⚽ וולפסון - ניהול משחק</h1>", unsafe_allow_html=True)

# יצירת הטאבים
tab_reg, tab_split, tab_pay, tab_db = st.tabs(["📝 רישום", "🏃 חלוקה", "💰 תשלומים", "⚙️ מאגר"])

# --- טאב 1: רישום ---
with tab_reg:
    m_date = st.date_input("תאריך המחזור:", date.today()).strftime("%d/%m/%Y")
    h_df = load_sheet("arrivals_history", ["name", "match_date", "paid", "temp_rating"])
    daily = h_df[h_df['match_date'] == m_date]
    
    col_a, col_b = st.columns(2)
    with col_a:
        with st.form("reg_member", clear_on_submit=True):
            st.write("**רישום מהמאגר**")
            u = st.selectbox("בחר שחקן:", [""] + sorted([p['name'] for p in st.session_state.players_list]))
            if st.form_submit_button("רשום ✅") and u:
                if not ((h_df['name'] == u) & (h_df['match_date'] == m_date)).any():
                    new = pd.DataFrame([{"name": u, "match_date": m_date, "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                    st.rerun()
    with col_b:
        with st.form("reg_guest", clear_on_submit=True):
            st.write("**רישום אורח**")
            g = st.text_input("שם:")
            r = st.slider("רמה:", 1, 10, 5)
            if st.form_submit_button("הוסף ⭐") and g:
                new = pd.DataFrame([{"name": f"⭐ {g}", "match_date": m_date, "temp_rating": r, "paid": "לא"}])
                conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                st.rerun()

    st.subheader(f"רשימת הגעה ({len(daily)})")
    for i, row in daily.iterrows():
        c_t, c_d = st.columns([0.8, 0.2])
        c_t.markdown(f"<div class='arrival-row'><span>{row['name']}</span></div>", unsafe_allow_html=True)
        if c_d.button("❌", key=f"del_{i}"):
            conn.update(worksheet="arrivals_history", data=h_df.drop(i))
            st.rerun()

# --- טאב 2: חלוקת קבוצות (המנגנון המלא) ---
with tab_split:
    st.subheader("חלוקת קבוצות מאוזנת")
    
    if not daily.empty:
        if st.button("בצע חלוקה אוטומטית 🚀"):
            # יצירת רשימת שחקנים עם ציונים
            pool = []
            for n in daily['name']:
                if n.startswith("⭐"):
                    rating = daily[daily.name == n].iloc[0].get('temp_rating', 5)
                else:
                    # מושך ציון מהמאגר
                    p_info = next((x for x in st.session_state.players_list if x['name'] == n), {'rating': 5})
                    rating = p_info.get('rating', 5)
                pool.append({'name': n, 'rating': float(rating)})
            
            # אלגוריתם חלוקה (Snake Draft)
            pool.sort(key=lambda x: x['rating'], reverse=True)
            team_white = []
            team_black = []
            for i, p in enumerate(pool):
                if i % 2 == 0: team_white.append(p)
                else: team_black.append(p)
            
            # שמירה לזיכרון של Streamlit
            st.session_state.final_teams = {"white": team_white, "black": team_black}

        # תצוגת הקבוצות (אם נוצרו)
        if st.session_state.final_teams:
            tw = st.session_state.final_teams["white"]
            tb = st.session_state.final_teams["black"]
            
            c_white, c_black = st.columns(2)
            with c_white:
                st.markdown("<div class='team-box'>", unsafe_allow_html=True)
                st.markdown("### ⚪ קבוצה לבנה")
                for p in tw: st.write(f"🏃 {p['name']} (ציון: {p['rating']})")
                st.markdown(f"**סה\"כ רמה:** {sum(p['rating'] for p in tw)}")
                st.markdown("</div>", unsafe_allow_html=True)
            with c_black:
                st.markdown("<div class='team-box'>", unsafe_allow_html=True)
                st.markdown("### ⚫ קבוצה שחורה")
                for p in tb: st.write(f"🏃 {p['name']} (ציון: {p['rating']})")
                st.markdown(f"**סה\"כ רמה:** {sum(p['rating'] for p in tb)}")
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("אין מספיק שחקנים רשומים לחלוקה.")

# --- טאב 3: תשלומים ---
with tab_pay:
    st.subheader("ניהול תשלומים")
    unpaid = daily[daily['paid'] != "כן"]
    if not unpaid.empty:
        to_pay = st.selectbox("מי שילם?", [""] + unpaid['name'].tolist())
        if st.button("עדכן ששולם") and to_pay:
            full = load_sheet("arrivals_history", [])
            full.loc[(full.name == to_pay) & (full.match_date == m_date), 'paid'] = "כן"
            conn.update(worksheet="arrivals_history", data=full)
            st.rerun()
    st.dataframe(daily[['name', 'paid']], use_container_width=True)

# --- טאב 4: מאגר ---
with tab_db:
    st.subheader("ניהול מאגר שחקנים")
    st.dataframe(pd.DataFrame(st.session_state.players_list), use_container_width=True)
    with st.form("new_player"):
        nn = st.text_input("שם שחקן חדש:")
        nr = st.slider("דירוג:", 1.0, 10.0, 5.0)
        if st.form_submit_button("הוסף למאגר"):
            df_all = load_sheet("Football_DB", ["name", "rating"])
            new_row = pd.DataFrame([{"name": nn, "rating": nr}])
            conn.update(worksheet="Football_DB", data=pd.concat([df_all, new_row], ignore_index=True))
            st.rerun()
