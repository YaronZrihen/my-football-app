import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. הגדרות דף ונעילה נגד WIDE
st.set_page_config(page_title="וולפסון 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { direction: rtl; }
    /* כפיית 2 עמודות בסלולר בלי שבירה ובלי WIDE */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 0 !important;
    }
    /* עיצוב כפתור 🔄 קומפקטי */
    .stButton button {
        width: 100% !important;
        padding: 0 !important;
        height: 45px !important;
        font-size: 20px !important;
    }
    /* מניעת רווחים מיותרים */
    .stMarkdown p { margin-bottom: 0px; }
    </style>
    """, unsafe_allow_html=True)

# 2. חיבור נתונים
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

# 3. טאבים - כל הקוד חוזר
st.title("⚽ וולפסון חולון")
tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון פרטים"])

# --- טאב 1: חלוקת קבוצות ---
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
                    'r': float(p_data.get('rating', 5.0)), 
                    'a': 2026 - int(p_data.get('birth_year', 1996))
                })
            
            pool.sort(key=lambda x: x['r'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        # עמודות ראשיות (לבן מול שחור)
        col_white, col_black = st.columns(2)
        
        with col_white:
            st.markdown("<h3 style='text-align:center;'>⚪ לבן</h3>", unsafe_allow_html=True)
            for i, p in enumerate(st.session_state.t1):
                # שורה פנימית: שם וכפתור
                c_name, c_btn = st.columns([0.7, 0.3])
                c_name.markdown(f"**{p['name']}**\n{p['r']:.1f} | {p['a']}")
                if c_btn.button("🔄", key=f"sw_w_{i}"):
                    st.session_state.t2.append(st.session_state.t1.pop(i))
                    st.rerun()
            avg1 = sum(p['r'] for p in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
            st.metric("ממוצע לבן", f"{avg1:.1f}")

        with col_black:
            st.markdown("<h3 style='text-align:center;'>⚫ שחור</h3>", unsafe_allow_html=True)
            for i, p in enumerate(st.session_state.t2):
                # שורה פנימית: שם וכפתור
                c_name, c_btn = st.columns([0.7, 0.3])
                c_name.markdown(f"**{p['name']}**\n{p['r']:.1f} | {p['a']}")
                if c_btn.button("🔄", key=f"sw_b_{i}"):
                    st.session_state.t1.append(st.session_state.t2.pop(i))
                    st.rerun()
            avg2 = sum(p['r'] for p in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0
            st.metric("ממוצע שחור", f"{avg2:.1f}")

# --- טאב 2: מאגר שחקנים ---
with tab2:
    if st.session_state.players:
        df_display = pd.DataFrame(st.session_state.players)
        st.dataframe(df_display[['name', 'rating', 'birth_year']], use_container_width=True)
    else:
        st.write("המאגר ריק.")

# --- טאב 3: עדכון פרטים ---
with tab3:
    st.subheader("הוספת / עדכון שחקן")
    with st.form("update_form"):
        new_name = st.text_input("שם מלא")
        new_rating = st.slider("רמה (1-10)", 1.0, 10.0, 5.0)
        new_year = st.number_input("שנת לידה", 1950, 2020, 1995)
        
        if st.form_submit_button("שמור שינויים"):
            if new_name:
                # בדיקה אם קיים
                existing = next((p for p in st.session_state.players if p['name'] == new_name), None)
                if existing:
                    existing['rating'] = new_rating
                    existing['birth_year'] = new_year
                else:
                    st.session_state.players.append({
                        'name': new_name, 
                        'rating': new_rating, 
                        'birth_year': new_year
                    })
                save_to_gsheets()
                st.success(f"הנתונים של {new_name} עודכנו!")
                st.rerun()
            else:
                st.error("חובה להזין שם")
