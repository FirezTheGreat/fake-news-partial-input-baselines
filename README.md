# Partial-Input Baselines Reveal Construction Artifacts in Fake News Benchmarks

A fake news detector trained on the ISOT dataset scores 98.4%. This project tests whether that
number measures fake news detection. It doesn't: models that never see an article's content still
score up to 97%, and the detector drops to 45–61% on other datasets. Full write-up:
[report/WSMA_Report.docx](report/WSMA_Report.docx).

## Reproduce it

Tested on Windows with Python 3.10. Needs about 1 GB of disk.

**1. Set up Python** (from the project folder):

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt        # macOS/Linux: .venv/bin/python
.venv\Scripts\python -m spacy download en_core_web_sm
```

**2. Get ISOT by hand.** It needs a free Kaggle account:
[kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset](https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset).
Unzip it and put `True.csv` and `Fake.csv` in `data/`. The other two datasets (LIAR and McIntire)
download automatically in the next step.

**3. Run everything:**

```bash
.\run                      # Windows (PowerShell); in cmd just: run
.venv/bin/python run_all.py   # macOS/Linux
```

Step 0 downloads LIAR and McIntire and checks every data file against the checksum of the copy the
published results came from. If anything is missing or different, it stops and says what to do.

**How long it takes:** about 1.5 hours the first time, because spaCy tags every article and VADER
scores them. That work is saved to `data/cache/` (71 MB), and later runs take about 15 minutes.
To skip the wait, copy someone's `data/cache/` folder into yours: each cache file records a hash of
the text it was made from, so a cache that doesn't match your data is ignored and rebuilt.

## What each step does

| Step | Script | Produces |
|---|---|---|
| 0 | `00_get_data.py` | Downloads LIAR and McIntire; verifies all datasets |
| 1 | `01_baseline.py` | E1: TF-IDF + logistic regression on full text |
| 2 | `02_partial_input.py` | E2a–c: first sentence, function words, metadata only |
| 3 | `03_stripped.py` | E3, E3b: source markers and page clutter removed |
| 4 | `04_cross_corpus.py` | E4, E4b: transfer to LIAR and McIntire |
| 5 | `05_more_probes.py` | E2d, E2e, E3c: sentiment, entities, stripped function words; SVM check |
| 6 | `06_confounds.py` | E5: everything again on US politics only (topic control) |
| 7 | `07_figures.py` | `figures/*.png` and `results/results_table.md` |

Run single steps with `.\run 3`, or several with `.\run 3 7`. Every experiment writes its metrics
to `results/<name>.json`; step 7 only reads those files, so redrawing figures never retrains anything.

## Checking your results match

All splits use a fixed seed, so a correct reproduction gives these numbers exactly:

| Condition | Accuracy |
|---|---|
| E1 full text | 98.4% |
| E2b function words only | 96.8% |
| E5c US politics only, stripped, function words | 90.3% |
| E4 ISOT → LIAR | 45.5% |
| E4b ISOT → McIntire | 61.2% |

The full table, with all 25 conditions, is in [results/results_table.md](results/results_table.md).

## Rebuilding the report

```bash
.venv\Scripts\python report\build_report.py .
```

This regenerates `report/WSMA_Report.docx` from the results and figures. **It overwrites the file,
including any edits made in Word.** Open it in Word afterwards and press F9 to update the contents
page.

## Layout

```
data/        datasets (not in git) and data/cache/ (spaCy/VADER output, not in git)
scripts/     common.py (shared harness), transforms.py (input views), 00–07 (steps)
results/     one JSON per experiment, top-coefficient lists, results_table.md
figures/     the charts used in the report
report/      the Word report, its generator and the architecture diagram
```

[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) has the full background, design decisions and findings.
