# SPDX-License-Identifier: MPL-2.0
"""RDF vocabulary used by coord-dsl."""

from rdflib import Namespace
from rdf_utils.namespace import URL_SECORO_MM


NS_MM_FSM = Namespace(f"{URL_SECORO_MM}/behaviour/fsm#")

URI_FSM_TYPE_FSM = NS_MM_FSM["FiniteStateMachine"]
URI_FSM_TYPE_STATE = NS_MM_FSM["State"]
URI_FSM_TYPE_TRANSITION = NS_MM_FSM["Transition"]
URI_FSM_TYPE_REACTION = NS_MM_FSM["Reaction"]

URI_FSM_PRED_NAME = NS_MM_FSM["name"]
URI_FSM_PRED_DESCRIPTION = NS_MM_FSM["description"]
URI_FSM_PRED_START_STATE = NS_MM_FSM["start-state"]
URI_FSM_PRED_END_STATE = NS_MM_FSM["end-state"]
URI_FSM_PRED_CURRENT_STATE = NS_MM_FSM["current-state"]
URI_FSM_PRED_STATES = NS_MM_FSM["states"]
URI_FSM_PRED_TRANSITIONS = NS_MM_FSM["transitions"]
URI_FSM_PRED_REACTIONS = NS_MM_FSM["reactions"]
URI_FSM_PRED_TRANSITION_FROM = NS_MM_FSM["transition-from"]
URI_FSM_PRED_TRANSITION_TO = NS_MM_FSM["transition-to"]
URI_FSM_PRED_DO_TRANSITION = NS_MM_FSM["do-transition"]
URI_FSM_PRED_FIRES_EVENTS = NS_MM_FSM["fires-events"]


NS_MM_BT = Namespace(f"{URL_SECORO_MM}/behaviour/behaviour-tree#")

URI_BT_TYPE_TREE = NS_MM_BT["BehaviourTree"]
URI_BT_TYPE_SEQUENCE = NS_MM_BT["Sequence"]
URI_BT_TYPE_SELECTOR = NS_MM_BT["Selector"]
URI_BT_TYPE_PARALLEL = NS_MM_BT["Parallel"]
URI_BT_TYPE_ACTION = NS_MM_BT["Action"]
URI_BT_TYPE_CONDITION = NS_MM_BT["Condition"]

URI_BT_PRED_ROOT = NS_MM_BT["root"]
URI_BT_PRED_CHILDREN = NS_MM_BT["children"]
URI_BT_PRED_MEMORY = NS_MM_BT["memory"]
URI_BT_PRED_SUCCESS_THRESHOLD = NS_MM_BT["success-threshold"]
URI_BT_PRED_OF_ACTION = NS_MM_BT["of-action"]
