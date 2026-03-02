import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# --- הגדרות דף ---
st.set_page_config(page_title="ניהול כדורגל וולפסון", layout="centered")

# --- מערכת עיצוב (CSS) מקיפה ---
st.markdown("""
    <style>
    /* הגדרות כיוון RTL */
    .stApp { direction: rtl; text-align: right; }
    div[data-testid="stVerticalBlock"] { direction: rtl; }
    
    /* כותרות וטקסט */
    h1, h2, h3, h4, p, label, .stSelectbox, .stTextInput, .stNumberInput { 
        text-align: right !important; direction: rtl !important; 
    }
    
    /* עיצוב טאבים */
    .stTabs [data-baseweb="tab-list"] { direction: rtl; justify-content: flex-end; gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 10px 20px; 
    }
    
    /* עיצוב כפתורים */
    .stButton button { 
        width: 100%; border-radius: 10px; height: 3.5em; 
        background-color: #2563eb; color: white; font-weight: bold; border: none;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stButton button:hover { background-color: #1d4ed8; border: none; color: white; }
    
    /* כפתור מחיקה אדום */
    div[data-testid="stColumn"] button { height: 2.5em; }
    
    /* שורת שחקן רשומה */
    .arrival-row { 
        background: #ffffff; padding: 15px; border-radius: 12px; 
        margin-bottom: 10px; border-right: 6px solid #3b82f6; 
        display: flex; justify-content: space-between; align-items: center;
        flex-direction: row-reverse; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
    }

    /* כרטיסי קבוצות */
    .team-container {
        background: #ffffff; padding: 20px; border-radius: 15px;
        border: 2px solid #e2e8f0; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        margin-top: 20px; min-height: 400px;
    }
    .white-header { border-top: 10px solid #cbd5e1; border-radius: 15px 15px 0 0; }
    .black-header { border-top: 10px solid #1e293b; border-radius: 15px 15px 0 0; }
    
    /* הודעות סטטוס */
    .stAlert { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# --- פונקציות ליבה ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name, cols):
    try:
        df = conn.read(worksheet=worksheet_name, ttl="0")
        if df is None or df.empty: return pd.DataFrame(columns=cols)
        df.columns = [c.strip() for c in df.columns]
        return df.dropna(subset=['name'])
    except:
        return pd.DataFrame(columns=cols)

# --- ניהול מצב (Session State) ---
if 'teams_output' not in st.session_state:
    st.session_state.teams_output = None

# טעינת נתונים ראשונית
df_players = get_data("Football_DB", ["name", "rating", "birth_year"])
st.session_state.all_players = df_players.to_dict('records')

# --- כותרת ראשית ---
st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>⚽ ניהול מועדון כדורגל וולפסון</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b;'>מערכת חכמה לרישום, חלוקה וניהול תשלומים</p>", unsafe_allow_html=True)

# --- יצירת הטאבים ---
tab_reg, tab_split, tab_pay, tab_db = st.tabs(["📝 רישום למשחק", "🏃 חלוקת קבוצות", "💰 מעקב תשלומים", "⚙️ מאגר שחקנים"])

# --- 1. טאב רישום ---
with tab_reg:
    current_date = st.date_input("בחר תאריך משחק:", date.today()).strftime("%d/%m/%Y")
    history = get_data("arrivals_history", ["name", "match_date", "paid", "temp_rating"])
    
    col_mem, col_gst = st.columns(2)
    
    with col_mem:
        st.subheader("רישום חבר מאגר")
        with st.form("member_form", clear_on_submit=True):
            player_name = st.selectbox("שם השחקן:", [""] + sorted([p['name'] for p in st.session_state.all_players]))
            if st.form_submit_button("אשר הגעה ✅"):
                if player_name:
                    if not ((history['name'] == player_name) & (history['match_date'] == current_date)).any():
                        new_data = pd.DataFrame([{"name": player_name, "match_date": current_date, "paid": "לא"}])
                        conn.update(worksheet="arrivals_history", data=pd.concat([history, new_data], ignore_index=True))
                        st.success(f"{player_name} נרשם בהצלחה")
                        st.rerun()

    with col_gst:
        st.subheader("רישום אורח / חדש")
        with st.form("guest_form", clear_on_submit=True):
            guest_name = st.text_input("שם האורח:")
            guest_rating = st.slider("דירוג יכולת (1-10):", 1.0, 10.0, 5.0, step=0.5)
            if st.form_submit_button("הוסף אורח ⭐"):
                if guest_name:
                    new_guest = pd.DataFrame([{"name": f"⭐ {guest_name}", "match_date": current_date, "temp_rating": guest_rating, "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([history, new_guest], ignore_index=True))
                    st.success(f"האורח {guest_name} נוסף")
                    st.rerun()

    st.divider()
    daily_list = history[history['match_date'] == current_date]
    st.subheader(f"רשימת שחקנים למשחק ({len(daily_list)})")
    
    for i, row in daily_list.iterrows():
        c_row, c_del = st.columns([0.85, 0.15])
        c_row.markdown(f"<div class='arrival-row'><span>{row['name']}</span></div>", unsafe_allow_html=True)
        if c_del.button("❌", key=f"del_{i}"):
            updated_history = history.drop(i)
            conn.update(worksheet="arrivals_history", data=updated_history)
            st.rerun()

# --- 2. טאב חלוקת קבוצות ---
with tab_split:
    st.subheader("חלוקה מאוזנת לפי רמת שחקן")
    
    if not daily_list.empty:
        if st.button("🚀 חלק קבוצות עכשיו"):
            # איסוף נתונים לחלוקה
            players_to_split = []
            for _, r in daily_list.iterrows():
                name = r['name']
                if name.startswith("⭐"):
                    rate = float(r.get('temp_rating', 5.0))
                else:
                    p_info = next((item for item in st.session_state.all_players if item['name'] == name), {'rating': 5.0})
                    rate = float(p_info.get('rating', 5.0))
                players_to_split.append({'name': name, 'rating': rate})
            
            # אלגוריתם חלוקה (Snake Draft)
            players_to_split.sort(key=lambda x: x['rating'], reverse=True)
            t_white, t_black = [], []
            for idx, p in enumerate(players_to_split):
                if idx % 2 == 0: t_white.append(p)
                else: t_black.append(p)
            
            st.session_state.teams_output = {"white": t_white, "black": t_black}

        if st.session_state.teams_output:
            tw = st.session_state.teams_output["white"]
            tb = st.session_state.teams_output["black"]
            
            col_w, col_b = st.columns(2)
            with col_w:
                st.markdown("<div class='team-container white-header'>", unsafe_allow_html=True)
                st.markdown("### ⚪ קבוצה לבנה")
                for p in tw: st.write(f"🏃 {p['name']} ({p['rating']})")
                st.markdown(f"**סה\"כ רמה:** {round(sum(p['rating'] for p in tw), 1)}")
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col_b:
                st.markdown("<div class='team-container black-header'>", unsafe_allow_html=True)
                st.markdown("### ⚫ קבוצה שחורה")
                for p in tb: st.write(f"🏃 {p['name']} ({p['rating']})")
                st.markdown(f"**סה\"כ רמה:** {round(sum(p['rating'] for p in tb), 1)}")
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("אין מספיק שחקנים רשומים לחלוקה.")

# --- 3. טאב תשלומים ---
with tab_pay:
    st.subheader("ניהול גבייה")
    not_paid = daily_list[daily_list['paid'] != "כן"]
    
    if not not_paid.empty:
        selected_payer = st.selectbox("מי שילם?", [""] + not_paid['name'].tolist())
        if st.button("סמן כ'שולם' 💰"):
            if selected_payer:
                full_h = get_data("arrivals_history", [])
                full_h.loc[(full_h.name == selected_payer) & (full_h.match_date == current_date), 'paid'] = "כן"
                conn.update(worksheet="arrivals_history", data=full_h)
                st.success(f"התשלום של {selected_payer} עודכן")
                st.rerun()
    
    st.table(daily_list[['name', 'paid']])

# --- 4. טאב מאגר שחקנים ---
with tab_db:
    st.subheader("ניהול המאגר הקבוע")
    st.dataframe(df_players[['name', 'rating', 'birth_year']], use_container_width=True)
    
    with st.expander("הוספת שחקן חדש למאגר"):
        with st.form("new_player_db"):
            n_name = st.text_input("שם מלא:")
            n_rate = st.slider("דירוג התחלתי:", 1.0, 10.0, 5.0)
            n_year = st.number_input("שנת לידה:", 1960, 2020, 1990)
            if st.form_submit_button("שמור במאגר"):
                if n_name:
                    new_entry = pd.DataFrame([{"name": n_name, "rating": n_rate, "birth_year": n_year}])
                    conn.update(worksheet="Football_DB", data=pd.concat([df_players, new_entry], ignore_index=True))
                    st.success("שחקן נוסף למאגר!")
                    st.rerun()
