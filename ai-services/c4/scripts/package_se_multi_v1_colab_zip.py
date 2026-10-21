#!/usr/bin/env python3
"""ZIP the se-path-multi-v1 Colab source from the real import closure.

Includes every local module imported by smoke_runner and full_run, including
package __init__ modules. Does not invent files and does not drop an import
to hide a missing module.
"""

from __future__ import annotations

import ast
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "colab_zips" / "se_path_multi_v1_colab.zip"
ENTRYPOINTS = (
    "training_se_v2.multi_action.smoke_runner",
    "training_se_v2.multi_action.full_run",
)
LOCAL_ROOTS = {"training_se_v1", "training_se_v2", "catalogues"}
EXTRA = (
    "README_SE_MULTI_COLAB.md",
    "experiments/notebooks/v2/02_se_path_multi_v1.ipynb",
)
MUST_INCLUDE = (
    "training_se_v1/__init__.py",
    "training_se_v1/protocol.py",
    "training_se_v1/catalogue.py",
    "training_se_v1/config.py",
    "training_se_v1/simulator.py",
    "catalogues/__init__.py",
    "catalogues/c1_practice_full_2026_10.py",
    "training_se_v2/__init__.py",
    "training_se_v2/multi_action/__init__.py",
    "training_se_v2/multi_action/smoke_runner.py",
    "training_se_v2/multi_action/full_run.py",
)


def _is_local(module: str) -> bool:
    return module.split(".", 1)[0] in LOCAL_ROOTS


def _module_path(module: str) -> Path | None:
    relative = Path(*module.split("."))
    module_file = ROOT / relative.with_suffix(".py")
    package_init = ROOT / relative / "__init__.py"
    if module_file.is_file():
        return module_file
    if package_init.is_file():
        return package_init
    return None


def _queue_module(module: str, queue: list[str]) -> None:
    if not module or not _is_local(module):
        return
    parts = module.split(".")
    for index in range(1, len(parts) + 1):
        queue.append(".".join(parts[:index]))


def _relative_module(current: str, current_path: Path, node: ast.ImportFrom) -> list[str]:
    parts = current.split(".")
    if current_path.name != "__init__.py":
        parts = parts[:-1]
    if node.level > 1:
        parts = parts[: -(node.level - 1)]
    base = ".".join(parts)
    found: list[str] = []
    if node.module:
        found.append(f"{base}.{node.module}" if base else node.module)
    else:
        for alias in node.names:
            found.append(f"{base}.{alias.name}" if base else alias.name)
    return found


def _imports_of(module: str, path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                found.extend(_relative_module(module, path, node))
            elif node.module:
                found.append(node.module)
    return found


def source_closure(
    entrypoints: tuple[str, ...] | None = None,
    must_include: tuple[str, ...] | None = None,
) -> list[Path]:
    entrypoints = entrypoints or ENTRYPOINTS
    must_include = must_include or MUST_INCLUDE
    queue = list(entrypoints)
    seen: set[str] = set()
    files: set[Path] = set()
    while queue:
        module = queue.pop(0)
        if module in seen or not _is_local(module):
            continue
        seen.add(module)
        path = _module_path(module)
        if path is None:
            raise FileNotFoundError(f"Local import {module} has no source file under {ROOT}")
        files.add(path)
        for imported in _imports_of(module, path):
            _queue_module(imported, queue)
    missing = [rel for rel in must_include if not (ROOT / rel).is_file() or (ROOT / rel) not in files]
    if missing:
        raise RuntimeError("Import closure is missing required source: " + ", ".join(missing))
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def main() -> None:
    files = source_closure()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(ROOT).as_posix())
        for rel in EXTRA:
            zf.write(ROOT / rel, rel)
        zf.writestr(
            "FULL_TRAINING.txt",
            "Set RUN_FULL_TRAINING=True only in Colab.\n"
            "Algorithm: sb3_contrib.MaskablePPO with use_masking=True.\n"
            "Seeds: 0,1,2. Select on validation return, then frozen test.\n"
            "Export native maskable_ppo_final.zip. Do not export policy.npz.\n"
            "Do not copy experiments/smoke_runs or experiments/parity_runs into active/.\n",
        )
        zf.writestr(
            "SOURCE_CLOSURE.txt",
            "\n".join(path.relative_to(ROOT).as_posix() for path in files) + "\n",
        )
    print(f"Wrote {OUT}")
    for path in files:
        print(path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
