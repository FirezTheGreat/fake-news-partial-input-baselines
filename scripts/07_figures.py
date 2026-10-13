"""Figures and results table. Reads results/*.json only; never retrains anything.

figures/fig1_accuracy.png      accuracy across all conditions, chance line
figures/fig2_leakage_tokens.png top 15 E1 tokens per class, provenance markers highlighted
figures/fig3_confusion.png     E1 vs E3 vs E3b confusion matrices
figures/fig4_degradation.png   accuracy as information is removed
figures/fig5_topic_matched.png E5: the strictest probes on US-politics-only data
figures/fig6_svm_check.png     logistic regression vs linear SVM on the same inputs
results/results_table.md       the results table for the report
"""

import json

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import PercentFormatter

from common import RESULTS_DIR, ROOT

FIGURES_DIR = ROOT / "figures"

# Validated palette (dataviz reference instance, light mode).
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
NEUTRAL_BAR = "#b5b4ad"

# Tokens that identify the publishing pipeline rather than the claim: agency name,
# dateline, timestamp format, image credits, URL / embed fragments, media tags.
# Hand-labelled; deliberately strict (attribution verbs like 'said' are left out).
PROVENANCE = {
    "reuters", "washington", "edt", "via", "image", "images", "getty", "featured",
    "pic", "https", "com", "www", "twitter", "video", "watch", "read", "breaking", "wire",
}

CONDITIONS = [  # (results file, label for figures and table, what the model sees); figure 1 rows
    ("e1_baseline", "E1  Full text", "Title + body"),
    ("e2a_first_sentence", "E2a  First sentence only", "Opening line of the body"),
    ("e2b_function_words", "E2b  Function words only", "Grammatical words + punctuation"),
    ("e2c_metadata", "E2c  Metadata only", "Eight numbers, no text"),
    ("e2d_sentiment", "E2d  Sentiment only", "Eight VADER scores, stripped text"),
    ("e2e_entities", "E2e  Named entities only", "Entity-type counts, stripped text"),
    ("e3_stripped", "E3  Source markers stripped", "Full text minus dateline, 'Reuters', lead"),
    ("e3b_furniture_stripped", "E3b  + page furniture stripped",
     "E3 minus credits, URLs, handles, media tags; plain quotes"),
    ("e3c_stripped_function_words", "E3c  Stripped, function words only", "E3b text reduced to function words"),
    ("e4_isot_titles", "E4 control  ISOT headlines", "Headline only, same dataset"),
    ("e4_liar_transfer", "E4  ISOT → LIAR", "Headline-trained, tested on LIAR"),
]
TABLE_ONLY = [  # extra rows for the results table (different test sets or chance levels)
    ("e4_liar_no_halftrue", "E4  ISOT → LIAR, no half-true", "LIAR without the ambiguous label"),
    ("e5a_topic_full", "E5a  US politics only: full text", "Topic-matched subset"),
    ("e5b_topic_stripped", "E5b  US politics only: stripped", "Topic-matched, E3b text"),
    ("e5c_topic_function_words", "E5c  US politics only: stripped function words",
     "Topic-matched, no markers, no content words"),
    ("e5d_topic_metadata", "E5d  US politics only: stripped metadata", "Topic-matched, eight numbers"),
    ("e1_svm", "E1  Full text (SVM)", "As E1, linear SVM"),
    ("e2a_svm", "E2a  First sentence (SVM)", "As E2a, linear SVM"),
    ("e2b_svm", "E2b  Function words (SVM)", "As E2b, linear SVM"),
    ("e3b_svm", "E3b  Page furniture stripped (SVM)", "As E3b, linear SVM"),
]

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"],
    "font.size": 10,
    "text.color": INK,
    "axes.labelcolor": INK_2,
    "axes.edgecolor": AXIS,
    "axes.facecolor": SURFACE,
    "figure.facecolor": SURFACE,
    "xtick.color": MUTED,
    "ytick.color": INK_2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


def load(name):
    path = RESULTS_DIR / f"{name}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def title(ax, main, sub):
    ax.set_title(main, loc="left", fontsize=12, fontweight="semibold", pad=22)
    ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=INK_2, va="bottom")


def fig1_accuracy(results):
    rows = [(label, results[name]) for name, label, _ in CONDITIONS if results.get(name)]
    labels = [label for label, _ in rows][::-1]
    acc = [r["accuracy"] for _, r in rows][::-1]
    chance = results["e1_baseline"]["majority_baseline"]

    fig, ax = plt.subplots(figsize=(8, 0.5 * len(rows) + 1.4))
    y = np.arange(len(rows))
    ax.barh(y, acc, height=0.55, color=BLUE, zorder=2)
    for yi, a in zip(y, acc):
        ax.text(a + 0.01, yi, f"{a:.1%}", va="center", fontsize=9, color=INK)
    ax.axvline(chance, color=INK_2, linestyle=(0, (4, 3)), linewidth=1, zorder=3)
    ax.text(chance, -0.75, f" chance {chance:.1%}", fontsize=8.5, color=INK_2, va="center")
    ax.set_ylim(-1, len(rows) - 0.5)

    ax.set_yticks(y, labels)
    ax.set_xlim(0, 1.08)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(axis="y", length=0)
    title(ax, "Accuracy by condition",
          "Chance = always guessing the majority class on the ISOT test split "
          "(LIAR's is %.1f%%)" % (100 * results["e4_liar_transfer"]["majority_baseline"])
          if results.get("e4_liar_transfer") else "Chance = majority class on the test split")
    fig.savefig(FIGURES_DIR / "fig1_accuracy.png")
    plt.close(fig)


def fig2_tokens(tokens):
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.2))
    for ax, cls, heading in ((axes[0], "real", "Predicts REAL"), (axes[1], "fake", "Predicts FAKE")):
        top = tokens[cls][:15][::-1]
        words = [w for w, _ in top]
        weights = [abs(c) for _, c in top]
        colors = [ORANGE if w in PROVENANCE else NEUTRAL_BAR for w in words]
        y = np.arange(len(top))
        ax.barh(y, weights, height=0.6, color=colors, zorder=2)
        ax.set_yticks(y, words)
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
        ax.set_xlabel("|coefficient|")
        ax.set_title(heading, loc="left", fontsize=11, fontweight="semibold")

    handles = [plt.Rectangle((0, 0), 1, 1, color=ORANGE), plt.Rectangle((0, 0), 1, 1, color=NEUTRAL_BAR)]
    fig.legend(handles, ["Source / page-furniture marker", "Other token"], loc="upper left",
               bbox_to_anchor=(0.01, 1.0), ncol=2, frameon=False, fontsize=9)
    fig.suptitle("Strongest E1 logistic regression tokens per class", x=0.01, y=1.06,
                 ha="left", fontsize=12, fontweight="semibold")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig2_leakage_tokens.png")
    plt.close(fig)


def fig3_confusion(panels):
    """panels: list of (heading, result) pairs, drawn side by side on one colour scale."""
    cmap = LinearSegmentedColormap.from_list("blue", ["#f0f5fc", "#cde2fb", "#6da7ec", "#2a78d6", "#104281"])
    matrices = [np.array(r["confusion_matrix"]) for _, r in panels]
    vmax = max(m.max() for m in matrices)

    fig, axes = plt.subplots(1, len(panels), figsize=(4.3 * len(panels), 3.9))
    for ax, m, (heading, r) in zip(axes, matrices, panels):
        ax.imshow(m, cmap=cmap, vmin=0, vmax=vmax)
        row_totals = m.sum(axis=1, keepdims=True)
        for i in range(2):
            for j in range(2):
                text_color = "white" if m[i, j] > vmax * 0.5 else INK
                ax.text(j, i, f"{m[i, j]:,}\n{m[i, j] / row_totals[i, 0]:.1%}", ha="center",
                        va="center", color=text_color, fontsize=10)
        ax.set_xticks([0, 1], ["Real", "Fake"])
        ax.set_yticks([0, 1], ["Real", "Fake"])
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_title(f"{heading}\naccuracy {r['accuracy']:.1%}, {m[0, 1] + m[1, 0]} errors",
                     loc="left", fontsize=10.5)
    fig.suptitle("Confusion matrices, same test split (row % in each cell)", x=0.01, ha="left",
                 fontsize=12, fontweight="semibold")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig3_confusion.png")
    plt.close(fig)


def fig4_degradation(results):
    steps = [("e1_baseline", "Full text"), ("e2_body_only", "Body only"),
             ("e2b_function_words", "Function words"), ("e2c_metadata", "Metadata only")]
    steps = [(label, results[name]["accuracy"]) for name, label in steps if results.get(name)]
    chance = results["e1_baseline"]["majority_baseline"]
    x = np.arange(len(steps))
    acc = [a for _, a in steps]

    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.plot(x, acc, color=BLUE, linewidth=2, solid_capstyle="round", zorder=2)
    ax.scatter(x, acc, s=70, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
    for xi, a in zip(x, acc):
        ax.text(xi, a + 0.025, f"{a:.1%}", ha="center", fontsize=9)
    ax.axhline(chance, color=INK_2, linestyle=(0, (4, 3)), linewidth=1)
    ax.text(-0.25, chance + 0.01, f"chance {chance:.1%}", va="bottom", fontsize=8.5, color=INK_2)

    ax.set_xticks(x, [label for label, _ in steps])
    ax.set_xlim(-0.3, len(steps) - 0.4)
    ax.set_ylim(0.4, 1.05)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(axis="x", length=0)
    ax.set_xlabel("Less information available to the model →")
    title(ax, "Accuracy as content is removed", "Logistic regression throughout, except metadata (random forest)")
    fig.savefig(FIGURES_DIR / "fig4_degradation.png")
    plt.close(fig)


def fig5_topic_matched(results):
    steps = [("e5a_topic_full", "Full text"), ("e5b_topic_stripped", "All markers stripped"),
             ("e5c_topic_function_words", "Stripped, function words only"),
             ("e5d_topic_metadata", "Stripped, eight numbers only")]
    steps = [(label, results[name]) for name, label in steps if results.get(name)]
    if not steps:
        return
    labels = [label for label, _ in steps][::-1]
    acc = [r["accuracy"] for _, r in steps][::-1]
    chance = steps[0][1]["majority_baseline"]

    fig, ax = plt.subplots(figsize=(8, 0.5 * len(steps) + 1.6))
    y = np.arange(len(steps))
    ax.barh(y, acc, height=0.55, color=BLUE, zorder=2)
    for yi, a in zip(y, acc):
        ax.text(a + 0.01, yi, f"{a:.1%}", va="center", fontsize=9, color=INK)
    ax.axvline(chance, color=INK_2, linestyle=(0, (4, 3)), linewidth=1, zorder=3)
    ax.text(chance, -0.75, f" chance {chance:.1%}", fontsize=8.5, color=INK_2, va="center")
    ax.set_ylim(-1, len(steps) - 0.5)
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 1.08)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(axis="y", length=0)
    title(ax, "Topic-matched check: US politics only, both classes",
          "Real world-news articles removed, so topic cannot separate the classes. "
          "Chance = majority class (fake) on this subset")
    fig.savefig(FIGURES_DIR / "fig5_topic_matched.png")
    plt.close(fig)


def fig6_svm_check(results):
    pairs = [("e1_baseline", "e1_svm", "E1  Full text"), ("e2a_first_sentence", "e2a_svm", "E2a  First sentence"),
             ("e2b_function_words", "e2b_svm", "E2b  Function words"),
             ("e3b_furniture_stripped", "e3b_svm", "E3b  Page furniture stripped")]
    pairs = [(results[a]["accuracy"], results[b]["accuracy"], label)
             for a, b, label in pairs if results.get(a) and results.get(b)]
    if not pairs:
        return
    pairs = pairs[::-1]
    y = np.arange(len(pairs))

    fig, ax = plt.subplots(figsize=(8, 0.55 * len(pairs) + 1.7))
    for yi, (lr, svm, _) in zip(y, pairs):
        ax.plot([lr, svm], [yi, yi], color=GRID, linewidth=2, zorder=1)
    ax.scatter([p[0] for p in pairs], y, s=70, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3,
               label="Logistic regression")
    ax.scatter([p[1] for p in pairs], y, s=70, color=ORANGE, edgecolor=SURFACE, linewidth=2, zorder=3,
               label="Linear SVM")
    for yi, (lr, svm, _) in zip(y, pairs):
        ax.text(min(lr, svm) - 0.002, yi, f"{lr:.1%} / {svm:.1%}  ", va="center", ha="right",
                fontsize=8.5, color=INK_2)
    ax.set_yticks(y, [p[2] for p in pairs])
    lo = min(min(p[0], p[1]) for p in pairs)
    ax.set_xlim(np.floor(lo * 50) / 50 - 0.02, 1.0)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.18), ncol=2, frameon=False, fontsize=9)
    title(ax, "Same inputs, different classifier", "Accuracy with logistic regression vs a linear SVM "
          "(axis starts above zero; points, not bars)")
    fig.savefig(FIGURES_DIR / "fig6_svm_check.png")
    plt.close(fig)


def results_table(results):
    lines = ["| Condition | What the model sees | Accuracy | Mean ± SD, 5 splits | F1 (fake) | Chance |",
             "|---|---|---|---|---|---|"]
    for name, label, sees in CONDITIONS + TABLE_ONLY:
        r = results.get(name)
        if r:
            spread = (f"{r['accuracy_mean']:.1%} ± {r['accuracy_sd']:.1%}"
                      if "accuracy_mean" in r else "n/a (fixed test set)")
            lines.append(f"| {label} | {sees} | {r['accuracy']:.1%} | {spread} | {r['f1']:.3f} | "
                         f"{r['majority_baseline']:.1%} |")
    table = "\n".join(lines) + "\n"
    with open(RESULTS_DIR / "results_table.md", "w", encoding="utf-8") as f:
        f.write(table)
    print(table)


def main():
    FIGURES_DIR.mkdir(exist_ok=True)
    names = {name for name, _, _ in CONDITIONS + TABLE_ONLY} | {"e2_body_only"}
    results = {name: load(name) for name in names}
    missing = sorted(n for n, r in results.items() if r is None)
    if missing:
        print(f"missing results (run their scripts first): {', '.join(missing)}")

    fig1_accuracy(results)
    tokens = load("e1_baseline_tokens")
    if tokens:
        fig2_tokens(tokens)
    panels = [("E1  Full text", "e1_baseline"), ("E3  Source markers stripped", "e3_stripped"),
              ("E3b  + page furniture stripped", "e3b_furniture_stripped")]
    panels = [(heading, results[name]) for heading, name in panels if results.get(name)]
    fig3_confusion(panels)
    fig4_degradation(results)
    fig5_topic_matched(results)
    fig6_svm_check(results)
    results_table(results)
    print(f"figures written to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
