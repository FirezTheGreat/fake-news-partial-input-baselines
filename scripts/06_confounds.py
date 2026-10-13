"""E5 — Topic-matched confound check: is the signal style, or topic?

ISOT's real articles are 53% US politics ('politicsNews') and 47% world news
('worldnews'); its fake articles are all US politics and US news. So part of any
result could be "world news = real". E5 keeps only US-politics real articles and
all fake articles, then repeats the strictest conditions:

E5a  full text
E5b  fully stripped text (E3 + E3b rules)
E5c  function words only, from the stripped text
E5d  eight metadata numbers, from the stripped text

The subject field is used only to choose rows, never as model input. Chance
changes on this subset (fake becomes the majority class).
"""

from sklearn.ensemble import RandomForestClassifier

from common import FAKE, RANDOM_STATE, load_isot, print_metrics, run_experiment, save_top_tokens
from transforms import WHITESPACE_TFIDF, fully_stripped_texts, metadata_features, stripped_profile


def main():
    df = load_isot()
    stripped = fully_stripped_texts(df)
    profile = stripped_profile(stripped.tolist())  # cached by step 5

    keep = ((df["label"] == FAKE) | (df["subject"] == "politicsNews")).to_numpy()
    sub = df[keep]
    labels = sub["label"]
    print(f"topic-matched subset: {len(sub)} articles, "
          f"{(labels != FAKE).sum()} real (politicsNews) / {(labels == FAKE).sum()} fake")

    print("\n=== E5a topic-matched, full text ===")
    result = run_experiment(sub["title"] + " " + sub["text"], labels, "e5a_topic_full")
    print_metrics(result)

    print("\n=== E5b topic-matched, fully stripped ===")
    result = run_experiment(stripped[keep], labels, "e5b_topic_stripped")
    print_metrics(result)
    save_top_tokens(result, k=15)

    print("\n=== E5c topic-matched, stripped, function words only ===")
    function_words = [p["fw"] for p, k in zip(profile, keep) if k]
    result = run_experiment(function_words, labels, "e5c_topic_function_words",
                            tfidf_kwargs=WHITESPACE_TFIDF)
    print_metrics(result)
    save_top_tokens(result, k=15)

    print("\n=== E5d topic-matched, stripped, metadata only ===")
    forest = RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1)
    result = run_experiment(metadata_features(stripped[keep]), labels, "e5d_topic_metadata", model=forest)
    print_metrics(result)


if __name__ == "__main__":
    main()
