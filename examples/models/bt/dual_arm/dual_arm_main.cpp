// SPDX-License-Identifier: MPL-2.0
// SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
// Author: Vamsi Kalagaturu
#include "dual_arm.hpp"
#include "coord_log.hpp"

#include <chrono>
#include <cstdio>
#include <string>

namespace {
constexpr int kWorkTicks = 3;

bool run_phase(
  const char     *who,
  struct fsm_nbx *fsm,
  unsigned int    active,
  unsigned int    done,
  int            &counter
)
{
    if (fsm->currentStateIndex != active) {
        counter = 0;
        return false;
    }
    if (++counter < kWorkTicks) return false;
    produce_event(fsm->eventData, done);
    counter = 0;
    log_fsm(who, std::string("finished ") + fsm->states[active].name + " -> produced *_DONE");
    return true;
}
} // namespace

class DualArm final : public dual_arm::DualArmRuntime
{
  public:
    void step_left_arm(struct fsm_nbx *fsm) override
    {
        log_fsm("left_arm", std::string("state=") + fsm->states[fsm->currentStateIndex].name);
        run_phase(
          "left_arm", fsm, left_arm::MOVING_TO_TAKE_POSE, left_arm::TAKE_POSE_DONE, left_move_
        );
    }
    void step_right_arm(struct fsm_nbx *fsm) override
    {
        log_fsm("right_arm", std::string("state=") + fsm->states[fsm->currentStateIndex].name);
        run_phase("right_arm", fsm, right_arm::PICKING, right_arm::PICK_DONE, right_pick_);
    }

  private:
    int left_move_ = 0, right_pick_ = 0;
};

int main(int argc, char *argv[])
{
    (void)argc;
    std::printf("=== dual_arm: PARALLEL (both arms advance together) ===\n");
    DualArm                 runtime;
    BT::BehaviorTreeFactory factory;
    dual_arm::register_nodes(factory, runtime);
    auto blackboard = BT::Blackboard::create();
    blackboard->set("left_arm_fault", false); // read by the retry [failure-if] guards
    blackboard->set("right_arm_fault", false);
    const auto  xml_path = std::filesystem::path(argv[0]).parent_path() / "dual_arm.xml";
    auto        tree     = dual_arm::create_tree(factory, xml_path, blackboard);
    CoordLogger bt_logger(tree.rootNode());
    const auto  status = tree.tickWhileRunning(std::chrono::milliseconds(10));
    std::printf(
      "=== dual_arm: %s ===\n", status == BT::NodeStatus::SUCCESS ? "SUCCESS" : "FAILURE"
    );
    return status == BT::NodeStatus::SUCCESS ? 0 : 1;
}
