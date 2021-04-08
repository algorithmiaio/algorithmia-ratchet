# %%

import os
import json
import pathlib

from Algorithmia import ADK

try:
    from .simulator import LoadSimulator
except Exception:
    from simulator import LoadSimulator

# %%


def apply(input, model):
    if not isinstance(input, dict):
        return "Input should be JSON"

    if "model" in input:
        model.config(**input["model"])

    if "inference" in input:
        inference = LoadSimulator()
        inference.simulate(input["inference"])
        return "Simulated inference load: " + str(inference)

    return "OK"


def load():
    this_dir = pathlib.Path(__file__).parent.absolute()

    ## Load init config from JSON
    init_events_file = os.path.join(this_dir, "init_events.json")
    if os.path.exists(init_events_file):
        with open(init_events_file, "r") as f:
            init_events = json.load(f)
        print("Init events:", init_events)

    model = LoadSimulator()
    model.simulate(init_events)

    return model


# Run the algo
algo = ADK(apply, load)
algo.init({})
