#   ________                           ____.       __
#  /  _____/_____    _____   ____     |    |__ ___/  |_  ________ __
# /   \  ___\__  \  /     \_/ __ \    |    |  |  \   __\/  ___/  |  \
# \    \_\  \/ __ \|  Y Y  \  ___//\__|    |  |  /|  |  \___ \|  |  /
#  \______  (____  /__|_|  /\___  >________|____/ |__| /____  >____/
#         \/     \/      \/     \/                          \/
# https://gamejutsu.app
# ETHOnline2022 submission by ChainHackers
__author__ = ["Gene A. Tsvigun"]
__license__ = "MIT"

import pytest

from eth_account import Account


@pytest.fixture(scope="module")
def dev(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def create_eth_account():
    def create():
        return Account.create()

    return create


@pytest.fixture(scope="module")
def create_funded_eth_account(dev):
    def create():
        acct = Account.create()
        dev.transfer(acct.address, "1 ether")
        dev.transfer(acct.address, "1 ether")
        return acct

    return create
