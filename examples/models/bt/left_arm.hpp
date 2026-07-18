/*
 * This is an auto-generated file. Do not edit it directly.
 *
 * FSM: left_arm
 * FSM Description:
 *
 * -----------------------------------------------------
 * Usage example:
 * -----------------------------------------------------

#include "coord2b/functions/event_loop.h"
#include "coord2b/functions/fsm.h"
#include "left_arm.hpp"

struct user_data {

};

void yyyy_behavior(struct user_data *userData, struct events *eventData) {
    // ... do something

    produce_event(eventData, left_arm::E_ZZZZ);
}

void fsm_behavior(struct events *eventData, struct user_data *userData) {
    if (consume_event(eventData, left_arm::E_XXXX)) {
        yyyy_behavior(userData, eventData);
    }
    ...
}

int main() {

    struct user_data userData = {};
    struct fsm_nbx *fsm = left_arm::create_fsm();
    if (!fsm) return 1;

    while (true) {
        produce_event(fsm->eventData, left_arm::E_STEP);

        // run state machine, event loop
        fsm_behavior(fsm->eventData, &userData);
        fsm_step_nbx(fsm);
        reconfig_event_buffers(fsm->eventData);
    }

    left_arm::destroy_fsm(fsm);
    return 0;
}

 * -----------------------------------------------------
 */

#ifndef LEFT_ARM_HPP
#define LEFT_ARM_HPP

#include "coord2b/types/fsm.h"
#include "coord2b/types/event_loop.h"
#include <new>


namespace left_arm {

struct fsm_nbx *create_fsm();
void            destroy_fsm(struct fsm_nbx *fsm);

// sm states
enum e_states { IDLE = 0, MOVING_TO_TAKE_POSE, AT_TAKE_POSE, PLACING, PLACED, NUM_STATES };

static constexpr const char *STATE_URIS[NUM_STATES] = {
    "https://secorolab.github.io/models/coordination/fsm/left-arm/IDLE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/MOVING_TO_TAKE_POSE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/AT_TAKE_POSE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/PLACING",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/PLACED",
};

// sm events
enum e_events { TAKE_POSE = 0, TAKE_POSE_DONE, PLACE, PLACE_DONE, NUM_EVENTS };

static constexpr const char *EVENT_URIS[NUM_EVENTS] = {
    "https://secorolab.github.io/models/coordination/fsm/left-arm/TAKE_POSE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/TAKE_POSE_DONE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/PLACE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/PLACE_DONE",
};

// sm transitions
enum e_transitions {
    MOVE_TAKE_POSE = 0,
    FINISH_TAKE_POSE,
    START_PLACE,
    FINISH_PLACE,
    NUM_TRANSITIONS
};

static constexpr const char *TRANSITION_URIS[NUM_TRANSITIONS] = {
    "https://secorolab.github.io/models/coordination/fsm/left-arm/MOVE_TAKE_POSE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/FINISH_TAKE_POSE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/START_PLACE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/FINISH_PLACE",
};

// sm reactions
enum e_reactions { ON_TAKE_POSE = 0, ON_TAKE_POSE_DONE, ON_PLACE, ON_PLACE_DONE, NUM_REACTIONS };

static constexpr const char *REACTION_URIS[NUM_REACTIONS] = {
    "https://secorolab.github.io/models/coordination/fsm/left-arm/ON_TAKE_POSE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/ON_TAKE_POSE_DONE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/ON_PLACE",
    "https://secorolab.github.io/models/coordination/fsm/left-arm/ON_PLACE_DONE",
};

inline struct fsm_nbx *create_fsm()
{

    struct fsm_nbx *fsm = new (std::nothrow) fsm_nbx{ .numReactions      = NUM_REACTIONS,
                                                      .numTransitions    = NUM_TRANSITIONS,
                                                      .numStates         = NUM_STATES,
                                                      .states            = nullptr,
                                                      .startStateIndex   = IDLE,
                                                      .endStateIndex     = PLACED,
                                                      .currentStateIndex = IDLE,
                                                      .eventData         = nullptr,
                                                      .reactions         = nullptr,
                                                      .transitions       = nullptr };
    if (!fsm) return nullptr;

    // sm states
    struct state *states = new (std::nothrow) state[NUM_STATES]{ { .name = "Idle" },
                                                                 { .name = "Moving_to_take_pose" },
                                                                 { .name = "At_take_pose" },
                                                                 { .name = "Placing" },
                                                                 { .name = "Placed" } };

    // sm transition table
    struct transition *transitions =
      new (std::nothrow) transition[NUM_TRANSITIONS]{ {
                                                        .startStateIndex = IDLE,
                                                        .endStateIndex   = MOVING_TO_TAKE_POSE,
                                                      },
                                                      {
                                                        .startStateIndex = MOVING_TO_TAKE_POSE,
                                                        .endStateIndex   = AT_TAKE_POSE,
                                                      },
                                                      {
                                                        .startStateIndex = AT_TAKE_POSE,
                                                        .endStateIndex   = PLACING,
                                                      },
                                                      {
                                                        .startStateIndex = PLACING,
                                                        .endStateIndex   = PLACED,
                                                      } };

    // sm reaction table
    struct event_reaction *reactions =
      new (std::nothrow) event_reaction[NUM_REACTIONS]{ {
                                                          .conditionEventIndex = TAKE_POSE,
                                                          .transitionIndex     = MOVE_TAKE_POSE,
                                                          .numFiredEvents      = 0,
                                                          .firedEventIndices   = nullptr,
                                                        },
                                                        {
                                                          .conditionEventIndex = TAKE_POSE_DONE,
                                                          .transitionIndex     = FINISH_TAKE_POSE,
                                                          .numFiredEvents      = 0,
                                                          .firedEventIndices   = nullptr,
                                                        },
                                                        {
                                                          .conditionEventIndex = PLACE,
                                                          .transitionIndex     = START_PLACE,
                                                          .numFiredEvents      = 0,
                                                          .firedEventIndices   = nullptr,
                                                        },
                                                        {
                                                          .conditionEventIndex = PLACE_DONE,
                                                          .transitionIndex     = FINISH_PLACE,
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

} // namespace left_arm

#endif // LEFT_ARM_HPP