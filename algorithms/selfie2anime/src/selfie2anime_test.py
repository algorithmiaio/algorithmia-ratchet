from . import selfie2anime

def test_selfie2anime():
    assert selfie2anime.apply("Jane") == "hello Jane"
