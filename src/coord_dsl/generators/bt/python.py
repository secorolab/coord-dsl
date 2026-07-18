# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Render a py_trees tree (Python expression) from the behaviour-tree RDF graph.

Scope: composites, the cleanly-mapping decorators, action/condition leaves,
FSM-coordination (``send/await``) nodes and the guard kinds with a clean
py_trees mapping (``failure-if``/``success-if`` preconditions and
``on-success``/``on-failure``/``post`` completion scripts, translated to
blackboard expressions at generation time). ``skip-if``/``while``/``on-halted``
guards, scripted builtins and the composites without a py_trees analogue
(``if-then-else``, ``while-do-else``, ``switch``) raise
``NotImplementedError`` -- the C++/XML backend covers those.
"""

import re

from rdflib import Namespace, RDF
from rdflib.namespace import split_uri
from rdf_utils.models.vocab import URI_QUDT_PRED_UNIT, URI_QUDT_PRED_VALUE
from rdf_utils.naming import get_valid_var_name

from coord_dsl.generators.bt.graph import URI_MM_BT
from coord_dsl.generators.bt.xml import BUILTIN_TAG, UNIT_SI

NS_BT = Namespace(URI_MM_BT)

# composite kind -> (py_trees class, extra constructor kwargs as source text)
_SEQUENCE = {"sequence": "memory=True", "sequence-with-memory": "memory=True",
             "reactive-sequence": "memory=False"}
_SELECTOR = {"fallback": "memory=True", "selector": "memory=True",
             "reactive-fallback": "memory=False"}
_PARALLEL = {
    "parallel": "policy=py_trees.common.ParallelPolicy.SuccessOnOne()",
    "parallel-all": "policy=py_trees.common.ParallelPolicy.SuccessOnAll()",
}

_BUILTIN_LEAF = {
    "always_success": "py_trees.behaviours.Success",
    "always_failure": "py_trees.behaviours.Failure",
}


# guard kind -> immediate status (pre) / status filter for the script (post)
_GUARD_PRE = {"failure-if": "py_trees.common.Status.FAILURE",
              "success-if": "py_trees.common.Status.SUCCESS"}
_GUARD_POST = {"on-success": "py_trees.common.Status.SUCCESS",
               "on-failure": "py_trees.common.Status.FAILURE",
               "post": "None"}

# BT.CPP guard-script subset: literals, blackboard idents, comparisons,
# arithmetic and boolean connectives. `:=` is handled by _script_stmt.
_SCRIPT_TOKEN = re.compile(
    r"\s*(?:(?P<num>\d+(?:\.\d+)?)|(?P<str>'[^']*'|\"[^\"]*\")"
    r"|(?P<op>==|!=|<=|>=|&&|\|\||[()<>+\-*/])|(?P<id>[^\d\W][\w-]*))"
)
_SCRIPT_OP = {"&&": "and", "||": "or"}
_SCRIPT_KEYWORD = {"true": "True", "false": "False"}


def _script_expr(script):
    """Translate a guard-script expression to Python over the blackboard."""
    out, pos = [], 0
    while pos < len(script):
        m = _SCRIPT_TOKEN.match(script, pos)
        if m is None:
            if not script[pos:].strip():
                break
            raise NotImplementedError(
                f"guard script {script!r} is outside the supported subset "
                f"(unrecognised input at {script[pos:].strip()!r})"
            )
        pos = m.end()
        if m.lastgroup == "id":
            tok = m.group("id")
            out.append(_SCRIPT_KEYWORD.get(tok) or f"_bb_get({tok!r})")
        else:
            tok = m.group(m.lastgroup)
            out.append(_SCRIPT_OP.get(tok, tok))
    return " ".join(out)


def _script_stmt(script):
    """Translate a guard-script assignment (``key := expr``) to Python."""
    key, sep, value = script.partition(":=")
    key = key.strip()
    if not sep or not re.fullmatch(r"[^\d\W][\w-]*", key):
        raise NotImplementedError(
            f"guard script {script!r} is outside the supported subset "
            "(expected a single 'key := expr' assignment)"
        )
    return f"_bb_set({key!r}, {_script_expr(value)})"


def _guard_wrap(g, node, expr, name):
    pre, post = [], []
    for gn in sorted(g.objects(node, NS_BT.guard), key=str):
        kind = str(g.value(gn, NS_BT["guard-kind"]))
        script = str(g.value(gn, NS_BT["guard-script"]))
        if kind in _GUARD_PRE:
            pre.append(f"({_GUARD_PRE[kind]}, lambda: {_script_expr(script)})")
        elif kind in _GUARD_POST:
            post.append(f"({_GUARD_POST[kind]}, lambda: {_script_stmt(script)})")
        else:
            raise NotImplementedError(
                f"guard {kind!r} has no py_trees mapping; use the C++/XML backend"
            )
    args = f"pre=[{', '.join(pre)}],\n    post=[{', '.join(post)}]"
    return f"_Guarded({name!r},\n" + _indent(expr, 1) + ",\n    " + args + ")"


def _scalar(lit):
    v = lit.toPython()
    return int(v) if isinstance(v, float) and v == int(v) else v


def _port(g, node, name):
    """Return a port's static value (scalar or seconds for a time quantity)."""
    for pn in g.objects(node, NS_BT.port):
        if str(g.value(pn, NS_BT["port-name"])) != name:
            continue
        qty = g.value(pn, URI_QUDT_PRED_VALUE)
        if qty is not None:
            return qty.toPython() * UNIT_SI[g.value(pn, URI_QUDT_PRED_UNIT)]
        val = g.value(pn, NS_BT["port-value"])
        return _scalar(val) if val is not None else None
    return None


def _name(g, node, default):
    n = g.value(node, NS_BT["instance-name"])
    return str(n) if n is not None else default


def _children(g, node):
    kids = [(int(g.value(c, NS_BT["child-index"])), c) for c in g.objects(node, NS_BT["has-child"])]
    return [c for _, c in sorted(kids)]


def _indent(text, level):
    pad = "    " * level
    return "\n".join(pad + line if line else line for line in text.splitlines())


def _decorator(g, node, child_expr, name):
    kind = str(g.value(node, NS_BT["decorator-kind"]))
    dec = "py_trees.decorators"
    if kind == "inverter":
        return f'{dec}.Inverter(name={name!r}, child={child_expr})'
    if kind == "force-success":
        return f'{dec}.FailureIsSuccess(name={name!r}, child={child_expr})'
    if kind == "force-failure":
        return f'{dec}.SuccessIsFailure(name={name!r}, child={child_expr})'
    if kind == "keep-running":
        return f'{dec}.SuccessIsRunning(name={name!r}, child={child_expr})'
    if kind == "run-once":
        return (f'{dec}.OneShot(name={name!r}, child={child_expr}, '
                'policy=py_trees.common.OneShotPolicy.ON_COMPLETION)')
    if kind == "retry":
        return f'{dec}.Retry(name={name!r}, child={child_expr}, num_failures={int(_port(g, node, "num_attempts"))})'
    if kind == "repeat":
        return f'{dec}.Repeat(name={name!r}, child={child_expr}, num_success={int(_port(g, node, "num_cycles"))})'
    if kind == "timeout":
        return f'{dec}.Timeout(name={name!r}, child={child_expr}, duration={float(_port(g, node, "msec"))})'
    raise NotImplementedError(f"decorator {kind!r} is not supported by the py_trees target")


def _render(g, node):
    expr = _render_node(g, node)
    if next(g.objects(node, NS_BT.guard), None) is not None:
        expr = _guard_wrap(g, node, expr, _name(g, node, "guarded"))
    return expr


def _render_node(g, node):
    types = set(g.objects(node, RDF.type))

    if NS_BT.Decorator in types:
        child = _render(g, _children(g, node)[0])
        return _decorator(g, node, child, _name(g, node, "decorator"))

    if NS_BT.SubTree in types:
        raise NotImplementedError("subtree nodes are not yet supported by the py_trees target")

    if NS_BT.FSMEvent in types:
        instance = g.value(node, NS_BT["on-fsm-instance"])
        inst = str(g.value(instance, NS_BT["instance-name"]))
        event = split_uri(g.value(node, NS_BT["of-event"]))[1]
        await_name = split_uri(g.value(node, NS_BT["await-target"]))[1]
        await_kind = str(g.value(node, NS_BT["await-kind"]))
        args = [f"runtime", f"{inst!r}", f"{event!r}", f"{await_name!r}", f"{await_kind!r}"]
        fail = g.value(node, NS_BT["fail-target"])
        if fail is not None:
            args += [f"on_fail={split_uri(fail)[1]!r}", f"on_fail_kind={str(g.value(node, NS_BT['fail-kind']))!r}"]
        name = _name(g, node, f"{inst}.{event}")
        return f"_FSMEvent({name!r}, " + ", ".join(args) + ")"

    if NS_BT.Leaf in types:
        beh = g.value(node, NS_BT["of-behaviour"])
        bname = str(g.value(beh, NS_BT["behaviour-name"]))
        name = _name(g, node, bname)
        if bname in _BUILTIN_LEAF:
            return f"{_BUILTIN_LEAF[bname]}(name={name!r})"
        if bname in BUILTIN_TAG:
            raise NotImplementedError(f"builtin leaf {bname!r} is not supported by the py_trees target")
        ports = {str(g.value(pn, NS_BT["port-name"])): _port(g, node, str(g.value(pn, NS_BT["port-name"])))
                 for pn in g.objects(node, NS_BT.port)}
        method = f"on_{get_valid_var_name(bname)}"
        return f"_Leaf({name!r}, runtime, {method!r}, {ports!r})"

    # composite
    kind = str(g.value(node, NS_BT["node-kind"]))
    children = _children(g, node)
    body = ",\n".join(_render(g, c) for c in children)
    block = "children=[\n" + _indent(body, 1) + ",\n]"
    name = _name(g, node, kind)
    if kind in _SEQUENCE:
        cls, extra = "py_trees.composites.Sequence", _SEQUENCE[kind]
    elif kind in _SELECTOR:
        cls, extra = "py_trees.composites.Selector", _SELECTOR[kind]
    elif kind in _PARALLEL:
        cls, extra = "py_trees.composites.Parallel", _PARALLEL[kind]
    else:
        raise NotImplementedError(f"composite {kind!r} is not supported by the py_trees target")
    inner = f"name={name!r}, {extra},\n" + _indent(block, 1) + ",\n"
    return f"{cls}(\n" + _indent(inner, 1) + ")"


def render_tree(g, root_ref):
    """Return the py_trees construction expression for the main tree's root."""
    return _render(g, g.value(root_ref, NS_BT.root))
