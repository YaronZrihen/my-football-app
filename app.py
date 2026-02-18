import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS (נועל את התצוגה הדו-טורית) ---
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    .block-container { padding: 10px !important; max-width: 500px !important; }
    
    /* מכולת הקבוצות - Flexbox קשיח */
    .teams-wrapper {
        display: flex !important;
        flex-direction: row !important;
        gap: 8px !important;
        width: 100% !important;
        margin-top: 15px;
    }
    
    .team-col {
        flex: 1 !important;
        min-width: 0 !important;
        background: #2d3748;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #4a5568;
    }

    .team-h {
        background: #3b82f6;
        color: white;
        text-align: center;
        padding: 8px;
        font-weight: bold;
        font-size: 16px;
    }

    .p-card {
        background: #1e293b;
        margin: 4px;
        padding: 8px;
        border-radius: 4px;
        border-right: 4px solid #60a5fa;
    }

    .p-name { font-size: 16px !important; font-weight: bold; display: block; color: #f8fafc; }
    .p-stats { font-size: 12px !important; color: #22c55e; }

    .t-footer {
        background: #0f172a;
        padding: 8px;
        text-align: center;
        font-size: 13px;
        color: #60a5fa;
        border-top: 1px solid #4a5568;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ---
conn = st.connection("gsheets", type=GSheetsConnection)
if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 30
    r = float(p.get('rating', 5.0))
    return r, 2026 - int(p.get('birth_year', 1996))

# --- 3. ממשק חלוקה ---
st.title("⚽ וולפסון חולון")

tab1, tab2 = st.tabs(["🏃 חלוקה", "📝 ניהול"])

with tab1:
    all_n = sorted([p['name'] for p in st.session_state.players])
    selected = st.pills("מי משחק?", all_n, selection_mode="multi")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            for n in selected:
                s, a = get_stats(n)
                pool.append({'name': n, 'f': s, 'age': a})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        # בניה דינמית של ה-HTML
        def gen_col_html(team_list, title):
            cards = ""
            for p in team_list:
                cards += f"""
                <div class="p-card">
                    <span class="p-name">{p['name']}</span>
                    <span class="p-stats">רמה: {p['f']:.1f} | גיל: {p['age']}</span>
                </div>
                """
            avg_f = sum(p['f'] for p in team_list)/len(team_list) if team_list else 0
            return f"""
            <div class="team-col">
                <div class="team-h">{title}</div>
                {cards}
                <div class="t-footer">ממוצע: {avg_f:.1f}</div>
            </div>
            """

        full_html = f"""
        <div class="teams-wrapper">
            {gen_col_html(st.session_state.t1, "⚪ לבן")}
            {gen_col_html(st.session_state.t2, "⚫ שחור")}
        </div>
        """
        st.markdown(full_html, unsafe_allow_html=True)

        # כפתורי החלפה נוחים מתחת
        st.write("---")
        st.subheader("🔄 החלפת שחקנים")
        c1, c2 = st.columns(2)
        with c1:
            m1 = st.selectbox("מהלבן:", ["--"] + [p['name'] for p in st.session_state.t1])
            if m1 != "--":
                p_obj = next(p for p in st.session_state.t1 if p['name'] == m1)
                st.session_state.t1.remove(p_obj)
                st.session_state.t2.append(p_obj)
                st.rerun()
        with c2:
            m2 = st.selectbox("מהשחור:", ["--"] + [p['name'] for p in st.session_state.t2])
            if m2 != "--":
                p_obj = next(p for p in st.session_state.t2 if p['name'] == m2)
                st.session_state.t2.remove(p_obj)
                st.session_state.t1.append(p_obj)
                st.rerun()
