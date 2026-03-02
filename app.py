import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# --- 1. הגדרות דף ועיצוב (RTL מלא) ---
st.set_page_config(page_title="ניהול כדורגל וולפסון", layout="centered")

st.markdown("""
    <style>
    /* הגדרות כיוון מימין לשמאל */
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stVerticalBlock"] { direction: rtl; }
    h1, h2, h3, h4, p, label, .stSelectbox, .stTextInput, .stNumberInput { 
        text-align: right !important; direction: rtl !important; 
    }
    
    /* עיצוב טאבים */
    .stTabs [data-baseweb="tab-list"] { direction: rtl; justify-content: flex-end; gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 10px 25px; 
    }
    
    /* עיצוב כפתורים כחולים וגדולים */
    .stButton button { 
        width: 100%; border-radius: 12px; height: 3.5em; 
        background-color: #2563eb; color: white; font-weight: bold; border: none;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s;
    }
    .stButton button:hover { background-color: #1d4ed8; color: white; transform: translateY(-2px); }
    
    /* כרטיסי שחקנים ברשימה */
    .player-card { 
        background: #ffffff; padding: 15px; border-radius: 12px; 
        margin-bottom: 10px; border-right: 6px solid #3b82f6; 
        display: flex; justify-content: space-between; align-items: center;
        flex-direction: row-reverse; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }

    /* כרטיסי קבוצות בחלוקה */
    .team-container {
        background: #ffffff; padding: 20px; border-radius: 15px;
        border: 2px solid #e2e8f0; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        margin-top: 20px;
    }
    .white-team-header { border-top: 10px solid #cbd5e1; border-radius: 15px 15px 0 0; }
    .black-team-header { border-top: 10px solid #1e293b; border-radius: 15px 15px 0 0; }
    
    /* טבלאות */
    .stTable { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור ופונקציות נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_sheet_data(sheet_name, columns):
    try:
        df = conn.read(worksheet=sheet_name, ttl="0")
        if df is None or df.empty: return pd.DataFrame(columns=columns)
        df.columns = [c.strip() for c in df.columns]
        return df.dropna(subset=['name'])
    except:
        return pd.DataFrame(columns=columns)

# --- 3. ניהול מצב האפליקציה (Session State) ---
# טעינת המאגר לזיכרון
if 'master_players' not in st.session_state:
    df_p = get_sheet_data("Football_DB", ["name", "rating", "birth_year"])
    st.session_state.master_players = df_p.to_dict('records')

# זיכרון לחלוקת קבוצות (כדי שלא ייעלם במעבר טאבים)
if 'last_split' not in st.session_state:
    st.session_state.last_split = None

# --- 4. כותרת המערכת ---
st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>⚽ ניהול מועדון כדורגל וולפסון</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>רישום, חלוקת קבוצות מאוזנת וניהול גבייה</p>", unsafe_allow_html=True)

# יצירת הטאבים
t_reg, t_split, t_pay, t_db = st.tabs(["📝 רישום שחקנים", "🏃 חלוקת קבוצות", "💰 תשלומים", "⚙️ ניהול מאגר"])

# --- 5. טאב רישום ---
with t_reg:
    game_date = st.date_input("תאריך המשחק:", date.today()).strftime("%d/%m/%Y")
    history_df = get_sheet_data("arrivals_history", ["name", "match_date", "paid", "temp_rating"])
    
    col_reg1, col_reg2 = st.columns(2)
    
    with col_reg1:
        st.subheader("שחקן מאגר")
        with st.form("reg_member", clear_on_submit=True):
            p_name = st.selectbox("בחר שם:", [""] + sorted([p['name'] for p in st.session_state.master_players]))
            if st.form_submit_button("רשום למשחק ✅") and p_name:
                if not ((history_df['name'] == p_name) & (history_df['match_date'] == game_date)).any():
                    new_entry = pd.DataFrame([{"name": p_name, "match_date": game_date, "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([history_df, new_entry], ignore_index=True))
                    st.success(f"{p_name} נרשם!")
                    st.rerun()

    with col_reg2:
        st.subheader("אורח / חדש")
        with st.form("reg_guest", clear_on_submit=True):
            g_name = st.text_input("שם האורח:")
            g_rate = st.slider("דירוג יכולת:", 1.0, 10.0, 5.0, step=0.5)
            if st.form_submit_button("הוסף אורח ⭐") and g_name:
                new_guest = pd.DataFrame([{"name": f"⭐ {g_name}", "match_date": game_date, "temp_rating": g_rate, "paid": "לא"}])
                conn.update(worksheet="arrivals_history", data=pd.concat([history_df, new_guest], ignore_index=True))
                st.success(f"האורח {g_name} נוסף!")
                st.rerun()

    st.divider()
    current_players = history_df[history_df['match_date'] == game_date]
    st.subheader(f"רשימת רשומים ({len(current_players)})")
    
    for i, row in current_players.iterrows():
        c_p, c_d = st.columns([0.85, 0.15])
        c_p.markdown(f"<div class='player-card'><span>{row['name']}</span></div>", unsafe_allow_html=True)
        if c_d.button("❌", key=f"del_{i}"):
            updated = history_df.drop(i)
            conn.update(worksheet="arrivals_history", data=updated)
            st.rerun()

# --- 6. טאב חלוקה ---
with t_split:
    st.subheader("חלוקה אוטומטית מאוזנת")
    
    if not current_players.empty:
        if st.button("בצע חלוקת קבוצות 🚀"):
            # איסוף נתונים ודירוגים
            pool = []
            for _, r in current_players.iterrows():
                name = r['name']
                if name.startswith("⭐"):
                    rating = float(r.get('temp_rating', 5.0))
                else:
                    p_info = next((p for p in st.session_state.master_players if p['name'] == name), {'rating': 5.0})
                    rating = float(p_info.get('rating', 5.0))
                pool.append({'name': name, 'rating': rating})
            
            # אלגוריתם Snake Draft לאיזון מקסימלי
            pool.sort(key=lambda x: x['rating'], reverse=True)
            white, black = [], []
            for idx, player in enumerate(pool):
                if idx % 2 == 0: white.append(player)
                else: black.append(player)
            
            st.session_state.last_split = {"white": white, "black": black}

        # הצגת תוצאות החלוקה
        if st.session_state.last_split:
            tw, tb = st.session_state.last_split["white"], st.session_state.last_split["black"]
            cw, cb = st.columns(2)
            
            with cw:
                st.markdown("<div class='team-container white-team-header'>", unsafe_allow_html=True)
                st.markdown("### ⚪ לבנים")
                for p in tw: st.write(f"🏃 {p['name']} ({p['rating']})")
                st.markdown(f"**חוזק קבוצה:** {round(sum(p['rating'] for p in tw), 1)}")
                st.markdown("</div>", unsafe_allow_html=True)
            
            with cb:
                st.markdown("<div class='team-container black-team-header'>", unsafe_allow_html=True)
                st.markdown("### ⚫ שחורים")
                for p in tb: st.write(f"🏃 {p['name']} ({p['rating']})")
                st.markdown(f"**חוזק קבוצה:** {round(sum(p['rating'] for p in tb), 1)}")
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("אין שחקנים רשומים לחלוקה. חזור לרישום.")

# --- 7. טאב תשלומים ---
with t_pay:
    st.subheader("מעקב תשלומים וגבייה")
    not_paid_list = current_players[current_players['paid'] != "כן"]
    
    if not not_paid_list.empty:
        p_to_pay = st.selectbox("מי שילם?", [""] + not_paid_list['name'].tolist())
        if st.button("עדכן ששולם 💰") and p_to_pay:
            full_history = get_sheet_data("arrivals_history", [])
            full_history.loc[(full_history.name == p_to_pay) & (full_history.match_date == game_date), 'paid'] = "כן"
            conn.update(worksheet="arrivals_history", data=full_history)
            st.success(f"התשלום של {p_to_pay} עודכן בהצלחה")
            st.rerun()
    
    st.markdown("### סטטוס תשלומים נוכחי")
    st.table(current_players[['name', 'paid']])

# --- 8. טאב ניהול מאגר ---
with t_db:
    st.subheader("מאגר השחקנים הקבוע")
    master_df = pd.DataFrame(st.session_state.master_players)
    st.dataframe(master_df[['name', 'rating', 'birth_year']], use_container_width=True)
    
    with st.expander("הוספת שחקן חדש למאגר"):
        with st.form("new_db_player", clear_on_submit=True):
            new_n = st.text_input("שם מלא:")
            new_r = st.slider("דירוג ראשוני:", 1.0, 10.0, 5.0)
            new_y = st.number_input("שנת לידה:", 1960, 2020, 1990)
            if st.form_submit_button("שמור במאגר"):
                if new_n:
                    new_player = pd.DataFrame([{"name": new_n, "rating": new_r, "birth_year": new_y}])
                    conn.update(worksheet="Football_DB", data=pd.concat([master_df, new_player], ignore_index=True))
                    st.success("השחקן נוסף למאגר!")
                    st.rerun()
