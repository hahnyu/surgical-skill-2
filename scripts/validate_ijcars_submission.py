#!/usr/bin/env python3
"""Validate corrected draft artifacts; --final also enforces human completion."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / 'submission/ijcars'
OUTPUT = ROOT / 'output/pdf'
BUILD = ROOT / 'tmp/pdfs/ijcars-build'
CORRECTIONS = ROOT / 'results/corrections/2026-11-16'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def command_text(*command):
    return subprocess.check_output(command, text=True)


def words(text):
    return len(re.findall(r"\b[\w'-]+\b", text))


def read_csv(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--final', action='store_true', help='Reject all outstanding human confirmations')
    args = parser.parse_args()
    names = ['ijcars_manuscript.pdf', 'ESM_1.pdf', 'ijcars_cover_letter.pdf']
    texts = {}
    for name in names:
        path = OUTPUT / name
        require(path.is_file() and path.stat().st_size > 0, f'Missing {path}')
        text = command_text('pdftotext', str(path), '-')
        require(not re.search(r'(?i)\bnan\b|\?\?|\{=latex\}|\\nolinkurl|```', text), f'Invalid rendering in {name}')
        texts[name] = text
    manuscript, supplement, cover = (texts[name] for name in names)
    require(3000 <= words(manuscript) <= 5000, f'Inclusive manuscript length: {words(manuscript)}')
    metadata = json.loads((SUBMISSION / 'build_metadata.json').read_text())
    require(words(manuscript) == metadata['inclusive_word_count'], 'Word count is stale')
    require(f"Total word count: {words(manuscript):,}" in manuscript, 'Displayed count is stale')
    abstract = manuscript.split('Keywords:', 1)[0].split('Purpose:', 1)[1]
    require(200 <= words(abstract) <= 250, f'Abstract length: {words(abstract)}')
    for name in ['Hamilton Jeong', 'Zaid Elnasser', 'Laurienne Jeong', 'Suélia de Siqueira Rodrigues Fleury Rosa']:
        require(name in manuscript and name in supplement, f'Missing author {name}')
    original_supplement = re.split(r'S16\.\s+Matched', supplement, maxsplit=1)[0]
    for text in [manuscript, original_supplement]:
        require('0.0196' not in text and '0.004975' not in text, 'Withdrawn p-value survives')
        require('0.153' in text and '0.214' in text and '0.043' in text, 'Corrected intervals missing')
    require('did not require further Cornell' not in manuscript + cover, 'Unsupported ethics assertion')
    require('The authors received no funding for this work.' in manuscript, 'Funding declaration missing')
    require('The authors declare no financial or non-financial competing interests.' in manuscript, 'Conflict declaration missing')
    refs = manuscript.rsplit('References', 1)[1]
    source = (SUBMISSION / 'manuscript.tex').read_text()
    cited = {key.strip() for group in re.findall(r'\\cite\w*\{([^}]+)\}', source) for key in group.split(',')}
    require(len(re.findall(r'\[\d+\]', refs)) == len(cited), 'Numbered bibliography/citation mismatch')
    for doi in ['10.5281/zenodo.7100542', '10.17617/3.CYSIAP', '10.17617/3.JK4ANF']:
        require(doi in refs.replace('\n', ''), f'Missing displayed dataset DOI {doi}')
    for number in range(1, 7):
        require((SUBMISSION / f'figures/Fig{number}.pdf').is_file(), f'Missing Figure {number}')
        require(manuscript.count(f'Figure {number}') >= 2, f'Figure {number} lacks citation/caption')
    for number in range(1, 6):
        require(manuscript.count(f'Table {number}') >= 2, f'Table {number} lacks citation/caption')
    require('Pages:           1' in command_text('pdfinfo', str(OUTPUT / names[2])), 'Cover letter must fit one page')
    require('a4345fc8cdcb50b90e286914ff6dec8ec1c7373e248f60a260c4eaf11f0d9bc3' in supplement.replace('\n', ''), 'Original lock hash missing')
    for stem in ['manuscript', 'supplement', 'cover_letter']:
        log = BUILD / stem / f'{stem}.log'
        require(log.is_file(), f'Build log missing: {log}')
        require(not re.search(r'Overfull|undefined|Undefined|LaTeX Warning|Package natbib Warning', log.read_text()), f'Material LaTeX warning: {log}')
    # Independent consistency checks tie corrected figures to the estimands.
    skill = read_csv(ROOT / 'results/metrics/phase4_skill_performance.csv')
    effects = read_csv(ROOT / 'results/locked/phase5_effect_summaries.csv')
    for row in read_csv(CORRECTIONS / 'figure6_source.csv'):
        if row['panel'] == 'same_participant_skill':
            original = next(r for r in skill if r['task'] == row['task'] and r['intervention'] == row['candidate'] and r['model'] == 'skill_logistic')
            require(float(row['estimate']) == float(original['participant_average_accuracy']), 'Figure 6 uses wrong weighting')
        else:
            original = next(r for r in effects if r['task'] == row['task'] and r['endpoint'] == 'held_task_effect_seed_average' and r['candidate'] == row['candidate'] and r['metric'] == row['metric'])
            for key in ['estimate', 'ci_low', 'ci_high']:
                require(float(row[key]) == float(original[key]), f'Figure 6/Table 5 mismatch: {key}')
    matched = read_csv(CORRECTIONS / 'identity_matched_null.csv')
    require(len(matched) == 10, 'Incomplete fixed-C diagnostic')
    require('S16.' in supplement and '0.01961' in supplement, 'Matched diagnostic missing from supplement')
    for row in matched:
        require(float(row['C']) == 1 and int(row['permutations']) == 50, 'Wrong matched pipeline')
        require(abs(float(row['empirical_p_value']) - 1/51) < 1e-12, 'Matched p-value mismatch')
    matched_manifest = json.loads((CORRECTIONS / 'matched_identity_manifest.json').read_text())
    aggregate_path = 'results/corrections/2026-11-16/identity_matched_null.csv'
    require(hashlib.sha256((ROOT / aggregate_path).read_bytes()).hexdigest() == matched_manifest['outputs'][aggregate_path], 'Matched diagnostic hash mismatch')
    analysis = json.loads((CORRECTIONS / 'analysis_manifest.json').read_text())
    for category in ['inputs', 'outputs']:
        for path, expected in analysis[category].items():
            require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, f'Correction hash mismatch: {path}')
    package = json.loads((SUBMISSION / 'package_manifest.json').read_text())
    for path, expected in package.items():
        require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, f'Package hash mismatch: {path}')
    confirmations = json.loads((SUBMISSION / 'author_confirmations.json').read_text())
    pending = [key for key, value in confirmations.items() if value is not True]
    placeholders = ['AUTHOR TO COMPLETE BEFORE SUBMISSION', 'PENDING AUTHOR CONFIRMATION', 'AUTHOR CONFIRMATION REQUIRED', 'PENDING RELEASE']
    if args.final:
        require(not pending, 'Final submission blocked by: ' + ', '.join(pending))
        require(not any(marker in manuscript + cover for marker in placeholders), 'Replace draft placeholders before final submission')
    else:
        require(manuscript.count('AUTHOR TO COMPLETE BEFORE SUBMISSION') <= 1, 'Repeated AI placeholder')
    print(f'Corrected draft validation passed: {words(manuscript)} words; {len(cited)} numbered references; 6 figures')
    print('Human confirmations pending: ' + (', '.join(pending) or 'none'))


if __name__ == '__main__':
    main()
