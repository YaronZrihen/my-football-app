import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import urllib.parse
import json

# --- 1. עיצוב RTL ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")
st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"], .main { direction: rtl; text-align: right; }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] { direction: rtl !important; text-align: right !important; }
    h1, h2, h3, p, label { text-align: right !important; direction: rtl !important; }
    .stButton button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לגוגל שיטס (עכשיו משתמש ב-Secrets שהגדרת) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # פקודת הקריאה עכשיו שואבת את הלינק מה-Secrets
        df = conn.read(ttl="0") 
        df = df.dropna(subset=['name'])
        return df.to_dict(orient='records')
    except:
        return []

def save_data(players_list):
    try:
        df = pd.DataFrame(players_list)
        # פקודת העדכון עכשיו תשתמש בהרשאות ה-Service Account
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"שגיאת שמירה: {e}")
        return False

if 'players' not in st.session_state:
    st.session_state.players = load_data()

# --- 3. תפריט Sidebar ---
with st.sidebar:
    st.title("⚽ תפריט")
    access = st.radio("מצב גישה:", ["שחקן", "מנהל"])
    menu = "שחקן"
    if access == "מנהל":
        pwd = st.text_input("סיסמה:", type="password")
        if pwd == "1234":
            menu = st.selectbox("פעולה:", ["ניהול מאגר", "חלוקה"])
        elif pwd: st.error("שגוי")

# --- 4. דף שחקן ---
if menu == "שחקן":
    st.title("📝 עדכון פרטים")
    # מיון שמות (הגנה מפני ערכים ריקים)
    names = sorted([str(p['name']) for p in st.session_state.players if 'name' in p]) if st.session_state.players else []
    sel = st.selectbox("מי אתה?", ["---", "🆕 חדש"] + names)
    
    final_name = ""
    curr = None
    if sel == "🆕 חדש":
        final_name = st.text_input("שם מלא:")
    elif sel != "---":
        final_name = sel
        curr = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        with st.form(key="player_main_form"):
            st.subheader(f"פרופיל: {final_name}")
            year = st.number_input("שנת לידה:", 1950, 2026, int(curr['birth_year']) if curr and 'birth_year' in curr else 1995)
            pos = st.text_input("תפקיד:", curr['pos'] if curr and 'pos' in curr else "")
            rate = st.slider("דירוג (1-10):", 1.0, 10.0, float(curr['rating']) if curr and 'rating' in curr else 5.0)
            
            st.write("**⭐ דרג חברים:**")
            p_ratings = {}
            if curr and 'peer_ratings' in curr and isinstance(curr['peer_ratings'], str):
                try: p_ratings = json.loads(curr['peer_ratings'])
                except: p_ratings = {}
            
            for p in st.session_state.players:
                if p['name'] != final_name:
                    p_val = p_ratings.get(p['name'], 5)
                    p_ratings[p['name']] = st.select_slider(f"רמה של {p['name']}:", options=list(range(1, 11)), value=int(p_val), key=f"r_{p['name']}")

            if st.form_submit_button("שמור הכל"):
                new_p = {"name": final_name, "birth_year": year, "pos": pos, "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
                idx = next((i for i, pl in enumerate(st.session_state.players) if pl['name'] == final_name), None)
                if idx is not None: st.session_state.players[idx] = new_p
                else: st.session_state.players.append(new_p)
                
                if save_data(st.session_state.players):
                    st.success("נשמר בהצלחה בגוגל שיטס!")
                    st.balloons()
                    st.rerun()

# --- 5. ניהול מאגר ---
elif menu == "ניהול מאגר":
    st.title("👤 ניהול")
    for i, p in enumerate(st.session_state.players):
        c = st.columns([3, 1])
        c[0].write(f"**{p['name']}** ({p['pos']})")
        if c[1].button("🗑️", key=f"del_{i}"):
            st.session_state.players.pop(i)
            save_data(st.session_state.players)
            st.rerun()

# --- 6. חלוקה ---
elif menu == "חלוקה":
    st.title("📋 חלוקה")
    selected = st.multiselect("מי הגיע?", [p['name'] for p in st.session_state.players])
    if st.button("חלק קבוצות"):
        pool = [p for p in st.session_state.players if p['name'] in selected]
        if len(pool) > 1:
            random.shuffle(pool)
            mid = len(pool)//2
            t1, t2 = pool[:mid], pool[mid:]
            st.success("הקבוצות חולקו!")
            st.write("⚪ **לבן:** " + ", ".join([p['name'] for p in t1]))
            st.write("⚫ **שחור:** " + ", ".join([p['name'] for p in t2]))
        else:
            st.error("בחר לפחות 2 שחקנים")
