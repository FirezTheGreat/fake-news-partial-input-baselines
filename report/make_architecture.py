"""Draws the system-architecture diagram for the report: report/architecture.png."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "architecture.png"
BLUE, BLUE_FILL, ORANGE, ORANGE_FILL = "#2a78d6", "#e6f0fb", "#eb6834", "#fdece4"
INK, INK_2, GREY_FILL, EDGE = "#0b0b0b", "#52514e", "#f3f2ee", "#c3c2b7"


def box(ax, x, y, w, h, title, lines=(), fill=GREY_FILL, edge=EDGE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12",
                                facecolor=fill, edgecolor=edge, linewidth=1.2))
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=10.5,
            fontweight="semibold", color=INK)
    for i, line in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.62 - i * 0.33, line, ha="center", va="top", fontsize=8.6, color=INK_2)


def arrow(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13,
                                 color=INK_2, linewidth=1.2))


def main():
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
    fig, ax = plt.subplots(figsize=(11, 6.4))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9.4)
    ax.axis("off")

    # Column 1: data
    box(ax, 0.2, 6.1, 3.2, 2.1, "ISOT corpus", ["True.csv  (Reuters)", "Fake.csv  (flagged sites)",
                                                  "44,898 articles"])
    box(ax, 0.2, 1.45, 3.2, 2.1, "LIAR corpus", ["PolitiFact statements", "12,836, 6-way → binary",
                                                 "test only (E4)"])

    # Column 2: cleaning
    box(ax, 3.95, 6.1, 3.45, 2.1, "Cleaning", ["drop empty bodies (631)", "drop duplicate bodies (5,623)",
                                              "38,644 articles"])
    arrow(ax, (3.4, 7.15), (3.95, 7.15))

    # Column 3: input conditions
    conditions = [
        ("E1", "full text (title + body)"),
        ("E2a", "first sentence only"),
        ("E2b", "function words only (spaCy POS)"),
        ("E2c", "8 surface statistics, no text"),
        ("E3 / E3b", "source markers / page clutter stripped"),
        ("E4", "headlines only"),
    ]
    box(ax, 7.8, 0.6, 4.1, 8.4, "Input conditions", fill=ORANGE_FILL, edge=ORANGE)
    for i, (tag, desc) in enumerate(conditions):
        y = 7.75 - i * 1.18
        ax.text(8.05, y, tag, fontsize=9.5, fontweight="semibold", color=INK, va="center")
        ax.text(8.05, y - 0.38, desc, fontsize=8.6, color=INK_2, va="center")
    arrow(ax, (7.4, 7.15), (7.8, 7.15))
    arrow(ax, (3.4, 2.5), (7.8, 2.5))

    # Column 4: shared harness
    box(ax, 12.6, 5.25, 3.3, 3.75, "run_experiment()", ["stratified 80/20 split", "(same split for all)",
                                                       "TF-IDF + logistic", "regression", "(random forest for E2c)",
                                                       "5 random splits", "→ mean ± SD"],
        fill=BLUE_FILL, edge=BLUE)
    arrow(ax, (11.9, 7.1), (12.6, 7.1))

    # Column 4 bottom: outputs
    box(ax, 12.6, 1.6, 3.3, 2.0, "Outputs", ["metrics JSON per condition", "top coefficients (leak tokens)",
                                             "figures + results table"])
    arrow(ax, (14.25, 5.25), (14.25, 3.6))

    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
