import Algorithmia
from Algorithmia import Client
import json
import tarfile
import shutil
import requests
from src.utilities import algorithm_exists, call_algo
from uuid import uuid4
import sys
from os import environ, path, listdir
from src.algorithm_creation import initialize_algorithm, migrate_datafiles, update_algorithm
from src.algorithm_testing import algorithm_test, algorithm_publish

WORKING_DIR = "/tmp/QA_TEMPLATE_WORKDIR"


def get_workflows(workflow_names):
    workflows = []
    for workflow_name in workflow_names:
        with open(f"workflows/{workflow_name}.json") as f:
            workflow_data = json.load(f)
            workflow_data['name'] = workflow_name
            workflows.append(workflow_data)
    return workflows


def find_algo(algo_name, artifact_path):
    local_path = f"algorithms/{algo_name}"
    if path.exists(local_path):
        shutil.copytree(local_path, artifact_path)
        return artifact_path
    else:
        raise Exception(f"algorithm {algo_name} not found in local cache (algorithms)")


def template_payload(payload, template_name):
    if isinstance(payload, str):
        payload = payload.replace("<algo>", template_name)
    elif isinstance(payload, dict):
        for key in payload.keys():
            if isinstance(payload[key], str):
                payload[key] = payload[key].replace("<algo>", template_name)
    return payload


def delete_workflows(workflows, destination_client: Client):
    for workflow in workflows:
        for algorithm in workflow.get("algorithms", []):
            algoname = algorithm["name"]
            username = next(destination_client.dir("").list()).path
            algo = destination_client.algo(f"algo://{username}/{algoname}")
            algo_url = "{}/v1/algorithms/{}".format(destination_client.apiAddress, algo.path)
            if algorithm_exists(algo):
                print(f"algorithm {username}/{algoname} exists; deleting...")
                headers = {"Content-Type": "application/json", "Authorization": "Simple {}".format(destination_client.apiKey)}
                req = requests.delete(algo_url, headers=headers)
                if req.status_code != 204:
                    raise Exception("Status code was: {}\n{}".format(req.status_code, req.text))
                else:
                    print(f"algorithm {username}/{algoname} was successfully deleted.")
            else:
                print(f"algorithm {username}/{algoname} doesn't exist, skipping...")


def create_workflows(workflows, source_client, destination_aems_master, destination_client):
    entrypoints = []
    for workflow in workflows:
        print(f"----- Creating workflow {workflow['name']} -----")
        if workflow.get("run_only", False):
            workflow_suffix = "1"
            print("----- Workflow is set to run-only, not recompilling -----")
        else:
            workflow_suffix = str(uuid4()).split('-')[-1]
            print(f"----- Workflow Suffix is: {workflow_suffix} -----")
        entrypoint_path = workflow['test_info'].get("entrypoint", None)
        algorithm_pairs = []
        for algorithm in workflow.get("algorithms", []):
            if path.exists(WORKING_DIR):
                shutil.rmtree(WORKING_DIR)
            print("\n")
            template_algorithm_name = algorithm['name']
            new_algorithm_name = f"{template_algorithm_name}_{workflow_suffix}"
            algorithm_pairs.append(( template_algorithm_name, new_algorithm_name))
            remote_code_path = algorithm.get("code", None)
            language = algorithm.get("language", "python-pip-old")
            environment = algorithm['environment']
            data_file_paths = algorithm['data_files']
            test_payload = algorithm['test_payload']
            artifact_path = f"{WORKING_DIR}/source"
            if remote_code_path:
                print("downloading code...")
                local_code_zip = source_client.file(remote_code_path).getFile().name
                tar = tarfile.open(local_code_zip)
                with tar.open(local_code_zip) as f:
                    f.extractall(path=artifact_path)
            else:
                print("checking for local code...")
                find_algo(template_algorithm_name, artifact_path)

            print("initializing algorithm...")
            algo_object = initialize_algorithm(new_algorithm_name, environment, destination_aems_master, destination_client)
            print("migrating datafiles...")
            migrate_datafiles(algo_object, data_file_paths, source_client, destination_client, WORKING_DIR)
            print("updating algorithm source...")
            update_algorithm(algo_object, template_algorithm_name, algorithm_pairs, destination_client, WORKING_DIR, artifact_path, language=language)
            print("testing algorithm...")
            payload = template_payload(test_payload, new_algorithm_name)
            algorithm_test(algo_object, payload)
            print("publishing algorithm...")
            published_algorithm = algorithm_publish(algo_object, test_payload)
            if entrypoint_path and entrypoint_path == template_algorithm_name:
                entrypoints.append(published_algorithm)
    return entrypoints


def workflow_test(algorithms, workflows):
    for algorithm, workflow in zip(algorithms, workflows):
        test_info = workflow['test_info']
        print("----- Testing workflow {} -----".format(workflow["name"]))
        for test in test_info['tests']:
            name = test['name']
            payload = test['payload']
            payload = template_payload(payload, algorithm.algoname)
            timeout = test['timeout']
            message = f"test {name} for {algorithm.username}/{algorithm.algoname} with timeout {timeout}"
            print("starting " + message)
            _ = call_algo(algorithm, payload)
            message = message + " succeeded."
            print(message)


if __name__ == "__main__":
    source_api_key = environ.get("SOURCE_API_KEY")
    source_ca_cert = environ.get("SOURCE_CA_CERT", None)
    destination_api_address = environ.get("DESTINATION_API_ADDRESS")
    destination_api_key = environ.get("DESTINATION_API_KEY")
    destination_ca_cert = environ.get("DESTINATION_CA_CERT", None)
    destination_aems_master = environ.get("DESTINATION_AEMS_MASTER", "prod")
    if len(sys.argv) > 1:
        workflow_names = [str(sys.argv[1])]
    else:
        workflow_names = []
        for file in listdir("workflows"):
            if file.endswith(".json"):
                workflow_names.append(file.split(".json")[0])

    workflows = get_workflows(workflow_names)
    if "source_info" in workflows[0]:
        source_api_address = workflows[0]['source_info']['cluster_address']
    else:
        source_api_address = "https://api.algorithmia.com"
    source_client = Algorithmia.client(api_key=source_api_key, api_address=source_api_address,
                                       ca_cert=source_ca_cert)
    destination_client = Algorithmia.client(api_key=destination_api_key, api_address=destination_api_address,
                                            ca_cert=destination_ca_cert)
    print("------- Starting Algorithm Benchmark Creation Procedure -------")
    entrypoint_algos = create_workflows(workflows, source_client, destination_aems_master, destination_client)
    print("------- Workflow Created, initiating QA Test Procedure -------")
    workflow_test(entrypoint_algos, workflows)
