"""Matched LLM marking comparison: Condition A (no retrieval) vs Condition B (same LLM + Vector RAG) on the v2 TEST split.

The ONLY difference between the conditions is the retrieved EVIDENCE block (see services.rag.rag_marking.build_prompt):
same model, rubric, scoring scale, temperature 0, same answers. Retrieval uses the TRAIN-only corpus.

SAFETY: real LLM calls happen only with --run-live AND a configured provider. Without them the script writes a BLOCKED
artefact (exit 0) and NO marks are produced. Mock/simulated outputs are never generated.

Usage: python -m experiments.rag_vs_norag --out DIR [--provider gemini|openai|local] [--run-live] [--limit N]
       python -m experiments.rag_vs_norag --out DIR --run-live --shard I/K      (one slice of the fixed test order)
       python -m experiments.rag_vs_norag --out DIR --aggregate K              (combine the K finished slices; no LLM calls)

MULTI-DAY RUNS (free-tier quota): the test answers are put in one fixed order (sorted by answer_id) and shard I of K takes
every K-th answer, so the K shards are disjoint and together cover the whole test split no matter when or in which order they
run. Each shard writes its own files and never overwrites another. `--limit N` is a different thing: a fixed-seed random
subsample for a cheap pilot. It is reproducible for the same file, but the sample depends on the row order of the data file, and
the observation that a larger N contains a smaller N's answers holds for the current pandas/numpy only (checked 2026-10-28, not
guaranteed), so --limit is not used for multi-day runs and can not be combined with --shard. The comparison counts as complete
only after --aggregate has verified all K shards.

SAME CONDITIONS ON EVERY DAY: the first shard writes run_manifest.json holding a fingerprint of everything that must not
change between shards (provider, configured model, system prompt and prompt templates, temperature and token limit,
top-k, threshold, embedding model, retrieval-corpus provenance, the SHA-256 of the dataset files, the SHA-256 of the experiment
source files (this script, the dataset loader and every file of services/rag and services/llm, line endings normalised) and the
result-affecting C3_* settings from the environment). Every later shard must reproduce the same fingerprint or it is refused
before any LLM call, and --aggregate re-checks the fingerprint of every shard and that all rows report one model identifier.
The Git commit and any uncommitted edits to those files are recorded for audit but are not compared: a commit that touches
other files does not block a run, while any change to the experiment code does. The manifest is created exclusively (an existing
one is never overwritten), made read-only, and verified against its own fingerprint on every use.

STATUS: offline research script. BLOCKED while no LLM credentials/quota exist; it then writes a BLOCKED artefact and
produces no marks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(HERE / ".env")  # same behaviour as the FastAPI app: keys come from the git-ignored .env (never printed)

from experiments.model_comparison import load_answers_with_reference  # noqa: E402
from services.llm import get_llm_provider  # noqa: E402
from services.rag.corpus import build_training_corpus  # noqa: E402
from services.rag.embeddings import get_embedding_provider  # noqa: E402
from services.rag.rag_marking import SYSTEM_RULES, build_prompt, rag_assess  # noqa: E402
from services.rag.vector_store import CurriculumVectorStore  # noqa: E402

DATASET = HERE / "datasets" / "c3_phase3_v5_repaired_v2"
PRED_FILE = "rag_vs_norag_predictions.csv"
SUMMARY_FILE = "rag_vs_norag_summary.json"
MANIFEST_FILE = "run_manifest.json"
GENERATION = {"temperature": 0.0, "max_tokens": 1024, "response_format": "json"}  # mirrors services/rag/rag_marking.py::rag_assess
DATASET_FILES = ("01_question_bank.csv", "02_controlled_answers_eligible.csv", "manifest.json")
# Experiment source whose content must be identical in every shard (paths relative to the c3 service folder).
CODE_FILES = ("experiments/rag_vs_norag.py", "experiments/model_comparison.py")
CODE_PACKAGES = ("services/rag", "services/llm")
# Non-secret environment settings that change what is sent to, or retrieved for, the model. (Keys and tokens are never recorded.)
ENV_SETTINGS = ("C3_GEMINI_MODEL", "C3_GEMINI_THINKING_BUDGET", "C3_GEMINI_THINKING_LEVEL", "C3_OPENAI_MODEL", "C3_EMBEDDING_PROVIDER",
                "C3_GEMINI_EMBEDDING_MODEL", "C3_OPENAI_EMBEDDING_MODEL", "C3_LOCAL_EMBEDDING_MODEL", "C3_VECTOR_BACKEND")


# Writes an explicit BLOCKED artefact instead of any marks when the live run cannot happen (never fabricates results).
def blocked(out: Path, reason: str, provider: str) -> int:
    """Write a BLOCKED result (no marks generated) explaining why the live comparison could not run."""
    art = {"status": "BLOCKED", "reason": reason, "provider_requested": provider,
           "test_answers": int((pd.read_csv(DATASET / "02_controlled_answers_eligible.csv", dtype=str)["split"] == "test").sum()),
           "calls_required": "2 x test answers (conditions A and B)", "results": None,
           "note": "No marks were generated; nothing here is an experimental result."}
    (out / "rag_vs_norag_status.json").write_text(json.dumps(art, indent=1), encoding="utf-8")
    print("BLOCKED:", reason)
    return 0


def _sha256_file(path: Path) -> str:
    """SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_files(root: Path = HERE) -> list[str]:
    """Relative paths of the experiment source files that define this comparison."""
    found = [f for f in CODE_FILES if (root / f).exists()]
    for package in CODE_PACKAGES:
        found += sorted(str(f.relative_to(root)).replace("\\", "/") for f in (root / package).glob("*.py"))
    return sorted(set(found))


def code_hashes(root: Path = HERE) -> dict[str, str]:
    """SHA-256 of each experiment source file with line endings normalised (a CRLF/LF checkout does not change it)."""
    return {f: hashlib.sha256((root / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for f in code_files(root)}


def git_info(root: Path = HERE) -> dict:
    """Git commit and the experiment files with uncommitted edits (audit information; None when git is unavailable)."""
    def run(*args: str) -> str | None:
        try:
            done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=20, check=True)
            return done.stdout
        except (OSError, subprocess.SubprocessError):
            return None
    commit = (run("rev-parse", "HEAD") or "").strip() or None
    status = run("status", "--porcelain", "--", *code_files(root))
    return {"git_commit": commit, "git_dirty_files": None if status is None else sorted(line[3:] for line in status.splitlines() if line.strip())}


def build_fingerprint(provider_name: str, model: str | None, top_k: int, threshold: float, embedding_model: str | None,
                      corpus_provenance: dict, dataset_dir: Path = DATASET, code_root: Path = HERE) -> dict:
    """Everything that must be identical in every shard of one comparison (no network needed to compute it)."""
    hit = [{"citation": "C1", "relevance_score": 0.5, "content": "example passage"}]
    sample = dict(question="Q", reference_answer="R", rubric=[{"criterion_id": "C1", "description": "D", "max_marks": 1}],
                  max_marks=1.0, student_answer="S")
    templates = hashlib.sha256((SYSTEM_RULES + "\n--A--\n" + build_prompt(hits=None, **sample)
                                + "\n--B--\n" + build_prompt(hits=hit, **sample)).encode("utf-8")).hexdigest()
    return {"provider": provider_name, "model": model, "generation": GENERATION, "prompt_templates_sha256": templates,
            "top_k": top_k, "threshold": threshold, "embedding_model": embedding_model, "corpus_provenance": corpus_provenance,
            "dataset": dataset_dir.name, "dataset_files_sha256": {f: _sha256_file(dataset_dir / f) for f in DATASET_FILES},
            "code_files_sha256": code_hashes(code_root), "environment": {k: os.getenv(k) for k in ENV_SETTINGS}}


def fingerprint_id(fingerprint: dict) -> str:
    """Short stable identifier of a fingerprint (key order does not matter)."""
    return hashlib.sha256(json.dumps(fingerprint, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def differing_keys(a: dict, b: dict) -> list[str]:
    """Top-level fingerprint fields whose values differ."""
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def _read_manifest(path: Path) -> dict:
    """Load run_manifest.json and verify it still matches its own fingerprint (detects edits and corruption)."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if fingerprint_id(manifest["fingerprint"]) != manifest.get("fingerprint_sha256"):
        raise ValueError(f"{MANIFEST_FILE} has been modified or corrupted (it no longer matches its own fingerprint)")
    return manifest


def check_or_create_manifest(out: Path, fingerprint: dict, k: int | None, info: dict | None = None) -> None:
    """Create run_manifest.json on the first shard; refuse a later shard whose conditions or shard count differ.

    The file is created exclusively ("x"), so two shards starting together can not both create it and an existing manifest is
    never overwritten; it is then made read-only. Every call re-verifies the manifest against its own fingerprint.
    """
    path = out / MANIFEST_FILE
    body = json.dumps({"fingerprint": fingerprint, "fingerprint_sha256": fingerprint_id(fingerprint), "shards": k, "created_with": info or {}},
                      indent=1)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(body)
        path.chmod(stat.S_IREAD)
        return
    except FileExistsError:
        pass
    manifest = _read_manifest(path)
    changed = differing_keys(manifest["fingerprint"], fingerprint)
    if changed:
        raise ValueError(f"experimental conditions differ from the first shard in: {', '.join(changed)} (see {MANIFEST_FILE})")
    if manifest.get("shards") != k:
        raise ValueError(f"this run was started with {manifest.get('shards')} shards, not {k}")


def parse_shard(text: str) -> tuple[int, int]:
    """'I/K' (1-based) -> (I, K); raises ValueError for anything else."""
    try:
        i, k = (int(x) for x in text.split("/"))
    except ValueError as exc:
        raise ValueError(f"--shard must look like 2/9, got {text!r}") from exc
    if not 1 <= i <= k:
        raise ValueError(f"--shard {text}: need 1 <= I <= K")
    return i, k


def select_answers(test: pd.DataFrame, limit: int | None = None, shard: tuple[int, int] | None = None) -> pd.DataFrame:
    """The answers to run: all, a fixed-seed random subsample (--limit) or one deterministic slice (--shard I/K)."""
    if limit and shard:
        raise ValueError("--limit and --shard can not be combined (a subsample can not be extended by later runs)")
    if shard:
        i, k = shard
        ordered = test.sort_values("answer_id").reset_index(drop=True)
        return ordered.iloc[i - 1::k].reset_index(drop=True)
    if limit:
        return test.sample(n=min(limit, len(test)), random_state=20261021).reset_index(drop=True)
    return test


def summarise(df: pd.DataFrame, provider: str, prov: dict, extra: dict | None = None) -> dict:
    """Per-condition counts and nMAE. Failed LLM calls are counted and excluded, never scored as zero."""
    summary = {"status": "EXECUTED", "provider": provider, "n_answers": int(df["answer_id"].nunique()), "corpus_provenance": prov,
               "models": sorted({str(m) for m in df["model"].dropna()}), "per_condition": {}, **(extra or {})}
    for cond, g in df.groupby("condition"):
        ok = g[g["llm_status"] == "ok"]
        if len(ok):
            err = (ok["predicted_mark"].astype(float) / ok["max_marks"] - ok["expected_mark"] / ok["max_marks"]).abs()
            summary["per_condition"][cond] = {"n_ok": int(len(ok)), "n_failed": int(len(g) - len(ok)), "nmae": float(err.mean())}
        else:
            summary["per_condition"][cond] = {"n_ok": 0, "n_failed": int(len(g))}
    return summary


def aggregate_shards(out: Path, k: int, expected_ids: set[str], provider: str, prov: dict) -> dict:
    """Combine shard files 1..K into the full result. Refuses a missing shard, a duplicate answer, an incomplete cover,
    shards produced under different conditions, or rows that report more than one model identifier."""
    manifest_path = out / MANIFEST_FILE
    if not manifest_path.exists():
        raise FileNotFoundError(f"{MANIFEST_FILE} is missing: the shards were not run by this harness version")
    manifest = _read_manifest(manifest_path)
    if manifest.get("shards") != k:
        raise ValueError(f"the run was started with {manifest.get('shards')} shards, not {k}")
    commits, dirty = set(), set()
    for i in range(1, k + 1):
        sp = out / f"rag_vs_norag_summary_shard{i}of{k}.json"
        if not sp.exists():
            raise FileNotFoundError(f"shard {i}/{k} has not been run (missing {sp.name})")
        run_config = json.loads(sp.read_text(encoding="utf-8")).get("run_config", {})
        if run_config.get("fingerprint_sha256") != manifest["fingerprint_sha256"]:
            raise ValueError(f"shard {i}/{k} was run under different conditions than the manifest")
        commits.add(run_config.get("git_commit"))
        dirty.update(run_config.get("git_dirty_files") or [])
    frames = []
    for i in range(1, k + 1):
        path = out / f"rag_vs_norag_predictions_shard{i}of{k}.csv"
        if not path.exists():
            raise FileNotFoundError(f"shard {i}/{k} has not been run (missing {path.name})")
        frames.append(pd.read_csv(path, dtype={"answer_id": str}))
    df = pd.concat(frames, ignore_index=True)
    models = sorted({str(m) for m in df["model"].dropna()})
    if len(models) > 1:
        raise ValueError(f"rows report more than one model identifier: {models}")
    per_answer = df.groupby("answer_id")["condition"].nunique()
    if (per_answer != 2).any():
        raise ValueError("every answer must have exactly conditions A and B; a shard is incomplete or overlaps another")
    if df.duplicated(["answer_id", "condition"]).any():
        raise ValueError("an answer appears in more than one shard")
    if set(df["answer_id"]) != set(expected_ids):
        raise ValueError(f"shards cover {df['answer_id'].nunique()} answers, the test split has {len(expected_ids)}")
    df.to_csv(out / PRED_FILE, index=False)
    audit = {"git_commits": sorted(str(c) for c in commits), "git_dirty_files": sorted(dirty),
             "reproducible_from_one_commit": len(commits) == 1 and None not in commits and not dirty}
    summary = summarise(df, provider, prov, {"aggregated_from_shards": k, "code_version": audit})
    (out / SUMMARY_FILE).write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main(argv=None) -> int:
    """Compare marking with and without retrieved context; refuses to call a live LLM without --run-live."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--provider", default=os.getenv("C3_LLM_PROVIDER", "gemini"))
    ap.add_argument("--run-live", action="store_true", help="allow real (billable / quota-limited) LLM calls")
    ap.add_argument("--limit", type=int, default=None, help="fixed-seed random subsample for a cheap pilot (depends on file row order; use --shard for multi-day runs)")
    ap.add_argument("--shard", default=None, help="run slice I of K of the fixed test order, e.g. 2/9 (multi-day runs)")
    ap.add_argument("--aggregate", type=int, default=None, metavar="K", help="combine K finished shards; makes no LLM calls")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--threshold", type=float, default=0.2)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    try:
        shard = parse_shard(a.shard) if a.shard else None
        if a.limit and shard:
            raise ValueError("--limit and --shard can not be combined")
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    if a.aggregate:
        # No LLM involved: only verifies and merges shard files already produced by live runs.
        ans = load_answers_with_reference(DATASET)
        test_ids = set(ans[ans["split"] == "test"]["answer_id"].astype(str))
        _, prov = build_training_corpus(DATASET)
        try:
            summary = aggregate_shards(a.out, a.aggregate, test_ids, a.provider, prov)
        except (FileNotFoundError, ValueError) as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(summary["per_condition"], indent=1))
        return 0
    try:
        provider = get_llm_provider(a.provider)
    except Exception as exc:
        return blocked(a.out, f"provider '{a.provider}' unavailable: {type(exc).__name__}", a.provider)
    # Gate 1: credentials. Gate 2 (below): the caller must opt in to real, quota-limited calls with --run-live.
    if not provider.is_available():
        return blocked(a.out, f"no credentials configured for '{a.provider}'", a.provider)
    if not a.run_live:
        return blocked(a.out, "live LLM calls not enabled (--run-live not given). Free-tier quota (about 20 requests/day/model) "
                              "cannot cover 2 x 90 calls; OpenAI credit was reported exhausted earlier in the project (not re-probed)", a.provider)

    # TRAIN-only retrieval corpus, so test answers cannot be retrieved as evidence (no leakage).
    docs, prov = build_training_corpus(DATASET)
    embedder = get_embedding_provider("local")
    store = CurriculumVectorStore(docs, embedding_backend="dense", embedding_provider=embedder)
    # Conditions that must not change between shards; a later shard that differs is refused before any LLM call.
    fingerprint = build_fingerprint(a.provider, getattr(provider, "model", None), a.top_k, a.threshold,
                                    getattr(embedder, "model", None), prov)
    version = git_info()
    if shard:
        try:
            check_or_create_manifest(a.out, fingerprint, shard[1], version)
        except ValueError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
    ans = load_answers_with_reference(DATASET)  # the answers file alone has empty reference answers
    test = ans[ans["split"] == "test"].reset_index(drop=True)
    test = select_answers(test, a.limit, shard)  # all answers, a fixed-seed pilot subsample, or one deterministic shard
    rows = []
    for r in test.to_dict("records"):
        mx = float(r["max_marks"])
        # Dataset has a single overall criterion per question, so one holistic rubric line is used for both conditions.
        rubric = [{"criterion_id": "C1", "description": "Overall correctness and completeness against the reference answer", "max_marks": mx}]
        # Same model, prompt, rubric and answer in both conditions; only the retrieved EVIDENCE block differs.
        for use_rag in (False, True):
            t0 = time.time()
            res = rag_assess(provider=provider, store=store, question_id=r["question_id"], question=r["question_text"],
                             reference_answer=r["reference_answer"], rubric=rubric, max_marks=mx, student_answer=r["student_answer"],
                             use_rag=use_rag, top_k=a.top_k, threshold=a.threshold)
            rows.append({"answer_id": r["answer_id"], "question_id": r["question_id"], "tier": r["answer_quality"], "condition": res["condition"],
                         "max_marks": mx, "expected_mark": float(r["expected_mark"]), "llm_status": res["llm_status"],
                         "predicted_mark": res.get("total_awarded_marks"), "retrieved": json.dumps([h["citation"] for h in res["retrieval"]["hits"]]),
                         "latency_s": round(time.time() - t0, 2), "tokens": res.get("tokens"), "model": res.get("model")})
    df = pd.DataFrame(rows)
    run_config = {"top_k": a.top_k, "threshold": a.threshold, "dataset": DATASET.name, "limit": a.limit,
                  "shard": f"{shard[0]}/{shard[1]}" if shard else None,
                  "fingerprint_sha256": fingerprint_id(fingerprint), **version}
    # A shard writes its own files so a later shard never overwrites an earlier one; --aggregate builds the full result.
    tag = f"_shard{shard[0]}of{shard[1]}" if shard else ""
    df.to_csv(a.out / PRED_FILE.replace(".csv", f"{tag}.csv"), index=False)
    summary = summarise(df, a.provider, prov, {"run_config": run_config})
    (a.out / SUMMARY_FILE.replace(".json", f"{tag}.json")).write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary["per_condition"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
