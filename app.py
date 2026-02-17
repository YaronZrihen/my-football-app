import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json

# --- 1. עיצוב Mobile-First ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, h4, p, label, .stMarkdown { text-align: right !important; direction: rtl !important; }
    
    /* עיצוב כרטיס שחקן בחלוקה */
    .player-card {
        background-color: #f8f9fa;
        border-right: 5px solid #2e7d32;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    
    /* ניווט עליון */
    div[data-testid="stSegmentedControl"] { margin-top: 25px !important; margin-bottom: 20px !important; }

    .stButton button { width: 100%; border-radius: 10px; font-weight: bold; }
    .btn-save { background-color: #2e7d32 !important; color: white !important; height: 3.5rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור נתונים ---
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
    sel = st.selectbox("מי אתה?", ["---", "🆕 שחקן חדש"] + names)
    
    final_name, curr = "", None
    if sel == "🆕 שחקן חדש": final_name = st.text_input("שם מלא:")
    elif sel != "---":
        final_name = sel
        curr = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        st.subheader(f"פרופיל: {final_name}")
        year = st.number_input("שנת לידה:", 1950, 2026, int(curr['birth_year']) if curr and 'birth_year' in curr else 1995)
        roles_list = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
        def_roles = curr['pos'].split(", ") if curr and 'pos' in curr and isinstance(curr['pos'], str) else []
        selected_pos = st.pills("תפקידים:", roles_list, selection_mode="multi", default=def_roles)
        
        st.write("**דירוג אישי (1-10):**")
        rate = st.radio("עצמי", [1,2,3,4,5,6,7,8,9,10], index=int(curr['rating']-1) if curr else 4, horizontal=True, label_visibility="collapsed", key="self_r")
        
        st.divider()
        st.subheader("⭐ דרג חברים")
        p_ratings = {}
        try: p_ratings = json.loads(curr['peer_ratings']) if curr and 'peer_ratings' in curr else {}
        except: p_ratings = {}

        for p in st.session_state.players:
            if p['name'] != final_name:
                st.markdown(f"**{p['name']}**")
                p_ratings[p['name']] = st.radio(f"r_{p['name']}", [1,2,3,4,5,6,7,8,9,10], index=int(p_ratings.get(p['name'], 5))-1, horizontal=True, label_visibility="collapsed")

        if st.button("שמור הכל ✅", css_class="btn-save"):
            new_p = {"name": final_name, "birth_year": year, "pos": ", ".join(selected_pos), "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
            idx = next((i for i, pl in enumerate(st.session_state.players) if pl['name'] == final_name), None)
            if idx is not None: st.session_state.players[idx] = new_p
            else: st.session_state.players.append(new_p)
            save_data(st.session_state.players)
            st.success("נשמר!")
            st.rerun()

# --- 5. דף מנהל ---
elif menu == "⚙️ מנהל":
    pwd = st.text_input("סיסמה:", type="password")
    if pwd == "1234":
        admin_action = st.segmented_control("פעולה", ["ניהול מאגר", "חלוקת קבוצות"], default="ניהול מאגר")
        
        if admin_action == "ניהול מאגר":
            for i, p in enumerate(st.session_state.players):
                f_s, avg_p, count_p = get_final_score(p['name'])
                with st.container(border=True):
                    st.markdown(f"### {p['name']}")
                    st.write(f"🎂 גיל: {2026-int(p['birth_year'])} | 🏃 {p.get('pos', '---')}")
                    c = st.columns(3)
                    c[0].metric("אישי", f"{float(p['rating']):.1f}")
                    c[1].metric("חברים", f"{avg_p:.1f}", f"({count_p})")
                    c[2].metric("סופי", f"{f_s:.1f}")
                    if st.button("🗑️ מחק", key=f"del_{i}"):
                        st.session_state.players.pop(i)
                        save_data(st.session_state.players)
                        st.rerun()
        
        elif admin_action == "חלוקת קבוצות":
            st.title("📋 חלוקה לקבוצות")
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
                st.divider()
                # תצוגת כרטיסי שחקן בשתי עמודות
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("⚪ לבן")
                    for i, p in enumerate(st.session_state.t1):
                        with st.container():
                            st.markdown(f"""<div class='player-card'><b>{p['name']}</b><br><small>{p.get('pos','-')} | ⭐{p['f']:.1f}</small></div>""", unsafe_allow_html=True)
                            if st.button("⬅️ העבר", key=f"movet2_{i}"):
                                st.session_state.t2.append(st.session_state.t1.pop(i))
                                st.rerun()

                with col2:
                    st.subheader("⚫ שחור")
                    for i, p in enumerate(st.session_state.t2):
                        with st.container():
                            st.markdown(f"""<div class='player-card' style='border-right-color: #000;'><b>{p['name']}</b><br><small>{p.get('pos','-')} | ⭐{p['f']:.1f}</small></div>""", unsafe_allow_html=True)
                            if st.button("עבר ➡️", key=f"movet1_{i}"):
                                st.session_state.t1.append(st.session_state.t2.pop(i))
                                st.rerun()

                # סיכום עוצמה
                pow1 = sum([p['f'] for p in st.session_state.t1])
                pow2 = sum([p['f'] for p in st.session_state.t2])
                st.write(f"💪 עוצמה: לבן **{pow1:.1f}** | שחור **{pow2:.1f}**")

                # הודעת וואטסאפ
                msg = f"⚽ *הקבוצות להיום:* \n\n⚪ *לבן:* \n" + "\n".join([f"• {p['name']} ({p.get('pos','-')})" for p in st.session_state.t1])
                msg += f"\n\n⚫ *שחור:* \n" + "\n".join([f"• {p['name']} ({p.get('pos','-')})" for p in st.session_state.t2])
                st.markdown(f'[📲 שלח הודעה בוואטסאפ](https://wa.me/?text={urllib.parse.quote(msg)})')
