import pytest

from eth_account import Account
from brownie.network.gas.strategies import GasNowScalingStrategy

@pytest.fixture(scope="module")
def dev(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def create_funded_eth_account(dev):
    def create():
        acct = Account.create()
        dev.transfer(acct.address, "1 ether")
        dev.transfer(acct.address, "1 ether")
        return acct

    return create
