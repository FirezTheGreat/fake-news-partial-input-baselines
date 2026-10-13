"""E4 — Cross-corpus transfer: train on ISOT headlines, test on LIAR statements.

LIAR has no article bodies, so the comparison is headline-level. Two runs:
  e4_isot_titles   in-domain control: ISOT titles only, usual 80/20 split
  e4_liar_transfer train on all ISOT titles, test on all 12,836 LIAR statements
The control shows how much the drop is due to crossing datasets rather than to
headlines simply carrying less information than full articles.
"""

import csv

import pandas as pd

from common import DATA_DIR, FAKE, REAL, load_isot, print_metrics, run_experiment

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


if __name__ == "__main__":
    main()
