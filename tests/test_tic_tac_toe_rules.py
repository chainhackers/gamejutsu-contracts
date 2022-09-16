#   ________                           ____.       __
#  /  _____/_____    _____   ____     |    |__ ___/  |_  ________ __
# /   \  ___\__  \  /     \_/ __ \    |    |  |  \   __\/  ___/  |  \
# \    \_\  \/ __ \|  Y Y  \  ___//\__|    |  |  /|  |  \___ \|  |  /
#  \______  (____  /__|_|  /\___  >________|____/ |__| /____  >____/
#         \/     \/      \/     \/                          \/
# https://gamejutsu.app
# ETHOnline2022 submission by ChainHackers
__author__ = ["Gene A. Tsvigun" ]
__license__ = "MIT"

import pytest
from brownie import reverts, interface
from brownie.convert import to_bytes
from eth_abi import encode_abi, decode_abi
from random import randbytes


@pytest.fixture(scope='module')
def rules(TicTacToeRules, dev):
    return interface.IGameJutsuRules(dev.deploy(TicTacToeRules))


@pytest.fixture
def game_id():
    return "0x" + randbytes(8).hex()


STATE_TYPES = ["uint8[9]", "bool", "bool"]
X, O = 0, 1


def test_is_valid_move(rules, game_id):
    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    game_state = [game_id, nonce, empty_board]

    # every cross move is valid on an empty board, naught can't move first
    for i in range(9):
        move_to_cell_i = to_bytes(i)
        assert rules.isValidMove(game_state, X, move_to_cell_i) is True
        assert rules.isValidMove(game_state, O, move_to_cell_i) is False

    # no move is valid when any of the players has won
    cross_wins = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], True, False])
    game_state = [game_id, nonce, cross_wins]
    for i in range(9):
        move_to_cell_i = to_bytes(i)
        assert rules.isValidMove(game_state, X, move_to_cell_i) is False
        assert rules.isValidMove(game_state, O, move_to_cell_i) is False

    nought_wins = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, True])
    game_state = [game_id, nonce, nought_wins]
    for i in range(9):
        move_to_cell_i = to_bytes(i)
        assert rules.isValidMove(game_state, X, move_to_cell_i) is False
        assert rules.isValidMove(game_state, O, move_to_cell_i) is False

    # X1 → O5 → X9 → O3 → X7
    # X  _  O
    # _  O  _
    # X  _  X

    board = encode_abi(STATE_TYPES, [[1, 0, 2, 0, 2, 0, 1, 0, 1], False, False])
    nonce = 5  # O moves next
    game_state = [game_id, nonce, board]

    def is_valid(player_id: int, cell_id: int) -> bool:
        return rules.isValidMove(game_state, player_id, to_bytes(cell_id))

    assert is_valid(X, 0) is False
    assert is_valid(O, 0) is False

    assert is_valid(X, 1) is False
    assert is_valid(O, 1) is True

    assert is_valid(X, 2) is False
    assert is_valid(O, 3) is True

    assert is_valid(X, 4) is False
    assert is_valid(O, 4) is False

    assert is_valid(X, 5) is False
    assert is_valid(O, 5) is True

    assert is_valid(X, 6) is False
    assert is_valid(O, 6) is False

    assert is_valid(X, 7) is False
    assert is_valid(O, 7) is True

    assert is_valid(X, 8) is False
    assert is_valid(O, 8) is False


def test_transition(rules, game_id):
    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    game_state = [game_id, nonce, empty_board]
    for i in range(9):
        next_game_id, next_nonce, next_state = rules.transition(game_state, X, to_bytes(i))
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
        next_game_id, next_nonce, next_state = rules.transition(game_state, O, to_bytes(i))
        assert next_game_id == game_id
        assert next_nonce == 2
        next_board = decode_abi(STATE_TYPES, next_state)
        print(next_board)
        expected_next_board = [0] * 9
        expected_next_board[i] = 2
        expected_next_board = (tuple(expected_next_board), False, False)
        assert next_board == expected_next_board

    # ╭───┬───┬───╮
    # │ X │ X │ . │
    # ├───┼───┼───┤
    # │ 0 │ 0 │   │
    # ├───┼───┼───┤
    # │   │   │   │
    # ╰───┴───┴───╯

    x_almost_won_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 2, 0, 0, 0, 0], False, False])
    nonce = 4
    x_almost_won_state = [game_id, nonce, x_almost_won_board]
    x_winning_move_data = to_bytes(2)
    next_game_id, next_nonce, next_state = rules.transition(x_almost_won_state, X, x_winning_move_data)
    x_won_board = encode_abi(STATE_TYPES, [[1, 1, 1, 2, 2, 0, 0, 0, 0], True, False])
    assert next_state.hex() == x_won_board.hex()
