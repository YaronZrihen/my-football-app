import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import urllib.parse
import json

# --- 1. עיצוב RTL ---
st.set_page_config(page_title="ניהול כדורגל", layout="wide")
st.markdown("""<style>.stApp { direction: rtl; text-align: right; }</style>""", unsafe_allow_html=True)

# --- 2. חיבור ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl="0")
        return df.dropna(subset=['name']).to_dict(orient='records')
    except: return []

def save_data(players_list):
    df = pd.DataFrame(players_list)
    conn.update(data=df)
    st.cache_data.clear()

if 'players' not in st.session_state:
    st.session_state.players = load_data()

# --- 3. פונקציית ציונים (החזרתי אותה!) ---
def get_final_score(player_name):
    player = next((p for p in st.session_state.players if p['name'] == player_name), None)
    if not player: return 5.0, 0.0, 0
    self_rate = float(player.get('rating', 5.0))
    peer_scores = []
    for p in st.session_state.players:
        try:
            r = json.loads(p.get('peer_ratings', '{}'))
            if player_name in r: peer_scores.append(float(r[player_name]))
        except: continue
    avg_p = sum(peer_scores)/len(peer_scores) if peer_scores else 0.0
    final = (self_rate + avg_p) / 2 if avg_p > 0 else self_rate
    return final, avg_p, len(peer_scores)

# --- 4. תפריט ---
with st.sidebar:
    st.title("⚽ תפריט")
    access = st.radio("גישה:", ["שחקן", "מנהל"])
    menu = "שחקן"
    if access == "מנהל" and st.text_input("סיסמה:", type="password") == "1234":
        menu = st.selectbox("פעולה:", ["ניהול", "חלוקה"])

# --- 5. דף שחקן (התיקון הקריטי כאן) ---
if menu == "שחקן":
    st.title("📝 עדכון פרטים")
    names = sorted([str(p['name']) for p in st.session_state.players]) if st.session_state.players else []
    sel = st.selectbox("מי אתה?", ["---", "🆕 חדש"] + names)
    
    name_to_edit = ""
    curr = None
    if sel == "🆕 חדש": name_to_edit = st.text_input("שם מלא:")
    elif sel != "---":
        name_to_edit = sel
        curr = next((p for p in st.session_state.players if p['name'] == name_to_edit), None)

    if name_to_edit:
        # הטופס מתחיל כאן
        with st.form(key="main_player_form"):
            st.subheader(f"פרופיל: {name_to_edit}")
            
            # שדות קלט פשוטים ללא עמודות כדי למנוע את השגיאה
            year = st.number_input("שנת לידה:", 1950, 2026, int(curr['birth_year']) if curr else 1995)
            pos = st.text_input("תפקידים (קשר, בלם וכו'):", curr['pos'] if curr else "")
            rate = st.slider("דירוג אישי (1-10):", 1.0, 10.0, float(curr['rating']) if curr else 5.0)
            
            st.write("---")
            st.write("**⭐ דרג חברים:**")
            
            p_ratings = {}
            try: p_ratings = json.loads(curr['peer_ratings']) if curr else {}
            except: p_ratings = {}

            for p in st.session_state.players:
                if p['name'] != name_to_edit:
                    p_ratings[p['name']] = st.select_slider(
                        f"רמה של {p['name']}:", 
                        options=list(range(1, 11)), 
                        value=int(p_ratings.get(p['name'], 5)),
                        key=f"r_{p['name']}"
                    )

            # הכפתור - נמצא בשורה נפרדת בתוך ה-with, ללא עמודות!
            submitted = st.form_submit_button("שמור ועדכן נתונים ✅")
            
            if submitted:
                new_data = {
                    "name": name_to_edit, "birth_year": year, 
                    "pos": pos, "rating": rate, 
                    "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)
                }
                idx = next((i for i, pl in enumerate(st.session_state.players) if pl['name'] == name_to_edit), None)
                if idx is not None: st.session_state.players[idx] = new_data
                else: st.session_state.players.append(new_data)
                
                save_data(st.session_state.players)
                st.success("נשמר בהצלחה!")
                st.balloons()
                st.rerun()

# --- 6. ניהול ---
elif menu == "ניהול":
    st.title("👤 מאגר")
    for i, p in enumerate(st.session_state.players):
        f, avg, count = get_final_score(p['name'])
        with st.container(border=True):
            col = st.columns([3, 1, 1])
            col[0].write(f"**{p['name']}** | {p['pos']}")
            col[1].write(f"סופי: {f:.1f}")
            if col[2].button("🗑️", key=f"d_{i}"):
                st.session_state.players.pop(i)
                save_data(st.session_state.players)
                st.rerun()

# --- 7. חלוקה ---
elif menu == "חלוקה":
    st.title("📋 חלוקה מאוזנת")
    pool = []
    for p in st.session_state.players:
        f, _, _ = get_final_score(p['name'])
        pool.append({**p, "f": f})
        
    selected = st.multiselect("מי כאן?", [p['name'] for p in pool])
    if st.button("חלק קבוצות"):
        active = [p for p in pool if p['name'] in selected]
        active.sort(key=lambda x: x['f'], reverse=True)
        t1, t2 = [], []
        for i, p in enumerate(active):
            if i % 2 == 0: t1.append(p)
            else: t2.append(p)
        
        c1, c2 = st.columns(2)
        c1.write("⚪ **לבן:**\n" + "\n".join([f"- {p['name']}" for p in t1]))
        c2.write("⚫ **שחור:**\n" + "\n".join([f"- {p['name']}" for p in t2]))
