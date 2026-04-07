from __future__ import annotations
from typing import Optional


class NamespaceDeclare:
    def __init__(self, **kwargs):
        self.name: str = kwargs.get("name", "")
        self.uri: str = kwargs.get("uri", "")


class State:
    def __init__(self, **kwargs):
        self.name: str = kwargs.get("name", "")
        self.uri: str = ""


class Event:
    def __init__(self, **kwargs):
        self.name: str = kwargs.get("name", "")
        self.uri: str = ""


class Transition:
    def __init__(self, **kwargs):
        self.name: str = kwargs.get("name", "")
        self.from_state: State = kwargs.get("from_state", State())
        self.to_state: State = kwargs.get("to_state", State())
        self.uri: str = ""


class FiredEvent:
    def __init__(self, **kwargs):
        self.event: Optional[Event] = kwargs.get("event")


class Reaction:
    def __init__(self, **kwargs):
        self.name: str = kwargs.get("name", "")
        self.when: Event = kwargs.get("when", Event())
        self.do: Transition = kwargs.get("do", Transition())
        self.fires: list[FiredEvent] = kwargs.get("fires", [])
        self.uri: str = ""

    @property
    def fired_events(self) -> list[Event]:
        return [f.event for f in self.fires if f.event is not None]


class FSM:
    def __init__(self, **kwargs):
        self.namespace: NamespaceDeclare = kwargs.get("namespace", NamespaceDeclare())
        self.name: str = kwargs.get("name", "")
        self.description: Optional[str] = kwargs.get("description")
        self.states: list[State] = kwargs.get("states", [])
        self.start_state: State = kwargs.get("start_state", State())
        self.end_state: State = kwargs.get("end_state", State())
        self.events: list[Event] = kwargs.get("events", [])
        self.transitions: list[Transition] = kwargs.get("transitions", [])
        self.reactions: list[Reaction] = kwargs.get("reactions", [])
        self.uri: str = ""

    def _all_entities(self) -> list:
        return self.states + self.events + self.transitions + self.reactions
