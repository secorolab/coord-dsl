# SPDX-License-Identifier: MPL-2.0
# Author: Minh Nguyen

import shutil
import subprocess
from pathlib import Path

from rdflib import Namespace, URIRef


def clang_format_file(path):
    """Format a generated C++ file in place using the nearest `.clang-format`.

    No-op when clang-format is unavailable or no style file is found upward
    (e.g. output written to a temp dir), so callers stay side-effect-free there.
    """
    path = Path(path)
    style = next(
        (p / ".clang-format" for p in path.resolve().parents if (p / ".clang-format").is_file()),
        None,
    )
    if style is None or shutil.which("clang-format") is None:
        return
    subprocess.run(
        ["clang-format", "-i", f"--style=file:{style}", "-fallback-style=none", str(path)],
        check=False,
    )


def write_dot(dot_source, output_path, img_format):
    """Write a graphviz graph, rendering it to an image unless the format is `dot`."""
    if img_format == "dot":
        Path(output_path).write_text(dot_source)
        return
    if shutil.which("dot") is None:
        raise ValueError(f"graphviz is needed to write {img_format!r}: no 'dot' on PATH")
    subprocess.run(
        ["dot", f"-T{img_format}", "-o", str(output_path)],
        input=dot_source, text=True, check=True,
    )


class IHasParent(object):
    def __init__(self, **kwargs) -> None:
        self.parent = kwargs.get("parent", None)
        assert self.parent is not None, f"'parent' not handled for type '{self.__class__.__name__}'"


class IHasNamespace(IHasParent):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    @property
    def namespace(self) -> Namespace:
        raise NotImplementedError(
            f"'namespace' property not implemented for '{self.__class__.__name__}'"
        )


class IHasNamespaceDeclare(IHasNamespace):
    uri: URIRef
    ns_prefix: str
    _ns_obj: Namespace

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.ns = kwargs.get("ns", None)
        assert self.ns is not None
        self.ns_prefix = self.ns.name

        self.name = kwargs.get("name", None)
        assert self.name is not None

        self._ns_obj = Namespace(self.ns.uri)
        self.uri = self._ns_obj[self.name]

    @property
    def namespace(self) -> Namespace:
        return self._ns_obj


class NamedNamespaceObject(IHasNamespace):
    def __init__(self, parent, name, **kwargs):
        del kwargs
        super().__init__(parent=parent)
        self.name = name
        self._uri = ""

    @property
    def namespace(self) -> Namespace:
        assert self.parent is not None, f"'parent' not set for '{self.__class__.__name__}'"
        return Namespace(self.parent.namespace)

    @property
    def uri(self) -> str:
        if self._uri == "":
            self._uri = self.namespace[self.name]
        return self._uri
