# SPDX-License-Identifier: MPL-2.0
# Author: Minh Nguyen

from typing import cast

from typing import Protocol

from rdflib import Namespace, URIRef


class NamespaceDecl(Protocol):
    name: str
    uri: str


class IHasParent(object):
    parent: object

    def __init__(self, *, parent: object) -> None:
        self.parent = parent


class IHasNamespace(IHasParent):
    def __init__(self, *, parent: object) -> None:
        super().__init__(parent=parent)

    @property
    def namespace(self) -> Namespace:
        raise NotImplementedError(
            f"'namespace' property not implemented for '{self.__class__.__name__}'"
        )


class IHasNamespaceDeclare(IHasNamespace):
    uri: URIRef
    ns: NamespaceDecl
    name: str
    ns_prefix: str
    _ns_obj: Namespace

    def __init__(self, *, parent: object, ns: NamespaceDecl, name: str) -> None:
        super().__init__(parent=parent)
        self.ns = ns
        self.ns_prefix = self.ns.name
        self.name = name

        self._ns_obj = Namespace(self.ns.uri)
        self.uri = self._ns_obj[self.name]

    @property
    def namespace(self) -> Namespace:
        return self._ns_obj


class NamedNamespaceObject(IHasNamespace):
    name: str
    _uri: str

    def __init__(self, parent: IHasNamespace, name: str):
        super().__init__(parent=parent)
        self.name = name
        self._uri = ""

    @property
    def namespace(self) -> Namespace:
        return Namespace(cast(IHasNamespace, self.parent).namespace)

    @property
    def uri(self) -> str:
        if self._uri == "":
            self._uri = self.namespace[self.name]
        return self._uri
