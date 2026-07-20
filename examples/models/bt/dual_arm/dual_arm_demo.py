#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Run the generated py_trees tree that drives two arms in parallel.

The Python counterpart of dual_arm_main.cpp: a parallel-all ticks both arms at
once, each under a retry decorator. The ``[failure-if]`` guards read blackboard
flags, so ``--fault left|right`` makes that branch fail its 3 attempts and set
the ``*_failed`` flag -- the same guard semantics as BT.CPP.

Generate first:
    textx generate ../fsms/right_arm.fsm --target python -o right_arm.py
    textx generate ../fsms/left_arm.fsm  --target python -o left_arm.py
    textx generate dual_arm_fsms.btree --target python

    python dual_arm_demo.py [--fault left|right]
"""
import sys

import py_trees

import left_arm
import right_arm
from coord_dsl.event_loop import produce_event
from dual_arm import DualArmRuntime, create_tree

WORK_TICKS = 3  # ticks each motion "runs" before it completes
FLAGS = ("left_arm_failed", "right_arm_failed", "coordination_complete", "coordination_failed")


class Demo(DualArmRuntime):
    """Controllers: after WORK_TICKS in its motion state, each arm produces its
    completion event."""

    def __init__(self):
        super().__init__()
        self._elapsed = {}

    def _run_phase(self, fsm, name, active, done):
        if fsm.current_state_index != active:
            return
        self._elapsed[name] = self._elapsed.get(name, 0) + 1
        if self._elapsed[name] == WORK_TICKS:
            produce_event(fsm.event_data, done)
            print(f"  {name}: finished, produced completion event")

    def step_left_arm(self, fsm):
        self._run_phase(fsm, "left_arm", left_arm.StateID.MOVING_TO_TAKE_POSE,
                        left_arm.EventID.TAKE_POSE_DONE)

    def step_right_arm(self, fsm):
        self._run_phase(fsm, "right_arm", right_arm.StateID.PICKING,
                        right_arm.EventID.PICK_DONE)


def main():
    fault = sys.argv[sys.argv.index("--fault") + 1] if "--fault" in sys.argv else None
    if fault not in (None, "left", "right"):
        print("usage: dual_arm_demo.py [--fault left|right]")
        return 2

    board = py_trees.blackboard.Blackboard()
    for flag in FLAGS:
        board.set(flag, False)
    for arm in ("left", "right"):
        board.set(f"{arm}_arm_fault", arm == fault)

    print(f"=== dual_arm: py_trees driving both arms{f'  ({fault}_arm will FAULT)' if fault else ''} ===")
    root = create_tree(Demo())
    for _ in range(1000):
        root.tick_once()
        if root.status != py_trees.common.Status.RUNNING:
            break

    print("  flags: " + ", ".join(f"{f}={board.get(f)}" for f in FLAGS))
    print(f"=== dual_arm: {root.status.name} ===")
    return 0 if root.status == py_trees.common.Status.SUCCESS else 1


if __name__ == "__main__":
    sys.exit(main())
