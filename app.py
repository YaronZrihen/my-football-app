import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
import json

# --- 1. עיצוב CSS "פטיש 5 קילו" לנעילת תצוגה ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    
    /* ביטול גמישות העמודות של Streamlit - הופך אותן לטור קשיח */
    [data-testid="column"] {
        flex: 1 1 48% !important;
        width: 48% !important;
        min-width: 48% !important;
    }
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        display: flex !important;
        gap: 5px !important;
    }

    /* עיצוב שורת שחקן סופר-קומפקטית */
    .p-box {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 4px;
        margin-bottom: 2px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 30px;
    }
    .p-name { font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70px; }
    .p-score { font-size: 10px; color: #22c55e; }

    /* כפתור 🔄 מזערי */
    .stButton > button[key^="m_"] {
        height: 22px !important;
        min-height: 22px !important;
        width: 100% !important;
        padding: 0 !important;
        font-size: 10px !important;
        margin-bottom: 5px;
        background-color: #4a5568 !important;
    }
    
    /* טבלת מאזן */
    .balance-table { width: 100%; margin-top: 10px; border-collapse: collapse; font-size: 12px; }
    .balance-table td { border: 1px solid #4a5568; padding: 4px; text-align: center; background: #2d3748; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. נתונים (אותה לוגיקה שעובדת) ---
if 'players' not in st.session_state:
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

if 't1' not in st.session_state: st.session_state.t1 = []
if 't2' not in st.session_state: st.session_state.t2 = []

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0
    r = float(p.get('rating', 5.0))
    try:
        pr = json.loads(p.get('peer_ratings', '{}'))
        peers = [float(v) for v in pr.values()]
        avg_p = sum(peers)/len(peers) if peers else 0
    except: avg_p = 0
    return (r + avg_p) / 2 if avg_p > 0 else r

# --- 3. ממשק ניהול (מפושט למקסימום) ---
st.title("⚽ חלוקת קבוצות")

tab = st.pills("תפריט", ["חלוקה", "מאגר"], default="חלוקה")

if tab == "חלוקה":
    all_names = [p['name'] for p in st.session_state.players]
    selected = st.pills("מי הגיע?", all_names, selection_mode="multi")
    
    if st.button("חלק קבוצות 🚀", use_container_width=True):
        pool = []
        for name in selected:
            pool.append({'name': name, 'f': get_stats(name)})
        pool.sort(key=lambda x: x['f'], reverse=True)
        st.session_state.t1, st.session_state.t2 = pool[0::2], pool[1::2]

    if st.session_state.t1 and selected:
        # כאן קורה הקסם - עמודות שלא נשברות
        c1, c2 = st.columns(2)
        
        for col, team, label, pfx in zip([c1, c2], [st.session_state.t1, st.session_state.t2], ["⚪ לבן", "⚫ שחור"], ["w", "b"]):
            with col:
                st.markdown(f"<p style='text-align:center;font-weight:bold;margin-bottom:5px;'>{label}</p>", unsafe_allow_html=True)
                for i, p in enumerate(team):
                    # שורת שחקן
                    st.markdown(f"""<div class='p-box'><span class='p-name'>{p['name']}</span><span class='p-score'>{p['f']:.1f}</span></div>""", unsafe_allow_html=True)
                    # כפתור החלפה מיד מתחת
                    if st.button("🔄", key=f"m_{pfx}_{i}"):
                        if pfx == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                        else: st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()

        # מאזן כוחות בטבלה קשיחה
        s1 = sum(p['f'] for p in st.session_state.t1)
        s2 = sum(p['f'] for p in st.session_state.t2)
        st.markdown(f"""
            <table class='balance-table'>
                <tr>
                    <td>לבן: <b>{s1:.1f}</b></td>
                    <td>שחור: <b>{s2:.1f}</b></td>
                </tr>
            </table>
        """, unsafe_allow_html=True)

        # וואטסאפ
        msg = f"⚽ קבוצות:\n\n⚪ לבן:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t1]) + f"\n\n⚫ שחור:\n" + "\n".join([f"• {p['name']}" for p in st.session_state.t2])
        st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg)}" style="display:block; text-align:center; background:#22c55e; color:white; padding:8px; border-radius:4px; text-decoration:none; margin-top:10px;">📲 שלח לוואטסאפ</a>', unsafe_allow_html=True)

else:
    st.write("ניהול מאגר שחקנים...")
    # כאן יבוא הקוד של המאגר אם תרצה, כרגע התמקדתי בתיקון החלוקה.
    
