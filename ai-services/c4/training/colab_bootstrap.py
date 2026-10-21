"""Bootstrap helpers for Google Colab (ZIP upload / optional GitHub checkout)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def install_requirements(requirements_path: Path | str) -> None:
    req = Path(requirements_path)
    if not req.exists():
        raise FileNotFoundError(
            f"Missing requirements file: {req}\n"
            "Upload the C4 source ZIP or clone the repo so ai-services/c4/requirements-training.txt is available."
        )
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)])


def mount_drive() -> Path:
    """Mount Google Drive in Colab. Raises with guidance outside Colab."""
    try:
        from google.colab import drive  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "google.colab is unavailable. Drive mount only works inside a Colab runtime. "
            "Locally, pass an output directory under ai-services/c4/experiments/results instead."
        ) from exc
    drive.mount("/content/drive")
    root = Path("/content/drive/MyDrive")
    if not root.exists():
        raise RuntimeError("Drive mount reported success but /content/drive/MyDrive is missing.")
    return root


def upload_and_extract_c4_zip(dest: Path | str = "/content/J26-SE-317") -> Path:
    """
    Prompt for a ZIP upload in Colab and extract it.

    Expected ZIP contents: either the full repo root (with ai-services/c4) or the c4 folder itself.
    """
    try:
        from google.colab import files  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "ZIP upload helper requires Google Colab. Locally, open the cloned repo instead."
        ) from exc

    dest_path = Path(dest)
    print("Select the AdaptiveLearnSE / C4 source ZIP from your computer…")
    uploaded = files.upload()
    if not uploaded:
        raise RuntimeError("No file uploaded. Re-run the cell and choose a ZIP.")

    zip_name = next(iter(uploaded.keys()))
    if not zip_name.lower().endswith(".zip"):
        raise ValueError(f"Expected a .zip file, got: {zip_name}")

    zip_path = Path.cwd() / zip_name
    dest_path.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_path)

    c4 = _locate_c4_root(dest_path)
    print(f"C4 root resolved to: {c4}")
    return c4


def _locate_c4_root(root: Path) -> Path:
    direct = root / "ai-services" / "c4"
    if direct.exists():
        return direct
    # ZIP may contain a single top-level folder.
    children = [p for p in root.iterdir() if p.is_dir() and not p.name.startswith("__")]
    for child in children:
        candidate = child / "ai-services" / "c4"
        if candidate.exists():
            return candidate
        if (child / "training").exists() and (child / "experiments").exists():
            return child
    if (root / "training").exists() and (root / "experiments").exists():
        return root
    raise FileNotFoundError(
        f"Could not find ai-services/c4 under {root}. "
        "Zip the repository root (or the c4 folder) and try again."
    )


def optional_github_clone(
    repo_url: str,
    branch: str,
    commit: str | None,
    dest: Path | str = "/content/J26-SE-317",
) -> Path:
    """
    Optional clone of a *verified committed* revision.

    Prefer ZIP upload for unpushed local work. Do not put tokens in the URL.
    """
    dest_path = Path(dest)
    if dest_path.exists():
        shutil.rmtree(dest_path)
    cmd = ["git", "clone", "--branch", branch, "--single-branch", repo_url, str(dest_path)]
    subprocess.check_call(cmd)
    if commit:
        subprocess.check_call(["git", "checkout", commit], cwd=str(dest_path))
    c4 = _locate_c4_root(dest_path)
    print(f"Cloned C4 root: {c4}")
    return c4


def add_c4_to_syspath(c4_root: Path | str) -> Path:
    """Ensure `import training...` works (parent of the training package)."""
    root = Path(c4_root).resolve()
    if not (root / "training").exists():
        raise FileNotFoundError(f"{root}/training not found")
    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)
    return root
