import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. הגדרות ועיצוב UI ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, h4, p, label, span { color: #e2e8f0 !important; text-align: right !important; }
    
    /* פריסת עמודות צפופה במיוחד */
    [data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        display: flex !important;
        flex-wrap: nowrap !important;
        gap: 2px !important;
    }
    
    [data-testid="column"] {
        width: 50% !important;
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }

    /* שורת שחקן "רזה" וקומפקטית */
    .player-row-box {
        background-color: #2d3748;
        border: 1px solid #4a5568;
        padding: 2px 4px;
        border-radius: 4px;
        margin-bottom: 2px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        overflow: hidden;
    }

    .player-name-text {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 70%;
    }

    /* כפתור העברה מזערי שמשולב בשורה */
    .stButton > button[key^="m_"] {
        width: 22px !important;
        height: 18px !important;
        min-height: 18px !important;
        padding: 0px !important;
        font-size: 10px !important;
        line-height: 1 !important;
        background-color: #4a5568 !important;
        border: 0.5px solid #718096 !important;
    }

    /* טבלת מאזנים צפופה */
    .stats-table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 11px; }
    .stats-table td { padding: 3px; border: 1px solid #4a5568; text-align: center; }
    
    /* צמצום אלמנטים כלליים */
    .stSelectbox, .stTextInput { margin-bottom: -10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ונתונים ---
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
choice = st.radio("M", ["👤 שחקן", "⚙️ מנהל"], index=st.session_state.menu_index, label_visibility="collapsed")
st.session_state.menu_index = 0 if choice == "👤 שחקן" else 1

# --- 4. דף שחקן ---
if st.session_state.menu_index == 0:
    st.title("📝 רישום")
    names = sorted([str(p['name']) for p in st.session_state.players])
    options = ["---", "🆕 חדש"] + names
    try: default_idx = options.index(st.session_state.edit_player)
    except: default_idx = 0
    sel = st.selectbox("בחר:", options, index=default_idx, key=f"sel_{st.session_state.widget_key}")
    
    if sel != "---":
        curr = next((p for p in st.session_state.players if p['name'] == sel), None)
        f_name = st.text_input("שם:", value=sel if sel != "🆕 חדש" else "")
        if f_name:
            with st.container(border=True):
                y = st.number_input("שנה:", 1950, 2026, int(curr['birth_year']) if curr else 1995)
                roles = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
                def_r = curr['pos'].split(", ") if curr and isinstance(curr['pos'], str) else []
                pos = st.pills("תפקיד:", roles, selection_mode="multi", default=def_r)
                rate = st.radio("ציון:", [1,2,3,4,5,6,7,8,9,10], index=int(curr['rating']-1) if curr else 4, horizontal=True)
            
            p_ratings = json.loads(curr['peer_ratings']) if curr and 'peer_ratings' in curr else {}
            for p in st.session_state.players:
                if p['name'] != f_name:
                    st.write(f"<small>{p['name']}</small>", unsafe_allow_html=True)
                    p_ratings[p['name']] = st.radio(f"r_{p['name']}", [1,2,3,4,5,6,7,8,9,10], index=int(p_ratings.get(p['name'], 5))-1, horizontal=True, key=f"rt_{p['name']}_{sel}", label_visibility="collapsed")

            if st.button("שמור"):
                new_d = {"name": f_name, "birth_year": y, "pos": ", ".join(pos), "rating": rate, "peer_ratings": json.dumps(p_ratings, ensure_ascii=False)}
                idx = next((i for i, x in enumerate(st.session_state.players) if x['name'] == f_name), None)
                if idx is not None: st.session_state.players[idx] = new_d
                else: st.session_state.players.append(new_d)
                save_data()
                st.session_state.edit_player = "---"
                st.rerun()

# --- 5. דף מנהל ---
else:
    pwd = st.text_input("Pass:", type="password")
    if pwd == "1234":
        act = st.pills("P", ["מאגר", "חלוקה"], default="מאגר", label_visibility="collapsed")
        
        if act == "מאגר":
            for i, p in enumerate(st.session_state.players):
                f_s, _, b_y = get_stats(p['name'])
                with st.container():
                    c1, c2, c3 = st.columns([3.5, 0.5, 0.5])
                    with c1: st.markdown(f"<div class='player-row-box'>{p['name']} | ⭐{f_s:.1f}</div>", unsafe_allow_html=True)
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
            
            if 't1' in st.session_state and selected:
                col1, col2 = st.columns(2)
                for col, team, label, key_pfx in zip([col1, col2], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"], ["w", "b"]):
                    with col:
                        st.markdown(f"<p style='text-align:center; font-weight:bold; margin-bottom:2px;'>{label}</p>", unsafe_allow_html=True)
                        for i, p in enumerate(team):
                            # שורה הכוללת שם, ציון וכפתור העברה
                            c_p, c_b = st.columns([0.8, 0.2])
                            with c_p:
                                st.markdown(f"<div class='player-row-box'><span class='player-name-text'>{p['name']}</span> <span>{p['f']:.1f}</span></div>", unsafe_allow_html=True)
                            with c_b:
                                if st.button("🔄", key=f"m_{key_pfx}_{i}"):
                                    if key_pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                                    else: st.session_state.t1.append(st.session_state.t2.pop(i))
                                    st.rerun()
                
                # מאזן
                p1, p2 = sum([x['f'] for x in st.session_state.t1]), sum([x['f'] for x in st.session_state.t2])
                st.markdown(f"""
                <table class="stats-table">
                    <tr><td>כוח לבן: <b>{p1:.1f}</b></td><td>כוח שחור: <b>{p2:.1f}</b></td></tr>
                </table>
                """, unsafe_allow_html=True)

                msg = f"⚽ קבוצות:\n\n⚪ לבן:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1])
                msg += f"\n\n⚫ שחור:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
                st.markdown(f'[📲 שלח לוואטסאפ](https://wa.me/?text={urllib.parse.quote(msg)})')
