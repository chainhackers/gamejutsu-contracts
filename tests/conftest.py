import pytest


@pytest.fixture(scope="module")
def dev(accounts):
    return accounts[0]
