import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json, os, re
from groq import Groq

DATASET_PATH = "teacher_dataset.csv"
FALLBACK_MSG = "Ithu 10th Maths-la illaye da! Maths doubt irundha kelu!"

STEP_PERSONA = """You are a Tamil Nadu 10th standard Maths teacher. Explain step-by-step in natural Tanglish (Tamil + English mix).

Return ONLY valid JSON — no markdown, no extra text, nothing else:
{
  "steps": [
    {
      "type": "intro",
      "label": "புரிஞ்சுக்கோ",
      "speak": "Natural Tanglish spoken explanation. NO math symbols — spell out everything: say 'x squared' not x², 'square root of 2' not √2, 'equals' not =, 'plus' not +. 2-3 warm sentences.",
      "display": "Board text. Use [M]formula here[/M] for math blocks."
    },
    {
      "type": "work",
      "label": "Step 1",
      "speak": "Next step explanation in Tanglish. No symbols.",
      "display": "Calculation. Use [M]...[/M] for math."
    },
    {
      "type": "answer",
      "label": "விடை",
      "speak": "Final answer in Tanglish.",
      "display": "Final answer"
    },
    {
      "type": "tip",
      "label": "நினைச்சுக்கோ",
      "speak": "Memory trick in Tanglish.",
      "display": "Tip text"
    }
  ]
}

Rules:
- 4 to 6 steps total (intro + 2-3 work + answer + tip)
- speak = pure speech text, zero symbols
- display = board text, can have [M]math[/M]
- Teacher phrases: "பாருங்க", "simple தான்", "okay?", "இல்லையா?", "சரியா?", "நல்லா நினைச்சுக்கோங்க"
- For non-maths questions: {"steps":[{"type":"intro","label":"Teacher says","speak":"Tanglish reply","display":"reply"}]}
- RETURN ONLY JSON. No explanation before or after."""

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

def _search_dataset(msg):
    if _df.empty or _vectorizer is None: return None
    exact = _df[_df["question"] == msg]
    if not exact.empty: return exact.iloc[0]["answer"]
    try:
        s = cosine_similarity(_vectorizer.transform([msg]), _X)
        i = s.argmax()
        if s[0][i] >= 0.4: return _df.iloc[i]["answer"]
    except: pass
    return None

def _groq_steps(msg):
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1200,
            temperature=0.7,
            messages=[
                {"role": "system", "content": STEP_PERSONA},
                {"role": "user",   "content": msg}
            ]
        )
        raw = r.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        return parsed
    except Exception as e:
        print(f"Teacher Groq error: {e}")
        return None

def get_reply(msg):
    msg_clean = msg.lower().strip()

    # Step 1: Dataset match
    dataset_reply = _search_dataset(msg_clean)
    if dataset_reply:
        return dataset_reply

    # Step 2: Groq step-by-step
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        parsed = _groq_steps(msg)
        if parsed:
            return json.dumps(parsed, ensure_ascii=False)

    return FALLBACK_MSG