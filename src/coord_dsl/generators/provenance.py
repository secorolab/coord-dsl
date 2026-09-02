# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""PROV-O provenance for generated FSM artifacts, in the shape motion-spec-dsl uses.

Each generator records what it wrote: the source models it read (``prov:used``),
the artifact it produced (``prov:wasGeneratedBy``) and the tool that did it
(``prov:wasAssociatedWith``). Targets are separate CLI invocations here, so the
document beside the artifacts accumulates -- generating ``xml`` then ``cpp``
leaves one document describing both, keyed by ``@id``.
"""

import re
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, XSD

PROV_NS = "https://secorolab.github.io/coord-dsl/provenance/"
DOCUMENT_NAME = "provenance.ld.json"
CDPROV = Namespace(PROV_NS)
# The tool agent and the files are shared concepts, so they are minted in the space
# motion-spec's prov_uri already uses and this document's nodes for them are the same nodes
# motion-spec-dsl's document describes. Only the activity instances stay under
# cdprov -- which therefore mints no vocabulary at all.
MSPROV = Namespace("https://secorolab.github.io/motion-spec/provenance/")
MS_PROV = Namespace("https://secorolab.github.io/metamodels/motion-spec/prov#")

_CONTEXT = [
    "https://secorolab.github.io/metamodels/prov.json",
    {"cdprov": PROV_NS, "msprov": str(MSPROV), "ms-prov": str(MS_PROV)},
]


def _slug(value) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_") or "item"


def _tool_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def source_paths(model) -> list[Path]:
    """The model file and everything it imported."""
    paths: dict[Path, None] = {}

    def visit(item):
        filename = getattr(item, "_tx_filename", None)
        if filename:
            paths[Path(filename).resolve()] = None
        for imp in getattr(item, "imports", []):
            for loaded in getattr(imp, "_tx_loaded_models", []):
                visit(loaded)

    visit(model)
    return list(paths)


def record(model, target: str, artifact: Path) -> Path:
    """Add one generated artifact to the provenance document beside it."""
    artifact = Path(artifact).resolve()
    document = artifact.parent / DOCUMENT_NAME
    stem = Path(getattr(model, "_tx_filename", "model")).stem
    now = datetime.now(timezone.utc).isoformat()
    activity = CDPROV[f"activity/{_slug(target)}_generation/{_slug(stem)}"]

    sources = source_paths(model)
    graph = Graph()
    if document.exists():
        graph.parse(document, format="json-ld")

    agent = MSPROV["agent/coord_dsl"]
    artifact_id = MSPROV[f"entity/generated/{_slug(artifact.name)}"]
    for subject in (activity, artifact_id):
        graph.remove((subject, None, None))
    graph.add((agent, RDF.type, PROV.SoftwareAgent))
    graph.add((agent, RDF.type, PROV.Agent))
    tool_version = _tool_version("coord_dsl")
    if tool_version:
        graph.set((agent, DCTERMS.hasVersion, Literal(tool_version)))
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, RDF.type, MS_PROV.SpecCompilation))
    graph.add((activity, PROV.wasAssociatedWith, agent))
    graph.add((activity, PROV.startedAtTime, Literal(now, datatype=XSD.dateTime)))
    graph.add((activity, PROV.endedAtTime, Literal(now, datatype=XSD.dateTime)))
    for path in sources:
        source = MSPROV[f"entity/source/{_slug(path.name)}"]
        graph.add((source, RDF.type, PROV.Entity))
        graph.set((source, PROV.atLocation, URIRef(path.as_uri())))
        graph.add((activity, PROV.used, source))
    graph.add((artifact_id, RDF.type, PROV.Entity))
    graph.add((artifact_id, PROV.atLocation, URIRef(artifact.as_uri())))
    graph.add((artifact_id, PROV.wasGeneratedBy, activity))
    graph.add((artifact_id, PROV.generatedAtTime, Literal(now, datatype=XSD.dateTime)))
    graph.serialize(document, format="json-ld", context=_CONTEXT, auto_compact=True, indent=2)
    return document
