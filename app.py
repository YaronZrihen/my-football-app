import streamlit as st
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components
import pandas as pd
import json

# ============================================================
# 1. הגדרות עמוד ו-CSS
# ============================================================
st.set_page_config(page_title="ניהול כדורגל 2026", layout="centered")

st.markdown("""
<style>
/* ===== בסיס ===== */
.stApp {
    background-color: #0f1117;
    color: #e2e8f0;
    direction: rtl;
    text-align: right;
}
h1, h2, h3, p, label, span, div {
    text-align: right !important;
    direction: rtl;
}
.block-container { padding: 12px !important; max-width: 700px; margin: auto; }

/* ===== כותרת ===== */
.main-title {
    font-size: 26px;
    text-align: center !important;
    font-weight: bold;
    margin-bottom: 18px;
    color: #60a5fa;
    letter-spacing: 1px;
}

/* ===== כרטיס שחקן במאגר ===== */
.database-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.card-name { font-size: 16px; font-weight: bold; color: #f1f5f9; }
.card-detail { font-size: 13px; color: #94a3b8; margin-top: 3px; }

/* ===== שחקן בחלוקה ===== */
.p-box {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    min-height: 38px;
    font-size: 14px;
}
.p-score { color: #22c55e; font-size: 12px; font-weight: bold; }

/* ===== סטטיסטיקות קבוצה ===== */
.team-stats {
    background: #0f172a;
    border-top: 2px solid #334155;
    padding: 8px;
    margin-top: 6px;
    font-size: 12px;
    text-align: center;
    border-radius: 0 0 10px 10px;
}
.team-header {
    background: #1e3a5f;
    border-radius: 8px 8px 0 0;
    padding: 8px;
    text-align: center;
    font-weight: bold;
    font-size: 15px;
}

/* ===== Pills ===== */
div[data-testid="stPills"] button {
    background-color: #334155 !important;
    color: #cbd5e1 !important;
    border-radius: 20px !important;
    font-size: 13px !important;
}
div[data-testid="stPills"] button[aria-checked="true"] {
    background-color: #3b82f6 !important;
    color: white !important;
    border: 1px solid #93c5fd !important;
}



.stButton button {
    border-radius: 8px !important;
    font-size: 14px !important;
    transition: all 0.2s;
}



/* ===== רספונסיבי למובייל ===== */
@media (max-width: 480px) {
    .main-title { font-size: 20px; }
    .p-box { font-size: 12px; padding: 4px 8px; }
    .block-container { padding: 6px !important; }
}

[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 6px !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 2. פונקציות עזר
# ============================================================

def safe_split(val: str) -> list:
    """פיצול מחרוזת לרשימה, עם טיפול בערכים ריקים."""
    if not val or pd.isna(val):
        return []
    return [x.strip() for x in str(val).split(',') if x.strip()]


def safe_get_json(val) -> dict:
    """המרה בטוחה ל-dict מ-JSON או dict קיים."""
    if not val or (isinstance(val, float) and pd.isna(val)):
        return {}
    if isinstance(val, dict):
        return val
    try:
        return json.loads(str(val))
    except (json.JSONDecodeError, TypeError):
        return {}





def get_player_score(player: dict) -> float:
    """
    חישוב ציון שחקן משוקלל:
    - 60% ציון עצמי
    - 40% ממוצע דירוג עמיתים (אם קיים)
    """
    try:
        self_rating = float(player.get('rating') or 5.0)
    except (ValueError, TypeError):
        self_rating = 5.0

    try:
        peer_ratings = safe_get_json(player.get('peer_ratings', '{}'))
        peers = []
        if isinstance(peer_ratings, dict):
            for v in peer_ratings.values():
                try:
                    peers.append(float(v))
                except (ValueError, TypeError):
                    pass
        avg_peers = sum(peers) / len(peers) if peers else 0
    except Exception:
        avg_peers = 0

    if avg_peers > 0:
        return round(self_rating * 0.6 + avg_peers * 0.4, 2)
    return round(self_rating, 2)


def get_player_age(player: dict) -> int:
    """חישוב גיל שחקן."""
    return 2026 - int(player.get('birth_year', 1995))


def balance_score(team: list) -> float:
    """חישוב ציון ממוצע לקבוצה."""
    if not team:
        return 0.0
    return sum(p['score'] for p in team) / len(team)


# ============================================================
# 3. אלגוריתם חלוקה חכם (Snake Draft + אופטימיזציה)
# ============================================================

def divide_teams(selected_names: list, players_data: list) -> tuple[list, list]:
    """
    חלוקה מאוזנת בשיטת Snake Draft + 100 סיבובי אופטימיזציה.

    Snake Draft: 1→t1, 2→t2, 3→t2, 4→t1, 5→t1, 6→t2 ...
    לאחר מכן מנסים להחליף שחקנים בין הקבוצות ולשפר איזון.
    """
    # בניית pool עם ציונים
    pool = []
    for name in selected_names:
        p = next((x for x in players_data if x['name'] == name), None)
        if p:
            pool.append({
                'name': name,
                'score': get_player_score(p),
                'age': get_player_age(p)
            })

    # מיון לפי ציון יורד
    pool.sort(key=lambda x: x['score'], reverse=True)

    t1, t2 = [], []
    for i, player in enumerate(pool):
        # Snake Draft pattern: 0→t1, 1→t2, 2→t2, 3→t1, 4→t1, 5→t2...
        block = i // 2
        pos_in_block = i % 2
        if block % 2 == 0:
            (t1 if pos_in_block == 0 else t2).append(player)
        else:
            (t2 if pos_in_block == 0 else t1).append(player)

    # אופטימיזציה: ניסיון החלפות לשיפור איזון
    improved = True
    iterations = 0
    while improved and iterations < 200:
        improved = False
        iterations += 1
        for i in range(len(t1)):
            for j in range(len(t2)):
                diff_before = abs(balance_score(t1) - balance_score(t2))
                # ניסיון החלפה
                t1[i], t2[j] = t2[j], t1[i]
                diff_after = abs(balance_score(t1) - balance_score(t2))
                if diff_after < diff_before:
                    improved = True  # שיפור! נשמור את ההחלפה
                else:
                    t1[i], t2[j] = t2[j], t1[i]  # ביטול החלפה

    return t1, t2


# ============================================================
# 4. חיבור ל-Google Sheets
# ============================================================

@st.cache_resource
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)


def load_players() -> list:
    """טעינת שחקנים מ-Google Sheets."""
    try:
        conn = get_connection()
        df = conn.read(ttl=300)  # cache ל-5 דקות
        return df.dropna(subset=['name']).to_dict(orient='records')
    except Exception as e:
        st.warning(f"⚠️ שגיאה בטעינת נתונים: {e}")
        return []


def save_to_gsheets(players: list) -> bool:
    """שמירה ל-Google Sheets עם טיפול בשגיאות."""
    try:
        conn = get_connection()
        df = pd.DataFrame(players)
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ שגיאת שמירה: {e}")
        return False


# ============================================================
# 5. אתחול Session State
# ============================================================

if 'players' not in st.session_state:
    st.session_state.players = load_players()

if 'edit_name' not in st.session_state:
    st.session_state.edit_name = "🆕 שחקן חדש"

if 'teams_generated' not in st.session_state:
    st.session_state.teams_generated = False


# ============================================================
# 6. ממשק ראשי
# ============================================================

st.markdown("<div class='main-title'>⚽ ניהול כדורגל 2026</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון/הרשמה"])


# ============================================================
# TAB 1: חלוקת קבוצות
# ============================================================
with tab1:
    all_names = sorted([p['name'] for p in st.session_state.players if str(p.get('active', 'True')) == 'True'])

    if not all_names:
        st.info("אין שחקנים במאגר. הוסף שחקנים בטאב 'עדכון/הרשמה'.")
    else:
        selected_names = st.pills(
            "בחר שחקנים שהגיעו:",
            all_names,
            selection_mode="multi",
            key="p_selection"
        )

        count = len(selected_names) if selected_names else 0
        color = "#22c55e" if count >= 6 else "#f59e0b" if count >= 2 else "#ef4444"
        st.markdown(f"<p style='color:{color}; font-weight:bold;'>נבחרו: {count} שחקנים</p>",
                    unsafe_allow_html=True)

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            divide_clicked = st.button("חלק קבוצות 🚀", use_container_width=True,
                                       disabled=count < 2)
        with col_btn2:
            reshuffle_clicked = st.button("ערבב מחדש 🔀", use_container_width=True,
                                          disabled=count < 2)

        if divide_clicked or reshuffle_clicked:
            if selected_names:
                t1, t2 = divide_teams(selected_names, st.session_state.players)
                st.session_state.t1 = t1
                st.session_state.t2 = t2
                st.session_state.teams_generated = True

        # הצגת קבוצות
        if st.session_state.teams_generated and selected_names and \
                't1' in st.session_state and 't2' in st.session_state:

            diff = abs(balance_score(st.session_state.t1) - balance_score(st.session_state.t2))
            balance_color = "#22c55e" if diff < 0.5 else "#f59e0b" if diff < 1.0 else "#ef4444"
            st.markdown(
                f"<p style='text-align:center; color:{balance_color}; font-size:13px;'>"
                f"פער בין קבוצות: {diff:.2f}</p>",
                unsafe_allow_html=True
            )

            col_w, col_b = st.columns(2)
            teams_data = [
                {"team_key": "t1", "label": "⚪ לבן"},
                {"team_key": "t2", "label": "⚫ שחור"}
            ]

            for col, data in zip([col_w, col_b], teams_data):
                with col:
                    team = st.session_state[data["team_key"]]
                    st.markdown(
                        f"<div class='team-header'>{data['label']} ({len(team)})</div>",
                        unsafe_allow_html=True
                    )
                    for i, player in enumerate(team):
                        c_txt, c_swp = st.columns([4, 1])
                        with c_txt:
                            pnum = next((p.get('player_num','') for p in st.session_state.players if p['name']==player['name']), '')
                            pnum_tag = f"<span style='color:#60a5fa;font-size:11px;'>#{pnum} </span>" if pnum else ""
                            st.markdown(
                                f"<div class='p-box'>"
                                f"<span>{pnum_tag}{player['name']} ({player['age']})</span>"
                                f"<span class='p-score'>{player['score']:.1f}</span>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with c_swp:
                            other_key = "t2" if data["team_key"] == "t1" else "t1"
                            if st.button("🔄", key=f"sw_{data['team_key']}_{i}"):
                                moved = st.session_state[data["team_key"]].pop(i)
                                st.session_state[other_key].append(moved)
                                st.rerun()

                    if team:
                        avg_score = balance_score(team)
                        avg_age = sum(p['age'] for p in team) / len(team)
                        st.markdown(
                            f"<div class='team-stats'>"
                            f"<b>רמה: {avg_score:.1f}</b> | גיל ממוצע: {avg_age:.1f}"
                            f"</div>",
                            unsafe_allow_html=True
                        )


# ============================================================
# TAB 2: מאגר שחקנים
# ============================================================
with tab2:
    st.subheader(f"מאגר שחקנים ({len(st.session_state.players)})")

    if not st.session_state.players:
        st.info("המאגר ריק. הוסף שחקנים בטאב 'עדכון/הרשמה'.")
    else:
        # חיפוש
        search = st.text_input("🔍 חפש שחקן:", placeholder="הקלד שם...")
        show_inactive = st.toggle("הצג שחקנים לא פעילים", value=False)
        filtered = [
            p for p in st.session_state.players
            if (not search or search.lower() in p['name'].lower())
            and (show_inactive or str(p.get('active', 'True')) == 'True')
        ]

        # מיון לפי ציון
        filtered_with_scores = sorted(
            filtered,
            key=lambda p: get_player_score(p),
            reverse=True
        )

        for i, p in enumerate(filtered_with_scores):
            score = get_player_score(p)
            age = get_player_age(p)
            roles = p.get('roles', 'לא הוגדר') or 'לא הוגדר'

            # צבע לפי ציון
            score_color = "#22c55e" if score >= 7 else "#f59e0b" if score >= 5 else "#ef4444"

            is_active = str(p.get('active', 'True')) == 'True'
            active_badge = "<span style='background:#22c55e;color:white;border-radius:4px;padding:1px 7px;font-size:11px;margin-right:6px;'>פעיל</span>" if is_active else "<span style='background:#ef4444;color:white;border-radius:4px;padding:1px 7px;font-size:11px;margin-right:6px;'>לא פעיל</span>"
            pnum = p.get('player_num', '')
            pnum_str = f"<span style='color:#60a5fa; font-size:12px; margin-left:6px;'>#{pnum}</span>" if pnum else ""
            st.markdown(
                f"<div class='database-card'>"
                f"<div class='card-name'>{pnum_str}{p['name']} <span style='color:#94a3b8; font-size:13px;'>({age})</span> {active_badge}</div>"
                f"<div class='card-detail'>"
                f"ציון: <span style='color:{score_color}; font-weight:bold;'>{score:.1f}</span> "
                f"| תפקידים: {roles}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True
            )

            st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
            ce, gap, ct, cd = st.columns([3, 0.15, 1, 1])
            with ce:
                if st.button("📝 ערוך", key=f"db_ed_{p['name']}", use_container_width=True):
                    st.session_state.edit_name = p['name']
                    st.rerun()
            with gap:
                st.empty()
            with ct:
                toggle_label = "🔴" if is_active else "🟢"
                if st.button(toggle_label, key=f"db_tog_{p['name']}", use_container_width=True):
                    idx = next(i for i, x in enumerate(st.session_state.players) if x['name'] == p['name'])
                    st.session_state.players[idx]['active'] = str(not is_active)
                    save_to_gsheets(st.session_state.players)
                    st.rerun()
            with cd:
                if st.button("🗑️", key=f"db_dl_{p['name']}", use_container_width=True):
                    st.session_state.players = [
                        x for x in st.session_state.players if x['name'] != p['name']
                    ]
                    save_to_gsheets(st.session_state.players)
                    st.rerun()

            st.markdown("<hr style='border-color:#1e293b; margin:4px 0;'>", unsafe_allow_html=True)


# ============================================================
# TAB 3: עדכון / הרשמה
# ============================================================
with tab3:
    st.subheader("עדכון פרטי שחקן")

    all_options = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    default_idx = (
        all_options.index(st.session_state.edit_name)
        if st.session_state.edit_name in all_options
        else 0
    )
    choice = st.selectbox("בחר שחקן:", all_options, index=default_idx)

    p_data = next((p for p in st.session_state.players if p['name'] == choice), None)

    with st.form("edit_form", clear_on_submit=False):
        f_name = st.text_input(
            "שם מלא *",
            value=p_data['name'] if p_data else "",
            placeholder="הכנס שם מלא"
        )
        # מספר שחקן — אוטומטי לשחקן חדש, ניתן לעריכה
        existing_numbers = [int(p.get('player_num', 0)) for p in st.session_state.players if str(p.get('player_num', '')).isdigit()]
        next_num = max(existing_numbers) + 1 if existing_numbers else 1
        f_player_num = st.number_input(
            "מספר שחקן *",
            min_value=1, max_value=999,
            value=int(p_data.get('player_num', next_num)) if p_data and str(p_data.get('player_num', '')).isdigit() else next_num,
        )
        f_active = st.toggle(
            "שחקן פעיל",
            value=str(p_data.get('active', 'True')) == 'True' if p_data else True,
            key="form_active"
        )
        f_year = st.number_input(
            "שנת לידה:",
            min_value=1950,
            max_value=2015,
            value=int(p_data['birth_year']) if p_data else 1990
        )

        # תפקידים
        ROLES = ["שוער", "בלם", "מגן", "קשר אחורי", "קשר קדמי", "כנף", "חלוץ"]
        existing_roles = safe_split(p_data.get('roles', '')) if p_data else []
        f_roles = st.pills(
            "תפקידים:",
            ROLES,
            selection_mode="multi",
            default=[r for r in existing_roles if r in ROLES]
        )

        f_rate_str = st.pills(
            "ציון עצמי (1-10):",
            options=[str(i) for i in range(1, 11)],
            default=str(int(p_data.get('rating', 5)) if p_data else 5),
            selection_mode="single",
            key="self_rate_pills",
        )
        f_rate = int(f_rate_str) if f_rate_str else 5

        # דירוג עמיתים — רק אם יש שחקנים אחרים
        st.markdown("---")
        st.markdown("**דירוג עמיתים** (אופציונלי):")

        other_players = [p for p in st.session_state.players if p['name'] != (p_data['name'] if p_data else "")]
        peer_res = {}
        exist_peers = safe_get_json(p_data.get('peer_ratings', '{}') if p_data else '{}')

        if other_players:
            # הצגה ב-expander כדי לא להעמיס את הטופס
            with st.expander(f"דרג {len(other_players)} שחקנים (לחץ להרחבה)"):
                for op in other_players:
                    peer_str = st.pills(
                        f"{op['name']}:",
                        options=[str(i) for i in range(1, 11)],
                        default=str(int(exist_peers.get(op['name'], 5))),
                        selection_mode="single",
                        key=f"pr_{op['name']}",
                    )
                    peer_res[op['name']] = int(peer_str) if peer_str else 5
        else:
            st.caption("אין שחקנים אחרים לדרג עדיין.")

        submitted = st.form_submit_button("💾 שמור", use_container_width=True)

        if submitted:
            errors = []
            if not f_name.strip():
                errors.append("שם מלא")
            if not f_roles:
                errors.append("תפקידים")
            if not f_rate_str:
                errors.append("ציון עצמי")
            # בדיקת כפילות מספר שחקן
            dup_num = any(
                str(p.get('player_num', '')) == str(f_player_num)
                and p['name'] != (p_data['name'] if p_data else "")
                for p in st.session_state.players
            )
            if dup_num:
                errors.append(f"מספר שחקן {f_player_num} כבר תפוס")
            if errors:
                st.error(f"❌ שגיאה: {', '.join(errors)}")
            else:
                roles_str = ",".join(f_roles) if f_roles else ""
                new_entry = {
                    "name": f_name.strip(),
                    "player_num": f_player_num,
                    "birth_year": f_year,
                    "rating": f_rate,
                    "roles": roles_str,
                    "peer_ratings": json.dumps(peer_res, ensure_ascii=False),
                    "active": str(f_active),
                }

                # עדכון או הוספה
                existing_idx = next(
                    (i for i, x in enumerate(st.session_state.players) if x['name'] == choice),
                    None
                )
                if existing_idx is not None:
                    st.session_state.players[existing_idx] = new_entry
                else:
                    # בדיקה שהשם לא כבר קיים
                    if any(p['name'] == f_name.strip() for p in st.session_state.players):
                        st.error("❌ שחקן עם שם זה כבר קיים.")
                        st.stop()
                    st.session_state.players.append(new_entry)

                if save_to_gsheets(st.session_state.players):
                    st.success(f"✅ {f_name} נשמר בהצלחה!")
                    st.session_state.edit_name = f_name.strip()
                    st.rerun()
