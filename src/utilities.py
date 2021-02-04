from Algorithmia.errors import ApiError


def algorithm_exists(algo):
    try:
        _ = algo.info()
        return True
    except ApiError:
        return False


def call_algo(algo, payload, timeout=None):
    if timeout:
        result = algo.set_options(timeout=timeout).pipe(payload).result
    else:
        result = algo.pipe(payload).result
    return result