"""E3 — Artifact removal: strip source markers, retrain on full text (rules in transforms.py).

E3  (as planned) applied identically to real and fake articles:
  1. the dateline, e.g. 'WASHINGTON (Reuters) - '
  2. the leading sentence of the body
  3. the word 'Reuters' anywhere (title or body, any case)
E3b additionally strips the fake sites' page furniture, i.e. text that is not
article prose, and normalises typography:
  4. media credits ('Featured image via ... Getty Images', 'Video via YouTube',
     'Screenshot via ...'), to the end of the line
  5. URLs and pic.twitter.com links
  6. Twitter @handles
  7. media tags: '[Video]', '(Tweets)', 'WATCH:', 'BREAKING:', 'READ MORE:'
  8. every apostrophe and quotation mark (curly or straight) replaced by a space,
     ellipsis and dashes mapped to ASCII: the fake scrape lost these characters
     (no curly quotes at all in fake vs 50.8% of real; "Trump s", "couldn t")

The E1 -> E3 / E3b gap measures how much of the signal lives in removable
markers (result: very little). The top coefficients printed afterwards show
what is still separable once these are gone.
"""

from common import load_isot, print_metrics, run_experiment, save_top_tokens
from transforms import stripped_titles_bodies, strip_page_furniture


def main():
    df = load_isot()
    titles, bodies = stripped_titles_bodies(df)

    print("=== E3 source markers stripped ===")
    result = run_experiment(titles + " " + bodies, df["label"], "e3_stripped")
    print_metrics(result)
    save_top_tokens(result)

    print("\n=== E3b source markers + page furniture stripped ===")
    texts = titles.map(strip_page_furniture) + " " + bodies.map(strip_page_furniture)
    result = run_experiment(texts, df["label"], "e3b_furniture_stripped")
    print_metrics(result)
    save_top_tokens(result)


if __name__ == "__main__":
    main()
