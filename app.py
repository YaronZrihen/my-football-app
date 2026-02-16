import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import urllib.parse
import json

# --- 1. הגדרות דף ועיצוב RTL ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"], .main { direction: rtl; text-align: right; }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] { direction: rtl !important; text-align: right !important; }
    div[data-testid="stSelectbox"] svg { right: auto !important; left: 10px !important; }
    h1, h2, h3, h4, p, label, span { text-align: right !important; direction: rtl !important; }
    .stButton button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור ל-Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# הכתובת של הגיליון שלך (שים לב שהשיתוף מוגדר ל-Anyone with the link)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1oexl9m3FA1T8zWOkTOSUuhBjBm2c5nZVIRqfNjtLS0M/edit?usp=sharing"

def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl="0")
        # ניקוי שורות ריקות לגמרי כדי שלא יפילו את המערכת
        df = df.dropna(subset=['name'])
        return df.to_dict(orient='records')
    except Exception as e:
        # אם הגיליון ריק לגמרי, נחזיר רשימה ריקה
        return []

def save_data(players_list):
    df = pd.DataFrame(players_list)
    conn.update(spreadsheet=SHEET_URL, data=df)
    st.cache_data.clear()

if 'players' not in st.session_state:
    st.session_state.players = load_data()

# --- 3. תפריט Sidebar ---
ADMIN_PASSWORD = "1234"

with st.sidebar:
    st.title("⚽ תפריט")
    access_mode = st.radio("מצב גישה:", ["שחקן (מילוי פרטים)", "מנהל (Admin)"])
    menu = "מילוי פרטים" 
    if access_mode == "מנהל (Admin)":
        pwd = st.text_input("סיסמה:", type="password")
        if pwd == ADMIN_PASSWORD:
            menu = st.selectbox("בחר פעולה:", ["ניהול מאגר שחקנים", "חלוקת קבוצות"])
        elif pwd: st.error("סיסמה שגויה")

# --- 4. דף שחקן: מילוי ודירוג ---
if menu == "מילוי פרטים":
    st.title("📝 עדכון פרטים ודירוג")
    
    # וידוא שכל השמות הם מחרוזות טקסט תקינות לפני המיון
    player_names = sorted([str(p['name']) for p in st.session_state.players if 'name' in p and pd.notna(p['name'])]) if st.session_state.players else []
    name_options = ["--- בחר שם ---", "🆕 שחקן חדש"] + player_names
    selected_name = st.selectbox("מי אתה?", options=name_options)
    
    final_name = ""
    curr_p_data = None
    if selected_name == "🆕 שחקן חדש":
        final_name = st.text_input("הקלד שם מלא:")
    elif selected_name != "--- בחר שם ---":
        final_name = selected_name
        curr_p_data = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        with st.form("p_form"):
            st.subheader(f"פרופיל: {final_name}")
            b_year = st.number_input("שנת לידה:", 1950, 2026, int(curr_p_data['birth_year']) if curr_p_data and 'birth_year' in curr_p_data else 1995)
            roles = ["שוער", "בלם", "מגן ימני", "מגן שמאלי", "קשר", "כנף", "חלוץ"]
            def_roles = curr_p_data['pos'].split(", ") if curr_p_data and 'pos' in curr_p_data else []
            selected_pos = st.pills("תפקידים:", options=roles, selection_mode="multi", default=def_roles)
            rate = st.slider("דירוג עצמי:", 1.0, 10.0, float(curr_p_data['rating']) if curr_p_data and 'rating' in curr_p_data else 5.0)
            
            p_ratings = json.loads(curr_p_data['peer_ratings']) if curr_p_data and 'peer_ratings' in curr_p_data and isinstance(curr_p_data['peer_ratings'], str) else {}

            st.write("**⭐ דרג חברים:**")
            for p in st.session_state.players:
                if p['name'] != final_name:
                    p_val = p_ratings.get(p['name'], 5)
                    p_ratings[p['name']] = st.select_slider(f"רמה של {p['name']}:", options=list(range(1, 11)), value=int(p_val), key=f"r_{p['name']}")

            if st.form_submit_button("שמור"):
                new_entry = {"name": final_name, "birth_year": b_year, "pos": ", ".join(selected_pos), "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
                idx = next((i for i, p in enumerate(st.session_state.players) if p['name'] == final_name), None)
                if idx is not None: st.session_state.players[idx] = new_entry
                else: st.session_state.players.append(new_entry)
                save_data(st.session_state.players)
                st.success("נשמר!")
                st.rerun()

# --- 5. ניהול מאגר (Admin) ---
elif menu == "ניהול מאגר שחקנים":
    st.title("👤 ניהול מאגר")
    all_received = {p['name']: [] for p in st.session_state.players}
    for p in st.session_state.players:
        p_ratings = json.loads(p['peer_ratings']) if 'peer_ratings' in p and isinstance(p['peer_ratings'], str) else {}
        for target, score in p_ratings.items():
            if target in all_received: all_received[target].append(score)

    st.divider()
    h = st.columns([2.5, 1, 1, 1, 0.5, 0.5])
    h[0].write("**גיל ושם**"); h[1].write("**אישי**"); h[2].write("**קבוצתי**"); h[3].write("**סופי**")
    
    for i, p in enumerate(st.session_state.players):
        age = 2026 - int(p['birth_year'])
        p_rate = float(p['rating'])
        r_list = all_received.get(p['name'], [])
        t_rate = sum(r_list)/len(r_list) if r_list else 0.0
        final_s = (p_rate + t_rate)/2 if t_rate > 0 else p_rate
        
        c = st.columns([2.5, 1, 1, 1, 0.5, 0.5])
        c[0].markdown(f"({age}) **{p['name']}**<br><small>🏃 {p['pos']}</small>", unsafe_allow_html=True)
        c[1].write(f"{p_rate:.1f}")
        c[2].write(f"{t_rate:.1f} ({len(r_list)})" if r_list else "---")
        c[3].write(f"**{final_s:.1f}**")
        
        if c[4].toggle("📝", key=f"e_{i}"):
            with st.form(f"f_{i}"):
                u_name = st.text_input("שם:", p['name'])
                u_year = st.number_input("שנה:", 1950, 2026, int(p['birth_year']))
                if st.form_submit_button("עדכן"):
                    st.session_state.players[i].update({"name": u_name, "birth_year": u_year})
                    save_data(st.session_state.players); st.rerun()
        if c[5].button("🗑️", key=f"d_{i}"):
            st.session_state.players.pop(i); save_data(st.session_state.players); st.rerun()

# --- 6. חלוקת קבוצות ---
elif menu == "חלוקת קבוצות":
    st.title("📋 חלוקה לבן/שחור")
    # לוגיקת עיבוד דומה לניהול מאגר
    processed = []
    for p in st.session_state.players:
        p_rate = float(p['rating'])
        processed.append({**p, "f_score": p_rate, "age": 2026 - int(p['birth_year'])})

    selected = st.pills("מי הגיע?", options=[p['name'] for p in processed], selection_mode="multi")
    if st.button("חלק קבוצות 🚀") and len(selected) > 1:
        available = [p for p in processed if p['name'] in selected]
        random.shuffle(available)
        mid = len(available)//2
        st.session_state.team_a, st.session_state.team_b = available[:mid], available[mid:]
        st.session_state.show_res = True

    if st.session_state.get('show_res'):
        c1, c2 = st.columns(2)
        for t_list, label, col, k in [(st.session_state.team_a, "⚪ לבן", c1, "team_a"), (st.session_state.team_b, "⚫ שחור", c2, "team_b")]:
            with col:
                st.subheader(label)
                for p in t_list:
                    with st.container(border=True):
                        st.write(f"**{p['name']}**")
                        st.write(f"<small>🎂 {p['age']} | 🏃 {p['pos']}</small>", unsafe_allow_html=True)
        
        msg = "⚽ *חלוקה:*\n\n⚪ *לבן:*\n" + "\n".join([f"- {p['name']}" for p in st.session_state.team_a])
        msg += "\n\n⚫ *שחור:*\n" + "\n".join([f"- {p['name']}" for p in st.session_state.team_b])
        st.markdown(f'[לחץ לשליחה בוואטסאפ](https://wa.me/?text={urllib.parse.quote(msg)})')


