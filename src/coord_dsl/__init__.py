from os.path import dirname, join
from textx import language, metamodel_from_file

fsm_meta_model = metamodel_from_file(join(dirname(__file__), "metamodels/fsm.tx"))


@language("fsm", "*.fsm")
def fsm_meta():
    "A language for describing finite state machines"
    return fsm_meta_model
