import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import urllib.parse
import json

# --- 1. עיצוב RTL וסגנון כפתורי דירוג ---
st.set_page_config(page_title="ניהול כדורגל", layout="wide")
st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"], .main { direction: rtl; text-align: right; }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] { direction: rtl !important; text-align: right !important; }
    h1, h2, h3, h4, p, label, span { text-align: right !important; direction: rtl !important; }
    
    /* עיצוב כפתורי הדירוג (Radio) */
    div[data-testid="stWidgetLabel"] p { font-weight: bold; font-size: 1.1em; color: #1e88e5; }
    div[data-role="radiogroup"] { gap: 10px; justify-content: flex-end; }
    
    .stButton button { width: 100%; border-radius: 8px; background-color: #2e7d32; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לגוגל ---
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

# --- 3. חישוב ציונים ---
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

# --- 4. תפריט Sidebar ---
with st.sidebar:
    st.title("⚽ תפריט")
    access = st.radio("מצב גישה:", ["שחקן", "מנהל"])
    menu = "שחקן"
    if access == "מנהל":
        pwd = st.text_input("סיסמה:", type="password")
        if pwd == "1234":
            menu = st.selectbox("פעולה:", ["ניהול מאגר", "חלוקת קבוצות"])

# --- 5. דף שחקן ---
if menu == "שחקן":
    st.title("📝 עדכון פרטים ודירוג")
    names = sorted([str(p['name']) for p in st.session_state.players]) if st.session_state.players else []
    sel = st.selectbox("מי אתה?", ["---", "🆕 שחקן חדש"] + names)
    
    final_name = ""
    curr = None
    if sel == "🆕 שחקן חדש": 
        final_name = st.text_input("הקלד שם מלא:")
    elif sel != "---":
        final_name = sel
        curr = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        st.subheader(f"פרופיל: {final_name}")
        
        year = st.number_input("שנת לידה:", 1950, 2026, int(curr['birth_year']) if curr and 'birth_year' in curr else 1995)
        
        roles = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
        if curr and 'pos' in curr and pd.notna(curr['pos']) and isinstance(curr['pos'], str):
            def_roles = curr['pos'].split(", ")
        else: def_roles = []
        selected_pos = st.pills("תפקידים:", roles, selection_mode="multi", default=def_roles)
        
        st.write("") # מרווח קטן
        # --- השינוי כאן: דירוג אישי באמצעות כפתורי רדיו ---
        rate = st.radio(
            "דרג את היכולת שלך (כמה אתה חזק):",
            options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            index=int(curr['rating'] - 1) if curr and 'rating' in curr else 4,
            horizontal=True,
            key="self_rating_radio"
        )
        
        st.divider()
        st.subheader("⭐ דרג חברים")
        st.info("דרג את רמת המשחק של החברים (1 = חלש, 10 = חזק מאוד)")
        
        p_ratings = {}
        try: p_ratings = json.loads(curr['peer_ratings']) if curr and 'peer_ratings' in curr and pd.notna(curr['peer_ratings']) else {}
        except: p_ratings = {}

        for p in st.session_state.players:
            if p['name'] != final_name:
                p_ratings[p['name']] = st.radio(
                    f"רמה של {p['name']}:",
                    options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                    index=int(p_ratings.get(p['name'], 5)) - 1,
                    horizontal=True,
                    key=f"r_{p['name']}"
                )

        if st.button("שמור הכל ועדכן מאגר ✅"):
            if not selected_pos:
                st.error("בחר לפחות תפקיד אחד")
            else:
                new_p = {
                    "name": final_name, "birth_year": year, 
                    "pos": ", ".join(selected_pos), "rating": rate, 
                    "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)
                }
                idx = next((i for i, pl in enumerate(st.session_state.players) if pl['name'] == final_name), None)
                if idx is not None: st.session_state.players[idx] = new_p
                else: st.session_state.players.append(new_p)
                
                save_data(st.session_state.players)
                st.success("הנתונים נשמרו בגיליון!")
                st.balloons()
                st.rerun()
                
# --- 6. ניהול מאגר (Admin) ---
elif menu == "ניהול מאגר":
    st.title("👤 ניהול מאגר וציונים")
    
    for i, p in enumerate(st.session_state.players):
        f, avg, count = get_final_score(p['name'])
        age = 2026 - int(p.get('birth_year', 1995))
        
        with st.container(border=True):
            # תצוגת השחקן בשתי שורות כמו שביקשת
            c = st.columns([3, 1, 1, 1, 1])
            with c[0]:
                st.subheader(p['name'])
                st.write(f"🎂 גיל: {age} | 🏃 תפקיד: {p.get('pos', '---')}")
            
            c[1].metric("אישי", f"{float(p.get('rating', 5)):.1f}")
            c[2].metric("חברים", f"{avg:.1f}", f"({count})")
            c[3].metric("סופי", f"{f:.1f}")
            
            # כפתורי פעולה
            edit_mode = st.checkbox("📝 עריכה", key=f"check_edit_{i}")
            if c[4].button("🗑️ מחיקה", key=f"del_{i}"):
                st.session_state.players.pop(i)
                save_data(st.session_state.players)
                st.rerun()

            # אם סימנו "עריכה", יפתח טופס קטן מתחת לשחקן
            if edit_mode:
                with st.expander("ערוך פרטים עבור " + p['name'], expanded=True):
                    new_name = st.text_input("שם:", value=p['name'], key=f"en_{i}")
                    new_year = st.number_input("שנת לידה:", 1950, 2026, int(p['birth_year']), key=f"ey_{i}")
                    new_pos = st.text_input("תפקיד:", value=p['pos'], key=f"ep_{i}")
                    new_rate = st.slider("דירוג אישי:", 1.0, 10.0, float(p['rating']), key=f"er_{i}")
                    
                    if st.button("שמור שינויים 💾", key=f"save_edit_{i}"):
                        st.session_state.players[i] = {
                            "name": new_name,
                            "birth_year": new_year,
                            "pos": new_pos,
                            "rating": new_rate,
                            "peer_ratings": p.get('peer_ratings', '{}') # שומר על הדירוגים הקיימים
                        }
                        save_data(st.session_state.players)
                        st.success("השינויים נשמרו!")
                        st.rerun()

# --- 7. חלוקת קבוצות ---
elif menu == "חלוקת קבוצות":
    st.title("📋 חלוקה למשחק")
    pool = []
    for p in st.session_state.players:
        f, _, _ = get_final_score(p['name'])
        pool.append({**p, "f": f})
        
    selected_players = st.multiselect("מי משחק היום?", [p['name'] for p in pool])
    
    if st.button("חלק קבוצות 🚀"):
        active = [p for p in pool if p['name'] in selected_players]
        if len(active) > 1:
            active.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(active):
                if i % 2 == 0: t1.append(p)
                else: t2.append(p)
            
            st.divider()
            c1, c2 = st.columns(2)
            c1.subheader("⚪ לבן")
            c1.write("\n".join([f"- {p['name']} ({p['pos']})" for p in t1]))
            c2.subheader("⚫ שחור")
            c2.write("\n".join([f"- {p['name']} ({p['pos']})" for p in t2]))
            
            msg = "⚽ *הקבוצות:* \n\n⚪ לבן: \n" + "\n".join([f"- {p['name']}" for p in t1])
            msg += "\n\n⚫ שחור: \n" + "\n".join([f"- {p['name']}" for p in t2])
            st.markdown(f'[📲 וואטסאפ](https://wa.me/?text={urllib.parse.quote(msg)})')



