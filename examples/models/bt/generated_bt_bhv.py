#!/usr/bin/env python3
"""Example of using a generated behaviour tree with custom behaviour in Python.

The actions move the user data towards their goals, and a monitor turns that data into the flags
the tree's conditions read, so the conditions depend on what the actions did.

SPDX-License-Identifier: MPL-2.0
"""

import signal
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

import py_trees

from pick import ACTION_IRI, FLAG_IRI, pick

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
    detection_confidence: float = 0.9   # of the object detector
    min_confidence: float = 0.5         # below it, the object is not visible
    distance_to_object: float = 0.3     # m, from the gripper
    approach_tolerance: float = 0.005   # m
    gripper_width: float = 0.08         # m, open
    object_width: float = 0.04          # m
    closing_speed: float = 0.05         # m/s
    grip_force: float = 0.0             # N
    force_rate: float = 40.0            # N/s, once the fingers touch the object
    min_grip_force: float = 10.0        # N, below it the object is not grasped
    height: float = 0.0                 # m, of the object above the table
    lift_height: float = 0.1            # m
    slip_height: float = 0.0            # m; the grip is lost here when > 0


def approach(ud: UserData) -> py_trees.common.Status:
    ud.distance_to_object = max(0.0, ud.distance_to_object - ud.speed * LOOP_DURATION)
    return SUCCESS if ud.distance_to_object <= ud.approach_tolerance else RUNNING


def grasp(ud: UserData) -> py_trees.common.Status:
    if ud.gripper_width > ud.object_width:
        ud.gripper_width = max(ud.object_width, ud.gripper_width - ud.closing_speed * LOOP_DURATION)
        return RUNNING
    ud.grip_force += ud.force_rate * LOOP_DURATION
    return SUCCESS if ud.grip_force >= ud.min_grip_force else RUNNING


def lift(ud: UserData) -> py_trees.common.Status:
    ud.height += ud.speed * LOOP_DURATION
    if ud.slip_height and ud.height >= ud.slip_height:
        ud.grip_force = 0.0
    return SUCCESS if ud.height >= ud.lift_height else RUNNING


def monitor(ud: UserData, board) -> None:
    """Derive the flags the conditions read from the user data."""
    board.object_visible = ud.detection_confidence >= ud.min_confidence
    board.object_grasped = ud.grip_force >= ud.min_grip_force


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
        if status == SUCCESS:
            print(
                f"  done: distance {self.ud.distance_to_object:.3f} m, width {self.ud.gripper_width:.3f} m,"
                f" force {self.ud.grip_force:.1f} N, height {self.ud.height:.3f} m"
            )
        return status


def main(speed: float, slip_height: float):
    signal.signal(signal.SIGINT, signal_handler)

    print("Starting generated behaviour tree example. Press Ctrl+C to exit.\n")
    board = py_trees.blackboard.Client(name="flags")
    for flag in FLAG_IRI:
        board.register_key(key=flag, access=py_trees.common.Access.WRITE)

    now = time.time()
    ud = UserData(current_time=now, speed=speed, slip_height=slip_height)
    steps = {"approach": approach, "grasp": grasp, "lift": lift}
    tree = py_trees.trees.BehaviourTree(
        pick({name: lambda name=name: Action(name, ud, board, steps[name]) for name in ACTION_IRI})
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
        description="Test generated behaviour tree example",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--speed", "-s", type=float, default=0.2, help="Arm speed in m/s when approaching and lifting"
    )
    parser.add_argument(
        "--slip-height",
        type=float,
        default=0.0,
        help="Height in m at which the grip is lost while lifting; 0 keeps the grip",
    )
    args = parser.parse_args()
    main(args.speed, args.slip_height)
