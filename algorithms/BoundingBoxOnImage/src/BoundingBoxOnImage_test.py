from . import BoundingBoxOnImage

def test_BoundingBoxOnImage():
    assert BoundingBoxOnImage.apply("Jane") == "hello Jane"
