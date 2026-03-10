import re

EMOTIONS = {
    "happy": {
        "keywords": [
            "super", "nalla", "good", "great", "romba", "enjoy", "happy",
            "santhosham", "awesome", "wonderful", "yay", "woah", "nice",
            "perfect", "excellent", "correct", "right", "yes",
            "aama", "seri", "okay", "sure", "definitely", "of course"
        ],
        "emoji": "😊", "label": "Happy", "rate": "+10%", "pitch": "+5Hz",
    },
    "funny": {
        "keywords": [
            "haha", "lol", "joke", "funny", "comedy", "laugh",
            "seriously", "apdiya", "unbelievable", "wait what"
        ],
        "emoji": "😂", "label": "Funny", "rate": "+15%", "pitch": "+8Hz",
    },
    "sad": {
        "keywords": [
            "sorry", "thappu", "mistake", "unfortunate",
            "mudiyaathu", "difficult", "hard", "fail", "wrong"
        ],
        "emoji": "😢", "label": "Sad", "rate": "-15%", "pitch": "-5Hz",
    },
    "angry": {
        "keywords": [
            "rules", "discipline", "strict", "fine", "warning",
            "must", "mandatory", "banned", "not allowed", "violation",
            "serious", "kodumai", "complaint"
        ],
        "emoji": "😠", "label": "Strict", "rate": "+5%", "pitch": "-8Hz",
    },
    "thinking": {
        "keywords": [
            "hmm", "maybe", "perhaps", "theriyaathu", "not sure",
            "possibly", "might", "paarkalaam", "actually", "depends",
            "konjam", "think", "consider", "puriyala"
        ],
        "emoji": "🤔", "label": "Thinking", "rate": "-5%", "pitch": "+0Hz",
    },
}

DEFAULT_EMOTION = {
    "emoji": "💬", "label": "Neutral",
    "rate": "+0%", "pitch": "+0Hz",
}

def detect_emotion(text: str) -> dict:
    text_lower = text.lower()
    scores = {}
    for name, data in EMOTIONS.items():
        score = sum(1 for k in data["keywords"] if k.lower() in text_lower)
        if score > 0:
            scores[name] = score
    if not scores:
        r = DEFAULT_EMOTION.copy(); r["name"] = "neutral"; return r
    best = max(scores, key=scores.get)
    r = EMOTIONS[best].copy(); r["name"] = best; return r

def format_reply(text, emotion):
    return f"{text} {emotion.get('emoji', '')}"

def get_voice_settings(twin_name: str, emotion: dict) -> dict:
    TWIN_VOICES = {
        "gobika":  "en-IN-NeerjaNeural",
        "teacher": "en-IN-NeerjaExpressiveNeural",
        "warden":  "en-IN-PrabhatNeural",
        "shop":    "en-IN-NeerjaNeural",
        "coach":   "en-IN-PrabhatNeural",
    }
    return {
        "voice": TWIN_VOICES.get(twin_name, "en-IN-NeerjaNeural"),
        "rate":  emotion.get("rate",  "+0%"),
        "pitch": emotion.get("pitch", "+0Hz"),
    }