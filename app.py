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


def get_peer_avg(player: dict, all_players: list = None) -> float | None:
    """
    ממוצע ציוני עמיתים — סורק את כל השחקנים ומחפש מי דירג את השחקן הזה.
    peer_ratings של כל שחקן = ציונים שהוא נתן לאחרים.
    """
    if all_players is None:
        # fallback — קרא מהשדה הישן
        peer_ratings = safe_get_json(player.get('peer_ratings', '{}'))
        if not isinstance(peer_ratings, dict):
            return None
        peers = [parse_rating(v) for v in peer_ratings.values()]
        peers = [v for v in peers if v is not None]
        return round(sum(peers) / len(peers), 1) if peers else None

    target_name = player.get('name', '')
    ratings_received = []
    for p in all_players:
        if p['name'] == target_name:
            continue
        pr = safe_get_json(p.get('peer_ratings', '{}'))
        val = parse_rating(pr.get(target_name))
        if val is not None:
            ratings_received.append(val)
    return round(sum(ratings_received) / len(ratings_received), 1) if ratings_received else None


def get_player_score(player: dict, all_players: list = None) -> float:
    """
    ציון משוכלל:
    - אם יש עמיתים: 60% אישי + 40% קבוצתי
    - אחרת: ציון אישי בלבד
    - אם אין כלום: 0
    """
    self_r = get_self_rating(player)
    peer_r = get_peer_avg(player, all_players)

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



def build_field_html(t1: list, t2: list, players_data: list) -> str:
    """בונה HTML אינטראקטיבי של מגרש עם drag & drop לפי תפקידים."""

    ROLE_POSITIONS = {
        "שוער":       {"x": 50, "y": 88},
        "בלם":        {"x": 50, "y": 73},
        "מגן ימין":   {"x": 20, "y": 63},
        "מגן שמאל":   {"x": 80, "y": 63},
        "קשר אחורי":  {"x": 50, "y": 53},
        "קשר קדמי":   {"x": 50, "y": 38},
        "אגף ימין":   {"x": 15, "y": 43},
        "אגף שמאל":   {"x": 85, "y": 43},
        "חלוץ":       {"x": 50, "y": 22},
    }
    ROLE_PRIORITY = ["שוער","בלם","מגן ימין","מגן שמאל","קשר אחורי","קשר קדמי","אגף ימין","אגף שמאל","חלוץ"]

    def assign_positions(team, color):
        """מיין שחקנים לפי תפקיד ראשי ופזר על המגרש."""
        assigned = []
        used_positions = set()
        # מעבר ראשון — שחקן שיש לו תפקיד ספציפי
        for p in team:
            name = p['name']
            pd = next((x for x in players_data if x['name'] == name), {})
            roles = [r.strip() for r in str(pd.get('roles','')).split(',') if r.strip()]
            placed = False
            for role in roles:
                if role in ROLE_POSITIONS and role not in used_positions:
                    pos = ROLE_POSITIONS[role]
                    assigned.append({"name": name, "x": pos["x"], "y": pos["y"], "role": role, "color": color, "score": p.get('score', 0)})
                    used_positions.add(role)
                    placed = True
                    break
            if not placed:
                assigned.append({"name": name, "x": None, "y": None, "role": "?", "color": color, "score": p.get('score', 0)})

        # מעבר שני — מי שנשאר ללא עמדה
        remaining_roles = [r for r in ROLE_PRIORITY if r not in used_positions]
        unplaced = [p for p in assigned if p["x"] is None]
        for i, p in enumerate(unplaced):
            if i < len(remaining_roles):
                role = remaining_roles[i]
                pos = ROLE_POSITIONS[role]
                p["x"] = pos["x"]
                p["y"] = pos["y"]
                p["role"] = role
            else:
                # אם עודף שחקנים — פזר בשורה תחתונה
                p["x"] = 10 + (i * 15) % 80
                p["y"] = 95
        return assigned

    team1_placed = assign_positions(t1, "#3b82f6")   # כחול = לבן
    team2_placed = assign_positions(t2, "#ef4444")    # אדום = שחור

    # בנה JSON לשחקנים
    import json
    players_json = json.dumps({"team1": team1_placed, "team2": team2_placed}, ensure_ascii=False)

    html = f"""
<div style="font-family:sans-serif; direction:rtl; padding:8px;">
  <div style="display:flex; gap:8px; margin-bottom:8px; justify-content:center;">
    <button onclick="toggleTeam(1)" id="btn1"
      style="padding:6px 16px; border-radius:6px; border:none; background:#3b82f6; color:white; cursor:pointer; font-size:13px;">⚪ לבן</button>
    <button onclick="toggleTeam(2)" id="btn2"
      style="padding:6px 16px; border-radius:6px; border:none; background:#ef4444; color:white; cursor:pointer; font-size:13px;">⚫ שחור</button>
    <button onclick="toggleTeam(0)" id="btn0"
      style="padding:6px 16px; border-radius:6px; border:none; background:#4a5568; color:white; cursor:pointer; font-size:13px;">שתי קבוצות</button>
  </div>
  <div style="position:relative; width:100%; max-width:420px; margin:0 auto;">
    <svg id="field" viewBox="0 0 420 560" style="width:100%; border-radius:8px; display:block;">
      <!-- מגרש -->
      <rect width="420" height="560" fill="#2d6a2d"/>
      <!-- פסי דשא -->
      <rect x="0" y="0" width="420" height="70" fill="#286228" opacity="0.5"/>
      <rect x="0" y="140" width="420" height="70" fill="#286228" opacity="0.5"/>
      <rect x="0" y="280" width="420" height="70" fill="#286228" opacity="0.5"/>
      <rect x="0" y="420" width="420" height="70" fill="#286228" opacity="0.5"/>
      <!-- קווים -->
      <rect x="20" y="20" width="380" height="520" fill="none" stroke="white" stroke-width="2"/>
      <line x1="20" y1="300" x2="400" y2="300" stroke="white" stroke-width="2"/>
      <circle cx="210" cy="300" r="50" fill="none" stroke="white" stroke-width="2"/>
      <circle cx="210" cy="300" r="3" fill="white"/>
      <!-- שער עליון -->
      <rect x="145" y="20" width="130" height="40" fill="none" stroke="white" stroke-width="2"/>
      <rect x="170" y="20" width="80" height="20" fill="none" stroke="white" stroke-width="2"/>
      <!-- שער תחתון -->
      <rect x="145" y="500" width="130" height="40" fill="none" stroke="white" stroke-width="2"/>
      <rect x="170" y="540" width="80" height="20" fill="none" stroke="white" stroke-width="2"/>
      <!-- עיגולי שוער -->
      <path d="M145,60 A65,65 0 0,1 275,60" fill="none" stroke="white" stroke-width="2"/>
      <path d="M145,500 A65,65 0 0,0 275,500" fill="none" stroke="white" stroke-width="2"/>
    </svg>
    <div id="players-layer" style="position:absolute; top:0; left:0; width:100%; height:100%;"></div>
  </div>
  <div id="tooltip" style="position:fixed; background:#1e293b; color:white; padding:6px 10px;
    border-radius:6px; font-size:12px; display:none; pointer-events:none; z-index:100;"></div>
</div>

<script>
var DATA = {players_json};
var activeTeam = 0;
var dragging = null;
var offsetX = 0, offsetY = 0;
var allPlayers = [];

function toggleTeam(t) {{
  activeTeam = t;
  render();
}}

function render() {{
  var layer = document.getElementById('players-layer');
  var svg = document.getElementById('field');
  var rect = svg.getBoundingClientRect();
  layer.innerHTML = '';
  allPlayers = [];

  var teams = activeTeam === 1 ? DATA.team1 :
              activeTeam === 2 ? DATA.team2 :
              DATA.team1.concat(DATA.team2);

  teams.forEach(function(p, i) {{
    var xPct = p.x / 100;
    var yPct = p.y / 100;
    var el = document.createElement('div');
    el.className = 'player-dot';
    el.dataset.idx = i;
    el.style.cssText = `
      position:absolute;
      left:calc(${{xPct * 100}}% - 22px);
      top:calc(${{yPct * 100}}% - 22px);
      width:44px; height:44px;
      border-radius:50%;
      background:${{p.color}};
      border:2px solid white;
      display:flex; flex-direction:column;
      align-items:center; justify-content:center;
      cursor:grab; user-select:none;
      box-shadow:0 2px 6px rgba(0,0,0,0.4);
      font-size:9px; color:white; font-weight:bold;
      text-align:center; line-height:1.2;
      transition: transform 0.1s;
      z-index:10;
    `;
    var shortName = p.name.split(' ')[0];
    el.innerHTML = `<span style="font-size:9px;line-height:1.1;">${{shortName}}</span><span style="font-size:8px;opacity:0.85;">${{p.role}}</span>`;

    el.addEventListener('mousedown', startDrag);
    el.addEventListener('touchstart', startDragTouch, {{passive:false}});
    el.addEventListener('mouseenter', function(e) {{
      var tt = document.getElementById('tooltip');
      tt.style.display = 'block';
      tt.innerHTML = `<b>${{p.name}}</b><br>${{p.role}} | ציון: ${{parseFloat(p.score).toFixed(1)}}`;
    }});
    el.addEventListener('mouseleave', function() {{
      document.getElementById('tooltip').style.display = 'none';
    }});
    layer.appendChild(el);
    allPlayers.push({{el: el, data: p}});
  }});
}}

function startDrag(e) {{
  e.preventDefault();
  dragging = e.currentTarget;
  dragging.style.cursor = 'grabbing';
  dragging.style.zIndex = 100;
  var r = dragging.getBoundingClientRect();
  offsetX = e.clientX - r.left - r.width/2;
  offsetY = e.clientY - r.top - r.height/2;
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
}}

function startDragTouch(e) {{
  e.preventDefault();
  dragging = e.currentTarget;
  var touch = e.touches[0];
  var r = dragging.getBoundingClientRect();
  offsetX = touch.clientX - r.left - r.width/2;
  offsetY = touch.clientY - r.top - r.height/2;
  document.addEventListener('touchmove', onDragTouch, {{passive:false}});
  document.addEventListener('touchend', stopDrag);
}}

function onDrag(e) {{
  if (!dragging) return;
  moveEl(e.clientX, e.clientY);
  var tt = document.getElementById('tooltip');
  tt.style.left = (e.clientX + 12) + 'px';
  tt.style.top  = (e.clientY - 10) + 'px';
}}

function onDragTouch(e) {{
  if (!dragging) return;
  e.preventDefault();
  var touch = e.touches[0];
  moveEl(touch.clientX, touch.clientY);
}}

function moveEl(cx, cy) {{
  var layer = document.getElementById('players-layer');
  var lr = layer.getBoundingClientRect();
  var x = cx - lr.left - 22;
  var y = cy - lr.top - 22;
  dragging.style.left = Math.max(0, Math.min(lr.width - 44, x)) + 'px';
  dragging.style.top  = Math.max(0, Math.min(lr.height - 44, y)) + 'px';
}}

function stopDrag(e) {{
  if (!dragging) return;
  dragging.style.cursor = 'grab';
  dragging.style.zIndex = 10;
  dragging = null;
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  document.removeEventListener('touchmove', onDragTouch);
  document.removeEventListener('touchend', stopDrag);
}}

document.addEventListener('mousemove', function(e) {{
  var tt = document.getElementById('tooltip');
  if (tt.style.display === 'block') {{
    tt.style.left = (e.clientX + 12) + 'px';
    tt.style.top  = (e.clientY - 10) + 'px';
  }}
}});

render();
</script>
"""
    return html

# ============================================================
# 4. חיבור ל-Google Sheets
# ============================================================

@st.cache_resource
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)


def load_players(force: bool = False) -> list:
    """טעינת שחקנים מ-Google Sheets — עם cache ידני ב-session_state."""
    import time
    now = time.time()
    cache_ttl = 300  # 5 דקות

    if not force:
        last = st.session_state.get('_players_loaded_at', 0)
        if now - last < cache_ttl and st.session_state.get('_players_cached'):
            return st.session_state['_players_cached']

    try:
        conn = get_connection()
        df = conn.read(ttl=0)
        players = df.dropna(subset=['name']).to_dict(orient='records')
        st.session_state['_players_cached'] = players
        st.session_state['_players_loaded_at'] = now
        return players
    except Exception as e:
        st.warning(f"⚠️ שגיאה בטעינת נתונים: {e}")
        return st.session_state.get('_players_cached', [])


def safe_int(val) -> int:
    """המרה בטוחה ל-int — מטפל ב-NaN, None, string ריק."""
    try:
        f = float(val)
        import math
        return 0 if math.isnan(f) else int(f)
    except (ValueError, TypeError):
        return 0


def _recalc_win_points(all_players: list, all_history: list):
    """
    חישוב מחדש של נקודות ניצחון לכל שחקן מההיסטוריה המלאה.
    מונע כפילויות — תמיד מחשב מאפס.
    """
    # אפס את כל הנקודות
    for p in all_players:
        p["win_points"] = 0
    # חשב מחדש מכל המשחקים
    for game in all_history:
        winner = game.get("winner", "")
        if not winner:
            continue
        winners = game.get("team1", []) if winner == "לבן" else game.get("team2", [])
        for name in winners:
            idx = next((i for i, p in enumerate(all_players) if p["name"] == name), None)
            if idx is not None:
                all_players[idx]["win_points"] = safe_int(all_players[idx].get("win_points")) + 1


def save_history_to_gsheets(history: list) -> bool:
    """שמירת היסטוריית משחקים לגיליון נפרד ב-Google Sheets."""
    try:
        conn = get_connection()
        rows = []
        for game in history:
            rows.append({
                "date": game["date"],
                "team": "לבן",
                "players": ", ".join(game.get("team1", [])),
                "avg_score": game.get("avg1", 0),
                "winner": game.get("winner", ""),
            })
            rows.append({
                "date": game["date"],
                "team": "שחור",
                "players": ", ".join(game.get("team2", [])),
                "avg_score": game.get("avg2", 0),
                "winner": game.get("winner", ""),
            })
        df = pd.DataFrame(rows)
        conn.update(data=df, worksheet="history")
        return True
    except Exception as e:
        st.warning(f"⚠️ לא ניתן לשמור היסטוריה: {e}")
        return False


def load_history_from_gsheets(force: bool = False) -> list:
    """טעינת היסטוריית משחקים — עם cache ידני ב-session_state."""
    import time
    now = time.time()
    cache_ttl = 300

    if not force:
        last = st.session_state.get('_history_loaded_at', 0)
        if now - last < cache_ttl and '_history_cached' in st.session_state:
            return st.session_state['_history_cached']

    try:
        conn = get_connection()
        df = conn.read(worksheet="history", ttl=0)
        if df.empty:
            result = []
        else:
            history = {}
            for _, row in df.iterrows():
                date = str(row.get("date", ""))
                team = str(row.get("team", ""))
                players = [p.strip() for p in str(row.get("players", "")).split(",") if p.strip()]
                avg = float(row.get("avg_score", 0) or 0)
                winner = str(row.get("winner", "") or "")
                if date not in history:
                    history[date] = {"date": date, "team1": [], "team2": [], "avg1": 0, "avg2": 0, "winner": ""}
                if team == "לבן":
                    history[date]["team1"] = players
                    history[date]["avg1"] = avg
                else:
                    history[date]["team2"] = players
                    history[date]["avg2"] = avg
                if winner:
                    history[date]["winner"] = winner
            result = sorted(history.values(), key=lambda x: x["date"], reverse=True)
        st.session_state['_history_cached'] = result
        st.session_state['_history_loaded_at'] = now
        return result
    except Exception as e:
        st.warning(f"⚠️ שגיאה בטעינת היסטוריה: {e}")
        return st.session_state.get('_history_cached', [])


def save_to_gsheets(players: list) -> bool:
    """שמירה ל-Google Sheets עם טיפול בשגיאות."""
    try:
        conn = get_connection()
        df = pd.DataFrame(players)
        # וודא שכל העמודות הנדרשות קיימות
        required_cols = ['name', 'player_num', 'birth_year', 'rating', 'roles', 'peer_ratings', 'active', 'win_points']
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

if 'game_history' not in st.session_state:
    st.session_state.game_history = load_history_from_gsheets()


# ============================================================
# 6. ממשק ראשי
# ============================================================

st.markdown("<div class='main-title'>⚽ ניהול כדורגל 2026</div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🏃 חלוקה", "🗄️ מאגר שחקנים", "📝 עדכון/הרשמה", "📅 היסטוריה"])


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

            # בניית HTML קומפקטי לסלולאר
            t1 = st.session_state.t1
            t2 = st.session_state.t2

            def player_rows(team, team_key):
                rows = ""
                for i, p in enumerate(team):
                    pnum = next((x.get('player_num','') for x in st.session_state.players if x['name']==p['name']), '')
                    pnum_tag = f"<span style='color:#60a5fa;font-size:10px;'>#{pnum}</span> " if pnum else ""
                    other_key = "t2" if team_key == "t1" else "t1"
                    rows += (
                        f"<div style='display:flex;justify-content:space-between;align-items:center;"
                        f"background:#1e293b;border-radius:5px;padding:5px 7px;margin-bottom:3px;'>"
                        f"<span style='font-size:12px;'>{pnum_tag}{p['name']} "
                        f"<span style='color:#64748b;font-size:11px;'>({p['age']})</span></span>"
                        f"<span style='color:#22c55e;font-size:11px;font-weight:bold;'>{p['score']:.1f}</span>"
                        f"</div>"
                    )
                return rows

            avg1 = balance_score(t1)
            avg2 = balance_score(t2)
            age1 = sum(p['age'] for p in t1)/len(t1) if t1 else 0
            age2 = sum(p['age'] for p in t2)/len(t2) if t2 else 0

            teams_html = f"""
<div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;direction:rtl;'>
  <div style='background:#1e3a5f;border-radius:8px 8px 0 0;overflow:hidden;'>
    <div style='background:#1e3a5f;padding:7px 10px;text-align:center;font-weight:bold;font-size:13px;'>
      ⚪ לבן ({len(t1)})
    </div>
    <div style='padding:6px;'>
      {player_rows(t1, 't1')}
    </div>
    <div style='background:#0f172a;padding:6px;text-align:center;font-size:11px;border-top:1px solid #334155;'>
      <b>רמה: {avg1:.1f}</b> | גיל: {age1:.1f}
    </div>
  </div>
  <div style='background:#3a1e1e;border-radius:8px 8px 0 0;overflow:hidden;'>
    <div style='background:#3a1e1e;padding:7px 10px;text-align:center;font-weight:bold;font-size:13px;'>
      ⚫ שחור ({len(t2)})
    </div>
    <div style='padding:6px;'>
      {player_rows(t2, 't2')}
    </div>
    <div style='background:#0f172a;padding:6px;text-align:center;font-size:11px;border-top:1px solid #334155;'>
      <b>רמה: {avg2:.1f}</b> | גיל: {age2:.1f}
    </div>
  </div>
</div>
"""
            st.markdown(teams_html, unsafe_allow_html=True)

            # כפתורי החלפה
            st.markdown("<p style='font-size:11px;color:#64748b;text-align:center;margin:4px 0;'>להחלפת שחקן בין קבוצות:</p>", unsafe_allow_html=True)
            swap_cols = st.columns(len(t1) + len(t2))
            for i, player in enumerate(t1):
                with swap_cols[i]:
                    if st.button("🔄", key=f"sw_t1_{i}", help=player['name']):
                        st.session_state.t2.append(st.session_state.t1.pop(i))
                        st.rerun()
            for j, player in enumerate(t2):
                with swap_cols[len(t1) + j]:
                    if st.button("🔄", key=f"sw_t2_{j}", help=player['name']):
                        st.session_state.t1.append(st.session_state.t2.pop(j))
                        st.rerun()

            # כפתור מגרש
            if st.button("🏟️ הצג מגרש", use_container_width=True):
                st.session_state.show_field = not st.session_state.get('show_field', False)

            if st.session_state.get('show_field', False):
                field_html = build_field_html(
                    st.session_state.t1,
                    st.session_state.t2,
                    st.session_state.players
                )
                import streamlit.components.v1 as components
                components.html(field_html, height=660, scrolling=False)

            # כפתור שמירת חלוקה
            st.markdown("---")
            game_date = st.date_input("תאריך המשחק:", value=None, key="game_date")
            if st.button("💾 שמור חלוקה להיסטוריה", use_container_width=True, disabled=not game_date):
                history = st.session_state.get('game_history', [])
                # בדוק אם כבר קיים משחק לאותו תאריך
                existing = next((i for i, g in enumerate(history) if g["date"] == str(game_date)), None)
                new_game = {
                    "date": str(game_date),
                    "team1": [p['name'] for p in st.session_state.t1],
                    "team2": [p['name'] for p in st.session_state.t2],
                    "avg1": round(balance_score(st.session_state.t1), 2),
                    "avg2": round(balance_score(st.session_state.t2), 2),
                    "winner": history[existing].get("winner", "") if existing is not None else "",
                }
                if existing is not None:
                    history[existing] = new_game
                else:
                    history.append(new_game)
                history = sorted(history, key=lambda x: x["date"], reverse=True)
                st.session_state.game_history = history
                save_history_to_gsheets(history)
                st.success(f"✅ חלוקה נשמרה לתאריך {game_date}")


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
            peer_avg    = get_peer_avg(p, st.session_state.players)
            weighted    = get_player_score(p, st.session_state.players)

            def score_color(s): return "#22c55e" if s >= 7 else "#f59e0b" if s >= 5 else "#ef4444"
            def score_badge(label, val):
                if val is None: return f"<span style='color:#4a5568;font-size:12px;'>{label}: —</span>"
                c = score_color(val)
                return f"<span style='font-size:12px;'>{label}: <b style='color:{c};'>{val:.1f}</b></span>"

            active_badge = "<span style='background:#22c55e;color:white;border-radius:4px;padding:1px 7px;font-size:11px;'>פעיל</span>" if is_active else "<span style='background:#ef4444;color:white;border-radius:4px;padding:1px 7px;font-size:11px;'>לא פעיל</span>"
            pnum = p.get('player_num', '')
            pnum_str = f"<span style='color:#60a5fa;font-size:12px;margin-left:6px;'>#{pnum}</span>" if pnum else ""

            wins = safe_int(p.get("win_points"))
            games_played = sum(
                1 for g in st.session_state.get('game_history', [])
                if p['name'] in g.get('team1', []) + g.get('team2', [])
            )
            if wins > 0 or games_played > 0:
                wins_str = f"<span style='color:#f59e0b;font-size:12px;margin-right:8px;'>🏆 {wins}/{games_played}</span>"
            else:
                wins_str = ""
            st.markdown(
                f"<div class='database-card'>"
                f"<div class='card-name' style='margin-bottom:6px;'>{pnum_str}{p['name']} "
                f"<span style='color:#94a3b8;font-size:13px;'>({age})</span> {active_badge} {wins_str}</div>"
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
                    st.session_state.nav_to_edit = True
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
    # באנר ניווט מהמאגר
    if st.session_state.pop('nav_to_edit', False):
        st.info(f"✏️ עורך: **{st.session_state.edit_name}** — גלול למטה לטופס")

    # אינדיקציה לאחר שמירה
    if st.session_state.get('show_save_success'):
        saved_name = st.session_state.pop('show_save_success')
        st.success(f"✅ {saved_name} נשמר בהצלחה!")
        st.markdown("<script>window.scrollTo(0,0);</script>", unsafe_allow_html=True)

    st.subheader("עדכון פרטי שחקן")

    all_options = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
    default_idx = (
        all_options.index(st.session_state.edit_name)
        if st.session_state.edit_name in all_options
        else 0
    )
    choice = st.selectbox("בחר שחקן:", all_options, index=default_idx)

    p_data = next((p for p in st.session_state.players if p['name'] == choice), None)

    # הצגת ציונים נוכחיים אם יש שחקן נבחר
    if p_data:
        self_r   = get_self_rating(p_data)
        peer_r   = get_peer_avg(p_data, st.session_state.players)
        weighted = get_player_score(p_data, st.session_state.players)

        def _sc(v): return "#22c55e" if v >= 7 else "#f59e0b" if v >= 5 else "#ef4444"
        def _badge(label, val):
            if val is None:
                return f"<div style='text-align:center;flex:1'><div style='font-size:11px;color:#94a3b8;margin-bottom:2px;'>{label}</div><div style='font-size:22px;color:#4a5568;'>—</div></div>"
            return f"<div style='text-align:center;flex:1'><div style='font-size:11px;color:#94a3b8;margin-bottom:2px;'>{label}</div><div style='font-size:22px;font-weight:bold;color:{_sc(val)};'>{val:.1f}</div></div>"

        st.markdown(
            f"<div style='display:flex;gap:8px;background:#1e293b;border-radius:10px;padding:12px 16px;margin-bottom:14px;'>"
            f"{_badge('ציון אישי', self_r)}"
            f"<div style='width:1px;background:#334155;margin:0 4px;'></div>"
            f"{_badge('ציון קבוצתי', peer_r)}"
            f"<div style='width:1px;background:#334155;margin:0 4px;'></div>"
            f"{_badge('משוכלל', weighted if weighted > 0 else None)}"
            f"</div>",
            unsafe_allow_html=True
        )

    # מספר שחקן רץ — לשחקן קיים: שומר את המספר שלו. לשחקן חדש: מספר רץ (len+1)
    if p_data and str(p_data.get('player_num', '')).isdigit():
        auto_num = int(p_data['player_num'])
    else:
        auto_num = len(st.session_state.players) + 1

    with st.form("edit_form", clear_on_submit=False):
        # מספר שחקן — מעל השם
        st.markdown(f"<div style='color:#94a3b8; font-size:14px; margin-bottom:4px;'>מספר שחקן: <b style='color:#60a5fa;'>#{auto_num}</b></div>", unsafe_allow_html=True)

        # שם מלא
        f_name = st.text_input(
            "שם מלא *",
            value=p_data['name'] if p_data else "",
            placeholder="הכנס שם מלא"
        )

        # שנת לידה
        f_year = st.number_input(
            "שנת לידה *",
            min_value=1950,
            max_value=2015,
            value=int(p_data['birth_year']) if p_data else 1990
        )

        # תפקידים
        ROLES = ["שוער", "בלם", "מגן ימין", "מגן שמאל", "קשר אחורי", "קשר קדמי", "אגף ימין", "אגף שמאל", "חלוץ"]
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
            options=["—"] + [str(i) for i in range(1, 11)],
            default=existing_rating if existing_rating else "—",
            selection_mode="single",
            key=f"self_rate_pills_{choice}",
        )
        f_rate = int(f_rate_str) if f_rate_str and f_rate_str != "—" else None

        # כפתור פעיל — מתחת לציון אישי
        st.markdown("<div style='margin-top:8px; margin-right:4px;'>", unsafe_allow_html=True)
        f_active = st.toggle(
            "שחקן פעיל",
            value=is_player_active(p_data) if p_data else True,
            key=f"form_active_{choice}"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # דירוג עמיתים
        st.markdown("---")
        st.markdown("**דירוג עמיתים** (חובה לכל שחקן):")

        other_players = sorted([p for p in st.session_state.players if p['name'] != (p_data['name'] if p_data else "")], key=lambda p: p['name'].strip().split()[0])
        peer_res = {}
        # exist_peers = מה השחקן נתן לאחרים (נשמר ב-peer_ratings שלו)
        exist_peers = safe_get_json(p_data.get('peer_ratings', '{}') if p_data else '{}')

        RATING_OPTIONS = ["—", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

        if other_players:
            with st.expander(f"דרג {len(other_players)} שחקנים (לחץ להרחבה)"):
                for op in other_players:
                    peer_val = exist_peers.get(op['name'])
                    try:
                        peer_default = str(int(float(peer_val))) if peer_val and float(peer_val) > 0 else "—"
                    except (ValueError, TypeError):
                        peer_default = "—"
                    peer_str = st.pills(
                        f"{op['name']} *",
                        options=RATING_OPTIONS,
                        default=peer_default,
                        selection_mode="single",
                        key=f"pr_{choice}_{op['name']}",
                    )
                    peer_res[op['name']] = int(peer_str) if peer_str and peer_str != "—" else None
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
                # peer_ratings = מה השחקן נתן לאחרים
                my_ratings = {k: v for k, v in peer_res.items() if v is not None and v > 0}

                new_entry = {
                    "name": f_name.strip(),
                    "player_num": auto_num,
                    "birth_year": f_year,
                    "rating": f_rate,
                    "roles": roles_str,
                    "peer_ratings": json.dumps(my_ratings, ensure_ascii=False),
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

                # peer_ratings נשמר אצל השחקן עצמו = מה שהוא נתן לאחרים
                # אין צורך לפזר לשורות אחרות

                if save_to_gsheets(st.session_state.players):
                    # לא טוענים מחדש מ-Sheets — session_state כבר מעודכן
                    st.session_state.edit_name = f_name.strip()
                    st.session_state.show_save_success = f_name.strip()
                    st.rerun()


# ============================================================
# TAB 4: היסטוריית משחקים
# ============================================================
with tab4:
    st.subheader("היסטוריית משחקים")

    col_r, col_pts = st.columns(2)
    with col_r:
        if st.button("🔄 רענן", use_container_width=True):
            st.session_state.game_history = load_history_from_gsheets(force=True)
            st.rerun()

    history = st.session_state.get('game_history', [])

    if not history:
        st.info("אין היסטוריה עדיין. שמור חלוקה מטאב החלוקה.")
    else:
        for gi, game in enumerate(history):
            date_str = game.get("date", "")
            t1       = game.get("team1", [])
            t2       = game.get("team2", [])
            avg1     = game.get("avg1", 0)
            avg2     = game.get("avg2", 0)
            winner   = game.get("winner", "")

            # תגי מנצח/מפסיד
            def team_label(team_name, team_winner):
                if not team_winner:
                    return f"{'⚪' if team_name == 'לבן' else '⚫'} {team_name}"
                if team_name == team_winner:
                    return f"{'⚪' if team_name == 'לבן' else '⚫'} {team_name} 🏆"
                return f"{'⚪' if team_name == 'לבן' else '⚫'} {team_name}"

            t1_color = "#22c55e" if winner == "לבן" else "#94a3b8" if winner else "#94a3b8"
            t2_color = "#22c55e" if winner == "שחור" else "#94a3b8" if winner else "#94a3b8"

            st.markdown(
                f"<div class='database-card'>"
                f"<div style='font-size:14px;font-weight:bold;color:#60a5fa;margin-bottom:8px;'>📅 {date_str}"
                f"{'  🏆 מנצח: ' + winner if winner else ''}</div>"
                f"<div style='display:flex;gap:12px;flex-wrap:wrap;'>"
                f"<div style='flex:1;min-width:120px;'>"
                f"<div style='font-size:12px;color:{t1_color};font-weight:bold;margin-bottom:4px;'>{team_label('לבן', winner)} — רמה {avg1:.1f}</div>"
                f"<div style='font-size:13px;color:#e2e8f0;'>{', '.join(t1) if t1 else '—'}</div>"
                f"</div>"
                f"<div style='flex:1;min-width:120px;'>"
                f"<div style='font-size:12px;color:{t2_color};font-weight:bold;margin-bottom:4px;'>{team_label('שחור', winner)} — רמה {avg2:.1f}</div>"
                f"<div style='font-size:13px;color:#e2e8f0;'>{', '.join(t2) if t2 else '—'}</div>"
                f"</div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True
            )

            # כפתורי קביעת מנצח
            cw1, cw2, cw3 = st.columns(3)
            with cw1:
                if st.button("🏆 לבן ניצח", key=f"win1_{gi}", use_container_width=True,
                             type="primary" if winner == "לבן" else "secondary"):
                    history[gi]["winner"] = "לבן"
                    st.session_state.game_history = history
                    _recalc_win_points(st.session_state.players, history)
                    save_history_to_gsheets(history)
                    save_to_gsheets(st.session_state.players)
                    st.rerun()
            with cw2:
                if st.button("🏆 שחור ניצח", key=f"win2_{gi}", use_container_width=True,
                             type="primary" if winner == "שחור" else "secondary"):
                    history[gi]["winner"] = "שחור"
                    st.session_state.game_history = history
                    _recalc_win_points(st.session_state.players, history)
                    save_history_to_gsheets(history)
                    save_to_gsheets(st.session_state.players)
                    st.rerun()
            with cw3:
                if winner and st.button("↩️ בטל תוצאה", key=f"win3_{gi}", use_container_width=True):
                    history[gi]["winner"] = ""
                    st.session_state.game_history = history
                    _recalc_win_points(st.session_state.players, history)
                    save_history_to_gsheets(history)
                    save_to_gsheets(st.session_state.players)
                    st.rerun()

            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # טבלת נקודות ניצחון
    st.markdown("---")
    st.markdown("### 🏅 טבלת נקודות ניצחון")
    pts_data = [
        {"שם": p["name"], "ניצחונות": safe_int(p.get("win_points"))}
        for p in sorted(st.session_state.players, key=lambda x: safe_int(x.get("win_points")), reverse=True)
        if is_player_active(p)
    ]
    if pts_data:
        for rank, row in enumerate(pts_data, 1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            bar_w = int(row["ניצחונות"] / max(r["ניצחונות"] for r in pts_data) * 100) if pts_data[0]["ניצחונות"] > 0 else 0
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:5px;'>"
                f"<span style='width:30px;text-align:center;'>{medal}</span>"
                f"<span style='width:120px;font-size:13px;'>{row['שם']}</span>"
                f"<div style='flex:1;background:#1e293b;border-radius:4px;height:18px;'>"
                f"<div style='width:{bar_w}%;background:#3b82f6;border-radius:4px;height:18px;'></div>"
                f"</div>"
                f"<span style='width:30px;text-align:left;font-size:13px;color:#60a5fa;font-weight:bold;'>{row['ניצחונות']}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.caption("אין נתוני ניצחונות עדיין.")
