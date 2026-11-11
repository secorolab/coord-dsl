# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)

from __future__ import annotations

from coord_dsl.classes.common import IHasNamespaceDeclare, IInheritNamespace


class BehaviourSet(IHasNamespaceDeclare):
    behaviours: list[BehaviourDecl]

    def __init__(self, parent, ns, name, behaviours) -> None:
        super().__init__(parent=parent, ns=ns, name=name)
        self.behaviours = behaviours


class BehaviourDecl(IInheritNamespace):
    def __init__(self, parent, name):
        super().__init__(parent=parent, name=name)


class BehaviourTree(IHasNamespaceDeclare):
    def __init__(self, parent, ns, name, root) -> None:
        super().__init__(parent=parent, ns=ns, name=name)
        self.root = root
