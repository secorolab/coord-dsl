"""
This is an auto-generated file. Do not edit it directly.

FSM: right_arm
FSM Description: 

Examples:

>>> from coord_dsl.fsm import fsm_step
>>> from coord_dsl.event_loop import reconfig_event_buffers
>>> from fsm_example import create_fsm
>>> fsm = create_fsm()
>>> while True:
...     if fsm.current_state_index == StateID.S_EXIT:
...         print("State machine completed successfully")
...         break
...     fsm_behavior(fsm, ud) # user-defined behaviour with user data
...     fsm_step(fsm)
...     reconfig_event_buffers(fsm.event_data)
"""
from enum import IntEnum, auto
from coord_dsl.event_loop import EventData
from coord_dsl.fsm import FSMData, Transition, EventReaction


# Event IDs
class EventID(IntEnum):
    PICK = 0
    PICK_DONE = auto()
    HANDOVER = auto()
    HANDOVER_DONE = auto()


# State IDs
class StateID(IntEnum):
    IDLE = 0
    PICKING = auto()
    PICKED = auto()
    MOVING_HANDOVER = auto()
    HANDOVER_POSE = auto()


# Transition IDs
class TransitionID(IntEnum):
    PICK_OBJECT = 0
    FINISH_PICK = auto()
    START_HANDOVER = auto()
    FINISH_HANDOVER = auto()


# Event reaction IDs
class ReactionID(IntEnum):
    ON_PICK = 0
    ON_PICK_DONE = auto()
    ON_HANDOVER = auto()
    ON_HANDOVER_DONE = auto()


# URI mappings
STATE_URIS: dict[StateID, str] = {
    StateID.IDLE: "https://secorolab.github.io/models/coordination/fsm/right-arm/IDLE",
    StateID.PICKING: "https://secorolab.github.io/models/coordination/fsm/right-arm/PICKING",
    StateID.PICKED: "https://secorolab.github.io/models/coordination/fsm/right-arm/PICKED",
    StateID.MOVING_HANDOVER: "https://secorolab.github.io/models/coordination/fsm/right-arm/MOVING_HANDOVER",
    StateID.HANDOVER_POSE: "https://secorolab.github.io/models/coordination/fsm/right-arm/HANDOVER_POSE",
}

EVENT_URIS: dict[EventID, str] = {
    EventID.PICK: "https://secorolab.github.io/models/coordination/fsm/right-arm/PICK",
    EventID.PICK_DONE: "https://secorolab.github.io/models/coordination/fsm/right-arm/PICK_DONE",
    EventID.HANDOVER: "https://secorolab.github.io/models/coordination/fsm/right-arm/HANDOVER",
    EventID.HANDOVER_DONE: "https://secorolab.github.io/models/coordination/fsm/right-arm/HANDOVER_DONE",
}

TRANSITION_URIS: dict[TransitionID, str] = {
    TransitionID.PICK_OBJECT: "https://secorolab.github.io/models/coordination/fsm/right-arm/PICK_OBJECT",
    TransitionID.FINISH_PICK: "https://secorolab.github.io/models/coordination/fsm/right-arm/FINISH_PICK",
    TransitionID.START_HANDOVER: "https://secorolab.github.io/models/coordination/fsm/right-arm/START_HANDOVER",
    TransitionID.FINISH_HANDOVER: "https://secorolab.github.io/models/coordination/fsm/right-arm/FINISH_HANDOVER",
}

REACTION_URIS: dict[ReactionID, str] = {
    ReactionID.ON_PICK: "https://secorolab.github.io/models/coordination/fsm/right-arm/ON_PICK",
    ReactionID.ON_PICK_DONE: "https://secorolab.github.io/models/coordination/fsm/right-arm/ON_PICK_DONE",
    ReactionID.ON_HANDOVER: "https://secorolab.github.io/models/coordination/fsm/right-arm/ON_HANDOVER",
    ReactionID.ON_HANDOVER_DONE: "https://secorolab.github.io/models/coordination/fsm/right-arm/ON_HANDOVER_DONE",
}


def create_fsm() -> FSMData:
    """Creates the FSM data structure."""
    # Transitions
    trans_dict = {
        TransitionID.PICK_OBJECT: Transition(StateID.IDLE, StateID.PICKING),
        TransitionID.FINISH_PICK: Transition(StateID.PICKING, StateID.PICKED),
        TransitionID.START_HANDOVER: Transition(StateID.PICKED, StateID.MOVING_HANDOVER),
        TransitionID.FINISH_HANDOVER: Transition(StateID.MOVING_HANDOVER, StateID.HANDOVER_POSE),
    }
    trans_list = [trans_dict[i] for i in TransitionID]

    # Event Reactions
    evt_reaction_dict = {
        ReactionID.ON_PICK: EventReaction(
            condition_event_index=EventID.PICK,
            transition_index=TransitionID.PICK_OBJECT,
            fired_event_indices=[],
        ),
        ReactionID.ON_PICK_DONE: EventReaction(
            condition_event_index=EventID.PICK_DONE,
            transition_index=TransitionID.FINISH_PICK,
            fired_event_indices=[],
        ),
        ReactionID.ON_HANDOVER: EventReaction(
            condition_event_index=EventID.HANDOVER,
            transition_index=TransitionID.START_HANDOVER,
            fired_event_indices=[],
        ),
        ReactionID.ON_HANDOVER_DONE: EventReaction(
            condition_event_index=EventID.HANDOVER_DONE,
            transition_index=TransitionID.FINISH_HANDOVER,
            fired_event_indices=[],
        ),
    }
    evt_reaction_list = [evt_reaction_dict[i] for i in ReactionID]

    # Events
    events = EventData(len(EventID))

    # Return FSM instance
    return FSMData(
        event_data          = events,
        num_states          = len(StateID),
        start_state_index   = StateID.IDLE,
        end_state_index     = StateID.HANDOVER_POSE,
        transitions         = trans_list,
        event_reactions     = evt_reaction_list,
        current_state_index = StateID.IDLE,
    )