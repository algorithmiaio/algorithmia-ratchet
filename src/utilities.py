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


def find_environment_id(environment_name, environments):
    for environment in environments:
        if environment['display_name'] == environment_name:
            return environment['id']
    raise Exception("Unable to find environment with display_name {}".format(environment_name))