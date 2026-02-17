import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב נקי וניטרלי (RTL) ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; direction: rtl; text-align: right; }
    h1, h2, h3, h4, p, label, span { color: #334155 !important; text-align: right !important; }

    /* כרטיסי שחקן בעיצוב סולידי */
    .player-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    /* ניווט עליון פשוט */
    div[data-testid="stSegmentedControl"] {
        margin-top: 20px !important;
        background-color: #e2e8f0;
        border-radius: 8px;
        padding: 4px;
    }

    /* כפתור שמירה ירוק סולידי */
    .stButton button { 
        width: 100%; 
        border-radius: 8px; 
        background-color: #475569 !important; /* אפור כהה */
        color: white !important; 
        height: 3rem;
    }
    
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ונתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)
curr_year = datetime.now().year

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

def get_stats(player_name):
    player = next((p for p in st.session_state.players if p['name'] == player_name), None)
    if not player: return 5.0, 0.0, 1995
    self_rate = float(player.get('rating', 5.0))
    peer_scores = []
    for p in st.session_state.players:
        try:
            r = json.loads(p.get('peer_ratings', '{}'))
            if player_name in r: peer_scores.append(float(r[player_name]))
        except: continue
    avg_p = sum(peer_scores)/len(peer_scores) if peer_scores else 0.0
    final = (self_rate + avg_p) / 2 if avg_p > 0 else self_rate
    return final, avg_p, int(player.get('birth_year', 1995))

# --- 3. ניווט ---
menu = st.segmented_control("ניווט", ["👤 שחקן", "⚙️ מנהל"], default="👤 שחקן", label_visibility="collapsed")

# --- 4. דף שחקן ---
if menu == "👤 שחקן":
    st.title("📝 רישום ודירוג")
    names = sorted([str(p['name']) for p in st.session_state.players]) if st.session_state.players else []
    sel = st.selectbox("מי אתה?", ["---", "🆕 חדש"] + names)
    
    final_name, curr = "", None
    if sel == "🆕 חדש": final_name = st.text_input("שם מלא:")
    elif sel != "---":
        final_name = sel
        curr = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        st.subheader(f"פרופיל: {final_name}")
        y = st.number_input("שנת לידה:", 1950, curr_year, int(curr['birth_year']) if curr else 1995)
        roles = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
        def_r = curr['pos'].split(", ") if curr and isinstance(curr['pos'], str) else []
        selected_pos = st.pills("תפקידים:", roles, selection_mode="multi", default=def_r)
        
        st.write("**דירוג עצמי (1-10):**")
        rate = st.radio("r", [1,2,3,4,5,6,7,8,9,10], index=int(curr['rating']-1) if curr else 4, horizontal=True, label_visibility="collapsed")
        
        st.divider()
        st.subheader("⭐ דרג חברים")
        p_ratings = {}
        try: p_ratings = json.loads(curr['peer_ratings']) if curr and 'peer_ratings' in curr else {}
        except: p_ratings = {}

        for p in st.session_state.players:
            if p['name'] != final_name:
                st.write(p['name'])
                p_ratings[p['name']] = st.radio(f"r_{p['name']}", [1,2,3,4,5,6,7,8,9,10], index=int(p_ratings.get(p['name'], 5))-1, horizontal=True, label_visibility="collapsed")

        if st.button("שמור נתונים"):
            new_p = {"name": final_name, "birth_year": y, "pos": ", ".join(selected_pos), "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
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
        admin_act = st.segmented_control("פעולה", ["מאגר", "חלוקה"], default="מאגר")
        
        if admin_act == "מאגר":
            for i, p in enumerate(st.session_state.players):
                f_s, avg_p, b_y = get_stats(p['name'])
                with st.container(border=True):
                    st.write(f"**{p['name']}** | גיל: {curr_year-b_y} | {p.get('pos','-')}")
                    c = st.columns(3)
                    c[0].metric("אישי", f"{float(p['rating']):.1f}")
                    c[1].metric("חברים", f"{avg_p:.1f}")
                    c[2].metric("סופי", f"{f_s:.1f}")
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.players.pop(i)
                        save_data(st.session_state.players)
                        st.rerun()
        
        elif admin_act == "חלוקה":
            pool = []
            for p in st.session_state.players:
                f_s, _, b_y = get_stats(p['name'])
                pool.append({**p, "f": f_s, "age": curr_year-b_y})
            
            selected = st.multiselect("מי משחק?", [p['name'] for p in pool])
            
            if "t1" not in st.session_state or st.button("חלק קבוצות 🚀"):
                active = [p for p in pool if p['name'] in selected]
                active.sort(key=lambda x: x['f'], reverse=True)
                st.session_state.t1 = active[0::2]
                st.session_state.t2 = active[1::2]

            if selected:
                col1, col2 = st.columns(2)
                for col, team, label in zip([col1, col2], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"]):
                    with col:
                        st.subheader(label)
                        for i, p in enumerate(team):
                            st.markdown(f"<div class='player-card'><b>{p['name']}</b><br><small>{p['age']} | {p.get('pos','-')} | ⭐{p['f']:.1f}</small></div>", unsafe_allow_html=True)
                            if st.button("🔄", key=f"move_{label}_{i}"):
                                if label == "⚪ לבן": st.session_state.t2.append(st.session_state.t1.pop(i))
                                else: st.session_state.t1.append(st.session_state.t2.pop(i))
                                st.rerun()

                # --- מאזן כוחות וגיל ---
                p1, p2 = sum([p['f'] for p in st.session_state.t1]), sum([p['f'] for p in st.session_state.t2])
                age1 = sum([p['age'] for p in st.session_state.t1])/len(st.session_state.t1) if st.session_state.t1 else 0
                age2 = sum([p['age'] for p in st.session_state.t2])/len(st.session_state.t2) if st.session_state.t2 else 0
                
                st.info(f"💪 עוצמה: לבן {p1:.1f} | שחור {p2:.1f}\n\n🎂 ממוצע גיל: לבן {age1:.1f} | שחור {age2:.1f}")

                msg = f"⚽ הקבוצות:\n\n⚪ לבן:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1])
                msg += f"\n\n⚫ שחור:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
                st.markdown(f'[📲 שלח לוואטסאפ](https://wa.me/?text={urllib.parse.quote(msg)})')
