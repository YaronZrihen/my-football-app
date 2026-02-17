import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json

# --- 1. עיצוב UI אגרסיבי לצמצום רוחב ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    
    /* ביטול מרווחים פנימיים של Streamlit */
    .block-container { padding-top: 2rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    
    /* הכרחת פריסה צמודה לעמודות */
    [data-testid="stHorizontalBlock"] {
        gap: 4px !important;
    }

    /* עיצוב שורת שחקן "מיני" */
    .player-mini-row {
        background-color: #2d3748;
        border: 1px solid #4a5568;
        padding: 1px 6px;
        border-radius: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 13px;
        height: 26px; /* גובה קבוע ודק */
        margin-bottom: 2px;
    }

    /* כפתור החלפה מזערי */
    .stButton > button[key^="m_"] {
        border-radius: 3px !important;
        padding: 0px 4px !important;
        height: 18px !important;
        min-height: 18px !important;
        width: 22px !important;
        font-size: 10px !important;
        background-color: #4a5568 !important;
        margin-top: 4px;
    }

    /* הסתרת כותרות מיותרות בסלולר */
    h5 { margin-bottom: 5px !important; font-size: 14px !important; text-align: center; }
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
    final = (s_rate + avg_p) / 2 if avg_p > 0 else s_rate
    return final, int(p.get('birth_year', 1995))

# --- 3. ניווט ---
choice = st.radio("M", ["👤 שחקן", "⚙️ מנהל"], index=st.session_state.menu_index, label_visibility="collapsed", horizontal=True)
st.session_state.menu_index = 0 if choice == "👤 שחקן" else 1

# --- 4. דף שחקן (מקוצר) ---
if st.session_state.menu_index == 0:
    st.subheader("רישום שחקן")
    # ... (הקוד של דף השחקן נשאר זהה לקוד הקודם שלך) ...
    # לטובת הקיצור אני מתמקד בתיקון ה-UI של החלוקה

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
                # שימוש בעמודות שוליים כדי לצמצם את המרכז
                # יחס של 0.1 לשוליים ו-2 למרכז יגרום לקבוצות להיות צמודות
                _, col_a, col_b, _ = st.columns([0.1, 2, 2, 0.1])
                
                teams_data = [(col_a, st.session_state.t1, "⚪ לבן", "w"), 
                              (col_b, st.session_state.t2, "⚫ שחור", "b")]
                
                for col, team, label, pfx in teams_data:
                    with col:
                        st.markdown(f"<h5>{label}</h5>", unsafe_allow_html=True)
                        for i, p in enumerate(team):
                            # שורה אחת שכוללת שם, ציון וכפתור
                            c_text, c_btn = st.columns([0.8, 0.2])
                            with c_text:
                                st.markdown(f"""<div class='player-mini-row'>
                                    <span>{p['name']}</span>
                                    <span style='color:#22c55e;'>{p['f']:.1f}</span>
                                </div>""", unsafe_allow_html=True)
                            with c_btn:
                                if st.button("🔄", key=f"m_{pfx}_{i}"):
                                    if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                                    else: st.session_state.t1.append(st.session_state.t2.pop(i))
                                    st.rerun()

                # מאזן כוחות בשורה אחת
                p1 = sum([x['f'] for x in st.session_state.t1])
                p2 = sum([x['f'] for x in st.session_state.t2])
                st.markdown(f"""
                <div style='text-align:center; background:#2d3748; padding:5px; border-radius:5px; margin-top:10px; font-size:12px;'>
                ⚪ {p1:.1f} | ⚫ {p2:.1f}
                </div>
                """, unsafe_allow_html=True)
