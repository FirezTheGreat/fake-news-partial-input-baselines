"""Builds report/Code_Walkthrough.pdf: a line-by-line guide to the code, a glossary, the
presenter brief and viva questions. Code is read from the scripts themselves, so the
listings always match the files. Rendered to PDF with Microsoft Edge (headless).

    .venv\\Scripts\\python report\\build_walkthrough.py
"""

import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "report" / "Code_Walkthrough.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
RESULTS = ROOT / "results"


def R(name):
    with open(RESULTS / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def pct(name):
    return f"{R(name)['accuracy']:.1%}"


# ---------------------------------------------------------------- mini markup

def md(text):
    """`code`, **bold**, paragraphs split by blank lines, '- ' bullets."""
    def inline(s):
        codes = []

        def keep(m):
            codes.append(f"<code>{m.group(1)}</code>")
            return f"\x00{len(codes) - 1}\x00"
        s = html.escape(s, quote=False)
        s = re.sub(r"`([^`]+)`", keep, s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<![\w*])\*(?=\S)([^*]+?)(?<=\S)\*(?![\w*])", r"<i>\1</i>", s)
        return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)

    out = []
    for block in re.split(r"\n\s*\n", text.strip("\n")):
        lines = [l.strip() for l in block.strip().split("\n")]
        bullet = re.compile(r"^(- |\d+\. )")
        if lines[0].startswith("### "):
            out.append(f"<h3>{inline(lines[0][4:])}</h3>")
            if len(lines) > 1:
                out.append(f"<p>{inline(' '.join(lines[1:]))}</p>")
        elif bullet.match(lines[0]):
            items, cur = [], None
            for l in lines:
                if bullet.match(l):
                    if cur is not None:
                        items.append(cur)
                    cur = bullet.sub("", l)
                else:
                    cur += " " + l
            items.append(cur)
            tag = "ul" if lines[0].startswith("- ") else "ol"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{tag}>")
        else:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n".join(out)


def code_block(path, start, end):
    lines = (ROOT / path).read_text(encoding="utf-8").split("\n")
    rows = []
    for n in range(start, end + 1):
        rows.append(f'<span class="ln">{n}</span>{html.escape(lines[n - 1]) or " "}')
    return '<pre class="code">' + "\n".join(rows) + "</pre>"


def table(headers, rows, cls=""):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def md_inline(s):
    return md(s)[3:-4] if not s.startswith("- ") else md(s)


# ---------------------------------------------------------------- coverage check

COVERAGE = {}


def walk(path, chunks):
    """Render a file as (line range, explanation) chunks and record coverage."""
    COVERAGE[path] = [(a, b) for a, b, _ in chunks]
    parts = []
    for a, b, text in chunks:
        label = f"Line {a}" if a == b else f"Lines {a}–{b}"
        parts.append(f'<div class="chunk"><div class="where">{path} · {label}</div>'
                     f"{code_block(path, a, b)}<div class='expl'>{md(text)}</div></div>")
    return "\n".join(parts)


def check_coverage():
    for path, ranges in COVERAGE.items():
        lines = (ROOT / path).read_text(encoding="utf-8").split("\n")
        covered = set()
        for a, b in ranges:
            covered.update(range(a, b + 1))
        missing = [i for i, l in enumerate(lines, 1) if l.strip() and i not in covered]
        if missing:
            print(f"  NOTE {path}: lines not shown: {missing}")


# ---------------------------------------------------------------- worked example

def worked_example():
    import spacy
    from common import load_isot
    from transforms import (FUNCTION_POS, first_sentence, metadata_features, strip_artifacts,
                            strip_page_furniture, REUTERS)

    df = load_isot()
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])
    out = []
    for idx, heading, limit in ((0, "A real (Reuters) article — row 0", 520),
                                (28000, "A fake article — row 28,000", 2000)):
        title, body = df.loc[idx, "title"], df.loc[idx, "text"]
        e3_body = strip_artifacts(body)
        e3b = strip_page_furniture(REUTERS.sub("", title)) + " " + strip_page_furniture(e3_body)
        fw = " ".join(t.lower_ for t in nlp(e3b) if t.pos_ in FUNCTION_POS)
        meta = metadata_features([title + " " + body]).iloc[0]

        def cut(s, n=limit):
            return html.escape(s if len(s) <= n else s[:n] + " …")

        meta_rows = "".join(f"<tr><td><code>{k}</code></td><td>{v:,.3f}</td></tr>"
                            if isinstance(v, float) and v % 1 else
                            f"<tr><td><code>{k}</code></td><td>{int(v):,}</td></tr>" for k, v in meta.items())
        out.append(f"""
<h3>{heading}</h3>
<div class="ex"><div class="exl">Title</div><div class="ext">{cut(title)}</div></div>
<div class="ex"><div class="exl">Body (as stored)</div><div class="ext">{cut(body)}</div></div>
<div class="ex"><div class="exl">E2a — first sentence</div><div class="ext">{cut(first_sentence(body))}</div></div>
<div class="ex"><div class="exl">E3 — markers stripped (body)</div><div class="ext">{cut(e3_body)}</div></div>
<div class="ex"><div class="exl">E3b — fully stripped (title + body)</div><div class="ext">{cut(e3b)}</div></div>
<div class="ex"><div class="exl">E3c — function words of the E3b text</div><div class="ext mono">{cut(fw, 700)}</div></div>
<div class="ex"><div class="exl">E2c — the eight numbers (unstripped title + body)</div><div class="ext"><table class="mini">{meta_rows}</table></div></div>
""")
    return "\n".join(out)


# ---------------------------------------------------------------- content

def build():
    E1 = R("e1_baseline")
    (tn, fp), (fn, tp) = E1["confusion_matrix"]
    results_rows = []
    for line in (RESULTS / "results_table.md").read_text(encoding="utf-8").splitlines()[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        results_rows.append(cells)

    S = []  # sections, in order
    add = S.append

    # ---------------- cover + contents
    add("""
<div class="cover">
  <div class="kicker">WSMA lab project · code walkthrough and viva guide</div>
  <h1 class="title">Partial-Input Baselines Reveal Construction Artifacts in Fake News Benchmarks</h1>
  <p class="sub">Every script explained line by line, every abbreviation spelled out, the presenter
  brief and the questions an examiner is likely to ask.</p>
  <p class="sub small">Generated from the code and results in the repository. Numbers are from the fixed
  test split (seed 42) unless a mean ± SD is given.</p>
</div>
<div class="toc">
<h2 class="nonum">Contents</h2>
<ol>
<li><a href="#s1">How to use this guide</a></li>
<li><a href="#s2">The project in two minutes</a></li>
<li><a href="#s3">Glossary: abbreviations and terms</a></li>
<li><a href="#s4">Core ideas you need before reading the code</a></li>
<li><a href="#s5">How the files fit together</a></li>
<li><a href="#s6">Worked example: one real and one fake article through every view</a></li>
<li><a href="#s7">Line-by-line walkthrough</a>
  <ol>
  <li><a href="#w-run">run.bat and run_all.py — the one command</a></li>
  <li><a href="#w-common">scripts/common.py — the shared experiment harness</a></li>
  <li><a href="#w-transforms">scripts/transforms.py — the restricted views of an article</a></li>
  <li><a href="#w-00">scripts/00_get_data.py — fetch and verify data</a></li>
  <li><a href="#w-01">scripts/01_baseline.py — E1</a></li>
  <li><a href="#w-02">scripts/02_partial_input.py — E2a, E2b, E2c</a></li>
  <li><a href="#w-03">scripts/03_stripped.py — E3, E3b</a></li>
  <li><a href="#w-04">scripts/04_cross_corpus.py — E4, E4b</a></li>
  <li><a href="#w-05">scripts/05_more_probes.py — E2d, E2e, E3c, SVM check</a></li>
  <li><a href="#w-06">scripts/06_confounds.py — E5</a></li>
  <li><a href="#w-07">scripts/07_figures.py — figures and results table</a></li>
  </ol></li>
<li><a href="#s8">Results: what every number means</a></li>
<li><a href="#s9">Presenter brief</a></li>
<li><a href="#s10">Viva questions and answers</a></li>
</ol>
</div>
""")

    # ---------------- 1
    add('<h2 id="s1">1. How to use this guide</h2>' + md(r"""
This guide is for presenting and defending the project on your own: every question, about the
results or about a line of code, comes to you, so read all of it. It explains what every line of the
experiment code does and, more importantly, **why** it is written that way, because "why" is what an
examiner asks.

Suggested reading order:

1. Sections 2, 3 and 4: the story, the vocabulary, the core ideas.
2. Section 7.2 (`common.py`) and 7.3 (`transforms.py`): every experiment goes through them, so most
   code questions land here.
3. Section 6 (worked example) and the rest of section 7, one script per experiment.
4. Sections 8, 9 and 10: the results, how to present them, and the questions to expect.

Code listings are copied from the files when this PDF is built, with the real line numbers, so
"line 78 of common.py" in this guide is line 78 in the editor. Blank lines are left out.
"""))

    # ---------------- 2
    add('<h2 id="s2">2. The project in two minutes</h2>' + md(fr"""
**The one-line story:** *I built a fake news detector, got 98%, then proved the 98% is fake.*

**The dataset.** ISOT is the most widely used fake news benchmark. Its 44,898 articles come in two
files: `True.csv` (21,417 articles, all from the Reuters news agency) and `Fake.csv` (23,481
articles from websites flagged as unreliable). Published classifiers on it report 98–99% accuracy.

**The problem.** Every real article comes from one newsroom and every fake one from a different set
of websites. A model can therefore get the label right by recognising **who wrote the article**
(Reuters' house style) without ever judging **whether it is true**. Analogy: if every cancer scan
came from Hospital A and every healthy scan from Hospital B, a model can reach 99% by recognising
the hospital's scanner, and it fails at Hospital C.

**The method.** *Partial-input baselines* (Gururangan et al., 2018): train models that are
deliberately denied the information they would need to do the task properly, such as the
article's content words. If such a crippled model still scores far above chance, the dataset is
leaking the answer through something other than the content.

**What we found:**

- Our detector (E1, full text): **{pct('e1_baseline')}**. Chance (always guessing the bigger class) is
  {E1['majority_baseline']:.1%}.
- First sentence only (E2a): **{pct('e2a_first_sentence')}**, higher than the full article.
- Only grammatical "function words" and punctuation, no nouns, verbs or names (E2b):
  **{pct('e2b_function_words')}**.
- Eight numbers such as word count and question marks, no words at all (E2c): **{pct('e2c_metadata')}**.
- Every source marker stripped from both classes (E3b): still **{pct('e3b_furniture_stripped')}**.
- US politics only, so topic cannot help, fully stripped, function words only (E5c):
  **{pct('e5c_topic_function_words')}** against {R('e5c_topic_function_words')['majority_baseline']:.1%} chance.
- Tested on other datasets: **{pct('e4_liar_transfer')}** on LIAR (below its
  {R('e4_liar_transfer')['majority_baseline']:.1%} chance) and **{pct('e4b_mcintire_full')}** on McIntire's
  full articles ({R('e4b_mcintire_full')['majority_baseline']:.1%} chance).

**Conclusion.** The 98% measures how well a model recognises the publisher's writing style, not
how well it detects false news. ISOT cannot tell the two apart, so accuracy on ISOT says little
about fake news detection.

**How the experiments map to the research questions in the report:**
""") + table(["Research question", "Experiments", "Answer"], [
        ["**RQ1** How much accuracy remains when the model is denied the content?", "E2a–E2e",
         "Almost all of it: 96.8% from function words alone."],
        ["**RQ2** How much is lost when source markers are removed (Reuters' markers, then both classes')?",
         "E3 (Reuters markers), E3b (both pipelines' markers), E3c", "About one point. The signal is in the whole writing style."],
        ["**RQ3** Does the detector transfer to independently labelled data?", "E4 (LIAR), E4b (McIntire)",
         "No: below chance on LIAR, 61% on McIntire."],
        ["**RQ4** Is it style, or topic, or the classifier?", "E5a–E5d, SVM check",
         "Style. It survives topic matching, and a different classifier does slightly better, not worse."],
    ]))

    # ---------------- 3 glossary
    abbrev = [
        ("WSMA", "Web and Social Media Analytics", "The course this lab project is for."),
        ("ISOT", "Information Security and Object Technology", "The research lab at the University of Victoria (Canada) that built the dataset; the dataset is named after it (Ahmed et al., 2017)."),
        ("LIAR", "not an abbreviation", "A fact-checking dataset named after its paper, “Liar, Liar Pants on Fire” (Wang, 2017). 12,836 short political statements rated by PolitiFact."),
        ("McIntire", "not an abbreviation", "The “fake or real news” dataset compiled by George McIntire: 6,335 full articles (6,059 after cleaning); real ones from mainstream outlets, not Reuters."),
        ("E1 … E5", "Experiment 1 … 5", "Our own labels for the experimental conditions (E2a, E3b etc. are variants)."),
        ("RQ", "Research Question", "RQ1–RQ4 in the report."),
        ("O1–O7", "Objectives 1–7", "The objectives listed in section 4.1 of the report."),
        ("ML", "Machine Learning", "Programs that learn a rule from examples instead of being given the rule."),
        ("NLP", "Natural Language Processing", "Computing with human language text."),
        ("TF", "Term Frequency", "How often a word occurs in one document."),
        ("IDF", "Inverse Document Frequency", "How rare a word is across all documents; rare words get a higher weight."),
        ("TF-IDF", "Term Frequency – Inverse Document Frequency", "TF × IDF: turns each article into a list of numbers, one per vocabulary word. See section 4.1."),
        ("LR", "Logistic Regression", "The main classifier: a weighted sum of features turned into a probability. See 4.2."),
        ("SVM", "Support Vector Machine", "Another linear classifier, used as a check. See 4.4."),
        ("LinearSVC", "Linear Support Vector Classifier", "scikit-learn's name for its linear SVM class."),
        ("RF", "Random Forest", "Many decision trees voting; used for the numeric (non-text) probes. See 4.3."),
        ("POS", "Part of Speech", "The grammatical category of a word: noun, verb, determiner, etc."),
        ("NER", "Named Entity Recognition", "Finding names of people, places, organisations, dates etc. in text."),
        ("VADER", "Valence Aware Dictionary and sEntiment Reasoner", "A rule-based sentiment scorer for English (in NLTK). Gives negative, neutral, positive and compound scores."),
        ("NLTK", "Natural Language Toolkit", "Python NLP library; we use only its VADER sentiment scorer."),
        ("spaCy", "not an abbreviation", "Python NLP library; we use it for POS tagging and NER."),
        ("en_core_web_sm", "English · core pipeline · trained on web text · small", "The spaCy model we load."),
        ("sklearn", "scikit-learn", "The Python machine-learning library used for TF-IDF, the classifiers, splitting and metrics."),
        ("NumPy", "Numerical Python", "Library for arrays of numbers and maths on them."),
        ("pandas", "from “panel data”", "Library for tables (DataFrames) and columns (Series)."),
        ("SD", "Standard Deviation", "How spread out a set of numbers is. “98.5% ± 0.2%” means the five runs varied by about 0.2 points."),
        ("F1", "F1 score (F-measure with β = 1)", "The harmonic mean of precision and recall; the 1 means both are weighted equally. See 4.5."),
        ("TP / FP / TN / FN", "True Positive / False Positive / True Negative / False Negative", "The four cells of the confusion matrix. “Positive” = predicted fake here."),
        ("CSV / TSV", "Comma- / Tab-Separated Values", "Plain-text table formats. ISOT and McIntire are CSV, LIAR is TSV."),
        ("JSON", "JavaScript Object Notation", "Plain-text format for structured data; every experiment saves its metrics as JSON."),
        ("PNG / PDF", "Portable Network Graphics / Portable Document Format", "Image format of the figures / this document."),
        ("URL", "Uniform Resource Locator", "A web address. Removed from articles in E3b."),
        ("HTTP(S)", "HyperText Transfer Protocol (Secure)", "How web pages are fetched; also appears as “https” in article text."),
        ("SHA-256", "Secure Hash Algorithm, 256-bit", "Produces a 64-character fingerprint of a file; any change to the file changes it. Used to verify the datasets."),
        ("MD5", "Message Digest 5", "An older, faster fingerprint function; used only to label the caches, not for security."),
        ("regex", "regular expression", "A pattern language for matching text, e.g. `@\\w+` matches Twitter handles."),
        ("NaN", "Not a Number", "pandas' marker for a missing value."),
        ("venv / .venv", "virtual environment", "A private copy of Python with the project's exact library versions."),
        ("pip", "“pip installs packages”", "Python's package installer."),
        ("CPU / RAM", "Central Processing Unit / Random-Access Memory", "Processor and working memory."),
        ("UTF-8", "Unicode Transformation Format, 8-bit", "The standard way to store any character (curly quotes, “→”) as bytes."),
        ("cp1252", "Windows code page 1252", "Windows' old default character set; it cannot print some characters, hence `PYTHONUTF8=1`."),
        ("GOP", "Grand Old Party", "Nickname of the US Republican Party; a strong “fake” token."),
        ("EDT", "Eastern Daylight Time", "US time zone; appears in Reuters timestamps."),
        ("NYT / NPR", "The New York Times / National Public Radio", "Mainstream outlets among McIntire's real articles."),
        ("BERT", "Bidirectional Encoder Representations from Transformers", "A large pretrained neural language model; often suggested as “why not use this?”. See section 10."),
        ("NLI", "Natural Language Inference", "The task where Gururangan et al. first showed partial-input artifacts (SNLI = Stanford NLI, MultiNLI = Multi-Genre NLI)."),
        ("DOI", "Digital Object Identifier", "Permanent ID for a publication, e.g. 10.18653/v1/N18-2017."),
        ("arXiv", "pronounced “archive”", "Free preprint server; papers there are not necessarily peer reviewed (Verma 2026 is a preprint)."),
    ]
    venues = [
        ("ACL", "Association for Computational Linguistics", "The main NLP society; also its annual conference."),
        ("NAACL-HLT", "North American Chapter of the ACL: Human Language Technologies", "Conference (Gururangan et al. 2018)."),
        ("EACL", "European Chapter of the ACL", "Conference (Zhou et al. 2021)."),
        ("EMNLP", "Empirical Methods in Natural Language Processing", "Conference (Schuster et al. 2019; Gardner et al. 2020 in “Findings of EMNLP”)."),
        ("IJCNLP", "International Joint Conference on Natural Language Processing", "Held jointly with EMNLP 2019."),
        ("*SEM", "Joint Conference on Lexical and Computational Semantics", "Conference (Poliak et al. 2018)."),
        ("ICLR", "International Conference on Learning Representations", "Conference (Kaushik et al. 2020)."),
        ("SIGKDD", "Special Interest Group on Knowledge Discovery and Data Mining (of the ACM)", "Publishes the Explorations newsletter (Shu et al. 2017)."),
        ("ACM", "Association for Computing Machinery", "Computing society."),
        ("ISDDC", "International Conference on Intelligent, Secure and Dependable Systems in Distributed and Cloud Environments", "Where the ISOT paper appeared (Ahmed et al. 2017)."),
        ("LNCS", "Lecture Notes in Computer Science", "Springer's book series that published the ISDDC proceedings."),
    ]
    pos_tags = [
        ("DET", "Determiner", "the, a, this, these, every", "kept"),
        ("PRON", "Pronoun", "he, you, it, we, anyone", "kept"),
        ("ADP", "Adposition (preposition)", "of, in, on, via, amid", "kept"),
        ("AUX", "Auxiliary verb", "is, was, has, would, could", "kept"),
        ("CCONJ", "Coordinating conjunction", "and, but, or", "kept"),
        ("SCONJ", "Subordinating conjunction", "whether, because, if, that", "kept"),
        ("PART", "Particle", "not, to (in “to go”), ’s", "kept"),
        ("PUNCT", "Punctuation", ". , ! ? : - ( )", "kept"),
        ("NOUN / PROPN", "Noun / Proper noun", "minister, budget / Trump, Reuters", "dropped"),
        ("VERB / ADJ / ADV", "Verb / Adjective / Adverb", "said, voted / huge / sharply", "dropped"),
        ("NUM", "Numeral", "2018, 14", "dropped"),
    ]
    ents = [
        ("PERSON", "People, including fictional"), ("ORG", "Organisations: companies, agencies, parties"),
        ("GPE", "Geo-Political Entity: countries, cities, states"),
        ("NORP", "Nationalities Or Religious or Political groups (e.g. Republicans, Muslim)"),
        ("LOC", "Non-GPE locations: mountains, seas"), ("FAC", "Facilities: buildings, airports, bridges"),
        ("DATE / TIME", "Dates and periods / times of day"), ("CARDINAL", "Numbers that are not another type"),
        ("ORDINAL", "first, second …"), ("MONEY / PERCENT / QUANTITY", "Amounts with units"),
        ("EVENT / LAW / WORK_OF_ART / PRODUCT / LANGUAGE", "Named events, laws, titles of works, products, languages"),
    ]
    terms = [
        ("Dataset artifact", "A pattern in a dataset that predicts the label but has nothing to do with the task. “(Reuters)” appears only in real articles: an artifact."),
        ("Construction artifact", "An artifact created by how the dataset was built, e.g. collecting each class from a different source."),
        ("Shortcut learning", "A model solving a task through an easy, irrelevant cue instead of the intended skill (Geirhos et al., 2020)."),
        ("Partial-input baseline / probe", "A model deliberately given only part of the input. If it still does well, that part leaks the label. Our core method."),
        ("Leakage", "Information reaching the model that should not, making scores look better than the model really is. Also: test-set information leaking into training."),
        ("Provenance / source marker", "Text that reveals who published the article: the agency name, datelines, image credits, URLs."),
        ("Dateline", "The place-and-agency prefix of a wire story, e.g. “WASHINGTON (Reuters) - ”."),
        ("Wire service / newswire", "An agency (like Reuters) that writes news for other outlets to republish; has a strict house style."),
        ("Page furniture", "Text on a web page that is not article prose: image credits, “[Video]” tags, embedded links, handles."),
        ("Typography", "The characters used for punctuation: curly ’ ” versus straight ' \" quotes, en/em dashes, “…”."),
        ("Function words", "Grammatical words carrying little meaning (the, of, is, and) plus punctuation. Opposite: content words (nouns, verbs, adjectives, names)."),
        ("Register / genre", "The style of writing typical of a setting: wire reporting (“said”, “told reporters”) vs. opinion blogging (“this”, “just”, “you”)."),
        ("Ablation", "Removing a component and re-measuring, to see what it contributed. E3/E3b are ablations."),
        ("Confound", "A third factor that could explain a result. Topic is a possible confound here (real has world news; fake does not); E5 removes it."),
        ("Topic-matched", "Restricted so both classes cover the same topic (E5: US politics only)."),
        ("Cross-corpus evaluation / transfer", "Train on one dataset, test on another. The honest test of whether a model learned the task or the dataset."),
        ("In-domain control", "The same model tested on its own dataset, to separate “crossing datasets is hard” from “this kind of input is weak”."),
        ("Chance / majority baseline", "Accuracy of always guessing the most common class in the test set. Measured, not assumed to be 50%."),
        ("Train / test split", "Training data is used to fit the model; the held-out test data is used only to measure it."),
        ("Stratified split", "A split that keeps the real/fake proportions identical in train and test."),
        ("Random seed / random_state", "A number that fixes the random choices so the same split comes out every time."),
        ("Feature", "One input number the model sees, e.g. the TF-IDF weight of “said”, or the word count."),
        ("Vocabulary", "The set of distinct words TF-IDF found in the training data; one feature per word."),
        ("Token / tokenisation", "A unit of text (word or punctuation mark) / splitting text into those units."),
        ("Coefficient / weight", "The number logistic regression multiplies a feature by. Positive pushes towards fake, negative towards real."),
        ("Regularisation", "A penalty on large weights so the model does not memorise the training data."),
        ("Standardisation", "Rescaling a numeric feature to mean 0 and SD 1 so features with big values don’t dominate."),
        ("Feature importance", "In a random forest, how much each feature helped the trees separate the classes, summing to 1."),
        ("Confusion matrix", "2 × 2 table of actual vs. predicted class. See 4.5."),
        ("Accuracy / precision / recall", "Share of all predictions that are right / of articles called fake, the share really fake / of fake articles, the share caught. See 4.5."),
        ("Generalisation", "Doing well on data unlike the training data."),
        ("Pipeline (scikit-learn)", "A chain of steps (e.g. TF-IDF then classifier) that is fitted and applied as one object, so the steps can’t be applied in the wrong order."),
        ("Fit / predict", "Learn from data / apply what was learned to new data."),
        ("Clone", "A fresh, untrained copy of a model with the same settings."),
        ("Cache", "A saved result so slow work (spaCy, VADER) is done once."),
        ("Hash / checksum", "A short fingerprint computed from data; identical data gives an identical fingerprint."),
        ("Process / thread / parallel", "Independent running program / a lighter worker inside one program / doing several things at the same time on different CPU cores."),
        ("DataFrame / Series", "pandas' table / single column."),
    ]
    add('<h2 id="s3">3. Glossary: abbreviations and terms</h2>'
        + '<h3>3.1 Abbreviations</h3>'
        + table(["Short form", "In full", "What it means here"], [(a, b, c) for a, b, c in abbrev], "gl")
        + '<h3>3.2 Part-of-speech tags (spaCy, Universal Dependencies tag set)</h3>'
        + md("E2b, E3c and E5c keep only the tags marked “kept”. Everything else is thrown away before the model sees the text.")
        + table(["Tag", "In full", "Examples", "Function-word probe"], pos_tags, "gl")
        + '<h3>3.3 Named-entity types (spaCy), used in E2e</h3>'
        + table(["Label", "Meaning"], ents, "gl")
        + '<h3>3.4 Terms</h3>'
        + table(["Term", "Meaning"], terms, "gl")
        + '<h3>3.5 Abbreviations in the references</h3>'
        + table(["Short form", "In full", "Where it appears"], venues, "gl"))

    # ---------------- 4 core ideas
    add('<h2 id="s4">4. Core ideas you need before reading the code</h2>' + md(r"""
### 4.1 TF-IDF: turning text into numbers

A classifier only understands numbers. `TfidfVectorizer` first learns a **vocabulary** from the
training articles (every distinct word; with default settings, words of two or more letters,
lowercased). Each article then becomes one long row of numbers, one per vocabulary word, almost all
zero.

- **TF (term frequency):** how many times the word occurs in this article.
- **IDF (inverse document frequency):** scikit-learn uses `ln((1 + n) / (1 + df)) + 1`, where `n`
  is the number of training articles and `df` the number containing the word. A word in every
  article ("the") gets the minimum weight; a rare word gets a high one.
- The value for a word is TF × IDF, and each article's row is then scaled to length 1, so a long
  article does not get bigger numbers just for being long.

Two choices matter for this project. We use **single words** (no word pairs), and we **do not remove
stop words** like "the", "on", "said". Many tutorials remove them; we keep them because the style
signal lives exactly there.
""") + "<h3>4.2 Logistic regression (the detector)</h3>" + md(r"""
Logistic regression gives every feature a **weight** (coefficient). For an article it computes
`score = bias + Σ weight × feature value` and turns the score into a probability with the logistic
(sigmoid) function `1 / (1 + e^(−score))`. Probability above 0.5 → predicted fake.

Training chooses the weights that make the training labels most probable, with a penalty on large
weights (L2 regularisation, scikit-learn's default strength `C = 1`) so it doesn't memorise.

**Why we chose it:**

- **It is readable.** Each word has exactly one weight. A large positive weight means "this word
  pushes towards fake"; large negative means "towards real". That is how we found "reuters",
  "said", "via" and "featured" (report Fig. 3). A neural network would not show this so directly.
- **It is the standard baseline** for TF-IDF text classification and the kind of model behind
  the published 98–99% ISOT results.
- **If a simple linear model already gets 98%, the task is suspiciously easy.** That is the point
  we are making.
""") + "<h3>4.3 Random forest (for the numeric probes)</h3>" + md(r"""
E2c, E2d, E2e and E5d give the model a small table of numbers (8 to 18 columns), not text. For
those we use a **random forest**: 100 decision trees (scikit-learn's default), each trained on a
random resample of the training data and considering a random subset of features at each split;
the trees vote.

Why not logistic regression here? With so few features, the useful rules are likely to be
**thresholds and combinations** ("more than two question marks *and* short words"), which trees
capture and a single weighted sum does not. The forest also reports **feature importances**: how
much each feature helped, summing to 1.
""") + "<h3>4.4 Linear SVM (the classifier check)</h3>" + md(r"""
A linear Support Vector Machine also draws a straight boundary, but chooses the one with the widest
gap (margin) between the classes. We rerun four conditions with it to answer "is this just because
you used logistic regression?". It scores slightly *higher* every time.
""") + "<h3>4.5 Metrics, using the E1 confusion matrix</h3>" + md(r"""
Fake is the **positive** class (label 1), real is 0. The E1 test set has 7,729 articles:
""") + table(["", "Predicted real", "Predicted fake"], [
        ["**Actually real** (4,238)", f"{tn:,}  (TN: correct)", f"{fp:,}  (FP: real wrongly called fake)"],
        ["**Actually fake** (3,491)", f"{fn:,}  (FN: fake missed)", f"{tp:,}  (TP: correct)"],
    ], "cm") + md(fr"""
- **Accuracy** = correct / all = ({tn:,} + {tp:,}) / 7,729 = **{E1['accuracy']:.1%}**.
- **Precision** (fake) = TP / (TP + FP) = {tp:,} / {tp + fp:,} = {E1['precision']:.1%}: when it says fake, how often it's right.
- **Recall** (fake) = TP / (TP + FN) = {tp:,} / {tp + fn:,} = {E1['recall']:.1%}: of the fake articles, how many it catches.
- **F1** = 2 × P × R / (P + R) = **{E1['f1']:.3f}**: one number balancing the two.
- **Chance (majority baseline)** = share of the biggest class in the test set = 4,238 / 7,729 =
  **{E1['majority_baseline']:.1%}**. A model that always says "real" gets this. We **measure** it
  because it is not 50%: after cleaning, ISOT is 54.8% real, the E5 subset is 60.9% fake, LIAR is
  55.8% "real". "Far above chance" is the evidence of leakage, so chance must be right.
""") + "<h3>4.6 Train/test split, stratification, seeds and repeats</h3>" + md(r"""
- **80/20 split:** 80% of articles train the model, the other 20% are only used to measure it. A
  model is never scored on articles it trained on. 20% of 38,644 is 7,729 test articles, which is
  enough that one percentage point is about 77 articles.
- **Stratified:** both parts keep the real/fake ratio of the whole data (54.8 / 45.2). Without it a
  random split could put proportionally more fake articles in the test set by chance, shifting
  both accuracy and chance for reasons unrelated to the model.
- **Fixed seed (`random_state = 42`):** the same articles land in the test set every run, on every
  computer, **in every experiment**. So when E1 scores 98.4% and E3b 97.3%, the difference comes from
  the input, not from a luckier split. (42 is just a convention; any fixed number works.)
- **Five repeats (seeds 42–46):** each experiment is also run on four further random splits. The
  report gives mean ± SD. SDs are 0.1–0.5 points, so differences of several points between conditions
  are real, not split luck. Seed 42's run supplies the headline numbers, confusion matrices and
  coefficients.
""") + "<h3>4.7 Why a pipeline prevents leakage</h3>" + md(r"""
TF-IDF *learns* things (the vocabulary, the IDF weights). If it learned them from all the data
before splitting, information about the test articles would leak into training. A scikit-learn
`Pipeline` fits TF-IDF and the classifier **on the training part only**, then merely *applies*
them to the test part. The same goes for `StandardScaler` on numeric features.
"""))

    # ---------------- 5 architecture
    add('<h2 id="s5">5. How the files fit together</h2>'
        + f'<img class="fig" src="{(ROOT / "report" / "architecture.png").as_uri()}">'
        + md(r"""
Data flows left to right: ISOT is cleaned; each experiment turns the cleaned articles into a
restricted **view** (functions in `transforms.py`); every view goes through the same
`run_experiment()` function (in `common.py`), which splits, trains, scores and writes a JSON file;
`07_figures.py` reads only those JSON files. LIAR and McIntire are used only as test sets (plus
McIntire's own in-domain control).
""") + table(["File", "Role", "Run as"], [
            ["`run.bat`", "Windows shortcut: runs `run_all.py` with the project's Python", "`.\\run`"],
            ["`run_all.py`", "Runs steps 0–7, steps 1–6 three at a time", "(called by run.bat)"],
            ["`scripts/common.py`", "Paths, constants, `load_isot()`, `run_experiment()`, printing and coefficient saving", "imported, never run"],
            ["`scripts/transforms.py`", "Every restricted view: first sentence, function words, metadata, stripping, entities, sentiment, caching", "imported, never run"],
            ["`scripts/00_get_data.py`", "Downloads LIAR/McIntire if missing, checks all data files' SHA-256", "step 0"],
            ["`scripts/01_baseline.py`", "E1", "step 1"],
            ["`scripts/02_partial_input.py`", "E2a, E2b, E2c, body-only", "step 2"],
            ["`scripts/03_stripped.py`", "E3, E3b", "step 3"],
            ["`scripts/04_cross_corpus.py`", "E4 (LIAR), E4b (McIntire)", "step 4"],
            ["`scripts/05_more_probes.py`", "E2d, E2e, E3c, SVM check", "step 5"],
            ["`scripts/06_confounds.py`", "E5a–E5d (topic-matched)", "step 6"],
            ["`scripts/07_figures.py`", "Seven figures + `results/results_table.md`", "step 7"],
            ["`data/`", "True.csv, Fake.csv, liar/, mcintire/, cache/ (saved spaCy and VADER output)", ""],
            ["`results/`", "One JSON per experiment, `*_tokens.json` coefficient lists, results table, `before_quote_fix/`", ""],
            ["`report/`", "The Word report and the scripts that build it and this guide (not part of the method, not covered line by line)", ""],
        ]))

    # ---------------- 6 worked example
    add('<h2 id="s6">6. Worked example: one real and one fake article through every view</h2>' + md(r"""
These are real rows of the cleaned dataset, put through the actual functions from
`transforms.py` when this PDF was built (long texts are cut with "…"). Use them when explaining
what each experiment "sees". Notice in the fake article: "tonight s", "Sanders  42.4" (apostrophes
lost in scraping), the "Featured image via … Getty Images" credit, "via Raw Story", and the
exclamation marks. Notice in the real article: the dateline "WASHINGTON (Reuters) -", the day of the
week, the curly quotes “ ”, and attribution ("called himself", "speaking on").

The "(IMAGE/VIDEO)" in the fake title survives stripping: the media-tag rule matches "(Video)" or
"[Image]" but not combined tags. Likewise, in the real article the "leading sentence" rule stops at
the first full stop, which is the one in "U.S.", so "S. Congress, …" remains. The rules are
hand-written and not perfect (they are applied identically to both classes), which the report
states as a limitation; E3c and E5c show the result does not depend on them, because function words
carry the signal anyway.
""") + worked_example())

    # ---------------- 7 walkthrough
    add('<h2 id="s7">7. Line-by-line walkthrough</h2>' + md(r"""
Each block shows the code with its real line numbers, then what it does and why. Read
`common.py` and `transforms.py` first: the experiment scripts are short because they call these.
"""))

    # 7.1 run
    add('<h3 id="w-run">7.1 run.bat and run_all.py — the one command</h3>' + md(r"""
**Purpose:** let anyone reproduce everything with one command (`.\run`), in about five minutes.
""") + walk("run.bat", [
        (1, 2, r"""
`@echo off` stops Windows printing each command before running it. Line 2 runs the project's own
Python (the one inside `.venv`, with the exact library versions from `requirements.txt`) on
`run_all.py`. `%~dp0` means "the folder this .bat file is in", so the command works from any folder.
`%*` passes on whatever was typed after `run`: `run 3 7` becomes `run_all.py 3 7`.
"""),
    ]) + walk("run_all.py", [
        (1, 11, r"""
The **docstring** (text in triple quotes at the top of a file or function) documents usage. It
also records a design decision: steps 1–6 only run in parallel once the caches exist (explained at
lines 33–35).
"""),
        (13, 18, r"""
Imports. `os` gives access to environment variables; `subprocess` starts another program (each
step runs as its own Python process); `sys` reads the command-line arguments and exits with an
error; `time` measures durations; `ThreadPoolExecutor` and `as_completed` run several steps at once
and collect them as they finish; `Path` handles file paths on any operating system.
"""),
        (20, 32, r"""
`Path(__file__).resolve().parent` is the folder containing this file, so all paths are relative to
the project wherever it is copied. `STEPS` maps each step number to its script.
"""),
        (33, 35, r"""
- `INDEPENDENT`: steps 1–6 never read each other's output, so they can run at the same time. They
  are listed **longest first** so the slow steps start immediately and the total time is shortest.
- `CACHES`: the four saved spaCy/VADER results. If two steps both found a cache missing at the same
  time, both would spend ~25 minutes building it and could overwrite each other's file. So parallel
  mode is only used once all four exist.
- `PARALLEL_STEPS = 3`: each experiment already fits its 5 splits in parallel, so 3 steps × 5 fits =
  15 workers, which suits a 16-core laptop.
"""),
        (37, 39, r"""
Copies the current environment variables and adds `PYTHONUTF8=1`. On Windows, Python otherwise
prints with code page 1252, which cannot show characters such as curly quotes or "→" that appear in
token lists, and the step would crash.
"""),
        (42, 51, r"""
`run_step` runs one script. It starts a timer, builds the command `[python, script path]`
(`sys.executable` is the Python running this file, i.e. the venv's), and runs it. With no log file
the output goes to the screen; otherwise standard output and errors both go into the log file. It
returns the step, the seconds taken and the **return code**: 0 means success, anything else failure.
"""),
        (54, 60, r"""
Runs steps one after another, printing a header for each. If a step fails, `sys.exit` stops the
whole pipeline with a message, because later steps (especially figures) would otherwise silently use
missing or old results.
"""),
        (63, 79, r"""
Runs steps three at a time. `pool.submit` starts each step on one of 3 worker threads; `as_completed`
hands back each step as it finishes, so its time can be printed straight away. Failures are
collected and reported at the end. **Threads are enough here** because each thread only waits for a
separate Python process; the real work happens in those processes, on their own CPU cores.
"""),
        (82, 86, r"""
`sys.argv[1:]` is the list of words typed after the script name (`run 3 7` → `["3", "7"]`). Unknown
step numbers are rejected with a helpful message.
"""),
        (88, 100, r"""
The plan. If steps were named, run exactly those, in that order. Otherwise: step 0 (check data);
then steps 1–6, in parallel if all caches exist, else one at a time (the first ever run, which builds
the caches); then step 7 last, because figures need every result.
"""),
        (102, 106, "Prints how long each step took and the total."),
        (109, 110, r"""
`if __name__ == "__main__":` is true only when the file is run directly, not when it is imported by
another file. Every script ends this way.
"""),
    ]))

    # 7.2 common
    add('<h3 id="w-common">7.2 scripts/common.py — the shared experiment harness</h3>' + md(r"""
**Purpose:** one place that loads and cleans ISOT, and one function, `run_experiment()`, that every
experiment calls. This is the most important file to understand. Because every condition goes
through the same function, with the same split and the same classifier, **the only thing that
differs between experiments is the input**. That is what makes the comparisons fair.
""") + walk("scripts/common.py", [
        (1, 1, "Module docstring."),
        (3, 15, r"""
Imports:

- `json` writes the results files; `Path` builds file paths.
- `numpy` (as `np`) for arrays and maths; `pandas` (as `pd`) for tables.
- `Parallel, delayed` from **joblib** run the five splits at once on separate CPU cores.
- `clone` makes a fresh, untrained copy of a model.
- `TfidfVectorizer` turns text into TF-IDF numbers; `LogisticRegression` is the classifier.
- `accuracy_score`, `confusion_matrix`, `precision_recall_fscore_support` compute the metrics.
- `train_test_split` makes the 80/20 split; `Pipeline` chains steps; `StandardScaler` rescales numbers.
"""),
        (17, 19, r"""
Project paths. `__file__` is this file; `.parent.parent` goes up from `scripts/` to the project folder.
"""),
        (21, 24, r"""
Constants used everywhere, so they cannot differ between experiments:

- `RANDOM_STATE = 42`: the seed that fixes the split (section 4.6).
- `TEST_SIZE = 0.2`: 20% test, 80% train. 80/20 is the conventional choice; with 38,644 articles,
  7,729 test articles make each percentage point about 77 articles, so estimates are stable.
- `N_SPLITS = 5`: number of random splits per experiment (seeds 42–46).
- `REAL, FAKE = 0, 1`: fake is class 1, the "positive" class, so precision, recall and F1 describe
  how well **fake** articles are detected.
"""),
        (27, 37, r"""
`load_isot()`'s docstring states the two cleaning rules and why. Every experiment loads data through
this function, so the row order is identical everywhere; together with the fixed seed, every
experiment gets the **same test articles**.
"""),
        (38, 41, r"""
Reads both CSV files (21,417 real and 23,481 fake rows) and adds a `label` column: 0 for every row
of True.csv, 1 for every row of Fake.csv. The label comes only from which file the row is in. That is
the root of the problem: the label is really "which source", and the model can learn exactly that.
"""),
        (42, 46, r"""
- Line 42: stack the two tables, real rows first. `ignore_index=True` renumbers rows 0, 1, 2 …
- Line 43: `fillna("")` replaces missing titles or bodies (NaN) with empty text so string operations
  don't fail.
- Line 44: **drop articles with an empty body** (631 rows). 630 of them are fake, so keeping them
  would hand the model a free rule, "empty = fake": a leak we would have created ourselves.
- Line 45: **drop duplicate bodies**, keeping the first copy (5,623 rows, almost all fake). If the
  same article sat in both train and test, the model would be "tested" on something it had
  memorised, inflating accuracy.
- Line 46: renumber the rows 0 … 38,643. Result: **38,644 articles, 21,191 real and 17,453 fake**.
"""),
        (49, 58, r"""
`_fit_on_split` (the leading underscore marks a helper meant for use only inside this file) does one
train/test run:

- `train_test_split(..., test_size=TEST_SIZE, stratify=labels, random_state=seed)` returns training
  features, test features, training labels and test labels. `stratify=labels` keeps the real/fake
  ratio identical in both parts (section 4.6).
- `clone(pipeline).fit(X_train, y_train)` trains a **fresh copy**, so the five runs cannot affect
  each other. Fitting the pipeline means: learn the TF-IDF vocabulary from the training text only,
  transform it, then train the classifier.
- It returns the trained copy, the training-set size, the true test labels and the predicted labels.
"""),
        (61, 74, r"""
The signature and docstring of `run_experiment`. Parameters:

- `features`: either **text** (one string per article) or a **numeric table** (one row per article,
  one column per measurement).
- `labels`: 0/1 per article. `name`: used for the results file name, e.g. `e1_baseline`.
- `model`: the classifier; logistic regression if none is given (the SVM and random forest runs pass
  their own).
- `tfidf_kwargs`: extra settings for TF-IDF (used by the function-word probes, see transforms.py
  line 23).
- `test_features` / `test_labels`: for cross-corpus tests (E4, E4b). If given, there is no split: the
  model trains on all of `features` and is tested on this other dataset.
"""),
        (75, 76, r"""
- `np.asarray` turns the labels into a NumPy array, whatever form they arrived in.
- `is_matrix`: a numeric table has 2 dimensions (rows × columns), a list of strings has 1.
  `getattr(features, "ndim", 1)` reads the number of dimensions, and gives 1 for a plain Python list,
  which has no `ndim` attribute. So the function decides by itself whether it was given text or numbers.
"""),
        (78, 82, r"""
- Line 78: use the given model, or else `LogisticRegression(max_iter=1000)`. `max_iter` is the
  number of steps the training algorithm may take; the default 100 can stop before training
  finishes on tens of thousands of features (and print a warning). 1000 gives it room.
- Line 80, numbers: `StandardScaler` (mean 0, SD 1 per column, so `char_count` in the thousands
  doesn't swamp `digit_ratio` around 0.01), then the classifier.
- Line 82, text: `TfidfVectorizer` then the classifier. `**(tfidf_kwargs or {})` passes any extra
  TF-IDF settings, or none.
- Both are **Pipelines**, so TF-IDF and scaling are fitted on the training part only (section 4.7).
"""),
        (84, 92, r"""
The normal case, no external test set:

- `seeds = range(42, 47)`: five seeds, 42 to 46.
- `Parallel(n_jobs=5)(delayed(_fit_on_split)(...) for seed in seeds)` runs `_fit_on_split` once per
  seed, all five at the same time on separate CPU cores. `delayed` packages each call so joblib can
  hand it to a worker. Results come back in seed order and are identical to running them one by one,
  just about five times faster.
- Line 92: the seed-42 run (`fits[0]`) supplies the headline numbers, the confusion matrix and the
  trained model whose coefficients we read. The other four only feed the mean ± SD.
"""),
        (93, 97, r"""
Cross-corpus case: the test set is a different dataset, fixed in advance, so there is nothing to
re-split. Train once on **all** of the training data and predict the other dataset. No SD is
reported for these rows ("n/a, fixed test set" in the table).
"""),
        (99, 101, r"""
Precision, recall and F1 for the fake class: `average="binary"` with `pos_label=FAKE` means "treat
fake as the positive class". `zero_division=0` returns 0 instead of a warning if a model never
predicts fake. The fourth returned value (support, i.e. counts) is not needed, hence `_`.
"""),
        (102, 115, r"""
The metrics saved for every experiment:

- `input`: whether it was text or a feature matrix; `model`: the classifier's class name.
- `n_train`, `n_test`: sizes. `int(...)` and `float(...)` convert NumPy numbers into plain Python
  numbers, which JSON can store.
- `majority_baseline`: `np.bincount(y_test)` counts how many test labels are 0 and how many are 1;
  the larger count divided by the total is the accuracy of always guessing that class = **chance**.
- `accuracy`, `precision`, `recall`, `f1`: as in section 4.5.
- `confusion_matrix`: rows are the true class [real, fake], columns the predicted class.
  `labels=[REAL, FAKE]` fixes that order. `.tolist()` makes it JSON-friendly.
"""),
        (117, 121, r"""
Only when there were five splits: the five accuracies, their mean and their standard deviation.
`ddof=1` gives the **sample** standard deviation (divide by n − 1), the correct one for a small sample.
"""),
        (123, 127, r"""
Writes `results/<name>.json` (creating `results/` if needed). Every number in the report and the
figures comes from these files. The function returns the metrics plus the trained pipeline; the
pipeline isn't saved to JSON (a model object isn't text), but the caller can read its coefficients
or feature importances.
"""),
        (130, 140, r"""
`print_metrics` prints a result readably on screen: sizes, chance, the four metrics to 4 decimals,
the five-split mean ± SD if present, and the confusion matrix. `f"{metric:<17}"` pads names to 17
characters so the numbers line up.
"""),
        (143, 148, r"""
`save_top_tokens`: the strongest words per class. Only works for linear models on text (logistic
regression), since only they have one weight per word.
"""),
        (149, 156, r"""
- `vocab`: the vocabulary TF-IDF learned, in column order; `vocab[i]` is the word for column `i`.
- `coefs`: the classifier's weights. `coef_` has one row for a two-class problem, hence `[0]`.
- `np.argsort(coefs)` gives the column numbers sorted from most negative to most positive weight.
- The last `k` (reversed, `order[::-1][:k]`) are the strongest **fake** words; the first `k` are the
  strongest **real** words.
"""),
        (157, 164, r"""
Prints the lists with the sign shown (`+8.3f`) and saves `results/<name>_tokens.json`, which
`07_figures.py` uses for the token chart (report Fig. 3).
"""),
    ]))

    # 7.3 transforms
    add('<h3 id="w-transforms">7.3 scripts/transforms.py — the restricted views of an article</h3>' + md(r"""
**Purpose:** every function here takes articles and returns only what one condition is allowed to
see. Keeping them in one file means the same definition is used everywhere (e.g. "fully stripped"
means the same in E3b, E4b, E5 and the SVM check). The slow ones save their output to `data/cache/`.
""") + walk("scripts/transforms.py", [
        (1, 6, "Module docstring: what the file is for and how caching works."),
        (8, 14, r"""
`hashlib` computes fingerprints (for cache keys); `json` reads and writes caches; `re` is Python's
regular-expression module (pattern matching on text); `pandas` builds feature tables; `DATA_DIR`
comes from `common.py`.
"""),
        (16, 18, r"""
- `CACHE_DIR` = `data/cache/`.
- `SPACY_PROCESSES = 4`: spaCy tags texts using 4 processes at once. Tested: more than 4 was not
  faster on this machine.
- `FUNCTION_POS`: the part-of-speech tags we count as function words: determiners, pronouns,
  adpositions, auxiliaries, both kinds of conjunction, particles and punctuation (table in section 3.2).
  Everything else (nouns, verbs, adjectives, adverbs, names, numbers) is thrown away.
"""),
        (20, 23, r"""
TF-IDF's default tokeniser keeps only words of **two or more** letters or digits, so it would throw
away "a", ",", "!", "?", "-" and ":", which are exactly the tokens the function-word probes need. These
settings tell it to split on spaces instead (`tokenizer=str.split`, `token_pattern=None`) and not to
lowercase (the text is lowercased already).
"""),
        (26, 44, r"""
The cache. `_cached(name, texts, compute)` returns `compute(texts)`, but saves it the first time:

- Line 31: the **key** is an MD5 fingerprint of all the input texts joined together (separated by
  the null character `\x00`, which never occurs in articles). Any change to any text changes the key.
- Lines 32–38: if a cache file exists and its key matches, load it (seconds instead of ~25 minutes).
  If the key differs, the data has changed, so the cache is **stale** and is rebuilt. A cache can
  therefore never silently feed results computed from different data.
- Lines 40–44: otherwise compute, then save `{"key": ..., "docs": ...}` as JSON.

MD5 is used as a fingerprint, not for security, so its known weaknesses don't matter here.
"""),
        (47, 55, r"""
`_spacy_pipe` runs spaCy over many texts:

- `import spacy` is inside the function so that cached runs never pay spaCy's loading time.
- `spacy.load("en_core_web_sm", disable=...)` loads the small English model with the parts we don't
  need switched off (faster).
- `nlp.pipe(texts, batch_size=50, n_process=4)` processes the texts in batches of 50 across 4
  processes. Progress is printed every 2,000 documents.
- `yield` makes this a **generator**: it hands back one processed document at a time instead of
  holding all 38,644 in memory.
"""),
        (58, 59, r"""
For one spaCy document: keep each token whose POS tag is in `FUNCTION_POS`, lowercased
(`t.lower_`), joined by spaces. E.g. "The minister said on Sunday that he would resign." →
"the on that he would ."
"""),
        (62, 66, r"""
**E2a.** `re.split(r"[.\n]", text, maxsplit=1)[0]` splits the text at the first full stop or line
break and keeps the part before it. For Reuters articles this is the dateline plus the opening of the
first sentence (section 6). It is deliberately simple; "U.S." would cut early, which doesn't matter for
a probe.
"""),
        (69, 76, r"""
**E2b.** Runs spaCy with the parser, entity recogniser and lemmatiser disabled (only the POS tagger
is needed), converts every article to its function-word string and caches the result as
`function_words`.
"""),
        (79, 98, r"""
**E2c.** Eight surface statistics per article, no words:

- `char_count`, `word_count` (`t.split()` splits on whitespace).
- `sentence_count`: number of runs of `.`, `!` or `?` (`[.!?]+` counts "?!" as one).
- `exclamation_marks`, `question_marks`.
- `all_caps_word_ratio`: share of words written entirely in capitals with more than one letter
  ("BREAKING", "HILARIOUS"; "I" and "A" don't count).
- `avg_word_length`, `digit_ratio` (share of characters that are digits).
- `max(..., 1)` prevents division by zero for an empty text. Returns a pandas DataFrame, which has 2
  dimensions, so `run_experiment` treats it as numbers (scaler + classifier).
"""),
        (101, 107, r"""
Patterns for **E3**, compiled once with `re.compile` for speed:

- `DATELINE` = `^[^\n]*?\(Reuters\)\s*-\s*` piece by piece: `^` the start of the text; `[^\n]*?` any
  characters except a line break, as few as possible; `\(Reuters\)` the literal "(Reuters)" (brackets
  escaped with `\`); `\s*-\s*` a dash with optional spaces around it. Catches "WASHINGTON (Reuters) - ",
  "WASHINGTON/BEIJING (Reuters) - " and "SAN JUAN, Puerto Rico (Reuters) - ".
- `LEADING_SENTENCE` = `^[^.\n]*[.\n]\s*`: from the start up to and including the first full stop or
  line break, plus following spaces.
- `REUTERS`: the word "reuters" anywhere, in any capitalisation (`re.IGNORECASE`).
"""),
        (109, 114, r"""
Patterns for **E3b**, the fake sites' page furniture:

- `IMAGE_CREDIT`: optional "featured", one of image/photo/pic/video/screenshot/screen capture/audio/gif
  (optional plural `s?`), then via/credit/by/courtesy (`\b` = whole word), then the rest of the line
  (`[^\n]*`). Catches "Featured image via Justin Sullivan/Getty Images".
- `URL`: `http://` or `https://` or `www.` or `pic.twitter.com/` followed by non-space characters (`\S+`).
- `HANDLE`: `@` followed by word characters, e.g. "@realDonaldTrump".
- `MEDIA_TAG`: bracketed tags like "[Video]", "(Tweets)", "[Images]", or "watch:", "breaking:",
  "read more:", "just in:" (`|` means "or").
"""),
        (115, 120, r"""
`TYPOGRAPHY` is a translation table: each curly or straight apostrophe or quote mark → a space,
"…" → "...", en dash and em dash → "-".

**Why:** the fake articles were scraped in a way that lost these characters ("tonight s",
"couldn t"), while Reuters text kept them ("tonight's", curly quotes in 50.8% of real articles, 0% of
fake). A model can separate the classes just by spotting an apostrophe. Turning every one into a
space **in both classes** makes them look the same ("tonight s" in both).

**Honesty point (from the comment):** this rule was extended **once**, after the E5c coefficients
showed the straight-quote case. It **lowered** our own headline numbers (E5c from 98.0% to 90.3%,
E3c from 93.4% to 90.7%), and the before/after results are both kept (`results/before_quote_fix/`)
and reported.
"""),
        (123, 127, r"""
**E3** on a body: remove the dateline once at the start (`count=1`), then the leading sentence
(which in wire copy follows the dateline and is formulaic; E2a showed the opening line alone gives
99.1%), then every "reuters". Applied to **every** article, real and fake alike. These markers
belong to the Reuters pipeline, so E3 removes one class's markers (RQ2's "from Reuters articles"),
and E3b adds the other pipeline's.
"""),
        (130, 134, r"""
**E3b**: replace each furniture pattern with a **space** (not nothing, so the words on either side
don't stick together), then apply the typography table.
"""),
        (137, 139, r"""
E3 for a whole table: titles have no dateline or lead, so only "Reuters" is removed from them; bodies
get the full `strip_artifacts`. `.map(f)` applies `f` to every row.
"""),
        (142, 145, r"""
The strictest text view: E3 then E3b on titles and bodies, joined with a space. Used by E4b, E5 and
the SVM check.
"""),
        (148, 164, r"""
One spaCy pass on stripped text, with the entity recogniser **on**, gives two things per article:
its function-word string (for E3c and E5c) and a count of each entity type (for E2e). Doing both in
one pass saves a second ~25-minute run. `counts.get(label, 0) + 1` adds one to that type's count.
`cache_name` must differ per dataset (ISOT uses `stripped_profile`, McIntire `mcintire_profile`),
otherwise one dataset's cache would overwrite the other's.
"""),
        (167, 172, r"""
**E2e** features. A DataFrame is built from the per-article count dictionaries; types an article
doesn't mention become 0 (`fillna(0)`); columns are sorted so the order is always the same; each count
is divided by the article's word count and × 100, i.e. **per 100 words**, so a long article doesn't
score high just for being long. Only counts reach the model, never the names themselves.
"""),
        (175, 199, r"""
**E2d** features. NLTK's VADER scorer gives four numbers for a piece of text: `neg`, `neu`, `pos`
(shares of negative, neutral and positive wording, summing to 1) and `compound` (overall from −1,
very negative, to +1, very positive). Title and body are scored separately → 8 columns.

Line 196 joins each title and body with `\x01` (a control character that never occurs in text) so
the cache key covers both; line 188 splits them apart again. `nltk.download(..., quiet=True)` fetches
VADER's word list the first time only.
"""),
    ]))

    # 7.4 00
    add('<h3 id="w-00">7.4 scripts/00_get_data.py — fetch and verify data (step 0)</h3>' + md(r"""
**Purpose:** make sure a reproducer has **exactly** the data the results came from.
""") + walk("scripts/00_get_data.py", [
        (1, 7, "Docstring: LIAR and McIntire download automatically; ISOT needs a Kaggle login, so it can't."),
        (9, 15, r"""
`hashlib` for SHA-256; `io` to treat downloaded bytes as a file; `sys` to exit with an error;
`urllib.request` to download; `zipfile` to open zip archives.
"""),
        (17, 17, "Where ISOT can be downloaded, printed if it is missing."),
        (19, 29, r"""
For each zip file URL, which files to take out of it and where to put them. Only the named files are
extracted, nothing else in the archive.
"""),
        (31, 39, r"""
The expected SHA-256 fingerprint of every data file. If even one byte differs (a re-uploaded dataset,
a converted line ending), the fingerprint is completely different. This actually happened once:
git's automatic line-ending conversion changed True.csv, the check caught it, and a
`.gitattributes` rule (`data/** -text`) now stores data files byte for byte.
"""),
        (42, 50, r"""
Downloads a zip (120-second timeout), keeps it in memory (`io.BytesIO`), creates the destination
folder if needed and writes only the named files.
"""),
        (53, 58, r"""
Computes a file's SHA-256 by reading it in 1 MB chunks (`1 << 20` = 2²⁰ = 1,048,576 bytes), so
large files never need to fit in memory. `iter(lambda: f.read(...), b"")` keeps reading until it gets
empty bytes (end of file).
"""),
        (61, 64, "Downloads a dataset only if any of its files is missing."),
        (66, 76, "Checks every file and prints ok, MISSING or DIFFERENT, counting problems."),
        (78, 83, r"""
Prints ISOT download instructions if needed. If anything is missing or different, `sys.exit` ends
with an error code, so `run_all.py` stops before any experiment runs on the wrong data.
"""),
        (86, 87, "Run `main()` when executed directly."),
    ]))

    # 7.5 01
    e1t = json.load(open(RESULTS / "e1_baseline_tokens.json", encoding="utf-8"))
    add('<h3 id="w-01">7.5 scripts/01_baseline.py — E1, the detector (step 1)</h3>' + md(r"""
**Purpose:** build the standard detector and reproduce the familiar ISOT accuracy. This is the
number the rest of the project interrogates.
""") + walk("scripts/01_baseline.py", [
        (1, 1, "Docstring."),
        (3, 3, "Imports the four helpers from common.py."),
        (6, 8, r"""
Loads the cleaned data and makes each article's text: title + a space + body (the space stops the
last word of the title from merging with the first word of the body).
"""),
        (10, 12, r"""
Runs the experiment (TF-IDF + logistic regression, 5 splits), prints the metrics and saves the 30
strongest words per class.
"""),
        (15, 16, "Entry point."),
    ]) + md(fr"""
**Result:** {pct('e1_baseline')} accuracy ({E1['accuracy_mean']:.1%} ± {E1['accuracy_sd']:.1%} over 5
splits), only {fp + fn} errors among 7,729 test articles ({fp} real called fake, {fn} fake missed).

**Strongest real words:** {", ".join(w for w, _ in e1t['real'][:12])}.
**Strongest fake words:** {", ".join(w for w, _ in e1t['fake'][:12])}.

**What to say:** the strongest clues are about **who published** the article, not whether it is
true: the agency name, the dateline city, the days of the week Reuters puts in every story, its
attribution verbs ("said", "told"); and on the fake side, image-credit lines ("featured image via"),
"video", "read" (from "READ MORE:") and an opinionated voice ("this", "just", "us"). Report Fig. 3 shows
these with the source markers in orange.
"""))

    # 7.6 02
    add('<h3 id="w-02">7.6 scripts/02_partial_input.py — E2a, E2b, E2c (step 2)</h3>' + md(r"""
**Purpose:** the partial-input probes. Each model is denied the article's real content. If one still
scores far above chance, the dataset leaks the label through what it *was* given.
""") + walk("scripts/02_partial_input.py", [
        (1, 7, "Docstring listing the conditions."),
        (9, 12, "Imports the random forest, the helpers and the views from transforms.py."),
        (15, 18, r"""
Loads data; `full` is title + body as a plain Python list (spaCy and the cache work on lists).
"""),
        (20, 23, fr"""
**E2a, first sentence only.** `df["text"].map(first_sentence)` keeps only the body up to the first
full stop. 15 strongest words per class are saved.

**Result: {pct('e2a_first_sentence')}**, *higher* than the full article. The real side's top words are
the dateline: reuters, washington, said, fla, calif, wednesday, london. The opening line is almost a
pure source label; the rest of the article only dilutes it.
"""),
        (25, 29, fr"""
**E2b, function words only.** Every article becomes its function-word string, e.g. "the of a and to ,
the -". No nouns, verbs, names or numbers survive. `WHITESPACE_TFIDF` keeps one-character tokens.

**Result: {pct('e2b_function_words')}.** The headline finding. Top fake tokens: ":", "via", "?", "!",
"this", "like", "that", "you", "why". Top real tokens: "...", "on", "-", "'s" and curly quote
characters. The two classes are told apart by punctuation habits and grammatical voice.
"""),
        (31, 40, fr"""
**E2c, eight numbers only**, with a random forest (`random_state` fixed so the forest is identical
each run; `n_jobs=-1` = use all cores).

Line 36 matters: `run_experiment` trains a **clone**, not the `forest` object itself, so the
importances must be read from the returned pipeline's `clf` step. Line 37 pairs each column name with
its importance and sorts from largest (`-p[1]` sorts descending).

**Result: {pct('e2c_metadata')}** from eight numbers. Most important: question marks (0.187), average
word length (0.175), share of all-caps words (0.132), exclamation marks (0.120). Fake articles ask
more questions, shout more and use shorter words.
"""),
        (42, 44, f"""
Full body without the title, needed for the degradation chart (report Fig. 8): {pct('e2_body_only')}.
"""),
        (47, 48, "Entry point."),
    ]))

    # 7.7 03
    e3bt = json.load(open(RESULTS / "e3b_furniture_stripped_tokens.json", encoding="utf-8"))
    add('<h3 id="w-03">7.7 scripts/03_stripped.py — E3, E3b (step 3)</h3>' + md(r"""
**Purpose:** the obvious objection is "just delete the word Reuters". This tests it: remove every
identifiable source marker and retrain on the full remaining text.
""") + walk("scripts/03_stripped.py", [
        (1, 21, r"""
The docstring lists all eight removal rules (implemented in transforms.py lines 101–145). Rules 1–3
are E3 (the Reuters pipeline's markers), 4–8 are added in E3b (the fake sites' page furniture and
the typography). The last paragraph states what the comparison measures.
"""),
        (23, 24, "Imports."),
        (27, 29, "Loads data and applies E3 to titles and bodies."),
        (31, 34, fr"""
**E3: {pct('e3_stripped')}** (from 98.4%). Removing the dateline, the first sentence and every
"Reuters" costs under one point.
"""),
        (36, 40, fr"""
**E3b:** additionally strips the furniture from both titles and bodies. **{pct('e3b_furniture_stripped')}.**
Errors rise only from {fp + fn} to {sum(R('e3b_furniture_stripped')['confusion_matrix'][0][1:]) + R('e3b_furniture_stripped')['confusion_matrix'][1][0]}.

Strongest real words afterwards: {", ".join(w for w, _ in e3bt['real'][:10])}: wire-service
attribution. Strongest fake: {", ".join(w for w, _ in e3bt['fake'][:10])}: an opinionated blog voice.
"via" survives in prose such as "via Raw Story" (crediting other sites). **What to say:** the source
is not in a few removable words; it runs through the whole way the article is written.
"""),
        (43, 44, "Entry point."),
    ]))

    # 7.8 04
    add('<h3 id="w-04">7.8 scripts/04_cross_corpus.py — E4, E4b (step 4)</h3>' + md(r"""
**Purpose:** the decisive test of whether the detector learned "fake news" or "ISOT": train on ISOT,
test on datasets it has never seen, labelled independently.
""") + walk("scripts/04_cross_corpus.py", [
        (1, 19, r"""
Docstring with all eight runs. Why two external datasets: LIAR has **no article bodies** (only short
statements), so E4 can only compare headlines. McIntire has **full articles** whose real side comes
from many outlets, not Reuters, so E4b tests the full-text detector itself.
"""),
        (21, 26, r"""
`csv` is needed for `QUOTE_NONE` (below). The other imports are the usual helpers and views.
"""),
        (28, 33, r"""
LIAR's files have no header row; these 14 column names come from the LIAR paper (Wang, 2017). Only
`label` and `statement` are used.
"""),
        (34, 38, r"""
LIAR rates statements on six levels. We collapse them to two: true, mostly-true and half-true count
as **real**; barely-true, false and pants-on-fire ("pants on fire" = blatantly false) as **fake**.
Half-true is the judgement call, so line 77 reruns without it.
"""),
        (41, 49, r"""
Reads the three LIAR files (train, valid, test). We don't train on LIAR, so all 12,836 statements are
used as one test set. `quoting=csv.QUOTE_NONE` tells pandas that quote marks are ordinary characters:
LIAR statements contain unbalanced quotes that would otherwise make rows merge. Line 48 adds the
binary label.
"""),
        (52, 58, r"""
McIntire, cleaned exactly like ISOT (empty and duplicate bodies dropped): 6,335 → 6,059 articles
(2,989 real, 3,070 fake). Its text labels "REAL"/"FAKE" become 0/1.
"""),
        (61, 64, "Loads both datasets and prints LIAR's six-way label counts."),
        (66, 68, fr"""
**E4 control:** ISOT headlines only, normal split. **{pct('e4_isot_titles')}**. So headlines alone
are enough within ISOT; any drop on LIAR is due to changing dataset, not to headlines being too short.
"""),
        (70, 73, fr"""
**E4 transfer:** train on all ISOT headlines, test on all LIAR statements. **{pct('e4_liar_transfer')}**,
**below** chance ({R('e4_liar_transfer')['majority_baseline']:.1%}). It called 5,575 of the 7,167
"real" statements fake (78%). Explanation: it learned "not written like Reuters = fake", and
politicians' statements aren't written like Reuters.
"""),
        (75, 80, fr"""
**Sensitivity check:** without half-true: **{pct('e4_liar_no_halftrue')}** vs
{R('e4_liar_no_halftrue')['majority_baseline']:.1%} chance. Still at or below chance, so the result
doesn't depend on our label mapping.
"""),
        (82, 86, r"""
Loads McIntire and prepares the four text versions: full text (title + body) and fully stripped text
(E3 + E3b rules) for both datasets.
"""),
        (88, 97, r"""
The five E4b runs as a list of (name, training text, training labels, test text, test labels,
TF-IDF settings). `None` as test text means "split normally" (the control). The function-word run
reads them from the stripped-text spaCy cache for each dataset (`mcintire_profile` for McIntire).
"""),
        (98, 102, fr"""
Runs each. **Results:** McIntire in-domain control **{pct('e4b_mcintire_control')}** (the task is
learnable on McIntire itself); ISOT → McIntire full text **{pct('e4b_mcintire_full')}**, stripped
{pct('e4b_mcintire_stripped')}, function words {pct('e4b_mcintire_function_words')} (chance
{R('e4b_mcintire_full')['majority_baseline']:.1%}); reverse, McIntire → ISOT, {pct('e4b_reverse')}.
The ISOT detector calls 2,022 of McIntire's 2,989 real articles fake (68%).
"""),
        (105, 106, "Entry point."),
    ]))

    # 7.9 05
    add('<h3 id="w-05">7.9 scripts/05_more_probes.py — E2d, E2e, E3c, SVM check (step 5)</h3>' + md(r"""
**Purpose:** more probes, all on **fully stripped** text, so they cannot use any marker already found.
Anything they find is new. Plus the classifier check.
""") + walk("scripts/05_more_probes.py", [
        (1, 11, "Docstring."),
        (13, 19, "Imports, including `LinearSVC` for the SVM check."),
        (22, 30, r"""
A small helper so E2d and E2e don't repeat code: train a random forest on a numeric table, print the
metrics and the eight most important features (read from the fitted clone, as in step 2).
"""),
        (33, 38, r"""
Builds the fully stripped title and body (E3 then E3b) once, and the joined text as a list.
"""),
        (40, 41, fr"""
**E2d, sentiment only:** 8 VADER scores per article. **{pct('e2d_sentiment')}.** Most important:
title and body compound scores. Sentiment alone is a weaker but real signal: fake articles are more
emotional.
"""),
        (43, 43, "One spaCy pass (cached) gives function words and entity counts for every stripped article."),
        (45, 46, fr"""
**E2e, named entities only:** counts per 100 words of each entity type. **{pct('e2e_entities')}.**
Most important: GPE (places), DATE, NORP (groups). Wire stories are full of places and dates.
"""),
        (48, 52, fr"""
**E3c, function words of the stripped text.** No content words and none of the removed markers.
**{pct('e3c_stripped_function_words')}.** Top fake: "!", ":", "?", "like", "this", "that", "why",
"you" (exclamation, rhetorical questions, direct address). Top real: "on", "--", "had", "would",
"could", "whether", "amid" (reported, hedged speech).
"""),
        (54, 65, fr"""
**SVM check:** E1, E2a, E2b and E3b rerun with `LinearSVC` instead of logistic regression. Results:
E1 {pct('e1_svm')}, E2a {pct('e2a_svm')}, E2b {pct('e2b_svm')}, E3b {pct('e3b_svm')}: slightly
**higher** every time. A different (and slightly stronger) classifier exploits the shortcut more, not
less.
"""),
        (68, 69, "Entry point."),
    ]))

    # 7.10 06
    add('<h3 id="w-06">7.10 scripts/06_confounds.py — E5, topic-matched (step 6)</h3>' + md(r"""
**Purpose:** rule out topic. Real articles are 53% US politics, 47% world news; fake articles are
all US/political news. So "world news = real" could explain part of the results.
""") + walk("scripts/06_confounds.py", [
        (1, 15, r"""
Docstring. Note line 13: the `subject` column is used only to **choose rows**, never as model input
(it would be a leak itself, since the two classes use different subject names).
"""),
        (17, 20, "Imports."),
        (23, 26, "Loads data; builds the fully stripped text and its spaCy profile for all articles (from cache)."),
        (28, 32, fr"""
`keep` is True for every fake article and for real articles whose subject is `politicsNews`. All
world-news articles are removed. Result: **28,666 articles, 11,213 real, 17,453 fake.** Fake is now
the majority, so **chance rises to {R('e5c_topic_function_words')['majority_baseline']:.1%}**.
`.to_numpy()` turns it into a plain True/False array usable on both the table and the stripped texts.
"""),
        (34, 36, f"**E5a, full text: {pct('e5a_topic_full')}.** Topic matching changes almost nothing."),
        (38, 41, f"**E5b, fully stripped: {pct('e5b_topic_stripped')}.**"),
        (43, 48, fr"""
**E5c, stripped function words: {pct('e5c_topic_function_words')}** vs {R('e5c_topic_function_words')['majority_baseline']:.1%}
chance. The strictest test in the project: same topic, no markers, no content words, and still ~30
points above chance. `zip(profile, keep)` keeps the cached function-word strings of the selected rows.
(This is the result that went from 98.0% to 90.3% when the quote rule was extended.)
"""),
        (50, 53, f"**E5d, eight numbers from stripped text: {pct('e5d_topic_metadata')}.**"),
        (56, 57, "Entry point."),
    ]))

    # 7.11 07
    add('<h3 id="w-07">7.11 scripts/07_figures.py — figures and results table (step 7)</h3>' + md(r"""
**Purpose:** draw every chart and the results table from the saved JSON files. It **never retrains**
anything, so figures can be restyled in seconds without changing a single number.
""") + walk("scripts/07_figures.py", [
        (1, 11, "Docstring listing every output file."),
        (13, 20, r"""
`matplotlib.pyplot` draws charts; `LinearSegmentedColormap` makes the blue shading for the confusion
matrices; `PercentFormatter` shows axes as percentages.
"""),
        (22, 28, r"""
Output folder and colours: blue for the main data, orange to highlight (source markers, the SVM),
greys for text, grid lines and background. Two colours only, chosen to stay distinguishable for
colour-blind readers.
"""),
        (30, 36, r"""
`PROVENANCE`: words we label by hand as **publisher markers** (agency, dateline, timestamp, image
credit, URL fragments, media tags). The token chart (report Fig. 3) colours them orange. Deliberately strict: "said" is left
out even though it is a wire-style word, so we don't overstate.
"""),
        (38, 68, r"""
Every condition: (results file, label, what the model sees). `CONDITIONS` are drawn in the accuracy chart;
`TABLE_ONLY` appear only in the table, because they have a different chance level or test set and
would mislead on the same axis.
"""),
        (70, 84, r"""
Global chart style: font, colours, no top/right border lines, 200 dpi (dots per inch) so figures are
sharp in print, and `bbox: tight` to trim empty margins.
"""),
        (87, 97, r"""
`load` reads one results file (or returns `None` if that experiment hasn't been run, so the figure is
skipped instead of crashing). `title` puts a bold title and a grey subtitle above a chart.
"""),
        (100, 125, r"""
**`fig1_accuracy.png` (report Fig. 2), accuracy by condition.** Horizontal bars (`barh`), one per condition, with the
percentage written at the end of each bar and a dashed vertical line at chance. Lists are reversed
(`[::-1]`) so E1 appears at the top.
"""),
        (128, 150, r"""
**`fig2_leakage_tokens.png` (report Fig. 3), strongest E1 words.** Two panels (real, fake), 15 words each, bar length = size of the
weight. Words in `PROVENANCE` are orange, the rest grey, with a legend.
"""),
        (153, 181, r"""
**`fig3_confusion.png` (report Fig. 4), confusion matrices** for E1, E3 and E3b side by side, all on **one colour scale**
(`vmax` = largest cell) so the shading is comparable. Each cell shows the count and the row
percentage; text turns white on dark cells. The panel title gives accuracy and total errors.
"""),
        (184, 209, r"""
**`fig4_degradation.png` (report Fig. 8), degradation.** Accuracy as information is removed: full text → body only → function
words → eight numbers, with the chance line. The point: accuracy falls slowly and stays far above
chance.
"""),
        (212, 240, "**`fig5_topic_matched.png` (report Fig. 6), topic-matched check (E5a–E5d)** with this subset's own chance line (60.9%)."),
        (243, 274, r"""
**`fig6_svm_check.png` (report Fig. 7), classifier check.** A dot plot: blue = logistic regression, orange = SVM, joined by a
grey line, for the same four inputs. The axis doesn't start at zero, so dots are used instead of bars
(bars starting above zero would exaggerate differences).
"""),
        (277, 310, r"""
**`fig7_cross_corpus.png` (report Fig. 5), cross-corpus.** For each direction, a blue bar (tested on the same dataset) and an orange
bar (tested on the other dataset), with a dashed tick at the other dataset's chance.
"""),
        (313, 326, r"""
Writes `results/results_table.md` (the table in section 8): accuracy, mean ± SD (or "n/a" for
fixed external test sets), F1 and chance for every condition.
"""),
        (329, 350, r"""
`main` loads every results file, lists any missing, and draws each figure and the table.
"""),
        (353, 354, "Entry point."),
    ]))

    # ---------------- 8 results
    add('<h2 id="s8">8. Results: what every number means</h2>' + md(r"""
The full table, exactly as produced by step 7. "Accuracy" is the seed-42 split; "Mean ± SD" is over
five random splits; "Chance" is always guessing the larger class of that test set.
""") + table(["Condition", "What the model sees", "Accuracy", "Mean ± SD", "F1 (fake)", "Chance"],
             results_rows, "res") + md(r"""
**How to read it, group by group:**

- **E1 vs E2 (RQ1).** A model that sees only the first sentence (99.1%), only function words (96.8%)
  or only eight numbers (86.2%) does almost as well as, or better than, the full-text detector. Content
  is not what the detector uses.
- **E3, E3b, E3c (RQ2).** Removing every source marker from both classes costs about one point
  (98.4 → 97.3%). Even then, function words alone give 90.7%. The source is in the writing style.
- **E4, E4b (RQ3).** Within its own data the detector is excellent; on other data it is at or below
  chance on LIAR and 61.2% on McIntire, calling two-thirds of genuine articles fake. McIntire's own
  model gets 91.9% on McIntire, so the task there is learnable; the ISOT model just didn't learn it.
- **E5 (RQ4, topic).** On US politics only, stripped, function words: 90.3% vs 60.9% chance. Topic
  does not explain the signal.
- **SVM rows (RQ4, classifier).** A different classifier does slightly better on every condition.
- **F1** moves with accuracy everywhere except the cross-corpus rows, where it can stay moderate
  while accuracy is low, because the model predicts "fake" for most articles (high recall, poor
  precision).

**Limitations to state openly:** the probes were run in depth on ISOT only (LIAR and McIntire are
used as test sets); only classical models (no transformer such as BERT); the stripping rules are
hand-written and were extended once (disclosed, with before/after numbers).
""") + f'<img class="fig" src="{(ROOT / "figures" / "fig1_accuracy.png").as_uri()}">')

    # ---------------- 9 presenter
    add('<h2 id="s9">9. Presenter brief</h2>' + md(r"""
**What this section is.** A *presenter brief* is the short package for giving the talk: the story
in order, the numbers to memorise, what to say about each figure, and how to answer questions. You
present alone, so the talk and every question, including code questions, are yours.

### The story, in order (about 3 minutes)

Figure numbers are the report's.

1. **Hook.** "Fake news detectors on the ISOT benchmark report 98 to 99 percent. I built one and
   got 98.4. Then I tested whether that number means anything."
2. **The flaw.** "Every real article in ISOT comes from Reuters; every fake one from a set of flagged
   websites. So a model could be recognising the newsroom instead of the lie." Hospital analogy.
3. **The method.** "Partial-input baselines, from Gururangan et al. 2018: I trained models that are
   *not allowed* to see the content. If they still score high, the dataset is leaking the answer."
4. **Probes (Fig. 2).** "The first sentence alone: 99.1. Only words like 'the, of, a' and
   punctuation: 96.8. Eight numbers like word count and question marks: 86.2. Chance is 54.8."
5. **Why (Fig. 3).** "The strongest clues are 'Reuters', 'Washington', days of the week,
   'featured image via'. Publisher markers, not truth."
6. **Stripping (Fig. 4).** "I removed every marker from both classes. Still 97.3."
7. **Topic and classifier (Figs. 6, 7).** "Same topic only, everything stripped, function words
   only: 90.3 against 60.9 chance. And a different classifier, a linear SVM, does slightly better,
   not worse."
8. **Other datasets (Fig. 5).** "Trained on ISOT, tested elsewhere: 45.5 on LIAR,
   below chance; 61.2 on a dataset of real articles from other outlets, calling two-thirds of genuine
   news fake."
9. **Conclusion.** "The 98 percent measures the newsroom, not the truth. Fake news detectors should be
   tested across sources and alongside partial-input baselines, not on a single benchmark split."
""") + "<h3>Numbers to memorise</h3>" + table(["Number", "What it is"], [
            ["**98.4%**", "E1, my detector, full text"], ["**54.8%**", "chance on ISOT"],
            ["**99.1%**", "E2a, first sentence only"], ["**96.8%**", "E2b, function words only (the headline)"],
            ["**86.2%**", "E2c, eight numbers, no words"], ["**97.3%**", "E3b, every marker stripped from both classes"],
            ["**90.3% vs 60.9%**", "E5c, US politics only + stripped + function words, vs chance"],
            ["**45.5% vs 55.8%**", "E4, ISOT → LIAR, below chance"],
            ["**61.2% vs 50.7%**", "E4b, ISOT → McIntire full articles; 68% of real articles called fake"],
            ["**38,644**", "articles after cleaning (from 44,898; 631 empty, 5,623 duplicates removed)"],
        ]) + "<h3>Figure talking points (figure numbers as in the report)</h3>" + table(["Figure", "Say"], [
            ["1 Architecture", "Every condition goes through one function with the same split and classifier; only the input changes."],
            ["2 Accuracy by condition", "Every bar, even the ones with no content, is far right of the chance line."],
            ["3 Strongest tokens", "Orange bars are publisher markers. The detector's best clues are about who wrote it."],
            ["4 Confusion matrices", "Stripping markers barely changes the errors: 121 → 206 of 7,729."],
            ["5 Cross-corpus", "Blue = same dataset, orange = other dataset. The orange bars fall to chance."],
            ["6 Topic-matched", "Same topic, still far above its 60.9% chance."],
            ["7 SVM check", "Orange dots (SVM) are slightly right of blue: a better model exploits the shortcut more."],
            ["8 Degradation", "Remove more and more information; accuracy falls slowly and never near chance."],
        ]) + "<h3>Talk structure and transitions</h3>" + table(["Part", "Story points", "Time", "Move on with"], [
            ["Part 1: the claim and the flaw", "1–3: hook, flaw, method (Fig. 1)", "about 1 min",
             "\"So what happens when I take the content away?\""],
            ["Part 2: the evidence", "4–6: probes, tokens, stripping (Figs. 2–4, 8)", "about 1 min",
             "\"But maybe it's just topic, or just my classifier, or just this dataset.\""],
            ["Part 3: the checks and the verdict", "7–9: topic, classifier, other datasets, conclusion (Figs. 5–7)",
             "about 1 min", "\"Thank you, I'm happy to take questions.\""],
        ]) + md(r"""
The transition lines are signposts: each one names the objection the next part answers, which keeps
the examiner following the argument. If a question comes mid-talk, answer it briefly and return to
the next story point.

### Explaining the code in 60 seconds

Be able to say this, ideally with `common.py` open:

1. "`run.bat` runs `run_all.py`, which runs steps 0 to 7. Step 0 checks the data against
   checksums."
2. "`load_isot()` loads both CSVs, labels them 0 and 1 by file, and drops empty and duplicate
   articles: 38,644 left."
3. "Each experiment turns the articles into a restricted view, using a function in
   `transforms.py`: first sentence, function words, eight numbers, stripped text."
4. "Every view goes through one function, `run_experiment()`: the same stratified 80/20 split with
   seed 42, TF-IDF and logistic regression inside a pipeline, five repeated splits, metrics saved to
   JSON."
5. "`07_figures.py` only reads those JSON files to draw the charts. So the only thing that differs
   between experiments is the input."

### Code questions to answer without notes

- What `run_experiment` does, line by line (7.2, lines 75–127): split, fit, metrics, five splits,
  cross-corpus mode.
- Why `stratify=labels`, why seed 42, why five splits (4.6).
- Why the TF-IDF is inside a `Pipeline` (4.7: no leakage from the test set).
- The two cleaning rules in `load_isot` and why (7.2, lines 42–46).
- How function words are extracted, and why `WHITESPACE_TFIDF` is needed (7.3, lines 16–23, 58–76).
- What each stripping rule removes, including the typography rule and why it was extended once (7.3,
  lines 101–145).
- Why the random forest reads importances from `result["pipeline"]`, not from `forest` (7.6).
- How the cross-corpus runs differ: no split, train on all of ISOT (7.2, lines 93–97; 7.8).

### Preparation checklist

- Read sections 2–4, 7.2, 7.3, 8 and 10 at least twice.
- Rehearse the talk out loud at least twice, timed (about 3 minutes plus questions). Recording
  yourself once on your phone shows where you rush or hesitate.
- Self-quiz with section 10: read only the question, answer out loud, then check the answer.
- Open the code once and find `run_experiment`, `load_isot`, `TYPOGRAPHY` and `DATELINE` by line
  number.
- If there is a demo: run `.\run` once on the presenting laptop beforehand (about 5 minutes).

### Framing rules

It *is* a fake news detector: I built one, and it is the thing under test. Never
claim the project is the first to find problems with ISOT (Zhou et al. 2021 and Verma 2026 found
related problems); the contribution is the style-only probes, stripping both classes, the topic
control and two cross-corpus tests. State limitations without being asked.
"""))

    # ---------------- 10 Q&A
    qa = [
        ("What's your accuracy?", "My detector gets 98.4%, like published results. The project shows that number doesn't measure fake news detection: models that can't see the content score almost the same, and the detector fails on other datasets."),
        ("So is this a fake news detector or not?", "Yes: I built one (E1), and then tested it. The detector is the object under test. The finding is about what its accuracy means."),
        ("Isn't fake news detection a common, solved project?", "It looks solved because ISOT makes it look easy. I show why: the classes can be told apart by publisher style alone."),
        ("Hasn't someone already shown this?", "Partly. Zhou et al. (2021) showed fake news datasets leak source identity, and Verma (2026, a preprint) audited this same corpus by removing tags and metadata. My stripping and transfer results agree with theirs. What I add: style-only probes (function words: 96.8%), stripping both classes' markers, a topic-matched control and a full-article cross-corpus test."),
        ("What is a partial-input baseline?", "A model deliberately given only part of the input. If it still scores well, that part leaks the label. Gururangan et al. (2018) used it to expose artifacts in NLI data."),
        ("Why logistic regression and not BERT?", "Its weights are readable: one per word, so I can see exactly what it relies on (report Fig. 3). It's the standard TF-IDF baseline and matches published ISOT results. A stronger model would likely exploit the same shortcuts at least as well (the SVM already does) and would hide what it uses. Transformers are named as a limitation and as future work."),
        ("Why a random forest for E2c/E2d/E2e?", "Those inputs are a few numbers, where useful rules are thresholds and combinations; trees capture those. It also gives feature importances."),
        ("Why stratified splitting?", "It keeps the real/fake ratio identical in train and test, so accuracy and chance aren't shifted by a lucky split, and chance is the same across experiments."),
        ("Why 80/20 and seed 42?", "80/20 is conventional and leaves 7,729 test articles (≈77 per percentage point). The seed fixes the split so every experiment uses the same test articles and anyone gets identical numbers. Any fixed number works; 42 is convention."),
        ("How do you know results aren't a lucky split?", "Each experiment is repeated on 5 random splits; SDs are 0.1–0.5 points, much smaller than the differences I interpret."),
        ("Why is chance 54.8% and not 50%?", "After removing empty and duplicate articles (mostly fake), ISOT is 54.8% real. I measure chance on each test set rather than assume 50%."),
        ("Why remove duplicates and empty articles?", "Duplicates across train and test let the model be tested on articles it memorised. 630 of 631 empty bodies were fake, so 'empty = fake' would be a leak I would have created."),
        ("Why does the first sentence beat the full article?", "In Reuters copy the opening contains the dateline (city, '(Reuters)'). It's an almost pure source label; the rest of the article dilutes it."),
        ("Why did removing 'Reuters' barely change anything?", "The source isn't in one word; it's the whole register: wire reporting says 'said', 'told reporters', 'amid'; partisan blogs say 'this', 'just', 'you', '!' and '?'."),
        ("Isn't it just topic? Real has world news.", "Tested in E5: US politics only, all markers stripped, function words only: 90.3% vs 60.9% chance."),
        ("Is it because of your classifier?", "No. A linear SVM is slightly higher on every condition I reran."),
        ("Why is LIAR below chance?", "The model learned 'not written like Reuters = fake'. Politicians' statements aren't written like Reuters, so it calls 78% of the true ones fake."),
        ("LIAR is only short statements. Unfair?", "That's why there's an in-domain control (ISOT headlines: 94.6%) and a second, full-article test (McIntire: 61.2%, while a model trained on McIntire gets 91.9%)."),
        ("Why count half-true as real?", "It's a judgement call, so I also ran it without half-true: 51.1% vs 55.6% chance. Same conclusion."),
        ("Did you change anything after seeing results?", "Once, disclosed: E5c's coefficients showed straight apostrophes still separated the classes (a scraping artifact), so the typography rule was extended to all quote marks in both classes. It lowered my own numbers (E5c 98.0 → 90.3%). Both versions are kept and reported."),
        ("Why no stemming or lemmatisation?", "They merge word forms (said/says → say). The signal I study is in function words and punctuation, which stemming doesn't change, and the published ISOT baselines don't stem. I do use POS tagging, NER, sentiment, regex cleaning and TF-IDF."),
        ("Why not remove stop words?", "Stop words are function words: the style signal lives there. Removing them would hide the effect I am measuring."),
        ("Could TF-IDF leak test information?", "No. It sits inside a scikit-learn Pipeline, so its vocabulary and IDF weights are learned from the training split only."),
        ("What would fix the benchmark?", "Evaluate across sources (train on some publishers, test on others), report partial-input baselines next to the main result, and build datasets where real and fake come from the same kinds of sources, labelled per claim."),
        ("Can I reproduce it?", "Yes: one command, about 5 minutes, with checksum-verified data and fixed seeds; the README lists the exact numbers you should get."),
        ("What are the limitations?", "Probes in depth on ISOT only; classical models only; hand-written stripping rules (extended once, disclosed). The topic, classifier, label-mapping and full-article objections were tested, not just mentioned."),
    ]
    add('<h2 id="s10">10. Viva questions and answers</h2>'
        + "".join(f'<div class="qa"><div class="q">{html.escape(q)}</div>{md(a)}</div>' for q, a in qa))

    return "\n".join(f'<section>{s}</section>' for s in S)


CSS = r"""
@page { size: A4; margin: 18mm 17mm 18mm 17mm;
  @bottom-center { content: counter(page); font: 9pt 'Segoe UI', sans-serif; color: #777; } }
@page :first { @bottom-center { content: none; } }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'Segoe UI', 'Calibri', sans-serif; font-size: 10.3pt; line-height: 1.45; color: #1a1a1a; }
h1.title { font-size: 25pt; line-height: 1.15; margin: 0 0 14px; color: #0b0b0b; }
.cover { padding-top: 70mm; break-after: page; }
.kicker { text-transform: uppercase; letter-spacing: .08em; font-size: 9pt; color: #2a78d6; font-weight: 600; margin-bottom: 10px; }
.sub { font-size: 12pt; color: #444; max-width: 150mm; } .small { font-size: 9.5pt; color: #777; }
.toc { break-after: page; } .toc ol { line-height: 1.8; } .toc ol ol { line-height: 1.6; font-size: 9.6pt; }
.toc a { color: #1a1a1a; text-decoration: none; }
h2 { font-size: 16pt; color: #0b0b0b; border-bottom: 2px solid #2a78d6; padding-bottom: 3px; margin-top: 0; break-after: avoid; }
section { break-before: page; } section:first-child { break-before: auto; }
h3 { font-size: 12.3pt; color: #104281; margin: 18px 0 6px; break-after: avoid; }
p { margin: 5px 0 7px; } ul { margin: 4px 0 8px; padding-left: 20px; } li { margin: 2px 0; }
code { font-family: Consolas, 'Cascadia Mono', monospace; font-size: 9pt; background: #eef2f7; padding: 0 3px; border-radius: 3px; }
pre.code { font-family: Consolas, 'Cascadia Mono', monospace; font-size: 8.4pt; line-height: 1.38; background: #f6f7f9;
  border: 1px solid #dde1e6; border-left: 3px solid #2a78d6; border-radius: 4px; padding: 6px 8px; margin: 4px 0 6px;
  white-space: pre-wrap; word-break: break-word; }
pre.code .ln { display: inline-block; width: 30px; color: #9aa0a6; user-select: none; }
.chunk { margin: 10px 0 14px; } .chunk pre { break-inside: avoid; }
.where { font-size: 8pt; color: #6b7280; font-weight: 600; letter-spacing: .02em; break-after: avoid; }
.expl { padding-left: 4px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 9.2pt; }
th { background: #e6f0fb; text-align: left; padding: 4px 6px; border-bottom: 1px solid #b8cde6; }
td { padding: 4px 6px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
tr { break-inside: avoid; }
table.gl td:first-child { font-weight: 600; white-space: nowrap; }
table.res { font-size: 8.3pt; } table.res td:nth-child(n+3) { white-space: nowrap; }
table.cm { width: auto; } table.cm td, table.cm th { padding: 5px 12px; }
table.mini { width: auto; font-size: 8.6pt; margin: 2px 0; } table.mini td { padding: 1px 10px 1px 0; border: none; }
.ex { display: flex; gap: 10px; border-bottom: 1px solid #eceef1; padding: 5px 0; break-inside: avoid; }
.exl { flex: 0 0 38mm; font-size: 8.6pt; font-weight: 600; color: #104281; }
.ext { flex: 1; font-size: 9pt; } .mono { font-family: Consolas, monospace; font-size: 8.5pt; }
img.fig { width: 100%; margin: 10px 0; break-inside: avoid; }
.qa { margin: 0 0 9px; break-inside: avoid; } .q { font-weight: 700; color: #104281; margin-bottom: 1px; }
.qa p { margin: 0; }
"""


def main():
    body = build()
    check_coverage()
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Code Walkthrough and Viva Guide</title><style>{CSS}</style></head><body>{body}</body></html>"""
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "walkthrough.html"
        page.write_text(doc, encoding="utf-8")
        subprocess.run([str(EDGE), "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={OUT}", page.as_uri()], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
