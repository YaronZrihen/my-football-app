import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime, date

# --- 1. הגדרות ועיצוב ---
st.set_page_config(page_title="ניהול כדורגל וולפסון", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span, div { text-align: right !important; direction: rtl; }
    .wolfson-title { font-size: 32px !important; text-align: center !important; color: #60a5fa; font-weight: bold; margin-bottom: 20px; }
    .card { background: #2d3748; border: 1px solid #4a5568; border-radius: 12px; padding: 15px; margin-bottom: 15px; }
    .arrival-row { display: flex; justify-content: space-between; align-items: center; background: #1e293b; padding: 10px 20px; border-radius: 8px; margin-bottom: 8px; border-right: 5px solid #3b82f6; }
    .team-box { background: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #4a5568; min-height: 200px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try:
        df = conn.read(worksheet=name, ttl="0")
        return df.dropna(subset=['name']) if not df.empty else pd.DataFrame(columns=['name'])
    except:
        return pd.DataFrame(columns=['name'])

# טעינת מאגר השחקנים הקבוע
if 'players' not in st.session_state:
    df_db = load_sheet("Football_DB")
    st.session_state.players = df_db.to_dict(orient='records')

# --- 3. פונקציות חישוב ודירוג ---
def safe_get_json(val):
    if not val or pd.isna(val): return {}
    try: return json.loads(str(val).replace("'", '"'))
    except: return {}

def get_full_stats(p):
    name = p['name']
    age = 2026 - int(p.get('birth_year', 1990))
    self_r = float(p.get('rating', 0))
    
    # חישוב ממוצע דירוג עמיתים
    peer_scores = []
    for voter in st.session_state.players:
        ratings = safe_get_json(voter.get('peer_ratings', '{}'))
        if name in ratings and float(ratings[name]) > 0:
            peer_scores.append(float(ratings[name]))
    
    avg_peer = sum(peer_scores)/len(peer_scores) if peer_scores else 0
    
    # שקלול סופי: ממוצע של עצמי ושל חברים
    if self_r > 0 and avg_peer > 0: final = (self_r + avg_peer) / 2
    else: final = self_r or avg_peer or 5.0
    
    return {"final": round(final, 1), "age": age, "peer_avg": round(avg_peer, 1), "peer_count": len(peer_scores)}

# --- 4. ממשק טאבים ---
st.markdown("<div class='wolfson-title'>⚽ וולפסון חולון - מערכת ניהול משולבת</div>", unsafe_allow_html=True)
tab_reg, tab_teams, tab_pay, tab_edit = st.tabs(["📝 רישום למשחק", "🏃 חלוקה", "💰 תשלומים וקופה", "⚙️ ניהול מאגר"])

# --- טאב 1: רישום (כולל מזדמנים ומחיקה) ---
with tab_reg:
    m_date = st.date_input("בחר תאריך מחזור:", value=date.today())
    m_date_str = m_date.strftime("%d/%m/%Y")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("רישום חבר קבוע")
        with st.form("reg_member"):
            names = sorted([p['name'] for p in st.session_state.players])
            u_name = st.selectbox("שם השחקן:", [""] + names)
            if st.form_submit_button("אשר הגעה"):
                if u_name:
                    h_df = load_sheet("arrivals_history")
                    if not ((h_df['name'] == u_name) & (h_df['match_date'] == m_date_str)).any():
                        new_row = pd.DataFrame([{"name": u_name, "match_date": m_date_str, "type": "חבר"}])
                        conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new_row], ignore_index=True))
                        st.success("נרשם!")
                        st.cache_data.clear()

    with col2:
        st.subheader("רישום שחקן מזדמן")
        with st.form("reg_guest"):
            g_name = st.text_input("שם האורח:")
            g_rate = st.slider("רמה (1-10):", 1, 10, 5)
            if st.form_submit_button("הוסף אורח ⭐"):
                if g_name:
                    h_df = load_sheet("arrivals_history")
                    new_row = pd.DataFrame([{"name": f"⭐ {g_name}", "match_date": m_date_str, "type": "אורח", "temp_rating": g_rate}])
                    conn.update(worksheet="arrivals_history", data=pd.concat([h_df, new_row], ignore_index=True))
                    st.success("אורח נוסף!")
                    st.cache_data.clear()

    st.write("---")
    st.subheader(f"רשימת מתייצבים - {m_date_str}")
    h_df = load_sheet("arrivals_history")
    daily = h_df[h_df['match_date'] == m_date_str]
    
    for idx, row in daily.iterrows():
        c_info, c_del = st.columns([5, 1])
        c_info.markdown(f"<div class='arrival-row'>{row['name']} <small>({row['type']})</small></div>", unsafe_allow_html=True)
        if c_del.button("❌", key=f"del_{idx}"):
            full_h = load_sheet("arrivals_history")
            full_h = full_h.drop(idx)
            conn.update(worksheet="arrivals_history", data=full_h)
            st.cache_data.clear()
            st.rerun()

# --- טאב 2: חלוקת קבוצות ---
with tab_teams:
    st.subheader(f"חלוקה למחזור {m_date_str}")
    if daily.empty:
        st.warning("אין שחקנים רשומים לתאריך זה.")
    else:
        playing = st.multiselect("שחקנים משתתפים בפועל:", daily['name'].tolist(), default=daily['name'].tolist())
        if st.button("חלק קבוצות 🚀", use_container_width=True):
            pool = []
            for n in playing:
                if n.startswith("⭐"):
                    r = daily[daily['name'] == n].iloc[0]
                    pool.append({'name': n, 'f': float(r.get('temp_rating', 5)), 'age': 30})
                else:
                    p = next(x for x in st.session_state.players if x['name'] == n)
                    s = get_full_stats(p)
                    pool.append({'name': n, 'f': s['final'], 'age': s['age']})
            
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            
            col_a, col_b = st.columns(2)
            for col, team, label in zip([col_a, col_b], [t1, t2], ["⚪ לבן", "⚫ שחור"]):
                with col:
                    st.markdown(f"### {label} ({len(team)})")
                    for p in team:
                        st.markdown(f"<div class='arrival-row'>{p['name']} <b>({p['f']})</b></div>", unsafe_allow_html=True)

# --- טאב 3: תשלומים (גליון נפרד) ---
with tab_pay:
    st.subheader("ניהול קופה")
    pay_df = load_sheet("payments_ledger")
    
    with st.form("pay_form"):
        p_name = st.selectbox("מי שילם?", [""] + daily['name'].tolist())
        p_amount = st.number_input("סכום:", value=50)
        p_method = st.selectbox("אמצעי תשלום:", ["ביט", "מזומן", "העברה"])
        if st.form_submit_button("תעד תשלום"):
            if p_name:
                new_p = pd.DataFrame([{"name": p_name, "amount": p_amount, "date": m_date_str, "method": p_method, "timestamp": datetime.now().strftime("%H:%M")}])
                conn.update(worksheet="payments_ledger", data=pd.concat([pay_df, new_p], ignore_index=True))
                st.success("תשלום נרשם!")
                st.cache_data.clear()

    st.write("### היסטוריית גבייה")
    st.dataframe(pay_df.sort_values(by="date", ascending=False), use_container_width=True)

# --- טאב 4: ניהול המאגר ודירוג עמיתים ---
with tab_edit:
    st.subheader("הוספה ועריכת שחקנים קבועים (Football_DB)")
    all_names = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    choice = st.selectbox("בחר שחקן לעריכה:", all_names)
    p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
    
    with st.form("edit_db_form"):
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "").strip()
        f_year = st.number_input("שנת לידה:", 1900, 2026, int(p_data['birth_year']) if p_data else 1990)
        f_rate = st.radio("ציון עצמי:", list(range(1,11)), index=int(p_data.get('rating',5))-1, horizontal=True)
        
        st.write("---")
        st.subheader("דירוג עמיתים (דרג את החברים):")
        peer_results = {}
        others = [p for p in st.session_state.players if p['name'] != (f_name or choice)]
        for idx, op in enumerate(others):
            curr_v = safe_get_json(p_data.get('peer_ratings', '{}') if p_data else '{}').get(op['name'], 0)
            peer_results[op['name']] = st.radio(f"דרג את {op['name']}:", [0]+list(range(1,11)), index=int(curr_v), horizontal=True, key=f"edit_peer_{idx}")

        if st.form_submit_button("שמור שינויים במאגר ✅"):
            if f_name:
                new_entry = {
                    "name": f_name, "birth_year": f_year, "rating": f_rate,
                    "peer_ratings": json.dumps({k: v for k, v in peer_results.items() if v > 0})
                }
                df_db = load_sheet("Football_DB")
                if p_data:
                    df_db.loc[df_db['name'] == choice, ['birth_year', 'rating', 'peer_ratings']] = [f_year, f_rate, new_entry['peer_ratings']]
                else:
                    df_db = pd.concat([df_db, pd.DataFrame([new_entry])], ignore_index=True)
                
                conn.update(worksheet="Football_DB", data=df_db)
                st.success("המאגר עודכן!")
                st.cache_data.clear()
                st.rerun()

    st.write("### המאגר הנוכחי")
    st.dataframe(pd.DataFrame([ {**p, **get_full_stats(p)} for p in st.session_state.players ])[['name', 'age', 'final', 'peer_avg', 'peer_count']])
