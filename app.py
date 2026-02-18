import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. הגדרות דף - הכי בסיסי שיש
st.set_page_config(page_title="וולפסון 2026", layout="centered")

# 2. CSS מינימליסטי - רק כדי ששתי עמודות יישארו אחת ליד השנייה בסלולר
st.markdown("""
    <style>
    .stApp { direction: rtl; }
    /* כפיית שתי עמודות בסלולר */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 5px !important;
    }
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 0 !important;
    }
    /* עיצוב כפתור 🔄 שיהיה קומפקטי */
    .stButton button {
        width: 100%;
        padding: 5px 0;
        font-size: 18px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. חיבור נתונים
conn = st.connection("gsheets", type=GSheetsConnection)
if 'players' not in st.session_state:
    df = conn.read(ttl="0")
    st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')

# 4. לוגיקה
def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    r = float(p.get('rating', 5.0)) if p else 5.0
    a = 2026 - int(p.get('birth_year', 1996)) if p else 30
    return r, a

# 5. ממשק ראשי
st.title("⚽ וולפסון חולון")

all_names = sorted([p['name'] for p in st.session_state.players])
selected = st.pills("מי משחק?", all_names, selection_mode="multi")

if st.button("חלק קבוצות 🚀", use_container_width=True):
    if selected:
        pool = [{'name': n, 'r': get_stats(n)[0], 'a': get_stats(n)[1]} for n in selected]
        pool.sort(key=lambda x: x['r'], reverse=True)
        t1, t2 = [], []
        for i, p in enumerate(pool):
            if i % 4 == 0 or i % 4 == 3: t1.append(p)
            else: t2.append(p)
        st.session_state.t1, st.session_state.t2 = t1, t2

# 6. הצגת הקבוצות
if 't1' in st.session_state and selected:
    col_w, col_b = st.columns(2)
    
    with col_w:
        st.subheader("⚪ לבן")
        for i, p in enumerate(st.session_state.t1):
            c1, c2 = st.columns([0.7, 0.3])
            c1.write(f"**{p['name']}** \n({p['r']:.1f} | {p['a']})")
            if c2.button("🔄", key=f"w_{i}"):
                st.session_state.t2.append(st.session_state.t1.pop(i))
                st.rerun()
        
    with col_b:
        st.subheader("⚫ שחור")
        for i, p in enumerate(st.session_state.t2):
            c1, c2 = st.columns([0.7, 0.3])
            c1.write(f"**{p['name']}** \n({p['r']:.1f} | {p['a']})")
            if c2.button("🔄", key=f"b_{i}"):
                st.session_state.t1.append(st.session_state.t2.pop(i))
                st.rerun()

    # ממוצעים למטה
    st.divider()
    m1, m2 = st.columns(2)
    avg1 = sum(p['r'] for p in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
    avg2 = sum(p['r'] for p in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0
    m1.metric("רמה לבן", f"{avg1:.1f}")
    m2.metric("רמה שחור", f"{avg2:.1f}")
