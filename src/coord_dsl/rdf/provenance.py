# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""The generation steps of coord-dsl, each recording itself in a bundle in the dataset it is given.

``build`` turns a state-machine or behaviour-tree model into its graph, and ``render`` turns that
graph and a template into code. Both work in one ``Dataset``: the model graph and the
``prov:Bundle`` are named graphs in it, and each step adds itself to the bundle as a
``prov-ext:Transformation`` associated with the package, which the caller states in the bundle
first. Files are named by their location, with the hash of their bytes as ``dcterms:identifier``.
Neither step writes the dataset.

The package, named by its purl, is the agent, though PROV-DM 2.2.1.1 defines a software agent as
running software.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from jinja2 import TemplateNotFound
from rdf_utils.models.prov import (
    add_directory_location,
    add_entity,
    add_file_entity,
    add_file_hash,
    create_bundle,
    get_file_path,
    get_git_info,
    get_py_pkg_info,
    load_pkg_prov,
    load_transformation_prov,
)
from rdf_utils.models.textx import add_model_prov
from rdf_utils.models.time import add_wall_instant
from rdflib import RDF, Dataset, Graph, Literal, URIRef
from rdflib.namespace import SDO

from coord_dsl.generators.bt import RENDERERS as BT_RENDERERS
from coord_dsl.generators.bt import gen_json as gen_bt_json
from coord_dsl.generators.fsm import RENDERERS, gen_json
from coord_dsl.rdf.bt import get_bt_graph
from coord_dsl.rdf.fsm import get_fsm_graph
from coord_dsl.rdf.vocab import URI_BT_PRED_CHILDREN, URI_BT_TYPE_TREE, URI_FSM_TYPE_FSM


def create_coord_dsl_bundle(dataset: Dataset) -> tuple[URIRef, URIRef]:
    """Create a bundle for coord_dsl in a dataset, stating the package as its agent.

    Returns:
        The IDs of the bundle and of the package, to pass to `build` and `render`
    """
    info = get_py_pkg_info("coord_dsl")
    bundle_id = create_bundle(dataset, info.purl)
    load_pkg_prov(dataset.graph(bundle_id), info)
    return bundle_id, info.purl


def _add_transformation(
    bundle: Graph,
    agent: URIRef,
    activity: URIRef,
    sources: list[URIRef],
    targets: list[URIRef],
    started_at: datetime,
    ended_at: datetime,
) -> None:
    """Add a transformation by an agent to a bundle, with its wall-clock instants."""
    beginning, end = URIRef(uuid4().urn), URIRef(uuid4().urn)
    add_wall_instant(bundle, beginning, started_at)
    add_wall_instant(bundle, end, ended_at)
    load_transformation_prov(bundle, activity, sources, targets, agent, beginning, end)


def _entry_tree(graph: Graph) -> URIRef:
    """The behaviour tree that no other tree holds as a child."""
    children = {
        child
        for head in graph.objects(predicate=URI_BT_PRED_CHILDREN)
        for child in graph.items(head)
    }
    entries = set(graph.subjects(RDF.type, URI_BT_TYPE_TREE)) - children
    if len(entries) != 1:
        raise ValueError(
            f"behaviour-tree graph has {len(entries)} trees that no other tree holds"
            " -- render needs exactly one entry tree"
        )
    (entry,) = entries
    assert isinstance(entry, URIRef)
    return entry


def build(
    model,
    dataset: Dataset,
    bundle_id: URIRef,
    agent_id: URIRef,
    graph_id: URIRef | None = None,
) -> URIRef:
    """Build the graph of a model in a dataset and add how it was made to a bundle.

    Parameters:
        model: the textX state-machine or behaviour-tree model, loaded from a file; that file
            and every model it imports are the sources
        dataset: the dataset holding the model graph and the bundle
        bundle_id: the `prov:Bundle` in the dataset to record in
        agent_id: the coord_dsl package, stated in the bundle with `load_pkg_prov`
        graph_id: the graph to build into; a new `urn:uuid:` when None

    Returns:
        The IRI of the model graph
    """
    graph_id = URIRef(uuid4().urn) if graph_id is None else graph_id
    bundle = dataset.graph(bundle_id)
    started_at = datetime.now(UTC)
    if hasattr(model, "trees"):
        get_bt_graph(model, dataset.graph(graph_id))
    else:
        get_fsm_graph(model, dataset.graph(graph_id))
    ended_at = datetime.now(UTC)

    source_ids = add_model_prov(bundle, model)
    for source_id in source_ids:
        path = get_file_path(bundle, source_id)
        assert path is not None, f"source '{source_id}' has no location"
        commit, repository, _, dirty = get_git_info(path)
        if commit is not None:
            bundle.add((source_id, SDO.identifier, Literal(f"{commit}-dirty" if dirty else commit)))
        if repository is not None:
            bundle.add((source_id, SDO.codeRepository, URIRef(repository)))
    activity = URIRef(uuid4().urn)
    _add_transformation(
        bundle, agent_id, activity, sorted(source_ids), [graph_id], started_at, ended_at
    )
    return graph_id


def render(
    dataset: Dataset,
    graph_id: URIRef,
    bundle_id: URIRef,
    agent_id: URIRef,
    target: str,
    output_file: Path,
) -> None:
    """Render a model graph in a dataset to code and add how it was made to a bundle.

    A graph with a `bt:BehaviourTree` renders from its entry tree, the one no other tree holds;
    any other graph renders its state machine.

    Parameters:
        dataset: the dataset holding the model graph and the bundle
        graph_id: the graph to render, e.g. from `build`
        bundle_id: the `prov:Bundle` in the dataset to record in
        agent_id: the coord_dsl package, stated in the bundle with `load_pkg_prov`; its
            template is found under it
        target: what to render, a key of the state-machine or behaviour-tree `RENDERERS`
        output_file: the file to write the code to

    Raises:
        FileNotFoundError: when the template is missing; nothing is written
        ValueError: when a behaviour-tree graph has no single entry tree
    """
    model_graph = dataset.graph(graph_id)
    bundle = dataset.graph(bundle_id)
    started_at = datetime.now(UTC)
    output_file = Path(output_file).resolve()
    if (None, RDF.type, URI_BT_TYPE_TREE) in model_graph:
        renderer, template_path = BT_RENDERERS[target]
        ir = gen_bt_json(model_graph, _entry_tree(model_graph))
    else:
        renderer, template_path = RENDERERS[target]
        fsm_ref = model_graph.value(predicate=RDF.type, object=URI_FSM_TYPE_FSM)
        assert isinstance(fsm_ref, URIRef)
        ir = gen_json(model_graph, fsm_ref)
    template_id = add_file_entity(bundle, agent_id, template_path)
    try:
        add_file_hash(bundle, template_id)
        code = renderer(ir)
    except (FileNotFoundError, TemplateNotFound) as error:
        raise FileNotFoundError(
            f"template for target '{target}' not found -- coord_dsl install is incomplete: {error}"
        ) from error
    output_file.write_text(code)
    ended_at = datetime.now(UTC)

    add_entity(bundle, graph_id)
    activity = URIRef(uuid4().urn)
    output_id = add_file_entity(
        bundle,
        add_directory_location(bundle, output_file.parent),
        output_file.name,
        generated_by=activity,
    )
    add_file_hash(bundle, output_id)
    _add_transformation(
        bundle, agent_id, activity, [graph_id, template_id], [output_id], started_at, ended_at
    )
