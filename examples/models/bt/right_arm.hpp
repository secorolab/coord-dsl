/*
 * This is an auto-generated file. Do not edit it directly.
 *
 * FSM: right_arm
 * FSM Description:
 *
 * -----------------------------------------------------
 * Usage example:
 * -----------------------------------------------------

#include "coord2b/functions/event_loop.h"
#include "coord2b/functions/fsm.h"
#include "right_arm.hpp"

struct user_data {

};

void yyyy_behavior(struct user_data *userData, struct events *eventData) {
    // ... do something

    produce_event(eventData, right_arm::E_ZZZZ);
}

void fsm_behavior(struct events *eventData, struct user_data *userData) {
    if (consume_event(eventData, right_arm::E_XXXX)) {
        yyyy_behavior(userData, eventData);
    }
    ...
}

int main() {

    struct user_data userData = {};
    struct fsm_nbx *fsm = right_arm::create_fsm();
    if (!fsm) return 1;

    while (true) {
        produce_event(fsm->eventData, right_arm::E_STEP);

        // run state machine, event loop
        fsm_behavior(fsm->eventData, &userData);
        fsm_step_nbx(fsm);
        reconfig_event_buffers(fsm->eventData);
    }

    right_arm::destroy_fsm(fsm);
    return 0;
}

 * -----------------------------------------------------
 */

#ifndef RIGHT_ARM_HPP
#define RIGHT_ARM_HPP

#include "coord2b/types/fsm.h"
#include "coord2b/types/event_loop.h"
#include <new>


namespace right_arm {

struct fsm_nbx *create_fsm();
void            destroy_fsm(struct fsm_nbx *fsm);

// sm states
enum e_states { IDLE = 0, PICKING, PICKED, MOVING_HANDOVER, HANDOVER_POSE, NUM_STATES };

static constexpr const char *STATE_URIS[NUM_STATES] = {
    "https://secorolab.github.io/models/coordination/fsm/right-arm/IDLE",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/PICKING",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/PICKED",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/MOVING_HANDOVER",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/HANDOVER_POSE",
};

// sm events
enum e_events { PICK = 0, PICK_DONE, HANDOVER, HANDOVER_DONE, NUM_EVENTS };

static constexpr const char *EVENT_URIS[NUM_EVENTS] = {
    "https://secorolab.github.io/models/coordination/fsm/right-arm/PICK",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/PICK_DONE",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/HANDOVER",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/HANDOVER_DONE",
};

// sm transitions
enum e_transitions {
    PICK_OBJECT = 0,
    FINISH_PICK,
    START_HANDOVER,
    FINISH_HANDOVER,
    NUM_TRANSITIONS
};

static constexpr const char *TRANSITION_URIS[NUM_TRANSITIONS] = {
    "https://secorolab.github.io/models/coordination/fsm/right-arm/PICK_OBJECT",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/FINISH_PICK",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/START_HANDOVER",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/FINISH_HANDOVER",
};

// sm reactions
enum e_reactions { ON_PICK = 0, ON_PICK_DONE, ON_HANDOVER, ON_HANDOVER_DONE, NUM_REACTIONS };

static constexpr const char *REACTION_URIS[NUM_REACTIONS] = {
    "https://secorolab.github.io/models/coordination/fsm/right-arm/ON_PICK",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/ON_PICK_DONE",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/ON_HANDOVER",
    "https://secorolab.github.io/models/coordination/fsm/right-arm/ON_HANDOVER_DONE",
};

inline struct fsm_nbx *create_fsm()
{

    struct fsm_nbx *fsm = new (std::nothrow) fsm_nbx{ .numReactions      = NUM_REACTIONS,
                                                      .numTransitions    = NUM_TRANSITIONS,
                                                      .numStates         = NUM_STATES,
                                                      .states            = nullptr,
                                                      .startStateIndex   = IDLE,
                                                      .endStateIndex     = HANDOVER_POSE,
                                                      .currentStateIndex = IDLE,
                                                      .eventData         = nullptr,
                                                      .reactions         = nullptr,
                                                      .transitions       = nullptr };
    if (!fsm) return nullptr;

    // sm states
    struct state *states = new (std::nothrow) state[NUM_STATES]{ { .name = "Idle" },
                                                                 { .name = "Picking" },
                                                                 { .name = "Picked" },
                                                                 { .name = "Moving_handover" },
                                                                 { .name = "Handover_pose" } };

    // sm transition table
    struct transition *transitions =
      new (std::nothrow) transition[NUM_TRANSITIONS]{ {
                                                        .startStateIndex = IDLE,
                                                        .endStateIndex   = PICKING,
                                                      },
                                                      {
                                                        .startStateIndex = PICKING,
                                                        .endStateIndex   = PICKED,
                                                      },
                                                      {
                                                        .startStateIndex = PICKED,
                                                        .endStateIndex   = MOVING_HANDOVER,
                                                      },
                                                      {
                                                        .startStateIndex = MOVING_HANDOVER,
                                                        .endStateIndex   = HANDOVER_POSE,
                                                      } };

    // sm reaction table
    struct event_reaction *reactions =
      new (std::nothrow) event_reaction[NUM_REACTIONS]{ {
                                                          .conditionEventIndex = PICK,
                                                          .transitionIndex     = PICK_OBJECT,
                                                          .numFiredEvents      = 0,
                                                          .firedEventIndices   = nullptr,
                                                        },
                                                        {
                                                          .conditionEventIndex = PICK_DONE,
                                                          .transitionIndex     = FINISH_PICK,
                                                          .numFiredEvents      = 0,
                                                          .firedEventIndices   = nullptr,
                                                        },
                                                        {
                                                          .conditionEventIndex = HANDOVER,
                                                          .transitionIndex     = START_HANDOVER,
                                                          .numFiredEvents      = 0,
                                                          .firedEventIndices   = nullptr,
                                                        },
                                                        {
                                                          .conditionEventIndex = HANDOVER_DONE,
                                                          .transitionIndex     = FINISH_HANDOVER,
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

} // namespace right_arm

#endif // RIGHT_ARM_HPP