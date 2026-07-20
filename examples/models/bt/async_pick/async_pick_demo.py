#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Run the generated py_trees tree against self-driving FSM controllers.

The Python counterpart of async_pick_main.cpp: each FSM runs in its own 1 kHz
thread that owns the step loop. The tree only DISPATCHES command events and
POLLS state across a lock, so the execution-policy hooks are overridden --
``advance`` becomes a no-op and the rest take the controller's lock. The model
awaits *states*, not events: an event edge cannot be sampled across the thread
boundary.

Generate first:
    textx generate ../fsms/right_arm.fsm --target python -o right_arm.py
    textx generate ../fsms/gripper.fsm   --target python -o gripper.py
    textx generate async_pick.btree --target python

    python async_pick_demo.py [--fault]
"""
import sys
import threading
import time

import py_trees

import gripper
import right_arm
from async_pick import AsyncPickRuntime, create_tree
from coord_dsl.event_loop import consume_event, produce_event, reconfig_event_buffers
from coord_dsl.fsm import fsm_step

CONTROL_PERIOD = 0.001  # 1 kHz control rate
MOTION_TICKS = 60       # each sub-behaviour runs ~60 ms of real time


class _Controller:
    """One FSM, its lock, and the thread that owns its step loop."""

    def __init__(self, fsm):
        self.fsm = fsm
        self.lock = threading.Lock()
        self.running = True
        self.motion = 0
        self.thread = None


class Demo(AsyncPickRuntime):
    def __init__(self, fault=False):
        super().__init__()
        self.fault = fault
        self._ctrl = {name: _Controller(self.fsm_of(name)) for name in ("right_arm", "gripper")}

    # ---- controller behaviour: runs inside the controller thread, under its
    # lock, so it reads the FSM directly instead of the locking hooks below ----

    def _run_motion(self, name, fsm, active, done):
        controller = self._ctrl[name]
        if fsm.current_state_index != active:
            controller.motion = 0
            return
        controller.motion += 1
        if controller.motion == MOTION_TICKS:
            produce_event(fsm.event_data, done)

    def step_right_arm(self, fsm):
        self._run_motion("right_arm", fsm, right_arm.StateID.PICKING, right_arm.EventID.PICK_DONE)

    def step_gripper(self, fsm):
        done = gripper.EventID.GRASP_FAULT if self.fault else gripper.EventID.GRASPED_OK
        self._run_motion("gripper", fsm, gripper.StateID.GRASPING, done)

    # ---- execution policy: the threads step the FSMs, so the tree must not ----

    def dispatch(self, instance, event):
        controller = self._ctrl[instance]
        with controller.lock:
            produce_event(controller.fsm.event_data, event)
        print(f"  {instance}: <= BT dispatched command")

    def advance(self, instance):
        pass  # the controller thread drives the FSM

    def current_state(self, instance):
        controller = self._ctrl[instance]
        with controller.lock:
            return controller.fsm.current_state_index

    def event_present(self, instance, event):
        controller = self._ctrl[instance]
        with controller.lock:
            return consume_event(controller.fsm.event_data, event)

    # ---- the 1 kHz controller threads ----

    def start(self):
        for name, controller in self._ctrl.items():
            controller.thread = threading.Thread(target=self._loop, args=(name, controller))
            controller.thread.start()

    def stop(self):
        for controller in self._ctrl.values():
            controller.running = False
        for controller in self._ctrl.values():
            controller.thread.join()

    def _loop(self, name, controller):
        next_tick = time.monotonic()
        last = None
        while controller.running:
            next_tick += CONTROL_PERIOD
            with controller.lock:
                self.step(name, controller.fsm)
                reconfig_event_buffers(controller.fsm.event_data)
                fsm_step(controller.fsm)
                if controller.fsm.current_state_index != last:
                    last = controller.fsm.current_state_index
                    print(f"  {name}: state={self._STATES[name](last).name}  [1 kHz thread]")
            time.sleep(max(0.0, next_tick - time.monotonic()))


def main():
    fault = "--fault" in sys.argv
    print(f"=== async_pick: py_trees + 1 kHz FSM threads{'  (gripper will FAULT)' if fault else ''} ===")
    runtime = Demo(fault)
    root = create_tree(runtime)
    runtime.start()
    try:
        for _ in range(1000):
            root.tick_once()
            if root.status != py_trees.common.Status.RUNNING:
                break
            time.sleep(0.01)  # let the controllers run between ticks
    finally:
        runtime.stop()
    print(f"=== async_pick: {root.status.name} ===")
    return 0 if root.status == py_trees.common.Status.SUCCESS else 1


if __name__ == "__main__":
    sys.exit(main())
