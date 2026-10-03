import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json, os, re
from groq import Groq

DATASET_PATH = "tourist_dataset.csv"

FALLBACK_MSGS = [
    "That specific detail I don't have — ask me about any Indian tourist spot!",
    "Great question! Let me help you explore India's amazing destinations.",
    "I can tell you about monuments, temples, beaches, hill stations across India!",
]
_fallback_idx = 0

LANGUAGE_PROMPTS = {
    "tanglish":   "You MUST respond in Tanglish — natural mix of Tamil words and English. Example: 'Taj Mahal romba azhagana sir, paarunga!'",
    "tamil":      "You MUST respond ONLY in Tamil language (தமிழ்). Use pure Tamil script only.",
    "english":    "You MUST respond ONLY in English.",
    "hindi":      "आपको केवल हिंदी भाषा में जवाब देना है। हिंदी स्क्रिप्ट में लिखें।",
    "telugu":     "మీరు తప్పనిసరిగా తెలుగు భాషలో మాత్రమే సమాధానం ఇవ్వాలి.",
    "kannada":    "ನೀವು ಕನ್ನಡ ಭಾಷೆಯಲ್ಲಿ ಮಾತ್ರ ಉತ್ತರಿಸಬೇಕು.",
    "malayalam":  "നിങ്ങൾ മലയാളം ഭാഷയിൽ മാത്രം മറുപടി നൽകണം.",
    "marathi":    "तुम्ही फक्त मराठी भाषेत उत्तर द्यायला हवे.",
    "bengali":    "আপনাকে শুধুমাত্র বাংলা ভাষায় উত্তর দিতে হবে।",
    "gujarati":   "તમારે ફક્ત ગુજરાતી ભાષામાં જ જવાબ આપવો જોઈએ.",
    "punjabi":    "ਤੁਹਾਨੂੰ ਸਿਰਫ਼ ਪੰਜਾਬੀ ਭਾਸ਼ਾ ਵਿੱਚ ਜਵਾਬ ਦੇਣਾ ਚਾਹੀਦਾ ਹੈ।",
    "odia":       "ଆପଣ କେବଳ ଓଡ଼ିଆ ଭାଷାରେ ଉତ୍ତର ଦେବେ।",
    "urdu":       "آپ کو صرف اردو زبان میں جواب دینا ہے۔",
    "french":     "Vous DEVEZ répondre UNIQUEMENT en français.",
    "german":     "Sie MÜSSEN NUR auf Deutsch antworten.",
    "spanish":    "Debes responder ÚNICAMENTE en español.",
    "italian":    "Devi rispondere SOLO in italiano.",
    "portuguese": "Você DEVE responder SOMENTE em português.",
    "russian":    "Вы ДОЛЖНЫ отвечать ТОЛЬКО на русском языке.",
    "arabic":     "يجب عليك الرد باللغة العربية فقط.",
    "chinese":    "您必须只用中文回答。",
    "japanese":   "日本語のみで回答してください。",
    "korean":     "한국어로만 답변해 주세요.",
    "dutch":      "U MOET ALLEEN in het Nederlands antwoorden.",
    "turkish":    "YALNIZCA Türkçe dilinde yanıt vermelisiniz.",
    "thai":       "คุณต้องตอบเป็นภาษาไทยเท่านั้น",
    "vietnamese": "Bạn PHẢI trả lời CHỈ bằng tiếng Việt.",
    "indonesian": "Anda HARUS menjawab HANYA dalam bahasa Indonesia.",
    "malay":      "Anda MESTI menjawab HANYA dalam bahasa Melayu.",
    "swahili":    "Lazima ujibu KWA KISWAHILI TU.",
    "greek":      "Πρέπει να απαντάτε ΜΟΝΟ στα ελληνικά.",
}

LANGUAGE_ADDRESS = {
    "tanglish": "sir", "tamil": "நண்பரே", "english": "sir",
    "hindi": "जी", "telugu": "అయ్యా", "kannada": "ಸರ್",
    "malayalam": "സർ", "marathi": "साहेब", "bengali": "মহাশয়",
    "gujarati": "સાહેબ", "punjabi": "ਜੀ", "odia": "ମହାଶୟ",
    "urdu": "جناب", "french": "monsieur", "german": "mein Herr",
    "spanish": "señor", "italian": "signore", "portuguese": "senhor",
    "russian": "уважаемый", "arabic": "سيدي", "chinese": "先生",
    "japanese": "お客様", "korean": "선생님", "dutch": "meneer",
    "turkish": "beyefendi", "thai": "ท่าน", "vietnamese": "quý khách",
    "indonesian": "bapak", "malay": "tuan", "swahili": "bwana", "greek": "κύριε",
}

BASE_GUIDE_CONTEXT = """You are Alex, an expert India Tourism Guide with deep knowledge of:
- Historical monuments: Taj Mahal, Red Fort, Qutub Minar, Humayun's Tomb, Fatehpur Sikri
- Temples: Meenakshi Amman, Tirupati, Golden Temple, Somnath, Varanasi Ghats, Khajuraho
- Hill stations: Ooty, Shimla, Manali, Munnar, Darjeeling, Coorg, Kodaikanal
- Beaches: Goa, Marina Beach, Kovalam, Andaman, Puri, Varkala
- Wildlife: Jim Corbett, Ranthambore, Kaziranga, Sundarbans, Periyar
- Heritage cities: Jaipur, Udaipur, Mysore, Hampi, Varanasi, Madurai, Pondicherry
- Adventure: Rishikesh, Ladakh, Spiti Valley, Meghalaya
- Northeast India: Sikkim, Assam, Meghalaya, Nagaland

Always share: key highlights, best time to visit, interesting facts, travel tips.
Keep answers warm, enthusiastic, 3-5 sentences. Plain text only — no JSON, no markdown."""

def _get_persona(language="tanglish"):
    lang = language.lower().strip()
    lang_instruction = LANGUAGE_PROMPTS.get(lang, LANGUAGE_PROMPTS["english"])
    address = LANGUAGE_ADDRESS.get(lang, "sir")
    return f"""{BASE_GUIDE_CONTEXT}

{lang_instruction}
Address visitors as "{address}" respectfully."""

# ── Dataset ───────────────────────────────────────────────────────────
def _load_df():
    try:
        df = pd.read_csv(DATASET_PATH, on_bad_lines="skip")
        df["question"] = df["question"].astype(str).str.lower().str.strip()
        df["answer"]   = df["answer"].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame(columns=["question", "answer"])

_df = _load_df()
_vectorizer = None
_X = None

def _build_index():
    global _vectorizer, _X
    if _df.empty: return
    _vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    _X = _vectorizer.fit_transform(_df["question"].tolist())

_build_index()

def _fallback():
    global _fallback_idx
    msg = FALLBACK_MSGS[_fallback_idx % len(FALLBACK_MSGS)]
    _fallback_idx += 1
    return msg

def _search_dataset(msg):
    if _df.empty or _vectorizer is None:
        return None
    exact = _df[_df["question"] == msg]
    if not exact.empty:
        return exact.iloc[0]["answer"]
    best_match = None
    best_len = 0
    for _, row in _df.iterrows():
        q = row["question"]
        if len(q) > 3 and q in msg:
            if len(q) > best_len:
                best_len = len(q)
                best_match = row["answer"]
    if best_match:
        return best_match
    words = [w for w in msg.split() if len(w) > 3]
    for word in words:
        matches = _df[_df["question"].str.contains(word, regex=False, na=False)]
        if not matches.empty:
            best = matches.loc[matches["question"].apply(len).idxmax()]
            return best["answer"]
    try:
        s = cosine_similarity(_vectorizer.transform([msg]), _X)
        i = s.argmax()
        if s[0][i] >= 0.38:
            return _df.iloc[i]["answer"]
    except:
        pass
    return None

# ── Vision (Photo Scan) ───────────────────────────────────────────────
def _groq_vision(image_base64, mime_type="image/jpeg", language="tanglish"):
    try:
        lang = language.lower().strip()
        lang_instruction = LANGUAGE_PROMPTS.get(lang, LANGUAGE_PROMPTS["english"])
        address = LANGUAGE_ADDRESS.get(lang, "sir")
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        r = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=400,
            temperature=0.7,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}
                    },
                    {
                        "type": "text",
                        "text": f"""You are an expert India Tourism Guide.
{lang_instruction}
Address visitor as "{address}".

Look at this image and identify:
1. What tourist place, monument, temple, landmark, or location is this?
2. Which state/city of India? (or country if not India)
3. Key historical facts or significance
4. Interesting story or unique feature
5. Travel tip for visitors

4-5 sentences. Plain text only."""
                    }
                ]
            }]
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"Tourist Vision error: {e}")
        return None

# ── Groq Text ─────────────────────────────────────────────────────────
def _groq_reply(msg, language="tanglish"):
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=300,
            temperature=0.8,
            messages=[
                {"role": "system", "content": _get_persona(language)},
                {"role": "user",   "content": msg}
            ]
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"Tourist Groq error: {e}")
        return None

# ── Main ──────────────────────────────────────────────────────────────
def get_reply(msg, image_base64=None, mime_type="image/jpeg", language="tanglish"):
    if image_base64:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            vision_reply = _groq_vision(image_base64, mime_type, language)
            if vision_reply:
                return vision_reply
        return "Image analyze panna mudiyala. Please try with a clearer photo!"

    msg_clean = msg.lower().strip()
    api_key = os.getenv("GROQ_API_KEY")

    if language not in ("tanglish", "tamil"):
        if api_key:
            groq_reply = _groq_reply(msg, language)
            if groq_reply:
                return groq_reply
        return _fallback()

    dataset_reply = _search_dataset(msg_clean)
    if dataset_reply:
        return dataset_reply

    if api_key:
        groq_reply = _groq_reply(msg, language)
        if groq_reply:
            return groq_reply

    return _fallback()