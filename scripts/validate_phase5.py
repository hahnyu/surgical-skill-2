#!/usr/bin/env python3
"""Validate the Phase 5 locked-analysis acceptance gate."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    config = yaml.safe_load((ROOT / "configs" / "experiments" / "phase5_locked.yaml").read_text())
    manifest = pd.read_csv(ROOT / "data" / "manifests" / "phase5_artifacts.csv")
    assert not manifest.empty
    assert not manifest["path"].duplicated().any()
    for row in manifest.itertuples():
        path = ROOT / row.path
        assert path.exists(), path
        assert sha256(path) == row.sha256, path
    assert len(manifest.loc[manifest["kind"] == "locked_private_prediction_input"]) == 12
    bootstrap = pd.read_parquet(ROOT / "results" / "locked" / "phase5_bootstrap_replicates.parquet")
    assert set(bootstrap["endpoint"]) == {
        "protocol_gap", "task_effect", "held_task_effect_seed_average",
        "identity_effect", "skill_effect",
    }
    assert bootstrap.groupby(["endpoint"] + [c for c in ["dataset", "task"] if c in bootstrap]).size().min() >= config["participant_bootstrap_replicates"]
    effects = pd.read_csv(ROOT / "results" / "locked" / "phase5_effect_summaries.csv")
    primary = effects.loc[(effects["endpoint"] == "task_effect") & (effects["candidate"] == "I3_identity_subspace") & (effects["protocol"] == "held_out_participant")]
    assert len(primary) == 7
    figures = sorted((ROOT / "results" / "figures").glob("phase5_figure*.svg"))
    sources = sorted((ROOT / "results" / "figures" / "source_data").glob("phase5_figure*_source.csv"))
    tables = sorted((ROOT / "results" / "tables").glob("phase5_table*.csv"))
    assert len(figures) == 6 and len(sources) == 6 and len(tables) == 5
    for path in figures:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("<svg") and text.rstrip().endswith("</svg>")
    report = (ROOT / "reports" / "final_results.md").read_text(encoding="utf-8")
    assert "I3 identity-subspace removal" in report
    assert "seven eligible dataset/task outcomes" in report
    deviations = (ROOT / "docs" / "DEVIATIONS.md").read_text(encoding="utf-8")
    assert "Phase 5" in deviations
    print("Phase 5 validation passed: hashes, resampling, figures, tables, report, and deviations checked")


if __name__ == "__main__":
    main()
