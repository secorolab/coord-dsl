#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Run the generated py_trees tree that coordinates two FSMs.

Generate first:
    textx generate right_arm.fsm --target python -o right_arm.py
    textx generate gripper.fsm   --target python -o gripper.py
    textx generate py_pick.btree --target python

    python py_pick_demo.py [--fault]
"""
import sys

import py_trees

import gripper
import right_arm
from coord_dsl.event_loop import produce_event
from py_pick import PyPickRuntime, create_tree

WORK_TICKS = 3  # ticks each arm motion "runs" before it completes


class Demo(PyPickRuntime):
    """Controllers: after WORK_TICKS in the active state, produce the completion
    event -- driving the FSM to the state the tree awaits."""

    def __init__(self, fault=False):
        super().__init__()
        self.fault = fault
        self._elapsed = {}

    def _run_phase(self, fsm, active, done, key):
        if fsm.current_state_index != active:
            self._elapsed[key] = 0
            return
        self._elapsed[key] = self._elapsed.get(key, 0) + 1
        if self._elapsed[key] == WORK_TICKS:
            produce_event(fsm.event_data, done)
            print(f"  {key}: finished, produced completion event")

    def step_right_arm(self, fsm):
        self._run_phase(fsm, right_arm.StateID.PICKING, right_arm.EventID.PICK_DONE, "right_arm")

    def step_gripper(self, fsm):
        done = gripper.EventID.GRASP_FAULT if self.fault else gripper.EventID.GRASPED_OK
        self._run_phase(fsm, gripper.StateID.GRASPING, done, "gripper")


def main():
    fault = "--fault" in sys.argv
    print(f"=== py_pick: py_trees coordinating FSMs{'  (gripper will FAULT)' if fault else ''} ===")
    root = create_tree(Demo(fault))
    for _ in range(1000):
        root.tick_once()
        if root.status != py_trees.common.Status.RUNNING:
            break
    print(f"=== py_pick: {root.status.name} ===")
    return 0 if root.status == py_trees.common.Status.SUCCESS else 1


if __name__ == "__main__":
    sys.exit(main())
