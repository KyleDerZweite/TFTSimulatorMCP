"""Installed simulator provenance and unchanged definition defaults."""

import hashlib
from importlib import metadata
import json
import os
from pathlib import Path


def simulator_identity():
    import Simulator
    from Simulator.simulators.tft_simulator import TFT_Simulator

    source_root = Path(Simulator.__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(source_root.rglob("*.py")):
        digest.update(str(path.relative_to(source_root)).encode())
        digest.update(path.read_bytes())
    distribution = metadata.distribution("tft-simulator")
    provenance = distribution.read_text("direct_url.json")
    revision = None
    if provenance:
        try:
            revision = json.loads(provenance).get("vcs_info", {}).get("commit_id")
        except (ValueError, AttributeError, TypeError):
            pass
    if not revision:
        revision = os.environ.get("TFT_MCP_SIMULATOR_REVISION")
    return {"revision": revision or "sha256:" + digest.hexdigest(), "source_sha256": digest.hexdigest(),
            "environment_name": TFT_Simulator.metadata.get("name"),
            "distribution_version": metadata.version("tft-simulator")}


def simulator_defaults():
    from Simulator import config

    defaults = {}
    for name, value in vars(config).items():
        if not name.isupper():
            continue
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            continue
        defaults[name] = value
    return defaults
