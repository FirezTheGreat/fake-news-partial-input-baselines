"""E1 — Baseline: TF-IDF + logistic regression on full text (title + body)."""

from common import load_isot, print_metrics, run_experiment, save_top_tokens


def main():
    df = load_isot()
    texts = df["title"] + " " + df["text"]

    result = run_experiment(texts, df["label"], "e1_baseline")
    print_metrics(result)
    save_top_tokens(result)


if __name__ == "__main__":
    main()
