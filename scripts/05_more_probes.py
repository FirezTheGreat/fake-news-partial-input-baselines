"""More probes, all on the fully stripped text (E3 + E3b rules), plus a model check.

The new probes run on stripped text so they cannot use any marker already
identified (Reuters, datelines, credits, curly quotes). Anything they find is new.

E2d  sentiment only: eight VADER scores (title and body), random forest
E2e  named entities only: counts of each spaCy entity type per 100 words, random forest
E3c  function words only, taken from the stripped text
SVM  E1, E2a, E2b and E3b repeated with a linear SVM instead of logistic regression,
     to show the results do not depend on the choice of classifier
"""

from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC

from common import RANDOM_STATE, load_isot, print_metrics, run_experiment, save_top_tokens
from transforms import (WHITESPACE_TFIDF, entity_features, first_sentence, fully_stripped_texts,
                        function_words, sentiment_features, strip_page_furniture,
                        stripped_profile, stripped_titles_bodies)


def forest_with_importances(features, labels, name):
    forest = RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1)
    result = run_experiment(features, labels, name, model=forest)
    print_metrics(result)
    fitted = result["pipeline"].named_steps["clf"]  # run_experiment fits a copy, not `forest` itself
    importances = sorted(zip(features.columns, fitted.feature_importances_), key=lambda p: -p[1])
    print("  feature importances (top 8):")
    for feature, importance in importances[:8]:
        print(f"    {importance:.3f}  {feature}")


def main():
    df = load_isot()
    labels = df["label"]
    titles, bodies = stripped_titles_bodies(df)
    titles, bodies = titles.map(strip_page_furniture), bodies.map(strip_page_furniture)
    stripped = (titles + " " + bodies).tolist()

    print("=== E2d sentiment only (stripped text) ===")
    forest_with_importances(sentiment_features(titles.tolist(), bodies.tolist()), labels, "e2d_sentiment")

    profile = stripped_profile(stripped)

    print("\n=== E2e named entities only (stripped text) ===")
    forest_with_importances(entity_features(profile, stripped), labels, "e2e_entities")

    print("\n=== E3c function words only, from stripped text ===")
    result = run_experiment([p["fw"] for p in profile], labels, "e3c_stripped_function_words",
                            tfidf_kwargs=WHITESPACE_TFIDF)
    print_metrics(result)
    save_top_tokens(result, k=15)

    print("\n=== Model check: linear SVM ===")
    full = (df["title"] + " " + df["text"]).tolist()
    svm_inputs = [
        ("e1_svm", full, None),
        ("e2a_svm", df["text"].map(first_sentence), None),
        ("e2b_svm", function_words(full), WHITESPACE_TFIDF),
        ("e3b_svm", fully_stripped_texts(df), None),
    ]
    for name, texts, tfidf_kwargs in svm_inputs:
        result = run_experiment(texts, labels, name, model=LinearSVC(random_state=RANDOM_STATE),
                                tfidf_kwargs=tfidf_kwargs)
        print_metrics(result)


if __name__ == "__main__":
    main()
