import Algorithmia
import requests


def get_environments(admin_api_key, fqdn):
    headers = {"Authorization": admin_api_key}
    url = f"{fqdn}/webapi/v1/algorithm-environments/environments/current"
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code != 200:
        raise Exception("Unable to get environments: {}".format(response.json()))
    results = response.json()
    return results

