import Algorithmia
from multiprocessing.pool import ThreadPool
from time import time

# API calls will begin at the apply() method, with the request body passed as 'input'
# For more details, see algorithmia.com/developers/algorithm-development/languages

sample_image_url = "https://james-s-public.s3.amazonaws.com/lena.png"
client = Algorithmia.client()
processing_algorithm = "algo://<user>/DeepFashion/latestPrivate"
MAX_CONCURRENT_CONNECTIONS=12

def process(url, client):
    """
    Calls an algorithm with an image url and the connected Algorithmia Client.
    In this case, instead of returning the response, we instead return the wall duration that this algorithm took to compute.
    """
    t0 = time()
    input = {
       "image": [url],
       "model":"small",
       "tags_only": True
    }
    client.algo(processing_algorithm).pipe(input)
    t1 = time()

    return t1-t0


def apply(input):
    """
    This algorithm can either accept an integer or list of strings as input.
    If an integer is provided, we assume that it's the batch size, and we create a batch consisting of our sample image.
    If a list of strings is provided, we assume that each string is a url and our batch is ready for processing.

    We then process the batch in parallel with the limit MAX_CONCURRENT_CONNECTIONS defining our threadpool size, and return the timing metrics from the run.
    """
    if isinstance(input, int):
        batch = [sample_image_url for _ in range(input)]
    elif isinstance(input, list):
        batch = input
    else:
        raise Exception("input must be either a list of urls, or an int value")
    payload = [(url, client) for url in batch]
    pool = ThreadPool(MAX_CONCURRENT_CONNECTIONS)
    timings = pool.starmap(func=process, iterable=payload)
    max_time = max(timings)
    min_time = min(timings)
    avg_time = sum(timings) / float(len(timings))
    return {"maximum_time": max_time, "minimum_time": min_time, "average_time": avg_time}


if __name__ == "__main__":
    num_iters = 1000
    print(apply(num_iters))
