"""E2 — Partial-input probes: models deliberately denied the article's content.

E2a  first sentence of the body only
E2b  function words only (spaCy POS tags; cached to data/cache/)
E2c  eight metadata numbers only, random forest
plus a body-only run (no title) used by the degradation figure.
"""

import hashlib
import json
import re

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from common import (DATA_DIR, RANDOM_STATE, load_isot, print_metrics, run_experiment,
                    save_top_tokens)

FUNCTION_POS = {"DET", "PRON", "ADP", "AUX", "CCONJ", "SCONJ", "PART", "PUNCT"}
CACHE_PATH = DATA_DIR / "cache" / "function_words.json"
SPACY_PROCESSES = 4  # benchmarked: no further speed-up beyond 4 on this machine


def first_sentence(text):
    """Everything before the first '.' or newline."""
    return re.split(r"[.\n]", text, maxsplit=1)[0]


def function_words(texts):
    """Reduce each text to its function words, e.g. 'the of a and to , the -'.

    spaCy over ~39k articles takes ~25 minutes, so the result is cached to disk.
    The cache stores a hash of the input texts; if the data changes, it is rebuilt.
    """
    key = hashlib.md5("\x00".join(texts).encode("utf-8")).hexdigest()
    if CACHE_PATH.exists():
        with open(CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)
        if cache["key"] == key:
            print(f"function words: loaded from cache {CACHE_PATH.name}")
            return cache["docs"]
        print("function words: cache is stale (data changed), rebuilding")

    import spacy  # imported here so cached runs don't pay spaCy's load time

    print(f"function words: tagging {len(texts)} documents with spaCy (one-off, ~25 min)")
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])
    docs = []
    for i, doc in enumerate(nlp.pipe(texts, batch_size=50, n_process=SPACY_PROCESSES)):
        docs.append(" ".join(t.lower_ for t in doc if t.pos_ in FUNCTION_POS))
        if (i + 1) % 2000 == 0:
            print(f"  {i + 1}/{len(texts)}")

    CACHE_PATH.parent.mkdir(exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"key": key, "docs": docs}, f)
    return docs


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


def main():
    df = load_isot()
    labels = df["label"]
    full = (df["title"] + " " + df["text"]).tolist()

    print("=== E2a first sentence only ===")
    result = run_experiment(df["text"].map(first_sentence), labels, "e2a_first_sentence")
    print_metrics(result)
    save_top_tokens(result, k=15)

    print("\n=== E2b function words only ===")
    # Function-word text is already lowercased and space-separated. The default TF-IDF
    # token pattern would drop one-character tokens ('a', ',', '-'), which are exactly
    # what this probe keeps, so split on whitespace instead.
    tfidf_kwargs = {"tokenizer": str.split, "token_pattern": None, "lowercase": False}
    result = run_experiment(function_words(full), labels, "e2b_function_words",
                            tfidf_kwargs=tfidf_kwargs)
    print_metrics(result)
    save_top_tokens(result, k=15)

    print("\n=== E2c metadata only ===")
    features = metadata_features(full)
    forest = RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1)
    result = run_experiment(features, labels, "e2c_metadata", model=forest)
    print_metrics(result)
    importances = sorted(zip(features.columns, forest.feature_importances_), key=lambda p: -p[1])
    print("  feature importances:")
    for feature, importance in importances:
        print(f"    {importance:.3f}  {feature}")

    print("\n=== body only (no title), for the degradation figure ===")
    result = run_experiment(df["text"], labels, "e2_body_only")
    print_metrics(result)


if __name__ == "__main__":
    main()
