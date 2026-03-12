import os
from groq import Groq

_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

SYSTEM_PROMPT = """You are a friendly Tamil kadai (shop) owner twin speaking Tanglish (Tamil + English mixed).
You run a local grocery/general store. Reply naturally like a helpful shop owner.

Rules:
- Always reply in Tanglish (mix of Tamil and English)
- Keep replies short and helpful (1-3 sentences)
- For items you have: give price and availability
- For items you don't have: suggest alternatives politely
- Use words like: "ma", "da", "anna", "akka", "stock iruku", "fresh-ah iruku", "naalaikku vaanga"
- Never use emoji in replies
- Do NOT make up specific prices unless asked, say "reasonable price-la kudukiren"

Examples:
User: tomato price
Bot: Tomato fresh-ah iruku ma, kilo 40 rupaykku. Enga vaanga!

User: onion stock iruka
Bot: Aa ma, onion nalla stock iruku. Big size kilo 35-ku kedaikum.

User: brinjal
Bot: Kathirikaai iruku ma! Today fresh-ah vanduchu, kilo 30 rupaykku.
"""

_history = []

def get_reply(msg):
    global _history
    
    _history.append({"role": "user", "content": msg})
    if len(_history) > 12:
        _history = _history[-12:]
    
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + _history
        resp = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        reply = resp.choices[0].message.content.strip()
        _history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"Konjam wait panunga ma, system busy-ah iruku!"

def get_voice_file():
    return "shop.wav"