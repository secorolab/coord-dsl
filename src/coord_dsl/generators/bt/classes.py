# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Typed textX objects for the behaviour-tree grammar."""

from coord_dsl.generators.common import IHasNamespaceDeclare, IHasParent


class BehaviourDecl(IHasParent):
    def __init__(self, parent, kind, name, ports):
        super().__init__(parent=parent)
        self.kind = kind
        self.name = name
        self.ports = ports


class PortDecl(IHasParent):
    def __init__(self, parent, direction, name, type):
        super().__init__(parent=parent)
        self.direction = direction
        self.name = name
        self.type = type


class BehaviourTree(IHasNamespaceDeclare):
    def __init__(self, parent, ns, name, params, root):
        super().__init__(parent=parent, ns=ns, name=name)
        self.params = params
        self.root = root


class MainBehaviourTree(BehaviourTree):
    pass


class CompositeNode(IHasParent):
    def __init__(self, parent, type, instance, ports, guards, children):
        super().__init__(parent=parent)
        self.type = type
        self.instance = instance
        self.ports = ports
        self.guards = guards
        self.children = children


class DecoratorNode(IHasParent):
    def __init__(self, parent, type, instance, ports, guards, child):
        super().__init__(parent=parent)
        self.type = type
        self.instance = instance
        self.ports = ports
        self.guards = guards
        self.child = child


class SubTreeNode(IHasParent):
    def __init__(self, parent, tree, instance, ports, guards):
        super().__init__(parent=parent)
        self.tree = tree
        self.instance = instance
        self.ports = ports
        self.guards = guards


class FSMDecl(IHasParent):
    def __init__(self, parent, name, source):
        super().__init__(parent=parent)
        self.name = name
        self.source = source


class FSMEventNode(IHasParent):
    def __init__(self, parent, fsm, event, await_fsm, await_target, fail_fsm, fail_target,
                 instance, ports, guards):
        super().__init__(parent=parent)
        self.fsm = fsm
        self.event = event
        self.await_fsm = await_fsm
        self.await_target = await_target
        self.fail_fsm = fail_fsm
        self.fail_target = fail_target
        self.instance = instance
        self.ports = ports
        self.guards = guards


class LeafNode(IHasParent):
    def __init__(self, parent, behaviour, instance, ports, guards, start_event, end_event):
        super().__init__(parent=parent)
        self.behaviour = behaviour
        self.instance = instance
        self.ports = ports
        self.guards = guards
        self.start_event = start_event
        self.end_event = end_event


class NodeGuards(IHasParent):
    def __init__(self, parent, items):
        super().__init__(parent=parent)
        self.items = items


class NodeGuard(IHasParent):
    def __init__(self, parent, kind, script):
        super().__init__(parent=parent)
        self.kind = kind
        self.script = script


class Port(IHasParent):
    def __init__(self, parent, name, blackboard, quantity, value):
        super().__init__(parent=parent)
        self.name = name
        self.blackboard = blackboard
        self.quantity = quantity
        self.value = value


class Quantity(IHasParent):
    def __init__(self, parent, num, unit):
        super().__init__(parent=parent)
        self.num = num
        self.unit = unit


class BlackboardRef(IHasParent):
    def __init__(self, parent, key):
        super().__init__(parent=parent)
        self.key = key


class EventName(IHasParent):
    def __init__(self, parent, ns, event, standalone):
        super().__init__(parent=parent)
        self.ns = ns
        self.event = event
        self.standalone = standalone
