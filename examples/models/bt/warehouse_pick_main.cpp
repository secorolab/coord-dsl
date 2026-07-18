// SPDX-License-Identifier: MPL-2.0
// SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
// Author: Vamsi Kalagaturu
#include "warehouse_pick.hpp"
#include "coord_log.hpp"

#include <iostream>
#include <string>

class WarehousePickRuntime final : public warehouse_pick::WarehousePickRuntime
{
  public:
    BT::NodeStatus on_battery_ok(BT::TreeNode &node) override
    {
        double min_level;
        return read(node, "min_level", min_level) && battery_ >= min_level
                 ? BT::NodeStatus::SUCCESS
                 : BT::NodeStatus::FAILURE;
    }

    BT::NodeStatus on_go_charge(BT::TreeNode &node) override
    {
        std::string dock;
        if (!read(node, "dock", dock)) return BT::NodeStatus::FAILURE;
        current_pose_ = dock;
        battery_      = 1.0;
        return BT::NodeStatus::SUCCESS;
    }

    BT::NodeStatus on_object_visible(BT::TreeNode &node) override
    {
        std::string target;
        return read(node, "target", target) && object_visible_ && target == target_
                 ? BT::NodeStatus::SUCCESS
                 : BT::NodeStatus::FAILURE;
    }

    BT::NodeStatus on_detect_object(BT::TreeNode &node) override
    {
        std::string target;
        if (!read(node, "target", target) || target.empty()) return BT::NodeStatus::FAILURE;
        target_         = target;
        object_visible_ = true;
        return node.setOutput("pose", pick_pose_) ? BT::NodeStatus::SUCCESS
                                                  : BT::NodeStatus::FAILURE;
    }

    BT::NodeStatus on_at_goal(BT::TreeNode &node) override
    {
        std::string goal;
        double      tolerance;
        if (!read(node, "goal", goal) || !read(node, "tolerance", tolerance) || tolerance < 0.0) {
            return BT::NodeStatus::FAILURE;
        }
        return current_pose_ == goal ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
    }

    BT::NodeStatus on_move_to(BT::TreeNode &node) override
    {
        std::string goal;
        std::string frame;
        double      speed;
        bool        precise;
        if (!read(node, "goal", goal) || !read(node, "frame", frame) || !read(node, "speed", speed)
            || !read(node, "precise", precise) || goal.empty() || frame.empty() || speed <= 0.0) {
            return BT::NodeStatus::FAILURE;
        }
        current_pose_ = goal;
        battery_ -= precise ? 0.02 : 0.01;
        return battery_ > 0.0 ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
    }

    BT::NodeStatus on_open_gripper(BT::TreeNode &) override
    {
        gripper_open_ = true;
        held_object_.clear();
        return BT::NodeStatus::SUCCESS;
    }

    BT::NodeStatus on_close_gripper(BT::TreeNode &node) override
    {
        double width;
        if (!read(node, "width", width) || width <= 0.0 || target_.empty())
            return BT::NodeStatus::FAILURE;
        gripper_open_ = false;
        held_object_  = target_;
        return node.setOutput("width", 0.0) ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
    }

    BT::NodeStatus on_holding(BT::TreeNode &node) override
    {
        std::string object;
        return read(node, "object", object) && object == held_object_ ? BT::NodeStatus::SUCCESS
                                                                      : BT::NodeStatus::FAILURE;
    }

    BT::NodeStatus on_inspect(BT::TreeNode &node) override
    {
        std::string object;
        if (!read(node, "object", object)) return BT::NodeStatus::FAILURE;
        const bool grasped = object == held_object_;
        if (!node.setOutput("result", std::string(grasped ? "grasped" : "missing"))) {
            return BT::NodeStatus::FAILURE;
        }
        return grasped ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
    }

    BT::NodeStatus on_place(BT::TreeNode &node) override
    {
        std::string object;
        std::string surface;
        if (!read(node, "object", object) || !read(node, "surface", surface)
            || object != held_object_ || surface != current_pose_) {
            return BT::NodeStatus::FAILURE;
        }
        held_object_.clear();
        return BT::NodeStatus::SUCCESS;
    }

  private:
    template<typename T> static bool read(BT::TreeNode &node, const char *port, T &value)
    {
        if (node.getInput(port, value)) return true;
        std::cerr << node.name() << ": missing or invalid " << port << "\n";
        return false;
    }

    double      battery_        = 1.0;
    bool        gripper_open_   = true;
    bool        object_visible_ = false;
    std::string current_pose_   = "home_dock";
    std::string held_object_;
    std::string pick_pose_ = "1;0;0";
    std::string target_;
};

int main(int argc, char *argv[])
{
    (void)argc;
    WarehousePickRuntime    runtime;
    BT::BehaviorTreeFactory factory;
    warehouse_pick::register_nodes(factory, runtime);
    auto blackboard = BT::Blackboard::create();
    blackboard->set("power_on", true);
    blackboard->set("battery", 1.0);
    blackboard->set("aborted", false);
    blackboard->set("attempts", 0);
    blackboard->set("cycles", 0);
    blackboard->set("estop", false);
    blackboard->set("reached", false);
    blackboard->set("target_object", "sample");
    blackboard->set("gripper_width", 0.08);
    blackboard->set("place_pose", "0;0;0");
    blackboard->set("waypoints", "");
    const auto  xml_path = std::filesystem::path(argv[0]).parent_path() / "warehouse_pick.xml";
    auto        tree     = warehouse_pick::create_tree(factory, xml_path, blackboard);
    CoordLogger bt_logger(tree.rootNode());
    const auto  status = tree.tickWhileRunning();
    std::printf(
      "=== warehouse_pick: %s ===\n", status == BT::NodeStatus::SUCCESS ? "SUCCESS" : "FAILURE"
    );
    return status == BT::NodeStatus::SUCCESS ? 0 : 1;
}
