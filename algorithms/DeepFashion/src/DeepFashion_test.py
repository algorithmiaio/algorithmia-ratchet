from . import DeepFashion

def test_DeepFashion():
    assert DeepFashion.apply("Jane") == "hello Jane"
