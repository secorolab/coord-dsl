"""
This is an auto-generated file. Do not edit it directly.

FSM: gripper
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
    GRASP = 0
    GRASPED_OK = auto()
    GRASP_FAULT = auto()


# State IDs
class StateID(IntEnum):
    IDLE = 0
    GRASPING = auto()
    GRASPED = auto()
    FAULT = auto()


# Transition IDs
class TransitionID(IntEnum):
    START_GRASP = 0
    FINISH_GRASP = auto()
    FAIL_GRASP = auto()


# Event reaction IDs
class ReactionID(IntEnum):
    ON_GRASP = 0
    ON_GRASPED_OK = auto()
    ON_GRASP_FAULT = auto()


# URI mappings
STATE_URIS: dict[StateID, str] = {
    StateID.IDLE: "https://secorolab.github.io/models/coordination/fsm/gripper/IDLE",
    StateID.GRASPING: "https://secorolab.github.io/models/coordination/fsm/gripper/GRASPING",
    StateID.GRASPED: "https://secorolab.github.io/models/coordination/fsm/gripper/GRASPED",
    StateID.FAULT: "https://secorolab.github.io/models/coordination/fsm/gripper/FAULT",
}

EVENT_URIS: dict[EventID, str] = {
    EventID.GRASP: "https://secorolab.github.io/models/coordination/fsm/gripper/GRASP",
    EventID.GRASPED_OK: "https://secorolab.github.io/models/coordination/fsm/gripper/GRASPED_OK",
    EventID.GRASP_FAULT: "https://secorolab.github.io/models/coordination/fsm/gripper/GRASP_FAULT",
}

TRANSITION_URIS: dict[TransitionID, str] = {
    TransitionID.START_GRASP: "https://secorolab.github.io/models/coordination/fsm/gripper/START_GRASP",
    TransitionID.FINISH_GRASP: "https://secorolab.github.io/models/coordination/fsm/gripper/FINISH_GRASP",
    TransitionID.FAIL_GRASP: "https://secorolab.github.io/models/coordination/fsm/gripper/FAIL_GRASP",
}

REACTION_URIS: dict[ReactionID, str] = {
    ReactionID.ON_GRASP: "https://secorolab.github.io/models/coordination/fsm/gripper/ON_GRASP",
    ReactionID.ON_GRASPED_OK: "https://secorolab.github.io/models/coordination/fsm/gripper/ON_GRASPED_OK",
    ReactionID.ON_GRASP_FAULT: "https://secorolab.github.io/models/coordination/fsm/gripper/ON_GRASP_FAULT",
}


def create_fsm() -> FSMData:
    """Creates the FSM data structure."""
    # Transitions
    trans_dict = {
        TransitionID.START_GRASP: Transition(StateID.IDLE, StateID.GRASPING),
        TransitionID.FINISH_GRASP: Transition(StateID.GRASPING, StateID.GRASPED),
        TransitionID.FAIL_GRASP: Transition(StateID.GRASPING, StateID.FAULT),
    }
    trans_list = [trans_dict[i] for i in TransitionID]

    # Event Reactions
    evt_reaction_dict = {
        ReactionID.ON_GRASP: EventReaction(
            condition_event_index=EventID.GRASP,
            transition_index=TransitionID.START_GRASP,
            fired_event_indices=[],
        ),
        ReactionID.ON_GRASPED_OK: EventReaction(
            condition_event_index=EventID.GRASPED_OK,
            transition_index=TransitionID.FINISH_GRASP,
            fired_event_indices=[],
        ),
        ReactionID.ON_GRASP_FAULT: EventReaction(
            condition_event_index=EventID.GRASP_FAULT,
            transition_index=TransitionID.FAIL_GRASP,
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
        end_state_index     = StateID.GRASPED,
        transitions         = trans_list,
        event_reactions     = evt_reaction_list,
        current_state_index = StateID.IDLE,
    )