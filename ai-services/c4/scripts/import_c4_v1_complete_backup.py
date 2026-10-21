"""Import C4_v1_07_08_complete_*.zip into ai-services/c4 destinations.

Verifies BACKUP_MANIFEST.json and export_bundle manifests; idempotent;
never overwrites differing SHA-256 (keeps both via .conflict_src_*).
Does not modify live training packages, inference loaders, or the source ZIP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_PATH_RUN = "train_full_se-path-sim-v1_20261013T181643.681Z"
EXPECTED_SUP_RUN = "train_full_se-supervised-sim-v1_20261014T002241.664Z"
EXPECTED_CATALOGUE_HASH = (
    "95aaba520a28a494e9d6fed0c30de5999b6d47f376368424fb211acb434a1622"
)
ZIP_ALIAS_TO_RUN = {
    "07_se_path_simulation_v1": EXPECTED_PATH_RUN,
    "08_se_supervised_simulation_v1": EXPECTED_SUP_RUN,
}

# Small presentation evidence (no datasets / model binaries / checkpoint zips).
PRESENTATION_SUFFIXES = {".json", ".csv", ".md"}
PRESENTATION_SKIP_PARTS = {
    "synthetic_data",
    "checkpoints",
    "models",
    "__pycache__",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_unsafe_zip_name(name: str) -> bool:
    n = name.replace("\\", "/")
    if n.startswith("/") or n.startswith("../") or "/../" in f"/{n}/":
        return True
    if n.startswith("|") or ":" in Path(n).name and False:
        return True
    # Reject absolute Windows paths inside archive
    if re.match(r"^[A-Za-z]:/", n):
        return True
    return False


def load_backup_manifest(zf: zipfile.ZipFile) -> dict[str, Any]:
    raw = zf.read("BACKUP_MANIFEST.json")
    return json.loads(raw.decode("utf-8"))


def verify_backup_manifest(
    zf: zipfile.ZipFile, manifest: dict[str, Any]
) -> dict[str, Any]:
    files = manifest.get("files") or []
    listed = {f["path"].replace("\\", "/"): f for f in files}
    zip_files = {
        i.filename.replace("\\", "/")
        for i in zf.infolist()
        if not i.is_dir() and not i.filename.endswith("/")
    }
    # BACKUP_MANIFEST itself may or may not be listed
    zip_files_no_man = {p for p in zip_files if p != "BACKUP_MANIFEST.json"}
    listed_paths = set(listed)
    missing = sorted(listed_paths - zip_files)
    unexpected = sorted(zip_files_no_man - listed_paths)
    mismatches: list[str] = []
    verified = 0
    for rel, meta in listed.items():
        if rel not in zip_files:
            continue
        info = zf.getinfo(rel)
        data = zf.read(rel)
        got_sha = sha256_bytes(data)
        got_sz = len(data)
        exp_sha = meta["sha256"]
        exp_sz = int(meta["bytes"])
        if got_sha != exp_sha or got_sz != exp_sz:
            mismatches.append(
                f"{rel}: sha {got_sha}!={exp_sha} or bytes {got_sz}!={exp_sz}"
            )
        else:
            verified += 1
        # also reject symlink-like (zipfile external_attr Unix symlink)
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            mismatches.append(f"SYMLINK rejected: {rel}")
    return {
        "listed": len(listed),
        "verified_ok": verified,
        "missing_from_zip": missing,
        "unexpected_unlisted": unexpected,
        "mismatches": mismatches,
        "ok": not missing and not unexpected and not mismatches and verified == len(listed),
    }


def extract_export_sha_map(manifest: dict[str, Any]) -> dict[str, str]:
    """Support path-sim nested sha256 dict OR supervised flat path→hash map."""
    if isinstance(manifest.get("sha256"), dict):
        return {k.replace("\\", "/"): v for k, v in manifest["sha256"].items()}
    # flat: every key that looks like a relative file path with hex hash value
    out: dict[str, str] = {}
    for k, v in manifest.items():
        if (
            isinstance(v, str)
            and re.fullmatch(r"[0-9a-f]{64}", v)
            and ("/" in k or "." in k)
            and k
            not in {
                "catalogue_hash",
                "protocol",
                "domain",
                "generator",
                "selected_algorithm",
                "exported_at_utc",
            }
        ):
            out[k.replace("\\", "/")] = v
    return out


def verify_export_bundle_bytes(
    files_by_rel: dict[str, bytes], bundle_prefix: str
) -> dict[str, Any]:
    man_rel = f"{bundle_prefix}/manifest.json"
    if man_rel not in files_by_rel:
        return {"ok": False, "error": f"missing {man_rel}"}
    manifest = json.loads(files_by_rel[man_rel].decode("utf-8"))
    sha_map = extract_export_sha_map(manifest)
    bad: list[str] = []
    for rel, exp in sha_map.items():
        full = f"{bundle_prefix}/{rel}"
        if full not in files_by_rel:
            bad.append(f"MISSING {rel}")
            continue
        got = sha256_bytes(files_by_rel[full])
        if got != exp:
            bad.append(f"MISMATCH {rel}")
    return {
        "ok": not bad,
        "checksum_count": len(sha_map),
        "bad": bad,
        "protocol": manifest.get("protocol"),
        "domain": manifest.get("domain"),
        "synthetic": manifest.get("synthetic"),
        "manifest_keys_sample": list(manifest.keys())[:12],
    }


def place_file(
    dest: Path,
    data: bytes,
    *,
    expected_sha: str,
    report: dict[str, Any],
) -> str:
    """Write bytes idempotently. Returns action: wrote|skipped_identical|conflict_preserved."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        existing = sha256_file(dest)
        if existing == expected_sha:
            report["skipped_identical"] += 1
            return "skipped_identical"
        # conflict: keep both
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        conflict = dest.with_name(dest.name + f".conflict_incoming_{stamp}")
        conflict.write_bytes(data)
        report["conflicts"].append(
            {
                "existing": str(dest),
                "existing_sha256": existing,
                "incoming_sha256": expected_sha,
                "incoming_saved_as": str(conflict),
            }
        )
        report["conflict_count"] += 1
        return "conflict_preserved"
    dest.write_bytes(data)
    report["wrote"] += 1
    return "wrote"


def is_presentation_candidate(rel_under_run: str) -> bool:
    parts = rel_under_run.replace("\\", "/").split("/")
    if any(p in PRESENTATION_SKIP_PARTS for p in parts):
        return False
    # skip large export model binaries even under export_bundle
    if "/models/" in f"/{rel_under_run}/":
        return False
    suf = Path(rel_under_run).suffix.lower()
    return suf in PRESENTATION_SUFFIXES


def map_archive_path(arc: str) -> list[tuple[str, Path]]:
    """Return list of (logical_role, destination) for an archive path."""
    return []  # filled in main via closures


def inspect_notebook(data: bytes) -> dict[str, Any]:
    nb = json.loads(data.decode("utf-8"))
    cells = nb.get("cells") or []
    code = [c for c in cells if c.get("cell_type") == "code"]
    with_out = 0
    errors = 0
    secret_hits = 0
    secret_patterns = [
        re.compile(r"(?i)api[_-]?key\s*=\s*['\"][^'\"]{8,}"),
        re.compile(r"(?i)secret\s*=\s*['\"][^'\"]{8,}"),
        re.compile(r"(?i)password\s*=\s*['\"][^'\"]{4,}"),
        re.compile(r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"),
        re.compile(r"(?i)sk-[A-Za-z0-9]{20,}"),
    ]
    for c in code:
        outs = c.get("outputs") or []
        if outs:
            with_out += 1
        for o in outs:
            if o.get("output_type") == "error":
                errors += 1
        # scan sources + stream text for secrets (count only; do not echo)
        blob = "".join(c.get("source") or [])
        for o in outs:
            if o.get("output_type") == "stream":
                blob += "".join(o.get("text") or [])
            elif o.get("output_type") in ("execute_result", "display_data"):
                data_o = o.get("data") or {}
                if "text/plain" in data_o:
                    t = data_o["text/plain"]
                    blob += "".join(t) if isinstance(t, list) else str(t)
        for pat in secret_patterns:
            if pat.search(blob):
                secret_hits += 1
                break
    return {
        "code_cells": len(code),
        "cells_with_outputs": with_out,
        "error_outputs": errors,
        "secret_pattern_hits": secret_hits,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zip",
        type=Path,
        default=Path(
            r"C:\Users\Deshan\Documents\GitHub\Softedge\Suwani_Research\C4_v1_exports"
        ),
        help="ZIP file or folder containing C4_v1_07_08_complete_*.zip",
    )
    parser.add_argument(
        "--c4-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    c4 = args.c4_root.resolve()
    src = args.zip
    if src.is_dir():
        cands = sorted(src.glob("C4_v1_07_08_complete_*.zip"))
        if not cands:
            raise SystemExit(f"No C4_v1_07_08_complete_*.zip under {src}")
        # Prefer the one whose manifest lists both expected runs
        chosen = None
        for z in cands:
            with zipfile.ZipFile(z, "r") as zf:
                if zf.testzip() is not None:
                    continue
                if "BACKUP_MANIFEST.json" not in zf.namelist():
                    continue
                man = load_backup_manifest(zf)
                runs = man.get("source_runs") or {}
                vals = " ".join(str(v) for v in runs.values())
                if EXPECTED_PATH_RUN in vals and EXPECTED_SUP_RUN in vals:
                    chosen = z
                    break
        if chosen is None:
            raise SystemExit(
                "No ZIP contained BOTH expected source runs in BACKUP_MANIFEST.source_runs"
            )
        zip_path = chosen
    else:
        zip_path = src.resolve()

    report: dict[str, Any] = {
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_zip": str(zip_path),
        "source_zip_sha256": sha256_file(zip_path),
        "source_zip_bytes": zip_path.stat().st_size,
        "wrote": 0,
        "skipped_identical": 0,
        "conflict_count": 0,
        "conflicts": [],
        "mapping": {},
        "verification": {},
        "contracts": {},
        "notebooks": {},
        "blockers": [],
    }

    if not zipfile.is_zipfile(zip_path):
        raise SystemExit("Not a valid ZIP")

    with zipfile.ZipFile(zip_path, "r") as zf:
        if zf.testzip() is not None:
            raise SystemExit(f"ZIP integrity failure: {zf.testzip()}")

        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if is_unsafe_zip_name(name):
                raise SystemExit(f"Unsafe archive path: {name!r}")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise SystemExit(f"Symlink in archive rejected: {name!r}")

        if "BACKUP_MANIFEST.json" not in zf.namelist():
            raise SystemExit("Missing BACKUP_MANIFEST.json")
        backup = load_backup_manifest(zf)
        report["backup_manifest_meta"] = {
            k: backup[k] for k in backup if k != "files"
        }
        bak_ver = verify_backup_manifest(zf, backup)
        report["verification"]["backup_manifest"] = bak_ver
        if not bak_ver["ok"]:
            report["blockers"].append("BACKUP_MANIFEST verification failed")
            out = c4 / "docs" / "C4_V1_IMPORT_REPORT.json"
            out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            raise SystemExit(json.dumps(bak_ver, indent=2))

        # Confirm expected runs
        src_runs = backup.get("source_runs") or {}
        joined = " ".join(str(v) for v in src_runs.values())
        if EXPECTED_PATH_RUN not in joined or EXPECTED_SUP_RUN not in joined:
            report["blockers"].append(
                f"source_runs mismatch: {src_runs} (expected {EXPECTED_PATH_RUN} and {EXPECTED_SUP_RUN})"
            )
            raise SystemExit(report["blockers"][-1])

        # Read all listed files into memory map (77MB zip — acceptable)
        files_by_rel: dict[str, bytes] = {}
        listed_sha: dict[str, str] = {}
        for entry in backup["files"]:
            rel = entry["path"].replace("\\", "/")
            data = zf.read(rel)
            files_by_rel[rel] = data
            listed_sha[rel] = entry["sha256"]

        # Verify export bundles from bytes
        for alias, run_name in ZIP_ALIAS_TO_RUN.items():
            prefix = f"runs/{alias}/export_bundle"
            ev = verify_export_bundle_bytes(files_by_rel, prefix)
            report["verification"][f"export_bundle_{alias}"] = ev
            if not ev["ok"]:
                report["blockers"].append(f"export_bundle verify failed for {alias}: {ev.get('bad')}")

        if report["blockers"]:
            raise SystemExit("\n".join(report["blockers"]))

        # Destinations
        path_archive = c4 / "local-colab-archive" / "v1" / EXPECTED_PATH_RUN
        sup_archive = c4 / "local-colab-archive" / "v1" / EXPECTED_SUP_RUN
        path_rt = (
            c4
            / "runtime-artifacts"
            / "se_path_sim_v1"
            / EXPECTED_PATH_RUN
            / "export_bundle"
        )
        sup_rt = (
            c4
            / "runtime-artifacts"
            / "se_supervised_sim_v1"
            / EXPECTED_SUP_RUN
            / "export_bundle"
        )
        nb_dir = c4 / "experiments" / "notebooks" / "v1"
        path_pres = c4 / "experiments" / "results" / "se_path_simulation_v1" / EXPECTED_PATH_RUN
        sup_pres = (
            c4
            / "experiments"
            / "results"
            / "se_supervised_simulation_v1"
            / EXPECTED_SUP_RUN
        )

        report["mapping"] = {
            f"runs/07_se_path_simulation_v1/**": str(path_archive),
            f"runs/08_se_supervised_simulation_v1/**": str(sup_archive),
            "runs/07.../export_bundle/**": str(path_rt),
            "runs/08.../export_bundle/**": str(sup_rt),
            "notebooks/*_executed.ipynb": str(nb_dir),
            "presentation path": str(path_pres),
            "presentation supervised": str(sup_pres),
        }

        imported_sha_check: list[dict[str, Any]] = []

        def write_and_verify(dest: Path, data: bytes, exp_sha: str, role: str) -> None:
            place_file(dest, data, expected_sha=exp_sha, report=report)
            if dest.is_file() and sha256_file(dest) == exp_sha:
                imported_sha_check.append(
                    {"dest": str(dest.relative_to(c4)), "sha256": exp_sha, "role": role, "ok": True}
                )
            elif not any(
                c["existing"] == str(dest) for c in report["conflicts"]
            ):
                # conflict path: verify conflict file
                pass

        for rel, data in files_by_rel.items():
            exp_sha = listed_sha[rel]
            parts = rel.split("/")

            if rel.startswith("notebooks/") and rel.endswith(".ipynb"):
                dest = nb_dir / Path(rel).name
                write_and_verify(dest, data, exp_sha, "notebook")
                report["notebooks"][Path(rel).name] = inspect_notebook(data)
                continue

            if rel.startswith("runs/07_se_path_simulation_v1/"):
                under = rel[len("runs/07_se_path_simulation_v1/") :]
                # full archive
                write_and_verify(path_archive / under, data, exp_sha, "path_archive")
                # export bundle copy
                if under.startswith("export_bundle/"):
                    sub = under[len("export_bundle/") :]
                    write_and_verify(path_rt / sub, data, exp_sha, "path_runtime_export")
                # presentation
                if is_presentation_candidate(under):
                    write_and_verify(path_pres / under, data, exp_sha, "path_presentation")
                continue

            if rel.startswith("runs/08_se_supervised_simulation_v1/"):
                under = rel[len("runs/08_se_supervised_simulation_v1/") :]
                write_and_verify(sup_archive / under, data, exp_sha, "sup_archive")
                if under.startswith("export_bundle/"):
                    sub = under[len("export_bundle/") :]
                    write_and_verify(sup_rt / sub, data, exp_sha, "sup_runtime_export")
                if is_presentation_candidate(under):
                    write_and_verify(sup_pres / under, data, exp_sha, "sup_presentation")
                continue

        report["imported_sha_verified_count"] = sum(
            1 for x in imported_sha_check if x["ok"]
        )
        report["imported_sha_sample"] = imported_sha_check[:8]

        # Contract reads from imported presentation/archive (saved artifacts)
        def read_json(p: Path) -> Any:
            if not p.is_file():
                return None
            return json.loads(p.read_text(encoding="utf-8"))

        path_cat = read_json(path_archive / "topic_catalogue.json")
        path_obs = read_json(path_archive / "observation_schema.json")
        path_proto = read_json(path_archive / "protocol.json")
        path_sel = read_json(path_archive / "selection_val.json")
        path_final_summary = path_archive / "final_simulator_test" / "test_summary.csv"
        if not path_final_summary.is_file():
            path_final_summary = (
                path_rt / "final_simulator_test" / "test_summary.csv"
            )

        sup_sel = read_json(sup_archive / "selection_val.json")
        sup_final = read_json(sup_archive / "final_test" / "final_test_metrics.json")
        if sup_final is None:
            sup_final = read_json(sup_rt / "final_test" / "final_test_metrics.json")
        sup_feat_r = read_json(sup_archive / "feature_schema_response.json")
        sup_feat_e = read_json(sup_archive / "feature_schema_exam.json")
        sup_contract = read_json(sup_archive / "frozen_contract.json")
        domain_markers = read_json(sup_rt / "DOMAIN_MARKERS.json")

        # Local contract comparison
        import sys

        sys.path.insert(0, str(c4))
        from catalogues.c1_practice_full_2026_10 import (
            N_TOPICS,
            Y3S1_TOPICS,
            Y3S2_TOPICS,
            catalogue_hash,
        )
        from training_se_v1.observation import OBS_DIM
        from training_se_v1 import PROTOCOL_VERSION as PATH_V1
        from training_se_supervised_v1 import PROTOCOL_VERSION as SUP_V1
        from training_se_supervised_v1.features_response import response_feature_names
        from training_se_supervised_v1.features_exam import exam_feature_names

        cat_hash_saved = None
        if isinstance(path_cat, dict):
            cat_hash_saved = path_cat.get("sha256") or path_cat.get("catalogue_hash")
        n_topics_saved = path_cat.get("n_topics") if isinstance(path_cat, dict) else None
        y3s1 = len(path_cat.get("y3s1_topics") or []) if isinstance(path_cat, dict) else None
        y3s2 = len(path_cat.get("y3s2_topics") or []) if isinstance(path_cat, dict) else None

        obs_dim_saved = path_obs.get("dim") if isinstance(path_obs, dict) else None
        n_actions_saved = path_obs.get("n_actions") if isinstance(path_obs, dict) else None
        path_protocol_saved = None
        if isinstance(path_proto, dict):
            path_protocol_saved = path_proto.get("protocol") or path_proto.get(
                "PROTOCOL_VERSION"
            )
        if path_protocol_saved is None and isinstance(path_obs, dict):
            path_protocol_saved = path_obs.get("protocol")

        resp_feats_saved = (
            len(sup_feat_r.get("features") or []) if isinstance(sup_feat_r, dict) else None
        )
        exam_feats_saved = (
            len(sup_feat_e.get("features") or []) if isinstance(sup_feat_e, dict) else None
        )

        # Path final returns from CSV
        path_returns: dict[str, Any] = {"missing": True}
        if path_final_summary.is_file():
            import csv

            rows = list(csv.DictReader(path_final_summary.open(encoding="utf-8")))
            path_returns = {"missing": False, "rows": rows}

        # Checkpoints present
        ckpt_finals = sorted(path_archive.glob("seed_*/maskable_ppo/maskable_ppo_final.zip"))
        export_finals = sorted(path_rt.glob("models/seed_*/maskable_ppo_final.zip"))

        report["contracts"] = {
            "local": {
                "path_protocol": PATH_V1,
                "sup_protocol": SUP_V1,
                "n_topics": N_TOPICS,
                "y3s1": len(Y3S1_TOPICS),
                "y3s2": len(Y3S2_TOPICS),
                "catalogue_hash": catalogue_hash(),
                "obs_dim": OBS_DIM,
                "n_actions": N_TOPICS,
                "response_features": len(response_feature_names()),
                "exam_features": len(exam_feature_names()),
            },
            "saved": {
                "path_protocol": path_protocol_saved,
                "catalogue_hash": cat_hash_saved,
                "n_topics": n_topics_saved,
                "y3s1": y3s1,
                "y3s2": y3s2,
                "obs_dim": obs_dim_saved,
                "n_actions": n_actions_saved,
                "response_features": resp_feats_saved,
                "exam_features": exam_feats_saved,
                "path_selection": path_sel,
                "sup_selection": {
                    "response": (sup_sel or {}).get("response") if isinstance(sup_sel, dict) else None,
                    "exam_score": (sup_sel or {}).get("exam_score") if isinstance(sup_sel, dict) else None,
                    "pass": (sup_sel or {}).get("pass") if isinstance(sup_sel, dict) else None,
                },
                "sup_final_test": sup_final,
                "path_final_returns_csv": path_returns,
                "domain_markers": domain_markers,
                "frozen_contract_protocol": (
                    (sup_contract or {}).get("protocol")
                    if isinstance(sup_contract, dict)
                    else None
                )
                or (
                    ((sup_contract or {}).get("contract") or {}).get("protocol")
                    if isinstance(sup_contract, dict)
                    else None
                ),
            },
            "expected_checks": {
                "catalogue_hash_match": cat_hash_saved == EXPECTED_CATALOGUE_HASH
                and catalogue_hash() == EXPECTED_CATALOGUE_HASH,
                "n_topics_46": n_topics_saved == 46 and N_TOPICS == 46,
                "semesters_28_18": y3s1 == 28 and y3s2 == 18,
                "obs_96": obs_dim_saved == 96 and OBS_DIM == 96,
                "actions_46": n_actions_saved == 46,
                "resp_54": resp_feats_saved == 54,
                "exam_98": exam_feats_saved == 98,
            },
            "checkpoints": {
                "archive_finals": [str(p.relative_to(c4)) for p in ckpt_finals],
                "export_finals": [str(p.relative_to(c4)) for p in export_finals],
                "seeds": [p.parent.parent.name for p in ckpt_finals],
            },
            "supervised_models": {
                "response": str(
                    (sup_rt / "models" / "response_selected.joblib").relative_to(c4)
                )
                if (sup_rt / "models" / "response_selected.joblib").is_file()
                else None,
                "exam_score": str(
                    (sup_rt / "models" / "exam_score_selected.joblib").relative_to(c4)
                )
                if (sup_rt / "models" / "exam_score_selected.joblib").is_file()
                else None,
                "pass": str(
                    (sup_rt / "models" / "pass_selected.joblib").relative_to(c4)
                )
                if (sup_rt / "models" / "pass_selected.joblib").is_file()
                else None,
            },
            "note": (
                "Final-test metrics retained for comparison only; "
                "do not use them to choose a deployment checkpoint. "
                "No inference loader changes in this import."
            ),
        }

        # Compare reference metrics if present (report only)
        ref = {
            "response_accuracy": 0.6562632098069607,
            "exam_mae": 0.06862722330047728,
            "pass_accuracy": 0.7966666666666666,
        }
        saved_cmp: dict[str, Any] = {}
        if isinstance(sup_final, dict):
            rt = (sup_final.get("response_test") or {})
            et = (sup_final.get("exam_score_test") or {})
            pt = (sup_final.get("pass_test") or {})
            saved_cmp = {
                "response_accuracy_saved": rt.get("accuracy"),
                "exam_mae_saved": et.get("mae"),
                "pass_accuracy_saved": pt.get("accuracy"),
                "matches_reference": {
                    "response_accuracy": rt.get("accuracy") == ref["response_accuracy"],
                    "exam_mae": et.get("mae") == ref["exam_mae"],
                    "pass_accuracy": pt.get("accuracy") == ref["pass_accuracy"],
                },
            }
        report["contracts"]["reference_comparison"] = saved_cmp

    # Write report
    report_path = c4 / "docs" / "C4_V1_IMPORT_REPORT.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # Keep hand-maintained inventory markdown if present; only create a stub when missing.
    md_path = c4 / "docs" / "C4_V1_IMPORT_INVENTORY.md"
    if not md_path.is_file():
        md_path.write_text(_render_md(report), encoding="utf-8")
        print(f"Wrote {md_path}")
    else:
        print(f"Preserved existing {md_path}")
    print(f"Wrote {report_path}")
    print(
        f"wrote={report['wrote']} skipped_identical={report['skipped_identical']} "
        f"conflicts={report['conflict_count']}"
    )


def _render_md(report: dict[str, Any]) -> str:
    c = report.get("contracts") or {}
    saved = c.get("saved") or {}
    checks = c.get("expected_checks") or {}
    lines = [
        "# C4 v1 import inventory",
        "",
        f"- **Source ZIP:** `{report.get('source_zip')}`",
        f"- **ZIP SHA-256:** `{report.get('source_zip_sha256')}`",
        f"- **Imported at (UTC):** {report.get('imported_at_utc')}",
        f"- **BACKUP_MANIFEST verified files:** {(report.get('verification') or {}).get('backup_manifest', {}).get('verified_ok')}",
        f"- **Wrote / skipped identical / conflicts:** {report.get('wrote')} / {report.get('skipped_identical')} / {report.get('conflict_count')}",
        "",
        "## Mapping",
        "",
    ]
    for k, v in (report.get("mapping") or {}).items():
        lines.append(f"- `{k}` → `{v}`")
    lines += ["", "## Contract checks", ""]
    for k, v in checks.items():
        lines.append(f"- `{k}`: **{v}**")
    lines += ["", "## Notebooks", ""]
    for name, meta in (report.get("notebooks") or {}).items():
        lines.append(
            f"- `{name}`: code={meta.get('code_cells')}, "
            f"with_outputs={meta.get('cells_with_outputs')}, "
            f"errors={meta.get('error_outputs')}, "
            f"secret_hits={meta.get('secret_pattern_hits')}"
        )
    lines += [
        "",
        "## Simulation-only retention",
        "",
        "- domain / synthetic markers preserved from saved export manifests",
        "- Active inference loaders unchanged (still v0 ASSISTments / SE paths)",
        "- No student UI wiring; no supervised→RL connection",
        "",
        f"Machine-readable: [`C4_V1_IMPORT_REPORT.json`](C4_V1_IMPORT_REPORT.json)",
        "",
    ]
    if report.get("blockers"):
        lines += ["## Blockers", ""] + [f"- {b}" for b in report["blockers"]]
    if saved.get("sup_final_test"):
        lines += ["", "## Saved final-test (comparison only; not for deployment selection)", ""]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
