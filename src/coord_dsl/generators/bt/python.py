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

Sub-trees are expanded here rather than at run time: each instance renders the
referenced tree under its own :class:`_Scope`, which maps the keys written in
the model to the keys emitted. A declared parameter takes the caller's binding
(a key or a literal); every other key is prefixed with the instance name, so
two instances of one sub-tree share no blackboard state -- BT.CPP's per-
sub-tree blackboard, resolved statically.
"""

import re

from rdflib import Namespace, RDF
from rdflib.namespace import split_uri
from rdf_utils.models.vocab import URI_QUDT_PRED_UNIT, URI_QUDT_PRED_VALUE
from rdf_utils.naming import get_valid_var_name

from coord_dsl.generators.bt.graph import URI_MM_BT, URI_MM_DATAFLOW
from coord_dsl.generators.bt.xml import BUILTIN_TAG, UNIT_SI

NS_BT = Namespace(URI_MM_BT)
NS_DF = Namespace(URI_MM_DATAFLOW)

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


class _Ref:
    """A port bound to a blackboard key. Rendered as the runtime's ``_Key``,
    which the leaf resolves when it ticks."""

    def __init__(self, key):
        self.key = key

    def __repr__(self):
        return f"_Key({self.key!r})"


class _Scope:
    """Maps a blackboard key as written in the model to the key (or literal)
    it resolves to. Identity for the main tree; inside a sub-tree instance the
    declared parameters take the caller's binding and every other key is
    private to that instance, mirroring BT.CPP's per-sub-tree blackboard."""

    def __init__(self, bindings=None, prefix=""):
        self._bindings = bindings or {}
        self._prefix = prefix

    def resolve(self, name):
        """Return an ``_Ref`` to the emitted key, or the literal bound to it."""
        if name in self._bindings:
            return self._bindings[name]
        return _Ref(self._prefix + name)


ROOT_SCOPE = _Scope()


def _script_read(scope, name):
    """A guard-script identifier: the scope's literal, or a blackboard read."""
    resolved = scope.resolve(name)
    return f"_bb_get({resolved.key!r})" if isinstance(resolved, _Ref) else repr(resolved)


def _script_expr(script, scope=ROOT_SCOPE):
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
            out.append(_SCRIPT_KEYWORD.get(tok) or _script_read(scope, tok))
        else:
            tok = m.group(m.lastgroup)
            out.append(_SCRIPT_OP.get(tok, tok))
    return " ".join(out)


def _script_stmt(script, scope=ROOT_SCOPE):
    """Translate a guard-script assignment (``key := expr``) to Python."""
    key, sep, value = script.partition(":=")
    key = key.strip()
    if not sep or not re.fullmatch(r"[^\d\W][\w-]*", key):
        raise NotImplementedError(
            f"guard script {script!r} is outside the supported subset "
            "(expected a single 'key := expr' assignment)"
        )
    target = scope.resolve(key)
    if not isinstance(target, _Ref):
        raise NotImplementedError(
            f"guard script {script!r} assigns to {key!r}, which the caller bound "
            "to a literal; bind it to a blackboard key instead"
        )
    return f"_bb_set({target.key!r}, {_script_expr(value, scope)})"


def _guard_wrap(g, node, expr, name, scope):
    pre, post = [], []
    for gn in sorted(g.objects(node, NS_BT.guard), key=str):
        kind = str(g.value(gn, NS_BT["guard-kind"]))
        script = str(g.value(gn, NS_BT["guard-script"]))
        if kind in _GUARD_PRE:
            pre.append(f"({_GUARD_PRE[kind]}, lambda: {_script_expr(script, scope)})")
        elif kind in _GUARD_POST:
            post.append(f"({_GUARD_POST[kind]}, lambda: {_script_stmt(script, scope)})")
        else:
            raise NotImplementedError(
                f"guard {kind!r} has no py_trees mapping; use the C++/XML backend"
            )
    args = f"pre=[{', '.join(pre)}],\n    post=[{', '.join(post)}]"
    return f"_Guarded({name!r},\n" + _indent(expr, 1) + ",\n    " + args + ")"


def _scalar(lit):
    v = lit.toPython()
    return int(v) if isinstance(v, float) and v == int(v) else v


def _port(g, node, name, scope=ROOT_SCOPE):
    """Return a port's value: a scalar, seconds for a time quantity, or an
    ``_Ref`` when it is bound to a blackboard key."""
    for pn in g.objects(node, NS_DF["has-argument"]):
        if str(g.value(pn, NS_DF.name)) != name:
            continue
        ref = g.value(pn, NS_DF.references)
        if ref is not None:
            return scope.resolve(str(g.value(ref, NS_DF.name)))
        qty = g.value(pn, URI_QUDT_PRED_VALUE)
        if qty is not None:
            return qty.toPython() * UNIT_SI[g.value(pn, URI_QUDT_PRED_UNIT)]
        val = g.value(pn, RDF.value)
        return _scalar(val) if val is not None else None
    return None


def _static_port(g, node, name, kind):
    """A port that must be known at generation time (decorator configuration)."""
    value = _port(g, node, name)
    if isinstance(value, _Ref):
        raise NotImplementedError(
            f"{kind} port {name!r} is bound to blackboard key {value.key!r}; the "
            "py_trees target needs it at generation time"
        )
    return value


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
        return f'{dec}.Retry(name={name!r}, child={child_expr}, num_failures={int(_static_port(g, node, "num_attempts", kind))})'
    if kind == "repeat":
        return f'{dec}.Repeat(name={name!r}, child={child_expr}, num_success={int(_static_port(g, node, "num_cycles", kind))})'
    if kind == "timeout":
        return f'{dec}.Timeout(name={name!r}, child={child_expr}, duration={float(_static_port(g, node, "msec", kind))})'
    raise NotImplementedError(f"decorator {kind!r} is not supported by the py_trees target")


def _subtree_scope(g, node, tree, scope, name):
    """Bind a sub-tree instance's parameters to the caller's arguments. Keys the
    caller did not bind stay private to this instance, so two instances of the
    same sub-tree never share blackboard state -- unless the instance is
    declared ``autoremap``, where an unbound key is the caller's key of the
    same name."""
    bindings = {}
    for pn in g.objects(tree, NS_DF["has-parameter"]):
        param = str(g.value(pn, NS_DF.name))
        if next((a for a in g.objects(node, NS_DF["has-argument"])
                 if str(g.value(a, NS_DF.name)) == param), None) is not None:
            bindings[param] = _port(g, node, param, scope)
    prefix = "" if g.value(node, NS_BT["auto-remap"]) else f"{name}/"
    return _Scope(bindings, prefix=prefix)


def _render(g, node, scope=ROOT_SCOPE, expanding=()):
    expr = _render_node(g, node, scope, expanding)
    if next(g.objects(node, NS_BT.guard), None) is not None:
        expr = _guard_wrap(g, node, expr, _name(g, node, "guarded"), scope)
    return expr


def _render_node(g, node, scope=ROOT_SCOPE, expanding=()):
    types = set(g.objects(node, RDF.type))

    if NS_BT.Decorator in types:
        child = _render(g, _children(g, node)[0], scope, expanding)
        return _decorator(g, node, child, _name(g, node, "decorator"))

    if NS_BT.SubTree in types:
        tree = g.value(node, NS_BT["of-tree"])
        tree_name = str(g.value(tree, NS_BT["behaviour-tree-name"]))
        if tree in expanding:
            raise NotImplementedError(
                f"sub-tree {tree_name!r} is recursive; the py_trees target expands "
                "sub-trees at generation time and cannot expand a cycle"
            )
        name = _name(g, node, tree_name)
        child_scope = _subtree_scope(g, node, tree, scope, name)
        return _render(g, g.value(tree, NS_BT.root), child_scope, expanding + (tree,))

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
        ports = {str(g.value(pn, NS_DF.name)): _port(g, node, str(g.value(pn, NS_DF.name)), scope)
                 for pn in g.objects(node, NS_DF["has-argument"])}
        method = f"on_{get_valid_var_name(bname)}"
        return f"_Leaf({name!r}, runtime, {method!r}, {ports!r})"

    # composite
    kind = str(g.value(node, NS_BT["node-kind"]))
    children = _children(g, node)
    body = ",\n".join(_render(g, c, scope, expanding) for c in children)
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
