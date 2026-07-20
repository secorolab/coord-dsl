# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""PROV-O provenance for generated artifacts, in the shape motion-spec-dsl uses.

Each generator records what it wrote: the source models it read (``prov:used``),
the artifact it produced (``prov:wasGeneratedBy``) and the tool that did it
(``prov:wasAssociatedWith``). Targets are separate CLI invocations here, so the
document beside the artifacts accumulates -- generating ``xml`` then ``cpp``
leaves one document describing both, keyed by ``@id``.
"""

import json
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PROV_NS = "https://secorolab.github.io/coord-dsl/provenance/"
DOCUMENT_NAME = "provenance.jsonld"
SCHEMA_VERSION = 1

_CONTEXT = ["https://secorolab.github.io/metamodels/prov.json", {"cdprov": PROV_NS}]


def _slug(value) -> str:
    return "".join(c if c.isalnum() or c in "_.-" else "_" for c in str(value)).strip("_") or "item"


def _tool_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def source_paths(model) -> list[Path]:
    """The model file and everything it pulled in: imports, and the FSMs a tree runs."""
    paths: dict[Path, None] = {}

    def visit(item):
        filename = getattr(item, "_tx_filename", None)
        if filename:
            paths[Path(filename).resolve()] = None
        for imp in getattr(item, "imports", []):
            for loaded in getattr(imp, "_tx_loaded_models", []):
                visit(loaded)

    visit(model)
    for fsm in getattr(model, "fsms", []):
        base = Path(getattr(model, "_tx_filename", ".")).parent
        paths[(base / fsm.source).resolve()] = None
    return list(paths)


def record(model, target: str, artifact: Path) -> Path:
    """Add one generated artifact to the provenance document beside it."""
    artifact = Path(artifact).resolve()
    document = artifact.parent / DOCUMENT_NAME
    stem = Path(getattr(model, "_tx_filename", "model")).stem
    now = datetime.now(timezone.utc).isoformat()
    activity = f"cdprov:activity/{_slug(target)}_generation/{_slug(stem)}"

    sources = source_paths(model)
    nodes = {
        "cdprov:bundle/coord-dsl-provenance": {
            "@id": "cdprov:bundle/coord-dsl-provenance",
            "@type": "prov:Bundle",
        },
        "cdprov:agent/coord_dsl": {
            "@id": "cdprov:agent/coord_dsl",
            "@type": ["prov:SoftwareAgent", "prov:Agent"],
            "version": _tool_version("coord_dsl"),
        },
        activity: {
            "@id": activity,
            "@type": ["prov:Activity"],
            "role": f"{target}_generation",
            "used": [f"cdprov:entity/source/{_slug(path.name)}" for path in sources],
            "wasAssociatedWith": "cdprov:agent/coord_dsl",
            "startedAtTime": now,
            "endedAtTime": now,
        },
    }
    for path in sources:
        nodes[f"cdprov:entity/source/{_slug(path.name)}"] = {
            "@id": f"cdprov:entity/source/{_slug(path.name)}",
            "@type": ["prov:Entity"],
            "role": "source_model",
            "atLocation": path.as_uri(),
        }
    artifact_id = f"cdprov:entity/generated/{_slug(artifact.name)}"
    nodes[artifact_id] = {
        "@id": artifact_id,
        "@type": ["prov:Entity"],
        "role": f"generated_{target}",
        "atLocation": artifact.as_uri(),
        "wasGeneratedBy": activity,
        "generatedAtTime": now,
    }

    merged = {}
    if document.exists():
        # keep what earlier targets recorded; an artifact regenerated now wins
        for node in json.loads(document.read_text()).get("@graph", []):
            merged[node["@id"]] = node
    merged.update(nodes)
    document.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "@context": _CONTEXT,
                "@graph": [
                    {k: v for k, v in node.items() if v is not None and v != []}
                    for node in merged.values()
                ],
            },
            indent=2,
        )
        + "\n"
    )
    return document
