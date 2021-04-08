# Algorithm simulator

This algorithm provides a way to simulate CPU load, GPU load and memory in RAM and GPU
for a mode and its inference requests.

The algorithm is fully configurable via JSON requests and its based on "events" where one event is one JSON object.
For example the initial load of an algorithm could be these series of events:

1. Download a model from data storage: 5 seconds waiting for IO
2. Load into memory generates some CPU load: 40% for 2s followed by 80% for 2s
3. Memory allocated is now 1 GB of RAM of Python objects and 1 GB of NumPy arrays
4. Load another part of the model to a GPU generates GPU load
5. Memory allocacted into the GPU is now 1GB

The list of events would be:

```json
[
    {"sleep": 5},
    {"cpu": [["40", "2s"], ["80", "2s"]]},
    {"mem": 1000},
    {"mem_numpy": 1000},
    {"gpu": ["5s"]},
    {"mem_gpu": "1000"}
]
```

| Param | Desc | Value |
|---|---|---|
| `sleep` | Sleep for an amount of time | `int`. Number of seconds to sleep for |
| `cpu` | CPU load simulator | List of lists. Each child is a list of two values: `["cpu_load", "duration"]` |
| `gpu` | GPU usage | `int`. Number of seconds to simulate matrix multiplication in the GPU |
| `mem` | Memory as Python objects | `int`. MB of memory to allocate |
| `mem_numpy` | Memory as a Numpy array | `int`. MB of memory to allocate using numpy arrays |
| `mem_gpu` | Memory in GPU as PyTorch tensor | `int`. MB of GPU memory to allocate (if GPU is present) |

The algorithm consits two parts:

1. Model (constant load)
2. Request (variable load)

## Model: Constant load

To simulate initial load of an algorithm we read the events from `src/init_events.json`.

After that it's possible to configure the constant load with a request with a JSON object.
For example to wait 5 seconds and go from 1 GB of RAM to 2 GB

```json
{
    "model":[
        {"sleep": 5}
        {"mem": 2000}
    ]
}
```

## Request: Variable load

Once the initial model is loaded we can make inference simulations that wont modify
the constant load.

Requests are based on JSON objets that will simulate any events passed as parameters.

For example to simulate one single event of some CPU usage

```json
{
    "inference":[
        {"cpu": ["70", "2s"]}
    ]
}
```

To simulate a sequence of events in order:

```json
{
    "inference":[
        {"cpu": [["40", "2s"], ["80", "2s"]]},
        {"mem": 1000},
        {"mem_numpy": 1000},
        {"sleep": 5},
        {"mem_gpu": "1000"}
    ]
}
```


## References

- CPU simulator: [stress-ng](https://wiki.ubuntu.com/Kernel/Reference/stress-ng)
