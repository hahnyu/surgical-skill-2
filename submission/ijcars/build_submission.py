#!/usr/bin/env python3
"""Build the IJCARS manuscript, supplement, and cover-letter PDFs."""

from __future__ import annotations

import csv
import json
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg


ROOT = Path(__file__).resolve().parents[2]
SUBMISSION = ROOT / "submission" / "ijcars"
FIGURES = SUBMISSION / "figures"
BUILD = ROOT / "tmp" / "pdfs" / "ijcars-build"
OUTPUT = ROOT / "output" / "pdf"

TITLE = (
    "Operator identity and out-of-user generalization in automated surgical "
    "skill assessment: a multi-dataset evaluation"
)

AUTHORS_TEX = r"""
\author{Hamilton Jeong\textsuperscript{1,*}, Zaid Elnasser\textsuperscript{1},
Laurienne Jeong\textsuperscript{1},\\
Su\'elia de Siqueira Rodrigues Fleury Rosa\textsuperscript{2}\\[0.75em]
\small \textsuperscript{1}College of Agriculture and Life Sciences, Cornell University,\\
\small 215 Garden Avenue, Ithaca, NY 14850, USA\\
\small \textsuperscript{2}Meinig School of Biomedical Engineering, Cornell University,\\
\small 237 Tower Road, Ithaca, NY 14850, USA\\[0.5em]
\small \textsuperscript{*}Corresponding author: \href{mailto:hhj22@cornell.edu}{hhj22@cornell.edu}}
""".strip()

ABSTRACT_TEX = r"""
\begin{abstract}
\textbf{Purpose:} Repeated recordings from the same operator can permit surgical-performance models to use operator-specific motion patterns. We tested whether operator identity was recoverable from surgical kinematics and whether suppressing that information improved prediction for unseen operators.

\textbf{Methods:} We retrospectively analyzed 2,501 dry-lab trials representing 92 dataset-participants from JIGSAWS, ROSMA, BGU-PatCut, and BGU-SKILLS. Outcomes were expert-rated Global Rating Scale, observed task errors, and image-derived cutting error; BGU-SKILLS contributed to identity analysis only. We compared same-participant with held-out-participant evaluation, used fresh linear and random-forest identity probes and JIGSAWS label permutations, and evaluated duration removal, duration residualization, linear identity-subspace projection (I3), and adversarial suppression (I4). Intervals used 2,000 participant bootstrap replicates.

\textbf{Results:} Unsuppressed identity accuracy ranged from 0.228--0.944 for linear probes and 0.381--0.844 for nonlinear probes across ten dataset-task groups. JIGSAWS participant-wise permutations retained substantially more same-participant skill accuracy than record-wise permutations (median differences 0.444--0.538). I3 reduced fresh linear identity accuracy by 0.184 (95\% interval 0.153--0.214) and nonlinear accuracy by 0.138 (0.100--0.175); I4 failed the prespecified two-probe rule. Held-out-participant standardized mean absolute error favored I3 in one of seven tasks and the unsuppressed model in six; six intervals crossed zero.

\textbf{Conclusion:} Identity was recoverable and targeted projection reduced tested identity recovery, but suppression did not consistently improve unseen-operator prediction. Identity diagnostics and held-out-user utility should be evaluated separately.
\end{abstract}

\noindent\textbf{Keywords:} surgical skill assessment; operator identity; out-of-user validation; domain generalization; kinematics; representation learning

\noindent\textbf{Total word count:} WORDCOUNT
""".strip()

SUPPLEMENT_AUTHORS_TEX = r"""
\author{Hamilton Jeong\textsuperscript{1,*}, Zaid Elnasser\textsuperscript{1},
Laurienne Jeong\textsuperscript{1},\\
Su\'elia de Siqueira Rodrigues Fleury Rosa\textsuperscript{2}\\[0.5em]
\small International Journal of Computer Assisted Radiology and Surgery\\
\small \textsuperscript{1}College of Agriculture and Life Sciences, Cornell University, Ithaca, NY, USA\\
\small \textsuperscript{2}Meinig School of Biomedical Engineering, Cornell University, Ithaca, NY, USA\\
\small \textsuperscript{*}Corresponding author: \href{mailto:hhj22@cornell.edu}{hhj22@cornell.edu}}
""".strip()

PREAMBLE = r"""
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{calc}
\usepackage{float}
\usepackage{xcolor}
\usepackage{amsmath,amssymb}
\usepackage[numbers,sort&compress]{natbib}
\usepackage[hidelinks]{hyperref}
\providecommand{\doi}[1]{\href{https://doi.org/#1}{https://doi.org/#1}}
\setlength{\emergencystretch}{3em}
\setlength{\parindent}{1.5em}
\setlength{\parskip}{0.25em}
\linespread{1.18}
\sloppy
\widowpenalty=10000
\clubpenalty=10000
\renewcommand{\refname}{References}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\providecommand{\real}[1]{#1}
""".strip()


TABLE1 = r"""
```{=latex}
\begin{table}[H]
\centering
\caption{Datasets, cohorts, outcomes, and analysis roles. Participant counts are dataset-specific and are not linked across cohorts.}
\label{tab:datasets}
\small
\begin{tabularx}{\textwidth}{@{}lXrrX@{}}
\toprule
Dataset & Tasks & Trials & Participants & Retained role/outcome \\
\midrule
JIGSAWS & Knot tying; needle passing; suturing & 103 & 8 overall & Expert-rated GRS; person-level mechanism \\
ROSMA & Pea on a peg; post and sleeve; wire chaser I & 206 & 12 & Observed task-specific errors \\
BGU-SKILLS & Knot tying; ring tower transfer; suturing & 938 & 18 & Identity and longitudinal robustness only \\
BGU-PatCut & Pattern cutting & 1,254 & 54 & Image-derived total cutting error \\
\bottomrule
\end{tabularx}
\end{table}
```
""".strip()

TABLE2 = r"""
```{=latex}
\begin{table}[H]
\centering
\caption{Harmonized kinematic feature families. Forty-one variables were available after source-specific matching. All transforms were fitted within training folds.}
\label{tab:features}
\small
\begin{tabularx}{\textwidth}{@{}lclX@{}}
\toprule
Family & Count & Availability & Contents \\
\midrule
Cross-arm/time & 3 & All datasets & Duration, bimanual speed correlation, path-length asymmetry \\
Instrument arm 1 & 19 & All core features & Sample count/rate; path length; speed, acceleration, jerk; idle fraction; workspace; gaps; gripper summaries \\
Instrument arm 2 & 19 & All core features & Same summaries as arm 1 \\
Gripper subset & 8 total & Not present in ROSMA & Mean, SD, range, and total variation for each arm \\
\bottomrule
\end{tabularx}
\end{table}
```
""".strip()

TABLE3 = r"""
```{=latex}
\begin{table}[H]
\centering
\caption{Participant-average ridge mean absolute error under same-participant and held-out-participant evaluation. Values remain in each dataset's native outcome units.}
\label{tab:baselines}
\small
\begin{tabular}{@{}llrr@{}}
\toprule
Dataset & Task & Same participant & Held-out participant \\
\midrule
BGU-PatCut & Pattern Cutting & 9,231.214 & 10,440.406 \\
JIGSAWS & Knot Tying & 2.735 & 3.505 \\
JIGSAWS & Needle Passing & 3.029 & 3.202 \\
JIGSAWS & Suturing & 3.246 & 4.968 \\
ROSMA & Pea on a Peg & 21.120 & 6.475 \\
ROSMA & Post and Sleeve & 0.433 & 0.443 \\
ROSMA & Wire Chaser I & 0.444 & 0.518 \\
\bottomrule
\end{tabular}
\end{table}
```
""".strip()

TABLE4 = r"""
```{=latex}
\begin{table}[H]
\centering
\caption{Unsuppressed identity recovery. Balanced accuracy is participant averaged. These tuned-probe results are descriptive; a fixed-penalty logistic null cannot calibrate either tuned model.}
\label{tab:identity}
\small
\begin{tabular}{@{}llrr@{}}
\toprule
Dataset & Task & Linear & Nonlinear \\
\midrule
JIGSAWS & Knot Tying & 0.869 & 0.827 \\
JIGSAWS & Needle Passing & 0.943 & 0.840 \\
JIGSAWS & Suturing & 0.944 & 0.844 \\
ROSMA & Pea on a Peg & 0.381 & 0.397 \\
ROSMA & Post and Sleeve & 0.446 & 0.381 \\
ROSMA & Wire Chaser I & 0.228 & 0.431 \\
BGU-SKILLS & Knot Tying & 0.530 & 0.393 \\
BGU-SKILLS & Ring Tower Transfer & 0.596 & 0.487 \\
BGU-SKILLS & Suturing & 0.762 & 0.618 \\
BGU-PatCut & Pattern Cutting & 0.834 & 0.750 \\
\bottomrule
\end{tabular}
\end{table}
```
""".strip()

TABLE5 = r"""
```{=latex}
\begin{table}[H]
\centering
\caption{Primary held-out-participant effects of I3 identity-subspace removal versus I0. Differences are MAE(I3) minus MAE(I0); negative values favor I3. Intervals resample participants.}
\label{tab:effects}
\footnotesize
\begin{tabularx}{\textwidth}{@{}lXrr@{}}
\toprule
Dataset & Task & Standardized difference [95\% interval] & Native difference [95\% interval] \\
\midrule
BGU-PatCut & Pattern Cutting & +0.029 [-0.038, +0.091] & +487.183 [-648.849, +1,613.362] \\
JIGSAWS & Knot Tying & +0.042 [-0.039, +0.132] & +0.205 [-0.195, +0.604] \\
JIGSAWS & Needle Passing & +0.125 [-0.018, +0.290] & +0.618 [-0.045, +1.400] \\
JIGSAWS & Suturing & -0.083 [-0.352, +0.170] & -0.401 [-1.757, +0.938] \\
ROSMA & Pea on a Peg & +24.141 [-0.019, +72.407] & +28.858 [-0.020, +86.539] \\
ROSMA & Post and Sleeve & +0.009 [-0.125, +0.154] & +0.005 [-0.072, +0.086] \\
ROSMA & Wire Chaser I & +0.004 [+0.000, +0.011] & +0.003 [0.000, +0.008] \\
\bottomrule
\end{tabularx}
\end{table}
```
""".strip()


def figure(number: int, name: str, caption: str, width: str = "0.96") -> str:
    return rf"""
```{{=latex}}
\begin{{figure}}[H]
\centering
\includegraphics[width={width}\textwidth]{{figures/{name}.pdf}}
\caption{{{caption}}}
\label{{fig:phase5-{number}}}
\end{{figure}}
```
""".strip()


FIGURE1 = figure(1, "Fig1", "Study design, datasets, validation protocols, identity diagnostics, interventions, and locked inference.")
FIGURE2 = figure(2, "Fig2", "Standardized protocol gap for ridge prediction. Positive values indicate less favorable held-out-participant than same-participant error. Each task has its own labeled x-axis scale.")
FIGURE3 = figure(3, "Fig3", "JIGSAWS same-participant person-level skill accuracy under observed labels and participant-wise versus record-wise shuffles. Markers show observed accuracy or shuffle medians; whiskers show the 2.5th--97.5th percentiles across 200 shuffles, not participant-confidence intervals.")
FIGURE4 = figure(4, "Fig4", "Fresh-probe balanced-accuracy changes with corrected participant-cluster intervals. Seeds are averaged within participant and task; participants are resampled jointly across tasks within each dataset. I1--I3 and random projection use I0; I4 variants use the capacity control. Lower values indicate less identity recovery.", "0.96")
FIGURE5 = figure(5, "Fig5", "Primary task-specific held-out-participant standardized MAE(I3) minus MAE(I0), with 95\\% intervals. Each task has its own labeled x-axis scale; negative values favor I3. All control effects remain available in the machine-readable supplement.", "0.96")
FIGURE6 = figure(6, "Fig6", "JIGSAWS task-specific comparison. Left: participant-average same-participant skill accuracy under I0 and I3. Right: standardized held-out-participant GRS MAE(I3) minus MAE(I0), with the same intervals as Table 5. Axes and endpoints differ between panels.")

def declarations() -> str:
    return (SUBMISSION / "declarations.md").read_text(encoding="utf-8")


SHORT_INTRODUCTION = r"""
# Introduction

Automated assessment could make surgical-training feedback more reproducible, but studies often contain small cohorts, repeated trials from each operator, and heterogeneous targets [@Lam2022]. Shared resources such as JIGSAWS support comparison across methods [@Ahmidi2017], yet a record-wise split can place trials from one person in both training and testing. A model may then exploit stable operator-specific motion patterns rather than information that transfers to a new operator, a form of shortcut learning [@Geirhos2020]. Claims about unseen users therefore require participant-held-out evaluation.

A same-participant versus held-out-participant performance gap reveals protocol sensitivity, while an identity probe tests whether a representation contains operator-identifying information. Neither proves that the outcome model uses identity. For person-constant labels, participant-wise permutation preserves identity-to-label lookup after destroying the original label assignment, whereas record-wise permutation breaks both.

An earlier unpublished JIGSAWS-only manuscript and software repository from this project (https://github.com/hahnyu/surgical-skill) analyzed the same 103 JIGSAWS trials. The present JIGSAWS component is therefore a replication and mechanistic extension, not independent validation. This study adds ROSMA, BGU-SKILLS, and BGU-PatCut; a harmonized representation; prespecified identity-suppression interventions; fresh probes; negative controls; and participant-level inference.

We asked whether operator identity was recoverable across surgical-training datasets and whether verified suppression improved prediction for an unseen operator. We expected identity recovery above empirical nulls and participant-wise JIGSAWS permutations to retain more same-participant classification than record-wise permutations. We evaluated utility only after requiring suppression to reduce both fresh linear and nonlinear identity probes.
""".strip()

SHORT_METHODS = r"""
# Methods

## Study design, datasets, and outcomes

This retrospective benchmark followed a protocol frozen before predictive modeling (`protocol-v1`, 21 September 2026). A post-lock correction dated 16 November 2026 revised uncertainty and reporting without refitting primary outcome or intervention models or changing participants or outcomes (Online Resource 1). Trials remained intact within folds, analyses were task specific, and the participant was the independent unit for uncertainty. The analysis included 2,501 dry-lab trials representing 92 dataset-participants across four distinct cohorts. JIGSAWS contributed 103 trials and expert-rated Global Rating Scale (GRS); its self-declared experience class was used only for a person-level diagnostic. ROSMA contributed 206 trials with observed task-error counts. BGU-PatCut contributed 1,254 trials with image-derived total cutting error. BGU-SKILLS contributed 938 trials to identity and longitudinal robustness analyses because its available performance metrics were derived from the planned kinematic predictors. Source provenance and detailed inclusion rules are reported in Online Resource 1 [@RivasBlanco2023; @ROSMAData2022; @SharonPatCut2024; @PatCutData2024; @BGUSkillsData2025].

## Features, validation, and models

Task windows followed source annotations. The harmonized representation contained 41 available variables spanning duration, per-arm sample count and rate, path length, speed, acceleration, jerk, idle fraction, workspace, missing-data gaps, gripper summaries where available, bimanual speed correlation, and path-length asymmetry. Imputation, scaling, model selection, and every learned transformation used training-fold data only.

Same-participant folds retained each participant on both sides; held-out-participant folds withheld complete participants. Inner validation matched the outer generalization unit. Phase 3 continuous-outcome baselines used training-mean, duration-only ridge, and all-feature ridge models with nested penalty selection. Phase 4 linear intervention comparisons fixed the downstream ridge penalty at alpha=10; their I0 comparator was fitted with that same penalty. JIGSAWS person-level classification used majority, duration-only multinomial-logistic, and all-feature multinomial-logistic models. All predictions were out of fold.

## Identity diagnostics and interventions

Identity probes predicted participant labels with nested multinomial logistic regression and random forests; balanced accuracy was averaged by participant. Fifty record-wise identity-label permutations used a fixed-C=1 logistic pipeline. Because it did not match the tuned observed probes, we withdrew their permutation-test claims and report observed identity accuracy descriptively. A separate post-lock fixed-C diagnostic with a matched null is reported in Online Resource 1. For JIGSAWS experience classification, 200 paired participant-wise and record-wise permutations were evaluated under same-participant folds.

I0 retained all features. I1 removed duration equivalents, and I2 residualized remaining features on duration. I3 fitted a regularized participant classifier within each training fold and projected out selected coefficient-span directions, following linear guarding principles [@Ravfogel2020]. A dimension-matched random projection served as a control. I4 used an eight-unit latent multilayer perceptron with a gradient-reversal identity head [@Ganin2016], plus capacity and shuffled-label controls. After freezing each representation, new linear and nonlinear probes tested identity recovery under same-participant folds. Held-out-participant representations were fitted separately; these probes do not verify identity removal in each held-out representation. The primary intervention had to reduce both probes; I4 was considered first, with I3 versus I0 prespecified if I4 failed.

## Estimands and inference

The primary utility estimand was participant-average held-out-participant MAE(I3) minus MAE(I0); negative values favor I3. Trial differences were also standardized by the outcome standard deviation estimated without the outer test fold. Task-utility effects are reported separately in native and standardized units, without pooling across tasks. Percentile intervals used 2,000 participant bootstrap replicates. For aggregate identity effects, seeds were averaged within participant and task before resampling dataset-participants jointly across their tasks; task groups received equal weight. I3 included ten groups; I4 included seven outcome-eligible groups. Intervals condition on saved out-of-fold predictions and do not capture model-refitting uncertainty. Leave-one-participant summaries omit scored participant effects without refitting. The JIGSAWS two-scheme shuffle comparison is descriptive, not a hypothesis test. Locked artifact hashes, complete hyperparameters, deviations, and reproducibility controls are in Online Resource 1; reporting follows an adapted TRIPOD+AI checklist [@Collins2024].
""".strip()

SHORT_RESULTS = r"""
# Results

## Feasibility and target audit

All datasets contained repeated trials and stable participant keys. JIGSAWS supplied the only expert-rated outcome; ROSMA errors and BGU-PatCut cutting error were retained as narrower task-performance outcomes. BGU-SKILLS was not relabeled with a kinematics-derived outcome.

## Protocol gap

Held-out-participant minus same-participant standardized ridge MAE was positive in six of seven eligible tasks (Figure 2). JIGSAWS person-level same-participant versus held-out-participant accuracy was 0.917 versus 0.444 for knot tying, 1.000 versus 0.464 for needle passing, and 0.872 versus 0.462 for suturing. Participant-average gaps were +0.419 (95% interval 0.063--0.775), +0.479 (0.214--0.757), and +0.400 (0.150--0.675).

## Identity recovery and formal nulls

Identity was recoverable in every dataset-task group (Table 4). Linear balanced accuracy ranged from 0.228 to 0.944 and nonlinear accuracy from 0.381 to 0.844; these are descriptive results, with no matched permutation-test claim for either tuned probe. Duration-only accuracy ranged from 0.056 to 0.225.

JIGSAWS participant-wise skill-label permutations (Figure 3) retained substantially more same-participant accuracy than record-wise permutations. Median paired differences were +0.444 for knot tying, +0.536 for needle passing, and +0.538 for suturing (none of 200 paired draws per task had a nonpositive difference), consistent with identity-compatible lookup. These Monte Carlo comparisons are not hypothesis-test p values.

## Intervention verification

I4 changed fresh linear identity accuracy by -0.048 (95% interval -0.098 to +0.002) relative to its capacity control and nonlinear accuracy by -0.003 (-0.045 to +0.043). Both corrected intervals crossed zero; I4 therefore failed the two-probe rule. I3 became primary. Relative to I0, I3 reduced linear balanced accuracy by 0.184 (0.153--0.214) and nonlinear accuracy by 0.138 (0.100--0.175), averaging dataset-task groups equally (Figure 4). Duration removal, duration residualization, and a dimension-matched random projection did not reproduce this joint reduction.

## Held-out-participant utility

Verified suppression did not consistently improve held-out-participant prediction (Figure 5; Table 5). The standardized I3-minus-I0 MAE point estimate favored I3 in one task and I0 in six; six of seven intervals crossed zero. The wire-chaser estimate was +0.004 (0.000--0.011). The ROSMA pea-on-a-peg standardized estimate was unstable because the outcome was sparse and some outer-training standard deviations were small. Native-unit estimates and all intervals are reported in Table 5.

## Same-participant skill and robustness

For JIGSAWS person-level skill, I3 changed same-participant accuracy by -0.025 (-0.075 to 0.000) for knot tying, 0.000 (0.000 to 0.000) for needle passing, and +0.025 (-0.100 to +0.125) for suturing (Figure 6). The expected consistent reduction was absent. Fresh nonlinear probes also showed that confusing I4's training adversary did not establish invariance. Influence, seed, fold, missingness, and hyperparameter analyses are reported in Online Resource 1.
""".strip()

SHORT_DISCUSSION = r"""
# Discussion

Operator identity was recoverable across four surgical-training datasets, and JIGSAWS participant-wise permutations showed that person-compatible structure could sustain same-participant classification after the original experience assignments were destroyed. Targeted linear projection reduced both fresh identity probes. This verified reduction nevertheless did not consistently improve prediction for unseen operators.

Protocol gaps and identity probes diagnose opportunities for shortcut use; they do not show that an outcome model depends on identity. Removing a learned identity subspace can also discard stable motion components that predict performance. The task-specific estimates, which favored I0 in six of seven tasks but mostly included both benefit and harm, support neither a universal benefit nor a universal cost of suppression. The I4 result further shows why a separately fitted nonlinear probe and matched controls are needed: the training adversary can be confused while identity remains decodable.

Held-out-participant evaluation should match claims about new users. Same-participant results remain relevant for systems that personalize to known trainees, but answer a different question. When suppression is proposed, independent probes should verify it and held-out-user utility should be measured rather than assumed.

## Limitations

Independent cohorts were small despite 2,501 trials: JIGSAWS had seven or eight participants per task, ROSMA 12, and BGU-SKILLS 18. Most intervals therefore permit effects in either direction, and no equivalence margin was prespecified. Outcomes were heterogeneous: only JIGSAWS GRS was expert rated; ROSMA errors and BGU-PatCut error measured narrower constructs. All tasks were simulated or dry-lab exercises, so the results do not establish clinical validity, educational benefit, fairness, or patient outcomes.

Identity may encode stable skill, motor strategy, prior training, or measurement artifacts; I3 removes selected linear directions and cannot prove that all identity is absent. The harmonized summary representation also differs from sequence or video models. Demographic attributes were unavailable. No prospective cohort or deployment study was performed, and one retained ROSMA trial with source coordinate spikes contributed to unstable pea-on-a-peg estimates.
""".strip()


def run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd or ROOT, check=True)


def strip_frontmatter(text: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)


def insert_before(text: str, heading: str, material: str) -> str:
    if heading not in text:
        raise ValueError(f"Heading not found: {heading}")
    return text.replace(heading, f"{material}\n\n{heading}", 1)


def pandoc_body(markdown: str, stem: str) -> str:
    source = BUILD / f"{stem}.md"
    destination = BUILD / f"{stem}_body.tex"
    source.write_text(markdown, encoding="utf-8")
    run([
        "pandoc", str(source), "--from=markdown", "--to=latex", "--natbib", "--no-highlight",
        "--bibliography", str(SUBMISSION / "references.bib"), "-o", str(destination),
    ])
    return destination.read_text(encoding="utf-8")


def prepare_manuscript_markdown() -> str:
    text = strip_frontmatter((ROOT / "paper" / "manuscript.md").read_text(encoding="utf-8"))
    text = re.sub(r"\A\s*> \*\*Submission metadata:.*?\n\n", "", text, count=1, flags=re.S)
    text = re.sub(r"# Abstract\n.*?(?=# Introduction)", "", text, count=1, flags=re.S)
    text = re.sub(r"# Introduction\n.*?(?=# Related work)", SHORT_INTRODUCTION + "\n\n", text, count=1, flags=re.S)
    text = re.sub(r"# Related work\n.*?(?=# Methods)", "", text, count=1, flags=re.S)
    text = re.sub(r"# Methods\n.*?(?=# Results)", SHORT_METHODS + "\n\n", text, count=1, flags=re.S)
    text = re.sub(r"# Results\n.*?(?=# Discussion)", SHORT_RESULTS + "\n\n", text, count=1, flags=re.S)
    text = re.sub(r"# Discussion\n.*?(?=# Conclusion)", SHORT_DISCUSSION + "\n\n", text, count=1, flags=re.S)
    text = re.sub(
        r"# Declarations\n.*?(?=# Tables and figures)",
        lambda _: declarations() + "\n\n",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(r"# Tables and figures\n.*\Z", "", text, count=1, flags=re.S)
    text = insert_before(text, "# Results", "## Use of artificial intelligence tools\n\n" + (SUBMISSION / "ai_use_disclosure.md").read_text(encoding="utf-8"))
    text = insert_before(text, "## Protocol gap", f"{FIGURE1}\n\n{TABLE1}\n\n{TABLE2}")
    text = insert_before(text, "## Identity recovery and formal nulls", f"{FIGURE2}\n\n{TABLE3}")
    text = insert_before(text, "## Intervention verification", f"{FIGURE3}\n\n{TABLE4}")
    text = insert_before(text, "## Held-out-participant utility", FIGURE4)
    text = insert_before(text, "## Same-participant skill and robustness", f"{FIGURE5}\n\n{TABLE5}")
    text = insert_before(text, "# Discussion", FIGURE6)
    text = text.replace(
        "## Protocol gap\n",
        "## Protocol gap\n\nFigure 1 summarizes the study flow. Table 1 documents the analyzed cohorts, and Table 2 lists the harmonized feature families.\n\n",
        1,
    )
    text = text.replace(
        "## Identity recovery and formal nulls\n",
        "## Identity recovery and formal nulls\n\nTable 3 reports the same-participant and held-out-participant baseline errors used to frame the protocol comparison.\n\n",
        1,
    )
    text = text.replace(
        "## Held-out-participant utility\n",
        "## Held-out-participant utility\n\nFigure 4 reports identity changes with corrected uncertainty; task utility is evaluated separately.\n\n",
        1,
    )
    return text.replace("−", "-").replace("–", "--").replace("—", "---")


def wrap_article(body: str, title: str, authors: bool, abstract: bool) -> str:
    author_block = AUTHORS_TEX if authors else SUPPLEMENT_AUTHORS_TEX
    abstract_block = ABSTRACT_TEX if abstract else ""
    return "\n".join([
        PREAMBLE,
        rf"\title{{{title}}}",
        author_block,
        r"\date{}",
        r"\begin{document}",
        r"\maketitle",
        abstract_block,
        r"\setcounter{secnumdepth}{0}" if not abstract else "",
        body,
        r"\bibliographystyle{unsrtnat}",
        r"\bibliography{references}",
        r"\end{document}",
        "",
    ])


def compile_tex(name: str, output_name: str) -> None:
    outdir = BUILD / name
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    run([
        "latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
        f"-outdir={outdir}", f"{name}.tex",
    ], cwd=SUBMISSION)
    shutil.copy2(outdir / f"{name}.pdf", OUTPUT / output_name)


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    if FIGURES.exists():
        shutil.rmtree(FIGURES)
    FIGURES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for source in sorted((ROOT / "results" / "figures").glob("phase5_figure*.svg")):
        if re.search(r"figure[12456]_", source.stem):
            continue
        svg_text = source.read_text(encoding="utf-8").replace("Participant-wise null", "Participant-wise shuffles").replace("Record-wise null", "Record-wise shuffles")
        dimensions = re.search(r'<svg[^>]+width="([0-9.]+)"[^>]+height="([0-9.]+)"', svg_text)
        if dimensions is None:
            raise RuntimeError(f"Missing numeric SVG dimensions in {source}")
        width, height = dimensions.groups()
        svg_text = svg_text.replace(
            '<rect width="100%" height="100%"',
            f'<rect x="0" y="0" width="{width}" height="{height}"',
        )
        sanitized = BUILD / f"{source.stem}.svg"
        sanitized.write_text(svg_text, encoding="utf-8")
        drawing = svg2rlg(str(sanitized))
        if drawing is None:
            raise RuntimeError(f"Could not parse {source}")
        number_match = re.search(r"figure([1-6])_", source.stem)
        if number_match is None:
            raise RuntimeError(f"Could not identify figure number for {source}")
        renderPDF.drawToFile(drawing, str(FIGURES / f"Fig{number_match.group(1)}.pdf"))

    from corrected_figures import build_corrected_figures
    build_corrected_figures(ROOT, FIGURES)

    bibliography = (ROOT / "paper" / "references.bib").read_text(encoding="utf-8")
    bibliography = bibliography.replace("@dataset{", "@misc{")
    # unsrtnat ignores DOI fields on misc records; give each dataset a URL.
    bibliography = re.sub(r"(@misc\{.*?)(?=\n@|\Z)", lambda m: re.sub(
        r"doi = \{([^}]+)\}", lambda d: "url = {https://doi.org/" + d.group(1) + "}", m.group(0)),
        bibliography, flags=re.S)
    (SUBMISSION / "references.bib").write_text(bibliography, encoding="utf-8")

    manuscript_body = pandoc_body(prepare_manuscript_markdown(), "manuscript_source")
    manuscript_tex = wrap_article(manuscript_body, TITLE, authors=True, abstract=True)
    (SUBMISSION / "manuscript.tex").write_text(manuscript_tex, encoding="utf-8")

    supplement_md = strip_frontmatter((ROOT / "paper" / "supplement.md").read_text(encoding="utf-8"))
    supplement_md = supplement_md.replace("Identity/longitudinal analysis only", "Identity and longitudinal analysis only")
    from corrected_supplement import correct_supplement
    supplement_md = correct_supplement(supplement_md, ROOT)
    supplement_md = supplement_md.replace("−", "-").replace("–", "--").replace("—", "---")
    supplement_body = pandoc_body(supplement_md, "supplement_source")
    supplement_tex = wrap_article(
        supplement_body,
        "Supplementary Information: " + TITLE,
        authors=False,
        abstract=False,
    )
    (SUBMISSION / "supplement.tex").write_text(supplement_tex, encoding="utf-8")

    compile_tex("manuscript", "ijcars_manuscript.pdf")
    # Count the rendered document inclusively, then converge the displayed count.
    for _ in range(3):
        rendered = subprocess.check_output(["pdftotext", str(OUTPUT / "ijcars_manuscript.pdf"), "-"], text=True)
        count = len(re.findall(r"\b[\w'-]+\b", rendered))
        displayed = f"{count:,}"
        new_tex = re.sub(r"Total word count:\} [\d,]+|Total word count:\} WORDCOUNT",
                         "Total word count:} " + displayed, manuscript_tex)
        if new_tex == manuscript_tex:
            break
        manuscript_tex = new_tex
        (SUBMISSION / "manuscript.tex").write_text(manuscript_tex, encoding="utf-8")
        compile_tex("manuscript", "ijcars_manuscript.pdf")
    (SUBMISSION / "build_metadata.json").write_text(json.dumps({"inclusive_word_count": count, "status": "draft; human confirmations pending"}, indent=2) + "\n")
    compile_tex("supplement", "ESM_1.pdf")
    compile_tex("cover_letter", "ijcars_cover_letter.pdf")

    obsolete = OUTPUT / "ijcars_supplement.pdf"
    if obsolete.exists():
        obsolete.unlink()

    rendered = subprocess.check_output(["pdftotext", str(OUTPUT / "ijcars_manuscript.pdf"), "-"], text=True)
    abstract = "Purpose:" + rendered.split("Purpose:", 1)[1].split("Keywords:", 1)[0]
    (SUBMISSION / "portal_abstract.txt").write_text(re.sub(r"\s+", " ", abstract).strip() + "\n")
    package_paths = [*SUBMISSION.glob("*.py"), *SUBMISSION.glob("*.tex"), *SUBMISSION.glob("*.bib"),
                     *SUBMISSION.glob("*.md"), SUBMISSION / "author_confirmations.json",
                     SUBMISSION / "build_metadata.json", SUBMISSION / "portal_abstract.txt",
                     *FIGURES.glob("*.pdf"), *OUTPUT.glob("*.pdf"),
                     * (ROOT / "results/corrections/2026-11-16").glob("*.csv"),
                     * (ROOT / "results/corrections/2026-11-16").glob("*.json")]
    package_manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(package_paths)}
    (SUBMISSION / "package_manifest.json").write_text(json.dumps(package_manifest, indent=2) + "\n")
    print("Built IJCARS submission PDFs in output/pdf")


if __name__ == "__main__":
    main()
