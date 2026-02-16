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

# --- 2. חיבור לגוגל שיטס ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1oexl9m3FA1T8zWOkTOSUuhBjBm2c5nZVIRqfNjtLS0M/edit?gid=1767684040#gid=1767684040"

def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl="0")
        df = df.dropna(subset=['name'])
        return df.to_dict(orient='records')
    except:
        return []

def save_data(players_list):
    df = pd.DataFrame(players_list)
    conn.update(spreadsheet=SHEET_URL, data=df)
    st.cache_data.clear()

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
    names = sorted([str(p['name']) for p in st.session_state.players]) if st.session_state.players else []
    sel = st.selectbox("מי אתה?", ["---"] + ["🆕 חדש"] + names)
    
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
            year = st.number_input("שנת לידה:", 1950, 2026, int(curr['birth_year']) if curr else 1995)
            pos = st.text_input("תפקיד:", curr['pos'] if curr else "")
            rate = st.slider("דירוג (1-10):", 1.0, 10.0, float(curr['rating']) if curr else 5.0)
            
            # דירוג חברים
            st.write("**⭐ דרג חברים:**")
            p_ratings = {}
            if curr and 'peer_ratings' in curr:
                try: p_ratings = json.loads(curr['peer_ratings'])
                except: p_ratings = {}
            
            for p in st.session_state.players:
                if p['name'] != final_name:
                    p_ratings[p['name']] = st.select_slider(f"רמה של {p['name']}:", options=list(range(1, 11)), value=int(p_ratings.get(p['name'], 5)), key=f"r_{p['name']}")

            if st.form_submit_button("שמור הכל"):
                new_p = {"name": final_name, "birth_year": year, "pos": pos, "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
                idx = next((i for i, pl in enumerate(st.session_state.players) if pl['name'] == final_name), None)
                if idx is not None: st.session_state.players[idx] = new_p
                else: st.session_state.players.append(new_p)
                save_data(st.session_state.players)
                st.success("נשמר!")
                st.balloons()

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
        random.shuffle(pool)
        mid = len(pool)//2
        t1, t2 = pool[:mid], pool[mid:]
        st.write("⚪ **לבן:** " + ", ".join([p['name'] for p in t1]))
        st.write("⚫ **שחור:** " + ", ".join([p['name'] for p in t2]))
