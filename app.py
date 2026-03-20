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

/* ===== כותרת קבועה בכל הטאבים ===== */
[data-testid="stHeader"] {
    background: #0f1117 !important;
}
[data-testid="stHeader"]::after {
    content: "⚽ ניהול כדורגל 2026";
    display: block;
    text-align: center;
    font-size: 22px;
    font-weight: bold;
    color: #60a5fa;
    padding: 10px 0 2px;
}

/* ===== כותרת ===== */
.main-title {
    font-size: 26px;
    text-align: center !important;
    font-weight: bold;
    margin-bottom: 4px;
    color: #60a5fa;
    letter-spacing: 1px;
    direction: rtl;
}
.sub-title {
    font-size: 12px;
    text-align: center !important;
    color: #4a5568;
    margin-bottom: 16px;
    direction: rtl;
}

/* ===== כרטיס שחקן במאגר ===== */
.card-name { font-size: 16px; font-weight: bold; color: #f1f5f9; direction: rtl; text-align: right; }
.card-detail { font-size: 14px; color: #94a3b8; margin-top: 3px; }
.p-score { color: #22c55e; font-size: 12px; font-weight: bold; }
.team-stats {
    background: #0f172a; border-top: 2px solid #334155;
    padding: 8px; margin-top: 6px; font-size: 12px;
    text-align: center; border-radius: 0 0 10px 10px;
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
    .block-container { padding: 6px !important; max-width: 100vw !important; overflow-x: hidden !important; }
}

/* ===== כללי — מניעת גלישה ===== */
.stApp { overflow-x: hidden !important; }
[data-testid="stAppViewContainer"] { overflow-x: hidden !important; }

/* ===== צמצום שורת שחקן בחלוקה ===== */
[data-testid="stHorizontalBlock"] {
    max-width: 100% !important;
    overflow: hidden !important;
}
[data-testid="stHorizontalBlock"] > div {
    min-width: 0 !important;
    overflow: hidden !important;
}

/* ===== p-box — תיבת שחקן בחלוקה ===== */
.p-box {
    background: #1e293b; border: 1px solid #334155; border-radius: 6px;
    padding: 7px 10px; margin-bottom: 4px;
    display: flex; justify-content: space-between; align-items: center;
    min-height: 38px; font-size: 14px;
    text-align: right; direction: rtl;
    width: 100%; box-sizing: border-box;
}

/* ===== database-card ===== */
.database-card {
    background: #1e293b; border: 1px solid #334155; border-radius: 10px;
    padding: 10px 12px; margin-bottom: 8px;
    text-align: right; direction: rtl;
    width: 100%; box-sizing: border-box;
}

/* ===== team-header ===== */
.team-header {
    background: #1e3a5f; border-radius: 8px 8px 0 0;
    padding: 8px; text-align: center;
    font-weight: bold; font-size: 15px; direction: rtl; text-align: right;
    width: 100%; box-sizing: border-box;
}

/* ===== כפתורי Streamlit — גודל מינימלי למובייל ===== */
@media (max-width: 480px) {
    .stButton button { font-size: 13px !important; padding: 5px 6px !important; min-width: 0 !important; }
    .p-box { font-size: 14px !important; }
    .team-header { font-size: 15px !important; }
    .database-card { font-size: 14px !important; }
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

# קבוצות תפקידים לתבנית
ROLE_GROUPS = {
    "שוער":      "שוערים",
    "בלם":       "מגנים",
    "מגן ימין":  "מגנים",
    "מגן שמאל":  "מגנים",
    "קשר אחורי": "קשרים",
    "קשר קדמי":  "קשרים",
    "אגף ימין":  "קשרים",
    "אגף שמאל":  "קשרים",
    "חלוץ":      "חלוצים",
}

def get_player_role(player_data: dict) -> str:
    """מחזיר תפקיד עיקרי, ואם אין — תפקיד ראשון מהרשימה."""
    primary = str(player_data.get('primary_role','') or '').strip()
    if primary and primary not in ('nan','none',''):
        return primary
    roles = safe_split(player_data.get('roles',''))
    return roles[0] if roles else ''


def divide_teams(selected_names: list, players_data: list,
                 formation: dict | None = None) -> tuple[list, list, list]:
    """
    חלוקה מאוזנת עם תמיכה בתבנית משחק.
    formation = {"שוערים": 1, "מגנים": 3, "קשרים": 3, "חלוצים": 2}
    מחזיר: t1, t2, missing_roles (תפקידים חסרים)
    """
    pool = []
    for name in selected_names:
        p = next((x for x in players_data if x['name'] == name), None)
        if p:
            role = get_player_role(p)
            group = ROLE_GROUPS.get(role, 'אחר')
            pool.append({
                'name': name,
                'score': get_player_score(p, players_data),
                'age': get_player_age(p),
                'role': role,
                'group': group,
            })

    # Snake Draft בסיסי — תמיד
    pool.sort(key=lambda x: x['score'], reverse=True)
    t1, t2 = [], []

    if not formation:
        # ללא תבנית — Snake Draft רגיל
        for i, player in enumerate(pool):
            block = i // 2
            pos_in_block = i % 2
            if block % 2 == 0:
                (t1 if pos_in_block == 0 else t2).append(player)
            else:
                (t2 if pos_in_block == 0 else t1).append(player)
    else:
        # חלוקה לפי תבנית:
        # 1. לכל קבוצת תפקידים — חלק לפי Snake Draft בתוך הקבוצה
        # 2. שחקנים עודפים/ללא תפקיד — Snake Draft לפי ציון
        used = set()
        for group, needed in formation.items():
            if needed == 0:
                continue
            group_players = [p for p in pool if p['group'] == group]
            # חלק שניים לכל צד (needed שחקנים בכל צד)
            for i, player in enumerate(group_players):
                side = i % 2  # 0=t1, 1=t2
                (t1 if side == 0 else t2).append(player)
                used.add(player['name'])

        # שחקנים שלא הוקצו — חלק לפי Snake Draft כדי לאזן מספרית
        remaining = [p for p in pool if p['name'] not in used]
        for i, player in enumerate(remaining):
            # תמיד תן לצד הקטן יותר
            if len(t1) <= len(t2):
                t1.append(player)
            else:
                t2.append(player)

    # בדיקת תפקידים חסרים
    missing = []
    if formation:
        for group, needed in formation.items():
            t1_count = sum(1 for p in t1 if p['group'] == group)
            t2_count = sum(1 for p in t2 if p['group'] == group)
            if t1_count < needed:
                missing.append(f"לבן חסר {needed-t1_count} {group}")
            if t2_count < needed:
                missing.append(f"שחור חסר {needed-t2_count} {group}")

    # אופטימיזציה: החלפות לשיפור איזון
    improved = True
    iterations = 0
    while improved and iterations < 200:
        improved = False
        iterations += 1
        for i in range(len(t1)):
            for j in range(len(t2)):
                diff_before = abs(balance_score(t1) - balance_score(t2))
                t1[i], t2[j] = t2[j], t1[i]
                diff_after = abs(balance_score(t1) - balance_score(t2))
                if diff_after < diff_before:
                    improved = True
                else:
                    t1[i], t2[j] = t2[j], t1[i]

    return t1, t2, missing



def build_field_html(t1: list, t2: list, players_data: list) -> str:
    """מגרש אחד — שתי קבוצות, כל אחת על המגרש המלא, כפתור מיתוג."""

    ROLE_POSITIONS = {
        "שוער":      {"x": 50, "y": 88},
        "בלם":       {"x": 50, "y": 74},
        "מגן ימין":  {"x": 22, "y": 66},
        "מגן שמאל":  {"x": 78, "y": 66},
        "קשר אחורי": {"x": 50, "y": 56},
        "אגף ימין":  {"x": 14, "y": 50},
        "אגף שמאל":  {"x": 86, "y": 50},
        "קשר קדמי":  {"x": 50, "y": 40},
        "חלוץ":      {"x": 50, "y": 18},
    }
    ROLE_PRIORITY = ["שוער","בלם","מגן ימין","מגן שמאל","קשר אחורי","אגף ימין","אגף שמאל","קשר קדמי","חלוץ"]

    def assign_positions(team, color):
        assigned = []
        used = set()
        for p in team:
            name = p['name']
            pd = next((x for x in players_data if x['name'] == name), {})
            roles = [r.strip() for r in str(pd.get('roles','')).split(',') if r.strip()]
            placed = False
            for role in roles:
                if role in ROLE_POSITIONS and role not in used:
                    pos = ROLE_POSITIONS[role]
                    assigned.append({"name": name, "x": pos["x"], "y": pos["y"], "role": role, "color": color, "score": p.get('score', 0)})
                    used.add(role)
                    placed = True
                    break
            if not placed:
                assigned.append({"name": name, "x": None, "y": None, "role": "?", "color": color, "score": p.get('score', 0)})
        remaining = [r for r in ROLE_PRIORITY if r not in used]
        unplaced = [p for p in assigned if p["x"] is None]
        for i, p in enumerate(unplaced):
            if i < len(remaining):
                pos = ROLE_POSITIONS[remaining[i]]
                p["x"], p["y"], p["role"] = pos["x"], pos["y"], remaining[i]
            else:
                p["x"] = 10 + (i * 15) % 80
                p["y"] = 95
        return assigned

    import json
    t1_placed = assign_positions(t1, "#4ade80")   # ירוק = לבן
    t2_placed = assign_positions(t2, "#f87171")   # אדום = שחור
    all_json  = json.dumps({"t1": t1_placed, "t2": t2_placed}, ensure_ascii=False)

    html = f"""
<div style="font-family:sans-serif;direction:rtl;padding:8px;">
  <div style="display:flex;gap:8px;margin-bottom:8px;justify-content:center;">
    <button onclick="show(1)" id="btn1"
      style="padding:5px 14px;border-radius:6px;border:2px solid #4ade80;background:#4ade80;color:#111;cursor:pointer;font-size:12px;font-weight:bold;">⚪ לבן</button>
    <button onclick="show(2)" id="btn2"
      style="padding:5px 14px;border-radius:6px;border:2px solid #f87171;background:#f87171;color:#111;cursor:pointer;font-size:12px;font-weight:bold;">⚫ שחור</button>
    <button onclick="show(0)" id="btn0"
      style="padding:5px 14px;border-radius:6px;border:2px solid #94a3b8;background:#334155;color:white;cursor:pointer;font-size:12px;">שתי קבוצות</button>
  </div>
  <div style="position:relative;max-width:360px;margin:0 auto;">
    <svg viewBox="0 0 360 480" style="width:100%;border-radius:8px;display:block;">
      <rect width="360" height="480" fill="#2d6a2d"/>
      <rect x="0"   y="0"   width="360" height="60"  fill="#286228" opacity="0.45"/>
      <rect x="0"   y="120" width="360" height="60"  fill="#286228" opacity="0.45"/>
      <rect x="0"   y="240" width="360" height="60"  fill="#286228" opacity="0.45"/>
      <rect x="0"   y="360" width="360" height="60"  fill="#286228" opacity="0.45"/>
      <rect x="12" y="12" width="336" height="456" fill="none" stroke="white" stroke-width="2"/>
      <line x1="12" y1="252" x2="348" y2="252" stroke="white" stroke-width="2"/>
      <circle cx="180" cy="252" r="42" fill="none" stroke="white" stroke-width="2"/>
      <circle cx="180" cy="252" r="3" fill="white"/>
      <rect x="112" y="12"  width="136" height="36" fill="none" stroke="white" stroke-width="2"/>
      <rect x="138" y="12"  width="84"  height="18" fill="none" stroke="white" stroke-width="2"/>
      <rect x="112" y="432" width="136" height="36" fill="none" stroke="white" stroke-width="2"/>
      <rect x="138" y="450" width="84"  height="18" fill="none" stroke="white" stroke-width="2"/>
      <path d="M112,48 A54,54 0 0,1 248,48"  fill="none" stroke="white" stroke-width="2"/>
      <path d="M112,432 A54,54 0 0,0 248,432" fill="none" stroke="white" stroke-width="2"/>
    </svg>
    <div id="players-layer" style="position:absolute;top:0;left:0;width:100%;height:100%;"></div>
  </div>
  <div id="tt" style="position:fixed;background:#1e293b;color:white;padding:5px 9px;
    border-radius:6px;font-size:11px;display:none;pointer-events:none;z-index:200;"></div>
</div>

<script>
var DATA = {all_json};
var active = 0;

function show(n) {{
  active = n;
  render();
}}

function render() {{
  var layer = document.getElementById('players-layer');
  layer.innerHTML = '';
  var players = active === 1 ? DATA.t1 :
                active === 2 ? DATA.t2 :
                DATA.t1.concat(DATA.t2);
  players.forEach(function(p) {{
    var el = document.createElement('div');
    el.style.cssText = [
      'position:absolute',
      'left:calc(' + p.x + '% - 20px)',
      'top:calc('  + p.y + '% - 20px)',
      'width:40px','height:40px','border-radius:50%',
      'background:' + p.color,
      'border:2px solid rgba(255,255,255,0.9)',
      'display:flex','flex-direction:column',
      'align-items:center','justify-content:center',
      'cursor:grab','user-select:none',
      'font-size:8px','color:#111','font-weight:bold',
      'text-align:center','line-height:1.2',
      'box-shadow:0 2px 6px rgba(0,0,0,0.5)','z-index:10'
    ].join(';');
    var short = p.name.split(' ')[0];
    el.innerHTML = '<span style="font-size:9px;">' + short + '</span>' +
                   '<span style="font-size:7px;opacity:0.85;">' + p.role + '</span>';
    el.addEventListener('mouseenter', function(e) {{
      var tt = document.getElementById('tt');
      tt.style.display='block';
      tt.innerHTML='<b>'+p.name+'</b><br>'+p.role+' | '+parseFloat(p.score).toFixed(1);
    }});
    el.addEventListener('mouseleave', function() {{ document.getElementById('tt').style.display='none'; }});
    addDrag(el, layer);
    layer.appendChild(el);
  }});
}}

function addDrag(el, layer) {{
  var ox=0, oy=0;
  function startMove(cx, cy) {{
    el.style.cursor='grabbing'; el.style.zIndex=100;
    var r=el.getBoundingClientRect(); ox=cx-r.left-20; oy=cy-r.top-20;
  }}
  function doMove(cx, cy) {{
    var lr=layer.getBoundingClientRect();
    el.style.left=Math.max(0,Math.min(lr.width-40, cx-lr.left-20))+'px';
    el.style.top =Math.max(0,Math.min(lr.height-40,cy-lr.top -20))+'px';
  }}
  function stopMove() {{ el.style.cursor='grab'; el.style.zIndex=10; }}
  el.addEventListener('mousedown',function(e){{ e.preventDefault(); startMove(e.clientX,e.clientY);
    var mm=function(e){{doMove(e.clientX,e.clientY);}};
    var mu=function(){{stopMove();document.removeEventListener('mousemove',mm);document.removeEventListener('mouseup',mu);}};
    document.addEventListener('mousemove',mm); document.addEventListener('mouseup',mu);
  }});
  el.addEventListener('touchstart',function(e){{ e.preventDefault(); startMove(e.touches[0].clientX,e.touches[0].clientY);
    var tm=function(e){{e.preventDefault();doMove(e.touches[0].clientX,e.touches[0].clientY);}};
    var tu=function(){{stopMove();document.removeEventListener('touchmove',tm);document.removeEventListener('touchend',tu);}};
    document.addEventListener('touchmove',tm,{{passive:false}}); document.addEventListener('touchend',tu);
  }},{{passive:false}});
}}

document.addEventListener('mousemove',function(e){{
  var tt=document.getElementById('tt');
  if(tt.style.display==='block'){{ tt.style.left=(e.clientX+12)+'px'; tt.style.top=(e.clientY-10)+'px'; }}
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
        required_cols = ['name', 'player_num', 'birth_year', 'rating', 'roles', 'primary_role', 'peer_ratings', 'active', 'win_points', 'phone', 'pin']
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

st.markdown(
    "<div class='main-title'>⚽ ניהול כדורגל 2026</div>"
    "<div class='sub-title'>נכתב ע״י ירון זריהן"
    " &nbsp;|&nbsp; <span style='font-size:11px;color:#4a5568;'>v2.0 · מרץ 2026</span></div>",
    unsafe_allow_html=True
)

# ---- טיפול בכניסה דרך קישור WhatsApp (query params) ----
import urllib.parse as _up
import math as _qm

def _clean_num_str(v):
    s = str(v or '').strip()
    if s.lower() in ('nan','none',''): return ''
    try:
        f = float(s)
        return '' if _qm.isnan(f) else str(int(f))
    except: return s

_qp_player = st.query_params.get("player", "")
_qp_pin    = st.query_params.get("pin", "")

if _qp_player and _qp_pin:
    _matched = next(
        (p for p in st.session_state.players
         if p['name'] == _qp_player
         and _clean_num_str(p.get('pin','')) == _qp_pin.strip()),
        None
    )
    if _matched:
        # הצג רק את טופס העריכה — ללא טאבים
        # חיווי שמירה מוצלחת
        if st.session_state.pop('wa_save_success', False):
            st.success(f"✅ הפרטים נשמרו בהצלחה!")
            st.markdown("<script>window.scrollTo(0,0);</script>", unsafe_allow_html=True)

        st.markdown(f"### ✏️ עדכון פרטים — {_matched['name']}")
        st.markdown(f"<div style='color:#94a3b8;font-size:13px;margin-bottom:12px;'>מחובר בתור: <b style='color:#60a5fa;'>{_matched['name']}</b></div>", unsafe_allow_html=True)

        # --- הצגת ציונים ---
        _sr = get_self_rating(_matched)
        _pr = get_peer_avg(_matched, st.session_state.players)
        _wr = get_player_score(_matched, st.session_state.players)
        def _sc(v): return "#22c55e" if v and v>=7 else "#f59e0b" if v and v>=5 else "#ef4444"
        def _bd(label, val):
            if val is None: return f"<div style='text-align:center;flex:1'><div style='font-size:11px;color:#94a3b8;'>{label}</div><div style='font-size:20px;color:#4a5568;'>—</div></div>"
            return f"<div style='text-align:center;flex:1'><div style='font-size:11px;color:#94a3b8;'>{label}</div><div style='font-size:20px;font-weight:bold;color:{_sc(val)};'>{val:.1f}</div></div>"
        st.markdown(
            f"<div style='display:flex;gap:8px;background:#1e293b;border-radius:10px;padding:12px;margin-bottom:14px;'>"
            f"{_bd('ציון אישי',_sr)}<div style='width:1px;background:#334155;'></div>"
            f"{_bd('קבוצתי',_pr)}<div style='width:1px;background:#334155;'></div>"
            f"{_bd('משוכלל',_wr if _wr>0 else None)}</div>",
            unsafe_allow_html=True
        )

        # --- טופס עריכה ---
        _pdata = _matched
        _auto_num = _clean_num_str(_pdata.get('player_num','')) or str(len(st.session_state.players))
        _existing_pin = _clean_num_str(_pdata.get('pin',''))

        st.markdown(f"<div style='color:#94a3b8;font-size:13px;'>מספר שחקן: <b style='color:#60a5fa;'>#{_auto_num}</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#94a3b8;font-size:13px;margin-bottom:8px;'>🔑 קוד: <b style='color:#60a5fa;'>{_existing_pin}</b></div>", unsafe_allow_html=True)

        with st.form("wa_edit_form"):
            _f_name  = st.text_input("שם מלא *", value=_pdata['name'])
            _raw_ph  = _pdata.get('phone','') or ''
            try:
                _ph_f = float(str(_raw_ph))
                _ph_s = '' if _qm.isnan(_ph_f) else ('0'+str(int(_ph_f)) if len(str(int(_ph_f)))==9 else str(int(_ph_f)))
            except: _ph_s = str(_raw_ph) if str(_raw_ph).lower() not in ('nan','none','') else ''
            _f_phone = st.text_input("מספר פלאפון *", value=_ph_s, placeholder="05X-XXXXXXX")
            _f_year  = st.number_input("שנת לידה *", 1950, 2015, int(float(_pdata.get('birth_year',1990) or 1990)))

            ROLES = ["שוער","בלם","מגן ימין","מגן שמאל","קשר אחורי","קשר קדמי","אגף ימין","אגף שמאל","חלוץ"]
            _ex_roles = safe_split(_pdata.get('roles',''))
            _f_roles = st.pills("תפקידים *", ROLES, selection_mode="multi", default=[r for r in _ex_roles if r in ROLES])

            _ex_rat  = _clean_num_str(_pdata.get('rating',''))
            _f_rate_str = st.pills("ציון עצמי (1-10) *",
                options=["—"]+[str(i) for i in range(1,11)],
                default=_ex_rat if _ex_rat else "—",
                selection_mode="single", key="wa_self_rate")
            _f_rate = int(_f_rate_str) if _f_rate_str and _f_rate_str != "—" else None

            _f_active = st.toggle("שחקן פעיל", value=is_player_active(_pdata), key="wa_active")

            # דירוג עמיתים
            st.markdown("---")
            st.markdown("**דירוג עמיתים:**")
            _other = sorted([p for p in st.session_state.players if p['name'] != _pdata['name']],
                           key=lambda p: p['name'].split()[0])
            _ex_peers = safe_get_json(_pdata.get('peer_ratings','{}'))
            _peer_res = {}
            if _other:
                with st.expander(f"דרג {len(_other)} שחקנים"):
                    for op in _other:
                        _pv = _ex_peers.get(op['name'])
                        try: _pd = str(int(float(_pv))) if _pv and float(_pv)>0 else "—"
                        except: _pd = "—"
                        _ps = st.pills(f"{op['name']} *",
                            options=["—"]+[str(i) for i in range(1,11)],
                            default=_pd, selection_mode="single",
                            key=f"wa_pr_{op['name']}_{_pdata['name']}")
                        _peer_res[op['name']] = int(_ps) if _ps and _ps!="—" else None

            if st.form_submit_button("💾 שמור", use_container_width=True):
                _errs = []
                if not _f_name.strip(): _errs.append("שם מלא")
                _ph = _f_phone.strip().replace('-','').replace(' ','')
                if not _ph:
                    _errs.append("מספר פלאפון — שדה חובה")
                elif not (_ph.isdigit() and len(_ph) in (9,10)):
                    _errs.append("מספר פלאפון — פורמט לא תקין (לדוגמה: 0521234567)")
                if not _f_roles: _errs.append("תפקידים")
                if not _f_rate: _errs.append("ציון עצמי")
                _unrated = [n for n,v in _peer_res.items() if v is None]
                if _unrated: _errs.append(f"דירוג חסר: {', '.join(_unrated)}")
                if _errs:
                    st.error(f"❌ חסר: {', '.join(_errs)}")
                else:
                    _clean_peers = {k:v for k,v in _peer_res.items() if v and v>0}
                    _new_entry = {
                        "name": _f_name.strip(), "player_num": _auto_num,
                        "birth_year": _f_year, "rating": _f_rate,
                        "roles": ",".join(_f_roles), "phone": _f_phone.strip(),
                        "peer_ratings": json.dumps(_clean_peers, ensure_ascii=False),
                        "active": str(_f_active), "pin": _existing_pin,
                        "win_points": _pdata.get('win_points',0),
                    }
                    _idx = next((i for i,x in enumerate(st.session_state.players) if x['name']==_pdata['name']), None)
                    if _idx is not None:
                        st.session_state.players[_idx] = _new_entry
                    if save_to_gsheets(st.session_state.players):
                        st.session_state.wa_save_success = True
                        st.rerun()
                    else:
                        st.error("❌ שגיאה בשמירה — נסה שוב")
        st.stop()  # אל תציג את שאר האפליקציה
    else:
        st.warning("⚠️ קישור לא תקין או קוד שגוי")
        st.query_params.clear()

# ---- handlers למאגר (query params) ----
_db_action = st.query_params.get("db_action", "")
if _db_action:
    _parts = _db_action.split("|")
    if len(_parts) == 2:
        _act, _pname = _parts
        if _act == "edit":
            st.session_state.edit_name = _pname
            st.session_state.nav_to_edit = True
        elif _act == "toggle":
            _idx = next((i for i,x in enumerate(st.session_state.players) if x['name']==_pname), None)
            if _idx is not None:
                _cur = str(st.session_state.players[_idx].get('active','True'))
                _new_active = str(_cur.lower() not in ('true','1'))
                st.session_state.players[_idx]['active'] = _new_active
                save_to_gsheets(st.session_state.players)
        elif _act == "delete":
            st.session_state.players = [x for x in st.session_state.players if x['name'] != _pname]
            save_to_gsheets(st.session_state.players)
    st.query_params.clear()
    st.rerun()

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

        # תבנית משחק
        with st.expander("⚽ תבנית משחק (אופציונלי)"):
            use_formation = st.toggle("הפעל תבנית", value=st.session_state.get('use_formation', False), key="use_formation")
            if use_formation:
                st.markdown("<small>הגדר כמה שחקנים מכל קבוצה בכל קבוצה</small>", unsafe_allow_html=True)
                fc1, fc2, fc3, fc4 = st.columns(4)
                with fc1: n_gk  = st.number_input("שוערים", 0, 3, st.session_state.get('f_gk',1),  key="f_gk")
                with fc2: n_def = st.number_input("מגנים",  0, 6, st.session_state.get('f_def',3), key="f_def")
                with fc3: n_mid = st.number_input("קשרים",  0, 6, st.session_state.get('f_mid',3), key="f_mid")
                with fc4: n_fwd = st.number_input("חלוצים", 0, 4, st.session_state.get('f_fwd',2), key="f_fwd")
                total = n_gk + n_def + n_mid + n_fwd
                st.caption(f"סה״כ: {total} שחקנים לכל קבוצה (={total*2} בסך הכל)")
                formation = {"שוערים": n_gk, "מגנים": n_def, "קשרים": n_mid, "חלוצים": n_fwd}
            else:
                formation = None

        divide_clicked = st.button("חלק קבוצות 🚀", use_container_width=True, disabled=count < 2)
        reshuffle_clicked = st.button("ערבב מחדש 🔀", use_container_width=True, disabled=count < 2)

        if divide_clicked or reshuffle_clicked:
            if selected_names:
                t1, t2, missing = divide_teams(selected_names, st.session_state.players, formation)
                st.session_state.t1 = t1
                st.session_state.t2 = t2
                st.session_state.teams_generated = True
                st.session_state.missing_roles = missing

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
            # הצג תפקידים חסרים
            missing = st.session_state.get('missing_roles', [])
            if missing:
                st.warning("⚠️ תפקידים חסרים: " + " | ".join(missing))

            # תצוגת קבוצות קומפקטית עם כפתורי החלפה
            t1 = st.session_state.t1
            t2 = st.session_state.t2
            avg1 = balance_score(t1)
            avg2 = balance_score(t2)
            age1 = sum(p['age'] for p in t1)/len(t1) if t1 else 0
            age2 = sum(p['age'] for p in t2)/len(t2) if t2 else 0

            avg1 = balance_score(t1); age1 = sum(p['age'] for p in t1)/len(t1) if t1 else 0
            avg2 = balance_score(t2); age2 = sum(p['age'] for p in t2)/len(t2) if t2 else 0

            def render_team(team, tk, header_bg, title):
                avg     = balance_score(team)
                age_avg = sum(p['age'] for p in team)/len(team) if team else 0
                # כותרת
                st.markdown(
                    f"<div style='background:{header_bg};border-radius:8px 8px 0 0;"
                    f"padding:10px 14px;text-align:center;font-weight:bold;font-size:17px;"
                    f"direction:rtl;margin-top:8px;'>"
                    f"{title} ({len(team)})"
                    f"<span style='font-size:15px;font-weight:normal;'> | רמה {avg:.1f} | גיל {age_avg:.1f}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                for i, p in enumerate(team):
                    pnum = next((x.get('player_num','') for x in st.session_state.players if x['name']==p['name']), '')
                    pnum_s = f"#{pnum}" if pnum else ""
                    sc = "#22c55e" if p['score'] >= 7 else "#f59e0b" if p['score'] >= 5 else "#94a3b8"
                    other_tk = "t2" if tk == "t1" else "t1"
                    ci, cb = st.columns([6, 1])
                    with ci:
                        st.markdown(
                            f"<div style='background:#1e293b;border-radius:6px;padding:9px 10px;"
                            f"direction:rtl;text-align:right;font-size:15px;line-height:1.4;margin-bottom:3px;'>"
                            f"<span style='color:#60a5fa;font-size:12px;margin-left:5px;'>{pnum_s}</span>"
                            f"<b>{p['name']}</b> "
                            f"<span style='color:#64748b;font-size:12px;font-weight:normal;'>({p['age']})</span>"
                            f"<span style='color:{sc};font-size:14px;font-weight:bold;float:left;'>{p['score']:.1f}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with cb:
                        if st.button("🔄", key=f"sw_{tk}_{i}", use_container_width=True):
                            moved = st.session_state[tk].pop(i)
                            st.session_state[other_tk].append(moved)
                            st.rerun()

            render_team(t1, "t1", "#1e3a5f", "⚪ לבן")
            render_team(t2, "t2", "#3a1e1e", "⚫ שחור")



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
    # בדיקת הרשאת מנהל
    if not st.session_state.get('admin_logged_in'):
        st.markdown("**🔒 גישה למנהל בלבד**")
        admin_input = st.text_input("קוד מנהל:", type="password",
                                    label_visibility="collapsed",
                                    placeholder="קוד מנהל")
        if st.button("כנס →", key="admin_login", use_container_width=True):
            if admin_input == "2026":
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("❌ קוד שגוי")
        st.stop()

    col_admin_out, _ = st.columns([1, 4])
    with col_admin_out:
        if st.button("🚪 התנתק", key="admin_logout"):
            del st.session_state['admin_logged_in']
            st.rerun()

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
            primary_role = str(p.get('primary_role','') or '')
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
                f"<div style='color:#94a3b8;font-size:12px;margin-bottom:4px;'>תפקידים: {roles}" + (f" | <b style='color:#f59e0b;'>⭐ {primary_role}</b>" if primary_role else "") + "</div>"
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

            import urllib.parse as _up
            import math as _m
            def _sp(v):
                """המר float ל-int string, טפל ב-NaN."""
                s = str(v or '').strip()
                if s.lower() in ('nan','none',''):
                    return ''
                try:
                    f = float(s)
                    return '' if _m.isnan(f) else str(int(f))
                except:
                    return s
            player_pin   = _sp(p.get('pin',''))
            player_phone = _sp(p.get('phone',''))
            app_url      = "https://my-football-app-maupcjcb9vmwxrthq7nduu.streamlit.app"
            toggle_label = "🔴" if is_active else "🟢"

            # כפתורי פעולה — HTML flex, שורה אחת, לא גולשת
            _pn_enc = _up.quote(p['name'])
            _wa_btn = ""
            if player_pin and player_phone:
                link   = f"{app_url}/?player={_pn_enc}&pin={player_pin}"
                wa_msg = f"שלום {p['name'].split()[0]}! קישור: {link} | קוד: {player_pin}"
                wa_url = f"https://wa.me/972{player_phone.lstrip('0').replace('-','')}?text={_up.quote(wa_msg)}"
                _wa_btn = (f"<a href='{wa_url}' target='_blank' style='background:#25d366;color:white;"
                           f"border-radius:6px;padding:6px 10px;text-decoration:none;font-size:14px;"
                           f"white-space:nowrap;text-align:center;'>💬</a>")

            # כפתור ערוך — st.button (חייב לעבוד)
            # toggle + delete + WA — HTML flex
            st.markdown(
                f"<div style='display:flex;gap:5px;margin:4px 0 2px;width:100%;box-sizing:border-box;'>"
                f"<a href='?db_action=toggle|{_pn_enc}' target='_top' style='background:#334155;color:white;border-radius:6px;"
                f"padding:8px 0;text-decoration:none;font-size:15px;flex:1;text-align:center;'>{toggle_label}</a>"
                f"{_wa_btn}"
                f"<a href='?db_action=delete|{_pn_enc}' target='_top' style='background:#7f1d1d;color:white;border-radius:6px;"
                f"padding:8px 0;text-decoration:none;font-size:15px;flex:1;text-align:center;'>🗑️</a>"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button("📝 ערוך", key=f"db_ed_{p['name']}", use_container_width=True):
                st.session_state.edit_name = p['name']
                st.session_state.nav_to_edit = True
                st.rerun()

            st.markdown("<hr style='border-color:#1e293b; margin:4px 0;'>", unsafe_allow_html=True)


# ============================================================
# TAB 3: עדכון / הרשמה
# ============================================================
with tab3:
    # ---- מצב לוגין ----
    # מנהל מחובר — גישה מלאה
    if st.session_state.get('admin_logged_in') and not st.session_state.get('tab3_logged_in'):
        st.session_state.tab3_logged_in = '__admin__'

    logged_in = st.session_state.get('tab3_logged_in', '')

    # באנר ניווט מהמאגר
    if st.session_state.pop('nav_to_edit', False):
        st.info(f"✏️ עורך: **{st.session_state.edit_name}** — גלול למטה לטופס")

    # אינדיקציה לאחר שמירה
    if st.session_state.get('show_save_success'):
        saved_name = st.session_state.pop('show_save_success')
        st.success(f"✅ {saved_name} נשמר בהצלחה!")
        st.markdown("<script>window.scrollTo(0,0);</script>", unsafe_allow_html=True)

    st.subheader("עדכון פרטי שחקן")

    # ---- בחירת שחקן לפי הרשאה ----
    if logged_in:
        if logged_in == '__admin__':
            st.success("👑 מצב מנהל — גישה מלאה")
            all_options = ["🆕 שחקן חדש"] + sorted([p['name'] for p in st.session_state.players])
            default_idx = (all_options.index(st.session_state.edit_name)
                          if st.session_state.edit_name in all_options else 0)
            choice = st.selectbox("בחר שחקן:", all_options, index=default_idx)
        else:
            st.success(f"👋 שלום, {logged_in}!")
            if st.button("🚪 התנתק", key="logout_btn"):
                del st.session_state['tab3_logged_in']
                st.rerun()
            choice = logged_in
    else:
        # לא מחובר — צריך להזין PIN
        st.markdown("**כניסה לעדכון פרטים:**")
        col_name, col_pin, col_go = st.columns([3, 2, 1])
        with col_name:
            login_name = st.selectbox("שם:", [""] + sorted([p['name'] for p in st.session_state.players]), label_visibility="collapsed")
        with col_pin:
            login_pin = st.text_input("PIN", placeholder="4 ספרות", max_chars=4, label_visibility="collapsed", type="password")
        with col_go:
            if st.button("כנס", use_container_width=True):
                if login_name and login_pin:
                    matched = next((p for p in st.session_state.players
                                    if p['name'] == login_name and str(p.get('pin','')) == login_pin), None)
                    if matched:
                        st.session_state.tab3_logged_in = matched['name']
                        st.session_state.edit_name = matched['name']
                        st.rerun()
                    else:
                        st.error("❌ שם או קוד שגוי")
        st.stop()
        choice = ""

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

    # תפקידים + תפקיד עיקרי — מחוץ לטופס כדי לאפשר עדכון דינמי
    ROLES_OUT = ["שוער", "בלם", "מגן ימין", "מגן שמאל", "קשר אחורי", "קשר קדמי", "אגף ימין", "אגף שמאל", "חלוץ"]
    existing_roles_out = safe_split(p_data.get('roles', '')) if p_data else []
    existing_primary_out = str(p_data.get('primary_role','') or '') if p_data else ''

    st.markdown("**תפקידים *** (בחר תפקידים, לאחר מכן בחר תפקיד עיקרי)")
    selected_roles = st.pills(
        "תפקידים",
        ROLES_OUT,
        selection_mode="multi",
        default=[r for r in existing_roles_out if r in ROLES_OUT],
        key=f"roles_out_{choice}",
        label_visibility="collapsed",
    )
    if selected_roles:
        _pr_default = existing_primary_out if existing_primary_out in selected_roles else selected_roles[0]
        selected_primary = st.selectbox(
            "⭐ תפקיד עיקרי:",
            options=selected_roles,
            index=selected_roles.index(_pr_default) if _pr_default in selected_roles else 0,
            key=f"primary_out_{choice}",
        )
    else:
        selected_primary = ""

    with st.form("edit_form", clear_on_submit=False):
        # מספר שחקן — מעל השם
        st.markdown(
            f"<div style='color:#94a3b8;font-size:14px;margin-bottom:2px;'>"
            f"מספר שחקן: <b style='color:#60a5fa;'>#{auto_num}</b></div>",
            unsafe_allow_html=True
        )

        # PIN — מיד מתחת למספר שחקן
        import math as _math

        def _clean_num(v):
            """המר float כמו 6536.0 ל-'6536', טפל ב-NaN."""
            if v is None or v == '':
                return ''
            s = str(v).strip()
            if s.lower() in ('nan', 'none', 'null'):
                return ''
            try:
                f = float(s)
                if _math.isnan(f):
                    return ''
                return str(int(f))
            except:
                return s

        existing_pin = _clean_num(p_data.get('pin','')) if p_data else ''
        if existing_pin:
            st.markdown(
                f"<div style='color:#94a3b8;font-size:13px;margin-bottom:8px;'>"
                f"🔑 קוד כניסה: <b style='color:#60a5fa;'>{existing_pin}</b></div>",
                unsafe_allow_html=True
            )
        else:
            existing_pin = ''
            if p_data:
                st.markdown(
                    "<div style='color:#f59e0b;font-size:12px;margin-bottom:8px;'>"
                    "🔑 קוד כניסה ייווצר בשמירה</div>",
                    unsafe_allow_html=True
                )
        auto_pin = existing_pin

        # שם מלא
        f_name = st.text_input(
            "שם מלא *",
            value=p_data['name'] if p_data else "",
            placeholder="הכנס שם מלא"
        )
        # טיפול בטוח בטלפון — המר 525623891.0 ל-'0525623891'
        _raw_phone = p_data.get('phone','') if p_data else ''
        try:
            _fp = float(str(_raw_phone or 0))
            import math as _m2
            if _m2.isnan(_fp) or _fp == 0:
                _safe_phone = ''
            else:
                # אם מספר ישראלי — הוסף 0 בהתחלה אם חסר
                _int_phone = str(int(_fp))
                _safe_phone = ('0' + _int_phone) if len(_int_phone) == 9 else _int_phone
        except:
            _s = str(_raw_phone or '').strip()
            _safe_phone = '' if _s.lower() in ('nan','none','') else _s
        f_phone = st.text_input(
            "מספר פלאפון *",
            value=_safe_phone,
            placeholder="05X-XXXXXXX"
        )

        # שנת לידה
        f_year = st.number_input(
            "שנת לידה *",
            min_value=1950,
            max_value=2015,
            value=int(p_data['birth_year']) if p_data else 1990
        )

        # תפקידים נלקחים מבחירה מחוץ לטופס
        f_roles = selected_roles
        f_primary_role = selected_primary

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
            _ph2 = f_phone.strip().replace('-','').replace(' ','')
            if not _ph2:
                errors.append("מספר פלאפון — שדה חובה")
            elif not (_ph2.isdigit() and len(_ph2) in (9,10)):
                errors.append("מספר פלאפון — פורמט לא תקין (לדוגמה: 0521234567)")
            if not f_roles:
                errors.append("תפקידים")
            if not f_rate:
                errors.append("ציון עצמי")
            unrated = [name for name, val in peer_res.items() if val is None]
            if unrated and other_players:
                errors.append(f"דירוג חסר: {', '.join(unrated)}")
            if errors:
                st.error(f"❌ שדות חובה חסרים: {', '.join(errors)}")
            else:
                roles_str = ",".join(f_roles) if f_roles else ""
                primary_str = f_primary_role if f_primary_role else (f_roles[0] if f_roles else "")
                # peer_res — שמור רק ערכים שדורגו (> 0), מחק None ו-0
                # peer_ratings = מה השחקן נתן לאחרים
                my_ratings = {k: v for k, v in peer_res.items() if v is not None and v > 0}

                import random as _random
                # צור PIN חדש רק לשחקן חדש
                new_pin = auto_pin if auto_pin else str(_random.randint(1000, 9999))
                new_entry = {
                    "name": f_name.strip(),
                    "player_num": auto_num,
                    "birth_year": f_year,
                    "rating": f_rate,
                    "roles": roles_str,
                    "primary_role": primary_str,
                    "peer_ratings": json.dumps(my_ratings, ensure_ascii=False),
                    "active": str(f_active),
                    "phone": f_phone.strip(),
                    "pin": new_pin,
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
                    st.session_state.edit_name = f_name.strip()
                    st.session_state.show_save_success = f_name.strip()
                    st.rerun()
                else:
                    st.error("❌ שגיאה בשמירה — נסה שוב")


# ============================================================
# ---- handler היסטוריה ----
_hist_action = st.query_params.get("hist", "")
if _hist_action:
    _ha_parts = _hist_action.split("|")
    if len(_ha_parts) == 2:
        _ha, _hdate = _ha_parts
        _hidx = next((i for i,g in enumerate(st.session_state.get('game_history',[])) if g['date']==_hdate), None)
        if _hidx is not None:
            _hgame = st.session_state.game_history[_hidx]
            if _ha in ("לבן","שחור"):
                st.session_state.game_history[_hidx]["winner"] = _ha
                _recalc_win_points(st.session_state.players, st.session_state.game_history)
                save_history_to_gsheets(st.session_state.game_history)
                save_to_gsheets(st.session_state.players)
            elif _ha == "cancel":
                st.session_state.game_history[_hidx]["winner"] = ""
                _recalc_win_points(st.session_state.players, st.session_state.game_history)
                save_history_to_gsheets(st.session_state.game_history)
                save_to_gsheets(st.session_state.players)
    st.query_params.clear()
    st.rerun()

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

            # כפתורי מנצח — HTML inline
            _hdate_enc = _up.quote(date_str)
            _w1_bg = "#2563eb" if winner == "לבן" else "#1e293b"
            _w2_bg = "#2563eb" if winner == "שחור" else "#1e293b"
            _cancel_btn = (
                f"<a href='?hist=cancel|{_hdate_enc}' style='background:#7f1d1d;color:white;"
                f"border-radius:6px;padding:6px 10px;text-decoration:none;font-size:13px;"
                f"white-space:nowrap;text-align:center;'>↩</a>"
            ) if winner else ""
            st.markdown(
                f"<div style='display:flex;gap:5px;margin:4px 0;'>"
                f"<a href='?hist=לבן|{_hdate_enc}' style='background:{_w1_bg};color:white;"
                f"border-radius:6px;padding:6px 12px;text-decoration:none;font-size:13px;"
                f"flex:1;text-align:center;white-space:nowrap;'>🏆 לבן</a>"
                f"<a href='?hist=שחור|{_hdate_enc}' style='background:{_w2_bg};color:white;"
                f"border-radius:6px;padding:6px 12px;text-decoration:none;font-size:13px;"
                f"flex:1;text-align:center;white-space:nowrap;'>🏆 שחור</a>"
                f"{_cancel_btn}"
                f"</div>",
                unsafe_allow_html=True
            )

            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # טבלת נקודות ניצחון
    st.markdown("---")
    st.markdown("### 🏅 טבלת נקודות ניצחון")

    history = st.session_state.get('game_history', [])

    pts_data = []
    for p in st.session_state.players:
        if not is_player_active(p):
            continue
        wins = safe_int(p.get("win_points"))
        games = sum(1 for g in history if p["name"] in g.get("team1", []) + g.get("team2", []))
        pct = round(wins / games * 100) if games > 0 else 0
        pts_data.append({"שם": p["name"], "ניצחונות": wins, "משחקים": games, "אחוז": pct})

    pts_data.sort(key=lambda x: (x["אחוז"], x["ניצחונות"]), reverse=True)

    if pts_data:
        max_wins = max(r["ניצחונות"] for r in pts_data) or 1
        for rank, row in enumerate(pts_data, 1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            bar_w = int(row["ניצחונות"] / max_wins * 100)
            pct_color = "#22c55e" if row["אחוז"] >= 60 else "#f59e0b" if row["אחוז"] >= 40 else "#94a3b8"
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>"
                f"<span style='width:26px;text-align:center;font-size:14px;'>{medal}</span>"
                f"<span style='width:100px;font-size:12px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;'>{row['שם']}</span>"
                f"<div style='flex:1;background:#1e293b;border-radius:4px;height:16px;'>"
                f"<div style='width:{bar_w}%;background:#3b82f6;border-radius:4px;height:16px;'></div>"
                f"</div>"
                f"<span style='font-size:12px;color:#60a5fa;font-weight:bold;white-space:nowrap;min-width:40px;text-align:left;'>"
                f"{row['ניצחונות']}/{row['משחקים']}</span>"
                f"<span style='font-size:12px;font-weight:bold;color:{pct_color};min-width:36px;text-align:left;'>"
                f"{row['אחוז']}%</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.caption("אין נתוני ניצחונות עדיין.")
