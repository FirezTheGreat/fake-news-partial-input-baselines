# Project Context — WSMA Lab Project

> Working context file. Keep this in the project root so Claude Code can read it
> instead of being re-briefed every session.
>
> **Ownership:** Abhishek works on this project alone (a former teammate, Yuvika,
> is no longer part of it). He builds the code, writes the report, gives the whole
> talk and answers every question. Section 12 is the presenter brief; the full
> version is `report/Code_Walkthrough.pdf` (§9–10).

---

## 1. Title

**Partial-Input Baselines Reveal Construction Artifacts in Fake News Benchmarks**

## 2. Course requirements

Web and Social Media Analytics (WSMA) lab project:
- Must include lab-covered text processing (scraping, cleaning, tokenisation,
  stemming/lemmatisation, POS/NER, TF-IDF, sentiment)
  - *Covered:* cleaning (dedup, empty bodies), tokenisation, POS tagging (E2b),
    NER (E2e), VADER sentiment (E2d), TF-IDF, regex text processing (E3/E3b).
    Stemming/lemmatisation not used (it would not touch function words or
    punctuation, where the signal is).
- Must add prediction / ML beyond that
- Must be grounded in named research papers
- Teacher wants it research-paper shaped, not just an implementation

Evaluated on: presentation, dataset used, model/algorithm used, output.

Report format required: Abstract → Introduction → Literature Survey → Problem
Statement (research gap) → Proposed (system architecture, objectives) →
Methodology (no citations) → Results and Discussion (charts, no citations) →
Conclusion → Future Work → References.

---

## 3. The one-paragraph summary

Fake news classifiers report 99%+ accuracy on the standard benchmark dataset
(ISOT). We show that number is an illusion — not by building a better classifier,
but by building deliberately crippled ones. If a model that cannot see the
article's content still separates real from fake, the dataset is leaking the
answer, and every 99% ever published on it is measuring something other than
deception.

## 4. Why the benchmark is broken

ISOT's "real" articles were scraped from Reuters. Its "fake" articles were scraped
from partisan sites flagged as unreliable. The two classes come from two different
publishing pipelines with different house styles — datelines, agency attribution,
byline conventions, punctuation habits.

A classifier can separate them near-perfectly by learning *which newsroom wrote
this*, never touching the question of whether it's true. Gradient descent takes the
easy path: detecting the string "(Reuters)" is one token; detecting a lie requires
understanding claims and evidence.

Analogy for the presentation: train a model to detect cancer where all cancer
samples came from Hospital A and all healthy samples from Hospital B. It hits 99%.
Test it on Hospital C and it's at coin-flip. It learned the hospital, not the
disease.

## 5. Why this is research-worthy

This sits inside an established literature called **shortcut learning / dataset
artifacts**. The methodology exists and has been pointed at fake news before, so
**do not claim novelty of the idea** (checked 2026-10-13):
- **Zhou et al. (2021, EACL)** — peer-reviewed. Unreliable-news datasets let models
  memorise the site→label mapping; with source-disjoint splits accuracy drops >10%.
  Recommends simple-model probes when building datasets.
- **Verma (2026, arXiv preprint, not peer-reviewed)** — audits this same
  ISOT/Kaggle corpus: subject-field-only probe gets F1 = 1.000; removing the
  newswire tag, metadata and duplicates only moves F1 0.9935 → 0.9814; LIAR
  transfer does not beat the majority class.

**Our contribution is therefore an independent replication plus extension:**
our E3 and E4 agree with Verma. What we add: content-free *style* probes —
function words only (E2b), first sentence only (E2a), eight surface statistics
(E2c, no subject field) — E3b (stripping both sides' page furniture), and the
typography / empty-body artifacts (section 16). Say this framing out loud; an
examiner who finds Verma will ask.

Prior work:
- **Gururangan et al. (2018)** — NLI datasets are broken: a model given only the
  hypothesis, never shown the premise, still hit ~67% on SNLI. Source of the
  partial-input method.
- **Poliak et al. (2018)** — generalised across ten NLI datasets.
- **Niven & Kao (2019)** — BERT's argument-reasoning performance came largely from
  spurious unigrams.
- **McCoy et al. (2019)** — HANS; high accuracy masking syntactic heuristics.
- **Schuster et al. (2019)** — did this for fact verification: FEVER has claim-side
  cues, claim-only baselines stay competitive against evidence-aware models.
  **Closest analogue to this work.**
- **Geirhos et al. (2020)** — named and formalised shortcut learning.

Remedies in the literature (future work only, do not implement): counterfactually
augmented data (Kaushik et al., 2020), contrast sets (Gardner et al., 2020).

---

## 6. Data

**ISOT Fake News Dataset** — 44,898 articles.
- `True.csv` — 21,417 real articles, scraped from Reuters
- `Fake.csv` — 23,481 fake articles, from flagged unreliable sites
- Columns: title, text, subject, date
- Source: Kaggle, "Fake and Real News Dataset" by clmentbisaillon (free)

**LIAR** — 12,836 PolitiFact-checked short political statements, 6-way labels
(true → pants-on-fire), collapsed to binary for transfer testing. Free, from UCSB.
Ships as three TSVs (train/test/valid) with no headers — column names come from
the paper.

**Cleaning applied (in `load_isot()`, every experiment):** drop 631 empty bodies
(630 of them fake — an empty body is itself a label leak), then drop 5,623
duplicate bodies (keep first). Result: **38,644 articles — 21,191 real, 17,453
fake**; majority-class chance on the test split = 54.8%. All duplicates were
within one label; none crossed classes. LIAR files verified: 10,269 / 1,284 /
1,283 rows = 12,836, 14 columns, no header.

**McIntire "fake or real news"** (added 2026-10-13) — 6,335 full articles; real from mainstream
outlets (NYT, NPR …; "(Reuters)" in only 0.3%), fake from flagged sites. No body overlap with ISOT.
Download: github.com/joolsa/fake_real_news_dataset → `fake_or_real_news.csv.zip` (the Kaggle
competition link did not work). Extract the CSV to `data/mcintire/`. Cleaned like ISOT → 6,059
(2,989 real / 3,070 fake). Its giveaways run the *opposite* way to ISOT's (fake has more curly quotes).

**Known limitation to state openly:** LIAR has no article bodies, only short
statements, so E4 is a headline-level comparison. Some transfer failure may be
domain shift rather than artifact reliance.

---

## 7. The four experiments

### E1 — Baseline
TF-IDF + logistic regression on full text (title + body). Expect ~99%. This is the
number being attacked.

### E2 — Partial-input probes ← the core contribution
Three deliberately crippled models, each denied the information needed to do the
real task:

**E2a — First sentence only.** Split on the first `.` or newline, train on that
alone. Captures datelines and agency attribution.

**E2b — Function words only.** spaCy POS tag every document, keep only
`DET PRON ADP AUX CCONJ SCONJ PART PUNCT`, drop everything else. The result is
gibberish like "the of a and to , the —". Pure style, zero semantics. If this hits
80%+, it is the headline result of the paper.
*Performance note: spaCy over 44k docs is slow. Use
`nlp.pipe(batch_size=200, disable=["ner", "parser"])` and cache the output to disk
so re-runs are free.*

**E2c — Metadata only.** No text at all. Character count, word count, sentence
count, exclamation marks, question marks, ALL-CAPS word ratio, average word
length, digit ratio. Eight numbers per article into a random forest.

Any of these scoring well above chance (~50%) is the finding. A model with no
access to content cannot be detecting deception.

*As built:* E2b keeps spaCy's lowercased token text for those POS tags; TF-IDF
splits on whitespace so one-character tokens (`a`, `,`, `-`) survive. spaCy
runs once (~25 min, 4 processes) and caches to `data/cache/function_words.json`,
keyed by a hash of the input texts. E2c uses title + body and a random forest
(100 trees). A body-only run (`e2_body_only`, no title) feeds figure 4.

### E3 — Artifact removal
Regex out datelines, the string "Reuters" anywhere, and the leading sentence.
Retrain on full text. *As built:* the dateline regex is broader than
`^[A-Z ]+\(Reuters\) -` so it catches `WASHINGTON/BEIJING (Reuters) -`.
**E3b** (added) also strips the fake sites' page furniture, identically for both
classes: media credits ("Featured image via … Getty Images", "Video via
YouTube"), URLs, @handles, media tags ("[Video]", "WATCH:"), and maps curly
quotes / ellipsis / dashes to ASCII. Rule: strip only text that is not article
prose. Regexes were fixed after one inspection pass and **not tuned further** —
tuning until accuracy drops would be p-hacking.

**Outcome: the E1→E3 gap turned out small (98.4 → 97.7 → 97.3%).** That is a
finding, not a failure: the source signal is distributed across the writing
itself (wire register vs partisan-blog register), not concentrated in removable
markers. The core evidence is therefore the E2 probes and the E1→E4 collapse.

### E4 — Cross-corpus transfer
Train on ISOT headlines only (since LIAR has no bodies), test on LIAR with labels
collapsed to binary. Expect near-chance. *As built:* binary mapping is
true / mostly-true / half-true → real, barely-true / false / pants-fire → fake
(state this; half-true is the judgement call). All 12,836 LIAR rows are the test
set. Added an **in-domain control** (`e4_isot_titles`: ISOT headlines, usual
split) so the drop can be attributed to crossing datasets, not to headlines
carrying less information.

### Added 2026-10-13: more probes and confound checks
All new probes run on **fully stripped text** (E3 + E3b rules), so they can't use any known marker.
- **E2d sentiment only** — 8 VADER scores (title + body), random forest → 73.8%. Fake is more negative
  (title compound −0.17 vs −0.07).
- **E2e named entities only** — spaCy entity-type counts per 100 words, random forest → 81.1%. Real has
  ~3× more places (GPE) and more dates; fake more people.
- **E3c stripped function words** → 90.7%. Fake: ! : ? like this why you. Real: on -- had would could
  whether amid (hedged wire register).
- **E5 topic-matched** (real `politicsNews` + all fake = 28,666; `subject` only selects rows; chance
  60.9%): full 98.3%, stripped 96.7%, stripped function words **90.3%**, stripped metadata 85.8%.
  → topic does not explain the result.
- **SVM check** (LinearSVC on E1/E2a/E2b/E3b): 99.3 / 99.7 / 97.5 / 98.1% — slightly *higher* than LR.
- **E4 without half-true**: 51.1% vs 55.6% chance — label mapping doesn't matter.
- **Rule 8 extended once** (all apostrophes/quote marks → space, both classes): E5c's top fake feature was a
  bare "s" (fake scrape lost apostrophes: "Trump s", word + lone s/t in 91.6% of fake vs 38.8% of real).
  Before/after: E5c 98.0 → 90.3%, E3c 93.4 → 90.7%. Old numbers kept in `results/before_quote_fix/`.
  Report this openly (report section 6.6).

### E4b — full-article cross-corpus (added 2026-10-13, closes the headline-only limitation)
In `04_cross_corpus.py`. McIntire in-domain control 91.9% (learnable). **ISOT → McIntire full text
61.2%** (chance 50.7%) — labels 68% of McIntire's real (mainstream, non-Reuters) articles as fake.
Stripped 59.8%, stripped function words 63.9%. Reverse McIntire → ISOT 65.0% (chance 54.8%).
Honest caveat: ~10 points above chance transfers. Figure 7 shows within vs across for both corpora.

### Robustness (added)
Every split-based experiment is refit on 5 stratified random splits (seeds
42–46); results carry `accuracy_mean` / `accuracy_sd`. Headline numbers and
confusion matrices are from the fixed seed-42 split, shared by all experiments.

### Supporting
- Inspect logistic regression coefficients to identify and rank leakage tokens
- Error analysis on what remains separable after E3

---

## 8. The one table that is the entire project

| Condition | What the model sees | Accuracy | Mean ± SD, 5 splits | F1 (fake) | Chance |
|---|---|---|---|---|---|
| E1  Full text | Title + body | 98.4% | 98.5% ± 0.2% | 0.983 | 54.8% |
| E2a  First sentence only | Opening line of the body | 99.1% | 99.0% ± 0.1% | 0.990 | 54.8% |
| E2b  Function words only | Grammatical words + punctuation | 96.8% | 96.8% ± 0.2% | 0.964 | 54.8% |
| E2c  Metadata only | Eight numbers, no text | 86.2% | 86.3% ± 0.1% | 0.842 | 54.8% |
| E2d  Sentiment only | Eight VADER scores, stripped text | 73.8% | 74.1% ± 0.5% | 0.696 | 54.8% |
| E2e  Named entities only | Entity-type counts, stripped text | 81.1% | 81.6% ± 0.4% | 0.782 | 54.8% |
| E3  Source markers stripped | Full text minus dateline, 'Reuters', lead | 97.7% | 97.7% ± 0.2% | 0.975 | 54.8% |
| E3b  + page furniture stripped | E3 minus credits, URLs, handles, media tags; plain quotes | 97.3% | 97.3% ± 0.1% | 0.970 | 54.8% |
| E3c  Stripped, function words only | E3b text reduced to function words | 90.7% | 90.8% ± 0.1% | 0.895 | 54.8% |
| E4 control  ISOT headlines | Headline only, same dataset | 94.6% | 94.7% ± 0.4% | 0.939 | 54.8% |
| E4  ISOT → LIAR | Headline-trained, tested on LIAR | 45.5% | n/a (fixed test set) | 0.549 | 55.8% |
| E4  ISOT → LIAR, no half-true | LIAR without the ambiguous label | 51.1% | n/a (fixed test set) | 0.631 | 55.6% |
| E4b control  McIntire in-domain | McIntire full text, its own split | 91.9% | 91.2% ± 0.5% | 0.921 | 50.7% |
| E4b  ISOT → McIntire, full text | Full articles, other dataset | 61.2% | n/a (fixed test set) | 0.700 | 50.7% |
| E4b  ISOT → McIntire, stripped | Both sides E3b-stripped | 59.8% | n/a (fixed test set) | 0.687 | 50.7% |
| E4b  ISOT → McIntire, function words | Stripped function words | 63.9% | n/a (fixed test set) | 0.671 | 50.7% |
| E4b  McIntire → ISOT, full text | Reverse direction | 65.0% | n/a (fixed test set) | 0.648 | 54.8% |
| E5a  US politics only: full text | Topic-matched subset | 98.3% | 98.5% ± 0.1% | 0.986 | 60.9% |
| E5b  US politics only: stripped | Topic-matched, E3b text | 96.7% | 97.0% ± 0.2% | 0.973 | 60.9% |
| E5c  US politics only: stripped function words | Topic-matched, no markers, no content words | 90.3% | 90.5% ± 0.2% | 0.920 | 60.9% |
| E5d  US politics only: stripped metadata | Topic-matched, eight numbers | 85.8% | 85.6% ± 0.3% | 0.884 | 60.9% |
| E1  Full text (SVM) | As E1, linear SVM | 99.3% | 99.3% ± 0.1% | 0.992 | 54.8% |
| E2a  First sentence (SVM) | As E2a, linear SVM | 99.7% | 99.6% ± 0.1% | 0.996 | 54.8% |
| E2b  Function words (SVM) | As E2b, linear SVM | 97.5% | 97.4% ± 0.1% | 0.972 | 54.8% |
| E3b  Page furniture stripped (SVM) | As E3b, linear SVM | 98.1% | 98.1% ± 0.1% | 0.979 | 54.8% |
Filled 2026-10-13 (deduplicated data). Regenerated by `.\run 7` into `results/results_table.md`.

The planned table had six rows; E3b and the E4 control were added.

---

## 9. Repo layout and code contract

```
WSMA/
├── PROJECT_CONTEXT.md      this file
├── requirements.txt        pinned versions
├── README.md               how to reproduce (setup, data, run, expected numbers)
├── run.bat / run_all.py    `.\run` = whole pipeline; `.\run 3` = one step
├── .venv/                  project Python (system pip install fails on this PC)
├── data/                   True.csv, Fake.csv, liar/*.tsv, cache/ (spaCy output)
├── scripts/
│   ├── common.py           shared harness: load_isot, run_experiment, token dump
│   ├── transforms.py       every input view (first sentence, function words, stripping,
│   │                       metadata, sentiment, entities) + data/cache/ handling
│   ├── 00_get_data.py      downloads LIAR + McIntire, SHA-256-verifies all datasets
│   ├── 01_baseline.py      E1
│   ├── 02_partial_input.py E2a, E2b, E2c, body-only
│   ├── 03_stripped.py      E3, E3b
│   ├── 04_cross_corpus.py  E4 control, E4 transfer, E4 without half-true
│   ├── 05_more_probes.py   E2d sentiment, E2e entities, E3c stripped function words, SVM check
│   ├── 06_confounds.py     E5a-d topic-matched (US politics only)
│   └── 07_figures.py       reads results/, writes figures/ + results_table.md
├── results/                one JSON per experiment, *_tokens.json, results_table.md
├── figures/                the four charts (PNG, 200 dpi)
└── report/                 the Word report draft
```
Full pipeline: ~5 min (splits fitted in parallel; steps 1-6 three at a time; logs in
results/logs/). Datasets and data/cache/ are committed, so a copy of the repo needs no downloads.
Without the cache, the first run rebuilds it (~1.5 h).

**Shared contract — everything goes through this one function:**

```python
run_experiment(texts, labels, name) -> dict
```

Stratified 80/20 split, TF-IDF + logistic regression, computes accuracy /
precision / recall / F1 / confusion matrix, writes `results/{name}.json`, returns
the dict. Must also accept a precomputed numeric feature matrix in place of raw
text, for the metadata-only condition.

Every experiment writes its metrics to JSON. `07_figures.py` reads those files
rather than re-running anything — so redrawing a chart never costs a retrain.

---

## 10. Build order (solo)

| Stage | Work | Rough time |
|---|---|---|
| 0 | Setup, download ISOT and LIAR, scaffold repo | 1 evening |
| 1 | E1 baseline + coefficient dump | 1 evening |
| 2 | E2a, E2b, E2c — the core | 2–3 evenings |
| 3 | E3 and E4 | 2 evenings |
| 4 | Figures, error analysis, report | 2–3 evenings |

E2b is the highest-value and slowest step. Do it first within stage 2.

**Status (2026-10-13):** stages 0–3 done; figures done; report drafted in
`report/`. See section 16 for what remains.

### Environment
```bash
pip install pandas scikit-learn nltk spacy matplotlib seaborn
python -m spacy download en_core_web_sm
```

---

## 11. Figures (the output the teacher grades)

1. **Accuracy across all six conditions** — bar chart, dashed line at 50% chance.
   The single most important figure in the report.
2. **Top leakage tokens by coefficient** — horizontal bars, top 15 per class,
   provenance artifacts in a distinct colour.
3. **Confusion matrices** — E1 vs E3 side by side, showing where errors appear once
   the shortcut is gone.
4. **Accuracy degradation curve** — full → body-only → function-words → metadata.

*As built:* fig1 includes E3b and the E4 control, and the chance line is the
measured majority-class rate (54.8%), not an assumed 50%. fig2 colours a
hand-labelled, deliberately strict provenance list (agency name, dateline,
timestamp, credits, URL/embed fragments, media tags; "said" is *not* in it) —
the list is in `07_figures.py`. fig3 shows E1, E3 and E3b.

---

## 12. Presenter brief

*Abhishek presents alone. The story, the numbers and the expected questions. The
line-by-line code explanations, the talk structure and the prep checklist are in
`report/Code_Walkthrough.pdf`.*

**The pitch, in one line:** published fake news detectors report 99% accuracy; we
tested whether they detect deception or just recognise which newsroom an article
came from.

**The numbers to memorise:** baseline 98.4% (E1); function words only 96.8%
(E2b) — the headline; source markers stripped from both sides still 97.3%
(E3b); US politics only + stripped + function words 90.3% vs 60.9% chance (E5c);
cross-corpus 45.5% on LIAR, below its 55.8% chance (E4); full articles from other outlets
61.2% vs 50.7% chance (E4b). Chance on ISOT is 54.8%. The gap between the first and the last *is* the project.

**Anticipated questions and answers:**

- *"What's your accuracy?"* → Our detector gets 98.4%, like published results. The
  project shows that number doesn't measure fake news detection.
- *"Isn't fake news detection a common project?"* → It's common because it looks
  easy, and it looks easy because the benchmark is broken. We built the standard
  detector and then tested why it (and everyone's) reports 98–99%.
- *"What if you're wrong and accuracy doesn't drop?"* → That's a legitimate
  negative result and we report it. It would mean the linguistic signal is real,
  which is itself worth knowing. Either direction gives us a finding.
- *"Why not use BERT?"* → Logistic regression coefficients are directly
  interpretable, and the artifact identification depends on reading them. A
  transformer would obscure exactly the thing we're trying to see.
- *"Why these specific probes?"* → They come from Gururangan et al. (2018), the
  standard method for detecting dataset artifacts. We're applying an established
  technique, not inventing one.
- *"Hasn't someone already shown this?"* → Partly, yes — Zhou et al. (2021) showed
  source memorisation in unreliable-news datasets, and a 2026 preprint by Verma
  audited this same corpus. Our stripping and LIAR results agree with theirs,
  which is independent confirmation. What we add is the style-only probes: a
  model that sees only words like "the, of, a" and punctuation still scores ~97%.
- *"Why did stripping 'Reuters' barely change accuracy?"* → Because the source
  isn't in one word, it's in the whole way the article is written — wire
  reporting says "said", "told reporters"; partisan blogs say "this", "just",
  "you". Removing the label on the bottle doesn't change what's in it.
- *"Isn't it just topic — real has world news, fake is all US politics?"* → We tested that. On US
  politics only, with every marker stripped and only function words left, the model still gets 90.3%
  (chance 60.9%).
- *"Is this just because you used logistic regression?"* → No. A linear SVM gets slightly higher accuracy
  on every condition. A stronger model exploits the shortcut more, not less.
- *"LIAR is only headlines — what about full articles?"* → We tested a second dataset of full
  articles from NYT, NPR and others. The detector drops from 98% to 61%, and calls two-thirds of the
  genuine articles fake.
- *"Why is LIAR below chance?"* → The model learned "not written like Reuters =
  fake". LIAR statements aren't written like Reuters, so it calls most of them
  fake.

**What the presenter needs:** the results table, the figures and the leakage
token list, all in `report/Code_Walkthrough.pdf` §8–10.

---

## 13. Citations

*Verified 2026-10-13 against ACL Anthology / publisher / arXiv records: authors,
venue, year, pages. All 11 originals were correct; details completed below.
12 and 13 are new (see section 5).*

1. Gururangan, S., Swayamdipta, S., Levy, O., Schwartz, R., Bowman, S. R., &
   Smith, N. A. (2018). Annotation Artifacts in Natural Language Inference Data.
   *NAACL-HLT 2018, Vol. 2 (Short Papers)*, 107–112. doi:10.18653/v1/N18-2017
   — partial-input methodology (hypothesis-only: ~67% SNLI, 53% MultiNLI)
2. Schuster, T., Shah, D., Yeo, Y. J. S., Filizzola Ortiz, D. R., Santus, E., &
   Barzilay, R. (2019). Towards Debiasing Fact Verification Models.
   *EMNLP-IJCNLP 2019*, 3419–3425. doi:10.18653/v1/D19-1341
3. Geirhos, R., Jacobsen, J.-H., Michaelis, C., Zemel, R., Brendel, W., Bethge,
   M., & Wichmann, F. A. (2020). Shortcut Learning in Deep Neural Networks.
   *Nature Machine Intelligence*, 2(11), 665–673. doi:10.1038/s42256-020-00257-z
4. Ahmed, H., Traore, I., & Saad, S. (2017). Detection of Online Fake News Using
   N-Gram Analysis and Machine Learning Techniques. In *ISDDC 2017*, LNCS 10618,
   127–138. Springer, Cham. — ISOT dataset
5. Wang, W. Y. (2017). "Liar, Liar Pants on Fire": A New Benchmark Dataset for
   Fake News Detection. *ACL 2017, Vol. 2 (Short Papers)*, 422–426.
   doi:10.18653/v1/P17-2067 — LIAR dataset
6. Poliak, A., Naradowsky, J., Haldar, A., Rudinger, R., & Van Durme, B. (2018).
   Hypothesis Only Baselines in Natural Language Inference. *\*SEM 2018*,
   180–191. doi:10.18653/v1/S18-2023
7. Niven, T., & Kao, H.-Y. (2019). Probing Neural Network Comprehension of
   Natural Language Arguments. *ACL 2019*, 4658–4664. doi:10.18653/v1/P19-1459
8. McCoy, R. T., Pavlick, E., & Linzen, T. (2019). Right for the Wrong Reasons:
   Diagnosing Syntactic Heuristics in Natural Language Inference. *ACL 2019*,
   3428–3448. doi:10.18653/v1/P19-1334
9. Kaushik, D., Hovy, E., & Lipton, Z. C. (2020). Learning the Difference that
   Makes a Difference with Counterfactually-Augmented Data. *ICLR 2020*.
   arXiv:1909.12434
10. Gardner, M. et al. (2020). Evaluating Models' Local Decision Boundaries via
    Contrast Sets. *Findings of EMNLP 2020*, 1307–1323.
    doi:10.18653/v1/2020.findings-emnlp.117
11. Shu, K., Sliva, A., Wang, S., Tang, J., & Liu, H. (2017). Fake News Detection
    on Social Media: A Data Mining Perspective. *ACM SIGKDD Explorations
    Newsletter*, 19(1), 22–36. doi:10.1145/3137597.3137600
12. Zhou, X., Elfardy, H., Christodoulopoulos, C., Butler, T., & Bansal, M.
    (2021). Hidden Biases in Unreliable News Detection Datasets. *EACL 2021*,
    2482–2492. doi:10.18653/v1/2021.eacl-main.211 — **new; closest peer-reviewed
    prior work on fake-news datasets**
13. Verma, Y. (2026). What Does 99% Accuracy Measure? A Reproducible Audit of
    Shortcut Learning in a Widely Used Fake News Corpus. arXiv:2609.25006
    (preprint, not peer-reviewed). doi:10.48550/arXiv.2609.25006 — **new; same
    corpus.** Confirmed real 2026-10-13: v1 dated 26 Jul 2026, code at
    github.com/vermayuvraj/fake-news-detection.

---

## 14. Glossary

**ISOT** — Information Security and Object Technology, the lab at the University of
Victoria that built the dataset.

**LIAR** — Not an acronym. Named after the paper title, *"Liar, Liar Pants on
Fire"*.

**Dataset artifact** — An unintended pattern that correlates with the label but has
nothing to do with the task. "(Reuters)" appearing only in real articles is one.

**Shortcut learning** — When a model solves a task via an easy irrelevant cue
instead of the intended reasoning. This project is a shortcut-learning audit.

**Partial-input baseline** — A model deliberately denied part of its input. If it
still performs well, the remaining part contains leaked signal. The core method.

**Leakage** — Information reaching the model that shouldn't, inflating performance.
Here it leaks through publication source.

**Ablation** — Removing a component and re-measuring to isolate its contribution.

**Cross-corpus evaluation** — Train on one dataset, test on a different one. The
honest test of generalisation.

**TF-IDF** — Term Frequency–Inverse Document Frequency. Turns text into numbers by
weighting words frequent in one document but rare across the collection.

**Function words** — Grammatical glue: the, is, of, and. Structure without meaning.
Opposite of content words.

**Dateline** — The place-and-source prefix on a wire story:
`WASHINGTON (Reuters) -`. Prime leakage vector.

**Chance** — What guessing gets you, ~50% here. Partial-input results near chance
mean no leakage; well above means leakage.

---

## 15. Framing rules — do not violate these

- **The detector is the thing under test.** We built a standard fake news
  detector (E1, 98.4%) and then showed what its accuracy actually measures:
  "We built a fake news detector, got 98%, then proved the 98% is fake."
- **The project works even if the hypothesis is wrong.** Partial-input scores near
  chance would be a legitimate negative result. The project is not staked on a
  guess — say so when asked.
- **State limitations openly.** LIAR's lack of article bodies, the single-corpus
  scope, classical models only. Papers that name their limits read as more
  credible, not less.
- **Understand every line before shipping it.** Code written with AI assistance is
  fine; code that can't be defended in a viva is not. If a design choice can't be
  explained, it gets rewritten or removed.

---

## 16. Findings and status (2026-10-13)

**Findings worth stating in the viva / report:**
- E2a beats E1: the first sentence alone (99.1%) out-scores the full article. "reuters" weight −41.
- E2b: function words + punctuation only → 96.8%. Strongest features are typographic.
- **Curly quotes:** 50.8% of real articles contain them, 0.0% of fake — lost in the fake scrape
  (fake text reads "couldn t"). Typography alone flags half the real class.
- **"(Reuters)"** in 99.2% of real bodies, 0.04% of fake. **"Featured image via"** in 46.8% of fake,
  0% of real.
- Empty bodies: 630 of 631 are fake (dropped). `subject` values don't overlap between classes (never used).
- E3/E3b barely move accuracy: what remains is register — real: said / told / reporters / spokesman;
  fake: this / just / you / here / hillary / gop / via ("watch below, via Raw Story").
- E4 below chance: the model calls 77% of LIAR statements fake ("not Reuters-style = fake").
- All 5-split SDs ≤ 0.5 points.

**Done:** pipeline E1–E5 + E4b (McIntire) + SVM check + robustness (7 steps, `.\run`);
7 figures; results table; architecture diagram; citations verified (incl. Verma DOI, page confirmed
real; McIntire dataset cited); Word report (`report/WSMA_Report.docx`, 21 pages, title page filled in
by hand, sole author Abhishek; `report/build_report.py` regenerates it and OVERWRITES Word edits);
`report/Code_Walkthrough.pdf` (line-by-line guide, glossary, presenter brief, viva Q&A); repo on GitHub
(FirezTheGreat/fake-news-partial-input-baselines). Framing agreed: "we built a detector,
got 98%, proved the 98% is fake". Lab topics covered: tokenisation, cleaning, POS (E2b/E3c/E5c),
NER (E2e), sentiment (E2d), TF-IDF. Not done by decision: stemming/lemmatisation, transformer check.

All threats that could be tested have been: topic (E5), classifier (SVM), LIAR mapping, headline-only
transfer (E4b). Remaining stated limitations: probes run in depth on ISOT only; classical models only;
hand-written stripping rules (extended once, disclosed).

**Remaining (Abhishek):** rehearse with the walkthrough's presenter brief. Report reworded and
finalised by Abhishek; PDF export at `report/WSMA_Report.pdf`.
