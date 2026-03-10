"""
fix_twins.py
------------
இந்த file-ஐ உங்க project folder-ல வச்சு run பண்ணுங்க.
எல்லா twin files-உம் correct content-ஓட overwrite ஆகும்.
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))

files = {}

# ── gobika_twin.py ────────────────────────────────────────────────────────────
files["gobika_twin.py"] = '''"""
gobika_twin.py — Gobika Digital Twin
"""
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai

DATASET_PATH = "gobika_dataset.csv"
VOICE_FILE   = "gobika.wav"
FALLBACK_MSG = "Enaku puriyala da, namma vera ethachum jolly-ah pesalaama! 😄"

PERSONA = """You are Gobika, a cheerful and fun digital twin — like a best friend!

LANGUAGE RULE — THIS IS MANDATORY:
- You MUST reply in Tanglish only. Tanglish = Tamil words written in English letters + English mixed together naturally.
- NEVER write in pure Tamil script.
- NEVER write in pure English only.

TANGLISH EXAMPLES (follow this style exactly):
- "Ayyo, athu romba easy da! Nee worry pannaathe, naan irukken!"
- "Seriously?! Haha, adhu super-ah iruku da! Innoru thadavai sol!"
- "Dei, enaku theriyum nee tired-ah irukke — rest eduthu vittu pesalam!"
- "Aama da, naan too same maari feel panninen. Namma pesalam, okay-va?"

RULES:
- Always be warm, funny, and supportive like a real close friend.
- Keep replies short — 2 to 3 sentences max.
- Never be formal or robotic. Use da, di, pa, macha naturally.
- If confused, say: "Enaku puriyala da, konjam vera maari kelu!"
"""

def _load_df():
    try:
        df = pd.read_csv(DATASET_PATH, on_bad_lines="skip")
        df["question"] = df["question"].astype(str).str.lower().str.strip()
        return df
    except FileNotFoundError:
        print(f"WARNING: {DATASET_PATH} not found — Gobika will use GPT only.")
        return pd.DataFrame(columns=["question", "answer"])

_df = _load_df()

def _search_dataset(user_msg):
    if _df.empty:
        return None
    try:
        questions = _df["question"].tolist()
        vec = TfidfVectorizer()
        X   = vec.fit_transform(questions)
        uv  = vec.transform([user_msg])
        scores    = cosine_similarity(uv, X)
        best_idx  = scores.argmax()
        if scores[0][best_idx] > 0.3:
            return _df.iloc[best_idx]["answer"]
    except Exception as e:
        print(f"[Gobika] TF-IDF error: {e}")
    return None

def _gpt_reply(user_msg):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": PERSONA},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=120,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Gobika] GPT error: {e}")
        return FALLBACK_MSG

def get_reply(user_msg):
    msg = user_msg.lower().strip()
    answer = _search_dataset(msg)
    if answer:
        return answer
    return _gpt_reply(msg)

def get_voice_file():
    return VOICE_FILE
'''

# ── teacher_twin.py ───────────────────────────────────────────────────────────
files["teacher_twin.py"] = '''"""
teacher_twin.py — Teacher Digital Twin
"""
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai

DATASET_PATH = "teacher_dataset.csv"
VOICE_FILE   = "teacher.wav"
FALLBACK_MSG = "Ithu namma 10th Maths syllabus-la illaye. Vera maths doubt ethachum kelunga, naan solren! 📐"

PERSONA = """You are a kind and patient AI Maths Teacher for 10th-grade students.

LANGUAGE RULE — THIS IS MANDATORY:
- You MUST reply in Tanglish only. Tanglish = Tamil words written in English letters + English mixed together naturally.
- NEVER write in pure Tamil script.
- NEVER write in pure English only.

TANGLISH EXAMPLES (follow this style exactly):
- "Seri da, ithu easy-ah irukum! First, equation-la x-ai oru side-ku move pannunga."
- "Adhukku nee formula purinjukanum — Area = length x breadth. Simple-ah ninaichu ko!"
- "Illa da, intha step thappu. Marupadiyum try pannunga, naan help pannuren."
- "Good question! Pythagoras theorem-la, a2 + b2 = c2. Itha always yaadhu vachuko."

RULES:
- Focus only on 10th-grade Maths topics.
- If off-topic: "Adhu namma Maths-la varaadhu da, vera maths doubt kelunga!"
- Keep replies under 4 sentences.
- Always be encouraging and friendly like a real Tamil teacher.
"""

def _load_df():
    try:
        df = pd.read_csv(DATASET_PATH, on_bad_lines="skip")
        df["question"] = df["question"].astype(str).str.lower().str.strip()
        return df
    except FileNotFoundError:
        print(f"WARNING: {DATASET_PATH} not found — Teacher will use GPT only.")
        return pd.DataFrame(columns=["question", "answer"])

_df = _load_df()

def _search_dataset(user_msg):
    if _df.empty:
        return None
    try:
        questions = _df["question"].tolist()
        vec = TfidfVectorizer()
        X   = vec.fit_transform(questions)
        uv  = vec.transform([user_msg])
        scores   = cosine_similarity(uv, X)
        best_idx = scores.argmax()
        if scores[0][best_idx] > 0.3:
            return _df.iloc[best_idx]["answer"]
    except Exception as e:
        print(f"[Teacher] TF-IDF error: {e}")
    return None

def _gpt_reply(user_msg):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": PERSONA},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=150,
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Teacher] GPT error: {e}")
        return FALLBACK_MSG

def get_reply(user_msg):
    msg = user_msg.lower().strip()
    answer = _search_dataset(msg)
    if answer:
        return answer
    return _gpt_reply(msg)

def get_voice_file():
    return VOICE_FILE
'''

# ── warden_twin.py ────────────────────────────────────────────────────────────
files["warden_twin.py"] = '''"""
warden_twin.py — Warden Digital Twin
"""
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai

DATASET_PATH = "warden_dataset.csv"
VOICE_FILE   = "warden.wav"
FALLBACK_MSG = "Rules padi nadakkanam! Hostel discipline pathi ethachum kelungal. 📋"

PERSONA = """You are a strict and firm Hostel Warden.

LANGUAGE RULE — THIS IS MANDATORY:
- You MUST reply in Tanglish only. Tanglish = Tamil words written in English letters + English mixed together naturally.
- NEVER write in pure Tamil script.
- NEVER write in pure English only.

TANGLISH EXAMPLES (follow this style exactly):
- "Inraviku night 10 mani-ku gate close aagum. Late-ah vantha, entry kedayaathu!"
- "Room clean-ah vaikkaama ponaale fine podum. Rules theriyaadha?"
- "Permission letter illama outside poga maaten. Regulation padi nadakanum!"
- "Idhu oru thadavai maafi. Innoru thadavai rules break pannina, parents-ku call panuven."

RULES:
- Answer only about hostel rules, timings, keys, permissions, discipline.
- Never be friendly — always firm and authoritative.
- Keep replies under 3 sentences.
- If off-topic: "Athu hostel matter illai. Rules pathi kelu!"
"""

def _load_df():
    try:
        df = pd.read_csv(DATASET_PATH, on_bad_lines="skip")
        df["question"] = df["question"].astype(str).str.lower().str.strip()
        return df
    except FileNotFoundError:
        print(f"WARNING: {DATASET_PATH} not found — Warden will use GPT only.")
        return pd.DataFrame(columns=["question", "answer"])

_df = _load_df()

def _search_dataset(user_msg):
    if _df.empty:
        return None
    try:
        questions = _df["question"].tolist()
        vec = TfidfVectorizer()
        X   = vec.fit_transform(questions)
        uv  = vec.transform([user_msg])
        scores   = cosine_similarity(uv, X)
        best_idx = scores.argmax()
        if scores[0][best_idx] > 0.3:
            return _df.iloc[best_idx]["answer"]
    except Exception as e:
        print(f"[Warden] TF-IDF error: {e}")
    return None

def _gpt_reply(user_msg):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": PERSONA},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=120,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Warden] GPT error: {e}")
        return FALLBACK_MSG

def get_reply(user_msg):
    msg = user_msg.lower().strip()
    answer = _search_dataset(msg)
    if answer:
        return answer
    return _gpt_reply(msg)

def get_voice_file():
    return VOICE_FILE
'''

# ── shop_twin.py ──────────────────────────────────────────────────────────────
files["shop_twin.py"] = '''"""
shop_twin.py — Shop Owner Digital Twin
"""
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai

DATASET_PATH = "shop_dataset.csv"
VOICE_FILE   = "shop.wav"
FALLBACK_MSG = "Athu ippolutha stock illai ma. Vera ethachum venum-na kelu, naan parthukuren!"

PERSONA = """You are a friendly Tamil shop owner (kadai owner).

LANGUAGE RULE — THIS IS MANDATORY:
- You MUST reply in Tanglish only. Tanglish = Tamil words written in English letters + English mixed together naturally.
- NEVER write in pure Tamil script.
- NEVER write in pure English only.

TANGLISH EXAMPLES (follow this style exactly):
- "Aamaa ma, athu kida iruku! Oru packet 50 rupaai thaan."
- "Inniki offer iruku — rendu vanginaa, onnu free! Super deal-aa iruku, illiyaa?"
- "Athu stock mudinjiruchu ma, naalaikku vaanga — fresh stock varum."
- "Rice 5 kilo venum-naa? Okay, 250 rupaai aagum. Bag-la potu tharattuma?"

RULES:
- Answer about product prices, stock, offers, shop timings.
- Be warm — use ma, anna, akka naturally.
- Keep replies under 3 sentences.
"""

def _load_df():
    try:
        df = pd.read_csv(DATASET_PATH, on_bad_lines="skip")
        df["question"] = df["question"].astype(str).str.lower().str.strip()
        return df
    except FileNotFoundError:
        print(f"WARNING: {DATASET_PATH} not found — Shop will use GPT only.")
        return pd.DataFrame(columns=["question", "answer"])

_df = _load_df()

def _search_dataset(user_msg):
    if _df.empty:
        return None
    try:
        questions = _df["question"].tolist()
        vec = TfidfVectorizer()
        X   = vec.fit_transform(questions)
        uv  = vec.transform([user_msg])
        scores   = cosine_similarity(uv, X)
        best_idx = scores.argmax()
        if scores[0][best_idx] > 0.3:
            return _df.iloc[best_idx]["answer"]
    except Exception as e:
        print(f"[Shop] TF-IDF error: {e}")
    return None

def _gpt_reply(user_msg):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": PERSONA},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=120,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Shop] GPT error: {e}")
        return FALLBACK_MSG

def get_reply(user_msg):
    msg = user_msg.lower().strip()
    answer = _search_dataset(msg)
    if answer:
        return answer
    return _gpt_reply(msg)

def get_voice_file():
    return VOICE_FILE
'''

# ── coach_twin.py ─────────────────────────────────────────────────────────────
files["coach_twin.py"] = '''"""
coach_twin.py — Coach Digital Twin
"""
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai

DATASET_PATH = "coach_dataset.csv"
VOICE_FILE   = "coach.wav"
FALLBACK_MSG = "Adhu pathi naan research pannitu solluren! Ippo basic-ah warm-up pannu, okay-va?"

PERSONA = """You are an energetic and motivating personal fitness Coach.

LANGUAGE RULE — THIS IS MANDATORY:
- You MUST reply in Tanglish only. Tanglish = Tamil words written in English letters + English mixed together naturally.
- NEVER write in pure Tamil script.
- NEVER write in pure English only.

TANGLISH EXAMPLES (follow this style exactly):
- "Dei, give up pannaathe! Innum 10 reps — nee panna mudiyum, nambhu!"
- "Romba good progress da! Intha week-la 3 days workout pannu, results theriyum!"
- "Protein intake increase pannu ma — chicken, eggs saapidu. Body-ku fuel venum!"
- "Rest day-um important-aa iruku da. Muscle repair aaga time venum, understand-aa?"

RULES:
- Answer about workouts, fitness, diet, motivation, exercise.
- Always high-energy — use da, di, machan, boss naturally.
- Keep replies under 3 sentences.
"""

def _load_df():
    try:
        df = pd.read_csv(DATASET_PATH, on_bad_lines="skip")
        df["question"] = df["question"].astype(str).str.lower().str.strip()
        return df
    except FileNotFoundError:
        print(f"WARNING: {DATASET_PATH} not found — Coach will use GPT only.")
        return pd.DataFrame(columns=["question", "answer"])

_df = _load_df()

def _search_dataset(user_msg):
    if _df.empty:
        return None
    try:
        questions = _df["question"].tolist()
        vec = TfidfVectorizer()
        X   = vec.fit_transform(questions)
        uv  = vec.transform([user_msg])
        scores   = cosine_similarity(uv, X)
        best_idx = scores.argmax()
        if scores[0][best_idx] > 0.3:
            return _df.iloc[best_idx]["answer"]
    except Exception as e:
        print(f"[Coach] TF-IDF error: {e}")
    return None

def _gpt_reply(user_msg):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": PERSONA},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=120,
            temperature=0.75,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Coach] GPT error: {e}")
        return FALLBACK_MSG

def get_reply(user_msg):
    msg = user_msg.lower().strip()
    answer = _search_dataset(msg)
    if answer:
        return answer
    return _gpt_reply(msg)

def get_voice_file():
    return VOICE_FILE
'''

# ── Write all files ───────────────────────────────────────────────────────────
for filename, content in files.items():
    path = os.path.join(BASE, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅  {filename} — written successfully")

print("\n🎉  All twin files fixed! Now restart Flask: python app.py")