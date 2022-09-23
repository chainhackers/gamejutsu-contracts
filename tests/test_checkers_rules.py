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
from brownie import interface
from eth_abi import encode_abi
from random import randbytes

from brownie.test import given, strategy as st
from hypothesis import strategies


@pytest.fixture(scope='module')
def rules(CheckersRules, dev):
    return interface.IGameJutsuRules(dev.deploy(CheckersRules))


@pytest.fixture(scope='session')
def game_id():
    return "0x" + randbytes(8).hex()


# struct State {
#     uint8[32] cells;
#     bool redMoves;
#     uint8 winner;
# }

# struct Move {
#     uint8 from;
#     uint8 to;
#     bool isJump;
#     bool passMoveToOpponent;
# }

STATE_TYPES = ["uint8[32]", "bool", "uint8"]
MOVE_TYPES = ["uint8", "uint8", "bool", "bool"]

W, R = 0, 1  # playerId


#                  1       2       3       4
#      1  01 │███│ o │███│ o │███│ o │███│ o │ 04
#      5  05 │ o │███│ o │███│ o │███│ o │███│ 08
#      9  09 │███│ o │███│ o │███│ o │███│ o │ 0C
#      13 0D │   │███│   │███│   │███│   │███│ 10
#      17 11 │███│   │███│   │███│   │███│   │ 14
#      21 15 │ x │███│ x │███│ x │███│ x │███│ 18
#      25 19 │███│ x │███│ x │███│ x │███│ x │ 1C
#      29 1D │ x │███│ x │███│ x │███│ x │███│ 20
#             1D      1E      1F      20

@given(
    empty_cells=st('uint8[32]', max_value=0),
    from_cell=st('uint8', min_value=1, max_value=32),
    to_cell=st('uint8', min_value=1, max_value=32),
    red_moves=st('bool')
)
def test_is_valid_move_empty_board(rules, game_id, empty_cells, from_cell, to_cell, red_moves):
    empty_board = [empty_cells, red_moves, 0]
    empty_board_encoded = encode_abi(STATE_TYPES, empty_board)
    nonce = 0
    game_state = [game_id, nonce, empty_board_encoded]

    move = [from_cell, to_cell, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, R, move_encoded)
    assert not rules.isValidMove(game_state, W, move_encoded)


@given(
    cells=(strategies.integers(min_value=1, max_value=32).map(lambda i: [2 if j == i - 1 else 0 for j in range(32)])),
    from_cell=st('uint8', min_value=1, max_value=32),
    to_cell=st('uint8', min_value=1, max_value=32),
    red_moves=st('bool')
)
def test_is_valid_move_single_white(rules, game_id, cells, from_cell, to_cell, red_moves):
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    nonce = 0
    game_state = [game_id, nonce, board_encoded]

    move = [from_cell, to_cell, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, W, move_encoded)

    is_valid = red_moves and cells[from_cell - 1] == 2 and from_cell // 4 > 0 and (
            (from_cell + 4) % 8 == 1 and to_cell == from_cell - 4 or
            (from_cell + 4) % 8 == 0 and to_cell == from_cell - 5 or
            (to_cell == from_cell - 4 or to_cell == from_cell - 5)
    )
    assert rules.isValidMove(game_state, R, move_encoded) == is_valid


@given(
    cells=(strategies.integers(min_value=1, max_value=32).map(lambda i: [2 if j == i - 1 else 0 for j in range(32)])),
    from_cell=st('uint8', min_value=1, max_value=32),
    to_cell=st('uint8', min_value=1, max_value=32),
    red_moves=st('bool')
)
def test_is_valid_move_single_white(rules, game_id, cells, from_cell, to_cell, red_moves):
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    nonce = 0
    game_state = [game_id, nonce, board_encoded]

    move = [from_cell, to_cell, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, R, move_encoded)

    is_valid = not red_moves and cells[from_cell - 1] == 2 and from_cell // 4 > 0 and (
            (from_cell + 4) % 8 == 1 and to_cell == from_cell - 4 or
            (from_cell + 4) % 8 == 0 and to_cell == from_cell - 5 or
            (to_cell == from_cell - 4 or to_cell == from_cell - 5)
    )
    assert rules.isValidMove(game_state, W, move_encoded) == is_valid
