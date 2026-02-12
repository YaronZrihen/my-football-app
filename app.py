import streamlit as st
import json
import os
import random
import urllib.parse

# --- 1. הגדרות דף ועיצוב RTL מקיף ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    /* יישור כללי לימין */
    .stApp, [data-testid="stSidebar"], .main {
        direction: rtl;
        text-align: right;
    }
    
    /* תיקון ספציפי לתיבות בחירה - Selectbox */
    div[data-testid="stSelectbox"] label {
        text-align: right !important;
        width: 100%;
    }
    div[data-baseweb="select"] {
        direction: rtl !important;
        text-align: right !important;
    }
    /* הזזת החץ של ה-Selectbox לשמאל */
    div[data-testid="stSelectbox"] svg {
        right: auto !important;
        left: 10px !important;
    }

    /* יישור כותרות וטקסטים */
    h1, h2, h3, h4, p, label, span {
        text-align: right !important;
        direction: rtl !important;
    }
    
    /* עיצוב כפתורים שיהיו נוחים בנייד */
    .stButton button {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות נתונים ---
def load_data():
    if os.path.exists('players.json'):
        with open('players.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(players):
    with open('players.json', 'w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False, indent=4)

if 'players' not in st.session_state:
    st.session_state.players = load_data()

# --- 3. תפריט צד (Sidebar) ---
ADMIN_PASSWORD = "1234"

with st.sidebar:
    st.title("⚽ תפריט")
    access_mode = st.radio("מצב גישה:", ["שחקן (מילוי פרטים)", "מנהל (Admin)"])
    
    menu = "מילוי פרטים" 
    if access_mode == "מנהל (Admin)":
        pwd = st.text_input("סיסמה:", type="password")
        if pwd == ADMIN_PASSWORD:
            st.success("גישת מנהל מאושרת")
            menu = st.selectbox("בחר פעולה:", ["ניהול מאגר שחקנים", "חלוקת קבוצות"])
        else:
            if pwd: st.error("סיסמה שגויה")

# --- 4. דף שחקן: מילוי ודירוג ---
if menu == "מילוי פרטים":
    st.title("📝 עדכון פרטים ודירוג")
    
    # הכנת רשימה ממוינת א-ב
    player_names = sorted([p['name'] for p in st.session_state.players])
    name_options = ["--- בחר שם מהרשימה ---", "🆕 שחקן חדש (לא במאגר)"] + player_names
    
    selected_name = st.selectbox("מי אתה?", options=name_options)
    
    final_name = ""
    curr_p_data = None
    
    if selected_name == "🆕 שחקן חדש (לא במאגר)":
        final_name = st.text_input("הקלד את שמך המלא:")
    elif selected_name != "--- בחר שם מהרשימה ---":
        final_name = selected_name
        curr_p_data = next((p for p in st.session_state.players if p['name'] == final_name), None)

    if final_name:
        with st.form("player_form"):
            st.subheader(f"עריכת פרופיל: {final_name}")
            
            b_year = st.number_input("שנת לידה:", 1950, 2026, curr_p_data.get('birth_year', 1995) if curr_p_data else 1995)
            
            roles = ["שוער", "בלם", "מגן ימני", "מגן שמאלי", "קשר", "כנף", "חלוץ"]
            def_roles = curr_p_data.get('pos', "").split(", ") if curr_p_data else []
            selected_pos = st.pills("תפקידים:", options=roles, selection_mode="multi", default=def_roles)
            
            def_rate = float(curr_p_data.get('rating', 5.0)) if curr_p_data else 5.0
            rate = st.slider("דרג את היכולת שלך (1-10):", 1.0, 10.0, def_rate)
            
            st.divider()
            st.write("**⭐ דרג חברים מהקבוצה (עוזר לאיזון):**")
            
            peer_ratings = curr_p_data.get('peer_ratings', {}) if curr_p_data else {}
            for p in st.session_state.players:
                if p['name'] != final_name:
                    p_val = peer_ratings.get(p['name'], 5)
                    peer_ratings[p['name']] = st.select_slider(
                        f"איך הרמה של {p['name']}?", options=list(range(1, 11)),
                        value=int(p_val), key=f"p_rate_{p['name']}"
                    )

            if st.form_submit_button("שמור ועדכן", use_container_width=True):
                if final_name and selected_pos:
                    new_entry = {
                        "name": final_name, "birth_year": b_year, 
                        "pos": ", ".join(selected_pos), "rating": rate, 
                        "peer_ratings": peer_ratings
                    }
                    idx = next((i for i, p in enumerate(st.session_state.players) if p['name'] == final_name), None)
                    if idx is not None:
                        st.session_state.players[idx] = new_entry
                    else:
                        st.session_state.players.append(new_entry)
                    
                    save_data(st.session_state.players)
                    st.success("הנתונים נשמרו!")
                    st.balloons()
                else:
                    st.error("חובה למלא שם ולבחור תפקיד")

# --- 5. ניהול מאגר (Admin) ---
elif menu == "ניהול מאגר שחקנים":
    st.title("👤 ניהול מאגר השחקנים")
    
    # חישוב ציונים קבוצתיים
    all_received = {p['name']: [] for p in st.session_state.players}
    for p in st.session_state.players:
        for target, score in p.get('peer_ratings', {}).items():
            if target in all_received: all_received[target].append(score)

    st.write(f"סה\"כ שחקנים: **{len(st.session_state.players)}**")
    
    # כותרות הטבלה
    st.divider()
    h = st.columns([2.5, 1, 1, 1, 0.5, 0.5])
    h[0].markdown("**גיל ושם**")
    h[1].markdown("**אישי**")
    h[2].markdown("**קבוצתי**")
    h[3].markdown("**סופי**")
    st.divider()

    for i, p in enumerate(st.session_state.players):
        age = 2026 - p.get('birth_year', 1995)
        p_rate = p.get('rating', 0.0)
        received_list = all_received.get(p['name'], [])
        t_rate = sum(received_list)/len(received_list) if received_list else 0.0
        final_s = (p_rate + t_rate)/2 if t_rate > 0 else p_rate
        
        c = st.columns([2.5, 1, 1, 1, 0.5, 0.5])
        # גיל, שם ותפקיד מתחת
        c[0].markdown(f"({age}) **{p['name']}**<br><small style='color:gray;'>🏃 {p['pos']}</small>", unsafe_allow_html=True)
        c[1].write(f"{p_rate:.1f}")
        c[2].write(f"{t_rate:.1f} ({len(received_list)})" if received_list else "---")
        c[3].write(f"**{final_s:.1f}**")
        
        if c[4].toggle("📝", key=f"edit_tgl_{i}"):
            with st.form(f"admin_edit_{i}"):
                u_name = st.text_input("שם:", p['name'])
                u_year = st.number_input("שנה:", 1950, 2026, p['birth_year'])
                u_pos = st.text_input("תפקידים:", p['pos'])
                u_rate = st.slider("דירוג:", 1.0, 10.0, float(p_rate))
                if st.form_submit_button("עדכן"):
                    st.session_state.players[i].update({"name": u_name, "birth_year": u_year, "pos": u_pos, "rating": u_rate})
                    save_data(st.session_state.players)
                    st.rerun()
        
        if c[5].button("🗑️", key=f"del_btn_{i}"):
            st.session_state.players.pop(i)
            save_data(st.session_state.players)
            st.rerun()
        st.divider()

# --- 6. חלוקת קבוצות לבן/שחור ---
elif menu == "חלוקת קבוצות":
    st.title("📋 חלוקה לבן/שחור")
    
    # חישוב נתונים לחלוקה
    all_received = {p['name']: [] for p in st.session_state.players}
    for p in st.session_state.players:
        for target, score in p.get('peer_ratings', {}).items():
            if target in all_received: all_received[target].append(score)
            
    processed = []
    for p in st.session_state.players:
        r_list = all_received.get(p['name'], [])
        t_rate = sum(r_list)/len(r_list) if r_list else 0.0
        f_score = (p['rating'] + t_rate)/2 if t_rate > 0 else p['rating']
        processed.append({**p, "f_score": f_score, "age": 2026 - p['birth_year']})

    p_names = [p['name'] for p in processed]
    selected = st.pills("בחר שחקנים שהגיעו:", options=p_names, selection_mode="multi")

    if st.button("בצע חלוקה אופטימלית 🚀", use_container_width=True):
        if len(selected) < 2:
            st.error("בחר לפחות 2 שחקנים")
        else:
            available = [p for p in processed if p['name'] in selected]
            best_diff = 100
            for _ in range(1000):
                random.shuffle(available)
                mid = len(available)//2
                t1, t2 = available[:mid], available[mid:]
                s1 = sum(x['f_score'] for x in t1)/len(t1)
                s2 = sum(x['f_score'] for x in t2)/len(t2)
                if abs(s1-s2) < best_diff:
                    best_diff = abs(s1-s2)
                    st.session_state.team_a, st.session_state.team_b = t1, t2
            st.session_state.show_results = True

    if st.session_state.get('show_results'):
        st.divider()
        res_c1, res_c2 = st.columns(2)
        teams_data = [(st.session_state.team_a, "⚪ לבן", res_c1, "team_a", "team_b"), 
                      (st.session_state.team_b, "⚫ שחור", res_c2, "team_b", "team_a")]
        
        for t_list, label, col, cur_key, other_key in teams_data:
            with col:
                st.subheader(label)
                for p in t_list:
                    with st.container(border=True):
                        st.markdown(f"**{p['name']}**")
                        st.markdown(f"<small>🎂 גיל: {p['age']} | ⭐ ציון: {p['f_score']:.1f}</small>", unsafe_allow_html=True)
                        st.markdown(f"<small>🏃 {p['pos']}</small>", unsafe_allow_html=True)
                        if st.button("⇄", key=f"swap_{p['name']}"):
                            p_obj = next(x for x in st.session_state[cur_key] if x['name'] == p['name'])
                            st.session_state[cur_key] = [x for x in st.session_state[cur_key] if x['name'] != p['name']]
                            st.session_state[other_key].append(p_obj)
                            st.rerun()
                if t_list:
                    avg_v = sum(x['f_score'] for x in t_list)/len(t_list)
                    st.metric("רייטינג ממוצע", f"{avg_v:.2f}")

        if st.button("📱 שלח חלוקה לוואטסאפ", use_container_width=True):
            msg = "⚽ *חלוקת קבוצות:*\n\n⚪ *לבן:*\n" + "\n".join([f"- {p['name']}" for p in st.session_state.team_a])
            msg += "\n\n⚫ *שחור:*\n" + "\n".join([f"- {p['name']}" for p in st.session_state.team_b])
            st.markdown(f'[לחץ כאן לשליחה בוואטסאפ](https://wa.me/?text={urllib.parse.quote(msg)})')