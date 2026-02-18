import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. הגדרות דף ו-CSS למניעת WIDE (מבנה חסין סלולר)
st.set_page_config(page_title="וולפסון 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { direction: rtl; }
    
    /* מניעת WIDE: נעילת 2 עמודות אחת ליד השנייה בכל מכשיר */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
        width: 100% !important;
    }
    
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 0 !important;
    }

    /* התאמת הכפתור למבנה צר */
    .stButton button {
        width: 100% !important;
        padding: 0px !important;
        font-size: 18px !important;
    }
    
    /* חיתוך טקסט ארוך כדי שלא ירחיב את העמודה */
    .stMarkdown p {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. חיבור נתונים מקורי
conn = st.connection("gsheets", type=GSheetsConnection)

if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except:
        st.session_state.players = []

def save_to_gsheets():
    df = pd.DataFrame(st.session_state.players)
    conn.update(data=df)
    st.cache_data.clear()

# 3. ממשק טאבים מלא (משוחזר)
st.title("⚽ וולפסון חולון")
tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון פרטים"])

# --- טאב 1: חלוקת קבוצות (עם כפתורי 🔄) ---
with tab1:
    names_list = sorted([p['name'] for p in st.session_state.players])
    selected = st.pills("מי משחק?", names_list, selection_mode="multi")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            for n in selected:
                p_data = next(p for p in st.session_state.players if p['name'] == n)
                # שימוש בנתונים המקוריים מהמאגר
                pool.append({
                    'name': n, 
                    'rating': float(p_data.get('rating', 5.0)), 
                    'birth_year': int(p_data.get('birth_year', 1996))
                })
            
            pool.sort(key=lambda x: x['rating'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        col_w, col_b = st.columns(2)
        
        with col_w:
            st.markdown("<h3 style='text-align:center;'>⚪ לבן</h3>", unsafe_allow_html=True)
            for i, p in enumerate(st.session_state.t1):
                c_name, c_btn = st.columns([0.75, 0.25])
                c_name.markdown(f"**{p['name']}**\n{p['rating']:.1f} | {2026-p['birth_year']}")
                if c_btn.button("🔄", key=f"w_sw_{i}"):
                    st.session_state.t2.append(st.session_state.t1.pop(i))
                    st.rerun()
            avg1 = sum(p['rating'] for p in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
            st.metric("רמת קבוצה", f"{avg1:.1f}")

        with col_b:
            st.markdown("<h3 style='text-align:center;'>⚫ שחור</h3>", unsafe_allow_html=True)
            for i, p in enumerate(st.session_state.t2):
                c_name, c_btn = st.columns([0.75, 0.25])
                c_name.markdown(f"**{p['name']}**\n{p['rating']:.1f} | {2026-p['birth_year']}")
                if c_btn.button("🔄", key=f"b_sw_{i}"):
                    st.session_state.t1.append(st.session_state.t2.pop(i))
                    st.rerun()
            avg2 = sum(p['rating'] for p in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0
            st.metric("רמת קבוצה", f"{avg2:.1f}")

# --- טאב 2: מאגר שחקנים (משוחזר) ---
with tab2:
    st.subheader("כל השחקנים במערכת")
    if st.session_state.players:
        df_all = pd.DataFrame(st.session_state.players)
        st.dataframe(df_all[['name', 'rating', 'birth_year', 'phone', 'position']], use_container_width=True)

# --- טאב 3: עדכון פרטים (משוחזר) ---
with tab3:
    st.subheader("עדכון או הוספת שחקן")
    with st.form("edit_form"):
        f_name = st.text_input("שם מלא (חובה)")
        f_rating = st.slider("דירוג (1-10)", 1.0, 10.0, 5.0)
        f_year = st.number_input("שנת לידה", 1950, 2015, 1990)
        f_phone = st.text_input("טלפון")
        f_pos = st.selectbox("תפקיד", ["שחקן שדה", "שוער"])
        
        if st.form_submit_button("שמור במאגר"):
            if f_name:
                existing = next((p for p in st.session_state.players if p['name'] == f_name), None)
                new_data = {
                    'name': f_name, 
                    'rating': f_rating, 
                    'birth_year': f_year,
                    'phone': f_phone,
                    'position': f_pos
                }
                if existing:
                    existing.update(new_data)
                else:
                    st.session_state.players.append(new_data)
                save_to_gsheets()
                st.success(f"הפרטים של {f_name} נשמרו!")
                st.rerun()
            else:
                st.error("נא להזין שם שחקן")
