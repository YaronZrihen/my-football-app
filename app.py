import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json

# --- 1. הגדרות ועיצוב UI "נעול" לסלולר ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    /* הגדרות בסיס */
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    .block-container { padding: 1rem !important; max-width: 100% !important; }

    /* הכרחת שתי עמודות צמודות בכל מכשיר - התיקון הקריטי */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    [data-testid="column"] {
        flex: 1 1 50% !important;
        min-width: 45% !important;
        max-width: 50% !important;
    }

    /* עיצוב שורת שחקן צפופה */
    .p-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 2px 6px;
        margin-bottom: 2px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 28px;
    }
    .p-name { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-score { font-size: 11px; color: #22c55e; font-weight: bold; }

    /* עיצוב כפתור 🔄 קומפקטי */
    .stButton > button[key^="m_"] {
        width: 100% !important;
        height: 20px !important;
        line-height: 1 !important;
        padding: 0 !important;
        font-size: 10px !important;
        margin-top: -2px;
        margin-bottom: 8px;
    }

    /* עיצוב כפתור עריכה/מחיקה */
    .stButton > button[key^="edit_"], .stButton > button[key^="del_"] {
        height: 30px !important;
        width: 100% !important;
    }

    /* הסתרת כותרות מיותרות */
    [data-testid="stHeader"] { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ניהול נתונים ---
if 'players' not in st.session_state:
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

# משתני שליטה לניווט ועריכה
if 'menu_idx' not in st.session_state: st.session_state.menu_idx = 0
if 'edit_name' not in st.session_state: st.session_state.edit_name = "---"
if 'ver' not in st.session_state: st.session_state.ver = 0 # גרסה לרענון ווידג'טים

def save():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = pd.DataFrame(st.session_state.players)
    conn.update(data=df)
    st.cache_data.clear()

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 1995
    r = float(p.get('rating', 5.0))
    try:
        pr = json.loads(p.get('peer_ratings', '{}'))
        peers = [float(v) for v in pr.values()]
        avg_p = sum(peers)/len(peers) if peers else 0
    except: avg_p = 0
    return (r + avg_p) / 2 if avg_p > 0 else r, int(p.get('birth_year', 1995))

# --- 3. תפריט טאבים ---
tab = st.radio("M", ["👤 שחקן", "⚙️ מנהל"], index=st.session_state.menu_idx, horizontal=True, label_visibility="collapsed")
st.session_state.menu_idx = 0 if tab == "👤 שחקן" else 1

# --- 4. דף שחקן ---
if st.session_state.menu_idx == 0:
    st.subheader("רישום ועדכון")
    names = sorted([p['name'] for p in st.session_state.players])
    options = ["---", "🆕 חדש"] + names
    
    # מנגנון בחירה אוטומטית בעת עריכה
    try: current_idx = options.index(st.session_state.edit_name)
    except: current_idx = 0
    
    sel = st.selectbox("בחר שחקן:", options, index=current_idx, key=f"sel_{st.session_state.ver}")
    
    if sel != "---":
        p_data = next((p for p in st.session_state.players if p['name'] == sel), None)
        f_name = st.text_input("שם מלא:", value=sel if sel != "🆕 חדש" else "")
        
        if f_name:
            y = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
            rate = st.select_slider("דירוג עצמי:", options=range(1,11), value=int(p_data['rating']) if p_data else 5)
            
            if st.button("שמור נתונים ✅", use_container_width=True):
                new_p = {"name": f_name, "birth_year": y, "rating": rate, "pos": p_data.get('pos','') if p_data else "", "peer_ratings": p_data.get('peer_ratings','{}') if p_data else "{}"}
                idx = next((i for i, x in enumerate(st.session_state.players) if x['name'] == f_name), None)
                if idx is not None: st.session_state.players[idx] = new_p
                else: st.session_state.players.append(new_p)
                save()
                st.session_state.edit_name = "---"
                st.session_state.ver += 1
                st.rerun()

# --- 5. דף מנהל ---
else:
    pwd = st.text_input("סיסמה:", type="password")
    if pwd == "1234":
        mode = st.pills("תצוגה", ["חלוקה", "מאגר"], default="חלוקה")
        
        if mode == "מאגר":
            for i, p in enumerate(st.session_state.players):
                score, _ = get_stats(p['name'])
                c1, c2, c3 = st.columns([3, 0.5, 0.5])
                with c1: st.markdown(f"<div class='p-card'><span>{p['name']}</span><span class='p-score'>{score:.1f}</span></div>", unsafe_allow_html=True)
                with c2: 
                    if st.button("✏️", key=f"edit_{i}"):
                        st.session_state.edit_name = p['name']
                        st.session_state.menu_idx = 0
                        st.session_state.ver += 1
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.players.pop(i); save(); st.rerun()

        elif mode == "חלוקה":
            active_names = st.pills("מי הגיע?", [p['name'] for p in st.session_state.players], selection_mode="multi")
            
            if st.button("חלק קבוצות 🚀", use_container_width=True):
                pool = []
                for name in active_names:
                    s, _ = get_stats(name)
                    pool.append(next(p for p in st.session_state.players if p['name'] == name))
                    pool[-1]['f_score'] = s
                pool.sort(key=lambda x: x['f_score'], reverse=True)
                st.session_state.t1, st.session_state.t2 = pool[0::2], pool[1::2]

            if 't1' in st.session_state and active_names:
                # הצגת שתי עמודות צמודות
                col_a, col_b = st.columns(2)
                
                for col, team, label, pfx in zip([col_a, col_b], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"], ["w", "b"]):
                    with col:
                        st.markdown(f"<p style='text-align:center;margin:0;font-weight:bold;'>{label}</p>", unsafe_allow_html=True)
                        for i, p in enumerate(team):
                            st.markdown(f"<div class='p-card'><span class='p-name'>{p['name']}</span><span class='p-score'>{p.get('f_score',0):.1f}</span></div>", unsafe_allow_html=True)
                            if st.button("🔄", key=f"m_{pfx}_{i}"):
                                if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                                else: st.session_state.t1.append(st.session_state.t2.pop(i))
                                st.rerun()

                # מאזן כוחות
                s1 = sum(p.get('f_score', 0) for p in st.session_state.t1)
                s2 = sum(p.get('f_score', 0) for p in st.session_state.t2)
                st.markdown(f"<div style='text-align:center; background:#3d495d; padding:5px; border-radius:4px; margin-top:10px; font-size:13px;'>⚪ {s1:.1f} | ⚫ {s2:.1f}</div>", unsafe_allow_html=True)

                # כפתור וואטסאפ
                msg = f"⚽ קבוצות:\n\n⚪ לבן:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1]) + f"\n\n⚫ שחור:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
                st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg)}" style="display:block; text-align:center; background:#22c55e; color:white; padding:8px; border-radius:4px; text-decoration:none; margin-top:10px; font-size:14px;">📲 שלח לוואטסאפ</a>', unsafe_allow_html=True)
