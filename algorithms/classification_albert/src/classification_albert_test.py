from . import classification_albert

def test_classification_albert():
    assert classification_albert.apply("Jane") == "hello Jane"
