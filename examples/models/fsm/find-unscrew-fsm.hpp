/*
 * This is an auto-generated file. Do not edit it directly.
 *
 * FSM: find-unscrew-fsm
 * FSM Description: Coordinate find -> loosen via motion monitor events
 *
 * -----------------------------------------------------
 * Usage example:
 * -----------------------------------------------------

#include "find-unscrew-fsm.fsm.hpp"

struct user_data {

};

void yyyy_behavior(struct user_data *userData, struct events *eventData) {
    // ... do something

    produce_event(eventData, E_ZZZZ);
}

void fsm_behavior(struct events *eventData, struct user_data *userData) {
    if (consume_event(eventData, E_XXXX)) {
        yyyy_behavior(userData, eventData);
    }
    ...
}

int main() {

    struct user_data userData = {};
    struct fsm_nbx *fsm = create_fsm();
    if (!fsm) return 1;

    while (true) {
        produce_event(fsm->eventData, E_STEP);

        // run state machine, event loop
        fsm_behavior(fsm->eventData, &userData);
        fsm_step_nbx(fsm);
        reconfig_event_buffers(fsm->eventData);
    }

    destroy_fsm(fsm);
    return 0;
}

 * -----------------------------------------------------
 */

#ifndef FIND-UNSCREW-FSM_FSM_HPP
#define FIND-UNSCREW-FSM_FSM_HPP

#include "coord2b/types/fsm.h"
#include "coord2b/types/event_loop.h"
#include <new>

struct fsm_nbx * create_fsm();
void destroy_fsm(struct fsm_nbx * fsm);

// sm states
enum e_states {
    S_START = 0,
    S_CONFIGURE,
    S_FIND,
    S_LOOSEN,
    S_EXIT,
    NUM_STATES
};

// sm events
enum e_events {
    E_CONFIGURED = 0,
    evt_rotation_limit_reached,
    evt_torque_upper_limit_reached,
    E_LOOSEN_DONE,
    NUM_EVENTS
};

// sm transitions
enum e_transitions {
    T_START_CONFIGURE = 0,
    T_CONFIGURE_FIND,
    T_FIND_LOOSEN,
    T_FIND_EXIT,
    T_LOOSEN_EXIT,
    NUM_TRANSITIONS
};

// sm reactions
enum e_reactions {
    R_CONFIGURED = 0,
    R_ROTATION_LIMIT,
    R_TORQUE_UPPER,
    R_LOOSEN_DONE,
    NUM_REACTIONS
};

inline struct fsm_nbx * create_fsm() {

    struct fsm_nbx * fsm = new (std::nothrow) fsm_nbx{
        .numReactions = NUM_REACTIONS,
        .numTransitions = NUM_TRANSITIONS,
        .numStates = NUM_STATES,
        .states = nullptr,
        .startStateIndex = S_START,
        .endStateIndex = S_EXIT,
        .currentStateIndex = S_START,
        .eventData = nullptr,
        .reactions = nullptr,
        .transitions = nullptr
    };
    if (!fsm) return nullptr;

    // sm states
    struct state * states = new (std::nothrow) state[NUM_STATES]{
        {.name = "S_start"}, 
        {.name = "S_configure"}, 
        {.name = "S_find"}, 
        {.name = "S_loosen"}, 
        {.name = "S_exit"} 
    };

    // sm transition table
    struct transition * transitions = new (std::nothrow) transition[NUM_TRANSITIONS]{
        {
            .startStateIndex = S_START,
            .endStateIndex = S_CONFIGURE,
        }, 
        {
            .startStateIndex = S_CONFIGURE,
            .endStateIndex = S_FIND,
        }, 
        {
            .startStateIndex = S_FIND,
            .endStateIndex = S_LOOSEN,
        }, 
        {
            .startStateIndex = S_FIND,
            .endStateIndex = S_EXIT,
        }, 
        {
            .startStateIndex = S_LOOSEN,
            .endStateIndex = S_EXIT,
        } 
    };

    // sm reaction table
    struct event_reaction * reactions = new (std::nothrow) event_reaction[NUM_REACTIONS]{
        {
            .conditionEventIndex = E_CONFIGURED,
            .transitionIndex = T_CONFIGURE_FIND,
            .numFiredEvents = 0,
            .firedEventIndices = nullptr,
    
        }, 
        {
            .conditionEventIndex = evt_rotation_limit_reached,
            .transitionIndex = T_FIND_LOOSEN,
            .numFiredEvents = 0,
            .firedEventIndices = nullptr,
    
        }, 
        {
            .conditionEventIndex = evt_torque_upper_limit_reached,
            .transitionIndex = T_FIND_EXIT,
            .numFiredEvents = 0,
            .firedEventIndices = nullptr,
    
        }, 
        {
            .conditionEventIndex = E_LOOSEN_DONE,
            .transitionIndex = T_LOOSEN_EXIT,
            .numFiredEvents = 0,
            .firedEventIndices = nullptr,
    
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
    struct events * eventData = new (std::nothrow) events{};
    _Bool * currentEvents = new (std::nothrow) _Bool[NUM_EVENTS]{false};
    _Bool * futureEvents = new (std::nothrow) _Bool[NUM_EVENTS]{false};
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
    eventData->numEvents = NUM_EVENTS;
    eventData->currentEvents = currentEvents;
    eventData->futureEvents = futureEvents;

    // sm fsm struct
    fsm->states = states;
    fsm->eventData = eventData;
    fsm->reactions = reactions;
    fsm->transitions = transitions;

    return fsm;
}

inline void destroy_fsm(struct fsm_nbx * fsm) {
    if (!fsm) return;
    if (fsm->reactions) {
        for (unsigned int i = 0; i < fsm->numReactions; ++i) {
            delete[] fsm->reactions[i].firedEventIndices;
            fsm->reactions[i].firedEventIndices = nullptr;
            fsm->reactions[i].numFiredEvents = 0;
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

#endif // FIND-UNSCREW-FSM_FSM_HPP