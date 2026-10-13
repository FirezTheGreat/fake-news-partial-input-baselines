"""Shared experiment harness. Every experiment goes through run_experiment()."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

RANDOM_STATE = 42
TEST_SIZE = 0.2
N_SPLITS = 5  # random splits per experiment for the mean +/- SD; seeds 42..46
REAL, FAKE = 0, 1


def load_isot():
    """Load ISOT as one DataFrame: True.csv rows first, then Fake.csv rows.

    Cleaning: drop rows with an empty body (630 of the 631 are fake, so an empty
    body is itself a label leak) and drop duplicate bodies, keeping the first copy
    (duplicates split across train/test would let the model be tested on articles
    it has already seen).

    Every experiment loads through here so row order is identical everywhere,
    which (with the fixed random_state) gives every experiment the same split.
    """
    true = pd.read_csv(DATA_DIR / "True.csv")
    fake = pd.read_csv(DATA_DIR / "Fake.csv")
    true["label"] = REAL
    fake["label"] = FAKE
    df = pd.concat([true, fake], ignore_index=True)
    df[["title", "text"]] = df[["title", "text"]].fillna("")
    df = df[df["text"].str.strip() != ""]
    df = df.drop_duplicates(subset="text", keep="first")
    return df.reset_index(drop=True)


def run_experiment(features, labels, name, model=None, tfidf_kwargs=None,
                   test_features=None, test_labels=None):
    """Split, fit, evaluate, save metrics to results/{name}.json.

    features: a 1-D sequence of strings (list / Series) -> TF-IDF is fitted on it;
              or a 2-D numeric matrix (ndarray / DataFrame) -> used as-is, standardised.
    model:    classifier to use; defaults to logistic regression.
    tfidf_kwargs: passed to TfidfVectorizer (text input only).
    test_features / test_labels: an external test set (cross-corpus, E4). When given,
              there is no split: the model trains on all of features/labels.

    Returns the metrics dict plus a "pipeline" key holding the fitted model
    (the pipeline is not written to JSON).
    """
    labels = np.asarray(labels)
    is_matrix = getattr(features, "ndim", 1) == 2

    if test_features is None:
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=TEST_SIZE, stratify=labels, random_state=RANDOM_STATE
        )
    else:
        X_train, y_train = features, labels
        X_test, y_test = test_features, np.asarray(test_labels)

    clf = model if model is not None else LogisticRegression(max_iter=1000)
    if is_matrix:
        pipeline = Pipeline([("scale", StandardScaler()), ("clf", clf)])
    else:
        pipeline = Pipeline([("tfidf", TfidfVectorizer(**(tfidf_kwargs or {}))), ("clf", clf)])

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary", pos_label=FAKE, zero_division=0
    )
    metrics = {
        "name": name,
        "input": "feature_matrix" if is_matrix else "text",
        "model": type(clf).__name__,
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "majority_baseline": float(np.bincount(y_test).max() / len(y_test)),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        # rows = true [real, fake], columns = predicted [real, fake]
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=[REAL, FAKE]).tolist(),
    }

    # Robustness: refit an identical, unfitted copy on N_SPLITS - 1 further random
    # stratified splits, so every accuracy can be reported as mean +/- SD. The
    # headline numbers and confusion matrix above stay those of the fixed split.
    # (Not applicable to a fixed external test set, where there is nothing to resplit.)
    if test_features is None:
        accuracies = [metrics["accuracy"]]
        for seed in range(RANDOM_STATE + 1, RANDOM_STATE + N_SPLITS):
            X_tr, X_te, y_tr, y_te = train_test_split(
                features, labels, test_size=TEST_SIZE, stratify=labels, random_state=seed
            )
            accuracies.append(float(accuracy_score(y_te, clone(pipeline).fit(X_tr, y_tr).predict(X_te))))
        metrics["accuracy_splits"] = accuracies
        metrics["accuracy_mean"] = float(np.mean(accuracies))
        metrics["accuracy_sd"] = float(np.std(accuracies, ddof=1))

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULTS_DIR / f"{name}.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return {**metrics, "pipeline": pipeline}


def print_metrics(result):
    print(f"{result['name']}  (n_train={result['n_train']}, n_test={result['n_test']})")
    print(f"  majority baseline {result['majority_baseline']:.4f}")
    for metric in ("accuracy", "precision", "recall", "f1"):
        print(f"  {metric:<17} {result[metric]:.4f}")
    if "accuracy_mean" in result:
        print(f"  accuracy over {len(result['accuracy_splits'])} splits  "
              f"{result['accuracy_mean']:.4f} +/- {result['accuracy_sd']:.4f}")
    print("  confusion matrix (rows true real/fake, cols predicted real/fake):")
    for row in result["confusion_matrix"]:
        print("   ", row)


def save_top_tokens(result, k=30):
    """Print and save the k strongest logistic regression coefficients per class.

    Positive coefficients push towards class 1 (fake), negative towards class 0 (real).
    Written to results/{name}_tokens.json for the figures script.
    """
    pipeline = result["pipeline"]
    vocab = pipeline.named_steps["tfidf"].get_feature_names_out()
    coefs = pipeline.named_steps["clf"].coef_[0]
    order = np.argsort(coefs)
    tokens = {
        "fake": [[vocab[i], float(coefs[i])] for i in order[::-1][:k]],
        "real": [[vocab[i], float(coefs[i])] for i in order[:k]],
    }
    for cls in ("fake", "real"):
        print(f"\nTop {k} tokens -> {cls.upper()}")
        for token, coef in tokens[cls]:
            print(f"  {coef:+8.3f}  {token}")

    with open(RESULTS_DIR / f"{result['name']}_tokens.json", "w") as f:
        json.dump(tokens, f, indent=2)
    return tokens
