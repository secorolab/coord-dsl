import json
from coord_dsl import fsm_meta_model as fsm_meta
from dataclasses import dataclass, field
from textx import generator
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


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

    def to_json(self):
        return json.dumps(
            {
                "states": self.states,
                "start_state": self.start_state,
                "current_state": self.current_state,
                "end_state": self.end_state,
                "events": self.events,
                "transitions": self.transitions,
                "reactions": self.reactions,
                "transitions_table": self.transitions_table,
                "reactions_table": self.reactions_table,
            },
            indent=4,
        )


def parse_fsm(model):
    fsm = FSMData()

    fsm.states = [state.name for state in model.states]

    fsm.start_state = model.start_state.name
    fsm.current_state = model.current_state.name
    fsm.end_state = model.end_state.name

    fsm.events = [event.name for event in model.events]

    for transition in model.transitions:
        fsm.transitions.append(transition.name)
        fsm.transitions_table[transition.name] = {
            "from": transition.from_state.name,
            "to": transition.to_state.name,
        }

    for reaction in model.reactions:
        fsm.reactions.append(reaction.name)
        fsm.reactions_table[reaction.name] = {
            "when": reaction.when.name,
            "do": reaction.do.name,
            "fires": [event.name for event in reaction.fires],
            "num_fires": len(reaction.fires),
        }

    return fsm


@generator("fsm", "console")
def fsm_console_gen(metamodel, model, output_path, overwrite, debug, **custom_args):
    print("Generating FSM...")

    fsm = parse_fsm(model)

    print(fsm.to_json())


@generator("fsm", "cpp")
def fsm_cpp_gen(metamodel, model, output_path, overwrite, debug, **custom_args):
    print("Generating C code for FSM...")

    # get module path
    module_path = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(module_path / "templates"))
    template = env.get_template("fsm.hpp.jinja2")

    fsm = parse_fsm(model)

    filename = model._tx_filename.split("/")[-1].split(".")[0]

    output = template.render(
        {
            "fsm_name": filename,
            "data": fsm,
        }
    )

    if not output_path:
        output_path = f"{model._tx_filename}.hpp"
    with open(output_path, "w") as f:
        f.write(output)
    print(f"FSM C code generated at {output_path}")


@generator("fsm", "json")
def fsm_json_gen(metamodel, model, output_path, overwrite, debug, **custom_args):
    print("Generating JSON for FSM...")

    fsm = parse_fsm(model)

    if not output_path:
        output_path = f"{model._tx_filename}.json"

    with open(output_path, "w") as f:
        f.write(fsm.to_json())
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
