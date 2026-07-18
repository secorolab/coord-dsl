"""
This is an auto-generated file. Do not edit it directly.

FSM: left_arm
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
    TAKE_POSE = 0
    TAKE_POSE_DONE = auto()
    PLACE = auto()
    PLACE_DONE = auto()


# State IDs
class StateID(IntEnum):
    IDLE = 0
    MOVING_TO_TAKE_POSE = auto()
    AT_TAKE_POSE = auto()
    PLACING = auto()
    PLACED = auto()


# Transition IDs
class TransitionID(IntEnum):
    MOVE_TAKE_POSE = 0
    FINISH_TAKE_POSE = auto()
    START_PLACE = auto()
    FINISH_PLACE = auto()


# Event reaction IDs
class ReactionID(IntEnum):
    ON_TAKE_POSE = 0
    ON_TAKE_POSE_DONE = auto()
    ON_PLACE = auto()
    ON_PLACE_DONE = auto()


# URI mappings
STATE_URIS: dict[StateID, str] = {
    StateID.IDLE: "https://secorolab.github.io/models/coordination/fsm/left-arm/IDLE",
    StateID.MOVING_TO_TAKE_POSE: "https://secorolab.github.io/models/coordination/fsm/left-arm/MOVING_TO_TAKE_POSE",
    StateID.AT_TAKE_POSE: "https://secorolab.github.io/models/coordination/fsm/left-arm/AT_TAKE_POSE",
    StateID.PLACING: "https://secorolab.github.io/models/coordination/fsm/left-arm/PLACING",
    StateID.PLACED: "https://secorolab.github.io/models/coordination/fsm/left-arm/PLACED",
}

EVENT_URIS: dict[EventID, str] = {
    EventID.TAKE_POSE: "https://secorolab.github.io/models/coordination/fsm/left-arm/TAKE_POSE",
    EventID.TAKE_POSE_DONE: "https://secorolab.github.io/models/coordination/fsm/left-arm/TAKE_POSE_DONE",
    EventID.PLACE: "https://secorolab.github.io/models/coordination/fsm/left-arm/PLACE",
    EventID.PLACE_DONE: "https://secorolab.github.io/models/coordination/fsm/left-arm/PLACE_DONE",
}

TRANSITION_URIS: dict[TransitionID, str] = {
    TransitionID.MOVE_TAKE_POSE: "https://secorolab.github.io/models/coordination/fsm/left-arm/MOVE_TAKE_POSE",
    TransitionID.FINISH_TAKE_POSE: "https://secorolab.github.io/models/coordination/fsm/left-arm/FINISH_TAKE_POSE",
    TransitionID.START_PLACE: "https://secorolab.github.io/models/coordination/fsm/left-arm/START_PLACE",
    TransitionID.FINISH_PLACE: "https://secorolab.github.io/models/coordination/fsm/left-arm/FINISH_PLACE",
}

REACTION_URIS: dict[ReactionID, str] = {
    ReactionID.ON_TAKE_POSE: "https://secorolab.github.io/models/coordination/fsm/left-arm/ON_TAKE_POSE",
    ReactionID.ON_TAKE_POSE_DONE: "https://secorolab.github.io/models/coordination/fsm/left-arm/ON_TAKE_POSE_DONE",
    ReactionID.ON_PLACE: "https://secorolab.github.io/models/coordination/fsm/left-arm/ON_PLACE",
    ReactionID.ON_PLACE_DONE: "https://secorolab.github.io/models/coordination/fsm/left-arm/ON_PLACE_DONE",
}


def create_fsm() -> FSMData:
    """Creates the FSM data structure."""
    # Transitions
    trans_dict = {
        TransitionID.MOVE_TAKE_POSE: Transition(StateID.IDLE, StateID.MOVING_TO_TAKE_POSE),
        TransitionID.FINISH_TAKE_POSE: Transition(StateID.MOVING_TO_TAKE_POSE, StateID.AT_TAKE_POSE),
        TransitionID.START_PLACE: Transition(StateID.AT_TAKE_POSE, StateID.PLACING),
        TransitionID.FINISH_PLACE: Transition(StateID.PLACING, StateID.PLACED),
    }
    trans_list = [trans_dict[i] for i in TransitionID]

    # Event Reactions
    evt_reaction_dict = {
        ReactionID.ON_TAKE_POSE: EventReaction(
            condition_event_index=EventID.TAKE_POSE,
            transition_index=TransitionID.MOVE_TAKE_POSE,
            fired_event_indices=[],
        ),
        ReactionID.ON_TAKE_POSE_DONE: EventReaction(
            condition_event_index=EventID.TAKE_POSE_DONE,
            transition_index=TransitionID.FINISH_TAKE_POSE,
            fired_event_indices=[],
        ),
        ReactionID.ON_PLACE: EventReaction(
            condition_event_index=EventID.PLACE,
            transition_index=TransitionID.START_PLACE,
            fired_event_indices=[],
        ),
        ReactionID.ON_PLACE_DONE: EventReaction(
            condition_event_index=EventID.PLACE_DONE,
            transition_index=TransitionID.FINISH_PLACE,
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
        end_state_index     = StateID.PLACED,
        transitions         = trans_list,
        event_reactions     = evt_reaction_list,
        current_state_index = StateID.IDLE,
    )