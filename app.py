import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json
from datetime import datetime

# --- 1. עיצוב CSS חכם (צפוף לקבוצות, רגיל לממשק) ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    /* הגדרות בסיס ויישור */
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, h4, p, label, span { text-align: right !important; direction: rtl; }

    /* כותרות מוקטנות */
    .main-title { font-size: 22px !important; text-align: center !important; margin-bottom: 15px; font-weight: bold; }
    .team-header { text-align: center !important; font-size: 13px !important; font-weight: bold; margin-bottom: 4px; }

    /* נעילת שתי עמודות רק לחלוקה */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 6px !important;
    }
    div[data-testid="column"] {
        flex: 1 1 50% !important;
        min-width: 45% !important;
        max-width: 50% !important;
    }

    /* שורת שחקן סופר-צפופה */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 2px 8px;
        margin-bottom: 2px;
        display: flex;
        justify-content: flex-start;
        align-items: center;
        height: 28px;
        direction: rtl;
    }
    .p-text { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-score-inline { color: #22c55e; font-size: 11px; margin-right: 4px; }

    /* כפתור 🔄 מזערי */
    .stButton > button[key^="m_"] {
        width: 100% !important;
        height: 22px !important;
        line-height: 1 !important;
        padding: 0 !important;
        font-size: 10px !important;
        margin-bottom: 8px;
        background-color: #3d495d !important;
    }

    /* טבלת מאזן קומפקטית */
    .stats-table { width: 100%; margin-top: 10px; border-collapse: collapse; background: #2d3748; font-size: 12px; }
    .stats-table td { padding: 4px; text-align: center; border: 1px solid #4a5568; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ונתונים ---
if 'players' not in st.session_state:
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

def get_player_info(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 1995
    r = float(p.get('rating', 5.0))
    try:
        pr = json.loads(p.get('peer_ratings', '{}'))
        peers = [float(v) for v in pr.values()]
        avg_p = sum(peers)/len(peers) if peers else 0
    except: avg_p = 0
    return (r + avg_p) / 2 if avg_p > 0 else r, int(p.get('birth_year', 1995))

# --- 3. ממשק משתמש ---
st.markdown("<div class='main-title'>⚽ ניהול כדורגל</div>", unsafe_allow_html=True)

# תפריט ניווט עליון
menu = st.pills("תפריט", ["חלוקה", "מאגר", "הרשמה"], default="חלוקה")

if menu == "חלוקה":
    all_names = sorted([p['name'] for p in st.session_state.players])
    
    # הצגת מספר הנבחרים
    selected_count = len(st.session_state.get('pills_sel', []))
    selected = st.pills(f"מי הגיע? ({selected_count})", all_names, selection_mode="multi", key="pills_sel")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if not selected:
            st.error("חובה לבחור שחקנים")
        else:
            pool = []
            curr_y = datetime.now().year
            for name in selected:
                score, b_year = get_player_info(name)
                pool.append({'name': name, 'f': score, 'age': curr_y - b_year})
            
            pool.sort(key=lambda x: x['f'], reverse=True)
            # חלוקה מאוזנת (Snake)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        c1, c2 = st.columns(2)
        
        teams = [(c1, st.session_state.t1, "⚪ לבן", "w"), 
                 (c2, st.session_state.t2, "⚫ שחור", "b")]
        
        for col, team, label, pfx in teams:
            with col:
                st.markdown(f"<p class='team-header'>{label} ({len(team)})</p>", unsafe_allow_html=True)
                for i, p in enumerate(team):
                    st.markdown(f"""
                        <div class='p-box'>
                            <span class='p-text'>{p['name']} <span class='p-score-inline'>({p['f']:.1f})</span></span>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("🔄", key=f"m_{pfx}_{i}"):
                        if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                        else: st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()

        # מאזן כוחות וגיל
        s1 = sum(p['f'] for p in st.session_state.t1)
        s2 = sum(p['f'] for p in st.session_state.t2)
        a1 = sum(p['age'] for p in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
        a2 = sum(p['age'] for p in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0
        
        st.markdown(f"""
            <table class="stats-table">
                <tr><td><b>כוח</b></td><td>⚪ {s1:.1f}</td><td>⚫ {s2:.1f}</td></tr>
                <tr><td><b>גיל</b></td><td>⚪ {a1:.1f}</td><td>⚫ {a2:.1f}</td></tr>
            </table>
        """, unsafe_allow_html=True)

        msg = f"⚽ קבוצות:\n\n⚪ לבן:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1]) + f"\n\n⚫ שחור:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
        st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg)}" style="display:block; text-align:center; background:#22c55e; color:white; padding:8px; border-radius:6px; text-decoration:none; margin-top:12px; font-weight:bold; font-size:14px;">📲 שלח לוואטסאפ</a>', unsafe_allow_html=True)

elif menu == "מאגר":
    st.subheader("ניהול שחקנים")
    st.write("כאן תוכל לערוך או למחוק שחקנים מהרשימה.")
    # לוגיקת המאגר הקיימת שלך...

elif menu == "הרשמה":
    st.subheader("רישום שחקן חדש")
    # לוגיקת ההרשמה הקיימת שלך...
