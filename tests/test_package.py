from dropfive import __version__


def test_package_version_is_available() -> None:
    assert __version__ == "0.4.0"
