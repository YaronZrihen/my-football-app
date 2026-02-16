import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import urllib.parse
import json

# --- 1. עיצוב RTL והגדרות ---
st.set_page_config(page_title="ניהול כדורגל מקצועי", layout="wide")
st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"], .main { direction: rtl; text-align: right; }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] { direction: rtl !important; text-align: right !important; }
    h1, h2, h3, h4, p, label, span { text-align: right !important; direction: rtl !important; }
    .stButton button { width: 100%; border-radius: 8px; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לגוגל שיטס ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl="0")
        df = df.dropna(subset=['name'])
        return df.to_dict(orient='records')
    except: return []

def save_data(players_list):
    try:
        df = pd.DataFrame(players_list)
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"שגיאה בשמירה לגוגל: {e}")
        return False

if 'players' not in st.session_state:
    st.session_state.players = load_data()

# --- 3. לוגיקה לחישוב ציונים ---
def get_final_score(player_name):
    player = next((p for p in st.session_state.players if p['name'] == player_name), None)
    if not player: return 0.0, 0.0, 0
    
    self_rate = float(player.get('rating', 5.0))
    peer_scores = []
    
    # איסוף כל הדירוגים ששחקנים אחרים נתנו לו
    for p in st.session_state.players:
        try:
            p_ratings = json.loads(p.get('peer_ratings', '{}'))
            if player_name in p_ratings:
                peer_scores.append(float(p_ratings[player_name]))
        except: continue
    
    avg_peers = sum(peer_scores) / len(peer_scores) if peer_scores else 0.0
    final = (self_rate + avg_peers) / 2 if avg_peers > 0 else self_rate
    return final, avg_peers, len(peer_scores)

# --- 4. תפריט Sidebar ---
with st.sidebar:
    st.title("⚽ ניהול משחקים")
    access = st.radio("מצב גישה:", ["שחקן", "מנהל (Admin)"])
    menu = "שחקן"
    if access == "מנהל (Admin)":
        if st.text_input("סיסמה:", type="password") == "1234":
            menu = st.selectbox("בחר פעולה:", ["ניהול מאגר", "חלוקת קבוצות"])
        else: st.warning("הכנס סיסמה לגישה לניהול")

# --- 5. דף שחקן ---
if menu == "שחקן":
    st.title("📝 עדכון פרטים ודירוג חברים")
    names = sorted([str(p['name']) for p in st.session_state.players if 'name' in p]) if st.session_state.players else []
    sel = st.selectbox("בחר את השם שלך:", ["---", "🆕 שחקן חדש"] + names)
    
    final_name = ""
    curr = None
    if sel == "🆕 שחקן חדש":
        final_name = st.text_input("שם מלא:")
    elif sel != "---":
        final_name = sel
        curr = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        with st.form(key=f"form_{final_name}"):
            col1, col2 = st.columns(2)
            with col1:
                year = st.number_input("שנת לידה:", 1950, 2026, int(curr['birth_year']) if curr and 'birth_year' in curr else 1995)
                rate = st.slider("דירוג היכולת שלך (1-10):", 1.0, 10.0, float(curr['rating']) if curr and 'rating' in curr else 5.0)
            with col2:
                roles = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
                def_roles = curr['pos'].split(", ") if curr and 'pos' in curr else []
                selected_pos = st.multiselect("תפקידים:", roles, default=def_roles)

            st.divider()
            st.subheader("⭐ דרג את החברים שלך")
            st.caption("הדירוג שלך עוזר לחלק את הקבוצות בצורה מאוזנת (הם לא יראו מה נתת להם)")
            
            peer_ratings = {}
            if curr and 'peer_ratings' in curr and isinstance(curr['peer_ratings'], str):
                try: peer_ratings = json.loads(curr['peer_ratings'])
                except: peer_ratings = {}

            # דירוג לכל שחקן אחר
            for p in st.session_state.players:
                if p['name'] != final_name:
                    peer_ratings[p['name']] = st.select_slider(
                        f"רמה של {p['name']}:", 
                        options=list(range(1, 11)), 
                        value=int(peer_ratings.get(p['name'], 5)), 
                        key=f"r_{p['name']}"
                    )

            if st.form_submit_button("שמור ועדכן הכל"):
                new_p = {
                    "name": final_name, "birth_year": year, 
                    "pos": ", ".join(selected_pos), "rating": rate, 
                    "peer_ratings": json.dumps(peer_ratings, ensure_ascii=False)
                }
                idx = next((i for i, pl in enumerate(st.session_state.players) if pl['name'] == final_name), None)
                if idx is not None: st.session_state.players[idx] = new_p
                else: st.session_state.players.append(new_p)
                
                if save_data(st.session_state.players):
                    st.success("הנתונים עודכנו בהצלחה בגוגל שיטס!")
                    st.balloons()
                    st.rerun()

# --- 6. ניהול מאגר (Admin) ---
elif menu == "ניהול מאגר":
    st.title("👤 ניהול וציונים")
    
    st.write("ציונים סופיים משקללים דירוג עצמי + דירוג חברים")
    
    for i, p in enumerate(st.session_state.players):
        final_s, avg_p, count_p = get_final_score(p['name'])
        
        with st.container(border=True):
            c = st.columns([2, 1, 1, 1, 0.5])
            c[0].markdown(f"**{p['name']}** \n<small>🎂 {2026-int(p['birth_year'])} | 🏃 {p['pos']}</small>", unsafe_allow_html=True)
            c[1].metric("אישי", f"{float(p['rating']):.1f}")
            c[2].metric("חברים", f"{avg_p:.1f}", f"{count_p} מדרגים")
            c[3].metric("סופי", f"{final_s:.1f}")
            
            if c[4].button("🗑️", key=f"del_{i}"):
                st.session_state.players.pop(i)
                save_data(st.session_state.players)
                st.rerun()

# --- 7. חלוקת קבוצות חכמה ---
elif menu == "חלוקת קבוצות":
    st.title("📋 חלוקה מאוזנת")
    
    # חישוב ציונים לכולם
    pool_data = []
    for p in st.session_state.players:
        final_s, _, _ = get_final_score(p['name'])
        pool_data.append({**p, "final_s": final_s})
    
    selected_names = st.multiselect("מי משחק היום?", [p['name'] for p in pool_data])
    
    if st.button("חלק קבוצות 🚀"):
        active_players = [p for p in pool_data if p['name'] in selected_names]
        if len(active_players) < 2:
            st.error("צריך לפחות 2 שחקנים...")
        else:
            # מיון לפי ציון וחלוקת נחש (Snake Draft) לאיזון מקסימלי
            active_players.sort(key=lambda x: x['final_s'], reverse=True)
            team_a, team_b = [], []
            for i, p in enumerate(active_players):
                if i % 2 == 0: team_a.append(p)
                else: team_b.append(p)
            
            st.divider()
            col1, col2 = st.columns(2)
            
            for t_list, label, col, icon in [(team_a, "⚪ לבן", col1, "⚪"), (team_b, "⚫ שחור", col2, "⚫")]:
                with col:
                    avg_team = sum(p['final_s'] for p in t_list) / len(t_list)
                    st.subheader(f"{label} (ממוצע: {avg_team:.1f})")
                    for p in t_list:
                        st.info(f"**{p['name']}** ({p['pos']})")

            # וואטסאפ
            msg = f"⚽ *הקבוצות מוכנות!*\n\n⚪ *לבן:* \n" + "\n".join([f"- {p['name']}" for p in team_a])
            msg += f"\n\n⚫ *שחור:* \n" + "\n".join([f"- {p['name']}" for p in team_b])
            url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
            st.markdown(f'[📲 שלח חלוקה בוואטסאפ]({url})')
