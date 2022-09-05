import pytest
from brownie import reverts, interface, config, project, accounts, convert
from eth_abi import encode_abi


@pytest.fixture(scope='module')
def rules(TicTacToeRules, dev):
    return dev.deploy(TicTacToeRules)


STATE_TYPES = ["uint8[9]", "bool", "bool"]


def test_is_valid_move(rules):
    empty = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    for i in range(9):
        assert rules.isValidMove(empty, convert.to_bytes(i), 1) is True

    cross_wins = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], True, False])
    for i in range(9):
        assert rules.isValidMove(cross_wins, convert.to_bytes(i), 1) is False

    cross_wins = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, True])
    for i in range(9):
        assert rules.isValidMove(cross_wins, convert.to_bytes(i), 1) is False

    # X1 → O5 → X9 → O3 → X7
    # X  _  O
    # _  O  _
    # X  _  X
    state = encode_abi(STATE_TYPES, [[1, 0, 2, 0, 2, 0, 1, 0, 1], False, False])
    assert rules.isValidMove(state, convert.to_bytes(0), 1) is False
    assert rules.isValidMove(state, convert.to_bytes(1), 1) is True
    assert rules.isValidMove(state, convert.to_bytes(2), 1) is False
    assert rules.isValidMove(state, convert.to_bytes(3), 1) is True
    assert rules.isValidMove(state, convert.to_bytes(4), 1) is False
    assert rules.isValidMove(state, convert.to_bytes(5), 1) is True
    assert rules.isValidMove(state, convert.to_bytes(6), 1) is False
    assert rules.isValidMove(state, convert.to_bytes(7), 1) is True
    assert rules.isValidMove(state, convert.to_bytes(8), 1) is False
