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





def is_player_active(player: dict) -> bool:
    """בדיקת פעילות שחקן — תומך ב-True/False/TRUE/FALSE/1/0/'true'/'false'."""
    val = player.get('active', True)
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    return str(val).strip().lower() not in ('false', '0', 'none', '')


def parse_rating(val) -> float | None:
    """המרת ערך דירוג למספר — מחזיר None אם לא תקין או 0."""
    try:
        f = float(val)
        return f if f > 0 else None
    except (ValueError, TypeError):
        return None


def get_self_rating(player: dict) -> float | None:
    """ציון עצמי — None אם לא הוגדר."""
    return parse_rating(player.get('rating'))


def get_peer_avg(player: dict) -> float | None:
    """ממוצע ציוני עמיתים — None אם אין דירוגים."""
    peer_ratings = safe_get_json(player.get('peer_ratings', '{}'))
    if not isinstance(peer_ratings, dict):
        return None
    peers = [parse_rating(v) for v in peer_ratings.values()]
    peers = [v for v in peers if v is not None]
    return round(sum(peers) / len(peers), 1) if peers else None


def get_player_score(player: dict) -> float:
    """
    ציון משוכלל:
    - אם יש עמיתים: 60% אישי + 40% קבוצתי
    - אחרת: ציון אישי בלבד
    - אם אין כלום: 0
    """
    self_r = get_self_rating(player)
    peer_r = get_peer_avg(player)

    if self_r is not None and peer_r is not None:
        return round(self_r * 0.6 + peer_r * 0.4, 2)
    if self_r is not None:
        return round(self_r, 2)
    return 0.0


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
        # וודא שכל העמודות הנדרשות קיימות
        required_cols = ['name', 'player_num', 'birth_year', 'rating', 'roles', 'peer_ratings', 'active']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''
        df = df[required_cols]

        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ שגיאת שמירה: {e}")
        import traceback
        st.error(traceback.format_exc())
        return False


# ============================================================
# 5. אתחול Session State
# ============================================================

if 'players' not in st.session_state:
    st.session_state.players = load_players()
    # אתחול מספרים רצים לשחקנים שאין להם player_num
    needs_save = False
    for i, p in enumerate(st.session_state.players):
        if not str(p.get('player_num', '')).isdigit():
            p['player_num'] = i + 1
            needs_save = True
    if needs_save:
        save_to_gsheets(st.session_state.players)

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
    all_names = sorted([p['name'] for p in st.session_state.players if is_player_active(p)])

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
            and (show_inactive or is_player_active(p))
        ]

        # מיון לפי שם פרטי (אות ראשונה)
        filtered_with_scores = sorted(
            filtered,
            key=lambda p: p['name'].strip().split()[0] if p.get('name') else ''
        )

        for i, p in enumerate(filtered_with_scores):
            age = get_player_age(p)
            roles = p.get('roles', 'לא הוגדר') or 'לא הוגדר'
            is_active = is_player_active(p)

            # ציונים
            self_rating = get_self_rating(p)
            peer_avg    = get_peer_avg(p)
            weighted    = get_player_score(p)

            def score_color(s): return "#22c55e" if s >= 7 else "#f59e0b" if s >= 5 else "#ef4444"
            def score_badge(label, val):
                if val is None: return f"<span style='color:#4a5568;font-size:12px;'>{label}: —</span>"
                c = score_color(val)
                return f"<span style='font-size:12px;'>{label}: <b style='color:{c};'>{val:.1f}</b></span>"

            active_badge = "<span style='background:#22c55e;color:white;border-radius:4px;padding:1px 7px;font-size:11px;'>פעיל</span>" if is_active else "<span style='background:#ef4444;color:white;border-radius:4px;padding:1px 7px;font-size:11px;'>לא פעיל</span>"
            pnum = p.get('player_num', '')
            pnum_str = f"<span style='color:#60a5fa;font-size:12px;margin-left:6px;'>#{pnum}</span>" if pnum else ""

            st.markdown(
                f"<div class='database-card'>"
                f"<div class='card-name' style='margin-bottom:6px;'>{pnum_str}{p['name']} "
                f"<span style='color:#94a3b8;font-size:13px;'>({age})</span> {active_badge}</div>"
                f"<div style='color:#94a3b8;font-size:12px;margin-bottom:4px;'>תפקידים: {roles}</div>"
                f"<div style='display:flex;gap:16px;flex-wrap:wrap;margin-top:4px;'>"
                f"{score_badge('אישי', self_rating)}"
                f"<span style='color:#4a5568;font-size:12px;'>|</span>"
                f"{score_badge('קבוצתי', peer_avg)}"
                f"<span style='color:#4a5568;font-size:12px;'>|</span>"
                f"<span style='font-size:12px;'>משוכלל: <b style='color:{score_color(weighted)};font-size:13px;'>{weighted:.1f}</b></span>"
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

    # מספר שחקן רץ — לשחקן קיים: שומר את המספר שלו. לשחקן חדש: מספר רץ (len+1)
    if p_data and str(p_data.get('player_num', '')).isdigit():
        auto_num = int(p_data['player_num'])
    else:
        auto_num = len(st.session_state.players) + 1

    with st.form("edit_form", clear_on_submit=False):
        # שם מלא
        f_name = st.text_input(
            "שם מלא *",
            value=p_data['name'] if p_data else "",
            placeholder="הכנס שם מלא"
        )

        # מספר שחקן — אוטומטי, לקריאה בלבד (מוצג כטקסט)
        st.markdown(f"<div style='color:#94a3b8; font-size:14px; margin-bottom:4px;'>מספר שחקן: <b style='color:#60a5fa;'>#{auto_num}</b></div>", unsafe_allow_html=True)

        # שנת לידה
        f_year = st.number_input(
            "שנת לידה *",
            min_value=1950,
            max_value=2015,
            value=int(p_data['birth_year']) if p_data else 1990
        )

        # תפקידים
        ROLES = ["שוער", "בלם", "מגן", "קשר אחורי", "קשר קדמי", "כנף", "חלוץ"]
        existing_roles = safe_split(p_data.get('roles', '')) if p_data else []
        f_roles = st.pills(
            "תפקידים *",
            ROLES,
            selection_mode="multi",
            default=[r for r in existing_roles if r in ROLES]
        )

        # ציון עצמי
        existing_rating = str(int(p_data['rating'])) if p_data and str(p_data.get('rating','')).replace('.','').isdigit() and int(float(p_data.get('rating',0))) > 0 else None
        f_rate_str = st.pills(
            "ציון עצמי (1-10) *",
            options=[str(i) for i in range(1, 11)],
            default=existing_rating,
            selection_mode="single",
            key="self_rate_pills",
        )
        f_rate = int(f_rate_str) if f_rate_str else None

        # כפתור פעיל — מתחת לציון אישי
        st.markdown("<div style='margin-top:8px; margin-right:4px;'>", unsafe_allow_html=True)
        f_active = st.toggle(
            "שחקן פעיל",
            value=is_player_active(p_data) if p_data else True,
            key="form_active"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # דירוג עמיתים
        st.markdown("---")
        st.markdown("**דירוג עמיתים** (חובה לכל שחקן):")

        other_players = [p for p in st.session_state.players if p['name'] != (p_data['name'] if p_data else "")]
        peer_res = {}
        exist_peers = safe_get_json(p_data.get('peer_ratings', '{}') if p_data else '{}')

        if other_players:
            with st.expander(f"דרג {len(other_players)} שחקנים (לחץ להרחבה)"):
                for op in other_players:
                    peer_val = exist_peers.get(op['name'])
                    peer_default = str(int(float(peer_val))) if peer_val and str(peer_val).replace('.','').isdigit() and int(float(peer_val)) > 0 else None
                    peer_str = st.pills(
                        f"{op['name']} *",
                        options=[str(i) for i in range(1, 11)],
                        default=peer_default,
                        selection_mode="single",
                        key=f"pr_{op['name']}",
                    )
                    peer_res[op['name']] = int(peer_str) if peer_str else None
        else:
            st.caption("אין שחקנים אחרים לדרג עדיין.")

        submitted = st.form_submit_button("💾 שמור", use_container_width=True)

        if submitted:
            errors = []
            if not f_name.strip():
                errors.append("שם מלא")
            if not f_roles:
                errors.append("תפקידים")
            if not f_rate:
                errors.append("ציון עצמי")
            # בדיקה שכל השחקנים דורגו
            unrated = [name for name, val in peer_res.items() if val is None]
            if unrated and other_players:
                errors.append(f"דירוג חסר: {', '.join(unrated)}")
            if errors:
                st.error(f"❌ שדות חובה חסרים: {', '.join(errors)}")
            else:
                roles_str = ",".join(f_roles) if f_roles else ""
                # peer_res — שמור רק ערכים שדורגו (> 0), מחק None ו-0
                clean_peers = {k: v for k, v in peer_res.items() if v is not None and v > 0}
                new_entry = {
                    "name": f_name.strip(),
                    "player_num": auto_num,
                    "birth_year": f_year,
                    "rating": f_rate,
                    "roles": roles_str,
                    "peer_ratings": json.dumps(clean_peers, ensure_ascii=False),
                    "active": str(f_active),
                }

                # עדכון או הוספה של השחקן הנוכחי
                existing_idx = next(
                    (i for i, x in enumerate(st.session_state.players) if x['name'] == choice),
                    None
                )
                if existing_idx is not None:
                    st.session_state.players[existing_idx] = new_entry
                else:
                    if any(p['name'] == f_name.strip() for p in st.session_state.players):
                        st.error("❌ שחקן עם שם זה כבר קיים.")
                        st.stop()
                    st.session_state.players.append(new_entry)

                # עדכון peer_ratings אצל כל שחקן שדורג ע"י השחקן הנוכחי
                # clean_peers = {שם_שחקן: ציון} — צריך להוסיף את הציון אצל כל אחד מהם
                editor_name = f_name.strip()
                for rated_name, rating_val in clean_peers.items():
                    target_idx = next(
                        (i for i, x in enumerate(st.session_state.players) if x['name'] == rated_name),
                        None
                    )
                    if target_idx is not None:
                        existing_pr = safe_get_json(st.session_state.players[target_idx].get('peer_ratings', '{}'))
                        existing_pr[editor_name] = rating_val
                        st.session_state.players[target_idx]['peer_ratings'] = json.dumps(existing_pr, ensure_ascii=False)

                if save_to_gsheets(st.session_state.players):
                    st.success(f"✅ {f_name} נשמר בהצלחה!")
                    st.session_state.edit_name = f_name.strip()
                    st.rerun()
