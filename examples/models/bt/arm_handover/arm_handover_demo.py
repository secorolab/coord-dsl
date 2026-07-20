#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Run the generated py_trees tree that hands an object between two arms.

The Python counterpart of arm_handover_main.cpp: a sequence drives right_arm
(pick, then move to the handover pose) and left_arm (take the pose, then place).

Generate first:
    textx generate ../fsms/right_arm.fsm --target python -o right_arm.py
    textx generate ../fsms/left_arm.fsm  --target python -o left_arm.py
    textx generate arm_handover_fsms.btree --target python

    python arm_handover_demo.py
"""
import sys

import py_trees

import left_arm
import right_arm
from arm_handover import ArmHandoverRuntime, create_tree
from coord_dsl.event_loop import produce_event

WORK_TICKS = 3  # ticks each motion "runs" before it completes


class Demo(ArmHandoverRuntime):
    """Controllers: after WORK_TICKS in a motion state, produce that motion's
    completion event -- driving the FSM to the state the tree awaits."""

    def __init__(self):
        super().__init__()
        self._elapsed = {}

    def _run_phase(self, fsm, name, phases):
        """phases maps an in-motion state to the event that completes it."""
        done = phases.get(fsm.current_state_index)
        if done is None:
            return
        key = (name, fsm.current_state_index)
        self._elapsed[key] = self._elapsed.get(key, 0) + 1
        if self._elapsed[key] == WORK_TICKS:
            produce_event(fsm.event_data, done)
            print(f"  {name}: finished, produced completion event")

    def step_right_arm(self, fsm):
        self._run_phase(fsm, "right_arm", {
            right_arm.StateID.PICKING: right_arm.EventID.PICK_DONE,
            right_arm.StateID.MOVING_HANDOVER: right_arm.EventID.HANDOVER_DONE,
        })

    def step_left_arm(self, fsm):
        self._run_phase(fsm, "left_arm", {
            left_arm.StateID.MOVING_TO_TAKE_POSE: left_arm.EventID.TAKE_POSE_DONE,
            left_arm.StateID.PLACING: left_arm.EventID.PLACE_DONE,
        })


def main():
    print("=== arm_handover: py_trees coordinating two arms ===")
    root = create_tree(Demo())
    for _ in range(1000):
        root.tick_once()
        if root.status != py_trees.common.Status.RUNNING:
            break
    print(f"=== arm_handover: {root.status.name} ===")
    return 0 if root.status == py_trees.common.Status.SUCCESS else 1


if __name__ == "__main__":
    sys.exit(main())
