import json
from coord_dsl import fsm_meta_model as fsm_meta
from dataclasses import dataclass, field
from textx import generator


@dataclass
class FSMData:
    states: list = field(default_factory=list)
    start_state: str = ""
    current_state: str = ""
    end_state: str = ""
    events: list = field(default_factory=list)
    transitions: list = field(default_factory=list)
    reactions: list = field(default_factory=list)
    transitions_table: dict = field(default_factory=dict)
    reactions_table: dict = field(default_factory=dict)


def parse_fsm(model):
    fsm = FSMData()

    fsm.states = [state.name for state in model.states]

    fsm.start_state = model.start_state.name
    fsm.current_state = model.current_state.name
    fsm.end_state = model.end_state.name

    fsm.events = [event.name for event in model.events]

    for transition in model.transitions:
        fired_events = (
            [event.name for event in transition.fires]
            if hasattr(transition, "fires") and transition.fires
            else []
        )

        fsm.transitions.append(transition.name)
        fsm.transitions_table[transition.name] = {
            "from": transition.from_state.name,
            "to": transition.to_state.name,
            "fires": fired_events,
            "num_fires": len(fired_events),
        }

        fsm.reactions.append(transition.when.name)

        reaction_name = f"R_{transition.when.name}"

        if reaction_name not in fsm.reactions_table:
            fsm.reactions_table[reaction_name] = {
                "when": transition.when.name,
                "transitions": [transition.name],
                "num_transitions": 1,
            }
        else:
            fsm.reactions_table[reaction_name]["transitions"].append(transition.name)
            fsm.reactions_table[reaction_name]["num_transitions"] += 1

    fsm.states.append("NUM_STATES")
    fsm.events.append("NUM_EVENTS")
    fsm.transitions.append("NUM_TRANSITIONS")
    fsm.reactions.append("NUM_REACTIONS")

    return fsm


@generator("fsm", "c")
def fsm_c_gen(metamodel, model, output_path, overwrite, debug, **custom_args):
    print("Generating C code for FSM...")
    print("model: ", model._tx_filename)

    fsm = parse_fsm(model)


@generator("fsm", "json")
def fsm_json_gen(metamodel, model, output_path, overwrite, debug, **custom_args):
    print("Generating JSON for FSM...")

    fsm = parse_fsm(model)
    fsm_dict = {
        "states": list(fsm.states),
        "start_state": fsm.start_state,
        "current_state": fsm.current_state,
        "end_state": fsm.end_state,
        "events": list(fsm.events),
        "transitions": list(fsm.transitions),
        "reactions": list(fsm.reactions),
        "transitions_table": fsm.transitions_table,
        "reactions_table": fsm.reactions_table,
    }

    if not output_path:
        output_path = f"{model._tx_filename}.json"

    with open(output_path, "w") as f:
        json.dump(fsm_dict, f, indent=4)
    print(f"FSM JSON generated at {output_path}")


if __name__ == "__main__":
    model = fsm_meta.model_from_file("../models/program.fsm")

    fsm = parse_fsm(model)

    # convert the FSM object to a dictionary
    fsm_dict = {
        "states": list(fsm.states),
        "start_state": fsm.start_state,
        "current_state": fsm.current_state,
        "end_state": fsm.end_state,
        "events": list(fsm.events),
        "transitions": list(fsm.transitions),
        "reactions": list(fsm.reactions),
        "transitions_table": fsm.transitions_table,
        "reactions_table": fsm.reactions_table,
    }

    print(json.dumps(fsm_dict, indent=4))
