import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json

# --- 1. עיצוב UI משופר (צבעים וניגודיות) ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    /* רקע כללי לאפליקציה */
    .stApp { 
        background-color: #f0f2f5; 
        direction: rtl; 
        text-align: right; 
    }
    
    h1, h2, h3, h4, p, label, .stMarkdown { text-align: right !important; direction: rtl !important; }

    /* עיצוב כותרות */
    h1 { color: #1e3a8a; font-size: 1.8rem !important; margin-bottom: 15px !important; }

    /* כרטיסי שחקן בניהול ובחלוקה */
    .player-card-white {
        background-color: white;
        border-right: 6px solid #2e7d32;
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        color: #333;
    }
    
    .player-card-black {
        background-color: #333;
        border-right: 6px solid #000;
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        color: white;
    }

    /* עיצוב תיבות הקלט (Inputs) */
    div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] select {
        background-color: white !important;
        border-radius: 8px !important;
    }

    /* ניווט עליון בולט */
    div[data-testid="stSegmentedControl"] {
        background-color: #ffffff;
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 4px;
        margin-top: 20px !important;
    }

    /* כפתור שמירה ירוק חזק */
    .stButton button { 
        width: 100%; 
        border-radius: 12px; 
        background-color: #15803d !important; 
        color: white !important; 
        font-weight: bold;
        height: 3.5rem;
    }
    
    /* מפריד */
    hr { margin: 2rem 0 !important; border-top: 2px solid #ddd !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה וחיבור נתונים ---
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
menu = st.segmented_control("תפריט", ["👤 שחקן", "⚙️ מנהל"], default="👤 שחקן", label_visibility="collapsed")

# --- 4. דף שחקן ---
if menu == "👤 שחקן":
    st.title("📝 עדכון ודירוג")
    names = sorted([str(p['name']) for p in st.session_state.players]) if st.session_state.players else []
    sel = st.selectbox("בחר שם מתוך הרשימה:", ["---", "🆕 שחקן חדש"] + names)
    
    final_name, curr = "", None
    if sel == "🆕 שחקן חדש": 
        final_name = st.text_input("הקלד שם מלא:")
    elif sel != "---":
        final_name = sel
        curr = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        with st.container(border=True):
            st.subheader(f"עריכת פרופיל: {final_name}")
            year = st.number_input("שנת לידה:", 1950, 2026, int(curr['birth_year']) if curr and 'birth_year' in curr else 1995)
            roles_list = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
            def_roles = curr['pos'].split(", ") if curr and 'pos' in curr and isinstance(curr['pos'], str) else []
            selected_pos = st.pills("תפקידים:", roles_list, selection_mode="multi", default=def_roles)
            
            st.write("**דירוג אישי (1-10):**")
            rate = st.radio("עצמי", [1,2,3,4,5,6,7,8,9,10], index=int(curr['rating']-1) if curr else 4, horizontal=True, label_visibility="collapsed", key="self_r")
        
        st.markdown("### ⭐ דרג חברים")
        p_ratings = {}
        try: p_ratings = json.loads(curr['peer_ratings']) if curr and 'peer_ratings' in curr else {}
        except: p_ratings = {}

        for p in st.session_state.players:
            if p['name'] != final_name:
                with st.container(border=True):
                    st.markdown(f"**{p['name']}**")
                    p_ratings[p['name']] = st.radio(f"r_{p['name']}", [1,2,3,4,5,6,7,8,9,10], index=int(p_ratings.get(p['name'], 5))-1, horizontal=True, label_visibility="collapsed")

        if st.button("שמור הכל ✅"):
            new_p = {"name": final_name, "birth_year": year, "pos": ", ".join(selected_pos), "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
            idx = next((i for i, pl in enumerate(st.session_state.players) if pl['name'] == final_name), None)
            if idx is not None: st.session_state.players[idx] = new_p
            else: st.session_state.players.append(new_p)
            save_data(st.session_state.players)
            st.success("נשמר בהצלחה!")
            st.rerun()

# --- 5. דף מנהל ---
elif menu == "⚙️ מנהל":
    pwd = st.text_input("סיסמה:", type="password")
    if pwd == "1234":
        admin_action = st.segmented_control("פעולה", ["ניהול מאגר", "חלוקת קבוצות"], default="ניהול מאגר")
        
        if admin_action == "ניהול מאגר":
            st.title("👤 רשימת שחקנים")
            for i, p in enumerate(st.session_state.players):
                f_s, avg_p, count_p = get_final_score(p['name'])
                with st.container(border=True):
                    st.markdown(f"### {p['name']}")
                    st.write(f"🎂 גיל: {2026-int(p['birth_year'])} | 🏃 {p.get('pos', '---')}")
                    c = st.columns(3)
                    c[0].metric("אישי", f"{float(p['rating']):.1f}")
                    c[1].metric("חברים", f"{avg_p:.1f}", f"({count_p} מדרגים)")
                    c[2].metric("סופי", f"{f_s:.1f}")
                    if st.button("🗑️ מחק", key=f"del_{i}"):
                        st.session_state.players.pop(i)
                        save_data(st.session_state.players)
                        st.rerun()
        
        elif admin_action == "חלוקת קבוצות":
            st.title("📋 חלוקה מאוזנת")
            pool = []
            for p in st.session_state.players:
                f_s, _, _ = get_final_score(p['name'])
                pool.append({**p, "f": f_s})
            
            selected_names = st.multiselect("מי משחק היום?", [p['name'] for p in pool])
            
            if "t1" not in st.session_state or st.button("חלק אוטומטית 🚀"):
                active = [p for p in pool if p['name'] in selected_names]
                active.sort(key=lambda x: x['f'], reverse=True)
                st.session_state.t1 = active[0::2]
                st.session_state.t2 = active[1::2]

            if selected_names:
                st.write(f"**סה\"כ שחקנים:** {len(selected_names)}")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### ⚪ לבן")
                    for i, p in enumerate(st.session_state.t1):
                        st.markdown(f"<div class='player-card-white'><b>{p['name']}</b><br><small>{p.get('pos','-')} | ⭐{p['f']:.1f}</small></div>", unsafe_allow_html=True)
                        if st.button("⬅️ העבר", key=f"movet2_{i}"):
                            st.session_state.t2.append(st.session_state.t1.pop(i))
                            st.rerun()

                with col2:
                    st.markdown("#### ⚫ שחור")
                    for i, p in enumerate(st.session_state.t2):
                        st.markdown(f"<div class='player-card-black'><b>{p['name']}</b><br><small>{p.get('pos','-')} | ⭐{p['f']:.1f}</small></div>", unsafe_allow_html=True)
                        if st.button("עבר ➡️", key=f"movet1_{i}"):
                            st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()

                p1 = sum([p['f'] for p in st.session_state.t1])
                p2 = sum([p['f'] for p in st.session_state.t2])
                st.info(f"⚖️ מאזן כוחות: לבן **{p1:.1f}** | שחור **{p2:.1f}**")

                msg = f"⚽ *הקבוצות להיום:* \n\n⚪ *לבן:* \n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1])
                msg += f"\n\n⚫ *שחור:* \n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
                st.markdown(f'[📲 שלח לוואטסאפ](https://wa.me/?text={urllib.parse.quote(msg)})')
