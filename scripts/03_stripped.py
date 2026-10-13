"""E3 — Artifact removal: strip source markers, retrain on full text.

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
  8. curly quotes, ellipsis and dashes mapped to their plain ASCII forms
     (the fake scrape has no curly quotes at all; 50.8% of real articles do)

The E1 -> E3 / E3b gap measures how much of the signal lives in removable
markers (result: very little). The top coefficients printed afterwards show
what is still separable once these are gone.
"""

import re

from common import load_isot, print_metrics, run_experiment, save_top_tokens

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
TYPOGRAPHY = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                            "…": "...", "–": "-", "—": "-"})


def strip_artifacts(text):
    text = DATELINE.sub("", text, count=1)
    text = LEADING_SENTENCE.sub("", text, count=1)
    return REUTERS.sub("", text)


def strip_page_furniture(text):
    for pattern in (IMAGE_CREDIT, URL, HANDLE, MEDIA_TAG):
        text = pattern.sub(" ", text)
    return text.translate(TYPOGRAPHY)


def main():
    df = load_isot()
    titles = df["title"].map(lambda t: REUTERS.sub("", t))
    bodies = df["text"].map(strip_artifacts)

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
