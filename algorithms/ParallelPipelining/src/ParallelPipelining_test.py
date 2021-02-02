from . import ParallelPipelining

def test_qa_parallel_pipelining():
    assert ParallelPipelining.apply("Jane") == "hello Jane"
