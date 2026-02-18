import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS חסין סלולר ומונע WIDE ---
st.set_page_config(page_title="כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    /* נעילת רוחב האפליקציה */
    .block-container { 
        max-width: 100% !important; 
        padding: 5px !important; 
    }
    .stApp { background-color: #1a1c23; color: white; direction: rtl; }
    
    /* הגדרות טבלה */
    .main-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed; /* חשוב מאוד למניעת WIDE */
    }
    .team-cell {
        width: 50%;
        vertical-align: top;
        padding: 2px;
    }

    /* כרטיס שחקן בתוך התא */
    .player-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 5px;
        height: 50px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        overflow: hidden;
    }
    .p-name { font-size: 14px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-stats { font-size: 11px; color: #22c55e; }

    /* עיצוב כפתור 🔄 בתוך העמודה הקטנה */
    [data-testid="column"] button {
        height: 50px !important;
        width: 100% !important;
        min-width: 0 !important;
        padding: 0 !important;
        background-color: #334155 !important;
        border: none !important;
        font-size: 18px !important;
        color: white !important;
    }

    .t-header { text-align: center; font-weight: bold; padding: 8px; border-radius: 4px; font-size: 15px; margin-bottom: 5px; }
    .t-footer { background: #1e293b; text-align: center; padding: 5px; border-radius: 4px; font-size: 12px; color: #60a5fa; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ונתונים ---
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
    # יצירת מבנה הטבלה
    st.write("") # מרווח
    
    # כותרות הקבוצות (בתוך טבלה)
    st.markdown(f"""
    <table class="main-table">
        <tr>
            <td class="team-cell"><div class="t-header" style="background:#3b82f6;">⚪ לבן</div></td>
            <td class="team-cell"><div class="t-header" style="background:#4a5568;">⚫ שחור</div></td>
        </tr>
    </table>
    """, unsafe_allow_html=True)

    # הצגת השחקנים - שילוב של טבלה עם כפתורי Streamlit
    t1 = st.session_state.t1
    t2 = st.session_state.t2
    max_len = max(len(t1), len(t2))

    for i in range(max_len):
        col_left, col_right = st.columns(2) # אלו שתי העמודות הראשיות (50/50)
        
        # צד לבן
        with col_left:
            if i < len(t1):
                p = t1[i]
                c1, c2 = st.columns([0.75, 0.25])
                with c1:
                    st.markdown(f"<div class='player-box'><div class='p-name'>{p['name']}</div><div class='p-stats'>{p['r']:.1f} | {p['a']}</div></div>", unsafe_allow_html=True)
                with c2:
                    if st.button("🔄", key=f"sw_w_{i}"):
                        st.session_state.t2.append(st.session_state.t1.pop(i))
                        st.rerun()
            else: st.write("")

        # צד שחור
        with col_right:
            if i < len(t2):
                p = t2[i]
                c1, c2 = st.columns([0.75, 0.25])
                with c1:
                    st.markdown(f"<div class='player-box'><div class='p-name'>{p['name']}</div><div class='p-stats'>{p['r']:.1f} | {p['a']}</div></div>", unsafe_allow_html=True)
                with c2:
                    if st.button("🔄", key=f"sw_b_{i}"):
                        st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()
            else: st.write("")

    # סיכום רמה בתחתית
    avg1 = sum(p['r'] for p in t1)/len(t1) if t1 else 0
    avg2 = sum(p['r'] for p in t2)/len(t2) if t2 else 0
    
    st.markdown(f"""
    <table class="main-table">
        <tr>
            <td class="team-cell"><div class="t-footer">רמה: {avg1:.1f}</div></td>
            <td class="team-cell"><div class="t-footer">רמה: {avg2:.1f}</div></td>
        </tr>
    </table>
    """, unsafe_allow_html=True)
