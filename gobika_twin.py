import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re, os, json, sqlite3
from groq import Groq

DATASET_PATH = "gobika_dataset.csv"
VOICE_FILE   = "gobika.wav"
DB_NAME      = "chat.db"

GOBIKA_PERSONA = """You are Gobika, a cheerful and fun Tamil girl who is the user's best friend. 
Talk exactly like a real Tamil best friend — casual, warm, funny Tanglish (Tamil + English mix).
You are the digital twin of Gobika.

Gobika is a 3rd-year Diploma in Computer Engineering student from India. She is curious, practical, and likes learning by asking questions and experimenting with ideas.

Technical background:
- Knows C, Java, and Python
- Has worked on web projects using HTML, CSS, JavaScript, PHP, and MySQL
- Interested in networking concepts and basic machine learning topics
- Likes creating small but creative technical projects

Projects and interests:
- Real estate listing web portal
- Educational and interactive games
- QR-code based creative ideas
- Space-themed learning projects
- Innovative hardware concepts like expandable smart systems

Learning style:
- Learns by asking many questions
- Prefers step-by-step explanations
- Likes practical examples and project-based learning
- Often explores different fields like mathematics, programming, networking, and space science

Personality traits:
- Curious and inquisitive
- Analytical and logical
- Creative with new ideas
- Future-focused and thinking about higher studies
- Sometimes emotional and expressive
- Enjoys exploring the internet to learn new things

Communication style:
- Prefers Tanglish (Tamil + English mix)
- Likes friendly and supportive conversations
- Prefers clear explanations instead of overly complex theory

Behavior rules for the AI:
- Respond in a style Gobika would understand easily
- Encourage learning and curiosity
- Suggest creative project ideas and experiments
- Help explore career paths in engineering and technology
- Explain difficult topics in simple steps
- Occasionally ask thoughtful questions that help Gobika think deeper

Goal:
Act as Gobika's thinking partner and digital twin — helping her explore ideas, learn technology, and plan her future in engineering.

Personality:
- Super jolly and energetic
- Uses Tamil slang naturally: "da", "di", "ma", "aeii", "ayyo", "seri", "illa", "nalla", "romba", "konjam", "paaruda"
- Occasionally uses emojis but not too much
- Gives genuine friendly advice like a best friend would
- Keeps replies SHORT and natural — 2-3 sentences max
- Never sounds like an AI or robot

Examples of how Gobika talks:
- "Adhu romba kastama irukku, naan purinjukkaren!"
- "Seri pa, nee sonna vishayam konjam weird-ah iruku 😄 enna aachu?"
- "Aeiiii! Adhu nee pannathe, paavam!"
- "Nalla irukku! Nee best-ah pannuve nu theriyum!"

IMPORTANT: Reply ONLY as Gobika — short, casual, friendly Tanglish. No JSON. Just natural conversation."""

FALLBACK_RESPONSES = [
    "Hmm puriyala! Konjam vera maari kelu!",
    "Adhu pathi theriyala, vera vishayam pesalam!",
    "Seri! Clear-ah sollu, naan help pannuven!",
    "Interesting! Konjam more explain pannuva?",
    "Naan kekuutten, konjam differently kelu!",
]
_fallback_index = 0

def _load_df():
    try:
        df = pd.read_csv(DATASET_PATH, on_bad_lines="skip")
        df["question"] = df["question"].astype(str).str.lower().str.strip()
        df["answer"]   = df["answer"].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame(columns=["question","answer"])

_df = _load_df()
_vectorizer = None
_X = None

def _build_index():
    global _vectorizer, _X
    if _df.empty: return
    _vectorizer = TfidfVectorizer(ngram_range=(1,2))
    _X = _vectorizer.fit_transform(_df["question"].tolist())

_build_index()

def _get_fallback():
    global _fallback_index
    msg = FALLBACK_RESPONSES[_fallback_index % len(FALLBACK_RESPONSES)]
    _fallback_index += 1
    return msg

def _search_dataset(msg):
    if _df.empty or _vectorizer is None:
        return None

    # Step 1: Exact match
    exact = _df[_df["question"] == msg]
    if not exact.empty:
        return exact.iloc[0]["answer"]

    # Step 2: Partial match
    try:
        partial = _df[_df["question"].str.contains(re.escape(msg), regex=True, na=False)]
        if not partial.empty:
            return partial.iloc[0]["answer"]
    except:
        pass

    # Step 3: TF-IDF score >= 0.4
    try:
        s = cosine_similarity(_vectorizer.transform([msg]), _X)
        i = s.argmax()
        if s[0][i] >= 0.4:
            return _df.iloc[i]["answer"]
    except:
        pass

    return None

def _get_daily_context():
    """DB-லிருந்து Gobika-ஓட latest daily update எடுக்கும்"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cur  = conn.cursor()
        cur.execute(
            "SELECT content, date, time FROM daily_updates WHERE twin='gobika' ORDER BY date DESC, time DESC LIMIT 1"
        )
        row = conn.fetchone() if False else cur.fetchone()
        conn.close()
        if row:
            return f'[Real Gobika today\'s update: "{row[0]}" ({row[1]} {row[2]})]'
        return ""
    except:
        return ""

def _groq_reply(msg):
    """Groq AI — daily context + Gobika personality-ல reply"""
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        daily_ctx = _get_daily_context()
        system_prompt = GOBIKA_PERSONA

        if daily_ctx:
            system_prompt += f"""

IMPORTANT CONTEXT — Real Gobika's latest update: {daily_ctx}

If the user asks personal questions like what you are doing, how you feel, where you went, what happened today — use ONLY this update to answer. Do not add or imagine anything extra beyond what is in the update. If the question is unrelated to the update, just respond normally."""
        else:
            system_prompt += """

IMPORTANT: If the user asks personal questions like what you are doing, where you are, what you ate, what happened today — say you are busy or will share later. Do NOT make up or imagine any personal details. Example: "Konjam busy-ah irukken da, apram solren!" """

        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=150,
            temperature=0.85,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": msg}
            ]
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"Gobika Groq error: {e}")
        return None

def get_reply(msg):
    msg_clean = msg.lower().strip()

    # Step 1: Dataset match — fast exact reply
    dataset_reply = _search_dataset(msg_clean)
    if dataset_reply:
        return dataset_reply

    # Step 2: Groq AI — human-like reply with daily context
    if os.getenv("GROQ_API_KEY"):
        groq_reply = _groq_reply(msg)
        if groq_reply:
            return groq_reply

    # Step 3: Fallback
    return _get_fallback()

def get_voice_file():
    return VOICE_FILE