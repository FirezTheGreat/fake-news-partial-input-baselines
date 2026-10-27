# Partial-Input Baselines Reveal Construction Artifacts in Fake News Benchmarks

A fake news detector trained on the ISOT dataset scores 98.4%. This project tests whether that
number measures fake news detection. It doesn't: models that never see an article's content still
score up to 97%, and the detector drops to 45–61% on other datasets.

- Report (IEEE format, as submitted): [report/WSMA_Report_IEEE.pdf](report/WSMA_Report_IEEE.pdf);
  single-column version: [report/WSMA_Report.pdf](report/WSMA_Report.pdf)
- Line-by-line code walkthrough, glossary and viva guide:
  [report/Code_Walkthrough.pdf](report/Code_Walkthrough.pdf)

## Reproduce it

Tested on Windows with Python 3.10, 16 cores and 32 GB RAM. Needs about 1.5 GB of disk.

**1. Set up Python** (from the project folder):

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt        # macOS/Linux: .venv/bin/python
.venv\Scripts\python -m spacy download en_core_web_sm
```

**2. Run everything:**

```bash
.\run                         # Windows (PowerShell); in cmd just: run
.venv/bin/python run_all.py   # macOS/Linux
```

That's it. All three datasets and the saved spaCy/VADER output (`data/cache/`) are included in the
repository, so nothing is downloaded and a full run takes **about 5 minutes** on a 16-core laptop.
Step 0 checks every data file against the checksum of the copy the published results came from.

**If the data is ever missing** (for example, a copy made without `data/`): step 0 re-downloads LIAR
and McIntire automatically; ISOT needs a free Kaggle account at
[kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset](https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset)
(put `True.csv` and `Fake.csv` in `data/`). Without `data/cache/`, the first run rebuilds it, which
takes about 1.5 hours; later runs are back to about 5 minutes.

**Why it's fast:** each experiment fits its five random splits in parallel, and steps 1–6, which
don't depend on each other, run three at a time with their output in `results/logs/`. Running them
one at a time (`.\run 1 2 3 4 5 6 7`) gives identical results, just slower.

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

## The documents

`report/WSMA_Report.docx` is the final, hand-edited report. `report/build_report.py` produced its
first draft; **don't run it again**, because it would overwrite the edited version.
`report/build_ieee.py` converts the edited report into the IEEE two-column version
(`WSMA_Report_IEEE.docx`; export to PDF from Word) without changing its text.
`report/Code_Walkthrough.pdf` is rebuilt from the code with
`.venv\Scripts\python report\build_walkthrough.py` (needs Microsoft Edge), so its listings always
match the scripts.

## Layout

```
data/        the three datasets and data/cache/ (saved spaCy/VADER output)
scripts/     common.py (shared harness), transforms.py (input views), 00–07 (steps)
results/     one JSON per experiment, top-coefficient lists, results_table.md
figures/     the charts used in the report
report/      the report (.docx and .pdf), Code_Walkthrough.pdf, their generators, the diagram
```

[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) has the full background, design decisions and findings.
