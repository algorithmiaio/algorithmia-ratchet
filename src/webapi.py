import Algorithmia
from time import sleep
import requests

def find_environment(environment_name, environments):
    for environment in environments:
        if environment['display_name'] == environment_name:
            return {"id": environment['id'], "spec_id": environment['environment_specification_id']}
    print("environment {} not found.".format(environment_name))
    return {}

def get_available_environments(admin_api_key, fqdn):
    headers = {"Authorization": admin_api_key}
    url = f"{fqdn}/webapi/v1/algorithm-environments/environments/current"
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code != 200:
        raise Exception("Unable to get environments: {}".format(response.json()))
    results = response.json()
    return results


def get_downloadable_environments(admin_api_key, fqdn):
    headers = {"Authorization": admin_api_key}
    url = f"{fqdn}/webapi/v1/algorithm-environments/environments/available"
    print("getting list of downloadable environments")
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code != 200:
        raise Exception("Unable to get environments: {}".format(response.json()))
    results = response.json()
    return results

def sync_environment(admin_api_key, fqdn, environment_spec_id):
    headers = {"Authorization": admin_api_key}
    trigger_url = f"{fqdn}/webapi/v1/algorithm-environments/environment-specifications/{environment_spec_id}/syncs"
    print("syncing environment {} ...".format(environment_spec_id))
    response = requests.post(trigger_url, headers=headers)
    if response.status_code != 202:
        print(response.status_code)
        raise Exception("Unable to sync environment: {}".format(response.text))
    environment_id = response.json()['environment_id']
    status_url = f"{fqdn}/webapi/v1/algorithm-environments/environment-specifications/{environment_spec_id}/syncs/{environment_id}"
    while True:
        response = requests.get(status_url, headers=headers, verify=False)
        if response.status_code == 200:
            print("waiting for sync...")
            sleep(5)
        elif response.status_code == 404:
            print("sync complete")
            return True
        else:
            raise Exception("Syncing failed: {}".format(response.text))
