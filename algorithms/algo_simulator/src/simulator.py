# %%
import os
import time
import pathlib
import subprocess

import numpy as np
import torch as th

# %%


this_dir = pathlib.Path(__file__).parent.absolute()


class LoadSimulator:
    def __init__(self, *args, **kwargs):
        self.cpu = []
        self.sleep = 0

        self.memory = None
        self.memory_allocated = 0

        self.array = None
        self.memory_allocated_np = 0

        self.th_tensor = None
        self.memory_allocated_gpu = 0

        self.config(*args, **kwargs)

    def __dict__(self):
        return {
            "cpu": self.cpu,
            "sleep": self.sleep,
            "memory_allocated": self.memory_allocated,
            "memory_allocated_np": self.memory_allocated_np,
            "memory_allocated_gpu": self.memory_allocated_gpu,
        }

    def __repr__(self):
        return str(self.__dict__())

    def config(self, cpu=None, gpu=None, mem=None, mem_numpy=None, mem_gpu=None):
        """
        Arguments
        ---------
            cpu: List of tuples (or lists), each tuple is (cpu_load, duration)
                It will simulate an initial load of those characteristics
                A single tuple can also be provided for single simulation
            gpu: int, duration to stress test the GPU

        """
        event = {}
        if cpu:
            event["cpu"] = cpu
        if gpu:
            event["gpu"] = gpu
        if mem:
            event["mem"] = mem
        if mem_numpy:
            event["mem_numpy"] = mem_numpy
        if mem_gpu:
            event["mem_gpu"] = mem_gpu

        self.simulate([event])

    def simulate(self, events):
        """
        Simulate a sequence of events

        Arguments
        ---------
            events: List of events to simulate in order

        Example
        -------
            [
                {"cpu": ["40", "1s"]},
                {"mem": 1000}
            ]
        """

        for event in events:
            if not event:
                # Empty event dict
                continue

            items = list(event.items())
            type_ = items[0][0]
            value = items[0][1]

            if type_ == "sleep":
                self.sleep(value)

            if type_ == "cpu":
                # Make it a list if we get a single value
                if not isinstance(value[0], list):
                    value = [value]
                self.cpu = value

                for load, duration in value:
                    self.stress_ng(load, duration)

            if type_ == "gpu":
                self.gpu_burn(value)

            if type_ == "mem":
                self.allocate_mem(value)

            if type_ == "mem_numpy":
                self.allocate_mem_numpy(value)

            if type_ == "mem_gpu":
                self.allocate_mem_gpu(value)

    def sleep(self, duration=0):
        time.sleep(duration)
        self.sleep = duration

    def stress_ng(self, load=100, duration=3, cpus=0):
        """
        Call stress-ng to simulate CPU load
        """

        tmp_path = os.path.join(this_dir, "tmp")

        if isinstance(duration, int):
            duration = f"{duration}s"

        try:
            cmd = [
                "stress-ng",
                "--temp-path",
                tmp_path,
                "-c",
                cpus,
                "--cpu-load",
                load,
                "-t",
                duration,
            ]
            cmd = [str(_) for _ in cmd]
            subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            print(e)

    def gpu_burn(self, duration=5):

        if isinstance(duration, int):
            duration = f"{duration}"

        try:
            # env = {"LD_LIBRARY_PATH": "/usr/local/cuda:$LD_LIBRARY_PATH"}
            cmd = [
                "./gpu-burn-master/gpu_burn",
                duration,
            ]
            cmd = [str(_) for _ in cmd]
            subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            print(e)

    def allocate_mem(self, mem_in_mb, raises=True):
        """
        Attempts to allocate the given amount of RAM to the running Python process.
        Arguments
        ---------
            mem_in_mb: the amount of RAM in megabytes to allocate
            raises: boolean, if True it raises an exception if there is not enough memory, if False it tries to allocate as much as possible
        Returns
        -------
            memory allocated in mb
        """

        try:
            # Each element takes approx 8 bytes
            # Multiply n by 1024**2 to convert from MB to Bytes
            self.memory = [0] * int(((mem_in_mb / 8) * (1024 ** 2)))
            self.memory_allocated = mem_in_mb
            return mem_in_mb

        except MemoryError as e:
            if raises:
                raise e
            # We didn't have enough RAM for our attempt, so we will recursively try
            # smaller amounts 10% smaller at a time
            self.stress_ram(int(mem_in_mb * 0.9))

    def allocate_mem_numpy(self, mem_in_mb):
        """
        Returns
        -------
            allocated memory in bytes
        """
        self.array = np.ones(shape=(mem_in_mb * (1024 ** 2)), dtype="u1")
        self.memory_allocated_np = self.array.size * self.array.itemsize

        return self.memory_allocated_np

    def allocate_mem_gpu(self, mem_in_mb):
        if not th.cuda.is_available():
            raise ValueError("Cannot allocate GPU memory: GPU not detected")

        cuda0 = th.cuda.current_device()

        self.th_tensor = th.ones(size=(mem_in_mb // 2 * (512 ** 2), ), dtype=th.float64, device=cuda0)

        self.memory_allocated_gpu = th.cuda.memory_allocated()

        print(bytesto(self.memory_allocated_gpu, 'm'))


def bytesto(bytes, to, bsize=1024):
    """convert bytes to megabytes, etc.
       sample code:
           print('mb= ' + str(bytesto(314575262000000, 'm')))
       sample output:
           mb= 300002347.946
    """

    a = {'k' : 1, 'm': 2, 'g' : 3, 't' : 4, 'p' : 5, 'e' : 6 }
    r = float(bytes)
    for i in range(a[to]):
        r = r / bsize

    return(r)

# %%

if __name__ == "__main__":
    # cpu = [("40", "5s"), ("80", "5s")]
    # model = LoadSimulator(cpu=cpu)

    # model = LoadSimulator(mem=1000)
    # model = LoadSimulator(mem_numpy=1000)
    # model = LoadSimulator(mem_gpu=1000)
    # model = LoadSimulator(mem_gpu=1234)

    model = LoadSimulator(gpu=5)

# %%
