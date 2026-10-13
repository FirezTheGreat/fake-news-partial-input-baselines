"""E2 — Partial-input probes: models deliberately denied the article's content.

E2a  first sentence of the body only
E2b  function words only (spaCy POS tags; cached to data/cache/)
E2c  eight metadata numbers only, random forest
plus a body-only run (no title) used by the degradation figure.
"""

from sklearn.ensemble import RandomForestClassifier

from common import RANDOM_STATE, load_isot, print_metrics, run_experiment, save_top_tokens
from transforms import WHITESPACE_TFIDF, first_sentence, function_words, metadata_features


def main():
    df = load_isot()
    labels = df["label"]
    full = (df["title"] + " " + df["text"]).tolist()

    print("=== E2a first sentence only ===")
    result = run_experiment(df["text"].map(first_sentence), labels, "e2a_first_sentence")
    print_metrics(result)
    save_top_tokens(result, k=15)

    print("\n=== E2b function words only ===")
    result = run_experiment(function_words(full), labels, "e2b_function_words",
                            tfidf_kwargs=WHITESPACE_TFIDF)
    print_metrics(result)
    save_top_tokens(result, k=15)

    print("\n=== E2c metadata only ===")
    features = metadata_features(full)
    forest = RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1)
    result = run_experiment(features, labels, "e2c_metadata", model=forest)
    print_metrics(result)
    fitted = result["pipeline"].named_steps["clf"]  # run_experiment fits a copy, not `forest` itself
    importances = sorted(zip(features.columns, fitted.feature_importances_), key=lambda p: -p[1])
    print("  feature importances:")
    for feature, importance in importances:
        print(f"    {importance:.3f}  {feature}")

    print("\n=== body only (no title), for the degradation figure ===")
    result = run_experiment(df["text"], labels, "e2_body_only")
    print_metrics(result)


if __name__ == "__main__":
    main()
