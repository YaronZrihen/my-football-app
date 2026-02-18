import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. נעילת מבנה CSS (מכריח 2 עמודות בכל מכשיר) ---
st.set_page_config(page_title="כדורגל וולפסון 2026", layout="centered")

st.markdown("""
    <style>
    /* הגדרות בסיס */
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    .block-container { padding: 10px !important; max-width: 500px !important; }
    
    /* כפיית 2 עמודות בסלולר - ללא שבירת שורה */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 8px !important;
    }
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 0 !important;
    }

    /* כרטיס שחקן בעיצוב נקי */
    .player-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 8px;
        display: flex;
        flex-direction: column;
        height: 70px;
        justify-content: center;
    }
    .p-name { font-size: 17px !important; font-weight: bold; color: white; display: block; }
    .p-stats { font-size: 12px !important; color: #22c55e; }

    /* עיצוב כפתור ההחלפה 🔄 */
    .stButton button {
        width: 100% !important;
        height: 70px !important;
        background-color: #334155 !important;
        color: white !important;
        border: none !important;
        font-size: 22px !important;
        border-radius: 8px !important;
    }
    
    .team-header {
        text-align: center; font-weight: bold; padding: 12px; 
        border-radius: 8px 8px 0 0; font-size: 18px; color: white;
    }
    .team-footer {
        background: #1e293b; text-align: center; padding: 8px;
        border-radius: 0 0 8px 8px; font-size: 13px; color: #60a5fa;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ולוגיקה ---
conn = st.connection("gsheets", type=GSheetsConnection)

if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except:
        st.session_state.players = []

def save_changes():
    df = pd.DataFrame(st.session_state.players)
    conn.update(data=df)
    st.cache_data.clear()

def get_player_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 30
    rating = float(p.get('rating', 5.0))
    age = 2026 - int(p.get('birth_year', 1996))
    return rating, age

# --- 3. בניית הממשק ---
st.title("⚽ וולפסון חולון")

tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון פרטים"])

# --- טאב 1: חלוקת קבוצות ---
with tab1:
    names_list = sorted([p['name'] for p in st.session_state.players])
    selected = st.pills("מי משחק?", names_list, selection_mode="multi")

    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected:
            pool = []
            for n in selected:
                r, a = get_player_stats(n)
                pool.append({'name': n, 'rating': r, 'age': a})
            
            pool.sort(key=lambda x: x['rating'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2

    if 't1' in st.session_state and selected:
        col_white, col_black = st.columns(2)
        
        # תצוגת קבוצה לבנה
        with col_white:
            st.markdown('<div class="team-header" style="background:#3b82f6;">⚪ לבן</div>', unsafe_allow_html=True)
            for i, p in enumerate(st.session_state.t1):
                c_txt, c_btn = st.columns([0.7, 0.3])
                with c_txt:
                    st.markdown(f"""<div class="player-card">
                        <span class="p-name">{p['name']}</span>
                        <span class="p-stats">רמה: {p['rating']:.1f} | {p['age']}</span>
                    </div>""", unsafe_allow_html=True)
                with c_btn:
                    if st.button("🔄", key=f"w_sw_{i}"):
                        st.session_state.t2.append(st.session_state.t1.pop(i))
                        st.rerun()
            avg1 = sum(p['rating'] for p in st.session_state.t1)/len(st.session_state.t1) if st.session_state.t1 else 0
            st.markdown(f'<div class="team-footer">ממוצע: {avg1:.1f}</div>', unsafe_allow_html=True)

        # תצוגת קבוצה שחורה
        with col_black:
            st.markdown('<div class="team-header" style="background:#4a5568;">⚫ שחור</div>', unsafe_allow_html=True)
            for i, p in enumerate(st.session_state.t2):
                c_txt, c_btn = st.columns([0.7, 0.3])
                with c_txt:
                    st.markdown(f"""<div class="player-card">
                        <span class="p-name">{p['name']}</span>
                        <span class="p-stats">רמה: {p['rating']:.1f} | {p['age']}</span>
                    </div>""", unsafe_allow_html=True)
                with c_btn:
                    if st.button("🔄", key=f"b_sw_{i}"):
                        st.session_state.t1.append(st.session_state.t2.pop(i))
                        st.rerun()
            avg2 = sum(p['rating'] for p in st.session_state.t2)/len(st.session_state.t2) if st.session_state.t2 else 0
            st.markdown(f'<div class="team-footer">ממוצע: {avg2:.1f}</div>', unsafe_allow_html=True)

# --- טאב 2: מאגר שחקנים ---
with tab2:
    st.subheader("רשימת כל השחקנים")
    for p in st.session_state.players:
        st.write(f"👤 **{p['name']}** - רמה: {p['rating']} | שנת לידה: {p['birth_year']}")
        st.write("---")

# --- טאב 3: עדכון פרטים ---
with tab3:
    st.subheader("הוספה או עדכון שחקן")
    with st.form("player_form"):
        name = st.text_input("שם השחקן")
        birth = st.number_input("שנת לידה", 1950, 2020, 1995)
        rating = st.slider("רמה (1-10)", 1.0, 10.0, 5.0)
        
        if st.form_submit_button("שמור שינויים"):
            # לוגיקה לעדכון או הוספה
            existing = next((p for p in st.session_state.players if p['name'] == name), None)
            if existing:
                existing['birth_year'] = birth
                existing['rating'] = rating
            else:
                st.session_state.players.append({'name': name, 'birth_year': birth, 'rating': rating})
            save_changes()
            st.success("הנתונים נשמרו בהצלחה!")
            st.rerun()
