import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# הגדרות דף - ממורכז (ביטול WIDE)
st.set_page_config(page_title="ניהול כדורגל וולפסון", layout="centered")

# CSS חזק ל-RTL ויישור לימין
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, h4, p, label, .stSelectbox, .stTextInput, .stNumberInput { 
        text-align: right !important; direction: rtl !important; 
    }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; justify-content: flex-end; }
    .stButton button { width: 100%; border-radius: 8px; }
    .arrival-row { 
        background: #f8fafc; padding: 12px; border-radius: 10px; 
        margin-bottom: 8px; border-right: 5px solid #3b82f6; 
        display: flex; justify-content: space-between; align-items: center;
        flex-direction: row-reverse; border: 1px solid #e2e8f0;
    }
    .team-box { background: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #cbd5e1; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# חיבור לגוגל שיטס
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name, expected_cols):
    try:
        df = conn.read(worksheet=name, ttl="0")
        if df is None or df.empty: return pd.DataFrame(columns=expected_cols)
        df.columns = [c.strip() for c in df.columns]
        return df.dropna(subset=['name'])
    except:
        return pd.DataFrame(columns=expected_cols)

# טעינת מאגר שחקנים ל-session_state
if 'players' not in st.session_state:
    df_p = load_sheet("Football_DB", ["name", "rating"])
    st.session_state.players = df_p.to_dict('records')

# שמירת קבוצות בזיכרון כדי שלא יעלמו במעבר טאבים
if 'teams' not in st.session_state:
    st.session_state.teams = None

st.markdown("<h1 style='text-align: center; color: #1e40af;'>⚽ וולפסון - ניהול משחק</h1>", unsafe_allow_html=True)

# יצירת הטאבים - שמות המשתנים קבועים למניעת שגיאות
tab_reg, tab_split, tab_pay, tab_db = st.tabs(["📝 רישום", "🏃 חלוקה", "💰 תשלומים", "⚙️ מאגר"])

# --- טאב 1: רישום ומחיקה ---
with tab_reg:
    m_date = st.date_input("תאריך המחזור:", date.today()).strftime("%d/%m/%Y")
    h_df = load_sheet("arrivals_history", ["name", "match_date", "paid", "temp_rating"])
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("שחקן מאגר")
        with st.form("f_reg", clear_on_submit=True):
            u_name = st.selectbox("בחר שם:", [""] + sorted([p['name'] for p in st.session_state.players]))
            if st.form_submit_button("רשום ✅") and u_name:
                if not ((h_df['name'] == u_name) & (h_df['match_date'] == m_date)).any():
                    new = pd.DataFrame([{"name": u_name, "match_date": m_date, "paid": "לא"}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                    st.rerun()

    with c2:
        st.subheader("שחקן אורח")
        with st.form("f_guest", clear_on_submit=True):
            g_name = st.text_input("שם האורח:")
            g_rate = st.slider("רמה (1-10):", 1, 10, 5)
            if st.form_submit_button("הוסף אורח ⭐") and g_name:
                new = pd.DataFrame([{"name": f"⭐ {g_name}", "match_date": m_date, "temp_rating": g_rate, "paid": "לא"}])
                conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new], ignore_index=True))
                st.rerun()

    st.divider()
    daily = h_df[h_df['match_date'] == m_date]
    st.subheader(f"רשימת הגעה ({len(daily)})")
    for i, row in daily.iterrows():
        c_txt, c_btn = st.columns([0.85, 0.15])
        c_txt.markdown(f"<div class='arrival-row'><span>{row['name']}</span></div>", unsafe_allow_html=True)
        if c_btn.button("❌", key=f"del_{i}"):
            conn.update(worksheet="arrivals_history", data=h_df.drop(i))
            st.rerun()

# --- טאב 2: חלוקת קבוצות (החלק ש"נעלם") ---
with tab_split:
    st.subheader("חלוקת קבוצות מאוזנת")
    
    if not daily.empty:
        if st.button("חלק קבוצות עכשיו 🚀"):
            pool = []
            for n in daily['name']:
                if n.startswith("⭐"):
                    r = daily[daily.name == n].iloc[0].get('temp_rating', 5)
                    pool.append({'n': n, 'r': float(r)})
                else:
                    p = next((x for x in st.session_state.players if x['name'] == n), {'rating': 5})
                    pool.append({'n': n, 'r': float(p.get('rating', 5))})
            
            # לוגיקת חלוקה (Snake Draft)
            pool.sort(key=lambda x: x['r'], reverse=True)
            t1, t2 = pool[::2], pool[1::2]
            st.session_state.teams = (t1, t2)
        
        # הצגת הקבוצות אם הן קיימות בזיכרון
        if st.session_state.teams:
            t1, t2 = st.session_state.teams
            ca, cb = st.columns(2)
            
            with ca:
                st.markdown("<div class='team-box'>", unsafe_allow_html=True)
                st.markdown("### ⚪ לבנים")
                for p in t1: st.write(f"🏃 {p['n']} ({p['r']})")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with cb:
                st.markdown("<div class='team-box'>", unsafe_allow_html=True)
                st.markdown("### ⚫ שחורים")
                for p in t2: st.write(f"🏃 {p['n']} ({p['r']})")
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("אין שחקנים רשומים למחזור זה. רשום שחקנים בטאב הרישום.")

# --- טאב 3: תשלומים ---
with tab_pay:
    st.subheader("מעקב תשלומים")
    unpaid = daily[daily['paid'] != "כן"]
    if not unpaid.empty:
        p_to_pay = st.selectbox("בחר מי שילם:", [""] + unpaid['name'].tolist())
        if st.button("עדכן ששולם 💰") and p_to_pay:
            full_h = load_sheet("arrivals_history", [])
            full_h.loc[(full_h.name == p_to_pay) & (full_h.match_date == m_date), 'paid'] = "כן"
            conn.update(worksheet="arrivals_history", data=full_h)
            st.rerun()
    st.table(daily[['name', 'paid']])

# --- טאב 4: מאגר שחקנים ---
with tab_db:
    st.subheader("ניהול המאגר")
    df_all = load_sheet("Football_DB", ["name", "rating"])
    st.dataframe(df_all[['name', 'rating']], use_container_width=True)
    
    with st.form("new_p"):
        st.write("הוספת שחקן חדש למאגר")
        nn = st.text_input("שם מלא:")
        nr = st.slider("דירוג:", 1.0, 10.0, 5.0)
        if st.form_submit_button("שמור"):
            new_p = pd.DataFrame([{"name": nn, "rating": nr}])
            conn.update(worksheet="Football_DB", data=pd.concat([df_all, new_p], ignore_index=True))
            st.rerun()
