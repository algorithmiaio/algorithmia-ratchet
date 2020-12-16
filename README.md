# Export and Test My Algorithm
A system to export an algorithm (or algorithms) from one cluster to another, and run a QC test against them to verify stability.

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
* `WORKFLOW_NAME`
    * The name of the workflow file you wish to execute. For a quick example check out [image_parallel_processing.json](workflows/image_parallel_pipelining.json)
    
After your environment variables are set, simply execute with:
`python3 export_and_test_my_algorithm.py`
If an exception is thrown at any stage, something went wrong - however if no failures were thrown that means everything is working perfectly, including our QA benchmark! Great!

## How to create a workflow
Please check out [image_parallel_processing.json](workflows/image_parallel_pipelining.json) as an example while we walk through the process.

A workflow is a json file consisting of 3 separate objects, `source_info`, `test_info`, and `algorithms`
* `source_info`
    * Contains information around where your algorithm code, and requisite model files are
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
       
            