"""
app.py  —  Digital Voice Twin
==============================
Fixed version:
  - Secrets loaded from .env (never hardcoded)
  - Twin selected per-user via Flask session (no global variable)
  - Single /chat route handles all three twins
  - Admin SQL matches actual DB schema
  - No duplicate functions
"""

import os
import time
import uuid
import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
# openai removed - using dataset only
import edge_tts
import asyncio

# ── Import each twin module ───────────────────────────────────────────────────
import gobika_twin
import teacher_twin
import warden_twin
import shop_twin
import coach_twin

# ── Import emotion engine ─────────────────────────────────────────────────────
from emotion_engine import detect_emotion, get_voice_settings, format_reply

# ── Load secrets from .env ────────────────────────────────────────────────────
load_dotenv()
# openai key not needed

GOBIKA_EMAIL       = os.getenv("GOBIKA_EMAIL")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
IMAP_SERVER        = "imap.gmail.com"
SMTP_SERVER        = "smtp.gmail.com"

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# ── Edge TTS voices per twin ─────────────────────────────────────────────────
TWIN_VOICES = {
    "gobika":  "en-IN-NeerjaNeural",
    "teacher": "en-IN-NeerjaExpressiveNeural",
    "warden":  "en-IN-PrabhatNeural",
    "shop":    "en-IN-NeerjaNeural",
    "coach":   "en-IN-PrabhatNeural",
}
DEFAULT_VOICE = "en-IN-NeerjaNeural"

# ── Twin registry ─────────────────────────────────────────────────────────────
# Maps twin name → its module. Adding a new twin = add one line here.
TWINS = {
    "gobika":  gobika_twin,
    "teacher": teacher_twin,
    "warden":  warden_twin,
    "shop":    shop_twin,
    "coach":   coach_twin,
}
DEFAULT_TWIN = "teacher"

# ── Database ──────────────────────────────────────────────────────────────────
DB_NAME = "chat.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  TEXT,
            twin     TEXT,
            sender   TEXT,
            message  TEXT,
            date     TEXT,
            time     TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_updates (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            twin     TEXT,
            content  TEXT,
            date     TEXT,
            time     TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS gobika_messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT,
            user_msg     TEXT,
            gobika_reply TEXT,
            date         TEXT,
            time         TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_date_time():
    now = datetime.now()
    return now.strftime("%d-%m-%Y"), now.strftime("%I:%M %p")

def save_message(user_id, twin, sender, message):
    date, time = get_date_time()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_history (user_id, twin, sender, message, date, time) VALUES (?,?,?,?,?,?)",
        (user_id, twin, sender, message, date, time),
    )
    conn.commit()
    conn.close()

# ── TTS voice generation with emotion ────────────────────────────────────────
def generate_voice(text: str, twin_name: str, emotion: dict) -> bool:
    output_path = "static/reply.wav"
    try:
        voice    = TWIN_VOICES.get(twin_name, DEFAULT_VOICE)
        rate     = emotion.get("rate",  "+0%")
        pitch    = emotion.get("pitch", "0Hz")

        async def _speak():
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch,
            )
            await communicate.save(output_path)

        asyncio.run(_speak())
        print(f"🎙️  Voice: {voice} | Emotion: {emotion.get('label')} | Rate: {rate} | Pitch: {pitch}")
        return True
    except Exception as e:
        print(f"❌  Edge TTS error: {e}")
        return False

# ── Before every request: ensure user has a session ID ───────────────────────
@app.before_request
def ensure_session():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat_page")
def chat_page():
    twin = request.args.get("twin", DEFAULT_TWIN).lower()
    if twin not in TWINS:
        twin = DEFAULT_TWIN
    session["twin"] = twin
    # twin name-ஐ directly template-ku pass பண்றோம்
    return render_template("chat.html", twin=twin)

# ── Single unified chat route ─────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    data     = request.json
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"reply": "Kuraiya sollunga, puriyala!"}), 400

    twin_name   = data.get("twin") or session.get("twin", DEFAULT_TWIN)
    twin_name   = twin_name.lower().strip()
    twin_module = TWINS.get(twin_name, teacher_twin)
    session["twin"] = twin_name

    # Gobika — check if needs human reply
    if twin_name == "gobika":
        needs_human = any(t in user_msg.lower() for t in HUMAN_TRIGGERS)
        if needs_human:
            import time as _time
            msg_id = str(int(_time.time() * 1000))
            # Get AI reply (used only if Gobika doesn't reply in time)
            ai_reply = twin_module.get_reply(user_msg)
            gobika_queue.append({
                "id":          msg_id,
                "twin":        twin_name,
                "user_msg":    user_msg,
                "ai_reply":    ai_reply,
                "human_reply": None,
                "status":      "pending",
                "ts":          _time.time()
            })
            # Save to chat history too
            chat_history.append({
                "twin":      twin_name,
                "user_msg":  user_msg,
                "bot_reply": ai_reply,
                "ts":        _time.time()
            })
            user_id = session["user_id"]
            save_message(user_id, twin_name, "user", user_msg)
            # Send waiting message — no AI reply yet
            waiting_msg = "Gobika-ku message போச்சு da! Reply-ku konjam wait pannunga... 🌸"
            return jsonify({
                "reply":       waiting_msg,
                "twin":        twin_name,
                "emotion":     "thinking",
                "emoji":       "🤔",
                "label":       "Waiting",
                "needs_human": True,
                "msg_id":      msg_id,
                "ai_reply":    ai_reply,
                "timeout_sec": 120,
            })

    # Get reply from twin
    bot_reply = twin_module.get_reply(user_msg)

    # Teacher twin — JSON steps return பண்ணும், emotion skip
    import json as _json
    is_teacher_json = False
    if twin_name == "teacher":
        try:
            cleaned = bot_reply.replace("```json","").replace("```","").strip()
            parsed  = _json.loads(cleaned)
            if "steps" in parsed:
                is_teacher_json = True
        except:
            pass

    if is_teacher_json:
        # JSON steps — voice for first step speak text
        first_speak = ""
        try:
            first_speak = parsed["steps"][0].get("speak", "")
        except:
            pass
        if first_speak:
            emotion = detect_emotion(first_speak)
            generate_voice(first_speak, twin_name, emotion)
        user_id = session["user_id"]
        save_message(user_id, twin_name, "user", user_msg)
        save_message(user_id, twin_name, "bot",  bot_reply)
        return jsonify({
            "reply":   bot_reply,
            "twin":    twin_name,
            "emotion": "neutral",
            "emoji":   "💬",
            "label":   "Neutral",
        })

    # Normal twins — emotion detect + format
    emotion      = detect_emotion(bot_reply)
    display_text = format_reply(bot_reply, emotion)

    # Generate voice with emotion tone
    generate_voice(bot_reply, twin_name, emotion)

    # Save to DB
    user_id = session["user_id"]
    save_message(user_id, twin_name, "user", user_msg)
    save_message(user_id, twin_name, "bot",  display_text)

    # Save to global chat history
    import time as _t
    chat_history.append({
        "twin":      twin_name,
        "user_msg":  user_msg,
        "bot_reply": display_text,
        "ts":        _t.time()
    })

    return jsonify({
        "reply":   display_text,
        "twin":    twin_name,
        "emotion": emotion.get("name",  "neutral"),
        "emoji":   emotion.get("emoji", "💬"),
        "label":   emotion.get("label", "Neutral"),
    })

# ── Admin panel ───────────────────────────────────────────────────────────────

@app.route("/admin")
def admin():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Columns match the actual schema: user_id, twin, sender, message, date, time
    c.execute("""
        SELECT user_id, twin, sender, message, date, time
        FROM chat_history
        ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()

    # Group by user_id for the template
    chats = {}
    for user_id, twin, sender, message, date, time in rows:
        if user_id not in chats:
            chats[user_id] = []
        chats[user_id].append({
            "twin":    twin,
            "sender":  sender,
            "message": message,
            "date":    date,
            "time":    time,
        })
    return render_template("admin.html", chats=chats)

@app.route("/admin_history")
def admin_history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT sender, message, date, time
        FROM chat_history
        ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return jsonify(rows)

@app.route("/admin_history_by_date")
def admin_history_by_date():
    selected_date = request.args.get("date")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if selected_date:
        c.execute(
            "SELECT sender, message, time FROM chat_history WHERE date=? ORDER BY id ASC",
            (selected_date,),
        )
    else:
        c.execute("SELECT sender, message, time FROM chat_history ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return jsonify(rows)

# ── Dev helper: test voice generation ────────────────────────────────────────
@app.route("/test_voice/<twin_name>")
def test_voice(twin_name):
    twin_module = TWINS.get(twin_name)
    if not twin_module:
        return jsonify({"error": f"Unknown twin: {twin_name}"}), 404
    ok = generate_voice("Vanakkam! Testing voice.", twin_module.get_voice_file())
    return jsonify({"status": "ok" if ok else "failed", "twin": twin_name})


# ── Gobika real-time dashboard routes ────────────────────────────────────────


# ── Global Chat History (all twins) ─────────────────────────────────────────
chat_history = []  # {twin, user_msg, bot_reply, ts}

# ── Gobika Real-time Human Reply System ──────────────────────────────────────
gobika_queue = []

HUMAN_TRIGGERS = [
    # Meet / contact
    "meet", "appointment", "call", "contact", "talk to",
    "real gobika", "phone", "number", "insta", "address",
    "meet pana", "meet pannalam", "pesanum", "pesalama",
    # Timing questions
    "pm", "am", "time", "timing", "eppo", "eppadi",
    "nalaki", "tomorrow", "today", "naal", "manikku",
    "ok va", "ok da", "okva", "okda", "confirm",
    "available", "free ya", "free da", "schedule",
    "evening", "morning", "night", "afternoon",
    "weekend", "sunday", "saturday", "monday",
    "come", "varuva", "varuviya", "varalama",
]

@app.route("/daily_update_post", methods=["POST"])
def daily_update_post():
    data   = request.json
    twin   = data.get("twin", "gobika").lower()
    update = data.get("update", "").strip()
    if not update:
        return jsonify({"error": "empty"}), 400
    date, time = get_date_time()
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()
    cur.execute("INSERT INTO daily_updates (twin, content, date, time) VALUES (?,?,?,?)", (twin, update, date, time))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/daily_updates_get")
def daily_updates_get():
    twin = request.args.get("twin", "gobika")
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()
    cur.execute("SELECT twin, content, date, time FROM daily_updates WHERE twin=? ORDER BY date DESC, time DESC LIMIT 50", (twin,))
    rows = cur.fetchall()
    conn.close()
    result = [{"twin":r[0], "update":r[1], "date":r[2], "time":r[3]} for r in rows]
    return jsonify(result)

@app.route("/daily_update_latest")
def daily_update_latest():
    twin = request.args.get("twin", "gobika")
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()
    cur.execute("SELECT content FROM daily_updates WHERE twin=? ORDER BY date DESC, time DESC LIMIT 1", (twin,))
    row = cur.fetchone()
    conn.close()
    return jsonify({"update": row[0] if row else None})

@app.route("/chat_history_data")
def chat_history_data():
    # Read from SQLite DB — persistent across restarts
    import time as _t
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()
    cur.execute("""
        SELECT twin, sender, message, date, time
        FROM chat_history
        ORDER BY date ASC, time ASC
    """)
    rows = cur.fetchall()
    conn.close()

    # Group user+bot pairs
    result = []
    i = 0
    while i < len(rows):
        twin, sender, message, date, time_str = rows[i]
        if sender == 'user' and i+1 < len(rows) and rows[i+1][1] == 'bot' and rows[i+1][0] == twin:
            # Parse datetime to timestamp
            try:
                from datetime import datetime as _dt
                # Format: "10-03-2026" "01:36 PM"
                dt = _dt.strptime(date + ' ' + time_str, '%d-%m-%Y %I:%M %p')
                ts = dt.timestamp()
            except:
                ts = _t.time()
            result.append({
                "twin":      twin,
                "user_msg":  message,
                "bot_reply": rows[i+1][2],
                "ts":        ts
            })
            i += 2
        else:
            i += 1

    return jsonify(result)

GOBIKA_PIN = os.getenv("GOBIKA_PIN", "1234")  # .env la change pannunga

@app.route("/gobika_update")
def gobika_update():
    return render_template("gobika_update.html")

@app.route("/gobika_update_verify", methods=["POST"])
def gobika_update_verify():
    pin = request.json.get("pin", "")
    if pin == GOBIKA_PIN:
        session["gobika_auth"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401

@app.route("/gobika_dashboard")
def gobika_dashboard():
    return render_template("gobika_dashboard.html")

@app.route("/gobika_pending", methods=["GET"])
def gobika_pending():
    return jsonify(gobika_queue)

@app.route("/gobika_reply", methods=["POST"])
def gobika_reply():
    data   = request.json
    msg_id = data.get("id")
    reply  = data.get("reply", "").strip()
    if not reply:
        return jsonify({"error": "empty"}), 400
    for item in gobika_queue:
        if item["id"] == msg_id:
            item["human_reply"] = reply
            item["status"]      = "answered"
            emotion = detect_emotion(reply)
            generate_voice(reply, "gobika", emotion)
            return jsonify({"ok": True, "reply": reply})
    return jsonify({"error": "not found"}), 404

# ── Start ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("─" * 40)
    print("🚀  Digital Voice Twin is starting...")
    print(f"    Twins loaded: {', '.join(TWINS.keys())}")
    print("─" * 40)
    app.run(debug=False, port=5000)