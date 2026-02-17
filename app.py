import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json

# --- 1. עיצוב UI קשוח למובייל ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    .block-container { padding: 1rem !important; }
    
    /* עיצוב הטבלה */
    .team-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed; /* הכרחת רוחב שווה */
    }
    .team-table td {
        vertical-align: top;
        padding: 2px;
        width: 50%;
    }
    
    /* שורת שחקן צפופה */
    .p-row {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 4px 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 13px;
        margin-bottom: 3px;
        height: 30px;
    }
    
    .p-name { 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        flex-grow: 1;
    }
    
    .p-score {
        color: #22c55e;
        font-weight: bold;
        margin-left: 5px;
    }

    /* כפתורי רדיו וטאבים קטנים */
    div[data-testid="stRadio"] > div { gap: 5px; }
    div[data-testid="stRadio"] label { padding: 5px 10px !important; font-size: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. נתונים ---
if 'players' not in st.session_state:
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

if 'menu_index' not in st.session_state: st.session_state.menu_index = 0
if 'edit_player' not in st.session_state: st.session_state.edit_player = "---"

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 1995
    s_rate = float(p.get('rating', 5.0))
    peer_scores = []
    for player in st.session_state.players:
        try:
            r = json.loads(player.get('peer_ratings', '{}'))
            if name in r: peer_scores.append(float(r[name]))
        except: continue
    avg_p = sum(peer_scores)/len(peer_scores) if peer_scores else 0.0
    return (s_rate + avg_p) / 2 if avg_p > 0 else s_rate, int(p.get('birth_year', 1995))

# --- 3. תפריט ---
choice = st.radio("M", ["👤 שחקן", "⚙️ מנהל"], index=st.session_state.menu_index, label_visibility="collapsed", horizontal=True)
st.session_state.menu_index = 0 if choice == "👤 שחקן" else 1

# --- 4. דף שחקן ---
if st.session_state.menu_index == 0:
    st.title("📝 רישום")
    # (הקוד של דף השחקן שלך כאן...)
    st.info("בחר שחקן מהרשימה או צור חדש")

# --- 5. דף מנהל וחלוקה ---
else:
    pwd = st.text_input("סיסמה:", type="password")
    if pwd == "1234":
        act = st.pills("פעולה", ["מאגר", "חלוקה"], default="חלוקה")
        
        if act == "חלוקה":
            pool = []
            for p in st.session_state.players:
                f_s, b_y = get_stats(p['name'])
                pool.append({**p, "f": f_s, "age": 2026-b_y})
            
            selected = st.pills("מי הגיע?", [p['name'] for p in pool], selection_mode="multi")
            
            if st.button("חלק קבוצות 🚀"):
                active = [p for p in pool if p['name'] in selected]
                active.sort(key=lambda x: x['f'], reverse=True)
                st.session_state.t1, st.session_state.t2 = active[0::2], active[1::2]
            
            if 't1' in st.session_state and selected:
                # יצירת טבלת HTML לשתי עמודות
                t1 = st.session_state.t1
                t2 = st.session_state.t2
                max_rows = max(len(t1), len(t2))
                
                # כותרות הטבלה
                html = """<table class='team-table'>
                    <tr>
                        <th style='text-align:center;'>⚪ לבן</th>
                        <th style='text-align:center;'>⚫ שחור</th>
                    </tr>"""
                
                st.markdown(html, unsafe_allow_html=True)
                
                # שימוש ב-Columns רק עבור הכפתורים כדי לשמור על אינטראקטיביות
                col_left, col_right = st.columns(2)
                
                with col_left:
                    for i, p in enumerate(t1):
                        st.markdown(f"""<div class='p-row'><span class='p-name'>{p['name']}</span><span class='p-score'>{p['f']:.1f}</span></div>""", unsafe_allow_html=True)
                        if st.button("🔄", key=f"mw_{i}"):
                            st.session_state.t2.append(st.session_state.t1.pop(i))
                            st.rerun()
                            
                with col_right:
                    for i, p in enumerate(t2):
                        st.markdown(f"""<div class='p-row'><span class='p-name'>{p['name']}</span><span class='p-score'>{p['f']:.1f}</span></div>""", unsafe_allow_html=True)
                        if st.button("🔄", key=f"mb_{i}"):
                            st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()

                # מאזן סופי
                p1 = sum([x['f'] for x in st.session_state.t1])
                p2 = sum([x['f'] for x in st.session_state.t2])
                st.markdown(f"<div style='text-align:center; background:#3d495d; padding:8px; border-radius:5px; margin-top:15px;'>💪 לבן: {p1:.1f} | שחור: {p2:.1f}</div>", unsafe_allow_html=True)
                
                # וואטסאפ
                msg = f"⚽ קבוצות להיום:\n\n⚪ לבן:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1]) + f"\n\n⚫ שחור:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
                st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg)}" style="display:block; text-align:center; background:#22c55e; color:white; padding:10px; border-radius:5px; text-decoration:none; margin-top:10px;">📲 שלח בוואטסאפ</a>', unsafe_allow_html=True)
