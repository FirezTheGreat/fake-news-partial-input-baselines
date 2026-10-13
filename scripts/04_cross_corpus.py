"""E4 — Cross-corpus transfer.

E4 (headlines, LIAR). LIAR has no article bodies, so the comparison is headline-level:
  e4_isot_titles      in-domain control: ISOT titles only, usual 80/20 split
  e4_liar_transfer    train on all ISOT titles, test on all 12,836 LIAR statements
  e4_liar_no_halftrue the same without the ambiguous half-true label
The control shows how much the drop is due to crossing datasets rather than to
headlines simply carrying less information than full articles.

E4b (full articles, McIntire "fake or real news", 6,335 articles). Its real
articles come from many mainstream outlets (not Reuters), so a model that learned
"Reuters style = real" should fail on it:
  e4b_mcintire_control         in-domain control: McIntire alone, usual split
  e4b_mcintire_full            train ISOT full text, test McIntire full text
  e4b_mcintire_stripped        both sides stripped with the E3 + E3b rules
  e4b_mcintire_function_words  stripped function words on both sides
  e4b_reverse                  train McIntire, test ISOT (full text)
Source: github.com/joolsa/fake_real_news_dataset (fake_or_real_news.csv).
"""

import csv

import pandas as pd

from common import DATA_DIR, FAKE, REAL, load_isot, print_metrics, run_experiment
from transforms import WHITESPACE_TFIDF, fully_stripped_texts, stripped_profile

# The TSVs have no header row; column names are from Wang (2017).
LIAR_COLUMNS = [
    "id", "label", "statement", "subject", "speaker", "job", "state", "party",
    "barely_true_counts", "false_counts", "half_true_counts", "mostly_true_counts",
    "pants_on_fire_counts", "context",
]
# Six-way labels collapsed to binary: the three "true" grades are real, the rest fake.
LIAR_BINARY = {
    "true": REAL, "mostly-true": REAL, "half-true": REAL,
    "barely-true": FAKE, "false": FAKE, "pants-fire": FAKE,
}


def load_liar():
    parts = [
        pd.read_csv(DATA_DIR / "liar" / f"{split}.tsv", sep="\t", header=None,
                    names=LIAR_COLUMNS, quoting=csv.QUOTE_NONE)
        for split in ("train", "valid", "test")
    ]
    liar = pd.concat(parts, ignore_index=True)
    liar["binary"] = liar["label"].map(LIAR_BINARY)
    return liar


def load_mcintire():
    """McIntire corpus, cleaned like ISOT: empty bodies and duplicate bodies dropped."""
    df = pd.read_csv(DATA_DIR / "mcintire" / "fake_or_real_news.csv")
    df[["title", "text"]] = df[["title", "text"]].fillna("")
    df = df[df["text"].str.strip() != ""].drop_duplicates(subset="text", keep="first")
    df["label"] = df["label"].map({"REAL": REAL, "FAKE": FAKE})
    return df.reset_index(drop=True)


def main():
    isot = load_isot()
    liar = load_liar()
    print(f"LIAR: {len(liar)} statements, six-way labels {liar['label'].value_counts().to_dict()}")

    print("\n=== E4 control: ISOT titles only, in-domain ===")
    result = run_experiment(isot["title"], isot["label"], "e4_isot_titles")
    print_metrics(result)

    print("\n=== E4 transfer: train ISOT titles, test LIAR ===")
    result = run_experiment(isot["title"], isot["label"], "e4_liar_transfer",
                            test_features=liar["statement"], test_labels=liar["binary"])
    print_metrics(result)

    # Sensitivity check on the label mapping: half-true is the judgement call, so drop it.
    print("\n=== E4 transfer, LIAR without half-true ===")
    clear = liar[liar["label"] != "half-true"]
    result = run_experiment(isot["title"], isot["label"], "e4_liar_no_halftrue",
                            test_features=clear["statement"], test_labels=clear["binary"])
    print_metrics(result)

    mc = load_mcintire()
    print(f"\nMcIntire: {len(mc)} articles after cleaning, "
          f"{(mc['label'] == REAL).sum()} real / {(mc['label'] == FAKE).sum()} fake")
    isot_full, mc_full = isot["title"] + " " + isot["text"], mc["title"] + " " + mc["text"]
    isot_stripped, mc_stripped = fully_stripped_texts(isot), fully_stripped_texts(mc)

    runs = [
        ("e4b_mcintire_control", mc_full, mc["label"], None, None, None),
        ("e4b_mcintire_full", isot_full, isot["label"], mc_full, mc["label"], None),
        ("e4b_mcintire_stripped", isot_stripped, isot["label"], mc_stripped, mc["label"], None),
        ("e4b_mcintire_function_words",
         [p["fw"] for p in stripped_profile(isot_stripped.tolist())], isot["label"],
         [p["fw"] for p in stripped_profile(mc_stripped.tolist(), cache_name="mcintire_profile")],
         mc["label"], WHITESPACE_TFIDF),
        ("e4b_reverse", mc_full, mc["label"], isot_full, isot["label"], None),
    ]
    for name, train_x, train_y, test_x, test_y, tfidf_kwargs in runs:
        print(f"\n=== {name} ===")
        result = run_experiment(train_x, train_y, name, tfidf_kwargs=tfidf_kwargs,
                                test_features=test_x, test_labels=test_y)
        print_metrics(result)


if __name__ == "__main__":
    main()
