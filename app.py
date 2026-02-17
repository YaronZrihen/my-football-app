import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json

# --- 1. עיצוב Mobile-First אגרסיבי ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    /* כיוון כללי RTL */
    .stApp { direction: rtl; text-align: right; }
    
    /* הקטנה משמעותית של כותרות */
    h1 { font-size: 1.2rem !important; font-weight: 800 !important; margin-top: -20px !important; padding-bottom: 10px !important; text-align: right !important; }
    h2 { font-size: 1.1rem !important; font-weight: 700 !important; text-align: right !important; }
    h3 { font-size: 1.0rem !important; font-weight: 600 !important; text-align: right !important; }
    
    /* הקטנת טקסט כללי וצמצום רווחים */
    p, label, span, div { font-size: 0.9rem !important; text-align: right !important; }
    .stMarkdown div p { margin-bottom: 5px !important; }

    /* תיקון מרווחים בראש הדף */
    .block-container { 
        padding-top: 2rem !important; 
        padding-left: 0.5rem !important; 
        padding-right: 0.5rem !important; 
    }

    /* עיצוב ניווט עליון קומפקטי */
    div[data-testid="stSegmentedControl"] {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 3px;
        margin-bottom: 15px !important;
    }
    div[data-testid="stSegmentedControl"] button {
        height: 40px !important;
        font-size: 0.9rem !important;
    }

    /* כפתורי רדיו (1-10) - שיהיו קטנים וצפופים */
    div[data-role="radiogroup"] { 
        gap: 2px !important; 
    }
    div[data-role="radiogroup"] label {
        padding: 5px !important;
        font-size: 0.8rem !important;
    }

    /* כפתור שמירה מותאם */
    .stButton button { 
        width: 100%; 
        border-radius: 8px; 
        background-color: #2e7d32; 
        color: white; 
        height: 3rem;
        font-weight: bold;
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

# --- 3. ניווט ---
menu = st.segmented_control(
    "תפריט",
    options=["👤 שחקן", "⚙️ מנהל"],
    default="👤 שחקן",
    label_visibility="collapsed"
)

# --- 4. תוכן ---
if menu == "👤 שחקן":
    st.title("📝 עדכון ודירוג")
    names = sorted([str(p['name']) for p in st.session_state.players]) if st.session_state.players else []
    sel = st.selectbox("בחר שם:", ["---", "🆕 חדש"] + names)
    
    final_name = ""
    curr = None
    if sel == "🆕 חדש": 
        final_name = st.text_input("שם מלא:")
    elif sel != "---":
        final_name = sel
        curr = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        st.subheader(f"פרופיל: {final_name}")
        year = st.number_input("שנת לידה:", 1950, 2026, int(curr['birth_year']) if curr and 'birth_year' in curr else 1995)
        
        roles = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
        def_roles = curr['pos'].split(", ") if curr and 'pos' in curr and isinstance(curr['pos'], str) else []
        selected_pos = st.pills("תפקידים:", roles, selection_mode="multi", default=def_roles)
        
        st.write("**דירוג אישי (1-10):**")
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

        if st.button("שמור ✅"):
            new_p = {"name": final_name, "birth_year": year, "pos": ", ".join(selected_pos), "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
            idx = next((i for i, pl in enumerate(st.session_state.players) if pl['name'] == final_name), None)
            if idx is not None: st.session_state.players[idx] = new_p
            else: st.session_state.players.append(new_p)
            save_data(st.session_state.players)
            st.success("נשמר!")
            st.rerun()

elif menu == "⚙️ מנהל":
    pwd = st.text_input("סיסמה:", type="password")
    if pwd == "1234":
        admin_action = st.segmented_control("פעולה", ["ניהול", "חלוקה"], default="ניהול")
        
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
