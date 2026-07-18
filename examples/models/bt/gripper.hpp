/*
 * This is an auto-generated file. Do not edit it directly.
 *
 * FSM: gripper
 * FSM Description:
 *
 * -----------------------------------------------------
 * Usage example:
 * -----------------------------------------------------

#include "coord2b/functions/event_loop.h"
#include "coord2b/functions/fsm.h"
#include "gripper.hpp"

struct user_data {

};

void yyyy_behavior(struct user_data *userData, struct events *eventData) {
    // ... do something

    produce_event(eventData, gripper::E_ZZZZ);
}

void fsm_behavior(struct events *eventData, struct user_data *userData) {
    if (consume_event(eventData, gripper::E_XXXX)) {
        yyyy_behavior(userData, eventData);
    }
    ...
}

int main() {

    struct user_data userData = {};
    struct fsm_nbx *fsm = gripper::create_fsm();
    if (!fsm) return 1;

    while (true) {
        produce_event(fsm->eventData, gripper::E_STEP);

        // run state machine, event loop
        fsm_behavior(fsm->eventData, &userData);
        fsm_step_nbx(fsm);
        reconfig_event_buffers(fsm->eventData);
    }

    gripper::destroy_fsm(fsm);
    return 0;
}

 * -----------------------------------------------------
 */

#ifndef GRIPPER_HPP
#define GRIPPER_HPP

#include "coord2b/types/fsm.h"
#include "coord2b/types/event_loop.h"
#include <new>


namespace gripper {

struct fsm_nbx *create_fsm();
void            destroy_fsm(struct fsm_nbx *fsm);

// sm states
enum e_states { IDLE = 0, GRASPING, GRASPED, FAULT, NUM_STATES };

static constexpr const char *STATE_URIS[NUM_STATES] = {
    "https://secorolab.github.io/models/coordination/fsm/gripper/IDLE",
    "https://secorolab.github.io/models/coordination/fsm/gripper/GRASPING",
    "https://secorolab.github.io/models/coordination/fsm/gripper/GRASPED",
    "https://secorolab.github.io/models/coordination/fsm/gripper/FAULT",
};

// sm events
enum e_events { GRASP = 0, GRASPED_OK, GRASP_FAULT, NUM_EVENTS };

static constexpr const char *EVENT_URIS[NUM_EVENTS] = {
    "https://secorolab.github.io/models/coordination/fsm/gripper/GRASP",
    "https://secorolab.github.io/models/coordination/fsm/gripper/GRASPED_OK",
    "https://secorolab.github.io/models/coordination/fsm/gripper/GRASP_FAULT",
};

// sm transitions
enum e_transitions { START_GRASP = 0, FINISH_GRASP, FAIL_GRASP, NUM_TRANSITIONS };

static constexpr const char *TRANSITION_URIS[NUM_TRANSITIONS] = {
    "https://secorolab.github.io/models/coordination/fsm/gripper/START_GRASP",
    "https://secorolab.github.io/models/coordination/fsm/gripper/FINISH_GRASP",
    "https://secorolab.github.io/models/coordination/fsm/gripper/FAIL_GRASP",
};

// sm reactions
enum e_reactions { ON_GRASP = 0, ON_GRASPED_OK, ON_GRASP_FAULT, NUM_REACTIONS };

static constexpr const char *REACTION_URIS[NUM_REACTIONS] = {
    "https://secorolab.github.io/models/coordination/fsm/gripper/ON_GRASP",
    "https://secorolab.github.io/models/coordination/fsm/gripper/ON_GRASPED_OK",
    "https://secorolab.github.io/models/coordination/fsm/gripper/ON_GRASP_FAULT",
};

inline struct fsm_nbx *create_fsm()
{

    struct fsm_nbx *fsm = new (std::nothrow) fsm_nbx{ .numReactions      = NUM_REACTIONS,
                                                      .numTransitions    = NUM_TRANSITIONS,
                                                      .numStates         = NUM_STATES,
                                                      .states            = nullptr,
                                                      .startStateIndex   = IDLE,
                                                      .endStateIndex     = GRASPED,
                                                      .currentStateIndex = IDLE,
                                                      .eventData         = nullptr,
                                                      .reactions         = nullptr,
                                                      .transitions       = nullptr };
    if (!fsm) return nullptr;

    // sm states
    struct state *states = new (std::nothrow) state[NUM_STATES]{
        { .name = "Idle" }, { .name = "Grasping" }, { .name = "Grasped" }, { .name = "Fault" }
    };

    // sm transition table
    struct transition *transitions =
      new (std::nothrow) transition[NUM_TRANSITIONS]{ {
                                                        .startStateIndex = IDLE,
                                                        .endStateIndex   = GRASPING,
                                                      },
                                                      {
                                                        .startStateIndex = GRASPING,
                                                        .endStateIndex   = GRASPED,
                                                      },
                                                      {
                                                        .startStateIndex = GRASPING,
                                                        .endStateIndex   = FAULT,
                                                      } };

    // sm reaction table
    struct event_reaction *reactions =
      new (std::nothrow) event_reaction[NUM_REACTIONS]{ {
                                                          .conditionEventIndex = GRASP,
                                                          .transitionIndex     = START_GRASP,
                                                          .numFiredEvents      = 0,
                                                          .firedEventIndices   = nullptr,
                                                        },
                                                        {
                                                          .conditionEventIndex = GRASPED_OK,
                                                          .transitionIndex     = FINISH_GRASP,
                                                          .numFiredEvents      = 0,
                                                          .firedEventIndices   = nullptr,
                                                        },
                                                        {
                                                          .conditionEventIndex = GRASP_FAULT,
                                                          .transitionIndex     = FAIL_GRASP,
                                                          .numFiredEvents      = 0,
                                                          .firedEventIndices   = nullptr,
                                                        } };

    if (!states || !transitions || !reactions) {
        delete[] states;
        delete[] transitions;
        delete[] reactions;
        delete fsm;
        return nullptr;
    }

    for (unsigned int i = 0; i < NUM_REACTIONS; ++i) {
        if (reactions[i].numFiredEvents > 0 && !reactions[i].firedEventIndices) {
            for (unsigned int j = 0; j < NUM_REACTIONS; ++j) {
                delete[] reactions[j].firedEventIndices;
            }
            delete[] reactions;
            delete[] transitions;
            delete[] states;
            delete fsm;
            return nullptr;
        }
    }

    // sm event data
    struct events *eventData     = new (std::nothrow) events{};
    _Bool         *currentEvents = new (std::nothrow) _Bool[NUM_EVENTS]{ false };
    _Bool         *futureEvents  = new (std::nothrow) _Bool[NUM_EVENTS]{ false };
    if (!eventData || !currentEvents || !futureEvents) {
        delete[] states;
        delete[] transitions;
        if (reactions) {
            for (unsigned int i = 0; i < NUM_REACTIONS; ++i) {
                delete[] reactions[i].firedEventIndices;
            }
        }
        delete[] reactions;
        delete[] currentEvents;
        delete[] futureEvents;
        delete eventData;
        delete fsm;
        return nullptr;
    }
    eventData->numEvents     = NUM_EVENTS;
    eventData->currentEvents = currentEvents;
    eventData->futureEvents  = futureEvents;

    // sm fsm struct
    fsm->states      = states;
    fsm->eventData   = eventData;
    fsm->reactions   = reactions;
    fsm->transitions = transitions;

    return fsm;
}

inline void destroy_fsm(struct fsm_nbx *fsm)
{
    if (!fsm) return;
    if (fsm->reactions) {
        for (unsigned int i = 0; i < fsm->numReactions; ++i) {
            delete[] fsm->reactions[i].firedEventIndices;
            fsm->reactions[i].firedEventIndices = nullptr;
            fsm->reactions[i].numFiredEvents    = 0;
        }
    }
    if (fsm->eventData) {
        delete[] fsm->eventData->currentEvents;
        delete[] fsm->eventData->futureEvents;
        delete fsm->eventData;
        fsm->eventData = nullptr;
    }
    delete[] fsm->reactions;
    delete[] fsm->transitions;
    delete[] fsm->states;
    delete fsm;
}

} // namespace gripper

#endif // GRIPPER_HPP