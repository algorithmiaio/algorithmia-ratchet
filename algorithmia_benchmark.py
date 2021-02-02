import Algorithmia
import json
import tarfile
import shutil
import sys
from os import environ, path
from src.algorithm_creation import initialize_algorithm, migrate_datafiles, update_algorithm
from src.algorithm_testing import algorithm_test, algorithm_publish, call_algo

WORKING_DIR = "/tmp/QA_TEMPLATE_WORKDIR"


def get_workflow(workflow_name):
    with open(f"workflows/{workflow_name}.json") as f:
        workflow_data = json.load(f)
    return workflow_data


def find_algo(algo_name, artifact_path):
    local_path = f"algorithms/{algo_name}"
    if path.exists(local_path):
        shutil.copytree(local_path, artifact_path)
        return artifact_path
    else:
        raise Exception(f"algorithm {algo_name} not found in local cache (algorithms)")


def create_workflow(workflow, source_client, destination_aems_master, destination_client):
    entrypoint_path = workflow['test_info'].get("entrypoint", None)
    entrypoint = None
    for algorithm in workflow.get("algorithms", []):
        print("\n")
        algorithm_name = algorithm['name']
        remote_code_path = algorithm.get("code", None)
        language = algorithm['language']
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
            find_algo(algorithm_name, artifact_path)

        print("initializing algorithm...")
        algo_object = initialize_algorithm(algorithm_name, language, destination_aems_master, destination_client)
        print("migrating datafiles...")
        migrate_datafiles(algo_object, data_file_paths, source_client, destination_client, WORKING_DIR)
        print("updating algorithm source...")
        update_algorithm(algo_object, destination_client, WORKING_DIR, artifact_path)
        print("testing algorithm...")
        algorithm_test(algo_object, test_payload)
        print("publishing algorithm...")
        published_algorithm = algorithm_publish(algo_object, test_payload)
        if entrypoint_path and entrypoint_path == algorithm_name:
            entrypoint = published_algorithm
    return entrypoint


def workflow_test(algorithm, workflow):
    test_info = workflow['test_info']
    print("starting QA tests...")
    for test in test_info['tests']:
        name = test['name']
        payload = test['payload']
        timeout = test['timeout']
        message = f"test {name} with {payload} for {algorithm.username}/{algorithm.algoname} with timeout {timeout}"
        print("starting " + message)
        result = call_algo(algorithm, payload)
        if isinstance(result, Exception):
            message = message + " failed."
        else:
            message = message + " succeeded."
            print(result)
        print(message)


if __name__ == "__main__":
    source_api_key = environ.get("SOURCE_API_KEY")
    source_ca_cert = environ.get("SOURCE_CA_CERT", None)
    destination_api_address = environ.get("DESTINATION_API_ADDRESS")
    destination_api_key = environ.get("DESTINATION_API_KEY")
    destination_ca_cert = environ.get("DESTINATION_CA_CERT", None)
    destination_aems_master = environ.get("DESTINATION_AEMS_MASTER", "prod")
    if len(sys.argv) > 1:
        workflow_name = str(sys.argv[1])
    else:
        raise Exception("Argument not provided to function, please provide a workflow name.")
    workflow = get_workflow(workflow_name)
    source_client = Algorithmia.client(api_key=source_api_key, api_address=workflow['source_info']['cluster_address'],
                                       ca_cert=source_ca_cert)
    destination_client = Algorithmia.client(api_key=destination_api_key, api_address=destination_api_address,
                                            ca_cert=destination_ca_cert)
    print("------- Starting Algorithm Export/Import Procedure -------")
    entrypoint_algo = create_workflow(workflow, source_client, destination_aems_master, destination_client)
    print("------- Workflow Created, initiating QA Test Procedure -------")
    workflow_test(entrypoint_algo, workflow)
