import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import urllib.parse

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

# החלף כאן ללינק של הגיליון שלך (לוודא שהגיליון פתוח לצפייה למי שיש לו לינק!)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1oexl9m3FA1T8zWOkTOSUuhBjBm2c5nZVIRqfNjtLS0M/edit?usp=sharing"

def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL)
        # הפיכת הנתונים חזרה לרשימת מילונים (Dicts) כדי שהקוד הקיים ימשיך לעבוד
        return df.to_dict(orient='records')
    except:
        return []

def save_data(players_list):
    # הפיכת הרשימה לטבלה ושמירה בגוגל
    df = pd.DataFrame(players_list)
    conn.update(spreadsheet=SHEET_URL, data=df)
    st.cache_data.clear() # ניקוי זיכרון כדי שהנתונים יתעדכנו מיד

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
        elif pwd:
            st.error("סיסמה שגויה")

# --- 4. דף שחקן: מילוי ודירוג ---
if menu == "מילוי פרטים":
    st.title("📝 עדכון פרטים ודירוג")
    
    player_names = sorted([p['name'] for p in st.session_state.players]) if st.session_state.players else []
    name_options = ["--- בחר שם מהרשימה ---", "🆕 שחקן חדש"] + player_names
    
    selected_name = st.selectbox("מי אתה?", options=name_options)
    
    final_name = ""
    curr_p_data = None
    
    if selected_name == "🆕 שחקן חדש":
        final_name = st.text_input("הקלד את שמך המלא:")
    elif selected_name != "--- בחר שם מהרשימה ---":
        final_name = selected_name
        curr_p_data = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        with st.form("player_form"):
            st.subheader(f"פרופיל: {final_name}")
            b_year = st.number_input("שנת לידה:", 1950, 2026, int(curr_p_data.get('birth_year', 1995)) if curr_p_data else 1995)
            
            roles = ["שוער", "בלם", "מגן ימני", "מגן שמאלי", "קשר", "כנף", "חלוץ"]
            def_roles = curr_p_data.get('pos', "").split(", ") if curr_p_data else []
            selected_pos = st.pills("תפקידים:", options=roles, selection_mode="multi", default=def_roles)
            
            rate = st.slider("דרג את היכולת שלך (1-10):", 1.0, 10.0, float(curr_p_data.get('rating', 5.0)) if curr_p_data else 5.0)
            
            # דירוג חברים (נשמר כמחרוזת JSON בתוך התא בגיליון)
            import json
            peer_ratings = json.loads(curr_p_data.get('peer_ratings', '{}')) if curr_p_data and isinstance(curr_p_data.get('peer_ratings'), str) else {}

            st.divider()
            st.write("**⭐ דרג חברים:**")
            for p in st.session_state.players:
                if p['name'] != final_name:
                    p_val = peer_ratings.get(p['name'], 5)
                    peer_ratings[p['name']] = st.select_slider(f"רמה של {p['name']}:", options=list(range(1, 11)), value=int(p_val), key=f"rate_{p['name']}")

            if st.form_submit_button("שמור ועדכן"):
                new_entry = {
                    "name": final_name, "birth_year": b_year, 
                    "pos": ", ".join(selected_pos), "rating": rate, 
                    "peer_ratings": json.dumps(peer_ratings, ensure_ascii=False)
                }
                idx = next((i for i, p in enumerate(st.session_state.players) if p['name'] == final_name), None)
                if idx is not None: st.session_state.players[idx] = new_entry
                else: st.session_state.players.append(new_entry)
                
                save_data(st.session_state.players)
                st.success("נשמר בגוגל שיטס!")
                st.balloons()

# --- המשך הקוד (ניהול מאגר וחלוקה) נשאר זהה ללוגיקה הקודמת ---
# (שים לב להשתמש ב-json.loads עבור peer_ratings כשאתה מחשב ציונים)

