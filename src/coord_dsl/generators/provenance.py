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

from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, XSD

PROV_NS = "https://secorolab.github.io/coord-dsl/provenance/"
DOCUMENT_NAME = "provenance.ld.json"
CDPROV = Namespace(PROV_NS)

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
    activity = CDPROV[f"activity/{_slug(target)}_generation/{_slug(stem)}"]

    sources = source_paths(model)
    graph = Graph()
    if document.exists():
        graph.parse(document, format="json-ld")

    bundle = CDPROV["bundle/coord-dsl-provenance"]
    agent = CDPROV["agent/coord_dsl"]
    artifact_id = CDPROV[f"entity/generated/{_slug(artifact.name)}"]
    for subject in (activity, artifact_id):
        graph.remove((subject, None, None))
    graph.add((bundle, RDF.type, PROV.Bundle))
    graph.add((agent, RDF.type, PROV.SoftwareAgent))
    graph.add((agent, RDF.type, PROV.Agent))
    tool_version = _tool_version("coord_dsl")
    if tool_version:
        graph.set((agent, CDPROV.version, Literal(tool_version)))
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, PROV.wasAssociatedWith, agent))
    graph.add((activity, PROV.startedAtTime, Literal(now, datatype=XSD.dateTime)))
    graph.add((activity, PROV.endedAtTime, Literal(now, datatype=XSD.dateTime)))
    for path in sources:
        source = CDPROV[f"entity/source/{_slug(path.name)}"]
        graph.add((source, RDF.type, PROV.Entity))
        graph.set((source, PROV.atLocation, URIRef(path.as_uri())))
        graph.add((activity, PROV.used, source))
    graph.add((artifact_id, RDF.type, PROV.Entity))
    graph.add((artifact_id, PROV.atLocation, URIRef(artifact.as_uri())))
    graph.add((artifact_id, PROV.wasGeneratedBy, activity))
    graph.add((artifact_id, PROV.generatedAtTime, Literal(now, datatype=XSD.dateTime)))
    graph.serialize(document, format="json-ld", context=_CONTEXT, auto_compact=True, indent=2)
    return document
