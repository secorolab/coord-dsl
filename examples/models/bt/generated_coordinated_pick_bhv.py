#!/usr/bin/env python3
"""Example of a generated behaviour tree ticking a generated state machine as one of its nodes.

The tree approaches the object, runs the pick_coordination FSM until the grasp holds, then lifts
under a check that the grasp still holds. The FSM's state behaviours move the user data, and a
monitor turns that data into the flags the tree's conditions read.

SPDX-License-Identifier: MPL-2.0
"""

import signal
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

import py_trees
from coord_dsl.event_loop import produce_event, reconfig_event_buffers
from coord_dsl.fsm import FSMData, fsm_step

from coordinated_pick import ACTION_IRI, FLAG_IRI, FSM_IRI, coordinated_pick
from pick_coordination import STATE_URIS, EventID, StateID, create_fsm

LOOP_DURATION = 0.01
RUNNING = py_trees.common.Status.RUNNING
SUCCESS = py_trees.common.Status.SUCCESS


def signal_handler(sig, frame):
    del sig, frame
    print("You pressed Ctrl+C, exiting!")
    sys.exit(0)


@dataclass
class UserData:
    current_time: float
    speed: float                        # m/s, of the arm when approaching and lifting
    failed_grasps: int                  # grasps to fail before one holds
    detection_confidence: float = 0.9   # of the object detector
    min_confidence: float = 0.5         # below it, the object is not visible
    distance_to_object: float = 0.3     # m, from the gripper
    approach_tolerance: float = 0.005   # m
    gripper_width: float = 0.08         # m, open
    open_width: float = 0.08            # m
    object_width: float = 0.04          # m
    closing_speed: float = 0.05         # m/s
    grip_force: float = 0.0             # N
    force_rate: float = 40.0            # N/s, once the fingers touch the object
    min_grip_force: float = 10.0        # N, below it the object is not grasped
    height: float = 0.0                 # m, of the object above the table
    lift_height: float = 0.1            # m


def monitor(ud: UserData, board) -> None:
    """Derive the flags the conditions read from the user data."""
    board.object_visible = ud.detection_confidence >= ud.min_confidence
    board.object_grasped = ud.grip_force >= ud.min_grip_force


def approach(ud: UserData) -> py_trees.common.Status:
    ud.distance_to_object = max(0.0, ud.distance_to_object - ud.speed * LOOP_DURATION)
    return SUCCESS if ud.distance_to_object <= ud.approach_tolerance else RUNNING


def lift(ud: UserData) -> py_trees.common.Status:
    ud.height += ud.speed * LOOP_DURATION
    return SUCCESS if ud.height >= ud.lift_height else RUNNING


def perceive(fsm: FSMData, ud: UserData) -> None:
    if ud.detection_confidence >= ud.min_confidence:
        produce_event(fsm.event_data, EventID.E_PERCEIVED)


def pick_step(fsm: FSMData, ud: UserData) -> None:
    if ud.gripper_width > ud.object_width:
        ud.gripper_width = max(ud.object_width, ud.gripper_width - ud.closing_speed * LOOP_DURATION)
        return
    if ud.failed_grasps:
        ud.failed_grasps -= 1
        print("  grasp slipped")
        produce_event(fsm.event_data, EventID.E_FAILED)
        return
    ud.grip_force += ud.force_rate * LOOP_DURATION
    if ud.grip_force >= ud.min_grip_force:
        produce_event(fsm.event_data, EventID.E_PICKED)


def recover(fsm: FSMData, ud: UserData) -> None:
    ud.gripper_width = min(ud.open_width, ud.gripper_width + ud.closing_speed * LOOP_DURATION)
    if ud.gripper_width >= ud.open_width:
        produce_event(fsm.event_data, EventID.E_RECOVERED)


FSM_BHV: dict[StateID, Callable[[FSMData, UserData], None]] = {
    StateID.S_IDLE: lambda fsm, ud: produce_event(fsm.event_data, EventID.E_START),
    StateID.S_PERCEIVE: perceive,
    StateID.S_PICK: pick_step,
    StateID.S_RECOVER: recover,
}


class Action(py_trees.behaviour.Behaviour):
    """Steps the user data once per tick until the step reports the action done."""

    def __init__(
        self, name: str, ud: UserData, board, step: Callable[[UserData], py_trees.common.Status]
    ):
        super().__init__(name=name)
        self.ud = ud
        self.board = board
        self.step = step

    def initialise(self):
        print(f"Action: {self.name} ({ACTION_IRI[self.name]})")

    def update(self):
        status = self.step(self.ud)
        monitor(self.ud, self.board)
        return status


class StateMachine(py_trees.behaviour.Behaviour):
    """Steps the FSM once per tick; it reports no outcome, a condition above it ends it."""

    def __init__(self, name: str, ud: UserData, board):
        super().__init__(name=name)
        self.ud = ud
        self.board = board
        self.fsm = create_fsm()
        self.state = None

    def initialise(self):
        print(f"State machine: {self.name} ({FSM_IRI[self.name]})")
        self.fsm = create_fsm()
        self.state = None

    def update(self):
        state = StateID(self.fsm.current_state_index)
        if state != self.state:
            print(f"  state: {state.name} ({STATE_URIS[state]})")
            self.state = state
        if state in FSM_BHV:
            FSM_BHV[state](self.fsm, self.ud)
        reconfig_event_buffers(self.fsm.event_data)
        fsm_step(self.fsm)
        monitor(self.ud, self.board)
        return RUNNING

    def terminate(self, new_status):
        if new_status == py_trees.common.Status.INVALID and self.state is not None:
            print(f"  halted in {self.state.name}")


def main(speed: float, failed_grasps: int):
    signal.signal(signal.SIGINT, signal_handler)

    print("Starting generated behaviour tree and FSM example. Press Ctrl+C to exit.\n")
    board = py_trees.blackboard.Client(name="flags")
    for flag in FLAG_IRI:
        board.register_key(key=flag, access=py_trees.common.Access.WRITE)

    now = time.time()
    ud = UserData(current_time=now, speed=speed, failed_grasps=failed_grasps)
    steps = {"approach": approach, "lift": lift}
    tree = py_trees.trees.BehaviourTree(
        coordinated_pick(
            {name: lambda name=name: Action(name, ud, board, steps[name]) for name in ACTION_IRI},
            {name: lambda name=name: StateMachine(name, ud, board) for name in FSM_IRI},
        )
    )

    loop_timeout = now + LOOP_DURATION
    while True:
        now = time.time()
        while now < loop_timeout:
            now = time.time()
        while loop_timeout < now:
            loop_timeout += LOOP_DURATION

        ud.current_time = now
        monitor(ud, board)
        tree.tick()
        if tree.root.status != RUNNING:
            print(f"Behaviour tree finished with {tree.root.status.value}")
            break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test generated behaviour tree and FSM example",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--speed", "-s", type=float, default=0.2, help="Arm speed in m/s when approaching and lifting"
    )
    parser.add_argument(
        "--failed-grasps",
        "-f",
        type=int,
        default=0,
        help="Grasps that slip before one holds; each sends the FSM through S_RECOVER",
    )
    args = parser.parse_args()
    main(args.speed, args.failed_grasps)
