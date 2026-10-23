"""The post-marking seal: fixes the returns, the adjudication record and the final labels after marking.

The pre-marking seal (sheets.py) records the sheets, return templates, key and plan. This module adds the second seal described in
GOLD_PROTOCOL.md. It binds every marker return to the sealed sheet it names, hashes the files, and records the hash of the
pre-marking seal so the two stages form a chain. Like the first seal it is tamper evidence only: it shows whether files changed
after sealing, not who may read or write them, and it cannot show who produced the marks. Seals of simulated material carry the
simulated notice. Pure functions plus a verifier; the caller decides where the files live.
"""

import json
import re
from pathlib import Path

from datasets.gold.common import SIMULATED_NOTICE, GoldToolError, canonical_bytes, sha256_file, sha256_hex

RETURN_NAME = re.compile(r"^return_([A-Za-z0-9_-]{1,32})\.json$")
REQUIRED = ("adjudication.json", "final_labels.json")


def post_marking_seal(pre_seal: dict, files: dict[str, bytes]) -> dict:
    """Seal named file contents. Needs a return file per marker, adjudication.json and final_labels.json."""
    if pre_seal.get("stage") != "pre_marking":
        raise GoldToolError("a post-marking seal must be built on a pre-marking seal")
    missing = [n for n in REQUIRED if n not in files]
    if missing:
        raise GoldToolError(f"missing file(s): {missing}")
    returns = {m.group(1): n for n in files if (m := RETURN_NAME.match(n))}
    if len(returns) < 2:
        raise GoldToolError("need at least two marker return files named return_<marker>.json")
    for marker, name in sorted(returns.items()):
        try:
            ret = json.loads(files[name].decode("utf-8"))
        except ValueError as exc:
            raise GoldToolError(f"{name} is not valid JSON") from exc
        sealed = pre_seal["files"].get(f"sheet_{marker}.json")
        if sealed is None or ret.get("sheet_sha256") != sealed or ret.get("marker") != marker or ret.get("origin") != pre_seal["origin"]:
            raise GoldToolError(f"{name} does not belong to the sealed sheet of marker {marker!r} (hash, marker or origin differs)")
    hashes = {name: sha256_hex(data) for name, data in sorted(files.items())}
    seal = {"seal_version": 1, "stage": "post_marking", "origin": pre_seal["origin"], "group": pre_seal["group"],
            "pre_marking_seal_sha256": pre_seal["seal_sha256"], "files": hashes, "seal_sha256": sha256_hex(canonical_bytes(hashes)),
            "meaning": "tamper evidence only: it shows whether these files changed after sealing, not who produced the marks or who may read them"}
    if pre_seal["origin"] == "toy_fixture":
        seal["notice"] = SIMULATED_NOTICE
    return seal


def verify_post_marking_seal(seal: dict, directory, pre_seal: dict | None = None) -> list[str]:
    """Names of sealed files that are missing or changed; also flags a chain that does not point at the given pre-marking seal."""
    bad = []
    for name, digest in seal["files"].items():
        path = Path(directory) / name
        if not path.exists() or sha256_file(path) != digest:
            bad.append(name)
    if sha256_hex(canonical_bytes(seal["files"])) != seal["seal_sha256"]:
        bad.append("seal_sha256")
    if pre_seal is not None and (pre_seal["seal_sha256"] != seal["pre_marking_seal_sha256"] or pre_seal["origin"] != seal["origin"]):
        bad.append("pre_marking_seal_sha256")
    return bad
