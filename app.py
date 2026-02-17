import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב UI ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, h4, p, label, span { color: #e2e8f0 !important; text-align: right !important; }
    .admin-player-row { background-color: #2d3748; border: 1px solid #4a5568; padding: 10px; border-radius: 8px; text-align: right; margin-bottom: 5px; width: 100%; }
    .stButton > button { border-radius: 6px !important; background-color: #4a5568 !important; color: white !important; border: none !important; }
    .stButton > button[key^="edit_"], .stButton > button[key^="del_"], .stButton > button[key^="move_"] { width: 40px !important; height: 35px !important; padding: 0px !important; font-size: 16px !important; }
    
    /* טבלת מאזנים */
    .stats-table { width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #2d3748; border-radius: 10px; overflow: hidden; }
    .stats-table th, .stats-table td { padding: 12px; text-align: center; border: 1px solid #4a5568; }
    .stats-table th { background-color: #3d495d; color: #22c55e; }

    div[data-testid="stRadio"] > div { flex-direction: row !important; justify-content: center; gap: 10px; }
    div[data-testid="stRadio"] label { background-color: #2d3748; padding: 10px 20px; border-radius: 10px; border: 1px solid #4a5568; cursor: pointer; }
    div[data-testid="stRadio"] label[data-checked="true"] { background-color: #4a5568; border-color: #22c55e; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. אתחול נתונים ---
if 'players' not in st.session_state:
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

if 'menu_index' not in st.session_state: st.session_state.menu_index = 0
if 'edit_player' not in st.session_state: st.session_state.edit_player = "---"
if 'widget_key' not in st.session_state: st.session_state.widget_key = 0

def save_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = pd.DataFrame(st.session_state.players)
    conn.update(data=df)
    st.cache_data.clear()

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 0.0, 1995
    s_rate = float(p.get('rating', 5.0))
    peer_scores = []
    for player in st.session_state.players:
        try:
            r = json.loads(player.get('peer_ratings', '{}'))
            if name in r: peer_scores.append(float(r[name]))
        except: continue
    avg_p = sum(peer_scores)/len(peer_scores) if peer_scores else 0.0
    return (s_rate + avg_p) / 2 if avg_p > 0 else s_rate, avg_p, int(p.get('birth_year', 1995))

# --- 3. תפריט ---
choice = st.radio("ניווט", ["👤 שחקן", "⚙️ מנהל"], index=st.session_state.menu_index, label_visibility="collapsed")
st.session_state.menu_index = 0 if choice == "👤 שחקן" else 1

# --- 4. דף שחקן ---
if st.session_state.menu_index == 0:
    st.title("📝 רישום ודירוג")
    names = sorted([str(p['name']) for p in st.session_state.players])
    options = ["---", "🆕 חדש"] + names
    try: default_idx = options.index(st.session_state.edit_player)
    except: default_idx = 0

    sel = st.selectbox("מי אתה?", options, index=default_idx, key=f"sel_{st.session_state.widget_key}")
    
    if sel != "---":
        curr = next((p for p in st.session_state.players if p['name'] == sel), None)
        f_name = st.text_input("שם מלא:", value=sel if sel != "🆕 חדש" else "")
        if f_name:
            with st.container(border=True):
                y = st.number_input("שנת לידה:", 1950, 2026, int(curr['birth_year']) if curr else 1995)
                roles = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
                def_r = curr['pos'].split(", ") if curr and isinstance(curr['pos'], str) else []
                pos = st.pills("תפקידים:", roles, selection_mode="multi", default=def_r)
                rate = st.radio("דירוג (1-10):", [1,2,3,4,5,6,7,8,9,10], index=int(curr['rating']-1) if curr else 4, horizontal=True)
            
            p_ratings = json.loads(curr['peer_ratings']) if curr and 'peer_ratings' in curr else {}
            for p in st.session_state.players:
                if p['name'] != f_name:
                    st.write(f"**{p['name']}**")
                    p_ratings[p['name']] = st.radio(f"r_{p['name']}", [1,2,3,4,5,6,7,8,9,10], index=int(p_ratings.get(p['name'], 5))-1, horizontal=True, key=f"rt_{p['name']}_{sel}")

            if st.button("שמור ✅"):
                new_d = {"name": f_name, "birth_year": y, "pos": ", ".join(pos), "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
                idx = next((i for i, x in enumerate(st.session_state.players) if x['name'] == f_name), None)
                if idx is not None: st.session_state.players[idx] = new_d
                else: st.session_state.players.append(new_d)
                save_data()
                st.session_state.edit_player = "---"
                st.rerun()

# --- 5. דף מנהל ---
else:
    pwd = st.text_input("סיסמה:", type="password")
    if pwd == "1234":
        act = st.pills("פעולה", ["מאגר", "חלוקה"], default="מאגר")
        
        if act == "מאגר":
            for i, p in enumerate(st.session_state.players):
                f_s, avg_p, b_y = get_stats(p['name'])
                age = (2026 - b_y) if isinstance(b_y, (int, float)) else "??"
                s_pos = str(p.get('pos', '-'))
                with st.container():
                    c1, c2, c3 = st.columns([3, 0.6, 0.6])
                    with c1: st.markdown(f"<div class='admin-player-row'><b>{p['name']}</b> | {age} | {s_pos[:15]}<br><small>⭐ {f_s:.1f}</small></div>", unsafe_allow_html=True)
                    with c2:
                        if st.button("✏️", key=f"edit_{i}"):
                            st.session_state.edit_player = p['name']
                            st.session_state.menu_index, st.session_state.widget_key = 0, st.session_state.widget_key + 1
                            st.rerun()
                    with c3:
                        if st.button("🗑️", key=f"del_{i}"):
                            st.session_state.players.pop(i); save_data(); st.rerun()
        
        elif act == "חלוקה":
            pool = []
            for p in st.session_state.players:
                f_s, _, b_y = get_stats(p['name'])
                pool.append({**p, "f": f_s, "age": 2026-b_y if b_y else 30})
            
            selected = st.pills("מי הגיע?", [p['name'] for p in pool], selection_mode="multi")
            if st.button("חלק קבוצות 🚀"):
                active = [p for p in pool if p['name'] in selected]
                active.sort(key=lambda x: x['f'], reverse=True)
                st.session_state.t1, st.session_state.t2 = active[0::2], active[1::2]
            
            if selected and 't1' in st.session_state:
                cols = st.columns(2)
                for col, team, label in zip(cols, [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"]):
                    with col:
                        st.subheader(label)
                        for i, p in enumerate(team):
                            st.markdown(f"<div style='background:#2d3748; padding:5px; border-radius:5px; margin-bottom:5px;'><b>{p['name']}</b><br><small>⭐{p['f']:.1f}</small></div>", unsafe_allow_html=True)
                            if st.button("🔄", key=f"m_{label}_{i}"):
                                if label == "⚪ לבן": st.session_state.t2.append(st.session_state.t1.pop(i))
                                else: st.session_state.t1.append(st.session_state.t2.pop(i))
                                st.rerun()
                
                # --- טבלת מאזנים ---
                p1, p2 = sum([x['f'] for x in st.session_state.t1]), sum([x['f'] for x in st.session_state.t2])
                a1 = sum([x['age'] for x in st.session_state.t1])/len(st.session_state.t1) if st.session_state.t1 else 0
                a2 = sum([x['age'] for x in st.session_state.t2])/len(st.session_state.t2) if st.session_state.t2 else 0
                
                st.markdown(f"""
                <table class="stats-table">
                    <tr><th>מדד</th><th>⚪ לבן</th><th>⚫ שחור</th></tr>
                    <tr><td>💪 עוצמה כללית</td><td>{p1:.1f}</td><td>{p2:.1f}</td></tr>
                    <tr><td>🎂 גיל ממוצע</td><td>{a1:.1f}</td><td>{a2:.1f}</td></tr>
                    <tr><td>🏃 כמות</td><td>{len(st.session_state.t1)}</td><td>{len(st.session_state.t2)}</td></tr>
                </table>
                """, unsafe_allow_html=True)

                msg = f"⚽ הקבוצות להיום:\n\n⚪ לבן:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1])
                msg += f"\n\n⚫ שחור:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
                st.markdown(f'[📲 שלח לוואטסאפ](https://wa.me/?text={urllib.parse.quote(msg)})')
