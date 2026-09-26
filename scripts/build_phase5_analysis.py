#!/usr/bin/env python3
"""Build the locked Phase 5 analysis from exact saved OOF predictions."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent


CONFIG_PATH = ROOT / "configs" / "experiments" / "phase5_locked.yaml"
PRIVATE = ROOT / "results" / "predictions" / "private"
LOCKED = ROOT / "results" / "locked"
FIGURES = ROOT / "results" / "figures"
FIGURE_DATA = FIGURES / "source_data"
TABLES = ROOT / "results" / "tables"
REPORT_TABLES = ROOT / "reports" / "tables"


def stable_seed(*parts: object) -> int:
    payload = "\0".join(str(part) for part in parts).encode()
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def config_sha256(config: dict) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.12g", na_rep="NA", lineterminator="\n")


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False, compression="zstd")


def balanced_accuracy(truth: pd.Series, prediction: pd.Series) -> float:
    truth = truth.astype(str)
    prediction = prediction.astype(str)
    recalls = [float((prediction.loc[truth == label] == label).mean()) for label in sorted(truth.unique())]
    return float(np.mean(recalls))


def verify_private_inputs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for manifest_name in ["phase3_artifacts.csv", "phase4_artifacts.csv"]:
        manifest = pd.read_csv(ROOT / "data" / "manifests" / manifest_name)
        for record in manifest.loc[manifest["kind"] == "private_oof_predictions"].to_dict("records"):
            path = ROOT / str(record["path"])
            if not path.exists():
                raise FileNotFoundError(f"missing locked prediction file: {path}")
            actual = sha256(path)
            if actual != record["sha256"]:
                raise ValueError(f"prediction hash mismatch: {path}")
            frame = pd.read_parquet(path)
            if len(frame) != int(record["rows"]):
                raise ValueError(f"prediction row mismatch: {path}")
            rows.append({
                "phase_manifest": manifest_name,
                "path": str(path.relative_to(ROOT)),
                "rows": len(frame),
                "sha256": actual,
                "config_sha256": record["config_sha256"],
                "generating_commits": record.get("analysis_commit", record.get("analysis_commits")),
            })
    return pd.DataFrame(rows).sort_values("path").reset_index(drop=True)


def participant_mean(frame: pd.DataFrame, value: str) -> pd.DataFrame:
    keys = [column for column in frame.columns if column != value]
    return frame.groupby(keys, dropna=False, sort=True)[value].mean().reset_index()


def outer_training_sd(frame: pd.DataFrame) -> pd.Series:
    """Return one target SD per row, excluding the row's complete outer fold."""
    keys = ["dataset", "task", "protocol"]
    unique = frame[keys + ["test_fold", "trial_key", "y_true"]].drop_duplicates()
    mapping: dict[tuple[str, str, str, str], float] = {}
    for group_key, group in unique.groupby(keys, sort=True):
        for fold in sorted(group["test_fold"].astype(str).unique()):
            train = group.loc[group["test_fold"].astype(str) != fold, "y_true"].astype(float)
            value = float(train.std(ddof=1))
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"invalid training target SD for {group_key}, {fold}: {value}")
            mapping[(*group_key, fold)] = value
    lookup = [mapping[(row.dataset, row.task, row.protocol, str(row.test_fold))] for row in frame.itertuples()]
    return pd.Series(lookup, index=frame.index, dtype=float)


def bootstrap_rows(
    values: pd.DataFrame,
    group_cols: list[str],
    value_col: str,
    endpoint: str,
    replicates: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    distributions: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    for group_key, group in values.groupby(group_cols, sort=True, dropna=False):
        group_key = group_key if isinstance(group_key, tuple) else (group_key,)
        participant_values = group.sort_values("participant_key")[value_col].astype(float).to_numpy()
        rng = np.random.default_rng(stable_seed(seed, endpoint, *group_key))
        indices = rng.integers(0, len(participant_values), size=(replicates, len(participant_values)))
        estimates = participant_values[indices].mean(axis=1)
        labels = dict(zip(group_cols, group_key, strict=True))
        summaries.append({
            "endpoint": endpoint,
            **labels,
            "estimate": float(participant_values.mean()),
            "ci_low": float(np.quantile(estimates, 0.025)),
            "ci_high": float(np.quantile(estimates, 0.975)),
            "participants": len(participant_values),
            "replicates": replicates,
        })
        distributions.extend(
            {"endpoint": endpoint, **labels, "replicate": index, "estimate": float(value)}
            for index, value in enumerate(estimates)
        )
    return pd.DataFrame(summaries), pd.DataFrame(distributions)


def leave_one_rows(values: pd.DataFrame, group_cols: list[str], value_col: str, endpoint: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for group_key, group in values.groupby(group_cols, sort=True, dropna=False):
        group_key = group_key if isinstance(group_key, tuple) else (group_key,)
        labels = dict(zip(group_cols, group_key, strict=True))
        full = float(group[value_col].mean())
        for participant in sorted(group["participant_key"].astype(str).unique()):
            retained = group.loc[group["participant_key"].astype(str) != participant, value_col]
            rows.append({
                "endpoint": endpoint,
                **labels,
                "omitted_participant": participant,
                "full_estimate": full,
                "leave_one_out_estimate": float(retained.mean()),
                "change_from_full": float(retained.mean() - full),
                "participants_retained": len(retained),
            })
    return pd.DataFrame(rows)


def build_protocol_gap(performance: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ridge = performance.loc[
        (performance["model"] == "ridge") & (performance["target_name"] != "self_declared_skill")
    ].copy()
    ridge["training_target_sd"] = outer_training_sd(ridge)
    ridge["standardized_absolute_error"] = (
        np.abs(ridge["y_true"].astype(float) - ridge["y_pred"].astype(float)) / ridge["training_target_sd"]
    )
    join = ["dataset", "task", "target_name", "participant_key", "trial_key", "seed"]
    wide = ridge.pivot(index=join, columns="protocol", values="standardized_absolute_error").reset_index()
    wide["value"] = wide["held_out_participant"] - wide["same_participant"]
    participant = wide.groupby(
        ["dataset", "task", "target_name", "participant_key"], sort=True
    )["value"].mean().reset_index()
    participant["metric"] = "held_minus_same_standardized_mae"
    return participant, ridge


def build_task_effects(linear_task: pd.DataFrame, adversarial_task: pd.DataFrame) -> pd.DataFrame:
    comparisons = [
        (linear_task, "I1_duration_removed", "I0_unsuppressed"),
        (linear_task, "I2_duration_residualized", "I0_unsuppressed"),
        (linear_task, "I3_identity_subspace", "I0_unsuppressed"),
        (linear_task, "random_projection", "I0_unsuppressed"),
        (adversarial_task, "I4_adversarial", "I4_capacity_lambda0"),
        (adversarial_task, "I4_shuffled_identity", "I4_capacity_lambda0"),
    ]
    output = []
    for frame, candidate, baseline in comparisons:
        selected = frame.loc[frame["intervention"].isin([candidate, baseline])].copy()
        selected["training_target_sd"] = outer_training_sd(selected)
        keys = [
            "dataset", "task", "protocol", "target_name", "seed", "participant_key",
            "trial_key", "test_fold", "training_target_sd",
        ]
        wide = selected.pivot(index=keys, columns="intervention", values="y_pred").reset_index()
        truth = selected.loc[selected["intervention"] == baseline, keys + ["y_true"]]
        wide = wide.merge(truth, on=keys, validate="one_to_one")
        wide["value"] = (
            np.abs(wide["y_true"].astype(float) - wide[candidate].astype(float))
            - np.abs(wide["y_true"].astype(float) - wide[baseline].astype(float))
        ) / wide["training_target_sd"]
        result = wide.groupby(
            ["dataset", "task", "protocol", "target_name", "seed", "participant_key"], sort=True
        )["value"].mean().reset_index()
        result["candidate"] = candidate
        result["baseline"] = baseline
        result["metric"] = "standardized_mae_difference"
        output.append(result)
    return pd.concat(output, ignore_index=True)


def build_identity_effects(linear: pd.DataFrame, adversarial: pd.DataFrame) -> pd.DataFrame:
    comparisons = [
        (linear, "I1_duration_removed", "I0_unsuppressed"),
        (linear, "I2_duration_residualized", "I0_unsuppressed"),
        (linear, "I3_identity_subspace", "I0_unsuppressed"),
        (linear, "random_projection", "I0_unsuppressed"),
        (adversarial, "I4_adversarial", "I4_capacity_lambda0"),
        (adversarial, "I4_shuffled_identity", "I4_capacity_lambda0"),
    ]
    output = []
    for frame, candidate, baseline in comparisons:
        selected = frame.loc[frame["intervention"].isin([candidate, baseline])]
        keys = ["dataset", "task", "model", "seed", "participant_key", "trial_key"]
        wide = selected.pivot(index=keys, columns="intervention", values="y_pred").reset_index()
        truth = selected.loc[selected["intervention"] == baseline, keys + ["y_true"]]
        wide = wide.merge(truth, on=keys, validate="one_to_one")
        wide["value"] = (
            (wide[candidate].astype(str) == wide["y_true"].astype(str)).astype(float)
            - (wide[baseline].astype(str) == wide["y_true"].astype(str)).astype(float)
        )
        result = wide.groupby(
            ["dataset", "task", "model", "seed", "participant_key"], sort=True
        )["value"].mean().reset_index()
        result["candidate"] = candidate
        result["baseline"] = baseline
        result["metric"] = "participant_accuracy_difference"
        output.append(result)
    return pd.concat(output, ignore_index=True)


def build_skill_effects(skill: pd.DataFrame) -> pd.DataFrame:
    output = []
    for candidate, baseline in [
        ("I1_duration_removed", "I0_unsuppressed"),
        ("I2_duration_residualized", "I0_unsuppressed"),
        ("I3_identity_subspace", "I0_unsuppressed"),
        ("random_projection", "I0_unsuppressed"),
        ("I4_adversarial", "I4_capacity_lambda0"),
    ]:
        selected = skill.loc[skill["intervention"].isin([candidate, baseline])]
        if selected.empty:
            continue
        keys = ["dataset", "task", "model", "seed", "participant_key", "trial_key"]
        wide = selected.pivot(index=keys, columns="intervention", values="y_pred").reset_index()
        truth = selected.loc[selected["intervention"] == baseline, keys + ["y_true"]]
        wide = wide.merge(truth, on=keys, validate="one_to_one")
        wide["value"] = (
            (wide[candidate].astype(str) == wide["y_true"].astype(str)).astype(float)
            - (wide[baseline].astype(str) == wide["y_true"].astype(str)).astype(float)
        )
        result = wide.groupby(
            ["dataset", "task", "model", "seed", "participant_key"], sort=True
        )["value"].mean().reset_index()
        result["candidate"] = candidate
        result["baseline"] = baseline
        result["metric"] = "skill_accuracy_difference"
        output.append(result)
    return pd.concat(output, ignore_index=True)


def esc(value: object) -> str:
    return html.escape(str(value))


def svg_start(width: int, height: int, title: str, subtitle: str = "") -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#18212b}.title{font-size:25px;font-weight:700}.sub{font-size:13px;fill:#52606d}.label{font-size:13px}.small{font-size:11px;fill:#52606d}.axis{stroke:#8b98a5;stroke-width:1}.grid{stroke:#dfe4e8;stroke-width:1}.zero{stroke:#273746;stroke-width:1.5;stroke-dasharray:5 4}</style>',
        f'<text x="36" y="38" class="title">{esc(title)}</text>',
        f'<text x="36" y="61" class="sub">{esc(subtitle)}</text>',
    ]


def save_svg(path: Path, parts: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts + ["</svg>"]) + "\n", encoding="utf-8")


def figure_schematic(source: pd.DataFrame) -> None:
    parts = svg_start(1200, 690, "Study design", "Repeated trials, paired protocols, identity interventions, and two endpoint families")
    colors = {"JIGSAWS": "#2a6f97", "ROSMA": "#2a9d8f", "BGU-PatCut": "#e76f51", "BGU-SKILLS": "#8d6ab8"}
    x_positions = [55, 255, 455, 655]
    for x, row in zip(x_positions, source.itertuples(), strict=True):
        color = colors[row.dataset]
        parts += [
            f'<rect x="{x}" y="105" width="165" height="115" rx="12" fill="{color}" opacity="0.13" stroke="{color}" stroke-width="2"/>',
            f'<text x="{x+14}" y="137" class="label" font-weight="700">{esc(row.dataset)}</text>',
            f'<text x="{x+14}" y="162" class="small">{esc(row.role)}</text>',
            f'<text x="{x+14}" y="184" class="small">n={row.participants}; trials={row.trials}</text>',
            f'<text x="{x+14}" y="204" class="small">{esc(row.target)}</text>',
        ]
    parts += [
        '<path d="M820 162 H895" stroke="#52606d" stroke-width="2" marker-end="url(#arrow)"/>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#52606d"/></marker></defs>',
        '<rect x="900" y="105" width="245" height="115" rx="12" fill="#eef2f5" stroke="#52606d"/>',
        '<text x="920" y="137" class="label" font-weight="700">Harmonized kinematics</text>',
        '<text x="920" y="162" class="small">Fold-fitted preprocessing</text>',
        '<text x="920" y="184" class="small">No outer-test participant leakage</text>',
        '<text x="920" y="204" class="small">Complete trials stay intact</text>',
    ]
    blocks = [
        (75, 305, "Same-participant", "Repetition-held-out; participant retained"),
        (375, 305, "Held-out-participant", "Complete participant absent from fitting"),
        (675, 305, "I0–I4 + controls", "Duration, identity subspace, adversarial"),
        (975, 305, "Frozen representation", "Fresh linear and nonlinear probes"),
    ]
    for x, y, label, note in blocks:
        parts += [
            f'<rect x="{x}" y="{y}" width="220" height="92" rx="12" fill="#ffffff" stroke="#2a6f97" stroke-width="2"/>',
            f'<text x="{x+16}" y="{y+34}" class="label" font-weight="700">{esc(label)}</text>',
            f'<text x="{x+16}" y="{y+59}" class="small">{esc(note)}</text>',
        ]
        if x < 975:
            parts.append(f'<path d="M{x+220} {y+46} H{x+292}" stroke="#52606d" stroke-width="2" marker-end="url(#arrow)"/>')
    parts += [
        '<path d="M1085 397 V475" stroke="#52606d" stroke-width="2" marker-end="url(#arrow)"/>',
        '<rect x="690" y="490" width="220" height="105" rx="12" fill="#e8f3f8" stroke="#2a6f97" stroke-width="2"/>',
        '<text x="708" y="525" class="label" font-weight="700">Outcome endpoint</text>',
        '<text x="708" y="551" class="small">Participant-average MAE</text>',
        '<text x="708" y="574" class="small">Same vs held; suppression vs I0</text>',
        '<rect x="960" y="490" width="220" height="105" rx="12" fill="#e8f5f1" stroke="#2a9d8f" stroke-width="2"/>',
        '<text x="978" y="525" class="label" font-weight="700">Identity endpoint</text>',
        '<text x="978" y="551" class="small">Fresh-probe balanced accuracy</text>',
        '<text x="978" y="574" class="small">Participant-level permutation null</text>',
        '<text x="55" y="650" class="sub">All uncertainty resamples participants; predictions are out of fold and linked to immutable configuration hashes.</text>',
    ]
    save_svg(FIGURES / "phase5_figure1_study_schematic.svg", parts)


def figure_forest(source: pd.DataFrame, path: Path, title: str, subtitle: str, x_label: str) -> None:
    source = source.reset_index(drop=True)
    width, row_h = 1100, 34
    height = 145 + row_h * len(source)
    parts = svg_start(width, height, title, subtitle)
    raw_low = float(min(source["ci_low"].min(), 0))
    raw_high = float(max(source["ci_high"].max(), 0))
    nonzero = np.abs(source[["estimate", "ci_low", "ci_high"]].to_numpy()).ravel()
    nonzero = nonzero[nonzero > 1e-9]
    use_asinh = bool(len(nonzero) and nonzero.max() / np.median(nonzero) > 20)
    transform = np.arcsinh if use_asinh else lambda value: value
    inverse = np.sinh if use_asinh else lambda value: value
    low = float(transform(raw_low))
    high = float(transform(raw_high))
    pad = max((high - low) * 0.08, 0.01)
    low, high = low - pad, high + pad
    left, right, top = 360, 1040, 93
    scale = lambda value: left + (float(transform(value)) - low) / (high - low) * (right - left)
    parts += [
        f'<line x1="{scale(0)}" y1="{top-12}" x2="{scale(0)}" y2="{top+row_h*len(source)}" class="zero"/>',
        f'<line x1="{left}" y1="{top+row_h*len(source)+8}" x2="{right}" y2="{top+row_h*len(source)+8}" class="axis"/>',
    ]
    for index, row in source.iterrows():
        y = top + index * row_h
        label = row.get("label", f"{row['dataset']} · {row['task']}")
        parts += [
            f'<text x="36" y="{y+5}" class="label">{esc(label)}</text>',
            f'<line x1="{scale(row.ci_low)}" y1="{y}" x2="{scale(row.ci_high)}" y2="{y}" stroke="#2a6f97" stroke-width="3"/>',
            f'<circle cx="{scale(row.estimate)}" cy="{y}" r="5" fill="#e76f51"/>',
            f'<text x="{right+10}" y="{y+5}" class="small">{row.estimate:.2f} [{row.ci_low:.2f}, {row.ci_high:.2f}]</text>',
        ]
    for transformed_value in np.linspace(low, high, 7):
        value = float(inverse(transformed_value))
        x = left + (transformed_value - low) / (high - low) * (right - left)
        label = f"{value:.1f}" if abs(value) >= 1 else f"{value:.2f}"
        parts += [f'<line x1="{x}" y1="{top+row_h*len(source)+8}" x2="{x}" y2="{top+row_h*len(source)+14}" class="axis"/>', f'<text x="{x}" y="{top+row_h*len(source)+31}" class="small" text-anchor="middle">{label}</text>']
    display_note = " (asinh display scale)" if use_asinh else ""
    parts.append(f'<text x="{(left+right)/2}" y="{height-10}" class="small" text-anchor="middle">{esc(x_label + display_note)}</text>')
    save_svg(path, parts)


def figure_identity_permutation(source: pd.DataFrame) -> None:
    width, height = 1050, 520
    parts = svg_start(width, height, "Identity-compatible skill lookup survives participant-wise permutation", "JIGSAWS same-participant accuracy; participant-wise permutation preserves person labels")
    left, right, top, bottom = 95, 1010, 105, 420
    y = lambda value: bottom - float(value) * (bottom - top)
    for tick in np.linspace(0, 1, 6):
        parts += [f'<line x1="{left}" y1="{y(tick)}" x2="{right}" y2="{y(tick)}" class="grid"/>', f'<text x="{left-12}" y="{y(tick)+4}" class="small" text-anchor="end">{tick:.1f}</text>']
    colors = {"observed": "#e76f51", "participant_permutation": "#2a6f97", "record_permutation": "#2a9d8f"}
    labels = {"observed": "Observed", "participant_permutation": "Participant-wise null", "record_permutation": "Record-wise null"}
    tasks = source["task"].drop_duplicates().tolist()
    for ti, task in enumerate(tasks):
        group = source.loc[source["task"] == task]
        center = 225 + ti * 300
        for ji, kind in enumerate(["observed", "participant_permutation", "record_permutation"]):
            row = group.loc[group["series"] == kind].iloc[0]
            x = center + (ji - 1) * 58
            parts += [f'<line x1="{x}" y1="{y(row.q025)}" x2="{x}" y2="{y(row.q975)}" stroke="{colors[kind]}" stroke-width="4"/>', f'<circle cx="{x}" cy="{y(row.estimate)}" r="7" fill="{colors[kind]}"/>']
        parts.append(f'<text x="{center}" y="455" class="label" text-anchor="middle">{esc(task)}</text>')
    for index, kind in enumerate(colors):
        x = 160 + index * 265
        parts += [f'<circle cx="{x}" cy="492" r="6" fill="{colors[kind]}"/>', f'<text x="{x+12}" y="496" class="small">{labels[kind]}</text>']
    save_svg(FIGURES / "phase5_figure3_identity_permutation.svg", parts)


def figure_utility_identity(source: pd.DataFrame) -> None:
    width, height = 920, 650
    parts = svg_start(width, height, "Utility–identity plane", "Lower is better on both axes; task error is averaged after within-task training-SD standardization")
    left, right, top, bottom = 105, 855, 100, 570
    xmin, xmax = 0, max(1.0, float(source["nonlinear_identity_balanced_accuracy"].max()) * 1.08)
    ymin, ymax = 0, float(source["held_standardized_mae"].max()) * 1.12
    x = lambda value: left + (float(value) - xmin) / (xmax - xmin) * (right - left)
    y = lambda value: bottom - (float(value) - ymin) / (ymax - ymin) * (bottom - top)
    for tick in np.linspace(0, xmax, 6):
        parts += [f'<line x1="{x(tick)}" y1="{top}" x2="{x(tick)}" y2="{bottom}" class="grid"/>', f'<text x="{x(tick)}" y="{bottom+24}" class="small" text-anchor="middle">{tick:.2f}</text>']
    for tick in np.linspace(0, ymax, 6):
        parts += [f'<line x1="{left}" y1="{y(tick)}" x2="{right}" y2="{y(tick)}" class="grid"/>', f'<text x="{left-12}" y="{y(tick)+4}" class="small" text-anchor="end">{tick:.2f}</text>']
    colors = ["#264653", "#457b9d", "#2a9d8f", "#e76f51", "#8d6ab8", "#f4a261"]
    for (index, row), color in zip(source.iterrows(), colors, strict=False):
        parts += [f'<circle cx="{x(row.nonlinear_identity_balanced_accuracy)}" cy="{y(row.held_standardized_mae)}" r="9" fill="{color}" stroke="#fff" stroke-width="2"/>', f'<text x="{x(row.nonlinear_identity_balanced_accuracy)+12}" y="{y(row.held_standardized_mae)-10}" class="label" font-weight="700">{esc(row.intervention_short)}</text>']
    parts += [f'<text x="{(left+right)/2}" y="625" class="label" text-anchor="middle">Nonlinear identity-probe balanced accuracy</text>', f'<text x="28" y="{(top+bottom)/2}" class="label" text-anchor="middle" transform="rotate(-90 28 {(top+bottom)/2})">Held-out participant standardized MAE</text>']
    save_svg(FIGURES / "phase5_figure4_utility_identity.svg", parts)


def figure_jigsaws(source: pd.DataFrame) -> None:
    width, height = 1150, 570
    parts = svg_start(width, height, "JIGSAWS mechanistic panel", "Identity suppression reduced fresh-probe recovery without a consistent new-user or same-user skill benefit")
    panels = [(35, "A  Same-user skill accuracy"), (405, "B  Identity-probe accuracy"), (775, "C  Held-out GRS effect")]
    for x0, title in panels:
        parts += [f'<rect x="{x0}" y="90" width="340" height="410" rx="10" fill="#fff" stroke="#d6dde3"/>', f'<text x="{x0+18}" y="122" class="label" font-weight="700">{esc(title)}</text>']
    panel_a = source.loc[source["panel"] == "same_user_skill"].reset_index(drop=True)
    for index, row in panel_a.iterrows():
        x = 85 + (index % len(panel_a)) * 85
        h = float(row.estimate) * 270
        parts += [f'<rect x="{x}" y="{440-h}" width="48" height="{h}" fill="#2a6f97" opacity="0.8"/>', f'<text x="{x+24}" y="465" class="small" text-anchor="middle">{esc(row.label)}</text>']
    panel_b = source.loc[source["panel"] == "identity_probe"].reset_index(drop=True)
    for index, row in panel_b.iterrows():
        x = 465 + index * 115
        h = float(row.estimate) * 270
        parts += [f'<rect x="{x}" y="{440-h}" width="58" height="{h}" fill="#2a9d8f" opacity="0.85"/>', f'<text x="{x+29}" y="465" class="small" text-anchor="middle">{esc(row.label)}</text>']
    panel_c = source.loc[source["panel"] == "held_grs_effect"].reset_index(drop=True)
    zero_x = 945
    parts.append(f'<line x1="{zero_x}" y1="150" x2="{zero_x}" y2="450" class="zero"/>')
    max_abs = max(abs(panel_c["ci_low"]).max(), abs(panel_c["ci_high"]).max(), 0.1)
    sx = lambda value: zero_x + float(value) / (max_abs * 1.15) * 135
    for index, row in panel_c.iterrows():
        y0 = 205 + index * 90
        parts += [f'<text x="795" y="{y0+5}" class="small">{esc(row.label)}</text>', f'<line x1="{sx(row.ci_low)}" y1="{y0}" x2="{sx(row.ci_high)}" y2="{y0}" stroke="#e76f51" stroke-width="4"/>', f'<circle cx="{sx(row.estimate)}" cy="{y0}" r="6" fill="#e76f51"/>']
    parts += ['<text x="205" y="535" class="small" text-anchor="middle">Accuracy</text>', '<text x="575" y="535" class="small" text-anchor="middle">Fresh nonlinear-probe accuracy</text>', '<text x="945" y="535" class="small" text-anchor="middle">Standardized MAE change; negative favors I3</text>']
    save_svg(FIGURES / "phase5_figure6_jigsaws_mechanism.svg", parts)


def build_tables(
    features: pd.DataFrame,
    held_task_summary: pd.DataFrame,
    identity_participant: pd.DataFrame,
    replicates: int,
    seed: int,
) -> dict[str, pd.DataFrame]:
    descriptive = pd.read_csv(REPORT_TABLES / "phase2_dataset_descriptives.csv")
    availability = pd.read_csv(REPORT_TABLES / "availability_license.csv")
    provenance = pd.read_csv(REPORT_TABLES / "target_provenance.csv")
    roles = {
        "JIGSAWS": "anchor expert-rated skill and mechanism",
        "ROSMA": "external objective-error outcome",
        "BGU-PatCut": "external image-derived accuracy outcome",
        "BGU-SKILLS": "identity and longitudinal robustness only",
    }
    primary_targets = provenance.loc[
        (provenance["primary_eligibility"] == "eligible")
        | (provenance["dataset"] == "BGU-SKILLS")
    ].groupby("dataset", sort=True)["target"].agg(lambda x: "; ".join(x)).rename("eligible_target")
    table1 = descriptive.groupby("dataset", sort=True).agg(
        tasks=("task", lambda x: "; ".join(x)),
        trials=("trials", "sum"),
        participants=("participants", "max"),
    ).reset_index().merge(availability, on="dataset", how="left").merge(primary_targets, on="dataset", how="left")
    table1["included_role"] = table1["dataset"].map(roles)

    metadata = {"dataset", "version", "task", "participant_key", "trial_key", "repetition", "session", "condition", "outcome_name", "outcome_value", "outcome_direction", "source_sha256"}
    feature_cols = [column for column in features.columns if column not in metadata]
    table2_rows = []
    for column in feature_cols:
        row = {"feature": column, "family": column.split("_")[0] if column.startswith(("psm1_", "psm2_")) else "cross_arm_or_time"}
        for dataset in sorted(features["dataset"].unique()):
            row[f"{dataset}_available_share"] = float(features.loc[features["dataset"] == dataset, column].notna().mean())
        row["direct_duration_equivalent"] = column in {"duration_s", "psm1_samples", "psm2_samples"}
        table2_rows.append(row)
    table2 = pd.DataFrame(table2_rows)

    phase3 = pd.read_csv(ROOT / "results" / "metrics" / "phase3_performance.csv")
    table3 = phase3.loc[
        (phase3["target_name"] != "self_declared_skill")
        & phase3["model"].isin(["feature_free_mean", "duration_ridge", "ridge"]),
        ["dataset", "task", "protocol", "target_name", "model", "participants", "trials", "participant_average_metric", "ci_low", "ci_high", "metric_name"],
    ].reset_index(drop=True)

    identity = pd.read_csv(ROOT / "results" / "metrics" / "phase3_identity_probes.csv")
    skill_perm = pd.read_csv(ROOT / "results" / "metrics" / "phase3_skill_permutation_summary.csv")
    id_rows = identity.assign(result_type="identity_probe")
    id_rows = id_rows[["result_type", "dataset", "task", "model", "participants", "balanced_accuracy", "balanced_accuracy_ci_low", "balanced_accuracy_ci_high", "permuted_identity_median_balanced_accuracy", "empirical_p_value"]]
    perm_rows = pd.DataFrame({
        "result_type": "skill_permutation",
        "dataset": "JIGSAWS",
        "task": skill_perm["task"],
        "model": "multinomial_logistic",
        "participants": np.nan,
        "balanced_accuracy": skill_perm["observed_accuracy"],
        "balanced_accuracy_ci_low": np.nan,
        "balanced_accuracy_ci_high": np.nan,
        "permuted_identity_median_balanced_accuracy": skill_perm["participant_permutation_median"],
        "empirical_p_value": skill_perm["empirical_p_participant_not_greater"],
    })
    table4 = pd.concat([id_rows, perm_rows], ignore_index=True)

    ablation = pd.read_csv(ROOT / "results" / "metrics" / "phase4_ablation_log.csv")
    held = held_task_summary.copy()
    held = held.rename(columns={"estimate": "standardized_task_effect", "ci_low": "task_ci_low", "ci_high": "task_ci_high"})
    identity_collapsed = identity_participant.groupby(
        ["dataset", "task", "model", "candidate", "baseline", "participant_key"], sort=True
    )["value"].mean().reset_index()
    probes, _ = bootstrap_rows(
        identity_collapsed, ["dataset", "task", "model", "candidate", "baseline"],
        "value", "identity_effect_seed_average", replicates, seed,
    )
    probes = probes.pivot(index=["dataset", "task", "candidate", "baseline"], columns="model", values="estimate").reset_index()
    table5 = held.merge(probes, on=["dataset", "task", "candidate", "baseline"], how="left").merge(ablation[["candidate", "baseline", "control_role"]], on=["candidate", "baseline"], how="left")
    return {
        "phase5_table1_datasets.csv": table1,
        "phase5_table2_features.csv": table2,
        "phase5_table3_baselines.csv": table3,
        "phase5_table4_identity_permutations.csv": table4,
        "phase5_table5_interventions.csv": table5,
    }


def write_report(protocol_summary: pd.DataFrame, task_summary: pd.DataFrame, identity_summary: pd.DataFrame, skill_summary: pd.DataFrame) -> None:
    primary_task = task_summary.loc[
        (task_summary["candidate"] == "I3_identity_subspace")
        & (task_summary["protocol"] == "held_out_participant")
    ]
    primary_identity = pd.read_csv(ROOT / "results" / "metrics" / "phase4_primary_comparison.csv")
    primary_identity = primary_identity.loc[primary_identity["candidate"] == "I3_identity_subspace"]
    improved = int((primary_task["estimate"] < 0).sum())
    harmed = int((primary_task["estimate"] > 0).sum())
    lines = [
        "# Final locked analysis",
        "",
        "Phase 5 locks the analysis to the exact Phase 3 and Phase 4 out-of-fold prediction artifacts. The single-command runner verifies their SHA-256 hashes before deriving any result, regenerates every table and SVG from source CSVs, and repeats the build to test byte-for-byte determinism.",
        "",
        "## Locked primary decision",
        "",
        "I4 adversarial suppression did not pass the prespecified two-probe verification rule, so I3 identity-subspace removal is the primary comparison with I0. I3 reduced both fresh identity probes:",
        "",
    ]
    for row in primary_identity.itertuples():
        lines.append(f"- {row.probe_model}: balanced-accuracy difference {row.balanced_accuracy_difference:+.3f} (95% participant-bootstrap interval {row.ci_low:+.3f} to {row.ci_high:+.3f}).")
    lines += [
        "",
        "## New-user utility",
        "",
        f"Across the seven eligible dataset/task outcomes, the participant-average held-out-user I3 effect favored suppression in {improved} and favored I0 in {harmed}. Effects are reported task by task because the outcome scales and constructs differ; no pooled grand effect is estimated.",
        "",
        "| Dataset/task | Standardized MAE difference | 95% participant-bootstrap interval |",
        "|---|---:|---:|",
    ]
    for row in primary_task.itertuples():
        lines.append(f"| {row.dataset} / {row.task} | {row.estimate:+.3f} | {row.ci_low:+.3f} to {row.ci_high:+.3f} |")
    lines += [
        "",
        "Negative values favor I3. Standardization divides each paired trial-level absolute-error difference by the target SD calculated without that outer test fold.",
        "ROSMA Pea on a Peg has a heavily zero-inflated error outcome; several outer-training SDs are small, so its standardized estimate and interval are correspondingly large. The raw-scale effect remains available in the Phase 4 tables, and the forest plots use an asinh display scale without changing source values.",
        "",
        "## Protocol and permutation diagnostics",
        "",
        f"The ridge same-user versus held-out-user protocol gap was positive in {int((protocol_summary['estimate'] > 0).sum())} of {len(protocol_summary)} eligible tasks after fold-specific standardization. The JIGSAWS participant-wise label permutation remained substantially more favorable than record-wise permutation in all three tasks, consistent with identity-compatible same-user lookup.",
        "",
        "## Mechanistic interpretation",
        "",
        "The locked results support a narrow conclusion: participant identity is recoverable, targeted linear suppression reduces fresh-probe identity recovery, and that reduction does not consistently improve held-out-participant prediction. Most primary task intervals include zero, and JIGSAWS has only seven or eight participants per task; leave-one-participant results are therefore retained as a first-class sensitivity output.",
        "",
        "## Reproduction",
        "",
        "```bash",
        ".venv/bin/python scripts/run_phase5_locked.py",
        "```",
        "",
        "The command validates Phases 1–4, rebuilds Phase 5 twice, compares output hashes, runs the complete test suite, and applies the Phase 5 acceptance validator.",
    ]
    (ROOT / "reports" / "final_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_manifest(config_hash: str, verified_inputs: pd.DataFrame) -> None:
    output_roots = [LOCKED, FIGURES, TABLES, ROOT / "reports", ROOT / "docs"]
    include_names = {
        "final_results.md", "locked_configuration.md", "DEVIATIONS.md", "search_log.md",
        *[p.name for p in LOCKED.glob("phase5_*.csv")],
        *[p.name for p in LOCKED.glob("phase5_*.parquet")],
        *[p.name for p in FIGURES.glob("phase5_*.svg")],
        *[p.name for p in FIGURE_DATA.glob("phase5_*.csv")],
        *[p.name for p in TABLES.glob("phase5_*.csv")],
    }
    artifacts = []
    for root in output_roots:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name in include_names:
                if path.suffix == ".csv":
                    with path.open("rb") as handle:
                        rows = max(sum(1 for _ in handle) - 1, 0)
                elif path.suffix == ".parquet":
                    rows = len(pd.read_parquet(path))
                else:
                    rows = 1
                artifacts.append({
                    "artifact": path.stem,
                    "path": str(path.relative_to(ROOT)),
                    "kind": "machine_readable_source" if path.suffix in {".csv", ".parquet"} else "figure_or_report",
                    "rows": rows,
                    "sha256": sha256(path),
                    "phase5_config_sha256": config_hash,
                })
    for row in verified_inputs.to_dict("records"):
        artifacts.append({
            "artifact": Path(str(row["path"])).stem,
            "path": row["path"],
            "kind": "locked_private_prediction_input",
            "rows": row["rows"],
            "sha256": row["sha256"],
            "phase5_config_sha256": config_hash,
        })
    frame = pd.DataFrame(artifacts).sort_values(["kind", "path"]).reset_index(drop=True)
    write_csv(ROOT / "data" / "manifests" / "phase5_artifacts.csv", frame)


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config_hash = config_sha256(config)
    replicates = int(config["participant_bootstrap_replicates"])
    seed = int(config["analysis_seed"])
    verified = verify_private_inputs()
    write_csv(LOCKED / "phase5_verified_prediction_inputs.csv", verified)

    performance = pd.read_parquet(PRIVATE / "phase3_performance.parquet")
    linear_task = pd.read_parquet(PRIVATE / "phase4_linear_task.parquet")
    adversarial_task = pd.read_parquet(PRIVATE / "phase4_adversarial_task.parquet")
    linear_probes = pd.read_parquet(PRIVATE / "phase4_linear_probes.parquet")
    adversarial_probes = pd.read_parquet(PRIVATE / "phase4_adversarial_probes.parquet")
    skill = pd.read_parquet(PRIVATE / "phase4_skill.parquet")
    features = pd.read_csv(ROOT / "data" / "processed" / "private" / "phase2_features.csv")

    protocol_participant, standardized_performance = build_protocol_gap(performance)
    task_participant = build_task_effects(linear_task, adversarial_task)
    identity_participant = build_identity_effects(linear_probes, adversarial_probes)
    skill_participant = build_skill_effects(skill)
    write_csv(LOCKED / "phase5_participant_protocol_gap.csv", protocol_participant)
    write_csv(LOCKED / "phase5_participant_task_effects.csv", task_participant)
    write_csv(LOCKED / "phase5_participant_identity_effects.csv", identity_participant)
    write_csv(LOCKED / "phase5_participant_skill_effects.csv", skill_participant)

    protocol_summary, protocol_boot = bootstrap_rows(
        protocol_participant, ["dataset", "task", "target_name", "metric"], "value",
        "protocol_gap", replicates, seed,
    )
    task_summary, task_boot = bootstrap_rows(
        task_participant,
        ["dataset", "task", "protocol", "target_name", "seed", "candidate", "baseline", "metric"],
        "value", "task_effect", replicates, seed,
    )
    held_task_participant = task_participant.loc[
        task_participant["protocol"] == "held_out_participant"
    ].groupby(
        ["dataset", "task", "protocol", "target_name", "candidate", "baseline", "metric", "participant_key"],
        sort=True,
    )["value"].mean().reset_index()
    held_task_summary, held_task_boot = bootstrap_rows(
        held_task_participant,
        ["dataset", "task", "protocol", "target_name", "candidate", "baseline", "metric"],
        "value", "held_task_effect_seed_average", replicates, seed,
    )
    identity_summary, identity_boot = bootstrap_rows(
        identity_participant,
        ["dataset", "task", "model", "seed", "candidate", "baseline", "metric"],
        "value", "identity_effect", replicates, seed,
    )
    skill_summary, skill_boot = bootstrap_rows(
        skill_participant,
        ["dataset", "task", "model", "seed", "candidate", "baseline", "metric"],
        "value", "skill_effect", replicates, seed,
    )
    bootstrap = pd.concat([protocol_boot, task_boot, held_task_boot, identity_boot, skill_boot], ignore_index=True)
    summaries = pd.concat([protocol_summary, task_summary, held_task_summary, identity_summary, skill_summary], ignore_index=True)
    write_parquet(LOCKED / "phase5_bootstrap_replicates.parquet", bootstrap)
    write_csv(LOCKED / "phase5_effect_summaries.csv", summaries)

    leave_one = pd.concat([
        leave_one_rows(protocol_participant, ["dataset", "task", "target_name", "metric"], "value", "protocol_gap"),
        leave_one_rows(task_participant, ["dataset", "task", "protocol", "target_name", "seed", "candidate", "baseline", "metric"], "value", "task_effect"),
        leave_one_rows(identity_participant, ["dataset", "task", "model", "seed", "candidate", "baseline", "metric"], "value", "identity_effect"),
        leave_one_rows(skill_participant, ["dataset", "task", "model", "seed", "candidate", "baseline", "metric"], "value", "skill_effect"),
    ], ignore_index=True)
    write_csv(LOCKED / "phase5_leave_one_participant.csv", leave_one)

    permutation_frames = []
    for name, endpoint in [
        ("phase3_identity_null_distribution.csv", "identity_record_permutation"),
        ("phase3_skill_permutation_distribution.csv", "skill_label_permutation"),
        ("phase3_outcome_null_distribution.csv", "continuous_outcome_record_permutation"),
    ]:
        frame = pd.read_csv(ROOT / "results" / "metrics" / name)
        frame.insert(0, "endpoint", endpoint)
        permutation_frames.append(frame)
    write_csv(LOCKED / "phase5_permutation_outputs.csv", pd.concat(permutation_frames, ignore_index=True))

    fold_rows = []
    for path in sorted((ROOT / "data" / "folds").glob("*.csv")):
        frame = pd.read_csv(path)
        fold_rows.append(frame.groupby(["dataset", "task", "protocol", "test_fold"], sort=True).agg(trials=("trial_key", "nunique"), participants=("participant_key", "nunique")).reset_index())
    write_csv(TABLES / "phase5_supplement_fold_composition.csv", pd.concat(fold_rows, ignore_index=True))
    write_csv(TABLES / "phase5_supplement_hyperparameter_selections.csv", pd.read_csv(ROOT / "results" / "metrics" / "phase4_selection.csv"))
    write_csv(TABLES / "phase5_supplement_missingness.csv", pd.read_csv(REPORT_TABLES / "missingness.csv"))
    write_csv(TABLES / "phase5_supplement_seed_stability.csv", pd.read_csv(ROOT / "results" / "metrics" / "phase4_seed_stability.csv"))
    supplement_index = pd.DataFrame([
        {"planned_item": "full fold composition", "artifact": "phase5_supplement_fold_composition.csv", "status": "complete"},
        {"planned_item": "participant-level results", "artifact": "results/locked/phase5_participant_*.csv", "status": "complete"},
        {"planned_item": "hyperparameter grids and selections", "artifact": "phase5_supplement_hyperparameter_selections.csv; phase3/phase4 YAML", "status": "complete"},
        {"planned_item": "all seeds", "artifact": "phase5_supplement_seed_stability.csv; phase4 YAML", "status": "complete"},
        {"planned_item": "exclusions and missingness", "artifact": "phase5_supplement_missingness.csv", "status": "complete"},
        {"planned_item": "sensitivity to outcome definition", "artifact": "reports/tables/target_provenance.csv", "status": "limited: secondary BGU component outcomes were not modeled in frozen Phase 3-4 predictions"},
        {"planned_item": "leave-one-participant influence", "artifact": "results/locked/phase5_leave_one_participant.csv", "status": "complete"},
        {"planned_item": "duration removal/residualization", "artifact": "phase5_table5_interventions.csv; phase4 YAML", "status": "complete"},
        {"planned_item": "random projection control", "artifact": "phase5_table5_interventions.csv", "status": "complete"},
        {"planned_item": "training curves and convergence", "artifact": "phase5_supplement_seed_stability.csv; phase4 selection records", "status": "limited: epoch-wise losses were not retained; all scheduled fits completed"},
        {"planned_item": "literature search update", "artifact": "docs/literature_search/search_log.md", "status": "complete 2026-09-26"},
    ])
    write_csv(TABLES / "phase5_supplement_index.csv", supplement_index)

    tables = build_tables(features, held_task_summary, identity_participant, replicates, seed)
    for name, frame in tables.items():
        write_csv(TABLES / name, frame)

    schematic_source = pd.DataFrame([
        {"dataset": "JIGSAWS", "participants": 8, "trials": 103, "target": "Expert-rated GRS", "role": "Anchor / mechanism"},
        {"dataset": "ROSMA", "participants": 12, "trials": 206, "target": "Observed task errors", "role": "External outcome"},
        {"dataset": "BGU-PatCut", "participants": 54, "trials": 1254, "target": "Image-derived cutting error", "role": "External outcome"},
        {"dataset": "BGU-SKILLS", "participants": 18, "trials": 938, "target": "No eligible independent target", "role": "Identity robustness"},
    ])
    write_csv(FIGURE_DATA / "phase5_figure1_source.csv", schematic_source)
    figure_schematic(schematic_source)

    protocol_figure = protocol_summary.copy()
    protocol_figure["label"] = protocol_figure["dataset"] + " · " + protocol_figure["task"]
    write_csv(FIGURE_DATA / "phase5_figure2_source.csv", protocol_figure)
    figure_forest(protocol_figure, FIGURES / "phase5_figure2_protocol_gap.svg", "Same-user versus held-out-user protocol gap", "Participant-bootstrap intervals; positive values mean held-out-user error is higher", "Held minus same standardized MAE")

    skill_perm = pd.read_csv(ROOT / "results" / "metrics" / "phase3_skill_permutation_summary.csv")
    permutation_source = []
    for row in skill_perm.itertuples():
        permutation_source += [
            {"task": row.task, "series": "observed", "estimate": row.observed_accuracy, "q025": row.observed_accuracy, "q975": row.observed_accuracy},
            {"task": row.task, "series": "participant_permutation", "estimate": row.participant_permutation_median, "q025": row.participant_permutation_q025, "q975": row.participant_permutation_q975},
            {"task": row.task, "series": "record_permutation", "estimate": row.record_permutation_median, "q025": row.record_permutation_q025, "q975": row.record_permutation_q975},
        ]
    permutation_source = pd.DataFrame(permutation_source)
    write_csv(FIGURE_DATA / "phase5_figure3_source.csv", permutation_source)
    figure_identity_permutation(permutation_source)

    interventions = [
        ("I0_unsuppressed", "I0", linear_task, linear_probes),
        ("I1_duration_removed", "I1", linear_task, linear_probes),
        ("I2_duration_residualized", "I2", linear_task, linear_probes),
        ("I3_identity_subspace", "I3", linear_task, linear_probes),
        ("I4_adversarial", "I4", adversarial_task, adversarial_probes),
        ("random_projection", "Random", linear_task, linear_probes),
    ]
    utility_rows = []
    for intervention, short, task_frame, probe_frame in interventions:
        task_selected = task_frame.loc[(task_frame["intervention"] == intervention) & (task_frame["protocol"] == "held_out_participant")].copy()
        task_selected["training_target_sd"] = outer_training_sd(task_selected)
        task_selected["standardized_absolute_error"] = np.abs(task_selected["y_true"].astype(float) - task_selected["y_pred"].astype(float)) / task_selected["training_target_sd"]
        task_value = task_selected.groupby(
            ["dataset", "task", "seed", "participant_key"], sort=True
        )["standardized_absolute_error"].mean().groupby(level=[0, 1, 2]).mean().mean()
        probe_selected = probe_frame.loc[(probe_frame["intervention"] == intervention) & (probe_frame["model"] == "nonlinear_probe")]
        probe_value = probe_selected.groupby(["dataset", "task", "seed"]).apply(
            lambda x: balanced_accuracy(x["y_true"], x["y_pred"]),
            include_groups=False,
        ).mean()
        utility_rows.append({"intervention": intervention, "intervention_short": short, "held_standardized_mae": float(task_value), "nonlinear_identity_balanced_accuracy": float(probe_value)})
    utility_source = pd.DataFrame(utility_rows)
    write_csv(FIGURE_DATA / "phase5_figure4_source.csv", utility_source)
    figure_utility_identity(utility_source)

    intervention_figure = held_task_summary.loc[
        held_task_summary["candidate"].isin(["I1_duration_removed", "I2_duration_residualized", "I3_identity_subspace", "random_projection", "I4_adversarial"])
    ].copy()
    intervention_figure["label"] = intervention_figure["candidate"].str.replace("_", " ") + " · " + intervention_figure["dataset"] + " · " + intervention_figure["task"]
    write_csv(FIGURE_DATA / "phase5_figure5_source.csv", intervention_figure)
    figure_forest(intervention_figure, FIGURES / "phase5_figure5_intervention_forest.svg", "Held-out-user intervention effects", "Participant-bootstrap intervals; negative values favor the intervention", "Paired standardized MAE difference")

    jigsaws_rows = []
    skill_performance = pd.read_csv(ROOT / "results" / "metrics" / "phase4_skill_performance.csv")
    for intervention, label in [("I0_unsuppressed", "I0"), ("I3_identity_subspace", "I3")]:
        match = skill_performance.loc[(skill_performance["intervention"] == intervention) & (skill_performance["model"] == "multinomial_logistic")]
        jigsaws_rows.append({"panel": "same_user_skill", "label": label, "estimate": match["accuracy"].mean(), "ci_low": np.nan, "ci_high": np.nan})
        probe = pd.read_csv(ROOT / "results" / "metrics" / "phase4_identity_probes.csv")
        probe = probe.loc[(probe["dataset"] == "JIGSAWS") & (probe["intervention"] == intervention) & (probe["model"] == "nonlinear_probe")]
        jigsaws_rows.append({"panel": "identity_probe", "label": label, "estimate": probe["balanced_accuracy"].mean(), "ci_low": np.nan, "ci_high": np.nan})
    jtask = task_summary.loc[(task_summary["dataset"] == "JIGSAWS") & (task_summary["protocol"] == "held_out_participant") & (task_summary["candidate"] == "I3_identity_subspace") & (task_summary["seed"] == 20260921)]
    for row in jtask.itertuples():
        jigsaws_rows.append({"panel": "held_grs_effect", "label": row.task, "estimate": row.estimate, "ci_low": row.ci_low, "ci_high": row.ci_high})
    jigsaws_source = pd.DataFrame(jigsaws_rows)
    write_csv(FIGURE_DATA / "phase5_figure6_source.csv", jigsaws_source)
    figure_jigsaws(jigsaws_source)

    write_report(protocol_summary, held_task_summary, identity_summary, skill_summary)
    locked_config_text = [
        "# Locked configuration", "",
        f"Phase 5 configuration SHA-256: `{config_hash}`", "",
        "The authoritative machine-readable configuration is `configs/experiments/phase5_locked.yaml`. It fixes the primary I3-versus-I0 comparison, 2,000 participant-bootstrap replicates, training-fold target-SD standardization, figure/table inventory, and exact private prediction-input verification.", "",
        "## Generating configurations", "",
        f"- Phase 3: `{config_sha256(yaml.safe_load((ROOT / config['phase3_config']).read_text()))}`",
        f"- Phase 4: `{config_sha256(yaml.safe_load((ROOT / config['phase4_config']).read_text()))}`", "",
        "Prediction rows retain their original generating Git commits. Phase 5 does not rewrite this provenance; it verifies exact artifact hashes before analysis.",
    ]
    (ROOT / "reports" / "locked_configuration.md").write_text("\n".join(locked_config_text) + "\n", encoding="utf-8")
    build_manifest(config_hash, verified)
    print(f"Built Phase 5: {len(bootstrap):,} bootstrap rows, {len(leave_one):,} leave-one rows, 6 figures, 5 main tables")


if __name__ == "__main__":
    main()
