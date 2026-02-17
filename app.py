import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב CSS (יציב, RTL, ונעילת עמודות) ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span { text-align: right !important; direction: rtl; }

    /* נעילת שתי עמודות בסלולר - מוגדר רק לאזור הקבוצות */
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

    /* כרטיס שחקן צפוף לחלוקה */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 4px 8px;
        margin-bottom: 3px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 32px;
    }
    .p-text { font-size: 13px; font-weight: 500; }
    .p-score { color: #22c55e; font-size: 11px; font-weight: bold; }

    /* כפתור 🔄 */
    .stButton > button[key^="m_"] {
        width: 100% !important;
        height: 24px !important;
        padding: 0 !important;
        background-color: #3d495d !important;
        font-size: 11px !important;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ולוגיקה ---
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

def get_info(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 1995
    r = float(p.get('rating', 5.0))
    try:
        pr = json.loads(p.get('peer_ratings', '{}'))
        peers = [float(v) for v in pr.values()]
        avg_p = sum(peers)/len(peers) if peers else 0
    except: avg_p = 0
    return (r + avg_p) / 2 if avg_p > 0 else r, int(p.get('birth_year', 1995))

# --- 3. תפריט ניווט ---
st.title("⚽ ניהול כדורגל")
menu = st.pills("תפריט", ["חלוקה", "מאגר", "הרשמה/עריכה"], default="חלוקה")

# --- 4. דף חלוקה ---
if menu == "חלוקה":
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected = st.multiselect(f"מי הגיע? ({len(all_names)})", all_names)

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            y = datetime.now().year
            for n in selected:
                s, b = get_info(n)
                pool.append({'name': n, 'f': s, 'age': y-b})
            pool.sort(key=lambda x: x['f'], reverse=True)
            st.session_state.t1, st.session_state.t2 = pool[0::2], pool[1::2]
        else:
            st.warning("בחר שחקנים קודם")

    if 't1' in st.session_state and selected:
        st.markdown("<div class='locked-columns'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        for col, team, label, pfx in zip([c1, c2], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"], ["w", "b"]):
            with col:
                st.markdown(f"<p style='text-align:center;font-weight:bold;'>{label} ({len(team)})</p>", unsafe_allow_html=True)
                for i, p in enumerate(team):
                    st.markdown(f"<div class='p-box'><span class='p-text'>{p['name']}</span> <span class='p-score'>({p['f']:.1f})</span></div>", unsafe_allow_html=True)
                    if st.button("🔄", key=f"m_{pfx}_{i}"):
                        if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                        else: st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        s1, s2 = sum(x['f'] for x in st.session_state.t1), sum(x['f'] for x in st.session_state.t2)
        a1 = sum(x['age'] for x in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
        a2 = sum(x['age'] for x in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0
        st.write(f"**מאזן כוח:** ⚪ {s1:.1f} | ⚫ {s2:.1f}")
        st.write(f"**גיל ממוצע:** ⚪ {a1:.1f} | ⚫ {a2:.1f}")

# --- 5. דף מאגר ---
elif menu == "מאגר":
    st.subheader("ניהול מאגר שחקנים")
    for i, p in enumerate(st.session_state.players):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{p['name']}** (יליד {p['birth_year']}) - דירוג: {p['rating']}")
        with col2:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.players.pop(i)
                save_data()
                st.rerun()

# --- 6. דף הרשמה ועריכה ---
elif menu == "הרשמה/עריכה":
    st.subheader("עדכון או הוספת שחקן")
    all_names = ["--- שחקן חדש ---"] + sorted([p['name'] for p in st.session_state.players])
    choice = st.selectbox("בחר שחקן לעריכה:", all_names)
    
    with st.form("reg_form"):
        p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
        new_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "")
        new_year = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
        new_rate = st.slider("דירוג (1-10):", 1, 10, int(p_data['rating']) if p_data else 5)
        
        if st.form_submit_button("שמור שינויים ✅"):
            if new_name:
                updated_p = {"name": new_name, "birth_year": new_year, "rating": new_rate, "peer_ratings": p_data['peer_ratings'] if p_data else "{}"}
                if p_data:
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                    st.session_state.players[idx] = updated_p
                else:
                    st.session_state.players.append(updated_p)
                save_data()
                st.success("הנתונים נשמרו!")
                st.rerun()
