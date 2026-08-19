from __future__ import annotations
from coord_dsl.classes.common import IHasNamespaceDeclare, IInheritNamespace


class EventLoop(IHasNamespaceDeclare):
    events: list[Event]
    flags: list[Flag]

    def __init__(self, parent, ns, name, members) -> None:
        super().__init__(parent=parent, ns=ns, name=name)
        self.members = members
        self.events = [m for m in members if isinstance(m, Event)]
        self.flags = [m for m in members if isinstance(m, Flag)]


class Event(IInheritNamespace):
    def __init__(self, parent, name):
        super().__init__(parent=parent, name=name)


class Flag(IInheritNamespace):
    def __init__(self, parent, name):
        super().__init__(parent=parent, name=name)


class EventRef:
    def __init__(self, parent, event):
        self.parent = parent
        self.event: Event = event
