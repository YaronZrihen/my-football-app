import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב CSS מקיף לכל הדפים ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label { text-align: right !important; direction: rtl; }

    /* עיצוב כרטיסי שחקן במאגר */
    .database-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }

    /* נעילת 2 עמודות - רק בדף חלוקה */
    .locked-columns [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 6px !important;
    }
    .locked-columns [data-testid="column"] {
        flex: 1 1 50% !important;
        min-width: 45% !important;
    }

    /* שורת שחקן צפופה (בחלוקה) */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 4px 8px;
        margin-bottom: 3px;
        display: flex;
        justify-content: flex-start;
        align-items: center;
        height: 30px;
    }
    .p-text { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-score { color: #22c55e; font-size: 11px; margin-right: 5px; }

    /* כפתורי 🔄 */
    .stButton > button[key^="m_"] {
        width: 100% !important;
        height: 24px !important;
        padding: 0 !important;
        background-color: #3d495d !important;
    }
    
    /* טבלת מאזן */
    .stats-table { width: 100%; margin-top: 15px; border-collapse: collapse; background: #2d3748; font-size: 12px; }
    .stats-table td { border: 1px solid #4a5568; padding: 6px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור ונתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except:
        st.session_state.players = []

def save_data():
    df = pd.DataFrame(st.session_state.players)
    conn.update(data=df)
    st.cache_data.clear()

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 1995
    r = float(p.get('rating', 5.0))
    try:
        pr = json.loads(p.get('peer_ratings', '{}'))
        peers = [float(v) for v in pr.values()]
        avg_p = sum(peers)/len(peers) if peers else 0
    except: avg_p = 0
    return (r + avg_p) / 2 if avg_p > 0 else r, int(p.get('birth_year', 1995))

# --- 3. תפריט ---
st.title("⚽ ניהול כדורגל")
menu = st.pills("תפריט", ["חלוקה", "מאגר", "הרשמה"], default="חלוקה")

# --- 4. דף חלוקה ---
if menu == "חלוקה":
    all_names = sorted([p['name'] for p in st.session_state.players])
    sel = st.pills(f"מי הגיע? ({len(st.session_state.get('p_sel', []))})", all_names, selection_mode="multi", key="p_sel")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if sel:
            pool = []
            curr_y = datetime.now().year
            for n in sel:
                s, b = get_stats(n)
                pool.append({'name': n, 'f': s, 'age': curr_y - b})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2
        else: st.error("בחר שחקנים")

    if 't1' in st.session_state and sel:
        st.markdown("<div class='locked-columns'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        for col, team, label, pfx in zip([c1, c2], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"], ["w", "b"]):
            with col:
                st.markdown(f"<p style='text-align:center;font-weight:bold;font-size:14px;'>{label} ({len(team)})</p>", unsafe_allow_html=True)
                for i, p in enumerate(team):
                    st.markdown(f"<div class='p-box'><span class='p-text'>{p['name']} <span class='p-score'>({p['f']:.1f})</span></span></div>", unsafe_allow_html=True)
                    if st.button("🔄", key=f"m_{pfx}_{i}"):
                        if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                        else: st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
        # מאזן
        s1, s2 = sum(x['f'] for x in st.session_state.t1), sum(x['f'] for x in st.session_state.t2)
        a1 = sum(x['age'] for x in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
        a2 = sum(x['age'] for x in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0
        st.markdown(f"<table class='stats-table'><tr><td><b>כוח</b></td><td>⚪ {s1:.1f}</td><td>⚫ {s2:.1f}</td></tr><tr><td><b>גיל</b></td><td>⚪ {a1:.1f}</td><td>⚫ {a2:.1f}</td></tr></table>", unsafe_allow_html=True)

# --- 5. דף מאגר (משופזר) ---
elif menu == "מאגר":
    st.header("🗄️ מאגר שחקנים")
    for i, p in enumerate(st.session_state.players):
        with st.container():
            st.markdown(f"""<div class='database-card'>
                <b>{p['name']}</b><br>
                <small>שנת לידה: {p['birth_year']} | דירוג: {p['rating']}</small>
            </div>""", unsafe_allow_html=True)
            c1, c2 = st.columns([1, 1])
            with c2:
                if st.button("🗑️ מחק", key=f"del_{i}", use_container_width=True):
                    st.session_state.players.pop(i)
                    save_data()
                    st.rerun()
            st.write("---")

# --- 6. דף הרשמה (מעוצב) ---
elif menu == "הרשמה":
    st.header("📝 רישום שחקן")
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("שם מלא:")
        year = st.number_input("שנת לידה:", 1950, 2026, 1995)
        rate = st.select_slider("רמה עצמית (1-10):", options=range(1, 11), value=5)
        if st.form_submit_button("שמור שחקן ✅", use_container_width=True):
            if name:
                st.session_state.players.append({"name": name, "birth_year": year, "rating": rate, "peer_ratings": "{}"})
                save_data()
                st.success(f"השחקן {name} נוסף למערכת!")
            else: st.error("חובה להזין שם")

if st.sidebar.button("רענן נתונים מ-Sheets 🔄"):
    st.cache_data.clear()
    st.rerun()
    
