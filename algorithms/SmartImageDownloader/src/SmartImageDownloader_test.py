from . import SmartImageDownloader

def test_SmartImageDownloader():
    assert SmartImageDownloader.apply("Jane") == "hello Jane"
