import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS מינימליסטי - נועל 2 עמודות ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    /* הגדרות בסיס */
    .stApp { background-color: #1a1c23; color: white; direction: rtl; }
    .block-container { padding: 10px !important; }

    /* כפיית 2 עמודות צמודות בכל מכשיר */
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

    /* כרטיס שחקן פשוט */
    .player-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 4px;
        height: 60px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .p-name { font-size: 15px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-stats { font-size: 11px; color: #22c55e; }

    /* כפתור החלפה */
    .stButton button {
        height: 60px !important;
        width: 100% !important;
        background-color: #334155 !important;
        font-size: 20px !important;
        border: none !important;
        border-radius: 6px !important;
    }

    .t-header { text-align: center; font-weight: bold; padding: 10px; border-radius: 6px; margin-bottom: 5px; }
    .t-footer { background: #1e293b; text-align: center; padding: 8px; border-radius: 6px; font-size: 12px; color: #60a5fa; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except:
        st.session_state.players = []

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 30
    return float(p.get('rating', 5.0)), 2026 - int(p.get('birth_year', 1996))

# --- 3. ממשק טאבים ---
st.markdown("<h2 style='text-align:center;'>⚽ וולפסון חולון</h2>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר", "📝 עדכון"])

# --- טאב 1: חלוקה ---
with tab1:
    names = sorted([p['name'] for p in st.session_state.players])
    selected = st.pills("מי הגיע?", names, selection_mode="multi")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = [{'name': n, 'r': get_stats(n)[0], 'a': get_stats(n)[1]} for n in selected]
            pool.sort(key=lambda x: x['r'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        c_left, c_right = st.columns(2)
        
        # קבוצה 1
        with c_left:
            st.markdown('<div class="t-header" style="background:#3b82f6;">⚪ לבן</div>', unsafe_allow_html=True)
            for i, p in enumerate(st.session_state.t1):
                col_p, col_b = st.columns([0.7, 0.3])
                with col_p:
                    st.markdown(f"<div class='player-card'><div class='p-name'>{p['name']}</div><div class='p-stats'>{p['r']:.1f} | {p['a']}</div></div>", unsafe_allow_html=True)
                with col_b:
                    if st.button("🔄", key=f"sw1_{i}"):
                        st.session_state.t2.append(st.session_state.t1.pop(i))
                        st.rerun()
            avg1 = sum(p['r'] for p in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
            st.markdown(f'<div class="t-footer">רמה: {avg1:.1f}</div>', unsafe_allow_html=True)

        # קבוצה 2
        with c_right:
            st.markdown('<div class="t-header" style="background:#4a5568;">⚫ שחור</div>', unsafe_allow_html=True)
            for i, p in enumerate(st.session_state.t2):
                col_p, col_b = st.columns([0.7, 0.3])
                with col_p:
                    st.markdown(f"<div class='player-card'><div class='p-name'>{p['name']}</div><div class='p-stats'>{p['r']:.1f} | {p['a']}</div></div>", unsafe_allow_html=True)
                with col_b:
                    if st.button("🔄", key=f"sw2_{i}"):
                        st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()
            avg2 = sum(p['r'] for p in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0
            st.markdown(f'<div class="t-footer">רמה: {avg2:.1f}</div>', unsafe_allow_html=True)

# --- טאב 2: מאגר ---
with tab2:
    st.dataframe(pd.DataFrame(st.session_state.players)[['name', 'rating', 'birth_year']], use_container_width=True)

# --- טאב 3: עדכון ---
with tab3:
    with st.form("update_form"):
        f_name = st.text_input("שם השחקן")
        f_rate = st.slider("רמה", 1.0, 10.0, 5.0)
        f_year = st.number_input("שנת לידה", 1950, 2015, 1995)
        if st.form_submit_button("שמור"):
            # לוגיקת שמירה ל-GSheets
            st.session_state.players.append({'name': f_name, 'rating': f_rate, 'birth_year': f_year})
            df_to_save = pd.DataFrame(st.session_state.players)
            conn.update(data=df_to_save)
            st.success("נשמר!")
            st.rerun()
