"""Builds report/WSMA_Report.docx from results/*.json and figures/*.png.

WARNING: rebuilding OVERWRITES the .docx, including any edits made in Word.
Needs python-docx (pip install python-docx). Usage, from the project root:
    .venv/Scripts/python report/build_report.py .
then open the .docx in Word and press F9 (or right-click the contents > Update Field).
"""

import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor

ROOT = Path(sys.argv[1])
RESULTS, FIGURES, OUT = ROOT / "results", ROOT / "figures", ROOT / "report" / "WSMA_Report.docx"
FONT = "Times New Roman"


def load(name):
    with open(RESULTS / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


R = {n: load(n) for n in ["e1_baseline", "e2a_first_sentence", "e2b_function_words", "e2c_metadata",
                          "e2_body_only", "e3_stripped", "e3b_furniture_stripped", "e4_isot_titles",
                          "e4_liar_transfer", "e4_liar_no_halftrue", "e2d_sentiment", "e2e_entities",
                          "e3c_stripped_function_words", "e5a_topic_full", "e5b_topic_stripped",
                          "e5c_topic_function_words", "e5d_topic_metadata", "e1_svm", "e2a_svm", "e2b_svm",
                          "e3b_svm", "e4b_mcintire_control", "e4b_mcintire_full", "e4b_mcintire_stripped",
                          "e4b_mcintire_function_words", "e4b_reverse"]}
BEFORE_FIX = {n: json.load(open(RESULTS / "before_quote_fix" / f"{n}.json", encoding="utf-8"))
              for n in ["e3c_stripped_function_words", "e5c_topic_function_words"]}


def pct(x, d=1):
    return f"{100 * x:.{d}f}%"


def acc(n):
    return pct(R[n]["accuracy"])


CHANCE = pct(R["e1_baseline"]["majority_baseline"])
LIAR_CHANCE = pct(R["e4_liar_transfer"]["majority_baseline"])
TOPIC_CHANCE = pct(R["e5a_topic_full"]["majority_baseline"])

doc = Document()

# ---------- page and base styles ----------
sec = doc.sections[0]
sec.page_width, sec.page_height = Mm(210), Mm(297)
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Cm(2.54))


def set_font(style, size, bold=None, italic=None, color=None):
    style.font.name = FONT
    style.font.size = Pt(size)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    if color is not None:
        style.font.color.rgb = color


normal = doc.styles["Normal"]
set_font(normal, 12)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.15
for level, size in ((1, 16), (2, 13), (3, 12)):
    st = doc.styles[f"Heading {level}"]
    set_font(st, size, bold=True, italic=False, color=RGBColor(0, 0, 0))
    st.paragraph_format.space_before = Pt(18 if level == 1 else 12)
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.keep_with_next = True
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        st.element.rPr.rFonts.attrib.pop(qn(attr), None)
for name in ("List Bullet", "List Number"):
    set_font(doc.styles[name], 12)
cap = doc.styles.add_style("CaptionText", 1)
set_font(cap, 10, italic=True)
cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
cap.paragraph_format.space_after = Pt(12)


# ---------- helpers ----------
def runs(par, text):
    """Inline markup: **bold**, *italic*, [[placeholder]] (yellow highlight); \\* is a literal asterisk."""
    text = text.replace("\\*", "\x00")
    for part in re.split(r"(\*\*.+?\*\*|\*.+?\*|\[\[.+?\]\])", text):
        if not part:
            continue
        if part.startswith("**"):
            par.add_run(part[2:-2].replace("\x00", "*")).bold = True
        elif part.startswith("[["):
            r = par.add_run(f"[{part[2:-2]}]")
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        elif part.startswith("*"):
            par.add_run(part[1:-1].replace("\x00", "*")).italic = True
        else:
            par.add_run(part.replace("\x00", "*"))
    return par


def p(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, style=None):
    par = doc.add_paragraph(style=style)
    par.alignment = align
    return runs(par, text)


def bullet(text):
    return runs(doc.add_paragraph(style="List Bullet"), text)


def numbered(text):
    return runs(doc.add_paragraph(style="List Number"), text)


def h(text, level=1):
    return doc.add_heading(text, level)


def figure(path, caption, width=Cm(15.5)):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.keep_with_next = True
    par.add_run().add_picture(str(path), width=width)
    doc.add_paragraph(caption, style="CaptionText")


def shade(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def table(header, rows, widths, caption, bold_rows=()):
    doc.add_paragraph(caption, style="CaptionText").paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, text in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(text)
        r.bold = True
        r.font.size = Pt(10)
        shade(cell, "E6F0FB")
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(text)
            r.font.size = Pt(10)
            r.bold = ri in bold_rows
    # keep the table on one page: rows can't split, and every row stays with the next
    for ri, row in enumerate(t.rows):
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            for cp in row.cells[i].paragraphs:
                cp.paragraph_format.space_after = Pt(1)
                cp.paragraph_format.space_before = Pt(1)
                cp.paragraph_format.line_spacing = 1.0
            if ri < len(t.rows) - 1:
                for cp in row.cells[i].paragraphs:
                    cp.paragraph_format.keep_with_next = True
    doc.add_paragraph()
    return t


def field(par, instr):
    for kind, text in (("begin", None), (None, instr), ("separate", None), (None, ""), ("end", None)):
        r = par.add_run()
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r._r.append(fc)
        elif text:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = text
            r._r.append(it)


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# footer page numbers
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
field(fp, "PAGE")

# ---------- title page ----------
for _ in range(5):
    doc.add_paragraph()
t = p("Partial-Input Baselines Reveal Construction Artifacts in Fake News Benchmarks",
      align=WD_ALIGN_PARAGRAPH.CENTER)
for r in t.runs:
    r.bold, r.font.size = True, Pt(20)
p("An audit of the ISOT fake news dataset", align=WD_ALIGN_PARAGRAPH.CENTER).runs[0].font.size = Pt(14)
doc.add_paragraph()
p("Web and Social Media Analytics (WSMA) — Lab Project Report", align=WD_ALIGN_PARAGRAPH.CENTER)
p("[[Course code]]", align=WD_ALIGN_PARAGRAPH.CENTER)
for _ in range(3):
    doc.add_paragraph()
p("**Submitted by**", align=WD_ALIGN_PARAGRAPH.CENTER)
p("[[Your full name]]  —  [[Roll number]]", align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
p("**Submitted to**", align=WD_ALIGN_PARAGRAPH.CENTER)
p("[[Instructor's name and title]]", align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
p("[[Department]], [[Institution]]", align=WD_ALIGN_PARAGRAPH.CENTER)
p("[[Submission date]]", align=WD_ALIGN_PARAGRAPH.CENTER)
page_break()

# ---------- contents ----------
p("**Contents**", align=WD_ALIGN_PARAGRAPH.LEFT).runs[0].font.size = Pt(16)
field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
page_break()

# ---------- abstract ----------
h("Abstract", 1)
p(f"Fake news classifiers trained on the ISOT benchmark routinely report accuracies near 99%. This "
  f"project asks what that number measures. ISOT's real articles were collected from a single news agency "
  f"(Reuters) and its fake articles from a set of websites flagged as unreliable, so a classifier could "
  f"separate the two classes by recognising the publisher rather than by detecting deception. We test this "
  f"with partial-input baselines: models deliberately denied the information that genuine veracity "
  f"assessment would require. On a cleaned, deduplicated version of ISOT (38,644 articles), a TF-IDF and "
  f"logistic regression baseline reaches {acc('e1_baseline')} accuracy. A model shown only the first "
  f"sentence of each article reaches {acc('e2a_first_sentence')}; a model shown only function words and "
  f"punctuation reaches {acc('e2b_function_words')}; and a random forest given eight surface statistics and "
  f"no words at all reaches {acc('e2c_metadata')}, against a majority-class baseline of {CHANCE}. Removing "
  f"source markers from both classes lowers accuracy only to {acc('e3b_furniture_stripped')}, because the "
  f"remaining signal is the writing register of the two publishing pipelines. The signal is not topic: "
  f"restricted to US politics in both classes, with every marker stripped, function words alone still give "
  f"{acc('e5c_topic_function_words')} against a chance level of {TOPIC_CHANCE}, and a linear SVM reproduces "
  f"every result. Finally, a headline model "
  f"that scores {acc('e4_isot_titles')} within ISOT falls to {acc('e4_liar_transfer')} on the LIAR "
  f"fact-checking corpus, below that corpus's majority-class rate of {LIAR_CHANCE}, and the full-text "
  f"detector falls from {acc('e1_baseline')} to {acc('e4b_mcintire_full')} on a second corpus of full "
  f"articles whose real news does not come from Reuters. We conclude that high "
  f"accuracy on ISOT reflects source and genre separability rather than any ability to detect false content.")
p("**Keywords:** fake news, dataset artifacts, shortcut learning, partial-input baselines, ISOT, LIAR, TF-IDF")

# ---------- 1 introduction ----------
h("1. Introduction", 1)
p("Automatic fake news detection is a popular application of text classification, and the ISOT Fake News "
  "Dataset is one of its most widely used benchmarks. Models trained on it, from simple bag-of-words "
  "classifiers to fine-tuned transformers, routinely report accuracy above 98%. Taken at face value, such "
  "numbers suggest that distinguishing true from false news articles is close to a solved problem.")
p("There is reason to doubt that reading. ISOT was assembled from two different sources: its real articles "
  "come from Reuters, and its fake articles come from websites flagged by fact-checking organisations as "
  "unreliable. The two classes therefore differ not only in truthfulness but in everything else that "
  "distinguishes a wire agency from a partisan website: datelines, attribution conventions, formatting, "
  "typography, page layout and tone. A classifier optimised for accuracy has no reason to learn the hard "
  "task (judging whether claims are true) when an easy one (recognising which publisher wrote the text) "
  "gives the same labels.")
p("An analogy makes the problem concrete. Suppose a model is trained to detect a disease, but every "
  "diseased sample came from Hospital A and every healthy sample from Hospital B. The model can reach "
  "near-perfect accuracy by learning the hospital's scanner signature, and it will fail on samples from "
  "Hospital C. It has learned the hospital, not the disease.")
p("This project builds a standard fake news detector, obtains the familiar 98% accuracy, and then tests "
  "whether that accuracy is real. The detector is the object under test. The approach is to build "
  "deliberately handicapped versions of it, each denied the information that real veracity assessment "
  "would need, and to measure how well they still perform. If a model that cannot see an article's content "
  "still separates real from fake, the labels are recoverable from something other than content, and the "
  "detector's accuracy is not measuring deception detection.")
p("The contributions of this report are:")
bullet("a cleaned version of ISOT with empty and duplicate articles removed, and a measured, rather than "
       "assumed, chance level;")
bullet("five content-free partial-input probes (first sentence, function words, eight surface statistics, "
       "sentiment scores and named-entity counts) applied to the same fixed train/test split;")
bullet("artifact-removal experiments that strip source markers from Reuters only, and then from both classes;")
bullet("cross-corpus tests on LIAR (headlines) and on a second corpus of full articles, each with an "
       "in-domain control that separates the effect of crossing datasets from other differences;")
bullet("confound checks showing that the results are not explained by topic (a US-politics-only subset) or "
       "by the choice of classifier (a linear SVM);")
bullet("an inspection of model coefficients that identifies specific leakage tokens, including three "
       "artifacts of the data collection process (lost quotation marks and apostrophes, curly-quote "
       "typography and empty articles).")
p("Section 2 reviews related work. Section 3 states the problem and research questions, Section 4 "
  "describes the proposed system and Section 5 the methodology. Section 6 presents and discusses the "
  "results, and Sections 7 and 8 give conclusions and directions for future work.")

# ---------- 2 literature ----------
h("2. Literature Survey", 1)
h("2.1 Fake news detection and its benchmarks", 2)
p("Shu et al. (2017) survey fake news detection on social media from a data mining perspective. They "
  "separate content-based approaches, which use the text of an article, from context-based approaches, "
  "which use social signals such as who shares it, and they argue that fake news is written deliberately "
  "to mislead, so content alone is often insufficient. Ahmed, Traore and Saad (2017) introduced the ISOT "
  "dataset used here, pairing Reuters articles with articles from sites flagged by PolitiFact and "
  "Wikipedia, and reported high accuracy with n-gram features and linear classifiers. Wang (2017) "
  "introduced LIAR, about 12,800 short political statements labelled on a six-point truthfulness scale by "
  "PolitiFact editors. Because LIAR labels individual claims by fact-checking rather than by publisher, "
  "it provides a useful external test of whether a model trained on ISOT has learned anything about "
  "truthfulness. McIntire's (2017) fake-or-real news corpus pairs fake articles from flagged websites with "
  "real articles from a range of mainstream outlets, which makes it a natural full-article counterpart.")
h("2.2 Dataset artifacts and partial-input baselines", 2)
p("Gururangan et al. (2018) showed that natural language inference (NLI) datasets contain annotation "
  "artifacts: a classifier that sees only the hypothesis, never the premise it should be compared against, "
  "reaches about 67% accuracy on SNLI and 53% on MultiNLI, well above chance for three classes. This "
  "partial-input method is the core technique of the present project. Poliak et al. (2018) generalised it "
  "to ten NLI datasets and found hypothesis-only baselines beating the majority class on many of them. "
  "McCoy, Pavlick and Linzen (2019) built the HANS evaluation set and showed that strong NLI models rely on "
  "shallow syntactic heuristics such as lexical overlap. Niven and Kao (2019) showed that BERT's high score "
  "on an argument reasoning task came from spurious statistical cues; on an adversarial version that "
  "removed them, performance fell to chance. Schuster et al. (2019) applied the same reasoning to fact "
  "verification, showing that claim-only models perform well on the FEVER dataset without consulting any "
  "evidence.")
h("2.3 Shortcut learning", 2)
p("Geirhos et al. (2020) unify these findings under the term shortcut learning: decision rules that "
  "perform well on standard benchmarks but fail under realistic conditions, because they exploit "
  "correlations in the data rather than the intended task. They recommend testing models out of "
  "distribution and treating benchmark accuracy with suspicion when an easier route to the labels exists.")
h("2.4 Artifacts in fake news datasets", 2)
p("Zhou et al. (2021) examined large unreliable-news datasets and found that when the same websites "
  "appear in both training and test data, models can perform well simply by memorising the mapping from "
  "site to label; with site-disjoint splits, accuracy fell by more than ten points. They recommend using "
  "simple models as bias probes during dataset construction. Most directly, Verma (2026) audits the same "
  "ISOT/Kaggle corpus used here. That preprint reports that a classifier given only the subject field "
  "reaches an F1 of 1.000, that removing the newswire tag, metadata and duplicates lowers F1 only from "
  "0.994 to 0.981, and that transfer to LIAR does not beat the majority class.")
h("2.5 Remedies", 2)
p("Two remedies have been proposed for artifact-laden datasets. Kaushik, Hovy and Lipton (2020) collect "
  "counterfactually augmented data, in which annotators minimally edit examples so that the label flips, "
  "and show that models trained on it rely less on spurious features. Gardner et al. (2020) propose "
  "contrast sets: small, label-changing perturbations of test examples that probe a model's local decision "
  "boundary. Neither is applied in this project; both are discussed as future work.")
table(["Work", "Setting", "Key finding", "Relevance here"], [
    ["Gururangan et al. (2018)", "NLI", "Hypothesis-only model: ~67% on SNLI", "Source of the partial-input method"],
    ["Poliak et al. (2018)", "10 NLI datasets", "Hypothesis-only beats majority on many", "Method generalises across datasets"],
    ["McCoy et al. (2019)", "NLI (HANS)", "Models use syntactic heuristics", "High accuracy can hide shallow rules"],
    ["Niven & Kao (2019)", "Argument reasoning", "BERT exploits spurious cues; chance when removed", "Removing cues reveals true ability"],
    ["Schuster et al. (2019)", "Fact verification", "Claim-only models do well on FEVER", "Partial input applied to veracity"],
    ["Geirhos et al. (2020)", "General ML", "Defines shortcut learning", "Conceptual framing"],
    ["Zhou et al. (2021)", "Unreliable news", "Site memorisation; >10-point drop on clean split", "Source leakage in fake-news data"],
    ["Verma (2026)", "ISOT", "Subject field alone: F1 = 1.000", "Same corpus; our results replicate it"],
], [3.6, 2.8, 4.8, 4.6], "Table 1. Summary of the most closely related work.")

# ---------- 3 problem statement ----------
h("3. Problem Statement", 1)
p("ISOT is widely used to train and compare fake news classifiers, and published results on it cluster "
  "around 98–99% accuracy. Because its two classes were collected from different publishers, that accuracy "
  "may reflect the ability to recognise the publisher rather than the ability to detect false content. "
  "Prior work has established that fake news datasets leak source identity (Zhou et al., 2021) and, for "
  "ISOT specifically, that metadata fields and newswire tags give the labels away (Verma, 2026).")
p("**Research gap.** Existing audits of ISOT remove or isolate specific *fields* or *tags*. They do not "
  "test whether the class signal survives when the model is denied content altogether and given only the "
  "style of the writing, nor whether stripping the markers of *both* publishing pipelines closes the gap. "
  "If a model given nothing but grammatical words and punctuation can still separate the classes, then no "
  "amount of tag removal will make ISOT a test of veracity.")
p("The project addresses three research questions:")
numbered("**RQ1.** How much of ISOT's classification accuracy remains when a model is denied the article's "
         "content and given only its opening line, its function words, or a handful of surface statistics?")
numbered("**RQ2.** How much accuracy is lost when source markers are removed from Reuters articles only, and "
         "from both classes?")
numbered("**RQ3.** Does a model trained on ISOT transfer to an independently labelled fact-checking corpus?")
numbered("**RQ4.** Is the remaining signal writing style, or is it explained by topic or by the choice of "
         "classifier?")

# ---------- 4 proposed ----------
h("4. Proposed System", 1)
h("4.1 Objectives", 2)
bullet("**O1.** Reproduce the headline ISOT accuracy with a standard, interpretable baseline on a cleaned, "
       "deduplicated version of the dataset.")
bullet("**O2.** Measure the accuracy of content-free partial-input probes against a measured chance level.")
bullet("**O3.** Measure the effect of removing source markers, first from one class and then from both.")
bullet("**O4.** Test cross-corpus transfer to LIAR, with an in-domain control.")
bullet("**O5.** Identify the specific tokens and patterns the models rely on.")
bullet("**O6.** Rule out topic and classifier choice as explanations for the results.")
bullet("**O7.** Draw recommendations for how fake news classifiers should be evaluated.")
h("4.2 System architecture", 2)
p("Figure 1 shows the pipeline. Both ISOT files are loaded and cleaned once. Each experimental condition "
  "then transforms the cleaned articles into a different input — full text, a fragment of the text, a "
  "stylistic reduction of the text, or a vector of numbers — and passes it to one shared evaluation "
  "function. That function applies the same stratified train/test split, the same classifier and the same "
  "metrics to every condition, so differences in accuracy can be attributed to the input alone. LIAR "
  "and the McIntire corpus are used as external test sets. All metrics are written to disk, and the figures and tables in this "
  "report are generated from those files.")
figure(ROOT / "report" / "architecture.png", "Figure 1. System architecture.", width=Cm(16))

# ---------- 5 methodology ----------
h("5. Methodology", 1)
h("5.1 Data and cleaning", 2)
p("The ISOT dataset contains 44,898 articles: 21,417 labelled real and 23,481 labelled fake, each with a "
  "title, body text, subject and date. Real articles were labelled 0 and fake articles 1. Two cleaning "
  "steps were applied before any experiment. First, 631 articles with an empty body were removed; 630 of "
  "them were fake, so an empty body would itself have revealed the label. Second, 5,623 articles whose body "
  "duplicated another article's body were removed, keeping the first copy. All duplicates fell within a "
  "single class. Duplicates matter because a copy in the training set and another in the test set would "
  "let the model be tested on an article it had already seen. The cleaned dataset has **38,644 articles: "
  "21,191 real and 17,453 fake**. The subject field was never used as model input, because its values do "
  "not overlap between the classes and would give away the label directly. It was used only to select rows "
  "for the topic-matched check (E5).")
p("The McIntire corpus contains 6,335 full news articles labelled real or fake. Its fake articles come "
  "from websites flagged as unreliable, and its real articles from mainstream outlets such as the New York "
  "Times and NPR; the Reuters dateline appears in only 0.3% of its real articles. It shares no article "
  "body with ISOT. It was cleaned in the same way as ISOT (36 empty and 240 duplicate bodies removed), "
  "leaving **6,059 articles: 2,989 real and 3,070 fake**.")
p("LIAR contains 12,836 statements (10,269 train, 1,284 validation, 1,283 test). Its six labels were "
  "collapsed to two: *true*, *mostly-true* and *half-true* were treated as real, and *barely-true*, "
  "*false* and *pants-fire* as fake. Placing *half-true* on the real side is a judgement call and is "
  "tested by repeating the transfer without the *half-true* statements.")
h("5.2 Shared evaluation protocol", 2)
p("Every condition is evaluated by the same function. The data is split 80/20 into training and test "
  "sets, stratified by label so that both sets keep the overall class proportions (54.8% real). The "
  "random seed is fixed, and every condition loads the articles in the same order, so all conditions are "
  "tested on exactly the same 7,729 articles. Text inputs are converted to TF-IDF vectors (unigrams, "
  "default settings) and classified with L2-regularised logistic regression. The vectoriser is fitted on "
  "the training set only, so no information from the test set influences the features. No "
  "hyperparameters were tuned: the aim is to measure the dataset, not to maximise accuracy.")
p("Logistic regression was chosen deliberately. Each word receives one weight, and the sign of the weight "
  "shows which class the word pushes towards, so the features a model relies on can be read directly. A "
  "linear model also strengthens the conclusions: if a simple model can separate the classes from "
  "stylistic input alone, the signal must be shallow and easy to find. To check that no result depends on "
  "this choice, the main text conditions were repeated with a linear support vector machine (SVM).")
p("Reported metrics are accuracy, and precision, recall and F1 for the fake class, together with the "
  "confusion matrix. Chance is defined as the accuracy of always predicting the larger class in the test "
  "set, which is 54.8% for ISOT and 55.8% for LIAR. To check that results do not depend on a particular "
  "split, every split-based condition was repeated on five different random stratified splits, and the "
  "mean and standard deviation of accuracy are reported alongside the fixed-split result.")
h("5.3 Experimental conditions", 2)
p("**E1 — Full text.** The title and body are concatenated and used in full. This is the baseline being "
  "audited.")
p("**E2a — First sentence only.** Only the text of the body up to the first full stop or line break is "
  "used. In wire copy this span contains the dateline and agency attribution.")
p("**E2b — Function words only.** Every article is part-of-speech tagged with spaCy (en_core_web_sm), "
  "and only tokens tagged as determiners, pronouns, adpositions, auxiliaries, coordinating and "
  "subordinating conjunctions, particles and punctuation are kept. The result contains no nouns, verbs, "
  "adjectives, names or numbers — for example \"the of a and to , the -\". Because these strings consist "
  "of single-character tokens, the TF-IDF tokeniser was set to split on whitespace so that tokens such as "
  "\"a\" and \",\" are kept.")
p("**E2c — Metadata only.** Each article is reduced to eight numbers: character count, word count, "
  "sentence count, exclamation marks, question marks, the proportion of words in capitals, average word "
  "length and the proportion of digits. These are standardised and classified with a random forest of "
  "100 trees. No words reach the model.")
p("**E2d — Sentiment only.** Each article, after the stripping described under E3b below, is reduced to eight VADER sentiment scores (negative, "
  "neutral, positive and compound, for the title and the body separately), classified with a random "
  "forest.")
p("**E2e — Named entities only.** spaCy's named-entity recogniser is run on each article after E3b stripping and the "
  "count of each entity type (people, places, organisations, dates and so on) per 100 words is kept, "
  "classified with a random forest. No entity names reach the model, only how many of each type occur.")
p("**E3 — Source markers stripped.** From every article, real and fake alike: the dateline (for example "
  "\"WASHINGTON (Reuters) -\"), the first sentence of the body, and every occurrence of the word "
  "\"Reuters\" are removed. The full remaining text is then used as in E1.")
p("**E3b — Page clutter stripped from both classes.** In addition to E3, text that is not article prose is "
  "removed from both classes: image and media credits (for example \"Featured image via … Getty Images\" "
  "or \"Video via YouTube\"), URLs, Twitter handles and media tags such as \"[Video]\" and \"WATCH:\". "
  "Every apostrophe and quotation mark, curly or straight, is replaced by a space, and ellipsis characters "
  "and dashes are converted to plain forms. This last rule exists because the fake articles lost these "
  "characters during scraping: \"Trump's\" appears as \"Trump s\" and \"couldn't\" as \"couldn t\" (a word "
  "followed by a lone *s* or *t* occurs in 91.6% of fake articles against 38.8% of real ones), so removing "
  "them from both classes makes the two equal. The removal rules were written after one inspection of the "
  "data and changed only once afterwards: the straight-quote case was added when the coefficients of E5c "
  "exposed it. Results from before that change are reported in Section 6.6 so that its effect is visible.")
p("**E3c — Stripped, function words only.** The E3b text is reduced to function words as in E2b. This "
  "probe has neither content words nor any of the markers removed in E3 and E3b.")
p("**E4 — Cross-corpus transfer.** Because LIAR has no article bodies, this experiment uses headlines. A "
  "model is trained on all ISOT titles and tested on all 12,836 LIAR statements. As an in-domain control, "
  "the same headline-only model is also evaluated on the standard ISOT split. The control shows how much "
  "accuracy headlines support within ISOT, so that any drop on LIAR can be attributed to crossing datasets.")
p("**E4b — Cross-corpus transfer, full articles.** The full-text detector is trained on all of ISOT and "
  "tested on all of McIntire, using full text, fully stripped text (E3 and E3b rules on both corpora) and "
  "stripped function words. As a control, McIntire is also evaluated on its own 80/20 split, and the "
  "transfer is repeated in the reverse direction (trained on McIntire, tested on ISOT).")
p("**E5 — Topic-matched check.** Real ISOT articles are 53% US politics and 47% world news, while the fake "
  "articles are all US politics and US news, so topic alone could separate part of the data. E5 keeps only "
  "the real US-politics articles and all fake articles (28,666 in total), and repeats the strictest "
  "conditions: full text (E5a), fully stripped text (E5b), stripped function words (E5c) and stripped "
  "metadata (E5d). On this subset fake articles are the majority, so chance rises to 60.9%.")
p("A body-only condition (E1 without the title) was also run to complete the degradation curve in Section 6.")
h("5.4 Leakage-token analysis", 2)
p("For every logistic regression model, the 30 words with the largest positive weights (pushing towards "
  "fake) and the 30 with the largest negative weights (pushing towards real) were recorded. A strict, "
  "hand-labelled list of provenance tokens — the agency name, the dateline city, timestamp formats, image "
  "credits, URL and embed fragments, and media tags — was used to mark which of the strongest features "
  "identify the publisher rather than the content.")
h("5.5 Implementation", 2)
p("The system is implemented in Python 3.10 with pandas 2.3, scikit-learn 1.7, spaCy 3.8, NLTK 3.10 "
  "(VADER) and matplotlib 3.10. Part-of-speech and entity tagging of the corpora take about 1.5 hours and "
  "are cached to disk. The repeated splits of each experiment are fitted in parallel, and independent "
  "experiments run concurrently. The datasets and cached tagging output are distributed with the code, so "
  "all experiments, figures and tables are reproduced by a single command in about five minutes, and a "
  "checksum test confirms that the data is identical to the copy used here.")

# ---------- 6 results ----------
h("6. Results and Discussion", 1)
h("6.1 Overview", 2)
rows = []
names = [("e1_baseline", "E1  Full text"), ("e2a_first_sentence", "E2a  First sentence only"),
         ("e2b_function_words", "E2b  Function words only"), ("e2c_metadata", "E2c  Metadata only"),
         ("e2d_sentiment", "E2d  Sentiment only"), ("e2e_entities", "E2e  Named entities only"),
         ("e3_stripped", "E3  Source markers stripped"), ("e3b_furniture_stripped", "E3b  Page clutter stripped"),
         ("e3c_stripped_function_words", "E3c  Stripped, function words"),
         ("e4_isot_titles", "E4 control  ISOT headlines"), ("e4_liar_transfer", "E4  ISOT → LIAR"),
         ("e4_liar_no_halftrue", "E4  ISOT → LIAR, no half-true"),
         ("e4b_mcintire_control", "E4b control  McIntire in-domain"),
         ("e4b_mcintire_full", "E4b  ISOT → McIntire, full text"),
         ("e4b_mcintire_stripped", "E4b  ISOT → McIntire, stripped"),
         ("e4b_mcintire_function_words", "E4b  ISOT → McIntire, function words"),
         ("e4b_reverse", "E4b  McIntire → ISOT"),
         ("e5a_topic_full", "E5a  US politics: full text"), ("e5b_topic_stripped", "E5b  US politics: stripped"),
         ("e5c_topic_function_words", "E5c  US politics: stripped function words"),
         ("e5d_topic_metadata", "E5d  US politics: stripped metadata")]
for n, label in names:
    r = R[n]
    spread = f"{pct(r['accuracy_mean'])} ± {pct(r['accuracy_sd'])}" if "accuracy_mean" in r else "—"
    rows.append([label, pct(r["accuracy"]), spread, f"{r['f1']:.3f}", pct(r["majority_baseline"])])
table(["Condition", "Accuracy", "Mean ± SD (5 splits)", "F1 (fake)", "Chance"], rows,
      [6.4, 2.1, 3.5, 2.0, 1.8], "Table 2. Accuracy of every condition (logistic regression, or random forest "
                                 "for numeric features). Chance is the majority-class rate of each test set.")
p(f"Table 2 and Figure 2 summarise the results. Every condition trained and tested on ISOT is far above "
  f"chance, including those that never see an article's content. Results are stable across random "
  f"splits: no standard deviation exceeds "
  f"{pct(max(R[n]['accuracy_sd'] for n, _ in names if 'accuracy_sd' in R[n]))}, so differences of a few "
  f"points between conditions are not split noise. The only conditions near or below chance are the "
  f"cross-corpus tests.")
figure(FIGURES / "fig1_accuracy.png", "Figure 2. Accuracy by condition. The dashed line marks the majority-class "
                                      "rate on the ISOT test split.")

h("6.2 Partial-input probes (RQ1)", 2)
e2a_tok = load("e2a_first_sentence_tokens")
p(f"**First sentence.** The opening line alone gives {acc('e2a_first_sentence')} accuracy, slightly *higher* "
  f"than the full article ({acc('e1_baseline')}). The strongest feature is the word \"reuters\" (weight "
  f"{e2a_tok['real'][0][1]:.1f}), more than four times the weight of any other. The next real-class features "
  f"are dateline fragments: \"washington\", \"fla\", \"calif\", \"pa\", \"london\", \"york\" and the names of "
  f"weekdays. The dateline appears in {'99.2%'} of real articles and in fewer than 0.1% of fake ones. On "
  f"the fake side, the opening line is identified by words such as \"just\", \"we\", \"our\" and \"you\", "
  f"which reflect a conversational, opinionated register.")
p(f"**Function words.** A model that sees only grammatical words and punctuation — no nouns, verbs, names "
  f"or numbers — reaches {acc('e2b_function_words')}. Its strongest features are typographic. The colon "
  f"and the words \"via\", \"this\", \"like\" and \"you\" push towards fake, as do the question mark, the "
  f"exclamation mark and the single-character ellipsis \"…\". Curly quotation marks, the possessive "
  f"\"’s\", parentheses, hyphens and the three-dot ellipsis \"...\" push towards real. Inspection of the "
  f"corpus explains the quotation marks: **50.8% of real articles contain curly quotation marks and no "
  f"fake article does.** The fake articles' quotation marks and apostrophes were lost during scraping (one "
  f"fake article reads \"couldn t\"), so typography alone identifies about half of the real class.")
p(f"**Metadata.** Eight numbers per article give {acc('e2c_metadata')} accuracy. The most important "
  f"features are the number of question marks (importance 0.19), average word length (0.18), the "
  f"proportion of capitalised words (0.13) and the number of exclamation marks (0.12). Fake articles "
  f"contain on average 1.23 question marks and 0.74 exclamation marks, against 0.10 and 0.06 for real "
  f"articles. These are properties of a writing style, not of truthfulness.")
p(f"**Sentiment and named entities.** Run on the stripped text, eight sentiment scores give "
  f"{acc('e2d_sentiment')} and entity-type counts give {acc('e2e_entities')}. Fake articles are more negative: "
  f"the average compound score of their titles is −0.17 against −0.07 for real titles, and of their "
  f"bodies −0.08 against +0.06. Real articles mention almost three times as many places per 100 words "
  f"(2.97 against 1.06) and more dates (1.85 against 1.08), which matches wire copy's habit of locating and "
  f"dating every event; fake articles mention more people (3.08 against 2.46). Neither probe sees a single "
  f"word of the article, yet both are far above chance.")
p("The answer to RQ1 is that very little of ISOT's accuracy depends on content: the class can be "
  "recovered from the first line, from the grammatical skeleton of the text, from punctuation counts, from "
  "tone, or from how often places and dates are mentioned.")

h("6.3 What the full-text model learns", 2)
p("Figure 3 shows the 15 strongest features of the E1 model for each class. The single strongest real "
  "feature is \"reuters\", followed closely by \"said\", the attribution verb of wire reporting. Other real "
  "features are a dateline city, weekday names and \"told\". On the fake side, seven of the 15 strongest "
  "features are page clutter rather than prose: \"via\", \"video\", \"image\", \"featured\", \"read\", "
  "\"watch\" and \"com\" come from image credits, embedded media and links. The phrase \"Featured image via\" alone appears in 46.8% of fake articles and in no real article.")
figure(FIGURES / "fig2_leakage_tokens.png", "Figure 3. Strongest logistic regression features per class (E1). "
                                            "Orange marks source and page-clutter markers.")
PROVENANCE = {"reuters", "washington", "edt", "via", "image", "images", "getty", "featured", "pic", "https",
              "com", "www", "twitter", "video", "watch", "read", "breaking", "wire"}
e1_tok = load("e1_baseline_tokens")
token_rows = []
for cls, label in (("real", "Real"), ("fake", "Fake")):
    for rank, (word, coef) in enumerate(e1_tok[cls][:10], start=1):
        token_rows.append([str(rank), word, f"{coef:+.2f}", label, "Yes" if word in PROVENANCE else ""])
p("Table 3 lists the ten strongest features for each class with their coefficients. A token is marked as an "
  "artifact when it identifies the publishing pipeline (agency name, dateline, timestamp format, image "
  "credit, link fragment or media tag) rather than anything said in the article.")
table(["Rank", "Token", "Coefficient", "Class", "Artifact?"], token_rows, [1.5, 3.5, 3.0, 2.0, 2.5],
      "Table 3. Ten strongest E1 features per class. Negative coefficients push towards real, positive towards fake.")

h("6.4 Artifact removal (RQ2)", 2)
p(f"Removing the Reuters dateline, the first sentence and every mention of Reuters lowers accuracy from "
  f"{acc('e1_baseline')} to {acc('e3_stripped')}. Additionally removing the fake sites' page clutter and "
  f"normalising typography lowers it only to {acc('e3b_furniture_stripped')}. Figure 4 shows that the "
  f"errors grow, from {sum(R['e1_baseline']['confusion_matrix'][0][1:]) + R['e1_baseline']['confusion_matrix'][1][0]} "
  f"to {R['e3b_furniture_stripped']['confusion_matrix'][0][1] + R['e3b_furniture_stripped']['confusion_matrix'][1][0]} "
  f"of 7,729, but remain rare in both classes.")
p("The features that survive explain why. After stripping, the strongest real features are \"said\", "
  "\"told\", \"says\", \"reporters\" and \"spokesman\": the attribution conventions of wire "
  "journalism, in which every claim is assigned to a named source. The strongest fake features are "
  "\"this\", \"just\", \"that\", \"you\", \"here\" and \"even\", together with partisan terms such "
  "as \"hillary\" and \"gop\": the direct, opinionated voice of political blogs. \"via\" remains the "
  "strongest fake feature, now in prose such as \"watch below, via Raw Story\": the blogs' habit of "
  "crediting other outlets. The source signal is not "
  "concentrated in a few removable markers. It runs through the register of the entire article. The answer "
  "to RQ2 is that marker removal barely matters, because ISOT's two classes are two different genres of "
  "writing.")
p(f"E3c makes the same point without any content words. Reduced to function words after all stripping, "
  f"the text still gives {acc('e3c_stripped_function_words')}. The strongest fake features are \"!\", "
  f"\":\", \"?\", \"like\", \"this\", \"why\" and \"you\" — exclamation, rhetorical questions and direct "
  f"address. The strongest real features are \"on\", \"--\", \"had\", \"would\", \"could\", \"whether\" "
  f"and \"amid\" — the hedged, conditional phrasing of wire reporting.")
figure(FIGURES / "fig3_confusion.png", "Figure 4. Confusion matrices on the same test split for E1, E3 and E3b.",
       width=Cm(16.5))

h("6.5 Cross-corpus transfer (RQ3)", 2)
liar = R["e4_liar_transfer"]["confusion_matrix"]
pred_fake = liar[0][1] + liar[1][1]
total = sum(map(sum, liar))
p(f"Within ISOT, a model trained on headlines alone reaches {acc('e4_isot_titles')}, so headlines carry "
  f"plenty of class signal. The same model applied to LIAR reaches {acc('e4_liar_transfer')}, below the "
  f"majority-class rate of {LIAR_CHANCE}. It labels {pct(pred_fake / total, 0)} of LIAR statements as fake, "
  f"although only {pct((liar[1][0] + liar[1][1]) / total, 0)} are. This is the behaviour expected of a model "
  f"that has learned \"not written like Reuters means fake\": LIAR's statements, short claims quoted from "
  f"politicians, are not written like wire copy, so most are labelled fake regardless of whether they are "
  f"true. Removing the *half-true* statements, the one ambiguous label, gives {acc('e4_liar_no_halftrue')} "
  f"against a chance level of {pct(R['e4_liar_no_halftrue']['majority_baseline'])}, so the result does not "
  f"depend on the label mapping.")
mc = R["e4b_mcintire_full"]["confusion_matrix"]
p(f"**Full articles.** Because LIAR contains only short statements, the test was repeated on the McIntire "
  f"corpus of full articles. McIntire itself is learnable: trained and tested on its own split, the same "
  f"pipeline reaches {acc('e4b_mcintire_control')}. The ISOT detector, however, reaches only "
  f"{acc('e4b_mcintire_full')} on it against a chance level of "
  f"{pct(R['e4b_mcintire_full']['majority_baseline'])}. It labels {pct(mc[0][1] / sum(mc[0]), 0)} of "
  f"McIntire's real articles — mainstream journalism that is not written in Reuters house style — as fake. "
  f"Stripping both corpora does not help ({acc('e4b_mcintire_stripped')}), and stripped function words give "
  f"{acc('e4b_mcintire_function_words')}. The reverse direction fails in the same way: trained on McIntire, "
  f"the model reaches {acc('e4b_reverse')} on ISOT against a chance level of "
  f"{pct(R['e4b_reverse']['majority_baseline'])}. Some signal does transfer, about ten points above chance, "
  f"but almost all of the within-corpus accuracy is lost (Figure 5).")
figure(FIGURES / "fig7_cross_corpus.png", "Figure 5. Accuracy within each dataset and on the other dataset. "
                                          "Dashed ticks mark chance on the dataset tested.", width=Cm(15))
p("The answer to RQ3 is that what the detector learns on ISOT does not transfer, neither to independently "
  "fact-checked claims nor to full articles from other publishers.")

h("6.6 Is it style, topic or the classifier? (RQ4)", 2)
p(f"**Topic.** Figure 6 repeats the strictest conditions on US politics only. Full text gives "
  f"{acc('e5a_topic_full')}, fully stripped text {acc('e5b_topic_stripped')}, stripped function words "
  f"{acc('e5c_topic_function_words')} and eight stripped surface statistics {acc('e5d_topic_metadata')}, "
  f"against a chance level of {TOPIC_CHANCE}. Removing the world-news articles changes almost nothing, so "
  f"topic does not explain the results.")
figure(FIGURES / "fig5_topic_matched.png", "Figure 6. The strictest probes on the US-politics-only subset. The "
                                           "dashed line is the majority-class rate on this subset.")
p(f"**A scraping artifact found on the way.** Before the straight-quote rule was added to E3b, E5c reached "
  f"{pct(BEFORE_FIX['e5c_topic_function_words']['accuracy'])}, and its strongest fake feature was a bare "
  f"\"s\" — the remains of apostrophes lost in the fake scrape. Removing apostrophes and quotation marks "
  f"from both classes lowered E5c to {acc('e5c_topic_function_words')} and E3c from "
  f"{pct(BEFORE_FIX['e3c_stripped_function_words']['accuracy'])} to {acc('e3c_stripped_function_words')}. "
  f"About eight points of the style probes' accuracy were therefore an encoding artifact; the remaining "
  f"accuracy is carried by genuine stylistic features.")
p(f"**Classifier.** Figure 7 repeats four conditions with a linear SVM. The SVM is slightly *more* accurate "
  f"in every case: {acc('e1_svm')} on full text, {acc('e2a_svm')} on the first sentence, {acc('e2b_svm')} on "
  f"function words and {acc('e3b_svm')} on stripped text. A stronger classifier exploits the same signal "
  f"more effectively; it does not make the problem go away.")
figure(FIGURES / "fig6_svm_check.png", "Figure 7. Accuracy with logistic regression and a linear SVM on the same "
                                       "inputs.", width=Cm(14))
p("The answer to RQ4 is that the signal is writing style. It survives the removal of topic differences, "
  "all identified markers and all content words, and it does not depend on the classifier.")

h("6.7 Accuracy as information is removed", 2)
p("Figure 8 orders the conditions by how much information they leave the model. Removing the title "
  "changes nothing, and removing every content word costs under two points. Only when the text is reduced "
  "to eight numbers does accuracy fall substantially, and even then it remains more than 30 points above "
  "chance.")
figure(FIGURES / "fig4_degradation.png", "Figure 8. Accuracy as content is removed.", width=Cm(14))

h("6.8 Threats to validity", 2)
p("Four threats were tested directly and ruled out: topic (E5), the choice of classifier (SVM check), the "
  "LIAR label mapping (transfer without *half-true*) and the headline-only nature of LIAR (full-article "
  "transfer to McIntire, E4b). The following remain.")
bullet("**Corpus scope.** The probes were applied in depth to ISOT only; McIntire was used for transfer. "
       "McIntire's labels, like ISOT's, are assigned by source rather than by fact-checking each article, "
       "so it shows that the detector does not generalise across sources, not what it would score on "
       "individually verified articles.")
bullet("**Classical models only.** Transformer models were not tested. The SVM result suggests that stronger "
       "models exploit the same signal at least as effectively, but this was not measured for transformers.")
bullet("**Hand-written removal rules.** E3b's rules cover the clutter found on inspection and were extended "
       "once (Section 6.6). Some site-specific markers, such as sign-offs naming the publishing website, "
       "may remain. The style probes reduce, but cannot eliminate, the chance that an unfound artifact "
       "contributes to their accuracy.")

# ---------- 7 conclusion ----------
h("7. Conclusion", 1)
p(f"This project built a standard fake news detector on the ISOT benchmark and tested it with "
  f"partial-input baselines. The detector reaches {acc('e1_baseline')} accuracy, but so do models that are denied the information "
  f"needed to judge truthfulness: {acc('e2a_first_sentence')} from the first sentence, "
  f"{acc('e2b_function_words')} from function words and punctuation, and {acc('e2c_metadata')} from eight "
  f"surface statistics, against a chance level of {CHANCE}. Removing source markers from both classes "
  f"leaves {acc('e3b_furniture_stripped')}; restricting both classes to US politics and keeping only "
  f"function words still leaves {acc('e5c_topic_function_words')} against a chance level of "
  f"{TOPIC_CHANCE}; a model that scores {acc('e4_isot_titles')} on ISOT headlines scores below chance "
  f"on LIAR; and the full-text detector falls to {acc('e4b_mcintire_full')} on a second corpus of full "
  f"articles, labelling most genuine mainstream news as fake.")
p("In short: we built a fake news detector, obtained 98% accuracy, and showed that the 98% does not "
  "measure fake news detection. The evidence points to one explanation. ISOT's labels coincide with two "
  "publishing pipelines, and "
  "models learn to recognise the pipeline. Because the difference is one of genre — wire reporting versus "
  "partisan commentary — it cannot be removed by deleting tags. Accuracy on ISOT should therefore be read "
  "as a measure of source and style separability, not of fake news detection. These findings agree with "
  "the source-memorisation results of Zhou et al. (2021) and with Verma's (2026) audit of the same corpus, "
  "and extend them by showing that the signal survives even when the model sees no content words at all. "
  "In the terms of Geirhos et al. (2020), ISOT rewards a shortcut, and published accuracies on it measure "
  "how well models take it.")
p("Three recommendations for evaluation practice follow. First, any accuracy reported on a fake news "
  "benchmark should be accompanied by partial-input baselines; a result is only meaningful to the extent "
  "that it exceeds what a content-free model achieves. Second, models should be tested on at least one "
  "independently constructed corpus, because within-corpus accuracy cannot distinguish learning veracity "
  "from learning the corpus. Third, the chance level should be measured on the actual test set rather than "
  "assumed, and the subject field and similar metadata should be checked for label leakage before use.")

# ---------- 8 future work ----------
h("8. Future Work", 1)
bullet("**Source-disjoint evaluation.** Build test sets from publishers never seen in training, so that "
       "recognising the publisher cannot help.")
bullet("**Matched sources.** Construct a benchmark in which true and false articles come from the same "
       "outlets, so that labels cannot be predicted from style.")
bullet("**Contrast sets and counterfactual data.** Minimally edit articles so that their veracity changes "
       "while their style does not, following Gardner et al. (2020) and Kaushik et al. (2020).")
bullet("**Neural models.** Repeat the probes with fine-tuned transformers to test whether larger models rely "
       "on the same artifacts.")
bullet("**Other corpora.** Apply the same probes to other fake news datasets, such as FakeNewsNet and "
       "BuzzFeed-Webis, to establish whether these construction artifacts are specific to ISOT or common "
       "across the field.")

# ---------- references ----------
h("References", 1)
refs = [
    "Ahmed, H., Traore, I., & Saad, S. (2017). Detection of online fake news using n-gram analysis and machine "
    "learning techniques. In *Intelligent, Secure, and Dependable Systems in Distributed and Cloud Environments "
    "(ISDDC 2017)*, LNCS 10618, pp. 127–138. Springer, Cham.",
    "Gardner, M., et al. (2020). Evaluating models' local decision boundaries via contrast sets. In *Findings of "
    "the Association for Computational Linguistics: EMNLP 2020*, pp. 1307–1323. "
    "https://doi.org/10.18653/v1/2020.findings-emnlp.117",
    "Geirhos, R., Jacobsen, J.-H., Michaelis, C., Zemel, R., Brendel, W., Bethge, M., & Wichmann, F. A. (2020). "
    "Shortcut learning in deep neural networks. *Nature Machine Intelligence, 2*(11), 665–673. "
    "https://doi.org/10.1038/s42256-020-00257-z",
    "Gururangan, S., Swayamdipta, S., Levy, O., Schwartz, R., Bowman, S. R., & Smith, N. A. (2018). Annotation "
    "artifacts in natural language inference data. In *Proceedings of NAACL-HLT 2018, Volume 2 (Short Papers)*, "
    "pp. 107–112. https://doi.org/10.18653/v1/N18-2017",
    "Kaushik, D., Hovy, E., & Lipton, Z. C. (2020). Learning the difference that makes a difference with "
    "counterfactually-augmented data. In *International Conference on Learning Representations (ICLR 2020)*. "
    "arXiv:1909.12434",
    "McCoy, R. T., Pavlick, E., & Linzen, T. (2019). Right for the wrong reasons: Diagnosing syntactic heuristics "
    "in natural language inference. In *Proceedings of ACL 2019*, pp. 3428–3448. "
    "https://doi.org/10.18653/v1/P19-1334",
    "McIntire, G. (2017). Fake or real news dataset [Data set]. GitHub. "
    "https://github.com/joolsa/fake_real_news_dataset",
    "Niven, T., & Kao, H.-Y. (2019). Probing neural network comprehension of natural language arguments. In "
    "*Proceedings of ACL 2019*, pp. 4658–4664. https://doi.org/10.18653/v1/P19-1459",
    "Poliak, A., Naradowsky, J., Haldar, A., Rudinger, R., & Van Durme, B. (2018). Hypothesis only baselines in "
    "natural language inference. In *Proceedings of the Seventh Joint Conference on Lexical and Computational "
    "Semantics (\\*SEM 2018)*, pp. 180–191. https://doi.org/10.18653/v1/S18-2023",
    "Schuster, T., Shah, D., Yeo, Y. J. S., Filizzola Ortiz, D. R., Santus, E., & Barzilay, R. (2019). Towards "
    "debiasing fact verification models. In *Proceedings of EMNLP-IJCNLP 2019*, pp. 3419–3425. "
    "https://doi.org/10.18653/v1/D19-1341",
    "Shu, K., Sliva, A., Wang, S., Tang, J., & Liu, H. (2017). Fake news detection on social media: A data mining "
    "perspective. *ACM SIGKDD Explorations Newsletter, 19*(1), 22–36. https://doi.org/10.1145/3137597.3137600",
    "Verma, Y. (2026). What does 99% accuracy measure? A reproducible audit of shortcut learning in a widely used "
    "fake news corpus. arXiv preprint arXiv:2609.25006. https://doi.org/10.48550/arXiv.2609.25006",
    "Wang, W. Y. (2017). \"Liar, liar pants on fire\": A new benchmark dataset for fake news detection. In "
    "*Proceedings of ACL 2017, Volume 2 (Short Papers)*, pp. 422–426. https://doi.org/10.18653/v1/P17-2067",
    "Zhou, X., Elfardy, H., Christodoulopoulos, C., Butler, T., & Bansal, M. (2021). Hidden biases in unreliable "
    "news detection datasets. In *Proceedings of EACL 2021*, pp. 2482–2492. "
    "https://doi.org/10.18653/v1/2021.eacl-main.211",
]
for ref in refs:
    par = p(ref, align=WD_ALIGN_PARAGRAPH.LEFT)
    par.paragraph_format.left_indent = Cm(1)
    par.paragraph_format.first_line_indent = Cm(-1)

OUT.parent.mkdir(exist_ok=True)
doc.save(OUT)
print(f"wrote {OUT}")
