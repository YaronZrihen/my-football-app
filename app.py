import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- 1. הגדרות ועיצוב CSS ---
st.set_page_config(page_title="ניהול כדורגל", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #1a1c23; color: #e2e8f0; direction: rtl; text-align: right; }
    h1, h2, h3, p, label, span { text-align: right !important; direction: rtl; }
    .block-container { padding: 5px !important; }
    .main-title { font-size: 18px !important; text-align: center !important; font-weight: bold; margin-bottom: 10px; color: #60a5fa; }
    
    .database-card {
        background: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 5px;
        text-align: right;
    }
    .card-title { font-size: 16px; font-weight: bold; color: #60a5fa; margin-bottom: 2px; }
    .card-detail { font-size: 13px; color: #cbd5e0; margin-bottom: 2px; }

    div[data-testid="column"] button {
        width: 100% !important;
        padding: 4px !important;
        height: 35px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. נתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

if 'players' not in st.session_state:
    try:
        df = conn.read(ttl="0")
        st.session_state.players = df.dropna(subset=['name']).to_dict(orient='records')
    except:
        st.session_state.players = []

def save_data():
    df = pd.DataFrame(st.session_state.players)
    conn.update(data=df)
    st.cache_data.clear()

# --- 3. ניהול ניווט (הפתרון לשגיאה) ---
# אתחול משתנים ב-session_state במידה ולא קיימים
if 'current_page' not in st.session_state:
    st.session_state.current_page = "חלוקה"
if 'player_to_edit' not in st.session_state:
    st.session_state.player_to_edit = "🆕 שחקן חדש"

st.markdown("<div class='main-title'>⚽ ניהול כדורגל</div>", unsafe_allow_html=True)

# תפריט Pills ללא KEY סטטי (כדי למנוע את השגיאה)
menu_options = ["חלוקה", "מאגר שחקנים", "עדכון/הרשמה"]

# מציאת האינדקס הנוכחי של העמוד
try:
    def_idx = menu_options.index(st.session_state.current_page)
except:
    def_idx = 0

# יצירת ה-Pills. הערך שלו תמיד נשמר ב-current_page
menu = st.pills("תפריט", menu_options, index=def_idx)

# אם המשתמש לחץ ידנית על התפריט, נעדכן את ה-state
if menu and menu != st.session_state.current_page:
    st.session_state.current_page = menu
    st.rerun()

# --- 4. דף חלוקה ---
if st.session_state.current_page == "חלוקה":
    all_names = sorted([p['name'] for p in st.session_state.players])
    st.pills(f"מי הגיע? ({len(st.session_state.get('p_sel', []))})", all_names, selection_mode="multi", key="p_sel")
    st.info("כאן מופיעה מערכת החלוקה שביקשת...")

# --- 5. דף מאגר שחקנים ---
elif st.session_state.current_page == "מאגר שחקנים":
    st.subheader("🗄️ ניהול שחקנים")
    for i, p in enumerate(st.session_state.players):
        st.markdown(f"""
            <div class='database-card'>
                <div class='card-title'>{p['name']}</div>
                <div class='card-detail'>גיל: {2026 - int(p['birth_year'])}</div>
                <div class='card-detail'>תפקידים: {p.get('roles', '')}</div>
            </div>
        """, unsafe_allow_html=True)
        
        col_edit, col_del = st.columns([4, 1])
        with col_edit:
            # כאן קורה הניווט המתוקן!
            if st.button(f"📝 עריכה", key=f"ed_{i}"):
                st.session_state.player_to_edit = p['name'] # מעדכנים מי השחקן
                st.session_state.current_page = "עדכון/הרשמה" # מעדכנים לאן ללכת
                st.rerun() # מריצים מחדש - וה-Pills יתעדכן לפי ה-index
        with col_del:
            if st.button("🗑️", key=f"dl_{i}"):
                st.session_state.players.pop(i)
                save_data()
                st.rerun()
        st.markdown("---")

# --- 6. דף עדכון/הרשמה ---
elif st.session_state.current_page == "עדכון/הרשמה":
    st.subheader("📝 עדכון פרטים")
    names = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    
    # בחירת השחקן (אם הגענו מעריכה, הוא יהיה פה)
    target = st.session_state.player_to_edit
    if target not in names: target = "🆕 שחקן חדש"
    
    choice = st.selectbox("בחר שחקן:", names, index=names.index(target))
    
    with st.form("edit_form"):
        p_data = next((p for p in st.session_state.players if p['name'] == choice), None)
        f_name = st.text_input("שם מלא:", value=p_data['name'] if p_data else "")
        f_year = st.number_input("שנת לידה:", 1950, 2026, int(p_data['birth_year']) if p_data else 1995)
        
        roles_list = ["שוער", "בלם", "מגן", "קשר אחורי", "קשר קדמי", "כנף", "חלוץ"]
        curr_r = p_data.get('roles', "") if p_data else ""
        curr_r_list = curr_r.split(',') if curr_r else []
        f_roles = st.pills("תפקידים:", roles_list, selection_mode="multi", default=curr_r_list)
        
        f_rate = st.radio("ציון (1-10):", range(1, 11), index=int(p_data.get('rating', 5))-1, horizontal=True)
        
        if st.form_submit_button("שמור ✅"):
            if f_name:
                new_p = {"name": f_name, "birth_year": f_year, "rating": f_rate, "roles": ",".join(f_roles)}
                if p_data:
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == choice)
                    st.session_state.players[idx] = new_p
                else:
                    st.session_state.players.append(new_p)
                save_data()
                st.session_state.player_to_edit = f_name
                st.success("נשמר!")
                st.rerun()

# איפוס המשתנה כשעוזבים את דף העריכה ידנית כדי לא "להיתקע" על שחקן
if st.session_state.current_page != "עדכון/הרשמה":
    st.session_state.player_to_edit = "🆕 שחקן חדש"
