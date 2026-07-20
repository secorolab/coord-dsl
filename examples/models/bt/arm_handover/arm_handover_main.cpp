// SPDX-License-Identifier: MPL-2.0
// SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
// Author: Vamsi Kalagaturu
#include "arm_handover.hpp"
#include "coord_log.hpp"

#include <chrono>
#include <cstdio>
#include <string>

namespace {
constexpr int kWorkTicks = 3; // ticks an arm motion "runs" before it completes

// Simulated arm controller: while `fsm` sits in `active`, run for kWorkTicks
// then produce `done`. Returns true on the tick it completes.
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

class ArmHandover final : public arm_handover::ArmHandoverRuntime
{
  public:
    void step_left_arm(struct fsm_nbx *fsm) override
    {
        log_fsm("left_arm", std::string("state=") + fsm->states[fsm->currentStateIndex].name);
        run_phase(
          "left_arm", fsm, left_arm::MOVING_TO_TAKE_POSE, left_arm::TAKE_POSE_DONE, left_move_
        ) || run_phase("left_arm", fsm, left_arm::PLACING, left_arm::PLACE_DONE, left_place_);
    }
    void step_right_arm(struct fsm_nbx *fsm) override
    {
        log_fsm("right_arm", std::string("state=") + fsm->states[fsm->currentStateIndex].name);
        run_phase("right_arm", fsm, right_arm::PICKING, right_arm::PICK_DONE, right_pick_)
          || run_phase(
            "right_arm", fsm, right_arm::MOVING_HANDOVER, right_arm::HANDOVER_DONE, right_handover_
          );
    }

  private:
    int left_move_ = 0, left_place_ = 0, right_pick_ = 0, right_handover_ = 0;
};

int main(int argc, char *argv[])
{
    (void)argc;
    std::printf("=== arm_handover: SEQUENCE (one arm at a time) ===\n");
    ArmHandover             runtime;
    BT::BehaviorTreeFactory factory;
    arm_handover::register_nodes(factory, runtime);
    const auto  xml_path = std::filesystem::path(argv[0]).parent_path() / "arm_handover.xml";
    auto        tree     = arm_handover::create_tree(factory, xml_path);
    CoordLogger bt_logger(tree.rootNode());
    const auto  status = tree.tickWhileRunning(std::chrono::milliseconds(10));
    std::printf(
      "=== arm_handover: %s ===\n", status == BT::NodeStatus::SUCCESS ? "SUCCESS" : "FAILURE"
    );
    return status == BT::NodeStatus::SUCCESS ? 0 : 1;
}
