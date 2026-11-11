#!/usr/bin/env python3
"""Example of the generated warehouse behaviour tree ticking three generated state machines.

A mobile manipulator fetches an item from a shelf and delivers it. The tree runs the base
navigation and arm motion FSMs in parallel while approaching the shelf and while carrying the
item, and the gripper FSM while grasping it. The actions and the FSMs' state behaviours move the
user data, and a monitor turns that data into the flags the tree's conditions read.

The aisle runs from the charger at 0 m past the shelf at 2 m to the dropoff at 4 m.

SPDX-License-Identifier: MPL-2.0
"""

import signal
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

import arm_motion
import base_navigation
import gripper
import py_trees
from coord_dsl.event_loop import produce_event, reconfig_event_buffers
from coord_dsl.fsm import fsm_step

from warehouse_order import ACTION_IRI, FLAG_IRI, FSM_IRI, warehouse_order

LOOP_DURATION = 0.01
RUNNING = py_trees.common.Status.RUNNING
SUCCESS = py_trees.common.Status.SUCCESS
FAILURE = py_trees.common.Status.FAILURE
AISLES = ("free", "movable", "closed")
FAULTS = ("none", "transient", "permanent")


def signal_handler(sig, frame):
    del sig, frame
    print("You pressed Ctrl+C, exiting!")
    sys.exit(0)


@dataclass
class UserData:
    current_time: float
    start_time: float
    speed: float                      # m/s, of the base
    battery: float                    # charge, 0 to 1
    aisle: str                        # one of AISLES
    path_blocked: bool                # something blocks the base's path once
    arm_collision: bool               # the arm collides once while moving
    slips: int                        # grasps that slip before one holds
    hidden_item: bool                 # the first scan misses the item
    lost: bool                        # the first localisation fails
    hardware_fault: str               # one of FAULTS
    dropoff_busy_until: float         # s after start
    estop_at: float                   # s after start; 0 never presses it
    min_battery: float = 0.2
    full_battery: float = 0.9
    drain_rate: float = 0.05          # charge per m driven
    charge_rate: float = 0.5          # charge per s docked
    charger_position: float = 0.0     # m
    shelf_position: float = 2.0       # m
    dropoff_position: float = 4.0     # m
    tolerance: float = 0.01           # m
    arm_speed: float = 2.0            # trajectory fraction per s
    open_width: float = 0.08          # m
    object_width: float = 0.04        # m
    closing_speed: float = 0.1        # m/s
    force_rate: float = 50.0          # N/s, once the fingers touch the item
    min_grip_force: float = 10.0      # N
    position: float = 0.0
    battery_ok: bool = True
    hardware_ok: bool = False
    localized: bool = False
    docked: bool = False
    item_visible: bool = False
    arm_pose: str = "stowed"
    arm_progress: float = 0.0
    gripper_width: float = 0.08
    grip_force: float = 0.0
    holding: bool = False
    placed: bool = False
    confirmed: bool = False
    reported: bool = False

    @property
    def elapsed(self) -> float:
        return self.current_time - self.start_time

    @property
    def nav_goal(self) -> float:
        if not self.battery_ok:
            return self.charger_position
        if self.holding:
            return self.dropoff_position
        return self.shelf_position

    @property
    def arm_goal(self) -> str:
        return "stowed" if self.holding else "pregrasp"


def monitor(ud: UserData, board) -> None:
    """Derive the flags the conditions read from the user data; the battery flag has hysteresis."""
    if ud.battery < ud.min_battery:
        ud.battery_ok = False
    elif ud.battery >= ud.full_battery:
        ud.battery_ok = True
    board.estop_released = not (ud.estop_at and ud.elapsed >= ud.estop_at)
    board.hardware_ok = ud.hardware_ok
    board.localized = ud.localized
    board.battery_ok = ud.battery_ok
    board.docked = ud.docked
    board.undocked = not ud.docked
    board.at_charger = abs(ud.position - ud.charger_position) <= ud.tolerance
    board.at_shelf = abs(ud.position - ud.shelf_position) <= ud.tolerance
    board.at_dropoff = abs(ud.position - ud.dropoff_position) <= ud.tolerance
    board.shelf_reachable = ud.aisle == "free"
    board.arm_at_pregrasp = ud.arm_pose == "pregrasp"
    board.arm_stowed = ud.arm_pose == "stowed"
    board.item_visible = ud.item_visible
    board.item_held = ud.holding
    board.dropoff_free = ud.elapsed >= ud.dropoff_busy_until
    board.item_placed = ud.placed
    board.order_confirmed = ud.confirmed


def drive_to(ud: UserData, goal: float) -> bool:
    step = min(ud.speed * LOOP_DURATION, abs(goal - ud.position))
    ud.position += step if goal > ud.position else -step
    ud.battery = max(0.0, ud.battery - ud.drain_rate * step)
    return abs(goal - ud.position) <= ud.tolerance


class Node(py_trees.behaviour.Behaviour):
    """A leaf stepping the user data once per tick, refreshing the flags after each step."""

    def __init__(self, name: str, iri: str, ud: UserData, board):
        super().__init__(name=name)
        self.iri = iri
        self.ud = ud
        self.board = board
        self.started = 0.0

    @property
    def running_for(self) -> float:
        return self.ud.current_time - self.started

    def initialise(self):
        self.started = self.ud.current_time
        print(
            f"[{self.ud.elapsed:5.2f} s] {type(self).__name__}: {self.name} ({self.iri})"
            f" at {self.ud.position:.2f} m, battery {self.ud.battery:.2f}"
        )

    def update(self):
        status = self.step()
        monitor(self.ud, self.board)
        return status


class Action(Node):
    def __init__(self, name: str, ud: UserData, board, step: Callable[["Action"], py_trees.common.Status]):
        super().__init__(name, ACTION_IRI[name], ud, board)
        self.action_step = step

    def step(self):
        return self.action_step(self)


def after(action: Action, duration: float, effect: Callable[[], py_trees.common.Status]):
    return RUNNING if action.running_for < duration else effect()


def run_self_test(action: Action):
    def test():
        action.ud.hardware_ok = action.ud.hardware_fault == "none"
        return SUCCESS

    return after(action, 0.2, test)


def reset_drivers(action: Action):
    def reset():
        if action.ud.hardware_fault == "transient":
            action.ud.hardware_fault = "none"
        return SUCCESS

    return after(action, 0.3, reset)


def localize(action: Action):
    def match():
        action.ud.localized = not action.ud.lost
        return SUCCESS

    return after(action, 0.3, match)


def spin_in_place(action: Action):
    def spin():
        action.ud.lost = False
        return SUCCESS

    return after(action, 0.5, spin)


def dock(action: Action):
    action.ud.docked = True
    return SUCCESS


def recharge(action: Action):
    ud = action.ud
    ud.battery = min(1.0, ud.battery + ud.charge_rate * LOOP_DURATION)
    return SUCCESS if ud.battery >= ud.full_battery else RUNNING


def undock(action: Action):
    action.ud.docked = False
    return SUCCESS


def clear_obstacle(action: Action):
    if action.ud.aisle != "movable":
        return FAILURE
    action.ud.aisle = "free"
    return SUCCESS


def request_help(action: Action):
    def cleared():
        action.ud.aisle = "free"
        return SUCCESS

    return after(action, 1.0, cleared)


def scan_shelf(action: Action):
    def scan():
        action.ud.item_visible = not action.ud.hidden_item
        return SUCCESS

    return after(action, 0.2, scan)


def reposition_camera(action: Action):
    action.ud.hidden_item = False
    return SUCCESS


def wait_for_dropoff(action: Action):
    return SUCCESS if action.board.dropoff_free else RUNNING


def place_item(action: Action):
    ud = action.ud
    ud.holding = False
    ud.placed = True
    ud.grip_force = 0.0
    ud.gripper_width = ud.open_width
    return SUCCESS


def confirm_order(action: Action):
    def confirm():
        action.ud.confirmed = True
        return SUCCESS

    return after(action, 0.2, confirm)


def report_done(action: Action):
    action.ud.reported = True
    return SUCCESS


STEPS: dict[str, Callable[[Action], py_trees.common.Status]] = {
    "run_self_test": run_self_test,
    "reset_drivers": reset_drivers,
    "localize": localize,
    "spin_in_place": spin_in_place,
    "dock": dock,
    "recharge": recharge,
    "undock": undock,
    "clear_obstacle": clear_obstacle,
    "request_help": request_help,
    "scan_shelf": scan_shelf,
    "reposition_camera": reposition_camera,
    "wait_for_dropoff": wait_for_dropoff,
    "place_item": place_item,
    "confirm_order": confirm_order,
    "report_done": report_done,
}


def navigation_behaviour(machine: "StateMachine"):
    ud, events, state = machine.ud, machine.fsm.event_data, machine.state
    if state == base_navigation.StateID.S_IDLE:
        produce_event(events, base_navigation.EventID.E_START)
    elif state == base_navigation.StateID.S_PLAN and machine.in_state_for >= 0.1:
        produce_event(events, base_navigation.EventID.E_PLANNED)
    elif state == base_navigation.StateID.S_DRIVE:
        goal = ud.nav_goal
        if drive_to(ud, goal):
            produce_event(events, base_navigation.EventID.E_ARRIVED)
        elif ud.path_blocked and abs(goal - ud.position) < 1.0:
            ud.path_blocked = False
            print("  path blocked")
            produce_event(events, base_navigation.EventID.E_BLOCKED)
    elif state == base_navigation.StateID.S_RECOVER and machine.in_state_for >= 0.3:
        produce_event(events, base_navigation.EventID.E_REPLANNED)


def arm_behaviour(machine: "StateMachine"):
    ud, events, state = machine.ud, machine.fsm.event_data, machine.state
    if state == arm_motion.StateID.S_IDLE:
        ud.arm_progress = 0.0
        produce_event(events, arm_motion.EventID.E_START)
    elif state == arm_motion.StateID.S_PLAN and machine.in_state_for >= 0.1:
        produce_event(events, arm_motion.EventID.E_TRAJECTORY_READY)
    elif state == arm_motion.StateID.S_MOVE:
        ud.arm_pose = "moving"
        ud.arm_progress = min(1.0, ud.arm_progress + ud.arm_speed * LOOP_DURATION)
        if ud.arm_collision and ud.arm_progress >= 0.5:
            ud.arm_collision = False
            print("  arm collision")
            produce_event(events, arm_motion.EventID.E_COLLISION)
        elif ud.arm_progress >= 1.0:
            ud.arm_pose = ud.arm_goal
            produce_event(events, arm_motion.EventID.E_POSE_REACHED)
    elif state == arm_motion.StateID.S_RETRACT and machine.in_state_for >= 0.2:
        ud.arm_progress = 0.0
        produce_event(events, arm_motion.EventID.E_RETRACTED)


def gripper_behaviour(machine: "StateMachine"):
    ud, events, state = machine.ud, machine.fsm.event_data, machine.state
    if state == gripper.StateID.S_OPEN:
        produce_event(events, gripper.EventID.E_START)
    elif state == gripper.StateID.S_CLOSE:
        ud.gripper_width = max(ud.object_width, ud.gripper_width - ud.closing_speed * LOOP_DURATION)
        if ud.gripper_width <= ud.object_width:
            produce_event(events, gripper.EventID.E_CONTACT)
    elif state == gripper.StateID.S_SQUEEZE:
        ud.grip_force += ud.force_rate * LOOP_DURATION
        if ud.slips and ud.grip_force >= ud.min_grip_force / 2:
            ud.slips -= 1
            ud.grip_force = 0.0
            print("  grasp slipped")
            produce_event(events, gripper.EventID.E_SLIPPED)
        elif ud.grip_force >= ud.min_grip_force:
            ud.holding = True
            produce_event(events, gripper.EventID.E_HOLDING)
    elif state == gripper.StateID.S_REOPEN:
        ud.gripper_width = min(ud.open_width, ud.gripper_width + ud.closing_speed * LOOP_DURATION)
        if ud.gripper_width >= ud.open_width:
            produce_event(events, gripper.EventID.E_REOPENED)


MACHINES = {
    "base_navigation": (base_navigation, navigation_behaviour),
    "arm_motion": (arm_motion, arm_behaviour),
    "gripper": (gripper, gripper_behaviour),
}


class StateMachine(Node):
    """Steps its FSM once per tick; it reports no outcome, a condition above it ends it."""

    def __init__(self, name: str, ud: UserData, board):
        super().__init__(name, FSM_IRI[name], ud, board)
        self.module, self.behaviour = MACHINES[name]
        self.fsm = self.module.create_fsm()
        self.state = None
        self.entered = 0.0

    @property
    def in_state_for(self) -> float:
        return self.ud.current_time - self.entered

    def initialise(self):
        super().initialise()
        self.fsm = self.module.create_fsm()
        self.state = None

    def step(self):
        state = self.module.StateID(self.fsm.current_state_index)
        if state != self.state:
            print(f"    {self.name}: {state.name} ({self.module.STATE_URIS[state]})")
            self.state = state
            self.entered = self.ud.current_time
        self.behaviour(self)
        reconfig_event_buffers(self.fsm.event_data)
        fsm_step(self.fsm)
        return RUNNING


def main(args):
    signal.signal(signal.SIGINT, signal_handler)

    print("Starting generated warehouse behaviour tree example. Press Ctrl+C to exit.\n")
    board = py_trees.blackboard.Client(name="flags")
    for flag in FLAG_IRI:
        board.register_key(key=flag, access=py_trees.common.Access.WRITE)

    now = time.time()
    ud = UserData(
        current_time=now,
        start_time=now,
        speed=args.speed,
        battery=args.battery,
        aisle=args.aisle,
        path_blocked=args.path_blocked,
        arm_collision=args.arm_collision,
        slips=args.slips,
        hidden_item=args.hidden_item,
        lost=args.lost,
        hardware_fault=args.hardware_fault,
        dropoff_busy_until=args.dropoff_busy,
        estop_at=args.estop_at,
    )
    ud.battery_ok = ud.battery >= ud.min_battery
    monitor(ud, board)
    tree = py_trees.trees.BehaviourTree(
        warehouse_order(
            {name: lambda name=name: Action(name, ud, board, STEPS[name]) for name in ACTION_IRI},
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
            print(
                f"Behaviour tree finished with {tree.root.status.value} after {ud.elapsed:.2f} s:"
                f" placed {ud.placed}, confirmed {ud.confirmed}, reported {ud.reported},"
                f" at {ud.position:.2f} m, battery {ud.battery:.2f}"
            )
            break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test generated warehouse behaviour tree and FSMs example",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--speed", "-s", type=float, default=2.0, help="Base speed in m/s")
    parser.add_argument("--battery", "-b", type=float, default=0.8, help="Initial charge, 0 to 1")
    parser.add_argument(
        "--aisle", choices=AISLES, default="free",
        help="The shelf's aisle: movable is cleared by the robot, closed needs help",
    )
    parser.add_argument("--path-blocked", action="store_true", help="Block the base once; it replans")
    parser.add_argument("--arm-collision", action="store_true", help="The arm collides once; it retracts")
    parser.add_argument("--slips", type=int, default=0, help="Grasps that slip before one holds")
    parser.add_argument("--hidden-item", action="store_true", help="The first scan misses the item")
    parser.add_argument("--lost", action="store_true", help="The first localisation fails")
    parser.add_argument(
        "--hardware-fault", choices=FAULTS, default="none",
        help="transient is fixed by a driver reset, permanent is not",
    )
    parser.add_argument("--dropoff-busy", type=float, default=0.0, help="Seconds until the dropoff is free")
    parser.add_argument("--estop-at", type=float, default=0.0, help="Seconds until the emergency stop; 0 never")
    main(parser.parse_args())
