#!/usr/bin/env python3
"""Validate the Phase 6 manuscript package against locked Phase 5 results."""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(name: str) -> str:
    path = PAPER / name
    require(path.exists(), f"missing {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    require(text.strip(), f"empty {path.relative_to(ROOT)}")
    return text


def citation_keys(text: str) -> set[str]:
    return set(re.findall(r"(?<![\w])@([A-Za-z][A-Za-z0-9_:-]+)", text))


def bib_keys(text: str) -> set[str]:
    return set(re.findall(r"@[A-Za-z]+\s*\{\s*([^,\s]+)", text))


def main() -> None:
    required = {
        "manuscript.md",
        "supplement.md",
        "references.bib",
        "data_code_availability.md",
        "reporting_checklist.md",
        "claim_evidence_matrix.md",
        "submission_checklist.md",
    }
    texts = {name: read(name) for name in sorted(required)}

    manuscript = texts["manuscript.md"]
    supplement = texts["supplement.md"]
    bibliography = texts["references.bib"]
    checklist = texts["reporting_checklist.md"]
    matrix = texts["claim_evidence_matrix.md"]

    required_sections = [
        "# Abstract", "# Introduction", "# Related work", "# Methods",
        "# Results", "# Discussion", "## Limitations", "# Conclusion",
        "# Declarations", "# Tables and figures",
    ]
    for section in required_sections:
        require(section in manuscript, f"missing manuscript section: {section}")
    require(manuscript.index("## Limitations") < manuscript.index("# Conclusion"),
            "limitations must precede conclusion")

    combined_citations = citation_keys(manuscript + "\n" + supplement + "\n" + checklist)
    available_bib = bib_keys(bibliography)
    require(combined_citations <= available_bib,
            f"undefined citations: {sorted(combined_citations - available_bib)}")

    locked_phrases = [
        "2,501", "−0.184", "−0.138", "+24.141", "+0.004",
        "0.004975", "0.0196", "a4345fc8cdcb50b90e286914ff6dec8ec1c7373e248f60a260c4eaf11f0d9bc3",
    ]
    combined = manuscript + "\n" + supplement
    for phrase in locked_phrases:
        require(phrase in combined, f"locked result/hash absent: {phrase}")

    require("same 103 JIGSAWS trials" in combined, "Paper 1 overlap not explicit")
    require("not independent" in combined.lower(), "independent-validation limitation absent")
    require("equivalence" in combined.lower(), "detectable-effect/equivalence discussion absent")
    require("expert-rated" in combined, "expert-rated target distinction absent")
    require("objective task-performance" in combined, "external target wording absent")

    forbidden = [
        "ROSMA expert skill", "BGU-PatCut expert skill", "BGU-SKILLS expert skill",
        "removed all identity", "proves invariance", "clinically validated",
    ]
    for phrase in forbidden:
        require(phrase.lower() not in combined.lower(), f"prohibited claim: {phrase}")

    for item in range(1, 28):
        require(re.search(rf"\| {item}(?:[a-z])? \|", checklist),
                f"TRIPOD+AI item {item} not mapped")
    for claim in range(1, 15):
        require(f"| C{claim} |" in matrix, f"claim C{claim} missing")

    effects_path = ROOT / "results" / "locked" / "phase5_effect_summaries.csv"
    require(effects_path.exists(), "locked effect summary missing")
    with effects_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    require(rows, "locked effect summary empty")

    require("repository does not currently declare a software license" in
            texts["data_code_availability.md"].lower(),
            "code-license status must be transparent")
    require("author/editor actions required" in texts["submission_checklist.md"].lower(),
            "submission metadata gate absent")

    print("Phase 6 validation passed")
    print(f"Validated {len(required)} paper artifacts, {len(combined_citations)} citation keys, and 14 claims")


if __name__ == "__main__":
    main()
