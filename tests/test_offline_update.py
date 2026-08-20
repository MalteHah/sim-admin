import pytest

from scripts.offline_update import version_tuple


def test_version_tuple_orders_numeric_versions() -> None:
    assert version_tuple("0.1.10") > version_tuple("0.1.9")
    assert version_tuple("1.0.0") > version_tuple("0.99.99")


@pytest.mark.parametrize("value", ["", "1.beta.0", "v1.0.0", "1.-1.0"])
def test_version_tuple_rejects_invalid_versions(value: str) -> None:
    with pytest.raises(ValueError):
        version_tuple(value)
