// SPDX-License-Identifier: MPL-2.0
// SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
#ifndef WAREHOUSE_PICK_BT_HPP
#define WAREHOUSE_PICK_BT_HPP

#include <behaviortree_cpp/bt_factory.h>
#include <filesystem>

namespace warehouse_pick {
class WarehousePickRuntime {
 public:
  virtual ~WarehousePickRuntime() = default;
  virtual BT::NodeStatus on_battery_ok(BT::TreeNode& node) = 0;
  virtual BT::NodeStatus on_go_charge(BT::TreeNode& node) = 0;
  virtual BT::NodeStatus on_object_visible(BT::TreeNode& node) = 0;
  virtual BT::NodeStatus on_detect_object(BT::TreeNode& node) = 0;
  virtual BT::NodeStatus on_at_goal(BT::TreeNode& node) = 0;
  virtual BT::NodeStatus on_move_to(BT::TreeNode& node) = 0;
  virtual BT::NodeStatus on_open_gripper(BT::TreeNode& node) = 0;
  virtual BT::NodeStatus on_close_gripper(BT::TreeNode& node) = 0;
  virtual BT::NodeStatus on_holding(BT::TreeNode& node) = 0;
  virtual BT::NodeStatus on_inspect(BT::TreeNode& node) = 0;
  virtual BT::NodeStatus on_place(BT::TreeNode& node) = 0;
};

inline void register_nodes(BT::BehaviorTreeFactory& factory, WarehousePickRuntime& runtime) {
  factory.registerSimpleCondition(
      "battery_ok",
      [&runtime](BT::TreeNode& node) { return runtime.on_battery_ok(node); },
      {
          BT::InputPort("min_level"),
      });
  factory.registerSimpleAction(
      "go_charge",
      [&runtime](BT::TreeNode& node) { return runtime.on_go_charge(node); },
      {
          BT::InputPort("dock"),
      });
  factory.registerSimpleCondition(
      "object_visible",
      [&runtime](BT::TreeNode& node) { return runtime.on_object_visible(node); },
      {
          BT::InputPort("target"),
      });
  factory.registerSimpleAction(
      "detect_object",
      [&runtime](BT::TreeNode& node) { return runtime.on_detect_object(node); },
      {
          BT::InputPort("target"),
          BT::OutputPort("pose"),
      });
  factory.registerSimpleCondition(
      "at_goal",
      [&runtime](BT::TreeNode& node) { return runtime.on_at_goal(node); },
      {
          BT::InputPort("goal"),
          BT::InputPort("tolerance"),
      });
  factory.registerSimpleAction(
      "move_to",
      [&runtime](BT::TreeNode& node) { return runtime.on_move_to(node); },
      {
          BT::InputPort("goal"),
          BT::InputPort("frame"),
          BT::InputPort("speed"),
          BT::InputPort("precise"),
          BT::InputPort("start_event"),
          BT::InputPort("end_event"),
      });
  factory.registerSimpleAction(
      "open_gripper",
      [&runtime](BT::TreeNode& node) { return runtime.on_open_gripper(node); });
  factory.registerSimpleAction(
      "close_gripper",
      [&runtime](BT::TreeNode& node) { return runtime.on_close_gripper(node); },
      {
          BT::BidirectionalPort("width"),
      });
  factory.registerSimpleCondition(
      "holding",
      [&runtime](BT::TreeNode& node) { return runtime.on_holding(node); },
      {
          BT::InputPort("object"),
      });
  factory.registerSimpleAction(
      "inspect",
      [&runtime](BT::TreeNode& node) { return runtime.on_inspect(node); },
      {
          BT::InputPort("object"),
          BT::OutputPort("result"),
      });
  factory.registerSimpleAction(
      "place",
      [&runtime](BT::TreeNode& node) { return runtime.on_place(node); },
      {
          BT::InputPort("object"),
          BT::InputPort("surface"),
      });
}

inline BT::Tree create_tree(BT::BehaviorTreeFactory& factory,
                            const std::filesystem::path& xml_path,
                            BT::Blackboard::Ptr blackboard = BT::Blackboard::create()) {
  return factory.createTreeFromFile(xml_path, blackboard);
}
}  // namespace warehouse_pick
#endif  // WAREHOUSE_PICK_BT_HPP
