import pytest
from brownie import reverts, interface, config, project, accounts, convert
from eth_abi import encode_abi, decode_abi


@pytest.fixture(scope='module')
def rules(TicTacToeRules, dev):
    return dev.deploy(TicTacToeRules)


STATE_TYPES = ["uint8[9]", "bool", "bool"]


def test_is_valid_move(rules):
    empty = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    for i in range(9):
        assert rules.isValidMove([empty, 0], convert.to_bytes(i)) is True

    cross_wins = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], True, False])
    for i in range(9):
        assert rules.isValidMove([cross_wins, 1], convert.to_bytes(i)) is False

    cross_wins = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, True])
    for i in range(9):
        assert rules.isValidMove([cross_wins, 2], convert.to_bytes(i)) is False

    # X1 → O5 → X9 → O3 → X7
    # X  _  O
    # _  O  _
    # X  _  X
    state = [encode_abi(STATE_TYPES, [[1, 0, 2, 0, 2, 0, 1, 0, 1], False, False]), 1]
    assert rules.isValidMove(state, convert.to_bytes(0)) is False
    assert rules.isValidMove(state, convert.to_bytes(1)) is True
    assert rules.isValidMove(state, convert.to_bytes(2)) is False
    assert rules.isValidMove(state, convert.to_bytes(3)) is True
    assert rules.isValidMove(state, convert.to_bytes(4)) is False
    assert rules.isValidMove(state, convert.to_bytes(5)) is True
    assert rules.isValidMove(state, convert.to_bytes(6)) is False
    assert rules.isValidMove(state, convert.to_bytes(7)) is True
    assert rules.isValidMove(state, convert.to_bytes(8)) is False


def test_transition(rules):
    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    state = [empty_board, 0]
    for i in range(9):
        next_state = rules.transition(state, convert.to_bytes(i))
        assert next_state[1] == 1
        next_board = decode_abi(STATE_TYPES, next_state[0])
        print(next_board)
        expected_next_board = [0] * 9
        expected_next_board[i] = 1
        expected_next_board = (tuple(expected_next_board), False, False)
        assert next_board == expected_next_board

    state = [empty_board, 1]
    for i in range(9):
        next_state = rules.transition(state, convert.to_bytes(i))
        assert next_state[1] == 2
        next_board = decode_abi(STATE_TYPES, next_state[0])
        print(next_board)
        expected_next_board = [0] * 9
        expected_next_board[i] = 2
        expected_next_board = (tuple(expected_next_board), False, False)
        assert next_board == expected_next_board
