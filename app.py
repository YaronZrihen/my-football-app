import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime

# --- 1. עיצוב CSS ונעילת הגדרות אתר ---
st.set_page_config(page_title="ניהול כדורגל וולפסון חולון", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span, div { text-align: right !important; direction: rtl; }
    .block-container { padding-top: 50px !important; }
    .wolfson-title { font-size: 28px !important; text-align: center !important; color: #60a5fa; font-weight: bold; margin-bottom: 30px; }
    .player-card { background: #2d3748; border: 1px solid #4a5568; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .card-header { font-size: 20px; font-weight: bold; color: #f8fafc; border-bottom: 1px solid #4a5568; padding-bottom: 8px; margin-bottom: 10px; }
    .card-row { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 14px; }
    .label { color: #94a3b8; }
    .value { color: #e2e8f0; font-weight: 500; }
    .highlight-value { color: #22c55e; font-weight: bold; }
    .roles-tag { background: #4a5568; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    .date-footer { font-size: 11px; color: #64748b; margin-top: 10px; border-top: 1px dotted #4a5568; padding-top: 5px; }
    .p-box { background: #2d3748; border: 1px solid #4a5568; border-radius: 4px; padding: 2px 8px; margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center; min-height: 35px; }
    .team-stats { background: #1e293b; border-top: 2px solid #4a5568; padding: 10px; margin-top: 10px; font-size: 14px; text-align: center; border-radius: 0 0 8px 8px; color: #e2e8f0; line-height: 1.5; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר ---
def safe_split(val):
    if not val or pd.isna(val): return []
    return [s.strip() for s in str(val).split(',') if s.strip()]

def safe_get_json(val):
    if not val or pd.isna(val): return {}
    if isinstance(val, dict): return val
    try:
        cleaned = str(val).strip()
        if cleaned.startswith("'") and cleaned.endswith("'"): cleaned = cleaned[1:-1]
        return json.loads(cleaned) if cleaned else {}
    except: return {}

conn = st.connection("gsheets", type=GSheetsConnection)

if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except:
        st.session_state.players = []

def save_to_gsheets():
    if not st.session_state.players or len(st.session_state.players) == 0:
        st.error("⚠️ המאגר ריק. השמירה בוטלה.")
        return
    try:
        df = pd.DataFrame(st.session_state.players)
        conn.update(data=df)
        st.cache_data.clear()
        st.toast("נשמר בהצלחה! ✅")
    except Exception as e:
        st.error(f"שגיאה בשמירה: {e}")

def get_player_full_stats(p):
    name = p['name']
    birth_year = int(p.get('birth_year', 1900))
    age = 2026 - birth_year
    self_rating = float(p.get('rating', 0))
    peer_scores = []
    for voter in st.session_state.players:
        if voter['name'] == name: continue
        voter_ratings = safe_get_json(voter.get('peer_ratings', '{}'))
        if name in voter_ratings and voter_ratings[name] > 0:
            peer_scores.append(float(voter_ratings[name]))
    count = len(peer_scores)
    avg_peer = sum(peer_scores) / count if count > 0 else 0
    if self_rating > 0 and count > 0: final_score = (self_rating + avg_peer) / 2
    elif self_rating > 0: final_score = self_rating
    elif count > 0: final_score = avg_peer
    else: final_score = 5.0
    return {"final": round(final_score, 1), "self": self_rating if self_rating > 0 else "ללא", "peer": round(avg_peer, 1) if avg_peer > 0 else "ללא", "age": age, "count": count}

# --- 3. ממשק משתמש ---
st.markdown("<div class='wolfson-title'>ניהול קבוצת כדורגל וולפסון חולון</div>", unsafe_allow_html=True)

if 'edit_name' not in st.session_state: st.session_state.edit_name = "🆕 שחקן חדש"
tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון/הרשמה"])

# --- 4. טאב חלוקה ---
with tab1:
    all_names = sorted([p['name'] for p in st.session_state.players])
    selected_names = st.pills("מי הגיע?", all_names, selection_mode="multi", key="p_selection")
    if st.button("חלק קבוצות 🚀", use_container_width=True):
        if selected_names:
            pool = []
            for n in selected_names:
                p = next(x for x in st.session_state.players if x['name'] == n)
                stats = get_player_full_stats(p)
                pool.append({'name': n, 'f': stats['final'], 'age': stats['age'], 'raters': stats['count']})
            pool.sort(key=lambda x: x['f'], reverse=True)
            t1, t2 = [], []
            for i, p in enumerate(pool):
                if i % 4 == 0 or i % 4 == 3: t1.append(p)
                else: t2.append(p)
            st.session_state.t1, st.session_state.t2 = t1, t2
    if 't1' in st.session_state and selected_names:
        col_w, col_b = st.columns(2)
        teams_data = [{"team": st.session_state.t1, "label": "⚪ לבן", "pfx": "w"}, {"team": st.session_state.t2, "label": "⚫ שחור", "pfx": "b"}]
        for col, data in zip([col_w, col_b], teams_data):
            with col:
                st.markdown(f"<p style='text-align:center; font-weight:bold;'>{data['label']}</p>", unsafe_allow_html=True)
                for i, p in enumerate(data['team']):
                    c_txt, c_swp = st.columns([3, 1])
                    with c_txt: st.markdown(f"<div class='p-box'><span>{p['name']} ({p['age']})</span><span><b>{p['f']:.1f}</b></span></div>", unsafe_allow_html=True)
                    with c_swp:
                        if st.button("🔄", key=f"sw_{data['pfx']}_{i}"):
                            if data['pfx'] == "w": st.session_state.t2.append(st.session_state.t1.pop(i))
                            else: st.session_state.t1.append(st.session_state.t2.pop(i))
                            st.rerun()
                if data['team']:
                    avg_f, avg_a = sum(p['f'] for p in data['team'])/len(data['team']), sum(p['age'] for p in data['team'])/len(data['team'])
                    st.markdown(f"<div class='team-stats'><b style='color:#60a5fa;'>רמה: {avg_f:.1f}</b><br>גיל: {avg_a:.1f}</div>", unsafe_allow_html=True)

# --- 5. טאב מאגר ---
with tab2:
    for i, p in enumerate(st.session_state.players):
        s = get_player_full_stats(p)
        roles = safe_split(p.get('roles', ''))
        st.markdown(f"""<div class='player-card'><div class='card-header'>{p['name']}</div><div class='card-row'><span class='label'>גיל:</span><span class='value'>{s['age']}</span></div><div class='card-row'><span class='label'>תפקידים:</span><span class='value'>{' '.join([f"<span class='roles-tag'>{r}</span>" for r in roles])}</span></div><div class='card-row'><span class='label'>ציון אישי:</span><span class='value'>{s['self']}</span></div><div class='card-row'><span class='label'>ציון קבוצתי:</span><span class='value'>{s['peer']} ({s['count']})</span></div><div class='card-row'><span class='label'>סופי:</span><span class='highlight-value'>{s['final']}</span></div><div class='date-footer'>רישום: {p.get('created_at','-')} | עדכון: {p.get('updated_at','-')}</div></div>""", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            if st.button("📝 עריכה", key=f"edit_{i}", use_container_width=True): st.session_state.edit_name = p['name']; st.rerun()
        with c3:
            if st.button("🗑️", key=f"del_{i}", use_container_width=True): st.session_state.players.pop(i); save_to_gsheets(); st.rerun()
        st.write("---")

# --- 6. טאב עדכון/הרשמה (כולל חסימת כפילויות) ---
with tab3:
    all_n = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    choice = st.selectbox("בחר שחקן:", all_n, index=all_n.index(st.session_state.edit_name) if st.session_state.edit_name in all_n else 0)
    p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
    
    with st.form("edit_form"):
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "").strip()
        f_year = st.number_input("שנת לידה:", 1900, 2026, int(p_data['birth_year']) if p_data and 'birth_year' in p_data else 1900)
        roles_options = ["שוער", "בלם", "מגן", "קשר", "כנף", "חלוץ"]
        valid_default = [r for r in safe_split(p_data.get('roles', '')) if r in roles_options] if p_data else []
        f_roles = st.pills("תפקידים:", roles_options, selection_mode="multi", default=valid_default)
        f_rate = st.radio("ציון עצמי:", [0]+list(range(1,11)), index=int(p_data.get('rating',0)) if p_data else 0, format_func=lambda x: "ללא" if x==0 else str(x), horizontal=True)
        
        st.write("---")
        st.write("דירוג עמיתים:")
        peer_res = {}
        other_p = [p for p in st.session_state.players if p['name'] != (f_name or choice)]
        for idx, op in enumerate(other_p):
            val = int(safe_get_json(p_data.get('peer_ratings', '{}') if p_data else '{}').get(op['name'], 0))
            peer_res[op['name']] = st.radio(f"דרג את {op['name']}:", [0]+list(range(1,11)), index=val if val <=10 else 0, format_func=lambda x: "ללא" if x==0 else str(x), horizontal=True, key=f"r_{choice}_{idx}")
        
        if st.form_submit_button("שמור שינויים ✅", use_container_width=True):
            if not f_name:
                st.error("חובה להזין שם שחקן!")
            else:
                # --- בדיקת כפילויות ---
                existing_names = [p['name'] for p in st.session_state.players if p['name'] != (p_data['name'] if p_data else None)]
                
                if f_name in existing_names:
                    st.error(f"שגיאה: השם '{f_name}' כבר קיים במאגר. אנא השתמש בשם אחר או הוסף שם משפחה.")
                else:
                    now = datetime.now().strftime("%d/%m/%Y %H:%M")
                    new_entry = {
                        "name": f_name, "birth_year": f_year, "rating": f_rate, 
                        "roles": ",".join(f_roles), "updated_at": now,
                        "peer_ratings": json.dumps({k: v for k, v in peer_res.items() if v > 0})
                    }
                    if p_data:
                        new_entry["created_at"] = p_data.get('created_at', now)
                        st.session_state.players[next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)] = new_entry
                    else:
                        new_entry["created_at"] = now
                        st.session_state.players.append(new_entry)
                    save_to_gsheets()
                    st.session_state.edit_name = f_name
                    st.rerun()

for _ in range(5): st.write("")
