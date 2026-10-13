# Partial-Input Baselines Reveal Construction Artifacts in Fake News Benchmarks

**Course:** Web and Social Media Analytics (WSMA)
**Team:** [Name 1], [Name 2]
**Date:** [date]

---

## 1. Abstract
*(~200 words — write this LAST, once results are in)*

Automated fake news detection is widely treated as a solved problem, with models
routinely reporting accuracies above 99% on standard benchmark corpora. This work
argues that such figures largely reflect dataset construction bias rather than
genuine deception detection. We audit the ISOT Fake News Dataset, in which
authentic articles are drawn from Reuters newswire while fabricated articles are
scraped from flagged partisan websites, creating systematic stylistic differences
between classes that are unrelated to veracity.

Adopting the partial-input baseline methodology established by Gururangan et al.
(2018) for natural language inference and extended by Schuster et al. (2019) to
fact verification, we train deliberately constrained classifiers that are denied
access to article content: first-sentence-only, function-words-only, and
metadata-only models. We additionally measure accuracy collapse under source-marker
removal, and test cross-corpus transfer to the LIAR dataset.

[RESULTS SENTENCE — e.g. "A function-words-only model, containing no semantic
content whatsoever, achieves X% accuracy, while cross-corpus transfer falls to Y%."]

Our findings indicate that reported benchmark performance substantially overstates
genuine capability, and we argue that partial-input probing and cross-corpus
evaluation should be treated as minimum reporting standards in this domain.

**Keywords:** fake news detection, dataset artifacts, shortcut learning,
partial-input baselines, benchmark evaluation

---

## 2. Introduction

- Rise of online misinformation; why automated detection matters for social media
  platforms
- Current state: published models report 99%+ accuracy on benchmark corpora such as
  ISOT, suggesting the problem is largely solved
- The tension: these models fail conspicuously in deployment despite near-perfect
  benchmark scores
- Our thesis: the benchmarks themselves are the problem. Accuracy is measuring
  publication source, not veracity
- Analogy to make the point accessible: a cancer classifier trained on samples where
  all positives came from one hospital and all negatives from another achieves 99%
  — by learning the hospital, not the disease
- Contribution statement: we apply an established artifact-auditing methodology to
  ISOT, independently confirming recent source-leakage findings (Zhou et al., 2021;
  Verma, 2026) and extending them with content-free *style* probes that quantify how
  much reported performance survives when the model is denied content

---

## 3. Literature Survey

**3.1 Fake news detection**
- Ahmed, Traore & Saad (2017) — introduced ISOT; n-gram + ML approaches
- Wang (2017) — introduced LIAR; highlighted difficulty of short-statement
  verification
- Shu et al. (2017) — survey of the field and its evaluation practices
- Note the trend: successive papers report incrementally higher accuracy on the same
  corpora

**3.2 Dataset artifacts and shortcut learning**
- Gururangan et al. (2018) — hypothesis-only models reach ~67% on SNLI without ever
  seeing the premise; establishes the partial-input baseline method
- Poliak et al. (2018) — generalises the finding across ten NLI datasets
- Niven & Kao (2019) — BERT's argument-reasoning performance traced to spurious
  unigrams
- McCoy et al. (2019) — HANS; high accuracy masking reliance on syntactic heuristics
- Geirhos et al. (2020) — formalises the phenomenon as *shortcut learning*

**3.3 Artifact auditing in fact verification**
- Schuster et al. (2019) — claim-only baselines remain competitive on FEVER against
  evidence-aware models. Closest prior work to ours.

**3.4 Artifacts in fake news datasets**
- Zhou et al. (2021, EACL) — unreliable-news datasets let models memorise the
  site→label mapping; accuracy drops >10 points on site-disjoint splits
- Verma (2026, arXiv preprint) — audits the same ISOT/Kaggle corpus: subject field
  alone gives F1 = 1.000; removing the newswire tag, metadata and duplicates only
  moves F1 0.994 → 0.981; LIAR transfer does not beat the majority class

**3.5 Mitigation approaches**
- Kaushik et al. (2020) — counterfactually augmented data
- Gardner et al. (2020) — contrast sets

**3.6 Identified gap**
Source leakage in fake news corpora is already established (Zhou et al., 2021), and
for ISOT specifically, metadata fields and the newswire tag are known to give the
labels away (Verma, 2026). Existing audits remove or isolate specific *fields* or
*tags*. What has not been tested is whether the class signal survives when the model
is denied content altogether and given only the *style* of the writing — function
words, the opening line, or punctuation statistics — and whether stripping the
markers of *both* publishing pipelines closes the gap. This work addresses that
narrower gap and independently replicates the earlier findings.

---

## 4. Problem Statement

Fake news classification models report near-perfect accuracy on benchmark corpora,
yet these corpora are constructed by pairing articles from structurally distinct
publishing pipelines. The real class in ISOT originates entirely from Reuters
newswire and carries consistent formatting conventions — datelines, agency
attribution, standardised byline structure — absent from the fake class.

Prior work has shown that classifiers on such corpora can learn publication
provenance rather than linguistic markers of deception (Zhou et al., 2021; Verma,
2026). If that is the whole story, reported performance is not merely optimistic but
categorically misdirected, and models trained on these corpora should be expected to
fail on any text outside the benchmark's construction.

**The problem this work addresses:** how much of ISOT benchmark performance survives
when the model is given only the *style* of an article and none of its content, and
whether removing both pipelines' source markers closes the gap.

---

## 5. Proposed System Architecture

### 5.1 Objectives

1. Establish a baseline reproducing the reported near-perfect accuracy on ISOT
2. Quantify the proportion of that accuracy recoverable *without* access to article
   content, via partial-input baselines
3. Measure accuracy collapse under explicit removal of source markers
4. Assess whether the learned decision boundary transfers to an independently
   constructed corpus
5. Identify and rank the specific lexical artifacts driving classification
6. Produce recommendations for evaluation practice in this domain

### 5.2 Architecture

```
                   ┌─────────────────────┐
                   │   ISOT Corpus       │
                   │  True.csv/Fake.csv  │
                   └──────────┬──────────┘
                              │
                   ┌──────────▼──────────┐
                   │   Preprocessing     │
                   │ clean → tokenise →  │
                   │ lemmatise → POS/NER │
                   └──────────┬──────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼─────┐      ┌────────▼────────┐     ┌──────▼──────┐
   │ FULL     │      │ PARTIAL-INPUT   │     │  STRIPPED   │
   │ TEXT     │      │ VIEWS           │     │  TEXT       │
   │          │      │ • first sent.   │     │ artifacts   │
   │ (E1)     │      │ • function wds  │     │ removed     │
   │          │      │ • metadata      │     │ (E3)        │
   └────┬─────┘      └────────┬────────┘     └──────┬──────┘
        │                     │  (E2)               │
        └─────────────────────┼─────────────────────┘
                              │
                   ┌──────────▼──────────┐
                   │  Feature Extraction │
                   │  TF-IDF / POS / NER │
                   │  sentiment / stats  │
                   └──────────┬──────────┘
                              │
                   ┌──────────▼──────────┐
                   │   Classifiers       │
                   │ LogReg / SVM / RF   │
                   └──────────┬──────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
  ┌─────▼──────┐    ┌─────────▼────────┐   ┌────────▼───────┐
  │ Comparison │    │ Coefficient      │   │ Cross-corpus   │
  │ Table      │    │ Inspection       │   │ Test on LIAR   │
  │            │    │ (leakage tokens) │   │ (E4)           │
  └────────────┘    └──────────────────┘   └────────────────┘
```

---

## 6. Methodology

### 6.1 Datasets
- **ISOT** — 44,898 articles; True.csv (21,417 Reuters) / Fake.csv (23,481 flagged
  sources). Fields: title, text, subject, date.
- **LIAR** — 12,836 PolitiFact-verified statements, 6-way labels, collapsed to
  binary for transfer testing. *Limitation: contains short statements only, no
  article bodies, so transfer evaluation is headline-level.*

### 6.2 Preprocessing
HTML cleaning → tokenisation (NLTK/spaCy) → stopword handling → lemmatisation.
Note that stopwords are **retained** for the function-words-only condition, where
they constitute the entire signal.

### 6.3 Feature extraction
| Family | Features |
|---|---|
| Lexical | TF-IDF, unigrams/bigrams/trigrams, lexical diversity |
| Syntactic | POS tag distribution, named-entity density (spaCy) |
| Affective | VADER and TextBlob polarity, subjectivity |
| Structural | Article length, punctuation counts, capitalisation ratio |

### 6.4 Models
Logistic regression (primary — coefficients are interpretable, which the artifact
analysis depends on), linear SVM, random forest. 80/20 stratified split, 5-fold
cross-validation.

### 6.5 Experimental conditions

| ID | Condition | Model input |
|---|---|---|
| E1 | Baseline | Full title + body |
| E2a | First sentence only | Opening sentence |
| E2b | Function words only | Content words removed |
| E2c | Metadata only | No text; structural features only |
| E3 | Artifact-stripped | Full text, source markers and datelines removed |
| E4 | Cross-corpus | Trained on ISOT, tested on LIAR |

### 6.6 Evaluation
Accuracy, precision, recall, F1, confusion matrices. Partial-input results are
interpreted against the ~50% chance baseline: results near chance indicate no
leakage; results substantially above chance indicate the condition's retained
information is sufficient to predict the label without doing the task.

---

## 7. Results and Discussion

*(Fill in after experiments. This table is the core deliverable.)*

### 7.1 Main results

| Condition | What the model sees | Accuracy | F1 |
|---|---|---|---|
| E1 — Full text | Everything | | |
| E2a — First sentence | Opening line | | |
| E2b — Function words | No content words | | |
| E2c — Metadata | No text at all | | |
| E3 — Artifacts stripped | Full text, no source markers | | |
| E4 — Cross-corpus | Different dataset (LIAR) | | |
| *Chance baseline* | *—* | *~50%* | *—* |

### 7.2 Leakage token analysis
*(Top-weighted features from the E1 logistic regression; flag provenance artifacts)*

| Rank | Token | Coefficient | Class | Artifact? |
|---|---|---|---|---|
| | | | | |

### 7.3 Discussion
- Interpret the gap between E1 and E3 as the magnitude of artifact contribution
- Interpret E2 results as evidence of content-independent separability
- Interpret E4 as the generalisation ceiling
- **If results contradict the hypothesis:** report honestly. Partial-input near
  chance would indicate the linguistic signal is genuine — a legitimate and
  publishable negative result.

### 7.4 Threats to validity
- Single benchmark corpus; findings may not generalise to all fake news datasets
- LIAR's structural difference (statements vs. articles) confounds E4; some transfer
  failure may be attributable to domain shift rather than artifact reliance
- Classical models only; transformer behaviour may differ

---

## 8. Conclusion and Future Work

**Conclusion:** Restate the quantified finding and its implication for evaluation
practice in fake news detection.

**Future work:**
- Extend the audit across multiple fake news corpora (FakeNewsNet, BuzzFeed-Webis)
  to establish whether the problem is corpus-specific or field-wide
- Apply mitigation strategies: counterfactually augmented data (Kaushik et al.,
  2020), contrast sets (Gardner et al., 2020)
- Construct a source-balanced corpus in which real and fake articles are drawn from
  matched publication pipelines
- Repeat the audit with transformer models to test whether artifact reliance
  persists at scale

---

## 9. References

1. Ahmed, H., Traore, I., & Saad, S. (2017). *Detection of Online Fake News Using
   N-Gram Analysis and Machine Learning Techniques.* ISDDC.
2. Gardner, M. et al. (2020). *Evaluating Models' Local Decision Boundaries via
   Contrast Sets.* Findings of EMNLP.
3. Geirhos, R. et al. (2020). *Shortcut Learning in Deep Neural Networks.* Nature
   Machine Intelligence, 2(11).
4. Gururangan, S. et al. (2018). *Annotation Artifacts in Natural Language
   Inference Data.* NAACL-HLT.
5. Kaushik, D., Hovy, E., & Lipton, Z. C. (2020). *Learning the Difference that
   Makes a Difference with Counterfactually-Augmented Data.* ICLR.
6. McCoy, T., Pavlick, E., & Linzen, T. (2019). *Right for the Wrong Reasons:
   Diagnosing Syntactic Heuristics in Natural Language Inference.* ACL.
7. Niven, T., & Kao, H.-Y. (2019). *Probing Neural Network Comprehension of Natural
   Language Arguments.* ACL.
8. Poliak, A. et al. (2018). *Hypothesis Only Baselines in Natural Language
   Inference.* *SEM.
9. Schuster, T. et al. (2019). *Towards Debiasing Fact Verification Models.* EMNLP.
10. Shu, K. et al. (2017). *Fake News Detection on Social Media: A Data Mining
    Perspective.* ACM SIGKDD Explorations, 19(1).
11. Wang, W. Y. (2017). *"Liar, Liar Pants on Fire": A New Benchmark Dataset for
    Fake News Detection.* ACL.
12. Zhou, X., Elfardy, H., Christodoulopoulos, C., Butler, T., & Bansal, M. (2021).
    *Hidden Biases in Unreliable News Detection Datasets.* EACL, 2482–2492.
13. Verma, Y. (2026). *What Does 99% Accuracy Measure? A Reproducible Audit of
    Shortcut Learning in a Widely Used Fake News Corpus.* arXiv:2609.25006.
    https://doi.org/10.48550/arXiv.2609.25006

*Verify every citation against the actual paper before submission — do not submit a
reference you have not personally confirmed exists and says what you claim.*
