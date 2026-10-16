#!/usr/bin/env python3
"""Validate the assembled IJCARS LaTeX submission package."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission" / "ijcars"
OUTPUT = ROOT / "output" / "pdf"
BUILD = ROOT / "tmp" / "pdfs" / "ijcars-build"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def command_text(*command: str) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def pdf_text(path: Path) -> str:
    return command_text("pdftotext", str(path), "-")


def page_count(path: Path) -> int:
    match = re.search(r"^Pages:\s+(\d+)$", command_text("pdfinfo", str(path)), re.M)
    require(match is not None, f"Could not read page count for {path}")
    return int(match.group(1))


def words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def main() -> None:
    required_sources = [
        SUBMISSION / "manuscript.tex",
        SUBMISSION / "supplement.tex",
        SUBMISSION / "cover_letter.tex",
        SUBMISSION / "references.bib",
        SUBMISSION / "submission_metadata.md",
        SUBMISSION / "submission_checklist.md",
        SUBMISSION / "ai_use_disclosure_PLACEHOLDER.md",
        SUBMISSION / "ethics_determination_request.md",
    ]
    required_pdfs = [
        OUTPUT / "ijcars_manuscript.pdf",
        OUTPUT / "ESM_1.pdf",
        OUTPUT / "ijcars_cover_letter.pdf",
    ]
    for path in required_sources + required_pdfs:
        require(path.is_file() and path.stat().st_size > 0, f"Missing required file: {path}")

    figures = sorted((SUBMISSION / "figures").glob("Fig*.pdf"))
    require([path.name for path in figures] == [f"Fig{i}.pdf" for i in range(1, 7)], "Expected Fig1.pdf through Fig6.pdf")
    require(sorted(path.name for path in OUTPUT.glob("*.pdf")) == ["ESM_1.pdf", "ijcars_cover_letter.pdf", "ijcars_manuscript.pdf"], "Unexpected PDF set in output/pdf")

    manuscript = pdf_text(required_pdfs[0])
    supplement = pdf_text(required_pdfs[1])
    cover = pdf_text(required_pdfs[2])

    total_words = words(manuscript)
    require(total_words == 4245, f"Inclusive manuscript word count changed: {total_words}")
    require("Total word count: 4,245" in manuscript, "Displayed total word count is missing")
    abstract = manuscript.split("Keywords:", 1)[0].split("Purpose:", 1)[1]
    require(200 <= words(abstract) <= 250, f"Structured abstract is {words(abstract)} words")

    for name in ["Hamilton Jeong", "Zaid Elnasser", "Laurienne Jeong", "Bhumika Iroji", "Suélia de Siqueira Rodrigues Fleury Rosa"]:
        require(name in manuscript, f"Missing author: {name}")
    for statement in [
        "The authors received no funding for this work.",
        "The authors declare no financial or non-financial competing interests.",
        "did not require further Cornell Institutional Review Board review",
        "Online Resource 1",
    ]:
        require(statement in manuscript, f"Missing required statement: {statement}")

    require(manuscript.count("AUTHOR TO COMPLETE BEFORE SUBMISSION") == 1, "AI disclosure placeholder must appear exactly once")
    require(not re.search(r"(?i)\bnan\b|\?\?", manuscript), "Manuscript contains an invalid numeric or unresolved marker")
    references = manuscript.rsplit("References", 1)[1]
    require(len(re.findall(r"\[\d+\]", references)) == 12, "Expected 12 numbered references")
    require("https://doi.org/" in manuscript, "References must display full DOI links")
    for number in range(1, 7):
        require(manuscript.count(f"Figure {number}") >= 2, f"Figure {number} is not both cited and captioned")
    for number in range(1, 6):
        require(manuscript.count(f"Table {number}") >= 2, f"Table {number} is not both cited and captioned")

    require(page_count(required_pdfs[2]) == 1, "Cover letter must fit on one page")
    require("International Journal of Computer Assisted Radiology and Surgery" in cover, "Cover letter is not journal specific")
    require("no funding" in cover and "no financial or non-financial competing interests" in cover, "Cover letter declarations are incomplete")

    for item in [
        "International Journal of Computer Assisted Radiology and Surgery",
        "Hamilton Jeong",
        "hhj22@cornell.edu",
        "a4345fc8cdcb50b90e286914ff6dec8ec1c7373e248f60a260c4eaf11f0d9bc3",
    ]:
        require(item in supplement, f"Supplement is missing: {item}")

    for log in BUILD.glob("*/*.log"):
        log_text = log.read_text(encoding="utf-8", errors="replace")
        require(not re.search(r"Overfull|undefined|Undefined|LaTeX Warning|Package natbib Warning", log_text), f"Material LaTeX warning in {log}")

    print("IJCARS submission package validation passed")
    print(f"  manuscript: {page_count(required_pdfs[0])} pages, {total_words} inclusive words")
    print(f"  Online Resource 1: {page_count(required_pdfs[1])} pages")
    print("  cover letter: 1 page")
    print("  figures: 6 numbered vector PDFs")
    print("  AI-use disclosure: one intentional human-authored placeholder")


if __name__ == "__main__":
    main()
