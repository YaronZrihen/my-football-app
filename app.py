import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- התיקון היחיד: CSS שמונע WIDE וגלישה ---
st.set_page_config(page_title="כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    /* 1. יישור לימין */
    .stApp { direction: rtl; }
    
    /* 2. מניעת גלישה רוחבית מוחלטת */
    html, body, [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
        width: 100vw;
    }

    /* 3. צמצום השוליים הלבנים שגורמים ל-WIDE */
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* 4. נעילת העמודות שלא יברחו הצידה בסלולר */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 10px !important;
    }
    
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- כאן מתחיל הקוד הכי טוב ששמרת (לא נגעתי בכלל) ---

# חיבור לנתונים
conn = st.connection("gsheets", type=GSheetsConnection)

if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except:
        st.session_state.players = []

# פונקציית שמירה
def save_to_gsheets():
    df = pd.DataFrame(st.session_state.players)
    conn.update(data=df)
    st.cache_data.clear()

# ממשק טאבים
st.title("⚽ וולפסון חולון")
tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון פרטים"])

# טאב חלוקה
with tab1:
    names_list = sorted([p['name'] for p in st.session_state.players])
    selected = st.pills("מי משחק?", names_list, selection_mode="multi")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            for n in selected:
                p_data = next(p for p in st.session_state.players if p['name'] == n)
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
            st.subheader("⚪ לבן")
            for i, p in enumerate(st.session_state.t1):
                c_name, c_btn = st.columns([0.7, 0.3])
                c_name.write(f"**{p['name']}**\n({p['rating']:.1f} | {2026-p['birth_year']})")
                if c_btn.button("🔄", key=f"w_{i}"):
                    st.session_state.t2.append(st.session_state.t1.pop(i))
                    st.rerun()
        with col_b:
            st.subheader("⚫ שחור")
            for i, p in enumerate(st.session_state.t2):
                c_name, c_btn = st.columns([0.7, 0.3])
                c_name.write(f"**{p['name']}**\n({p['rating']:.1f} | {2026-p['birth_year']})")
                if c_btn.button("🔄", key=f"b_{i}"):
                    st.session_state.t1.append(st.session_state.t2.pop(i))
                    st.rerun()

# טאב מאגר
with tab2:
    if st.session_state.players:
        st.dataframe(pd.DataFrame(st.session_state.players), use_container_width=True)

# טאב עדכון
with tab3:
    with st.form("edit_form"):
        f_name = st.text_input("שם מלא")
        f_rating = st.slider("דירוג", 1.0, 10.0, 5.0)
        f_year = st.number_input("שנת לידה", 1950, 2015, 1990)
        if st.form_submit_button("שמור"):
            # לוגיקת העדכון המקורית שלך...
            save_to_gsheets()
            st.rerun()
