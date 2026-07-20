// SPDX-License-Identifier: MPL-2.0
// SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
// Author: Vamsi Kalagaturu
//
// Synchronous C++ counterpart of py_pick_demo.py: the same py_pick tree, driven
// by the BT tick. Run with `--fault` to make the gripper fault (on-fail state).
#include "py_pick.hpp"
#include "coord_log.hpp"

#include <cstdio>
#include <string>

namespace {
constexpr int kWorkTicks = 3;

bool run_phase(const char *who, struct fsm_nbx *fsm, unsigned int active, unsigned int done,
               int &counter)
{
    if (fsm->currentStateIndex != active) {
        counter = 0;
        return false;
    }
    if (++counter < kWorkTicks) return false;
    produce_event(fsm->eventData, done);
    counter = 0;
    log_fsm(who, std::string("finished ") + fsm->states[active].name + " -> produced completion");
    return true;
}
}  // namespace

class PyPick final : public py_pick::PyPickRuntime
{
  public:
    explicit PyPick(bool fault) : fault_(fault) {}

    void step_right_arm(struct fsm_nbx *fsm) override
    {
        log_fsm("right_arm", std::string("state=") + fsm->states[fsm->currentStateIndex].name);
        run_phase("right_arm", fsm, right_arm::PICKING, right_arm::PICK_DONE, right_);
    }
    void step_gripper(struct fsm_nbx *fsm) override
    {
        log_fsm("gripper", std::string("state=") + fsm->states[fsm->currentStateIndex].name);
        const unsigned int done = fault_ ? gripper::GRASP_FAULT : gripper::GRASPED_OK;
        run_phase("gripper", fsm, gripper::GRASPING, done, grip_);
    }

  private:
    bool fault_;
    int right_ = 0, grip_ = 0;
};

int main(int argc, char *argv[])
{
    const bool fault = (argc > 1 && std::string(argv[1]) == "--fault");
    std::printf("=== py_pick: SEQUENCE, state await%s ===\n", fault ? "  (gripper set to FAULT)" : "");
    PyPick                  runtime(fault);
    BT::BehaviorTreeFactory factory;
    py_pick::register_nodes(factory, runtime);
    const auto  xml_path = std::filesystem::path(argv[0]).parent_path() / "py_pick.xml";
    auto        tree     = py_pick::create_tree(factory, xml_path);
    CoordLogger bt_logger(tree.rootNode());
    const auto  status = tree.tickWhileRunning(std::chrono::milliseconds(10));
    std::printf("=== py_pick: %s ===\n", status == BT::NodeStatus::SUCCESS ? "SUCCESS" : "FAILURE");
    return status == BT::NodeStatus::SUCCESS ? 0 : 1;
}
