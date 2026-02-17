import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. הגדרות ועיצוב UI (Soft Dark & Compact) ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    /* רקע ואווירה כללית */
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, h4, p, label, span { color: #e2e8f0 !important; text-align: right !important; }

    /* כרטיס שחקן בחלוקה - צמוד לימין */
    .player-card {
        background-color: #2d3748;
        border: 1px solid #4a5568;
        padding: 8px 12px;
        border-radius: 8px;
        margin-bottom: 5px;
        text-align: right;
    }
    
    /* שורת שחקן במאגר - קומפקטית */
    .admin-player-row {
        background-color: #2d3748;
        border: 1px solid #4a5568;
        padding: 6px 12px;
        border-radius: 8px;
        text-align: right;
        width: 100%;
    }

    /* כפתורי פעולה זעירים (עריכה, מחיקה, העברה) */
    .stButton > button {
        border-radius: 6px !important;
        background-color: #4a5568 !important;
        color: white !important;
        border: none !important;
    }
    
    /* סגנון ספציפי לכפתורי ה-Icons הקטנים */
    .stButton > button[key^="edit_"], .stButton > button[key^="del_"], .stButton > button[key^="move_"] {
        width: 38px !important;
        height: 32px !important;
        padding: 0px !important;
        font-size: 14px !important;
    }

    /* מונה שחקנים */
    .count-badge {
        background-color: #1e293b;
        padding: 4px 12px;
        border-radius: 12px;
        color: #22c55e !important;
        border: 1px solid #22c55e;
        display: inline-block;
        margin: 10px 0;
    }

    /* תיבות קלט */
    input, select, textarea {
        background-color: #2d3748 !important;
        color: white !important;
        border: 1px solid #4a5568 !important;
    }
    
    div[data-testid="stSegmentedControl"] { background-color: #2d3748; border-radius: 10px; padding: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ולוגיקה ---
conn = st.connection("gsheets", type=GSheetsConnection)
curr_year = datetime.now().year

if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except:
        st.session_state.players = []

if 'edit_player_name' not in st.session_state:
    st.session_state.edit_player_name = None

def save_data():
    df = pd.DataFrame(st.session_state.players)
    conn.update(data=df)
    st.cache_data.clear()

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
menu = st.segmented_control("תפריט", ["👤 שחקן", "⚙️ מנהל"], default="👤 שחקן", label_visibility="collapsed")

# --- 4. דף שחקן ---
if menu == "👤 שחקן":
    st.title("📝 רישום ודירוג")
    names = sorted([str(p['name']) for p in st.session_state.players]) if st.session_state.players else []
    options = ["---", "🆕 חדש"] + names
    
    # לוגיקת בחירה אוטומטית בעריכה
    start_idx = 0
    if st.session_state.edit_player_name in options:
        start_idx = options.index(st.session_state.edit_player_name)
        st.session_state.edit_player_name = None # איפוס אחרי שימוש

    sel = st.selectbox("בחר שם מהרשימה:", options, index=start_idx)
    
    if sel != "---":
        curr = next((p for p in st.session_state.players if p['name'] == sel), None)
        final_name = st.text_input("שם מלא:", value=sel if sel != "🆕 חדש" else "")
        
        if final_name:
            with st.container(border=True):
                y = st.number_input("שנת לידה:", 1950, curr_year, int(curr['birth_year']) if curr else 1995)
                roles = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
                def_r = curr['pos'].split(", ") if curr and isinstance(curr['pos'], str) else []
                selected_pos = st.pills("תפקידים:", roles, selection_mode="multi", default=def_r)
                
                st.write("**דירוג עצמי (1-10):**")
                rate = st.radio("rating_self", [1,2,3,4,5,6,7,8,9,10], index=int(curr['rating']-1) if curr else 4, horizontal=True, label_visibility="collapsed")
            
            st.divider()
            st.subheader("⭐ דרג חברים")
            p_ratings = json.loads(curr['peer_ratings']) if curr and 'peer_ratings' in curr else {}
            for p in st.session_state.players:
                if p['name'] != final_name:
                    st.write(f"**{p['name']}**")
                    p_ratings[p['name']] = st.radio(f"r_{p['name']}", [1,2,3,4,5,6,7,8,9,10], index=int(p_ratings.get(p['name'], 5))-1, horizontal=True, label_visibility="collapsed")

            if st.button("שמור הכל ✅"):
                new_p = {"name": final_name, "birth_year": y, "pos": ", ".join(selected_pos), "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
                idx = next((i for i, pl in enumerate(st.session_state.players) if pl['name'] == final_name), None)
                if idx is not None: st.session_state.players[idx] = new_p
                else: st.session_state.players.append(new_p)
                save_data()
                st.success("הנתונים נשמרו!")
                st.rerun()

# --- 5. דף מנהל ---
elif menu == "⚙️ מנהל":
    pwd = st.text_input("סיסמה:", type="password")
    if pwd == "1234":
        admin_act = st.segmented_control("פעולה", ["מאגר", "חלוקה"], default="מאגר")
        
        if admin_act == "מאגר":
            st.subheader("🗃️ ניהול שחקנים")
            for i, p in enumerate(st.session_state.players):
                f_s, avg_p, b_y = get_stats(p['name'])
                age = curr_year - b_y if b_y else "??"
                pos = p.get('pos', '-')
                pos_display = (pos[:15] + '..') if isinstance(pos, str) and len(pos) > 15 else pos
                
                with st.container():
                    c_txt, c_ed, c_del = st.columns([3, 0.6, 0.6])
                    with c_txt:
                        st.markdown(f"""
                            <div class='admin-player-row'>
                                <b>{p['name']}</b> | {age} | {pos_display}<br>
                                <small style='color:#94a3b8;'>⭐ {f_s:.1f} (אישי: {p.get('rating',0)} | חברים: {avg_p:.1f})</small>
                            </div>
                        """, unsafe_allow_html=True)
                    with c_ed:
                        if st.button("✏️", key=f"edit_{i}"):
                            st.session_state.edit_player_name = p['name']
                            st.info("השחקן נבחר. עברו ללשונית 'שחקן' לעריכה.")
                            st.rerun()
                    with c_del:
                        if st.button("🗑️", key=f"del_{i}"):
                            st.session_state.players.pop(i)
                            save_data()
                            st.rerun()
        
        elif admin_act == "חלוקה":
            pool = []
            for p in st.session_state.players:
                f_s, _, b_y = get_stats(p['name'])
                pool.append({**p, "f": f_s, "age": curr_year-b_y})
            
            selected_names = st.pills("מי הגיע?", [p['name'] for p in pool], selection_mode="multi")
            st.markdown(f"<div class='count-badge'>נבחרו {len(selected_names)} שחקנים</div>", unsafe_allow_html=True)
            
            if st.button("חלק קבוצות 🚀"):
                active = [p for p in pool if p['name'] in selected_names]
                active.sort(key=lambda x: x['f'], reverse=True)
                st.session_state.t1 = active[0::2]
                st.session_state.t2 = active[1::2]

            if selected_names and 't1' in st.session_state:
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

                p1, p2 = sum([p['f'] for p in st.session_state.t1]), sum([p['f'] for p in st.session_state.t2])
                age1 = sum([p['age'] for p in st.session_state.t1])/len(st.session_state.t1) if st.session_state.t1 else 0
                age2 = sum([p['age'] for p in st.session_state.t2])/len(st.session_state.t2) if st.session_state.t2 else 0
                
                with st.container(border=True):
                    st.write(f"💪 עוצמה: לבן {p1:.1f} | שחור {p2:.1f}")
                    st.write(f"🎂 גיל: לבן {age1:.1f} | שחור {age2:.1f}")

                msg = f"⚽ הקבוצות:\n\n⚪ לבן:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1])
                msg += f"\n\n⚫ שחור:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
                st.markdown(f'[📲 שלח לוואטסאפ](https://wa.me/?text={urllib.parse.quote(msg)})')
