import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. נעילת רוחב מוחלטת (Anti-Scroll) ---
st.set_page_config(page_title="כדורגל וולפסון", layout="centered")

st.markdown("""
    <style>
    /* ביטול גלישה רוחבית בכל רמות הדף */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
        overflow-x: hidden !important;
        width: 100vw !important;
        position: relative;
    }

    .block-container { 
        padding: 5px !important; 
        max-width: 100% !important; 
    }

    /* כפיית 2 עמודות צמודות ברוחב 50% מדויק */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        gap: 4px !important;
    }
    
    [data-testid="column"] {
        /* חישוב דינמי של חצי מסך פחות מרווחים כדי שלא יגלוש */
        width: calc(50vw - 10px) !important;
        flex: none !important;
        min-width: 0 !important;
    }

    /* כרטיס שחקן צפוף וקריא */
    .p-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 6px;
        padding: 6px;
        margin-bottom: 4px;
        height: 60px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .p-name { 
        font-size: 15px !important; 
        font-weight: bold; 
        color: white; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
    }
    .p-stats { font-size: 11px !important; color: #22c55e; }

    /* כפתור 🔄 דק שלא תופס מקום */
    [data-testid="column"] button {
        height: 60px !important;
        width: 100% !important;
        min-width: 0 !important;
        padding: 0 !important;
        background-color: #334155 !important;
        border: none !important;
        font-size: 20px !important;
    }

    .t-head { text-align: center; font-weight: bold; padding: 10px; border-radius: 6px 6px 0 0; font-size: 16px; }
    .t-foot { background: #1e293b; text-align: center; padding: 6px; border-radius: 0 0 6px 6px; font-size: 12px; color: #60a5fa; }
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

tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר", "📝 עדכון"])

with tab1:
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
        c_white, c_black = st.columns(2)
        
        for col, team, label, color, tid in zip([c_white, c_black], 
                                               [st.session_state.t1, st.session_state.t2], 
                                               ["⚪ לבן", "⚫ שחור"], ["#3b82f6", "#4a5568"], ["t1", "t2"]):
            with col:
                st.markdown(f"<div class='t-head' style='background:{color};'>{label}</div>", unsafe_allow_html=True)
                for i, p in enumerate(team):
                    # עמודות פנימיות - שם וכפתור
                    ci1, ci2 = st.columns([0.7, 0.3])
                    with ci1:
                        st.markdown(f"""<div class='p-card'>
                            <div class='p-name'>{p['name']}</div>
                            <div class='p-stats'>{p['r']:.1f} | {p['a']}</div>
                        </div>""", unsafe_allow_html=True)
                    with ci2:
                        if st.button("🔄", key=f"sw_{tid}_{i}"):
                            if tid == "t1": st.session_state.t2.append(st.session_state.t1.pop(i))
                            else: st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()
                
                if team:
                    avg = sum(x['r'] for x in team)/len(team)
                    st.markdown(f"<div class='t-foot'>רמה: {avg:.1f}</div>", unsafe_allow_html=True)

with tab2:
    for p in st.session_state.players:
        st.write(f"👤 {p['name']} (רמה {p['rating']})")

with tab3:
    st.write("טופס עדכון (כמו בגרסאות הקודמות)")
