# Project Context — WSMA Lab Project

> Working context file, kept in the project root so Claude Code can read it instead of being
> re-briefed every session. For learning the project, read `report/Code_Walkthrough.pdf`; this
> file is the short reference.
>
> **Ownership:** Abhishek works on this project alone (a former teammate, Yuvika, is no longer
> part of it). He wrote and owns the code and report, gives the whole talk and answers every
> question.

---

## 1. The project

**Title:** Partial-Input Baselines Reveal Construction Artifacts in Fake News Benchmarks
(subtitle: *An audit of the ISOT fake news dataset*).

**One line:** "I built a fake news detector, got 98%, then proved the 98% is fake."

ISOT's real articles all come from Reuters and its fake ones from flagged partisan sites, so a
classifier can get the label right by recognising the publisher's writing style without judging
truth. Partial-input baselines (models denied the content) test this: if they still score far
above chance, the dataset leaks the label. The detector is the thing under test.

Analogy: cancer scans all from Hospital A, healthy scans all from Hospital B — a model hits 99% by
recognising the hospital, and fails at Hospital C.

## 2. Course requirements (WSMA = Web and Social Media Analytics)

- Lab text processing: covered — cleaning (empty/duplicate removal), tokenisation, POS tagging
  (E2b/E3c/E5c), NER (E2e), VADER sentiment (E2d), TF-IDF, regex processing (E3/E3b).
  Stemming/lemmatisation deliberately not used (it would not touch function words or punctuation,
  where the signal is).
- Prediction/ML on top; grounded in named papers; research-paper shaped.
- Evaluated on: presentation, dataset, model/algorithm, output.
- Report order: Abstract → Introduction → Literature Survey → Problem Statement → Proposed
  (architecture, objectives) → Methodology (no citations) → Results and Discussion (no citations)
  → Conclusion → Future Work → References.

## 3. Novelty — what to claim and what not to

Do **not** claim the idea is new. Closest prior work:
- **Zhou et al. (2021, EACL)** — unreliable-news datasets let models memorise source → label;
  source-disjoint splits cost >10 points.
- **Verma (2026, arXiv preprint, not peer-reviewed)** — audits this same corpus: removing the
  newswire tag, metadata and duplicates barely moves F1; LIAR transfer fails.

**Contribution:** independent replication (E3, E4 agree with Verma) plus extensions: content-free
style probes (E2a–E2e, especially function words only), stripping *both* classes' markers (E3b),
the topic-matched control (E5), a full-article cross-corpus test (E4b), the classifier check, and
the typography / empty-body artifacts.

Method sources: Gururangan et al. 2018 (partial-input baselines), Poliak et al. 2018, Schuster et
al. 2019 (closest analogue: fact verification), Geirhos et al. 2020 (shortcut learning).
Remedies, future work only: Kaushik et al. 2020, Gardner et al. 2020.

## 4. Data

| Dataset | Size | Use |
|---|---|---|
| ISOT (`data/True.csv`, `data/Fake.csv`), Kaggle "Fake and Real News Dataset" | 44,898 → **38,644** after cleaning (21,191 real / 17,453 fake) | all experiments |
| LIAR (`data/liar/*.tsv`, UCSB), no header, 14 columns | 12,836 statements (10,269 / 1,284 / 1,283) | E4 test set only |
| McIntire (`data/mcintire/fake_or_real_news.csv`, github.com/joolsa/fake_real_news_dataset) | 6,335 → 6,059 (2,989 real / 3,070 fake) | E4b |

Cleaning (`load_isot()`): drop 631 empty bodies (630 fake — a leak), then 5,623 duplicate bodies
(none crossed classes). Chance on the ISOT test split = 54.8%. LIAR six-way labels → binary:
true / mostly-true / half-true = real. All data files are SHA-256-checked by step 0, and the
datasets plus spaCy/VADER caches are committed (`.gitattributes`: `data/** -text`).

## 5. Experiments (as built)

All go through `run_experiment()` in `scripts/common.py`: stratified 80/20 split, seed 42 (same
test articles for every experiment), TF-IDF + logistic regression in a Pipeline (random forest for
numeric features), 5 splits (seeds 42–46) for mean ± SD, metrics to `results/<name>.json`.

| | What the model sees | Script |
|---|---|---|
| E1 | Full text (title + body) | 01 |
| E2a / E2b / E2c | First sentence / function words only / 8 surface numbers (RF) | 02 |
| E3 / E3b | Reuters markers stripped / + fake sites' page furniture and typography, both classes | 03 |
| E4 / E4b | ISOT headlines → LIAR (+ control, + no half-true) / ISOT full text → McIntire (+ control, stripped, function words, reverse) | 04 |
| E2d / E2e / E3c / SVM | Sentiment (RF) / entity counts (RF) / stripped function words / LinearSVC rerun of E1, E2a, E2b, E3b | 05 |
| E5a–d | US politics only (topic-matched; chance 60.9%): full, stripped, stripped function words, metadata | 06 |

Stripping rules live in `scripts/transforms.py`. They were written after one inspection and
changed **once**: the typography rule was extended to every apostrophe and quote mark after E5c's
coefficients exposed the straight-quote case (E5c 98.0 → 90.3%, E3c 93.4 → 90.7%). Pre-fix results
are kept in `results/before_quote_fix/` and the change is reported in the report.

## 6. Results

Full table: `results/results_table.md` (25 rows). The numbers to know:

| Number | Condition |
|---|---|
| 98.4% | E1, the detector (chance 54.8%) |
| 99.1% | E2a, first sentence only |
| 96.8% | E2b, function words only — the headline |
| 86.2% | E2c, eight numbers, no words |
| 97.3% | E3b, every marker stripped from both classes |
| 90.3% vs 60.9% | E5c, US politics only, stripped, function words |
| 45.5% vs 55.8% | E4, ISOT → LIAR (below chance) |
| 61.2% vs 50.7% | E4b, ISOT → McIntire full articles (68% of real called fake); McIntire's own model 91.9% |
| 99.3 / 99.7 / 97.5 / 98.1% | SVM on E1 / E2a / E2b / E3b — slightly higher than LR |

Findings behind them:
- "reuters" is the strongest E2a feature (weight −41.3, about four times any other).
- Curly quotes in 50.8% of real articles, 0% of fake; "(Reuters)" in 99.2% of real bodies, 0.04%
  of fake; "Featured image via" in 34.9% of fake, 0% of real; a word followed by a lone s/t
  ("Trump s") in 91.6% of fake vs 38.8% of real stripped articles.
- After stripping, real = wire attribution (said, told, reporters, spokesman); fake = blog voice
  (this, just, you, here, hillary, gop, via).
- All 5-split SDs ≤ 0.5 points.

Limitations to state: probes in depth on ISOT only; classical models only; hand-written stripping
rules (extended once, disclosed).

## 7. Repository

```
run.bat / run_all.py     .\run = whole pipeline (~5 min); .\run 3 = one step
requirements.txt         pinned versions (+ python -m spacy download en_core_web_sm)
data/                    ISOT, LIAR, McIntire, cache/ (saved spaCy/VADER output)
scripts/common.py        load_isot(), run_experiment(), print_metrics(), save_top_tokens()
scripts/transforms.py    every restricted view + caching
scripts/00–07            data check, E1, E2, E3, E4, more probes + SVM, E5, figures
results/                 one JSON per experiment, *_tokens.json, results_table.md, before_quote_fix/
figures/                 seven charts used in the report
report/                  WSMA_Report.docx/.pdf (final, hand-edited), WSMA_Report_IEEE.docx/.pdf
                         (IEEE two-column version, the one to submit), Code_Walkthrough.pdf,
                         their generators, architecture diagram
```

`report/build_report.py` generated the first draft of the report; running it again **overwrites**
the hand-edited final version. `report/build_ieee.py` converts the edited report to IEEE format
(text unchanged; citations become [n], sections I/II, "Fig."/"TABLE I" captions); rerun it after any
edit to the .docx, then export the PDF from Word. `report/build_walkthrough.py` rebuilds the walkthrough PDF from the
code (safe to rerun). GitHub: FirezTheGreat/fake-news-partial-input-baselines.

## 8. Rules

- **Framing:** it is a fake news detector, and the detector is the thing under test.
- **Either result is a finding:** probes near chance would have been a legitimate negative result.
- **State limitations openly.**
- **Understand every line:** code that can't be defended in the viva gets rewritten or removed.
- **Commits:** credit only Abhishek (no Claude co-author line).

## 9. Citations (verified 2026-10-13)

1. Gururangan, S., Swayamdipta, S., Levy, O., Schwartz, R., Bowman, S. R., & Smith, N. A. (2018).
   Annotation Artifacts in Natural Language Inference Data. *NAACL-HLT 2018*, 107–112.
   doi:10.18653/v1/N18-2017
2. Schuster, T., Shah, D., Yeo, Y. J. S., Filizzola Ortiz, D. R., Santus, E., & Barzilay, R.
   (2019). Towards Debiasing Fact Verification Models. *EMNLP-IJCNLP 2019*, 3419–3425.
   doi:10.18653/v1/D19-1341
3. Geirhos, R., Jacobsen, J.-H., Michaelis, C., Zemel, R., Brendel, W., Bethge, M., & Wichmann,
   F. A. (2020). Shortcut Learning in Deep Neural Networks. *Nature Machine Intelligence*, 2(11),
   665–673. doi:10.1038/s42256-020-00257-z
4. Ahmed, H., Traore, I., & Saad, S. (2017). Detection of Online Fake News Using N-Gram Analysis
   and Machine Learning Techniques. *ISDDC 2017*, LNCS 10618, 127–138. Springer. — ISOT
5. Wang, W. Y. (2017). "Liar, Liar Pants on Fire": A New Benchmark Dataset for Fake News
   Detection. *ACL 2017*, 422–426. doi:10.18653/v1/P17-2067 — LIAR
6. Poliak, A., Naradowsky, J., Haldar, A., Rudinger, R., & Van Durme, B. (2018). Hypothesis Only
   Baselines in Natural Language Inference. *\*SEM 2018*, 180–191. doi:10.18653/v1/S18-2023
7. Niven, T., & Kao, H.-Y. (2019). Probing Neural Network Comprehension of Natural Language
   Arguments. *ACL 2019*, 4658–4664. doi:10.18653/v1/P19-1459
8. McCoy, R. T., Pavlick, E., & Linzen, T. (2019). Right for the Wrong Reasons: Diagnosing
   Syntactic Heuristics in Natural Language Inference. *ACL 2019*, 3428–3448.
   doi:10.18653/v1/P19-1334
9. Kaushik, D., Hovy, E., & Lipton, Z. C. (2020). Learning the Difference that Makes a Difference
   with Counterfactually-Augmented Data. *ICLR 2020*. arXiv:1909.12434
10. Gardner, M. et al. (2020). Evaluating Models' Local Decision Boundaries via Contrast Sets.
    *Findings of EMNLP 2020*, 1307–1323. doi:10.18653/v1/2020.findings-emnlp.117
11. Shu, K., Sliva, A., Wang, S., Tang, J., & Liu, H. (2017). Fake News Detection on Social Media:
    A Data Mining Perspective. *ACM SIGKDD Explorations*, 19(1), 22–36. doi:10.1145/3137597.3137600
12. Zhou, X., Elfardy, H., Christodoulopoulos, C., Butler, T., & Bansal, M. (2021). Hidden Biases
    in Unreliable News Detection Datasets. *EACL 2021*, 2482–2492.
    doi:10.18653/v1/2021.eacl-main.211
13. Verma, Y. (2026). What Does 99% Accuracy Measure? A Reproducible Audit of Shortcut Learning in
    a Widely Used Fake News Corpus. arXiv:2609.25006 (preprint). doi:10.48550/arXiv.2609.25006
14. McIntire, G. fake_or_real_news dataset. github.com/joolsa/fake_real_news_dataset

## 10. Status (2026-10-15)

Everything is built, verified and pushed: pipeline reproduces from a fresh GitHub clone in ~4 min
with identical results; report finalised by Abhishek (PDF exported); walkthrough PDF current.
**Remaining:** learning the project and rehearsing (walkthrough §9–10).
