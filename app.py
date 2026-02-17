import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב CSS ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span { text-align: right !important; direction: rtl; }
    .block-container { padding: 5px !important; }
    .main-title { font-size: 18px !important; text-align: center !important; font-weight: bold; margin-bottom: 10px; color: #60a5fa; }
    
    .database-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 5px;
        text-align: right;
    }
    .card-title { font-size: 16px; font-weight: bold; color: #60a5fa; margin-bottom: 2px; }
    .card-detail { font-size: 13px; color: #cbd5e0; margin-bottom: 2px; }

    div[data-testid="column"] button {
        width: 100% !important;
        padding: 4px !important;
        height: 35px !important;
    }
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
    pr = p.get('peer_ratings', '{}')
    if isinstance(pr, str):
        try: pr = json.loads(pr)
        except: pr = {}
    peers = [float(v) for v in pr.values()] if isinstance(pr, dict) else []
    avg_p = sum(peers)/len(peers) if peers else 0
    return (r + avg_p) / 2 if avg_p > 0 else r, int(p.get('birth_year', 1995))

# --- 3. ניהול ניווט חכם ---
# אתחול משתני מצב אם הם לא קיימים
if 'menu_selection' not in st.session_state:
    st.session_state.menu_selection = "חלוקה"
if 'edit_player_name' not in st.session_state:
    st.session_state.edit_player_name = "🆕 שחקן חדש"

st.markdown("<div class='main-title'>⚽ ניהול כדורגל</div>", unsafe_allow_html=True)

# יצירת התפריט עם ערך דינמי
menu_options = ["חלוקה", "מאגר שחקנים", "עדכון/הרשמה"]
menu = st.pills("תפריט", menu_options, key="pills_nav", default=st.session_state.menu_selection)

# עדכון ה-state לפי הבחירה בתפריט
st.session_state.menu_selection = menu

# --- 4. דף חלוקה ---
if st.session_state.menu_selection == "חלוקה":
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected = st.pills(f"מי הגיע? ({len(st.session_state.get('p_sel', []))})", all_names, selection_mode="multi", key="p_sel")
    
    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            for n in selected:
                s, b = get_player_stats(n)
                pool.append({'name': n, 'f': s, 'age': 2026 - b})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        c1, c2 = st.columns(2)
        for col, team, label, pfx in zip([c1, c2], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"], ["w", "b"]):
            with col:
                st.markdown(f"<p style='text-align:center;font-size:12px;font-weight:bold;'>{label}</p>", unsafe_allow_html=True)
                for i, p in enumerate(team):
                    st.markdown(f"<div style='background:#2d3748; border-radius:4px; padding:2px 8px; margin-bottom:2px; height:26px; border:1px solid #4a5568;'><span style='font-size:12px;'>{p['name']} ({p['f']:.1f})</span></div>", unsafe_allow_html=True)
                    if st.button("🔄", key=f"m_{pfx}_{i}"):
                        if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                        else: st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()

# --- 5. דף מאגר ---
elif st.session_state.menu_selection == "מאגר שחקנים":
    st.subheader("🗄️ ניהול שחקנים")
    for i, p in enumerate(st.session_state.players):
        score, birth = get_player_stats(p['name'])
        st.markdown(f"""
            <div class='database-card'>
                <div class='card-title'>{p['name']}</div>
                <div class='card-detail'>גיל: {2026 - birth} | ציון: {score:.1f}</div>
            </div>
        """, unsafe_allow_html=True)
        
        col_edit, col_del = st.columns([4, 1])
        with col_edit:
            if st.button(f"📝 עריכה", key=f"ed_{i}"):
                # התיקון הקריטי: מעדכנים את ה-key של ה-pills ישירות
                st.session_state.pills_nav = "עדכון/הרשמה" 
                st.session_state.menu_selection = "עדכון/הרשמה"
                st.session_state.edit_player_name = p['name']
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"dl_{i}"):
                st.session_state.players.pop(i)
                save_data()
                st.rerun()

# --- 6. דף עדכון/הרשמה ---
elif st.session_state.menu_selection == "עדכון/הרשמה":
    st.subheader("📝 עדכון פרטים")
    names = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    
    # וידוא שהאינדקס נכון
    current_target = st.session_state.get('edit_player_name', "🆕 שחקן חדש")
    try:
        default_idx = names.index(current_target)
    except:
        default_idx = 0
        
    choice = st.selectbox("בחר שחקן:", names, index=default_idx)
    
    with st.form("edit_form"):
        p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "")
        f_year = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
        
        roles_list = ["שוער", "בלם", "מגן", "קשר אחורי", "קשר קדמי", "כנף", "חלוץ"]
        curr_r = p_data.get('roles', "") if p_data else ""
        curr_r_list = curr_r.split(',') if isinstance(curr_r, str) and curr_r else []
        f_roles = st.pills("תפקידים:", roles_list, selection_mode="multi", default=curr_r_list)
        
        f_rate = st.radio("ציון (1-10):", range(1, 11), index=int(p_data['rating'])-1 if p_data else 4, horizontal=True)
        
        if st.form_submit_button("שמור ✅"):
            if f_name:
                new_p = {"name": f_name, "birth_year": f_year, "rating": f_rate, "roles": ",".join(f_roles), "peer_ratings": p_data['peer_ratings'] if p_data else "{}"}
                if p_data:
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                    st.session_state.players[idx] = new_p
                else:
                    st.session_state.players.append(new_p)
                save_data()
                st.session_state.edit_player_name = f_name # נשאר על אותו שחקן אחרי שמירה
                st.success("נשמר!")
                st.rerun()
