import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. עיצוב CSS (נעילה מוחלטת) ---
st.set_page_config(page_title="כדורגל 2026", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; }
    .block-container { padding: 5px !important; max-width: 500px !important; }

    /* מכולה שחייבת להישאר ב-2 טורים */
    .mobile-grid {
        display: flex !important;
        flex-direction: row !important;
        width: 100% !important;
        gap: 5px !important;
    }
    .team-col {
        flex: 1 !important;
        min-width: 48% !important;
    }
    .t-header {
        text-align: center; font-weight: bold; padding: 10px;
        border-radius: 8px 8px 0 0; color: white; font-size: 16px;
    }
    .p-row {
        background: #2d3748; border: 1px solid #4a5568;
        border-radius: 5px; margin: 3px 0; padding: 8px;
        display: flex; justify-content: space-between; align-items: center;
        height: 50px;
    }
    .p-name { font-size: 15px; font-weight: bold; color: white; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .p-score { font-size: 12px; color: #22c55e; }
    
    /* עיצוב כפתור החלפה כקישור (Link) שנראה כמו כפתור */
    .swap-btn {
        background: #4a5568; color: white !important; text-decoration: none !important;
        width: 35px; height: 35px; display: flex; align-items: center; justify-content: center;
        border-radius: 4px; font-size: 18px; font-weight: bold;
    }
    .t-footer {
        background: #1e293b; text-align: center; padding: 8px;
        border-radius: 0 0 8px 8px; font-size: 13px; color: #60a5fa;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. לוגיקה ונתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)
if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except: st.session_state.players = []

# טיפול בהחלפת שחקנים דרך ה-URL (Query Params)
query_params = st.query_params
if "swap" in query_params and "from" in query_params:
    player_name = query_params["swap"]
    from_team = query_params["from"]
    
    if 't1' in st.session_state and 't2' in st.session_state:
        if from_team == "t1":
            p = next((x for x in st.session_state.t1 if x['name'] == player_name), None)
            if p:
                st.session_state.t1.remove(p)
                st.session_state.t2.append(p)
        else:
            p = next((x for x in st.session_state.t2 if x['name'] == player_name), None)
            if p:
                st.session_state.t2.remove(p)
                st.session_state.t1.append(p)
    
    st.query_params.clear()
    st.rerun()

def get_stats(name):
    p = next((x for x in st.session_state.players if x['name'] == name), None)
    if not p: return 5.0, 30
    r = float(p.get('rating', 5.0))
    return r, 2026 - int(p.get('birth_year', 1996))

# --- 3. ממשק ---
st.markdown("<h3 style='text-align:center;'>⚽ וולפסון חולון</h3>", unsafe_allow_html=True)

all_n = sorted([p['name'] for p in st.session_state.players])
selected = st.pills("מי משחק?", all_n, selection_mode="multi")

if st.button("חלק קבוצות 🚀", use_container_width=True):
    if selected:
        pool = [{'name': n, 'f': get_stats(n)[0], 'age': get_stats(n)[1]} for n in selected]
        pool.sort(key=lambda x: x['f'], reverse=True)
        t1, t2 = [], []
        for i, p in enumerate(pool):
            if i % 4 == 0 or i % 4 == 3: t1.append(p)
            else: t2.append(p)
        st.session_state.t1, st.session_state.t2 = t1, t2

if 't1' in st.session_state and selected:
    t1, t2 = st.session_state.t1, st.session_state.t2
    
    def render_team(team, title, color, team_key):
        avg = sum(p['f'] for p in team)/len(team) if team else 0
        rows_html = ""
        for p in team:
            # יצירת לינק להחלפה
            swap_url = f"?swap={p['name']}&from={team_key}"
            rows_html += f"""
            <div class="p-row">
                <div style="display:flex; flex-direction:column; overflow:hidden;">
                    <span class="p-name">{p['name']}</span>
                    <span class="p-score">{p['f']:.1f}</span>
                </div>
                <a href="{swap_url}" target="_self" class="swap-btn">🔄</a>
            </div>
            """
        return f"""
        <div class="team-col">
            <div class="t-header" style="background:{color};">{title}</div>
            {rows_html}
            <div class="t-footer">ממוצע: {avg:.1f}</div>
        </div>
        """

    # הזרקת ה-HTML של שתי העמודות במכה אחת
    full_grid_html = f"""
    <div class="mobile-grid">
        {render_team(t1, "⚪ לבן", "#3b82f6", "t1")}
        {render_team(t2, "⚫ שחור", "#4a5568", "t2")}
    </div>
    """
    st.markdown(full_grid_html, unsafe_allow_html=True)
