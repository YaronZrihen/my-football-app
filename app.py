import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json

# --- 1. עיצוב מותאם לסלולר (Mobile-First) ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    /* הגדרות RTL */
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, h4, p, label, .stMarkdown { text-align: right !important; direction: rtl !important; }

    /* עיצוב כפתורי הניווט העליון (Segmented Control) */
    div[data-testid="stSegmentedControl"] {
        display: flex;
        justify-content: center;
        width: 100%;
        margin-bottom: 20px;
    }
    div[data-testid="stSegmentedControl"] button {
        flex-grow: 1;
        height: 50px !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
    }

    /* הקטנת רווחים לסלולר */
    .block-container { padding-top: 1rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
    
    /* עיצוב כפתורי הדירוג - מרווחים שווים */
    div[data-role="radiogroup"] { 
        gap: 4px !important; 
        justify-content: space-between !important;
    }

    /* כפתור שמירה ירוק ובולט */
    .stButton button { 
        width: 100%; 
        border-radius: 12px; 
        background-color: #2e7d32; 
        color: white; 
        font-weight: bold;
        height: 3.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור וטעינה ---
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

# --- 3. ניווט עליון בולט ---
menu = st.segmented_control(
    "בחר תפריט:",
    options=["👤 שחקן", "⚙️ מנהל"],
    default="👤 שחקן",
    label_visibility="collapsed"
)

# --- 4. תוכן לפי בחירה ---
if menu == "👤 שחקן":
    st.title("📝 עדכון ודירוג")
    names = sorted([str(p['name']) for p in st.session_state.players]) if st.session_state.players else []
    sel = st.selectbox("מי אתה?", ["---", "🆕 חדש"] + names)
    
    final_name = ""
    curr = None
    if sel == "🆕 חדש": 
        final_name = st.text_input("שם מלא:")
    elif sel != "---":
        final_name = sel
        curr = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        st.subheader(f"שחקן: {final_name}")
        year = st.number_input("שנת לידה:", 1950, 2026, int(curr['birth_year']) if curr and 'birth_year' in curr else 1995)
        
        roles = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
        def_roles = curr['pos'].split(", ") if curr and 'pos' in curr and isinstance(curr['pos'], str) else []
        selected_pos = st.pills("תפקידים:", roles, selection_mode="multi", default=def_roles)
        
        st.write("**דירוג אישי:**")
        rate = st.radio("רמה:", [1,2,3,4,5,6,7,8,9,10], index=int(curr['rating']-1) if curr else 4, horizontal=True, label_visibility="collapsed", key="self")
        
        st.divider()
        st.subheader("⭐ דרג חברים")
        p_ratings = {}
        try: p_ratings = json.loads(curr['peer_ratings']) if curr and 'peer_ratings' in curr else {}
        except: p_ratings = {}

        for p in st.session_state.players:
            if p['name'] != final_name:
                st.write(f"רמה של {p['name']}:")
                p_ratings[p['name']] = st.radio(f"r_{p['name']}", [1,2,3,4,5,6,7,8,9,10], 
                                                index=int(p_ratings.get(p['name'], 5))-1, horizontal=True, label_visibility="collapsed")

        if st.button("שמור הכל ✅"):
            new_p = {"name": final_name, "birth_year": year, "pos": ", ".join(selected_pos), "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
            idx = next((i for i, pl in enumerate(st.session_state.players) if pl['name'] == final_name), None)
            if idx is not None: st.session_state.players[idx] = new_p
            else: st.session_state.players.append(new_p)
            save_data(st.session_state.players)
            st.success("נשמר!")
            st.rerun()

elif menu == "⚙️ מנהל":
    pwd = st.text_input("סיסמת מנהל:", type="password")
    if pwd == "1234":
        admin_action = st.segmented_control("פעולה:", ["ניהול", "חלוקה"], default="ניהול")
        
        if admin_action == "ניהול":
            for i, p in enumerate(st.session_state.players):
                f, avg, count = get_final_score(p['name'])
                with st.container(border=True):
                    st.markdown(f"**{p['name']}** (🎂{2026-int(p['birth_year'])})")
                    st.caption(f"🏃 {p.get('pos', '---')}")
                    c = st.columns(3)
                    c[0].metric("אישי", f"{float(p['rating']):.1f}")
                    c[1].metric("חברים", f"{avg:.1f}")
                    c[2].metric("סופי", f"{f:.1f}")
                    
                    if st.button("🗑️ מחק", key=f"del_{i}"):
                        st.session_state.players.pop(i)
                        save_data(st.session_state.players)
                        st.rerun()
        
        elif admin_action == "חלוקה":
            pool = []
            for p in st.session_state.players:
                f, _, _ = get_final_score(p['name'])
                pool.append({**p, "f": f})
            selected = st.multiselect("מי משחק?", [p['name'] for p in pool])
            if st.button("חלק קבוצות 🚀"):
                active = [p for p in pool if p['name'] in selected]
                active.sort(key=lambda x: x['f'], reverse=True)
                t1, t2 = active[0::2], active[1::2]
                
                st.subheader("⚪ לבן")
                st.write(", ".join([p['name'] for p in t1]))
                st.subheader("⚫ שחור")
                st.write(", ".join([p['name'] for p in t2]))
                
                msg = f"⚽ הקבוצות:\n\n⚪ לבן: {', '.join([p['name'] for p in t1])}\n\n⚫ שחור: {', '.join([p['name'] for p in t2])}"
                st.markdown(f'[📲 שלח בוואטסאפ](https://wa.me/?text={urllib.parse.quote(msg)})')
