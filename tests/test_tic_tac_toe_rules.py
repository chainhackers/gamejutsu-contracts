import pytest
from brownie import reverts, interface, config, project, accounts, convert
from eth_abi import encode_abi, decode_abi
from random import randbytes


@pytest.fixture(scope='module')
def rules(TicTacToeRules, dev):
    return dev.deploy(TicTacToeRules)


@pytest.fixture
def game_id():
    return "0x" + randbytes(8).hex()


STATE_TYPES = ["uint8[9]", "bool", "bool"]


def test_is_valid_move(rules, game_id):
    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    game_state = [game_id, nonce, empty_board]

    for i in range(9):
        assert rules.isValidMove(game_state, convert.to_bytes(i)) is True

    cross_wins = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], True, False])
    game_state = [game_id, nonce, cross_wins]
    for i in range(9):
        assert rules.isValidMove(game_state, convert.to_bytes(i)) is False

    nought_wins = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, True])
    game_state = [game_id, nonce, nought_wins]
    for i in range(9):
        assert rules.isValidMove(game_state, convert.to_bytes(i)) is False

    # X1 → O5 → X9 → O3 → X7
    # X  _  O
    # _  O  _
    # X  _  X

    board = encode_abi(STATE_TYPES, [[1, 0, 2, 0, 2, 0, 1, 0, 1], False, False])
    nonce = 5
    game_state = [game_id, nonce, board]
    assert rules.isValidMove(game_state, convert.to_bytes(0)) is False
    assert rules.isValidMove(game_state, convert.to_bytes(1)) is True
    assert rules.isValidMove(game_state, convert.to_bytes(2)) is False
    assert rules.isValidMove(game_state, convert.to_bytes(3)) is True
    assert rules.isValidMove(game_state, convert.to_bytes(4)) is False
    assert rules.isValidMove(game_state, convert.to_bytes(5)) is True
    assert rules.isValidMove(game_state, convert.to_bytes(6)) is False
    assert rules.isValidMove(game_state, convert.to_bytes(7)) is True
    assert rules.isValidMove(game_state, convert.to_bytes(8)) is False


def test_transition(rules, game_id):
    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    game_state = [game_id, nonce, empty_board]
    for i in range(9):
        next_game_id, next_nonce, next_state = rules.transition(game_state, convert.to_bytes(i))
        assert next_game_id == game_id
        assert next_nonce == 1
        next_board = decode_abi(STATE_TYPES, next_state)
        print(next_board)
        expected_next_board = [0] * 9
        expected_next_board[i] = 1
        expected_next_board = (tuple(expected_next_board), False, False)
        assert next_board == expected_next_board

    nonce = 1
    game_state = [game_id, nonce, empty_board]
    for i in range(9):
        next_game_id, next_nonce, next_state = rules.transition(game_state, convert.to_bytes(i))
        assert next_game_id == game_id
        assert next_nonce == 2
        next_board = decode_abi(STATE_TYPES, next_state)
        print(next_board)
        expected_next_board = [0] * 9
        expected_next_board[i] = 2
        expected_next_board = (tuple(expected_next_board), False, False)
        assert next_board == expected_next_board
