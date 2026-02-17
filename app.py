import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב CSS סופי (הכל כלול) ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span { text-align: right !important; direction: rtl; }
    .block-container { padding: 5px !important; }

    /* הקטנה דרסטית של כותרות */
    .main-title { font-size: 18px !important; text-align: center !important; font-weight: bold; margin-bottom: 10px; color: #60a5fa; }
    .team-header { text-align: center !important; font-size: 12px !important; font-weight: bold; margin-bottom: 4px; }

    /* נעילת שתי עמודות בסלולר */
    .team-section [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    .team-section [data-testid="column"] {
        flex: 1 1 50% !important;
        min-width: 45% !important;
    }

    /* שורת שחקן צפופה */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 2px 8px;
        margin-bottom: 2px;
        display: flex;
        justify-content: flex-start;
        align-items: center;
        height: 26px;
    }
    .p-text { font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-score { color: #22c55e; font-size: 10px; margin-right: 4px; opacity: 0.9; }

    /* כפתור 🔄 קטן */
    .stButton > button[key^="m_"] {
        width: 100% !important;
        height: 20px !important;
        padding: 0 !important;
        font-size: 9px !important;
        background-color: #3d495d !important;
        margin-bottom: 8px;
    }

    /* טבלת מאזן */
    .stats-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }
    .stats-table td { border: 1px solid #4a5568; padding: 4px; text-align: center; background: #2d3748; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. נתונים ---
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

def get_player_stats(name):
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
st.markdown("<div class='main-title'>⚽ ניהול כדורגל</div>", unsafe_allow_html=True)
menu = st.pills("תפריט", ["חלוקה", "מאגר שחקנים", "הרשמה/עריכה"], default="חלוקה")

# --- 4. דף חלוקה ---
if menu == "חלוקה":
    all_names = sorted([p['name'] for p in st.session_state.players])
    # מונה שחקנים בתוך ה-pills
    sel_count = len(st.session_state.get('p_sel', []))
    selected = st.pills(f"מי הגיע? ({sel_count})", all_names, selection_mode="multi", key="p_sel")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            curr_y = datetime.now().year
            for n in selected:
                s, b = get_player_stats(n)
                pool.append({'name': n, 'f': s, 'age': curr_y - b})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        st.markdown("<div class='team-section'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        for col, team, label, pfx in zip([c1, c2], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"], ["w", "b"]):
            with col:
                st.markdown(f"<p class='team-header'>{label} ({len(team)})</p>", unsafe_allow_html=True)
                for i, p in enumerate(team):
                    st.markdown(f"<div class='p-box'><span class='p-text'>{p['name']} <span class='p-score'>({p['f']:.1f})</span></span></div>", unsafe_allow_html=True)
                    if st.button("🔄", key=f"m_{pfx}_{i}"):
                        if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                        else: st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # טבלת מאזן (כוח וגיל)
        s1, s2 = sum(x['f'] for x in st.session_state.t1), sum(x['f'] for x in st.session_state.t2)
        a1 = sum(x['age'] for x in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
        a2 = sum(x['age'] for x in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0
        st.markdown(f"<table class='stats-table'><tr><td><b>נתון</b></td><td>⚪ לבן</td><td>⚫ שחור</td></tr><tr><td><b>כוח</b></td><td>{s1:.1f}</td><td>{s2:.1f}</td></tr><tr><td><b>גיל</b></td><td>{a1:.1f}</td><td>{a2:.1f}</td></tr></table>", unsafe_allow_html=True)

# --- 5. דף מאגר ---
elif menu == "מאגר שחקנים":
    st.subheader("ניהול ומחיקה")
    for i, p in enumerate(st.session_state.players):
        col1, col2 = st.columns([5, 1])
        with col1: st.write(f"**{p['name']}** (יליד {p['birth_year']})")
        with col2:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.players.pop(i)
                save_data()
                st.rerun()

# --- 6. דף הרשמה/עריכה ---
elif menu == "הרשמה/עריכה":
    st.subheader("עדכון פרטים")
    names = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    choice = st.selectbox("בחר שחקן לעריכה:", names)
    
    with st.form("reg_form"):
        p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "")
        f_year = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
        f_rate = st.slider("דירוג (1-10):", 1, 10, int(p_data['rating']) if p_data else 5)
        if st.form_submit_button("שמור שינויים ✅"):
            if f_name:
                updated_p = {"name": f_name, "birth_year": f_year, "rating": f_rate, "peer_ratings": p_data['peer_ratings'] if p_data else "{}"}
                if p_data:
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                    st.session_state.players[idx] = updated_p
                else: st.session_state.players.append(updated_p)
                save_data()
                st.success("נשמר!")
                st.rerun()
