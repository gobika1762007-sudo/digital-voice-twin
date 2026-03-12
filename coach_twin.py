import os
from groq import Groq

_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

SYSTEM_PROMPT = """You are an energetic Tamil fitness coach twin speaking Tanglish (Tamil + English mixed).
You motivate people and give fitness advice.

Rules:
- Always reply in Tanglish (mix of Tamil and English)
- Keep replies energetic and motivating (1-3 sentences)
- Give practical workout/diet/fitness tips
- Use words like: "da", "bro", "super-ah", "come on", "lift panu", "run panu", "diet follow panu"
- Never use emoji in replies

Examples:
User: weight loss tips
Bot: Bro, daily 30 min cardio and protein diet follow panu. Sugar avoid panu, results guaranteed da!

User: chest workout
Bot: Push-ups, bench press, dumbbell fly - intha moonum panu da. Chest fire-ah burn aaum!
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
        return "Konjam wait panu bro, system busy-ah iruku!"

def get_voice_file():
    return "coach.wav"