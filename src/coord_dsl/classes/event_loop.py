from __future__ import annotations
from coord_dsl.classes.common import IHasNamespaceDeclare, IInheritNamespace


class EventLoop(IHasNamespaceDeclare):
    events: list[Event]

    def __init__(self, parent, ns, name, events) -> None:
        super().__init__(parent=parent, ns=ns, name=name)
        self.events = events


class Event(IInheritNamespace):
    def __init__(self, parent, name):
        super().__init__(parent=parent, name=name)


class EventRef:
    def __init__(self, parent, event):
        self.parent = parent
        self.event: Event = event
