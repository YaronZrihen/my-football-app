import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב UI (יישור לימין וצפיפות) ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span { text-align: right !important; direction: rtl; }

    /* נעילת שתי עמודות בסלולר - רק בחלק של הקבוצות */
    .mobile-columns [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    .mobile-columns [data-testid="column"] {
        flex: 1 1 50% !important;
        min-width: 45% !important;
    }

    /* כרטיס שחקן צפוף לחלוקה */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 4px 8px;
        margin-bottom: 2px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 32px;
    }
    .p-text { font-size: 13px; }
    .p-score { color: #22c55e; font-size: 11px; font-weight: bold; }

    /* כפתור 🔄 */
    .stButton > button[key^="m_"] {
        width: 100% !important;
        height: 24px !important;
        padding: 0 !important;
        background-color: #3d495d !important;
        font-size: 11px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. נתונים (חיבור קשיח ל-GSheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except:
        st.session_state.players = []

def save_to_sheets():
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

# --- 3. ניווט טאבים (כמו שאהבת) ---
tab = st.radio("תפריט", ["👤 שחקן/הרשמה", "⚙️ ניהול/חלוקה"], horizontal=True, label_visibility="collapsed")

# --- 4. דף שחקן / הרשמה ---
if tab == "👤 שחקן/הרשמה":
    st.subheader("רישום ועדכון פרטים")
    names = sorted([p['name'] for p in st.session_state.players])
    options = ["---", "🆕 שחקן חדש"] + names
    
    sel = st.selectbox("בחר שם לעדכון או רישום:", options)
    
    with st.form("player_form"):
        p_data = next((p for p in st.session_state.players if p['name'] == sel), None)
        f_name = st.text_input("שם מלא:", value=sel if sel not in ["---", "🆕 שחקן חדש"] else "")
        y = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
        rate = st.slider("דירוג עצמי:", 1, 10, int(p_data['rating']) if p_data else 5)
        
        if st.form_submit_button("שמור נתונים ✅"):
            if f_name:
                new_p = {"name": f_name, "birth_year": y, "rating": rate, "peer_ratings": p_data['peer_ratings'] if p_data else "{}"}
                idx = next((i for i, x in enumerate(st.session_state.players) if x['name'] == f_name), None)
                if idx is not None: st.session_state.players[idx] = new_p
                else: st.session_state.players.append(new_p)
                save_to_sheets()
                st.success("נשמר בהצלחה!")
                st.rerun()

# --- 5. דף ניהול וחלוקה ---
else:
    pwd = st.text_input("סיסמת מנהל:", type="password")
    if pwd == "1234":
        mode = st.segmented_control("מצב:", ["חלוקה", "מאגר"], default="חלוקה")
        
        if mode == "מאגר":
            st.write("### רשימת שחקנים")
            for i, p in enumerate(st.session_state.players):
                c1, c2 = st.columns([4, 1])
                with c1: st.write(f"**{p['name']}** ({p['birth_year']})")
                with c2:
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.players.pop(i)
                        save_to_sheets()
                        st.rerun()

        else: # מצב חלוקה
            names = [p['name'] for p in st.session_state.players]
            selected = st.multiselect(f"מי הגיע? ({len(names)})", names)
            
            if st.button("חלק קבוצות 🚀", use_container_width=True):
                pool = []
                curr_y = datetime.now().year
                for n in selected:
                    s, b = get_player_stats(n)
                    pool.append({'name': n, 'f': s, 'age': curr_y - b})
                pool.sort(key=lambda x: x['f'], reverse=True)
                st.session_state.t1, st.session_state.t2 = pool[0::2], pool[1::2]

            if 't1' in st.session_state and selected:
                st.markdown("<div class='mobile-columns'>", unsafe_allow_html=True)
                col_a, col_b = st.columns(2)
                for col, team, label, pfx in zip([col_a, col_b], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"], ["w", "b"]):
                    with col:
                        st.markdown(f"<p style='text-align:center;font-weight:bold;'>{label} ({len(team)})</p>", unsafe_allow_html=True)
                        for i, p in enumerate(team):
                            st.markdown(f"<div class='p-box'><span class='p-text'>{p['name']}</span> <span class='p-score'>({p['f']:.1f})</span></div>", unsafe_allow_html=True)
                            if st.button("🔄", key=f"m_{pfx}_{i}"):
                                if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                                else: st.session_state.t1.append(st.session_state.t2.pop(i))
                                st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

                # מאזן גיל וכוח
                s1, s2 = sum(x['f'] for x in st.session_state.t1), sum(x['f'] for x in st.session_state.t2)
                a1 = sum(x['age'] for x in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
                a2 = sum(x['age'] for x in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0
                st.write(f"**כוח:** ⚪ {s1:.1f} | ⚫ {s2:.1f}")
                st.write(f"**גיל ממוצע:** ⚪ {a1:.1f} | ⚫ {a2:.1f}")
                
