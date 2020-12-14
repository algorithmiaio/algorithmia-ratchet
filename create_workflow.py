import Algorithmia
from Algorithmia import Client
from Algorithmia.errors import AlgorithmException, ApiError
from tqdm import tqdm
import tarfile
import os
from time import sleep
from shutil import rmtree
import sh
import json
from os import environ
from uuid import uuid4

WORKING_DIR = "/tmp/QA_TEMPLATE_WORKDIR"


def initialize_algorithm(user, algoname, mode, destination_client: Client):
    algo = destination_client.algo(f"{user}/{algoname}")
    try:
        _ = algo.info()
        print(f"algorithm {user}/{algoname} already exists; skipping initialization...")
        return algo
    except Exception:
        print(f"algorithm {user}/{algoname} doesn't exist, creating...")
        if mode == "python3":
            environment = "4beb6189-3e18-4a7a-a466-473bebe68a9f"
        elif mode == "python2":
            environment = "f7ed7c9b-d205-48ef-9ddf-61880b96c1f4"
        elif mode == "pytorch":
            environment = "5b027084-5fa7-431a-bdbd-f4f8eefc6ae1"
        elif mode == "tensorflow-2.3":
            environment = "e9c1291c-1295-41b9-a4c5-30f7f44920aa"
        elif mode == "tensorflow-1.14":
            environment = "27d3d02d-1da0-4868-986e-e0c6937e7d16"
        else:
            raise Exception("mode is not currently supported")

        algo.create(
            details={
                "label": f"QA - {algoname} - {str(uuid4())}",
            },
            settings={
                "source_visibility": "closed",
                "license": "apl",
                "algorithm_environment": environment,
                "network_access": "full",
                "pipeline_enabled": True
            }
        )
        return algo


def migrate_datafiles(algo, data_file_paths, source_client, destination_client, working_directory):
    artifact_path = f"{working_directory}/source"
    os.makedirs(artifact_path, exist_ok=True)
    collection_path = f"data://{algo.username}/{algo.algoname}"
    if not destination_client.dir(collection_path).exists():
        destination_client.dir(collection_path).create()
        for path in data_file_paths:
            filename = path.split("/")[-1]
            deployed_file_path = f"{collection_path}/{filename}"
            local_datafile_path = source_client.file(path).getFile().name
            destination_client.file(deployed_file_path).putFile(local_datafile_path)
        print(f"data files uploaded for {collection_path}")
    else:
        print(f"{collection_path} already exists, assuming datafiles are correct; skipping migration...")


def update_algorithm(algo, remote_client, local_code_path, working_directory):
    source_path = f"{working_directory}/source"
    api_key = remote_client.apiKey
    api_address = remote_client.apiAddress
    destination_algorithm_name = algo.algoname
    destination_username = algo.username
    templatable_username = "<user>"
    repo_path = f"{working_directory}/{destination_algorithm_name}"
    git_path = f"https://{algo.username}:{api_key}@git.{api_address.split('https://api.')[-1]}/git/{destination_username}/{destination_algorithm_name}.git"
    os.makedirs(source_path, exist_ok=True)
    os.makedirs(repo_path, exist_ok=True)

    tar = tarfile.open(local_code_path)
    with tar.open(local_code_path) as f:
        f.extractall(path=source_path)
    clone_bake = sh.git.bake(C=working_directory)
    publish_bake = sh.git.bake(C=repo_path)
    clone_bake.clone(git_path)
    sh.rm("-r", f"{repo_path}/src")
    sh.cp("-R", f"{source_path}/src", f"{repo_path}/src")
    sh.cp("-R", f"{source_path}/requirements.txt", f"{repo_path}/requirements.txt")
    sh.xargs.sed(sh.find(repo_path, "-type", "f"), i=f"s/{templatable_username}/{destination_username}/g")
    try:
        publish_bake.add(".")
        publish_bake.commit(m="automatic initialization commit")
        publish_bake.push()
    except Exception as e:
        if "Your branch is up to date with" not in str(e):
            raise e
        else:
            print(
                f"algorithm {destination_username}/{destination_algorithm_name} is already up to date, skipping update...")
            pass
    finally:
        rmtree(working_directory)
        return algo


def call_algo(algo, payload, timeout=None):
    try:
        if timeout:
            result = algo.set_options(timeout=timeout).pipe(payload).result
        else:
            result = algo.pipe(payload).result
        return result
    except Exception as e:
        return e


def algorithm_publish(algo, payload):
    try:
        algo.publish(
            settings={"algorithm_callability": "private"},
            version_info={
                "release_notes": "created programmatically",
                "sample_input": json.dumps(payload),
                "version_type": "minor"
            }
        )
        print(f"algorithm {algo.username}/{algo.algoname} published")
        return algo
    except ApiError as e:
        if "Version already published" in str(e):
            print(f"algorithm {algo.username}/{algo.algoname} already published")
            return algo
        else:
            raise e

def algorithm_test(algo, payload):
    try:
        algo_info = algo.info()
        latest_hash = algo_info.version_info.git_hash
        algo.url = f"/v1/algo/{algo.username}/{algo.algoname}/{latest_hash}"
        result = call_algo(algo, payload)
        if isinstance(result, Exception):
            raise result
        print(f"testing for algorithm {algo.username}/{algo.algoname}/{latest_hash} complete")
        return algo
    except AlgorithmException as e:
        if "version hash" in str(e):
            sleep(1)
            algorithm_test(algo, payload)
            return algo
        else:
            raise e


def get_workflow(workflow_name):
    with open(f"workflows/{workflow_name}.json") as f:
        workflow_data = json.load(f)
    return workflow_data


def create_workflow(workflow, source_client, destination_client):
    entrypoint_path = workflow['test_info'].get("entrypoint", None)
    algorithm_owner = workflow['algorithm_owner']
    entrypoint = None
    for algorithm in tqdm(workflow.get("algorithms", [])):
        print("\n")
        algorithm_name = algorithm['name']
        code_path = algorithm['code']
        language = algorithm['language']
        data_file_paths = algorithm['data_files']
        test_payload = algorithm['test_payload']
        print("downloading code...")
        local_code_zip = source_client.file(code_path).getFile().name
        print("initializing algorithm...")
        algo_object = initialize_algorithm(algorithm_owner, algorithm_name, language, destination_client)
        print("migrating datafiles...")
        migrate_datafiles(algo_object, data_file_paths, source_client, destination_client, WORKING_DIR)
        print("updating algorithm source...")
        update_algorithm(algo_object, destination_client, local_code_zip, WORKING_DIR)
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
        result = call_algo(algorithm, payload)
        message = f"test {name} with {payload} for {algorithm.username}/{algorithm.algoname} with timeout {timeout}"
        print("starting "+message)
        if isinstance(result, Exception):
            message = message + " failed."
        else:
            message = message + " succeeded."
            print(result)
        print(message)


if __name__ == "__main__":
    source_api_address = environ.get("SOURCE_API_ADDRESS")
    source_api_key = environ.get("SOURCE_API_KEY")
    destination_api_address = environ.get("DESTINATION_API_ADDRESS")
    destination_api_key = environ.get("DESTINATION_API_KEY")
    source_client = Algorithmia.client(api_key=source_api_key, api_address=source_api_address)
    destination_client = Algorithmia.client(api_key=destination_api_key, api_address=destination_api_address)
    workflow = get_workflow("image_parallel_pipelining")
    print("------- Starting Algorithm Export/Import Procedure -------")
    entrypoint_algo = create_workflow(workflow, source_client, destination_client)
    print("------- Workflow Created, initiating QA Test Procedure -------")
    workflow_test(entrypoint_algo, workflow)
