// SPDX-License-Identifier: MPL-2.0
// SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
// Author: Vamsi Kalagaturu
//
// Asynchronous integration: each FSM runs in its own 1 kHz controller thread
// (owns the coord2b step loop). The BT only DISPATCHES command events and POLLS
// FSM state (level/state await) across a mutex. Run with `--fault` to make the
// gripper fault and drive the sequence to FAILURE via the node's on-fail target.
#include "async_pick.hpp"
#include "coord_log.hpp"

#include <atomic>
#include <chrono>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

using namespace std::chrono_literals;

namespace {
constexpr int kMotionMs = 60; // each sub-behaviour runs ~60 ms of real time

struct Controller
{
    struct fsm_nbx   *fsm = nullptr;
    std::mutex        mtx;
    std::thread       thread;
    std::atomic<bool> running{ true };
    int               motion = 0; // ms elapsed in the active motion state
};
} // namespace

class AsyncPick final : public async_pick::AsyncPickRuntime
{
  public:
    explicit AsyncPick(bool fault) : fault_(fault)
    {
        start("right_arm");
        start("gripper");
    }
    ~AsyncPick() override
    {
        for (auto &entry : controllers_) {
            entry.second->running = false;
            entry.second->thread.join();
        }
        // base destructor frees the FSMs, safe now that the threads have stopped
    }

    // ---- controller behaviours: run inside the controller thread (lock held) ----
    void step_right_arm(struct fsm_nbx *fsm) override
    {
        run_motion(
          fsm, right_arm::PICKING, right_arm::PICK_DONE, controllers_["right_arm"]->motion
        );
    }
    void step_gripper(struct fsm_nbx *fsm) override
    {
        const unsigned int done = fault_ ? gripper::GRASP_FAULT : gripper::GRASPED_OK;
        run_motion(fsm, gripper::GRASPING, done, controllers_["gripper"]->motion);
    }

    // ---- execution policy: the FSMs are stepped by their own threads, so the BT
    // node must not step them -- it only dispatches and polls, under the lock. ----
    void dispatch(const std::string &inst, unsigned int event) override
    {
        Controller                 &c = *controllers_[inst];
        std::lock_guard<std::mutex> g(c.mtx);
        produce_event(c.fsm->eventData, event);
        log_fsm(inst.c_str(), "<= BT dispatched command");
    }
    void advance(const std::string &) override {} // no-op: controller threads drive the FSMs
    unsigned int current_state(const std::string &inst) override
    {
        Controller                 &c = *controllers_[inst];
        std::lock_guard<std::mutex> g(c.mtx);
        return c.fsm->currentStateIndex;
    }
    bool event_present(const std::string &inst, unsigned int event) override
    {
        Controller                 &c = *controllers_[inst];
        std::lock_guard<std::mutex> g(c.mtx);
        return consume_event(c.fsm->eventData, event);
    }

  private:
    static void run_motion(struct fsm_nbx *fsm, unsigned int active, unsigned int done, int &motion)
    {
        if (fsm->currentStateIndex != active) {
            motion = 0;
            return;
        }
        if (++motion == kMotionMs) produce_event(fsm->eventData, done);
    }

    void start(const std::string &name)
    {
        auto c             = std::make_unique<Controller>();
        c->fsm             = fsm_of(name);
        Controller *cp     = c.get();
        controllers_[name] = std::move(c);
        cp->thread         = std::thread([this, name, cp] { loop(name, cp); });
    }

    void loop(const std::string &name, Controller *c)
    {
        auto         next = std::chrono::steady_clock::now();
        unsigned int last = ~0u;
        while (c->running) {
            next += 1ms; // 1 kHz control rate
            {
                std::lock_guard<std::mutex> g(c->mtx);
                step(name, c->fsm); // controller behaviour (may produce completion events)
                reconfig_event_buffers(c->fsm->eventData);
                fsm_step_nbx(c->fsm);
                if (c->fsm->currentStateIndex != last) {
                    last = c->fsm->currentStateIndex;
                    log_fsm(
                      name.c_str(),
                      std::string("state=") + c->fsm->states[last].name + "  [1 kHz thread]"
                    );
                }
            }
            std::this_thread::sleep_until(next);
        }
    }

    bool                                               fault_;
    std::map<std::string, std::unique_ptr<Controller>> controllers_;
};

int main(int argc, char *argv[])
{
    const bool fault = (argc > 1 && std::string(argv[1]) == "--fault");
    std::printf(
      "=== async_pick: 1 kHz threaded controllers, STATE await%s ===\n",
      fault ? "  (gripper set to FAULT)" : ""
    );
    AsyncPick               runtime(fault);
    BT::BehaviorTreeFactory factory;
    async_pick::register_nodes(factory, runtime);
    const auto  xml_path = std::filesystem::path(argv[0]).parent_path() / "async_pick.xml";
    auto        tree     = async_pick::create_tree(factory, xml_path);
    CoordLogger bt_logger(tree.rootNode());
    const auto  status = tree.tickWhileRunning(5ms);
    std::printf(
      "=== async_pick: %s ===\n", status == BT::NodeStatus::SUCCESS ? "SUCCESS" : "FAILURE"
    );
    return status == BT::NodeStatus::SUCCESS ? 0 : 1;
}
