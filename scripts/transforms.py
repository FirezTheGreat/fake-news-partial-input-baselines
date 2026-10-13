"""Text transformations shared by the experiment scripts.

Each turns articles into the restricted view a condition is allowed to see.
The slow ones (spaCy, VADER) cache their output to data/cache/, keyed by a hash
of the input texts, so they run once and are rebuilt only if the data changes.
"""

import hashlib
import json
import re

import pandas as pd

from common import DATA_DIR

CACHE_DIR = DATA_DIR / "cache"
SPACY_PROCESSES = 4  # benchmarked: no further speed-up beyond 4 on this machine
FUNCTION_POS = {"DET", "PRON", "ADP", "AUX", "CCONJ", "SCONJ", "PART", "PUNCT"}

# Function-word text is lowercased and space-separated. The default TF-IDF token
# pattern would drop one-character tokens ('a', ',', '-'), which are exactly what
# these probes keep, so split on whitespace instead.
WHITESPACE_TFIDF = {"tokenizer": str.split, "token_pattern": None, "lowercase": False}


# ---------- caching ----------

def _cached(name, texts, compute):
    """Return compute(texts), cached at data/cache/{name}.json and keyed by the texts."""
    path = CACHE_DIR / f"{name}.json"
    key = hashlib.md5("\x00".join(texts).encode("utf-8")).hexdigest()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
        if cache["key"] == key:
            print(f"{name}: loaded from cache")
            return cache["docs"]
        print(f"{name}: cache is stale (data changed), rebuilding")

    docs = compute(texts)
    CACHE_DIR.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"key": key, "docs": docs}, f)
    return docs


def _spacy_pipe(texts, disable, describe):
    import spacy  # imported here so cached runs don't pay spaCy's load time

    print(f"{describe}: running spaCy over {len(texts)} documents (one-off, ~25 min)")
    nlp = spacy.load("en_core_web_sm", disable=disable)
    for i, doc in enumerate(nlp.pipe(texts, batch_size=50, n_process=SPACY_PROCESSES)):
        if (i + 1) % 2000 == 0:
            print(f"  {i + 1}/{len(texts)}", flush=True)
        yield doc


def _function_word_string(doc):
    return " ".join(t.lower_ for t in doc if t.pos_ in FUNCTION_POS)


# ---------- E2a ----------

def first_sentence(text):
    """Everything before the first '.' or newline."""
    return re.split(r"[.\n]", text, maxsplit=1)[0]


# ---------- E2b ----------

def function_words(texts):
    """Reduce each text to its function words, e.g. 'the of a and to , the -'."""
    def compute(texts):
        docs = _spacy_pipe(texts, ["parser", "ner", "lemmatizer"], "function words")
        return [_function_word_string(doc) for doc in docs]
    return _cached("function_words", texts, compute)


# ---------- E2c ----------

def metadata_features(texts):
    """Eight surface statistics per article. No words survive into the model."""
    rows = []
    for t in texts:
        words = t.split()
        n_words = max(len(words), 1)
        n_chars = max(len(t), 1)
        rows.append({
            "char_count": len(t),
            "word_count": len(words),
            "sentence_count": len(re.findall(r"[.!?]+", t)),
            "exclamation_marks": t.count("!"),
            "question_marks": t.count("?"),
            "all_caps_word_ratio": sum(w.isupper() and len(w) > 1 for w in words) / n_words,
            "avg_word_length": sum(len(w) for w in words) / n_words,
            "digit_ratio": sum(c.isdigit() for c in t) / n_chars,
        })
    return pd.DataFrame(rows)


# ---------- E3 / E3b ----------

# Broader than '^[A-Z ]+\(Reuters\) -' so it also catches 'WASHINGTON/BEIJING (Reuters) -'
# and 'SAN JUAN, Puerto Rico (Reuters) -'. Only matches at the start of the body.
DATELINE = re.compile(r"^[^\n]*?\(Reuters\)\s*-\s*")
LEADING_SENTENCE = re.compile(r"^[^.\n]*[.\n]\s*")
REUTERS = re.compile(r"reuters", re.IGNORECASE)

IMAGE_CREDIT = re.compile(r"(featured\s+)?(image|photo|pic|video|screenshot|screen\s+capture|audio|gif)s?"
                          r"\s+(via|credit|by|courtesy)\b[^\n]*", re.IGNORECASE)
URL = re.compile(r"https?://\S+|www\.\S+|pic\.twitter\.com/\S+", re.IGNORECASE)
HANDLE = re.compile(r"@\w+")
MEDIA_TAG = re.compile(r"[\[(](videos?|tweets?|images?|photos?|watch|audio)[\])]"
                       r"|\b(watch|breaking|read more|just in)\s*:", re.IGNORECASE)
# The fake scrape lost apostrophes and quotation marks ("Trump s", "couldn t": a word
# followed by a lone s/t appears in 91.6% of fake vs 38.8% of real stripped articles),
# so every apostrophe and quote mark becomes a space in both classes. Ellipsis and dashes
# map to ASCII. (Extended once, after the E5c coefficients exposed the straight-quote case.)
TYPOGRAPHY = str.maketrans({"‘": " ", "’": " ", "'": " ", "“": " ", "”": " ", '"': " ",
                            "…": "...", "–": "-", "—": "-"})


def strip_artifacts(text):
    """E3: remove the dateline, the leading sentence and the word 'Reuters'."""
    text = DATELINE.sub("", text, count=1)
    text = LEADING_SENTENCE.sub("", text, count=1)
    return REUTERS.sub("", text)


def strip_page_furniture(text):
    """E3b: remove credits, URLs, handles and media tags; normalise typography."""
    for pattern in (IMAGE_CREDIT, URL, HANDLE, MEDIA_TAG):
        text = pattern.sub(" ", text)
    return text.translate(TYPOGRAPHY)


def stripped_titles_bodies(df):
    """(titles, bodies) after E3 stripping."""
    return df["title"].map(lambda t: REUTERS.sub("", t)), df["text"].map(strip_artifacts)


def fully_stripped_texts(df):
    """Title + body after E3 and E3b stripping: the strictest text view."""
    titles, bodies = stripped_titles_bodies(df)
    return titles.map(strip_page_furniture) + " " + bodies.map(strip_page_furniture)


# ---------- probes on stripped text (function words + named entities, one spaCy pass) ----------

def stripped_profile(texts, cache_name="stripped_profile"):
    """For each (already stripped) text: its function-word string and its entity-label counts.

    cache_name must differ per dataset (ISOT uses the default) so caches don't overwrite each other.
    """
    def compute(texts):
        docs = _spacy_pipe(texts, ["parser", "lemmatizer"], "stripped-text profile")
        out = []
        for doc in docs:
            counts = {}
            for ent in doc.ents:
                counts[ent.label_] = counts.get(ent.label_, 0) + 1
            out.append({"fw": _function_word_string(doc), "ents": counts})
        return out
    return _cached(cache_name, texts, compute)


def entity_features(profile, texts):
    """Named-entity counts per 100 words, one column per spaCy entity type."""
    counts = pd.DataFrame([p["ents"] for p in profile]).fillna(0)
    counts = counts[sorted(counts.columns)]
    words = pd.Series([max(len(t.split()), 1) for t in texts], index=counts.index)
    return counts.div(words, axis=0) * 100


# ---------- sentiment ----------

def sentiment_features(titles, bodies):
    """VADER negative / neutral / positive / compound scores, for title and body separately."""
    def compute(pairs):
        import nltk
        from nltk.sentiment import SentimentIntensityAnalyzer

        nltk.download("vader_lexicon", quiet=True)
        sia = SentimentIntensityAnalyzer()
        print(f"sentiment: scoring {len(pairs)} documents with VADER (one-off)")
        out = []
        for i, pair in enumerate(pairs):
            title, body = pair.split("\x01", 1)
            t, b = sia.polarity_scores(title), sia.polarity_scores(body)
            out.append([t["neg"], t["neu"], t["pos"], t["compound"],
                        b["neg"], b["neu"], b["pos"], b["compound"]])
            if (i + 1) % 5000 == 0:
                print(f"  {i + 1}/{len(pairs)}", flush=True)
        return out

    pairs = [f"{t}\x01{b}" for t, b in zip(titles, bodies)]
    rows = _cached("sentiment", pairs, compute)
    return pd.DataFrame(rows, columns=["title_neg", "title_neu", "title_pos", "title_compound",
                                       "body_neg", "body_neu", "body_pos", "body_compound"])
