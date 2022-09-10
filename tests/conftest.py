import pytest


@pytest.fixture(scope="module")
def dev(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def player_a(accounts):
    return accounts[1]


@pytest.fixture(scope="module")
def player_b(accounts):
    return accounts[2]
