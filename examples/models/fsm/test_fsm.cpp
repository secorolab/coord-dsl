#include <chrono>
#include <csignal>
#include <iostream>
#include <ostream>
#include <thread>
#include "coord2b/functions/event_loop.h"
#include "coord2b/functions/fsm.h"
#include "ex_fsm.hpp"

sig_atomic_t stopFlag = 0;

void handler(int) { stopFlag = 1; }


int main()
{
    using clock = std::chrono::steady_clock;

    signal(SIGINT, &handler);

    constexpr auto tick_period  = std::chrono::microseconds(1000); // 1kHz
    constexpr auto print_period = std::chrono::milliseconds(500);  // 2Hz
    auto           next_tick    = clock::now();
    auto           now          = clock::now();
    auto           next_print   = now + print_period;

    auto fsm     = ex_fsm::create_fsm();
    bool compile = true;
    printf("Starting generated FSM example. Press Ctrl+C to exit.\n\n");
    while (!stopFlag) {
        next_tick += tick_period;

        produce_event(fsm->eventData, ex_fsm::E_STEP);

        // run state machine, event loop
        fsm_step_nbx(fsm);
        reconfig_event_buffers(fsm->eventData);

        // handle print
        now = clock::now();
        if (now > next_print) {
            next_print += print_period;
            std::cout << "State: " << fsm->states[fsm->currentStateIndex].name << " ("
                      << ex_fsm::STATE_URIS[fsm->currentStateIndex] << ")" << std::endl;

            if (fsm->currentStateIndex == ex_fsm::S_CONFIGURE) {
                produce_event(fsm->eventData, ex_fsm::E_CONFIGURE_EXIT);
            } else if (fsm->currentStateIndex == ex_fsm::S_IDLE) {
                if (compile) {
                    produce_event(fsm->eventData, ex_fsm::E_IDLE_EXIT_COMPILE);
                } else {
                    produce_event(fsm->eventData, ex_fsm::E_IDLE_EXIT_EXECUTE);
                }
                compile = !compile;
            } else if (fsm->currentStateIndex == ex_fsm::S_COMPILE) {
                produce_event(fsm->eventData, ex_fsm::E_COMPILE_EXIT);
            } else if (fsm->currentStateIndex == ex_fsm::S_EXECUTE) {
                produce_event(fsm->eventData, ex_fsm::E_EXECUTE_EXIT);
            }
        }

        std::this_thread::sleep_until(next_tick);
    }

    ex_fsm::destroy_fsm(fsm);

    return 0;
}
