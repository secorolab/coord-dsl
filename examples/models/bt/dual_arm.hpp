// SPDX-License-Identifier: MPL-2.0
// SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
#ifndef DUAL_ARM_BT_HPP
#define DUAL_ARM_BT_HPP

#include <behaviortree_cpp/bt_factory.h>
#include <filesystem>
#include <string>

#include "coord2b/functions/event_loop.h"
#include "coord2b/functions/fsm.h"
#include "left_arm.hpp"
#include "right_arm.hpp"

namespace dual_arm {
class DualArmRuntime
{
  public:
    DualArmRuntime()
    {
        fsm_left_arm_  = left_arm::create_fsm();
        fsm_right_arm_ = right_arm::create_fsm();
    }
    virtual ~DualArmRuntime()
    {
        left_arm::destroy_fsm(fsm_left_arm_);
        right_arm::destroy_fsm(fsm_right_arm_);
    }
    // Advance the left_arm controller one tick; produce completion events
    // (e.g. *_DONE) onto fsm->eventData once its current sub-behaviour finishes.
    virtual void step_left_arm(struct fsm_nbx *fsm) = 0;
    // Advance the right_arm controller one tick; produce completion events
    // (e.g. *_DONE) onto fsm->eventData once its current sub-behaviour finishes.
    virtual void step_right_arm(struct fsm_nbx *fsm) = 0;

    struct fsm_nbx *fsm_of(const std::string &instance)
    {
        if (instance == "left_arm") return fsm_left_arm_;
        if (instance == "right_arm") return fsm_right_arm_;
        return nullptr;
    }

    int event_index(const std::string &instance, const std::string &event)
    {
        if (instance == "left_arm") {
            if (event == "TAKE_POSE") return left_arm::TAKE_POSE;
            if (event == "TAKE_POSE_DONE") return left_arm::TAKE_POSE_DONE;
            if (event == "PLACE") return left_arm::PLACE;
            if (event == "PLACE_DONE") return left_arm::PLACE_DONE;
        }
        if (instance == "right_arm") {
            if (event == "PICK") return right_arm::PICK;
            if (event == "PICK_DONE") return right_arm::PICK_DONE;
            if (event == "HANDOVER") return right_arm::HANDOVER;
            if (event == "HANDOVER_DONE") return right_arm::HANDOVER_DONE;
        }
        return -1;
    }

    int state_index(const std::string &instance, const std::string &state)
    {
        if (instance == "left_arm") {
            if (state == "IDLE") return left_arm::IDLE;
            if (state == "MOVING_TO_TAKE_POSE") return left_arm::MOVING_TO_TAKE_POSE;
            if (state == "AT_TAKE_POSE") return left_arm::AT_TAKE_POSE;
            if (state == "PLACING") return left_arm::PLACING;
            if (state == "PLACED") return left_arm::PLACED;
        }
        if (instance == "right_arm") {
            if (state == "IDLE") return right_arm::IDLE;
            if (state == "PICKING") return right_arm::PICKING;
            if (state == "PICKED") return right_arm::PICKED;
            if (state == "MOVING_HANDOVER") return right_arm::MOVING_HANDOVER;
            if (state == "HANDOVER_POSE") return right_arm::HANDOVER_POSE;
        }
        return -1;
    }

    void step(const std::string &instance, struct fsm_nbx *fsm)
    {
        if (instance == "left_arm") {
            step_left_arm(fsm);
            return;
        }
        if (instance == "right_arm") {
            step_right_arm(fsm);
            return;
        }
    }

    // ---- Execution policy. Defaults drive the FSM synchronously from the BT
    // tick; override these for a self-driving controller (e.g. a real-time
    // thread stepping the FSM independently -- then dispatch()/current_state()
    // must be made thread-safe and advance() a no-op). ----

    // Inject a command event toward the instance's FSM.
    virtual void dispatch(const std::string &instance, unsigned int event)
    {
        produce_event(fsm_of(instance)->eventData, event);
    }
    // One coordination step: run the controller behaviour, then the coord2b step.
    virtual void advance(const std::string &instance)
    {
        struct fsm_nbx *fsm = fsm_of(instance);
        step(instance, fsm);
        reconfig_event_buffers(fsm->eventData);
        fsm_step_nbx(fsm);
    }
    // Edge detection: was `event` present on the current buffer this step?
    virtual bool event_present(const std::string &instance, unsigned int event)
    {
        return consume_event(fsm_of(instance)->eventData, event);
    }
    // Level detection: the instance's current FSM state index.
    virtual unsigned int current_state(const std::string &instance)
    {
        return fsm_of(instance)->currentStateIndex;
    }

  private:
    struct fsm_nbx *fsm_left_arm_  = nullptr;
    struct fsm_nbx *fsm_right_arm_ = nullptr;
};

// Drives an FSM instance from the tree: dispatches `event`, then each tick
// checks completion (`await`, edge on an event or level on a state) and
// optional failure (`on_fail`). RUNNING while the sub-behaviour runs.
class FSMEventNode : public BT::StatefulActionNode
{
  public:
    FSMEventNode(const std::string &name, const BT::NodeConfig &config, DualArmRuntime *runtime)
      : BT::StatefulActionNode(name, config), runtime_(runtime)
    {}

    static BT::PortsList providedPorts()
    {
        return {
            BT::InputPort<std::string>("fsm"),     BT::InputPort<std::string>("event"),
            BT::InputPort<std::string>("await"),   BT::InputPort<std::string>("await_kind"),
            BT::InputPort<std::string>("on_fail"), BT::InputPort<std::string>("on_fail_kind")
        };
    }

    BT::NodeStatus onStart() override
    {
        std::string event, await, await_kind;
        if (!getInput("fsm", instance_) || !getInput("event", event) || !getInput("await", await)
            || !getInput("await_kind", await_kind)) {
            return BT::NodeStatus::FAILURE;
        }
        command_        = runtime_->event_index(instance_, event);
        await_is_state_ = (await_kind == "state");
        await_index_    = resolve(await, await_is_state_);

        std::string on_fail, on_fail_kind;
        if (getInput("on_fail", on_fail) && !on_fail.empty()
            && getInput("on_fail_kind", on_fail_kind)) {
            fail_is_state_ = (on_fail_kind == "state");
            fail_index_    = resolve(on_fail, fail_is_state_);
        }

        if (runtime_->fsm_of(instance_) == nullptr || command_ < 0 || await_index_ < 0) {
            return BT::NodeStatus::FAILURE;
        }
        runtime_->dispatch(instance_, static_cast<unsigned int>(command_));
        return BT::NodeStatus::RUNNING;
    }

    BT::NodeStatus onRunning() override
    {
        runtime_->advance(instance_);
        if (fail_index_ >= 0 && reached(fail_index_, fail_is_state_))
            return BT::NodeStatus::FAILURE;
        return reached(await_index_, await_is_state_) ? BT::NodeStatus::SUCCESS
                                                      : BT::NodeStatus::RUNNING;
    }

    void onHalted() override {}

  private:
    int resolve(const std::string &name, bool is_state)
    {
        return is_state ? runtime_->state_index(instance_, name)
                        : runtime_->event_index(instance_, name);
    }
    bool reached(int index, bool is_state)
    {
        return is_state ? runtime_->current_state(instance_) == static_cast<unsigned int>(index)
                        : runtime_->event_present(instance_, static_cast<unsigned int>(index));
    }

    DualArmRuntime *runtime_;
    std::string     instance_;
    int             command_ = -1, await_index_ = -1, fail_index_ = -1;
    bool            await_is_state_ = false, fail_is_state_ = false;
};

inline void register_nodes(BT::BehaviorTreeFactory &factory, DualArmRuntime &runtime)
{
    factory.registerNodeType<FSMEventNode>("FSMEvent", &runtime);
}

inline BT::Tree create_tree(
  BT::BehaviorTreeFactory     &factory,
  const std::filesystem::path &xml_path,
  BT::Blackboard::Ptr          blackboard = BT::Blackboard::create()
)
{
    return factory.createTreeFromFile(xml_path, blackboard);
}
} // namespace dual_arm
#endif // DUAL_ARM_BT_HPP
