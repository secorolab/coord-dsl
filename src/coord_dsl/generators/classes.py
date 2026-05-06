from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from coord_dsl.generators.common import (
    IHasNamespaceDeclare,
    NamedNamespaceObject,
    NamespaceDecl,
)


class State(NamedNamespaceObject):
    pass


class Event(NamedNamespaceObject):
    pass


class Transition(NamedNamespaceObject):
    def __init__(
        self,
        parent: IHasNamespaceDeclare,
        name: str,
        from_state: State,
        to_state: State,
    ):
        super().__init__(parent=parent, name=name)
        self.from_state: State = from_state
        self.to_state: State = to_state


class FiredEvent:
    def __init__(self, parent: object | None = None, event: Optional[Event] = None):
        self.parent = parent
        self.event = event


class Reaction(NamedNamespaceObject):
    def __init__(
        self,
        parent: IHasNamespaceDeclare,
        name: str,
        when: Event,
        do: Transition,
        fires: list[FiredEvent],
    ):
        super().__init__(parent=parent, name=name)
        self.when: Event = when
        self.do: Transition = do
        self.fires: list[FiredEvent] = fires

    @property
    def fired_events(self) -> list[Event]:
        return [f.event for f in self.fires if f.event is not None]


class FSM(IHasNamespaceDeclare):
    def __init__(
        self,
        parent: object,
        ns: NamespaceDecl,
        name: str,
        description: Optional[str],
        states: list[State],
        start_state: State,
        end_state: State,
        events: list[Event],
        transitions: list[Transition],
        reactions: list[Reaction],
    ):
        super().__init__(parent=parent, ns=ns, name=name)
        self.description: Optional[str] = description
        self.states: list[State] = states
        self.start_state: State = start_state
        self.end_state: State = end_state
        self.events: list[Event] = events
        self.transitions: list[Transition] = transitions
        self.reactions: list[Reaction] = reactions

    def _all_entities(self) -> Sequence[NamedNamespaceObject]:
        return self.states + self.events + self.transitions + self.reactions
