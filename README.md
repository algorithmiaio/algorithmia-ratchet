# Algorithmia TestBench
A system to export an algorithm (or algorithms) from one cluster to another, and run real-life benchmark tests to ensure cluster quality and stability.

## Requirements
As this workflow will download and then upload dependency files, if your workflow contains large dependencies it's recommended to execute this on a server (such as Deep Purple) via proxy.

This workflow does not contain any system dependencies, all that's required is a `pip install -r requirements.txt`

## How to Run
Before running, this script uses a number of `environment variables` to help it understand state and to preserve privacy,
here is a list of all of them and what they refer to:

* `SOURCE_API_KEY`
    * The API Key that has access to your source code (stored as a tar.gz ball), along with your model files
    * This API key must be management capable, able to read/write data, and has no restrictions on algorithm paths
    * We capture the username that owns this API key from the key itself
    * for security reasons does not contain a default, but our basic workflow requires a master key from the user `quality` on prod
* `SOURCE_CA_CERT`
    * This optional field is used to pass a certificate to our algorithm clients, in the event that the source cluster requires one.
    * No default, optional
* `DESTINATION_API_ADDRESS`
    * Similar to our source API address, but the destination; where are we writing our algorithms to?
    * Has no default
    * If unsure as to what your API address is, simply prefix your url with `api`, like `https://api.someuser.enthalpy.click`
* `DESTINATION_API_KEY`
    * Same as our source api key, but must be owned by the `algorithm_owner` user defined in your workflow file
    * Must be management capable, ability to read/write and create data collections, and have unrestricted algorithm access
* `DESTINATION_CA_CERT`
    * Same as the optional source ca cert, optional - but if the destination cluster requires one; can be provided here
* `DESTINATION_AEMS_MASTER`
    * The name of the master of which AEMS images are pulled from, can be either `test` or `prod` today
    * Defaults to `prod`
* `WORKFLOW_NAME`
    * The name of the workflow file you wish to execute. For a quick example check out [image_benchmark.json](workflows/image_benchmark.json)
    
After your environment variables are set, simply execute with:
`python3 export_and_test_my_algorithm.py`
If an exception is thrown at any stage, something went wrong - however if no failures were thrown that means everything is working perfectly, including our QA benchmark! Great!

## How to create a workflow
Please check out [image_benchmark.json](workflows/image_benchmark.json) as an example while we walk through the process.

A workflow is a json file consisting of 3 separate objects, `source_info`, `test_info`, and `algorithms`
* `source_info`
    * Contains information around where your algorithm code, and requisite model files are; defaults to pointing to the production cluster.
    * Contains the following fields:
        * `cluster_address` 
            * The api address where our source cluster is located, similar to `DESTINATION_API_ADDRESS` but as we  have a single source of truth for our workflow; this is baked in
            * If using a non-standard source address, you may need to provide a ca cert to the `SOURCE_CA_CERT`  environment variable
* `test_info`
    * This optional field provides information used to perform a QA test or benchmark against your workflow.
    * Can contain any number of tests, however expects a single algorithm in your workflow to execute as an `entrypoint`
    Contains the following fields:
        * `entrypoint`
            * The name of an algorithm that is a part of this workflow, that will act as our entrypoint for testing purposes
            * If your workflow contains more than one entrypoint, consider breaking your 1 workflow into multiple
            * name must match exactly the `name` of one of your algorithms.
        * `tests`
            * contains a list of `test`s that will be executed consequtively. Each test has the following:
                * `name`
                    * The name of your test, only used for diagnostics
                * `payload`
                    * The json encoded payload that will be provided to your `entrypoint` algorithm
                * `timeout`
                    * An optional field that defines the timeout for this algorithm request
* `algorithms`
    * A list of `algorithm` objects that we plan to export into our destination cluster, and test
    * Algorithms defined here will get exported and tested `in order`, so if order matters take that into consideration
    * An algorithm contains the following fields:
        * `name`
            * The name of your algorithm, _must be unique_
            * Case sensitive, for best results keep it the same as the original algorithm
        * `code_path`
            * The data API path containing your tar.gz ball that has your algorithm
            * For simplicities sake, this tar.gz should contain both `requirements.txt` and anything contained in `src` for most python examples
            * The `.my` value can be used instead of a username, to keep everything generic
        * `language`
            * This contains a shorthand for a subset of our supported algorithm languages
            * Currently the only supported development language is python, however here are the following variants:
                * `python2`
                * `python3`
                * `pytorch`
                * `tensorflow-2.3`
                * `tensorflow-1.14`
            * more will be added once the AEMS api endpoints stabilize
        * `data_files`
            * A list of data api file paths that contain either model files, or other dependent files (such as those for testing)
            * As the same with `code_path`, it's recommended to replace your username with `.my` to keep your workflow generic and easy to change
        * `test_payload`
            * A json encoded object that will be passed to this algorithm as input to verify that everything is working as expected
            * If the algorithm fails to process  your test payload, the process will return an exception, and the error message that was returned
       
            
## How to create a workflow
Creating a new workflow has 2 steps:
* Create a workflow.json file in `/workflows`
* Creating an Algorithm template (or templates) in the `/algorithms` directory
Lets explore each of step in detail.

### Workflow Creation
First create a workflow with a useful filename, you'll use this to refer to your workflow operations.

`touch workflows/hello_world.json`

**some important things to note:**
* Algorithm order matters!
    * Make sure that you define downstream algorithms first, and walk back towards your "orchestrator" if you have one.
    * For example, define `smartImageDownloader` first, before defining your Image Classifier that uses it.
* All algorithm data is to be stored in the Data API
    * It can be any collection, but the reason for this is to ensure that we can export data into closed off networks.
    
Lets look at a basic template and walk through the different components.

```json
{
  "source_info": {
    "cluster_address": "https://api.algorithmia.com"
  },
  "test_info": {
    "entrypoint": "hello_world",
    "tests": [
      {
        "name": "basic test",
        "payload": "Algorithmia",
        "timeout": 10
      }
    ]
  },
  "algorithms": [
    {
      "name": "hello_world",
      "data_files": [],
      "environment": "python3",
      "test_payload": "Algorithmia"
    }
  ]
}
```

#### source_info
For the moment, this contains only the `cluster_address` algorithmia cluster api addresswhere data files are located, in the future this may be optional.
Unless you're storing data files on a different cluster than production, please leave this as is.
#### test_info
This is where you define the benchmark tests for your algorithm to pass
* `"entrypoint"` - defines which algorithm should be "called" during all tests, only one algorithm can be an entrypoint per workflow. Name must match up exactly with the name you defined in `algorithms`.
* `"tests` - a list of tests which get run in order, each test consists of:
    * `"name"` - the name of the test (for reporting purposes)
    * `"payload"` - the json encoded payload to provide to your entrypoint algorithm.
        * If you're interacting with data files, it's recommended to define them in your algorithm's `data_files` object, and to refer to them with the following schema:
            * `"data://.my/<algo>/..."`, replacing ... with the name of your datafile.
        * If you're algorithm writes to a particular location, to ensure that the collection exists it's recommended to use the following output schema:
            * `"data://.algo/temp/..."`, replacing ... with the name of your datafile.
    * `"timeout"` - the amount of seconds we should wait for your algorithm before determining that the test failed, maximum value is `3000`.
#### algorithms

This is where you define the algorithms that your workflow will need to get executed, this includes any dependent algorithms (like smart image downloader).
Please ensure that you define your algorithms in order of dependency requirements. If one of your algorithms depends on another, list the downstream one first.
* `"algorithms"` - a list of algorithm objects that this workflow will use
    * `"name"` - the name of your algorithm, must match the name of the directory defined in `/algorithms` as well as the name of the algorithm files associated.
        * for example, if your algorithm is "hello_world", the directory path containing your algorithm code must be `/algorithms/hello_world` which in the src directory contains `hello_world.py` and `hello_world_test.py`
    * `"data_files"` - this list object contains all model files and other objects required at runtime for your algorithm, as a data API URI prefixed with '.my'
        * for the moment, these files should be stored in a data collection owned by user `quality` on production
        * data file collection paths are not used, so they can be anything
        * If your algorithm uses an image or data file as input for testing, those objects should be stored using this system as well
    * `"language"` - the environments `language` enum that should be used to create this algorithm.
        * the concept of "language" is not quite right, as we're potentially using the same language but with different dependencies
        * check to make sure that your required dependencies exist as a language already defined in `/src/images.py`
        * if running the benchmark on an AEMS cluster that does not access to the PROD or TEST AEMS masters, you'll need to interact with the `environments/current` webapi endpoint to populate your environments list
        * if you hit any kind of system 500 error during the build stage, make sure that your language is configured and that the language `environment id` is valid.
    * `"test_payload"` - the json encodable (string, list, dict, etc) algorithm payload you wish to send to your algorithm to verify runtime functionality
        * not used during the benchmark process, you may use different payloads during validation and benchmarking
        * If you're interacting with data files, it's recommended to define them in your algorithm's `data_files` object, and to refer to them with the following schema:
            * `"data://.my/<algo>/..."`, replacing ... with the name of your datafile.
If you have any questions as to the schema or best practices in regards to creating a workflow file, please ping zeryx or the algo-team on slack and we should be able to help :)
              
### Algorithm Template Creation
Now that we have the workflow configured, lets take a look at the `/algorithms` directory, and what it takes to setup a new algorithm template.

Currently our templating service supports the following languages:
* [x] Python
* [ ] Scala
* [ ] Java
* [ ] R
* [ ] Javascript
* [ ] Ruby
* [ ] C#
* [ ] Rust
#### For Python
* the name of each directory **is equal to** the name of the algorithm, this is used for lookups and is important.
  * This is also case sensitve, as algorithm names are also case sensitive.
  * eg: "/algorithms/BoundingBoxOnImage" contains the `BoundingBoxOnImage` algorithm
* inside an algorithm directory, we have a `/src` directory and a `requirements.txt` file
    * The `/src` directory should contain all algorithm files present in the original algorithms `src` directory.
    * However, for any references to an algorithm or data file, should be replaced with the following:
        * for data files:
            * original - `"data://myuser/mycollection/somedata_file"`
            * template friendly version - `"data://.my/<algo>/somedata_file"`
        * for algorithms:
            * original - `"algo://someuser/somealgo/0.2.4"`
            * template friendly version - `"algo://.my/somealgo/latestPrivate"`
* typically, no changes are required for `requirements.txt` files, just copy them from the original algorithm.
* if you end up using a data location on disk that contains the algorithm name, consider renaming it as there may be a conflict with our algorithm creation service.



