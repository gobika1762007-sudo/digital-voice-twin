import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATASET_PATH = "warden_dataset.csv"
VOICE_FILE   = "warden.wav"
FALLBACK_MSG = "Rules padi nadakkanam! Hostel pathi kelu!"

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

def _search(msg):
    if _df.empty or _vectorizer is None:
        return FALLBACK_MSG

    # Step 1: Exact match
    exact = _df[_df["question"] == msg]
    if not exact.empty:
        return exact.iloc[0]["answer"]

    # Step 2: Partial match
    partial = _df[_df["question"].str.contains(msg, regex=False, na=False)]
    if not partial.empty:
        return partial.iloc[0]["answer"]

    # Step 3: TF-IDF with threshold 0.3
    try:
        s = cosine_similarity(_vectorizer.transform([msg]), _X)
        i = s.argmax()
        if s[0][i] >= 0.3:
            return _df.iloc[i]["answer"]
    except:
        pass

    return FALLBACK_MSG

def get_reply(msg):
    return _search(msg.lower().strip())

def get_voice_file():
    return VOICE_FILE