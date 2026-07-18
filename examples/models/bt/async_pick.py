# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
#
# This is an auto-generated file. Do not edit it directly.
# py_trees behaviour tree for: async_pick
import py_trees
from coord_dsl.event_loop import produce_event, consume_event, reconfig_event_buffers
from coord_dsl.fsm import fsm_step
import right_arm
import gripper


class AsyncPickRuntime:
    """Runtime contract: implement the leaf/FSM hooks, pass an instance to
    :func:`create_tree`."""

    def __init__(self):
        self._fsm = {
            'right_arm': right_arm.create_fsm(),
            'gripper': gripper.create_fsm(),
        }

    _EVENTS = {
        'right_arm': right_arm.EventID,
        'gripper': gripper.EventID,
    }
    _STATES = {
        'right_arm': right_arm.StateID,
        'gripper': gripper.StateID,
    }

    def step_right_arm(self, fsm):
        """Advance the right_arm controller one tick; produce completion
        events (e.g. *_DONE) once its current sub-behaviour finishes."""
        raise NotImplementedError

    def step_gripper(self, fsm):
        """Advance the gripper controller one tick; produce completion
        events (e.g. *_DONE) once its current sub-behaviour finishes."""
        raise NotImplementedError

    def fsm_of(self, instance):
        return self._fsm[instance]

    def event_index(self, instance, event):
        return int(self._EVENTS[instance][event])

    def state_index(self, instance, state):
        return int(self._STATES[instance][state])

    def step(self, instance, fsm):
        {
            'right_arm': self.step_right_arm,
            'gripper': self.step_gripper,
        }[instance](fsm)

    # ---- Execution policy. Defaults drive the FSM synchronously from the tick;
    # override for a self-driving controller (e.g. a real-time thread), making
    # dispatch()/current_state() thread-safe and advance() a no-op. ----

    def dispatch(self, instance, event):
        produce_event(self.fsm_of(instance).event_data, event)

    def advance(self, instance):
        fsm = self.fsm_of(instance)
        self.step(instance, fsm)
        reconfig_event_buffers(fsm.event_data)
        fsm_step(fsm)

    def event_present(self, instance, event):
        return consume_event(self.fsm_of(instance).event_data, event)

    def current_state(self, instance):
        return self.fsm_of(instance).current_state_index


def _bb_get(key):
    try:
        return py_trees.blackboard.Blackboard.get(key)
    except KeyError:
        return None


_bb_set = py_trees.blackboard.Blackboard.set


class _Guarded(py_trees.decorators.Decorator):
    """BT.CPP-style guards. ``pre``: (status, condition) pairs checked before
    the child (re)enters -- a true condition returns the status without
    ticking the child. ``post``: (status, script) pairs run when the child
    completes with that status (``None`` matches any completion)."""

    def __init__(self, name, child, pre, post):
        super().__init__(name=name, child=child)
        self._pre = pre
        self._post = post

    def tick(self):
        if self.decorated.status != py_trees.common.Status.RUNNING:
            for status, condition in self._pre:
                if condition():
                    self.stop(status)
                    yield self
                    return
        yield from super().tick()

    def update(self):
        status = self.decorated.status
        if status != py_trees.common.Status.RUNNING:
            for wanted, script in self._post:
                if wanted is None or wanted == status:
                    script()
        return status


class _Leaf(py_trees.behaviour.Behaviour):
    """A declared action/condition; delegates to a runtime ``on_*`` hook."""

    def __init__(self, name, runtime, method, ports):
        super().__init__(name=name)
        self._runtime = runtime
        self._method = method
        self.ports = ports

    def update(self):
        return getattr(self._runtime, self._method)(self)


class _FSMEvent(py_trees.behaviour.Behaviour):
    """Dispatches a command event, then drives/polls the FSM until ``await``
    (an event, edge-triggered, or a state, level-triggered); optional
    ``on_fail`` maps a fault target to FAILURE."""

    def __init__(self, name, runtime, instance, event, await_name, await_kind,
                 on_fail=None, on_fail_kind=None):
        super().__init__(name=name)
        self._rt = runtime
        self._instance = instance
        self._event = event
        self._await_name = await_name
        self._await_state = await_kind == "state"
        self._fail_name = on_fail
        self._fail_state = on_fail_kind == "state"

    def initialise(self):
        self._command = self._rt.event_index(self._instance, self._event)
        self._await = self._resolve(self._await_name, self._await_state)
        self._fail = self._resolve(self._fail_name, self._fail_state) if self._fail_name else None
        self._rt.dispatch(self._instance, self._command)

    def update(self):
        self._rt.advance(self._instance)
        if self._fail is not None and self._reached(self._fail, self._fail_state):
            return py_trees.common.Status.FAILURE
        if self._reached(self._await, self._await_state):
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.RUNNING

    def _resolve(self, name, is_state):
        return (self._rt.state_index if is_state else self._rt.event_index)(self._instance, name)

    def _reached(self, index, is_state):
        if is_state:
            return self._rt.current_state(self._instance) == index
        return self._rt.event_present(self._instance, index)


def create_tree(runtime) -> py_trees.behaviour.Behaviour:
    """Build the 'async_pick' tree bound to ``runtime`` and return its root."""
    return _Guarded('guarded',
        py_trees.composites.Sequence(
            name='sequence', memory=True,
                children=[
                    _FSMEvent('right_arm.PICK', runtime, 'right_arm', 'PICK', 'PICKED', 'state'),
                    _FSMEvent('gripper.GRASP', runtime, 'gripper', 'GRASP', 'GRASPED', 'state', on_fail='FAULT', on_fail_kind='state'),
                ],),
        pre=[],
        post=[(py_trees.common.Status.FAILURE, lambda: _bb_set('pick_failed', True)), (py_trees.common.Status.SUCCESS, lambda: _bb_set('pick_complete', True))])
