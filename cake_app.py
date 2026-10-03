"""
cake_app.py — Cake Shop Voice Order System
==========================================
Twilio phone call → AI conversation → Order saved to DB
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from flask import Flask, request, Response, render_template_string
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)

# Allow ngrok headers
@app.after_request
def add_headers(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# ── Config ────────────────────────────────────────────────────────────
TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUM   = os.getenv("TWILIO_PHONE_NUMBER")
SHOP_NAME    = os.getenv("CAKE_SHOP_NAME", "Sweet Cake Shop")
OWNER_PHONE  = os.getenv("OWNER_PHONE", "")
WHATSAPP_FROM = "whatsapp:+14155238886"  # Twilio sandbox number
DB_NAME      = "cake_orders.db"

IST = timezone(timedelta(hours=5, minutes=30))

# ── Database ──────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id     TEXT UNIQUE,
            phone        TEXT,
            name         TEXT,
            cake_type    TEXT,
            flavor       TEXT,
            size         TEXT,
            delivery_date TEXT,
            delivery_time TEXT,
            address      TEXT,
            message      TEXT,
            amount       INTEGER DEFAULT 0,
            status       TEXT DEFAULT 'pending',
            created_date TEXT,
            created_time TEXT
        )
    """)
    # Add amount column if not exists (for existing DBs)
    try:
        c.execute("ALTER TABLE orders ADD COLUMN amount INTEGER DEFAULT 0")
        conn.commit()
    except:
        pass
    conn.commit()
    conn.close()

init_db()

def get_ist():
    now = datetime.now(IST)
    return now.strftime("%d-%m-%Y"), now.strftime("%I:%M %p")

def save_order(data: dict):
    date, time_str = get_ist()
    order_id = "ORD" + str(uuid.uuid4())[:6].upper()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO orders
        (order_id, phone, name, cake_type, flavor, size,
         delivery_date, delivery_time, address, message, amount, created_date, created_time)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        order_id,
        data.get("phone", ""),
        data.get("name", ""),
        data.get("cake_type", ""),
        data.get("flavor", ""),
        data.get("size", ""),
        data.get("delivery_date", ""),
        data.get("delivery_time", ""),
        data.get("address", ""),
        data.get("message", ""),
        data.get("amount", 0),
        date, time_str
    ))
    conn.commit()
    conn.close()
    return order_id

# ── Price List ───────────────────────────────────────────────────────
CAKE_PRICES = {
    # Regular Cakes — (half_kg, one_kg)
    "pineapple cake":           (300, 600),
    "black forest cake":        (320, 630),
    "strawberry cake":          (330, 680),
    "mango cake":               (380, 750),
    "butter scotch cake":       (330, 650),
    "butterscotch cake":        (330, 650),
    "white forest cake":        (360, 730),
    "chocolate truffle cake":   (350, 700),
    "choco vanilla cake":       (350, 680),
    "choco chips cake":         (350, 700),
    "mix fruit cake":           (360, 720),
    "caramel mix fruit cake":   (380, 780),
    "swiss chocolate cake":     (360, 700),
    "dutch exotic cake":        (400, 800),
    # Premium Cakes
    "exotic black forest cake": (360, 700),
    "pineapple delight cake":   (350, 700),
    "royal mix fruit cake":     (380, 750),
    "premium mix fruit cake":   (425, 800),
    "rasmalai cake":            (500, 1000),
    "strawberry premium cake":  (400, 750),
    "mango premium cake":       (400, 800),
    # Generic fallback
    "chocolate":                (350, 700),
    "vanilla":                  (300, 600),
    "strawberry":               (330, 680),
    "mango":                    (380, 750),
    "butterscotch":             (330, 650),
    "black forest":             (320, 630),
    "pineapple":                (300, 600),
    "rasmalai":                 (500, 1000),
}

def calculate_price(cake_type: str, flavor: str, size: str) -> int:
    """Calculate price based on cake type, flavor and size"""
    # Determine size
    size_lower = size.lower()
    if "2" in size_lower or "two" in size_lower:
        multiplier = 2.0
        base_size = "one_kg"
    elif "1.5" in size_lower or "one and half" in size_lower or "one half" in size_lower:
        multiplier = 1.5
        base_size = "one_kg"
    elif "1" in size_lower or "one kg" in size_lower:
        multiplier = 1.0
        base_size = "one_kg"
    else:
        multiplier = 1.0
        base_size = "half_kg"

    # Find price
    search_terms = []
    combined = (flavor + " " + cake_type).lower().strip()
    search_terms.append(combined)
    search_terms.append(cake_type.lower().strip())
    search_terms.append(flavor.lower().strip())

    price_half = 350  # default
    price_one  = 700

    for term in search_terms:
        for key, (p_half, p_one) in CAKE_PRICES.items():
            if key in term or term in key:
                price_half = p_half
                price_one  = p_one
                break

    if base_size == "half_kg":
        return int(price_half * multiplier)
    else:
        return int(price_one * multiplier)

# ── Session store (in-memory) ─────────────────────────────────────────
# Key: call_sid, Value: order dict
sessions = {}

STEPS = ["name", "cake_type", "flavor", "size", "delivery_date", "delivery_time", "address", "message"]

QUESTIONS = {
    "name":          "Aww, how sweet! May I know your good name please?",
    "cake_type":     "Lovely! So what is the occasion? Is it a birthday, wedding, anniversary, or any special celebration?",
    "flavor":        "Ooh exciting! What flavor would make you happy? We have chocolate, vanilla, strawberry, butterscotch, red velvet, and black forest. All freshly baked!",
    "size":          "Perfect choice! Now, how big should the cake be? We have half kg, one kg, one and a half kg, or two kg.",
    "delivery_date": "Great! When would you like us to deliver? Please tell me the date.",
    "delivery_time": "And what time works best for you? Morning, afternoon, or evening?",
    "address":       "Almost done! Please tell me your delivery address so we can bring the cake right to your door!",
    "message":       "Oh how fun! Would you like us to write a special message on the cake? Say it out loud and we will make it happen! Or just say no message if you prefer.",
}

def tts(text):
    """Create TwiML voice response with friendly female voice"""
    r = VoiceResponse()
    r.say(text, voice="Polly.Raveena", language="en-IN")
    return r

def ask_question(step, call_sid):
    """Ask current step question and gather speech"""
    r = VoiceResponse()
    question = QUESTIONS.get(step, "Please say your answer.")
    gather = Gather(
        input="speech",
        action=f"/cake/answer?step={step}&call_sid={call_sid}",
        method="POST",
        speech_timeout="3",
        language="en-IN",
        hints="chocolate vanilla strawberry birthday wedding anniversary kg delivery morning afternoon evening",
    )
    gather.say(question, voice="Polly.Raveena", language="en-IN")
    r.append(gather)
    # Timeout fallback
    r.redirect(f"/cake/answer?step={step}&call_sid={call_sid}&timeout=1", method="POST")
    return str(r)

# ── Routes ────────────────────────────────────────────────────────────

@app.route("/cake/incoming", methods=["GET", "POST"])
def incoming_call():
    """Handle incoming call — welcome message"""
    # Skip Twilio signature validation for development
    call_sid = request.values.get("CallSid", str(uuid.uuid4()))
    caller   = request.values.get("From", "Unknown")

    # Init session
    sessions[call_sid] = {
        "phone": caller,
        "step_index": 0,
    }

    r = VoiceResponse()
    gather = Gather(
        input="speech",
        action=f"/cake/start?call_sid={call_sid}",
        method="POST",
        speech_timeout="2",
        language="en-IN",
    )
    gather.say(
        f"Hello! So lovely to hear from you! Welcome to {SHOP_NAME}! "
        "I am your cake ordering assistant. "
        "I will help you place your order. "
        "Please say yes to continue, or no to call back later.",
        voice="Polly.Raveena",
        language="en-IN"
    )
    r.append(gather)
    r.redirect(f"/cake/start?call_sid={call_sid}&auto=1", method="POST")
    return Response(str(r), mimetype="text/xml")


@app.route("/cake/start", methods=["GET", "POST"])
def start_order():
    """Start collecting order details"""
    call_sid = request.values.get("call_sid", "")
    speech   = request.values.get("SpeechResult", "").lower()
    auto     = request.values.get("auto", "0")

    if "no" in speech and "yes" not in speech:
        r = VoiceResponse()
        r.say("Oh, no worries at all! We are here whenever you are ready. Have a lovely day, take care, bye bye!", voice="Polly.Raveena", language="en-IN")
        r.hangup()
        return Response(str(r), mimetype="text/xml")

    # Initialize session if needed
    if call_sid not in sessions:
        sessions[call_sid] = {"phone": "Unknown", "step_index": 0}

    sessions[call_sid]["step_index"] = 0
    first_step = STEPS[0]
    return Response(ask_question(first_step, call_sid), mimetype="text/xml")


@app.route("/cake/answer", methods=["GET", "POST"])
def collect_answer():
    """Collect answer for current step, move to next"""
    call_sid = request.values.get("call_sid", "")
    step     = request.values.get("step", "name")
    speech   = request.values.get("SpeechResult", "").strip()
    timeout  = request.values.get("timeout", "0")

    if call_sid not in sessions:
        sessions[call_sid] = {"phone": "Unknown", "step_index": 0}

    session = sessions[call_sid]

    # Save answer
    if speech and timeout == "0":
        session[step] = speech
    elif timeout == "1" and step not in session:
        session[step] = "Not specified"

    # Find next step
    current_idx = STEPS.index(step) if step in STEPS else 0
    next_idx = current_idx + 1

    if next_idx < len(STEPS):
        # More questions
        next_step = STEPS[next_idx]
        session["step_index"] = next_idx

        # Acknowledge and ask next
        r = VoiceResponse()
        ack_msgs = {
            "name":          f"What a beautiful name, {speech}! So nice to meet you! ",
            "cake_type":     "Oh how wonderful, that is going to be so special! ",
            "flavor":        "Mmm, great taste! That flavor is absolutely delicious! ",
            "size":          "Perfect size! That cake is going to look amazing! ",
            "delivery_date": "Noted down! We will make sure it is fresh and ready! ",
            "delivery_time": "Sure thing! We will be there right on time! ",
            "address":       "Got it, thank you so much! ",
        }
        ack = ack_msgs.get(step, "Okay! ") if speech else ""
        gather = Gather(
            input="speech",
            action=f"/cake/answer?step={next_step}&call_sid={call_sid}",
            method="POST",
            speech_timeout="2",
            language="en-IN",
            hints="chocolate vanilla strawberry birthday wedding anniversary kg morning afternoon evening",
        )
        gather.say(ack + QUESTIONS[next_step], voice="Polly.Raveena", language="en-IN")
        r.append(gather)
        r.redirect(f"/cake/answer?step={next_step}&call_sid={call_sid}&timeout=1", method="POST")
        return Response(str(r), mimetype="text/xml")

    else:
        # All steps done — save order
        order_id = save_order(session)

        # Confirmation summary
        name      = session.get("name", "")
        cake_type = session.get("cake_type", "")
        flavor    = session.get("flavor", "")
        size      = session.get("size", "")
        del_date  = session.get("delivery_date", "")
        del_time  = session.get("delivery_time", "")
        msg       = session.get("message", "no message")

        # Calculate price
        amount = calculate_price(cake_type, flavor, size)
        session["amount"] = amount

        # Save amount to DB
        conn2 = sqlite3.connect(DB_NAME)
        conn2.execute("UPDATE orders SET amount=? WHERE order_id=?",
                      (amount, order_id))
        conn2.commit()
        conn2.close()

        r = VoiceResponse()
        r.say(
            f"Yay, {name}! Your order is all set and we are so excited to bake for you! "
            f"So just to recap, you have ordered a {size} {flavor} {cake_type}, "
            f"and we will deliver it on {del_date} by {del_time}. "
            f"The total comes to just Rupees {amount}. "
            f"Your order ID is {' '.join(order_id)}, please save it! "
            f"Our team will call you back shortly to confirm everything. "
            f"Thank you so much for choosing {SHOP_NAME}! "
            f"Have a super sweet day, take care, bye bye!",
            voice="Polly.Raveena",
            language="en-IN"
        )
        r.hangup()

        # Send acknowledgment SMS — NOT confirmation
        try:
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            phone = session.get("phone", "")
            if phone and phone != "Unknown":
                client.messages.create(
                    body=(
                        f"🎂 {SHOP_NAME}\n"
                        f"Order Received!\n"
                        f"ID: {order_id}\n"
                        f"Cake: {size} {flavor} {cake_type}\n"
                        f"Size: {size} | Amount: Rs.{amount}/-\n"
                        f"Delivery: {del_date} {del_time}\n"
                        f"We will call you back to confirm your order shortly!"
                    ),
                    from_=TWILIO_NUM,
                    to=phone
                )
        except Exception as e:
            print(f"SMS error: {e}")

        # Notify owner via WhatsApp
        try:
            if OWNER_PHONE:
                client2 = Client(TWILIO_SID, TWILIO_TOKEN)
                client2.messages.create(
                    body=(
                        f"🎂 *NEW ORDER - {SHOP_NAME}*\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"📋 *ID:* {order_id}\n"
                        f"👤 *Customer:* {name}\n"
                        f"📞 *Phone:* {session.get('phone', '')}\n"
                        f"🎂 *Cake:* {size} {flavor} {cake_type}\n"
                        f"📅 *Delivery:* {del_date} {del_time}\n"
                        f"📍 *Address:* {session.get('address', '')}\n"
                        f"💰 *Amount:* Rs.{amount}/-\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"Please confirm the order from dashboard!"
                    ),
                    from_=WHATSAPP_FROM,
                    to=f"whatsapp:{OWNER_PHONE}"
                )
                print(f"✅ Owner WhatsApp notified: {OWNER_PHONE}")
        except Exception as e:
            print(f"Owner WhatsApp error: {e}")

        print(f"\n🎂 NEW ORDER: {order_id} | {name} | Rs.{amount}/- | {size} {flavor} {cake_type}")
        print(f"   Dashboard: http://localhost:5001/cake/orders\n")
        # Cleanup session
        if call_sid in sessions:
            del sessions[call_sid]

        return Response(str(r), mimetype="text/xml")


# ── Admin Dashboard ───────────────────────────────────────────────────
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>🎂 Cake Orders</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0d0d1a; color:#fff; font-family:'Segoe UI',sans-serif; padding:15px; }
h1 { color:#f9a8d4; font-size:20px; margin-bottom:15px; }
.stats { display:flex; gap:10px; margin-bottom:20px; }
.stat { flex:1; background:rgba(249,168,212,0.1); border:1px solid rgba(249,168,212,0.3); border-radius:12px; padding:12px; text-align:center; }
.stat .num { font-size:24px; font-weight:800; color:#f9a8d4; }
.stat .lbl { font-size:10px; color:rgba(255,255,255,0.5); margin-top:2px; }
.refresh { background:rgba(249,168,212,0.2); border:1px solid #f9a8d4; color:#f9a8d4; padding:8px 16px; border-radius:8px; cursor:pointer; font-size:12px; margin-bottom:15px; width:100%; }

/* Mobile cards instead of table */
.order-card {
    background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
    border-radius:14px; padding:14px; margin-bottom:12px;
    border-left:3px solid #f9a8d4;
}
.order-card.confirmed { border-left-color:#4ade80; }
.order-card.delivered { border-left-color:#38bdf8; }

.order-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.order-id { font-size:11px; font-weight:800; color:#f9a8d4; letter-spacing:1px; }
.amount { font-size:18px; font-weight:800; color:#4ade80; }

.order-name { font-size:16px; font-weight:700; color:#fff; margin-bottom:4px; }
.order-phone { font-size:13px; color:#38bdf8; margin-bottom:8px; }
.order-phone a { color:#38bdf8; text-decoration:none; }

.order-details { display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:10px; }
.detail { background:rgba(255,255,255,0.04); border-radius:8px; padding:6px 10px; }
.detail .dlbl { font-size:9px; color:rgba(255,255,255,0.4); letter-spacing:1px; text-transform:uppercase; }
.detail .dval { font-size:12px; color:#fff; margin-top:2px; }

.order-address { background:rgba(255,255,255,0.04); border-radius:8px; padding:8px 10px; margin-bottom:10px; }
.order-address .dlbl { font-size:9px; color:rgba(255,255,255,0.4); letter-spacing:1px; text-transform:uppercase; }
.order-address .dval { font-size:12px; color:#fff; margin-top:2px; }

.order-msg { background:rgba(249,168,212,0.06); border-radius:8px; padding:8px 10px; margin-bottom:10px; font-size:12px; color:#f9a8d4; font-style:italic; }

.order-footer { display:flex; justify-content:space-between; align-items:center; }
.badge { display:inline-block; padding:3px 12px; border-radius:10px; font-size:11px; font-weight:700; }
.pending  { background:rgba(251,191,36,0.2);  color:#fbbf24; border:1px solid #fbbf24; }
.confirmed{ background:rgba(74,222,128,0.2);  color:#4ade80; border:1px solid #4ade80; }
.delivered{ background:rgba(56,189,248,0.2);  color:#38bdf8; border:1px solid #38bdf8; }
.order-time { font-size:10px; color:rgba(255,255,255,0.3); }

.confirm-btn {
    background:rgba(74,222,128,0.2); border:1px solid #4ade80;
    color:#4ade80; padding:6px 16px; border-radius:8px;
    cursor:pointer; font-size:12px; font-weight:700;
}
.call-btn {
    background:rgba(56,189,248,0.2); border:1px solid #38bdf8;
    color:#38bdf8; padding:6px 14px; border-radius:8px;
    cursor:pointer; font-size:12px; font-weight:700;
    text-decoration:none; display:inline-block;
}
.btn-row { display:flex; gap:8px; margin-top:8px; }
</style>
<script>
function confirmOrder(orderId) {
    if (!confirm("Confirm this order and send SMS to customer?")) return;
    fetch("/cake/update_status", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({order_id: orderId, status: "confirmed"})
    }).then(r => r.json()).then(d => {
        if (d.ok) { alert("✅ Order confirmed! SMS sent to customer."); location.reload(); }
    }).catch(e => alert("Error: " + e));
}
</script>
</head>
<body>
<h1>🎂 {{ shop_name }}</h1>
<div class="stats">
    <div class="stat"><div class="num">{{ total }}</div><div class="lbl">Total</div></div>
    <div class="stat"><div class="num">{{ pending }}</div><div class="lbl">Pending</div></div>
    <div class="stat"><div class="num">{{ confirmed }}</div><div class="lbl">Confirmed</div></div>
</div>
<button class="refresh" onclick="location.reload()">🔄 Refresh Orders</button>

{% for o in orders %}
<div class="order-card {{ o.status }}">
    <div class="order-top">
        <span class="order-id">{{ o.order_id }}</span>
        <span class="amount">₹{{ o.amount or 0 }}/-</span>
    </div>

    <div class="order-name">{{ o.name or 'Unknown' }}</div>
    <div class="order-phone">
        📞 <a href="tel:{{ o.phone }}">{{ o.phone }}</a>
    </div>

    <div class="order-details">
        <div class="detail">
            <div class="dlbl">Cake</div>
            <div class="dval">{{ o.cake_type or '-' }}</div>
        </div>
        <div class="detail">
            <div class="dlbl">Flavor</div>
            <div class="dval">{{ o.flavor or '-' }}</div>
        </div>
        <div class="detail">
            <div class="dlbl">Size</div>
            <div class="dval">{{ o.size or '-' }}</div>
        </div>
        <div class="detail">
            <div class="dlbl">Delivery</div>
            <div class="dval">{{ o.delivery_date or '-' }}<br><small>{{ o.delivery_time or '' }}</small></div>
        </div>
    </div>

    {% if o.address %}
    <div class="order-address">
        <div class="dlbl">📍 Address</div>
        <div class="dval">{{ o.address }}</div>
    </div>
    {% endif %}

    {% if o.message and o.message != 'Not specified' %}
    <div class="order-msg">💬 "{{ o.message }}"</div>
    {% endif %}

    <div class="order-footer">
        <span class="badge {{ o.status }}">{{ o.status }}</span>
        <span class="order-time">{{ o.created_date }} {{ o.created_time }}</span>
    </div>

    <div class="btn-row">
        <a href="tel:{{ o.phone }}" class="call-btn">📞 Call</a>
        {% if 'confirmed' not in o.status and 'delivered' not in o.status %}
        <button class="confirm-btn" onclick="confirmOrder('{{ o.order_id }}')">✅ Confirm</button>
        {% endif %}
    </div>
</div>
{% endfor %}
</body>
</html>
"""

@app.route("/cake/orders")
def orders_dashboard():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    total     = len(rows)
    pending   = sum(1 for r in rows if r["status"] == "pending")
    confirmed = sum(1 for r in rows if r["status"] == "confirmed")

    return render_template_string(
        DASHBOARD_HTML,
        orders=rows,
        total=total,
        pending=pending,
        confirmed=confirmed,
        shop_name=SHOP_NAME
    )


@app.route("/cake/update_status", methods=["POST"])
def update_status():
    order_id = request.json.get("order_id")
    status   = request.json.get("status")

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE order_id=?", (status, order_id))
    conn.commit()

    # If confirming — send SMS to customer
    if status == "confirmed":
        c.execute("SELECT * FROM orders WHERE order_id=?", (order_id,))
        order = c.fetchone()
        conn.close()
        if order:
            try:
                client = Client(TWILIO_SID, TWILIO_TOKEN)
                phone = order["phone"]
                if phone and phone != "Unknown":
                    client.messages.create(
                        body=(
                            f"🎂 {SHOP_NAME}\n"
                            f"✅ Your order is CONFIRMED!\n"
                            f"ID: {order_id}\n"
                            f"Cake: {order['size']} {order['flavor']} {order['cake_type']}\n"
                            f"Delivery: {order['delivery_date']} {order['delivery_time']}\n"
                            f"Amount: Rs.{order['amount'] or 0}/-\n"
                            f"Please keep the amount ready. Pay on delivery. Thank you for choosing us! 😊"
                        ),
                        from_=TWILIO_NUM,
                        to=phone
                    )
                    print(f"✅ Confirmation SMS sent to {phone}")
            except Exception as e:
                print(f"SMS error: {e}")
    else:
        conn.close()

    return {"ok": True}


if __name__ == "__main__":
    print("─" * 40)
    print("🎂 Cake Shop Voice Order System")
    print(f"   Shop: {SHOP_NAME}")
    print(f"   Orders dashboard: http://localhost:5001/cake/orders")
    print(f"   Twilio webhook:   /cake/incoming")
    print("─" * 40)
    app.run(host="0.0.0.0", port=5001, debug=False)