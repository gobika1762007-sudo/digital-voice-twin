"""
app.py  —  Digital Voice Twin
Twins: Teacher (Python), Tourist Guide (India), Cake Shop
"""

import os
import time
import uuid
import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import edge_tts
import asyncio

import teacher_twin
import tourist_twin
from emotion_engine import detect_emotion, get_voice_settings, format_reply

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

@app.after_request
def skip_ngrok_warning(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

TWIN_VOICES = {
    "teacher": "en-IN-NeerjaExpressiveNeural",
    "tourist": "en-IN-PrabhatNeural",
}
DEFAULT_VOICE = "en-IN-NeerjaNeural"

TWINS = {
    "teacher": teacher_twin,
    "tourist": tourist_twin,
}
DEFAULT_TWIN = "teacher"

DB_NAME = "chat.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

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
    conn.commit()
    conn.close()

init_db()

def get_date_time():
    from datetime import timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    return now.strftime("%d-%m-%Y"), now.strftime("%I:%M %p")

def save_message(user_id, twin, sender, message):
    date, time_str = get_date_time()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_history (user_id, twin, sender, message, date, time) VALUES (?,?,?,?,?,?)",
        (user_id, twin, sender, message, date, time_str),
    )
    conn.commit()
    conn.close()

def clean_for_tts(text):
    import re
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002600-\U000027BF"
        u"\U0001F900-\U0001F9FF"
        "]+", flags=re.UNICODE)
    result = emoji_pattern.sub("", text)
    result = re.sub(r"\[.*?\]", "", result)
    result = " ".join(result.split())
    return result.strip()

def generate_voice(text: str, twin_name: str, emotion: dict) -> bool:
    import platform
    text = clean_for_tts(text)
    if not text:
        return False
    if platform.system() == "Windows":
        os.makedirs("C:/tmp", exist_ok=True)
        output_path = "C:/tmp/reply.wav"
    else:
        output_path = "/tmp/reply.wav"
    try:
        voice = TWIN_VOICES.get(twin_name, DEFAULT_VOICE)
        rate  = emotion.get("rate",  "+0%")
        pitch = emotion.get("pitch", "+0Hz")

        async def _speak():
            communicate = edge_tts.Communicate(
                text=text, voice=voice, rate=rate, pitch=pitch,
            )
            await communicate.save(output_path)

        asyncio.run(_speak())
        print(f"🎙️  Voice: {voice} | Emotion: {emotion.get('label')} | Rate: {rate} | Pitch: {pitch}")
        return True
    except Exception as e:
        print(f"❌  Edge TTS error: {e}")
        return False

@app.before_request
def ensure_session():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/manifest.json")
def manifest():
    from flask import send_file
    return send_file("manifest.json", mimetype="application/manifest+json")

@app.route("/service-worker.js")
def service_worker():
    from flask import send_file, make_response
    response = make_response(send_file("service-worker.js", mimetype="application/javascript"))
    response.headers["Service-Worker-Allowed"] = "/"
    return response

@app.route("/chat_page")
def chat_page():
    twin = request.args.get("twin", DEFAULT_TWIN).lower()
    if twin not in TWINS:
        twin = DEFAULT_TWIN
    session["twin"] = twin
    return render_template("chat.html", twin=twin)

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

    frontend_history = data.get("history", [])
    groq_history = []
    for h in frontend_history[-10:]:
        role    = h.get("role", "user")
        content = str(h.get("content", ""))[:400]
        groq_history.append({"role": role, "content": content})

    image_b64  = data.get("image_base64", None)
    mime_type  = data.get("mime_type", "image/jpeg")
    language   = data.get("language", "tanglish")

    if twin_name == "teacher":
        bot_reply = twin_module.get_reply(user_msg, history=groq_history)
    elif twin_name == "tourist":
        bot_reply = twin_module.get_reply(
            user_msg,
            image_base64=image_b64 if image_b64 else None,
            mime_type=mime_type,
            language=language
        )
    else:
        bot_reply = twin_module.get_reply(user_msg)

    import json as _json
    is_teacher_json = False
    parsed = None
    if twin_name == "teacher":
        try:
            cleaned = bot_reply.replace("```json", "").replace("```", "").strip()
            parsed  = _json.loads(cleaned)
            if "steps" in parsed:
                is_teacher_json = True
        except Exception:
            pass

    if is_teacher_json:
        first_text = ""
        try:
            first_text = parsed["steps"][0].get("text", "")
        except Exception:
            pass
        if first_text:
            emotion = detect_emotion(first_text)
            generate_voice(first_text, twin_name, emotion)
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

    emotion      = detect_emotion(bot_reply)
    display_text = format_reply(bot_reply, emotion)
    generate_voice(bot_reply, twin_name, emotion)

    user_id = session["user_id"]
    save_message(user_id, twin_name, "user", user_msg)
    save_message(user_id, twin_name, "bot",  display_text)

    return jsonify({
        "reply":   display_text,
        "twin":    twin_name,
        "emotion": emotion.get("name",  "neutral"),
        "emoji":   emotion.get("emoji", "💬"),
        "label":   emotion.get("label", "Neutral"),
    })

@app.route("/dashboard")
def dashboard_redirect():
    from flask import redirect
    return redirect("http://localhost:5001/cake/orders")

@app.route("/cake")
def cake_page():
    shop_name = os.getenv("CAKE_SHOP_NAME", "Sweet Cake Shop")
    phone = os.getenv("TWILIO_PHONE_NUMBER", "")
    from flask import render_template_string
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🎂 {{ shop_name }}</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0d0d1a; color:#fff; font-family:'Segoe UI',sans-serif;
       min-height:100vh; display:flex; flex-direction:column;
       align-items:center; justify-content:center; padding:20px; }
.back-btn { position:fixed; top:16px; left:16px;
    background:transparent; color:#f9a8d4; border:1px solid #f9a8d4;
    padding:6px 14px; border-radius:8px; cursor:pointer;
    font-size:13px; text-decoration:none; }
.card { background:rgba(249,168,212,0.06); border:1px solid rgba(249,168,212,0.3);
        border-radius:24px; padding:40px 30px; text-align:center;
        max-width:340px; width:100%;
        box-shadow:0 0 40px rgba(249,168,212,0.1); }
.icon { font-size:72px; margin-bottom:16px; }
.shop-name { font-size:24px; font-weight:800; color:#f9a8d4; margin-bottom:8px; }
.tagline { font-size:13px; color:rgba(255,255,255,0.4); margin-bottom:36px; }
.label { font-size:11px; letter-spacing:2px; color:rgba(255,255,255,0.3);
         text-transform:uppercase; margin-bottom:12px; }
.phone-number { font-size:32px; font-weight:800; color:#fff;
                letter-spacing:2px; margin-bottom:8px; }
.call-btn { display:block; background:linear-gradient(135deg,#f9a8d4,#ec4899);
            color:#fff; text-decoration:none; padding:16px 32px;
            border-radius:50px; font-size:18px; font-weight:800;
            margin:24px auto 0; box-shadow:0 4px 20px rgba(249,168,212,0.4);
            transition:0.2s; }
.call-btn:hover { transform:scale(1.04); }
.note { font-size:11px; color:rgba(255,255,255,0.25); margin-top:20px; line-height:1.6; }
</style>
</head>
<body>
<a href="/" class="back-btn">← Back</a>
<div class="card">
    <div class="icon">🎂</div>
    <div class="shop-name">{{ shop_name }}</div>
    <div class="tagline">Fresh cakes made with love 🍰</div>
    <div class="label">Call us to order</div>
    <div class="phone-number">{{ phone }}</div>
    <a href="tel:{{ phone }}" class="call-btn">📞 Call & Order Now</a>
    <div class="note">
        Our AI assistant will take your order.<br>
        Available 24/7 · Fast delivery · Custom cakes
    </div>
</div>
</body>
</html>
""", shop_name=shop_name, phone=phone)

@app.route("/audio/reply.wav")
def serve_audio():
    import platform
    from flask import send_file
    path = "C:/tmp/reply.wav" if platform.system() == "Windows" else "/tmp/reply.wav"
    if os.path.exists(path):
        return send_file(path, mimetype="audio/wav")
    return "", 404

@app.route("/chat_history_data")
def chat_history_data():
    import time as _t
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()
    cur.execute("""
        SELECT twin, sender, message, date, time
        FROM chat_history ORDER BY date ASC, time ASC
    """)
    rows = cur.fetchall()
    conn.close()
    result = []
    i = 0
    while i < len(rows):
        twin, sender, message, date, time_str = rows[i]
        if sender == "user" and i+1 < len(rows) and rows[i+1][1] == "bot" and rows[i+1][0] == twin:
            try:
                from datetime import datetime as _dt
                dt = _dt.strptime(date + " " + time_str, "%d-%m-%Y %I:%M %p")
                ts = dt.timestamp()
            except Exception:
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

# ── Cake Shop Routes ──────────────────────────────────────────────────
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client as TwilioClient

TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUM   = os.getenv("TWILIO_PHONE_NUMBER")
OWNER_PHONE  = os.getenv("OWNER_PHONE", "")
SHOP_NAME    = os.getenv("CAKE_SHOP_NAME", "Sweet Cake Shop")
WHATSAPP_FROM = "whatsapp:+14155238886"
CAKE_DB      = "cake_orders.db"
cake_sessions = {}

CAKE_STEPS = ["name","cake_type","flavor","size","delivery_date","delivery_time","address","message"]
CAKE_QUESTIONS = {
    "name":          "May I know your good name please?",
    "cake_type":     "What type of cake? Birthday, wedding, anniversary, or custom cake?",
    "flavor":        "What flavor? Chocolate, vanilla, strawberry, butterscotch, red velvet, or black forest?",
    "size":          "What size? Half kg, one kg, one and a half kg, or two kg?",
    "delivery_date": "What is your preferred delivery date?",
    "delivery_time": "Morning, afternoon, or evening delivery?",
    "address":       "Please tell me your delivery address.",
    "message":       "Any special message on the cake? Say no message if not needed.",
}

CAKE_PRICES = {
    "pineapple cake":(300,600),"black forest cake":(320,630),"strawberry cake":(330,680),
    "mango cake":(380,750),"butter scotch cake":(330,650),"butterscotch cake":(330,650),
    "white forest cake":(360,730),"chocolate truffle cake":(350,700),"choco vanilla cake":(350,680),
    "choco chips cake":(350,700),"mix fruit cake":(360,720),"swiss chocolate cake":(360,700),
    "dutch exotic cake":(400,800),"rasmalai cake":(500,1000),"strawberry premium cake":(400,750),
    "mango premium cake":(400,800),"custom cake":(350,700),"birthday":(350,700),
    "chocolate":(350,700),"vanilla":(300,600),"strawberry":(330,680),
    "mango":(380,750),"butterscotch":(330,650),"black forest":(320,630),"pineapple":(300,600),
}

def _cake_init_db():
    conn = sqlite3.connect(CAKE_DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT UNIQUE,
        phone TEXT, name TEXT, cake_type TEXT, flavor TEXT, size TEXT,
        delivery_date TEXT, delivery_time TEXT, address TEXT, message TEXT,
        amount INTEGER DEFAULT 0, status TEXT DEFAULT 'pending',
        created_date TEXT, created_time TEXT)""")
    try: c.execute("ALTER TABLE orders ADD COLUMN amount INTEGER DEFAULT 0")
    except: pass
    conn.commit(); conn.close()

_cake_init_db()

def _cake_price(cake_type, flavor, size):
    size_l = (size or "").lower()
    if "2" in size_l or "two" in size_l: mult,base = 2.0,"one"
    elif "1" in size_l or "one" in size_l: mult,base = 1.0,"one"
    else: mult,base = 1.0,"half"
    ph,po = 350,700
    combined = ((flavor or "")+" "+(cake_type or "")).lower()
    for key,(p_half,p_one) in CAKE_PRICES.items():
        if key in combined: ph,po = p_half,p_one; break
    return int((po if base=="one" else ph)*mult)

def _cake_save(data):
    from datetime import timezone, timedelta
    IST = timezone(timedelta(hours=5,minutes=30))
    now = datetime.now(IST)
    date_str = now.strftime("%d-%m-%Y"); time_str = now.strftime("%I:%M %p")
    order_id = "ORD"+str(uuid.uuid4())[:6].upper()
    conn = sqlite3.connect(CAKE_DB)
    conn.execute("""INSERT INTO orders (order_id,phone,name,cake_type,flavor,size,
        delivery_date,delivery_time,address,message,amount,created_date,created_time)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (order_id,data.get("phone",""),data.get("name",""),data.get("cake_type",""),
         data.get("flavor",""),data.get("size",""),data.get("delivery_date",""),
         data.get("delivery_time",""),data.get("address",""),data.get("message",""),
         data.get("amount",0),date_str,time_str))
    conn.commit(); conn.close()
    return order_id

def _cake_ask(step, call_sid):
    r = VoiceResponse()
    g = Gather(input="speech", action=f"/cake/answer?step={step}&call_sid={call_sid}",
               method="POST", speech_timeout="3", language="en-IN",
               hints="chocolate vanilla strawberry birthday wedding kg morning afternoon evening")
    g.say(CAKE_QUESTIONS.get(step,"Please answer."), voice="Polly.Raveena", language="en-IN")
    r.append(g)
    r.redirect(f"/cake/answer?step={step}&call_sid={call_sid}&timeout=1", method="POST")
    return str(r)
@app.route("/chat_dashboard")
def chat_dashboard():
    return render_template("chat_dashboard.html")
@app.route("/cake/incoming", methods=["GET","POST"])
def cake_incoming():
    call_sid = request.values.get("CallSid", str(uuid.uuid4()))
    caller   = request.values.get("From","Unknown")
    cake_sessions[call_sid] = {"phone":caller,"step_index":0}
    r = VoiceResponse()
    g = Gather(input="speech", action=f"/cake/start?call_sid={call_sid}",
               method="POST", speech_timeout="2", language="en-IN")
    g.say(f"Hello! Welcome to {SHOP_NAME}! I am your cake ordering assistant. Say yes to place an order.",
          voice="Polly.Raveena", language="en-IN")
    r.append(g)
    r.redirect(f"/cake/start?call_sid={call_sid}&auto=1", method="POST")
    return app.response_class(str(r), mimetype="text/xml")

@app.route("/cake/start", methods=["GET","POST"])
def cake_start():
    call_sid = request.values.get("call_sid","")
    speech   = request.values.get("SpeechResult","").lower()
    if "no" in speech and "yes" not in speech:
        r = VoiceResponse()
        r.say("No problem! Call us again when ready. Thank you! Bye!", voice="Polly.Raveena", language="en-IN")
        r.hangup()
        return app.response_class(str(r), mimetype="text/xml")
    if call_sid not in cake_sessions:
        cake_sessions[call_sid] = {"phone":"Unknown","step_index":0}
    cake_sessions[call_sid]["step_index"] = 0
    return app.response_class(_cake_ask(CAKE_STEPS[0], call_sid), mimetype="text/xml")

@app.route("/cake/answer", methods=["GET","POST"])
def cake_answer():
    call_sid = request.values.get("call_sid","")
    step     = request.values.get("step","name")
    speech   = request.values.get("SpeechResult","").strip()
    timeout  = request.values.get("timeout","0")
    if call_sid not in cake_sessions:
        cake_sessions[call_sid] = {"phone":"Unknown","step_index":0}
    sess = cake_sessions[call_sid]
    if speech and timeout=="0": sess[step] = speech
    elif timeout=="1" and step not in sess: sess[step] = "Not specified"
    current_idx = CAKE_STEPS.index(step) if step in CAKE_STEPS else 0
    next_idx = current_idx + 1
    if next_idx < len(CAKE_STEPS):
        next_step = CAKE_STEPS[next_idx]
        acks = {"name":f"Thank you {speech}! ","cake_type":"Great! ","flavor":"Wonderful! ",
                "size":"Perfect! ","delivery_date":"Noted! ","delivery_time":"Sure! ","address":"Got it! "}
        ack = acks.get(step,"") if speech else ""
        r = VoiceResponse()
        g = Gather(input="speech", action=f"/cake/answer?step={next_step}&call_sid={call_sid}",
                   method="POST", speech_timeout="3", language="en-IN",
                   hints="chocolate vanilla strawberry birthday kg morning afternoon evening")
        g.say(ack+CAKE_QUESTIONS[next_step], voice="Polly.Raveena", language="en-IN")
        r.append(g)
        r.redirect(f"/cake/answer?step={next_step}&call_sid={call_sid}&timeout=1", method="POST")
        return app.response_class(str(r), mimetype="text/xml")
    else:
        name=sess.get("name",""); cake_type=sess.get("cake_type","")
        flavor=sess.get("flavor",""); size=sess.get("size","")
        del_date=sess.get("delivery_date",""); del_time=sess.get("delivery_time","")
        amount = _cake_price(cake_type, flavor, size)
        sess["amount"] = amount
        order_id = _cake_save(sess)
        r = VoiceResponse()
        r.say(f"Thank you {name}! Order placed. {size} {flavor} {cake_type}. "
              f"Delivery on {del_date} {del_time}. Total Rupees {amount}. "
              f"Order ID {' '.join(order_id)}. We will call to confirm. "
              f"Thank you for choosing {SHOP_NAME}! Have a sweet day!",
              voice="Polly.Raveena", language="en-IN")
        r.hangup()
        try:
            tc = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
            phone = sess.get("phone","")
            if phone and phone != "Unknown":
                tc.messages.create(
                    body=(f"🎂 {SHOP_NAME}\nOrder Received!\nID: {order_id}\n"
                          f"Cake: {size} {flavor} {cake_type}\nAmount: Rs.{amount}/-\n"
                          f"Delivery: {del_date} {del_time}\nWe will call to confirm!"),
                    from_=TWILIO_NUM, to=phone)
            if OWNER_PHONE:
                tc.messages.create(
                    body=(f"🎂 NEW ORDER - {SHOP_NAME}\nID: {order_id}\n"
                          f"Customer: {name}\nPhone: {phone}\n"
                          f"Cake: {size} {flavor} {cake_type}\nAmount: Rs.{amount}/-\n"
                          f"Delivery: {del_date} {del_time}\nAddress: {sess.get('address','')}"),
                    from_=WHATSAPP_FROM, to=f"whatsapp:{OWNER_PHONE}")
        except Exception as e:
            print(f"SMS/WA error: {e}")
        if call_sid in cake_sessions: del cake_sessions[call_sid]
        return app.response_class(str(r), mimetype="text/xml")

if __name__ == "__main__":
    init_db()
    print("─" * 40)
    print("🚀  Digital Voice Twin is starting...")
    print(f"    Twins loaded: {', '.join(TWINS.keys())}")
    print("─" * 40)
    app.run(host="0.0.0.0", debug=False, port=5000)