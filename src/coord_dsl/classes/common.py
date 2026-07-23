# SPDX-License-Identifier: MPL-2.0
# Author: Minh Nguyen

from typing import Optional
from rdflib import Namespace, URIRef


class IHasParent(object):
    def __init__(self, **kwargs) -> None:
        self.parent = kwargs.get("parent", None)
        assert (
            self.parent is not None
        ), f"'parent' not handled for type '{self.__class__.__name__}'"


class IHasNamespace(IHasParent):
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


class IInheritNamespace(IHasNamespace):
    _uri: Optional[URIRef]

    def __init__(self, parent, name, **kwargs):
        super().__init__(parent=parent)
        self.name = name
        self._uri = None

    @property
    def namespace(self) -> Namespace:
        if not isinstance(self.parent, IHasNamespace):
            raise ValueError(
                f"parent of '{self.name}' ({self.__class__.__name__}) not an instance of"
                f" IHasNamespace: {self.parent}"
            )
        return self.parent.namespace

    @property
    def uri(self) -> URIRef:
        if self._uri is None:
            self._uri = self.namespace[self.name]
        return self._uri
