import Algorithmia
from Algorithmia import Client
from Algorithmia.errors import AlgorithmException, ApiError
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
        elif mode == "tensorflow":
            environment = "d6110155-1452-4a62-bd51-28d099ba51fc"
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


def update_algorithm(algo, password, cluster_url, local_code_path, working_directory):
    source_path = f"{working_directory}/source"
    destination_algorithm_name = algo.algoname
    destination_username = algo.username
    templatable_username = "<user>"
    repo_path = f"{working_directory}/{destination_algorithm_name}"
    git_path = f"https://{algo.username}:{password}@git.{cluster_url.split('https://api.')[-1]}/git/{destination_username}/{destination_algorithm_name}.git"
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


def algorithm_test(algo, payload):
    try:
        algo_info = algo.info()
        latest_hash = algo_info.version_info.git_hash
        algo.url = f"/v1/algo/{algo.username}/{algo.algoname}/{latest_hash}"
        _ = algo.pipe(payload)
        print(f"testing for algorithm {algo.username}/{algo.algoname}/{latest_hash} complete")
        algo.publish(
            settings={"algorithm_callability": "private"},
            version_info={
                "release_notes": "created programmatically",
                "sample_input": json.dumps(payload),
                "version_type": "minor"
            }
        )
    except AlgorithmException as e:
        if "version hash" in str(e):
            sleep(1)
            algorithm_test(algo, payload)
            pass
        else:
            print(e)
            raise e
    except ApiError as e:
        if "Version already published" in str(e):
            pass
        else:
            raise e


def create_workflow(workflow_name, artifact_client, deploy_client, username, password):
    with open(f"workflows/{workflow_name}.json") as f:
        workflow_data = json.load(f)
    for algorithm in workflow_data.get("algorithms", []):
        algorithm_name = algorithm['name']
        code_path = algorithm['code']
        language = algorithm['language']
        data_file_paths = algorithm['data_files']
        test_payload = algorithm['test_payload']
        local_code_zip = artifact_client.file(code_path).getFile().name
        algo_object = initialize_algorithm(username, algorithm_name, language, deploy_client)
        migrate_datafiles(algo_object, data_file_paths, artifact_client, deploy_client, WORKING_DIR)
        update_algorithm(algo_object, password, deploy_client.apiAddress, local_code_zip, WORKING_DIR)
        algorithm_test(algo_object, test_payload)


if __name__ == "__main__":
    source_api_address = environ.get("SOURCE_API_ADDRESS")
    source_api_key = environ.get("SOURCE_API_KEY")
    destination_api_address = environ.get("DESTINATION_API_ADDRESS")
    destination_api_key = environ.get("DESTINATION_API_KEY")
    username = environ.get("USERNAME")
    password = environ.get("PASSWORD")
    source_client = Algorithmia.client(api_key=source_api_key, api_address=source_api_address)
    destination_client = Algorithmia.client(api_key=destination_api_key, api_address=destination_api_address)
    create_workflow("image_parallel_pipelining", source_client, destination_client, username, password)
