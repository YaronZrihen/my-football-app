import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS "נועל" - מונע WIDE מוחלט ---
st.set_page_config(page_title="כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    /* מניעת WIDE וגלישה */
    .block-container { max-width: 500px !important; padding: 10px !important; }
    .stApp { background-color: #1a1c23; color: white; direction: rtl; }
    
    /* טבלה חסינת סלולר */
    .main-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }
    .team-col {
        width: 50%;
        vertical-align: top;
        padding: 4px;
    }
    .header {
        text-align: center;
        padding: 10px;
        border-radius: 8px 8px 0 0;
        font-weight: bold;
        font-size: 16px;
    }
    .player-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        padding: 8px;
        margin-top: 4px;
        border-radius: 4px;
        height: 50px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .p-name { font-size: 15px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-stats { font-size: 11px; color: #22c55e; }
    
    .footer {
        background: #1e293b;
        text-align: center;
        padding: 6px;
        font-size: 12px;
        border-radius: 0 0 8px 8px;
        color: #60a5fa;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. נתונים ולוגיקה ---
conn = st.connection("gsheets", type=GSheetsConnection)
if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 30
    return float(p.get('rating', 5.0)), 2026 - int(p.get('birth_year', 1996))

# --- 3. ממשק ---
st.markdown("<h3 style='text-align:center;'>⚽ וולפסון חולון</h3>", unsafe_allow_html=True)

names = sorted([p['name'] for p in st.session_state.players])
selected = st.pills("מי משחק?", names, selection_mode="multi")

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
    t1, t2 = st.session_state.t1, st.session_state.t2
    
    # בניית שורות השחקנים לטבלה
    max_len = max(len(t1), len(t2))
    rows_html = ""
    for i in range(max_len):
        p1 = t1[i] if i < len(t1) else None
        p2 = t2[i] if i < len(t2) else None
        
        cell1 = f"<div class='player-card'><div class='p-name'>{p1['name']}</div><div class='p-stats'>{p1['r']:.1f} | {p1['a']}</div></div>" if p1 else ""
        cell2 = f"<div class='player-card'><div class='p-name'>{p2['name']}</div><div class='p-stats'>{p2['r']:.1f} | {p2['a']}</div></div>" if p2 else ""
        
        rows_html += f"<tr><td class='team-col'>{cell1}</td><td class='team-col'>{cell2}</td></tr>"

    avg1 = sum(p['r'] for p in t1)/len(t1) if t1 else 0
    avg2 = sum(p['r'] for p in t2)/len(t2) if t2 else 0

    # הזרקת הטבלה (חסין WIDE)
    st.markdown(f"""
    <table class="main-table">
        <tr>
            <td class="team-col"><div class="header" style="background:#3b82f6;">⚪ לבן</div></td>
            <td class="team-col"><div class="header" style="background:#4a5568;">⚫ שחור</div></td>
        </tr>
        {rows_html}
        <tr>
            <td class="team-col"><div class="footer">רמה: {avg1:.1f}</div></td>
            <td class="team-col"><div class="footer">רמה: {avg2:.1f}</div></td>
        </tr>
    </table>
    """, unsafe_allow_html=True)

    # --- מנגנון החלפה מהיר (מחוץ לטבלה כדי שלא ישבור אותה) ---
    st.write("")
    with st.expander("🔄 החלפת שחקן"):
        c1, c2 = st.columns(2)
        with c1:
            m1 = st.selectbox("מהלבן:", ["--"] + [p['name'] for p in t1])
        with c2:
            m2 = st.selectbox("מהשחור:", ["--"] + [p['name'] for p in t2])
        
        if st.button("בצע החלפה ✅", use_container_width=True):
            if m1 != "--" and m2 != "--":
                p1_obj = next(p for p in st.session_state.t1 if p['name'] == m1)
                p2_obj = next(p for p in st.session_state.t2 if p['name'] == m2)
                st.session_state.t1.remove(p1_obj)
                st.session_state.t2.remove(p2_obj)
                st.session_state.t1.append(p2_obj)
                st.session_state.t2.append(p1_obj)
                st.rerun()

# --- שאר הקוד (מאגר/עדכון) ---
with st.sidebar:
    st.header("ניהול מאגר")
    if st.button("הצג שחקנים"):
        st.write(st.session_state.players)
