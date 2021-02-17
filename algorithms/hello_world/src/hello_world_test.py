from . import hello

def test_hello():
    assert hello.apply("Jane") == "hello Jane"
