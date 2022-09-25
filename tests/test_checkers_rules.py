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

from typing import List, Tuple
import pytest
from brownie import interface
from eth_abi import encode_abi, decode_abi
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
#      1  01 │███│ o │███│ o │███│ o │███│ o │ 04 4
#      5  05 │ o │███│ o │███│ o │███│ o │███│ 08 8
#      9  09 │███│ o │███│ o │███│ o │███│ o │ 0C 12
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
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_move_empty_board(rules, game_id, empty_cells, from_cell, to_cell, red_moves, nonce):
    empty_board = [empty_cells, red_moves, 0]
    empty_board_encoded = encode_abi(STATE_TYPES, empty_board)
    game_state = [game_id, nonce, empty_board_encoded]

    move = [from_cell, to_cell, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, R, move_encoded)
    assert not rules.isValidMove(game_state, W, move_encoded)


@given(
    cells=(strategies.integers(min_value=1, max_value=32).map(lambda i: [1 if j == i - 1 else 0 for j in range(32)])),
    from_cell=st('uint8', min_value=1, max_value=32),
    to_cell=st('uint8', min_value=1, max_value=32),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_move_single_white(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [from_cell, to_cell, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, W, move_encoded)

    is_valid = not red_moves and cells[from_cell - 1] == 2 and from_cell // 4 < 7 and (
            (from_cell + 4) % 8 == 1 and to_cell == from_cell - 4 or
            (from_cell + 4) % 8 == 0 and to_cell == from_cell - 5 or
            (to_cell == from_cell + 4 or to_cell == from_cell + 5)
    )
    assert rules.isValidMove(game_state, R, move_encoded) == is_valid


@given(
    cells=(strategies.integers(min_value=1, max_value=32).map(lambda i: [2 if j == i - 1 else 0 for j in range(32)])),
    from_cell=st('uint8', min_value=1, max_value=32),
    to_cell=st('uint8', min_value=1, max_value=32),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_move_single_red(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [from_cell, to_cell, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, W, move_encoded)

    is_valid = red_moves and occupied_by_red(from_cell, cells) and unoccupied(to_cell, cells) and to_cell in [
        up_left(from_cell),
        up_right(from_cell)]

    assert rules.isValidMove(game_state, R, move_encoded) == is_valid


@given(
    cells=(strategies.sets(strategies.integers(min_value=1, max_value=32), min_size=1, max_size=32).map(
        lambda s: [1 if j + 1 in s else 0 for j in range(32)])),
    from_cell=st('uint8', min_value=1, max_value=32),
    to_cell=st('uint8', min_value=1, max_value=32),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_move_multiple_white_checkers(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [from_cell, to_cell, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, R, move_encoded)

    is_valid = not red_moves and occupied_by_white(from_cell, cells) and unoccupied(to_cell,
                                                                                    cells) and from_cell // 4 < 7 and (
                       to_cell in [down_left(from_cell), down_right(from_cell)]
               )
    assert rules.isValidMove(game_state, W, move_encoded) == is_valid


@given(
    cells=(strategies.sets(strategies.integers(min_value=1, max_value=32), min_size=1, max_size=32).map(
        lambda s: [2 if j + 1 in s else 0 for j in range(32)])),
    from_cell=st('uint8', min_value=1, max_value=32),
    to_cell=st('uint8', min_value=1, max_value=32),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_move_multiple_red_checkers(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [from_cell, to_cell, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, W, move_encoded)

    is_valid = red_moves and occupied_by_red(from_cell, cells) and unoccupied(to_cell, cells) and to_cell in [
        up_left(from_cell),
        up_right(from_cell)]

    assert rules.isValidMove(game_state, R, move_encoded) == is_valid


#                  1       2       3       4
#      1  01 │███│   │███│   │███│   │███│   │ 04 04
#      5  05 │   │███│ . │███│ 7 │███│ . │███│ 08 08
#      9  09 │███│   │███│ o │███│ o │███│   │ 0C 12
#      13 0D │   │███│   │███│ x │███│   │███│ 10 16
#      17 11 │███│   │███│ o │███│ o │███│   │ 14 20
#      21 15 │   │███│ . │███│   │███│ . │███│ 18 24
#      25 19 │███│   │███│   │███│   │███│   │ 1C 28
#      29 1D │   │███│   │███│   │███│   │███│ 20 32
#             1D      1E      1F      20

@given(
    cells=(strategies.tuples(
        strategies.integers(min_value=1, max_value=32),
        strategies.booleans(),
        strategies.booleans(),
        strategies.booleans(),
    ).map(
        lambda t: [
            1 if j + 1 == t[0] else
            2 if j + 1 == t[0] - 9 and t[1] or
                 j + 1 == t[0] - 7 and t[2] or
                 j + 1 == t[0] + 7 and t[3] or
                 j + 1 == t[0] + 9 else
            0 for j in range(32)])),
    from_cell=st('uint8', min_value=1, max_value=32),
    to_cell=st('uint8', min_value=1, max_value=32),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_jump_single_white(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    player_who_cannot_move = R
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [from_cell, to_cell, True, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)

    is_valid = not red_moves and occupied_by_white(from_cell, cells) and unoccupied(to_cell, cells) and (
            to_cell == jump_down_left(from_cell) and occupied_by_red(down_left(from_cell), cells) or
            to_cell == jump_down_right(from_cell) and occupied_by_red(down_right(from_cell), cells)
    )
    assert rules.isValidMove(game_state, W, move_encoded) == is_valid


#                  1       2       3       4
#      1  01 │███│   │███│   │███│   │███│   │ 04 4
#      5  05 │   │███│ . │███│   │███│ . │███│ 08 8
#      9  09 │███│   │███│ x │███│ x │███│   │ 0C 12
#      13 0D │   │███│   │███│ o │███│   │███│ 10 16
#      17 11 │███│   │███│ x │███│ x │███│   │ 14 20
#      21 15 │   │███│ . │███│   │███│ . │███│ 18 24
#      25 19 │███│   │███│   │███│   │███│   │ 1C 28
#      29 1D │   │███│   │███│   │███│   │███│ 20 32
#             1D      1E      1F      20

@given(
    cells=(strategies.tuples(
        strategies.integers(min_value=1, max_value=32),
        strategies.booleans(),
        strategies.booleans(),
        strategies.booleans(),
    ).map(
        lambda t: [
            1 if j + 1 == t[0] else
            2 if j + 1 == t[0] - 9 and t[1] or
                 j + 1 == t[0] - 7 and t[2] or
                 j + 1 == t[0] + 7 and t[3] or
                 j + 1 == t[0] + 9 else
            0 for j in range(32)])),
    from_cell=st('uint8', min_value=1, max_value=32),
    to_cell=st('uint8', min_value=1, max_value=32),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_jump_single_red(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    player_who_cannot_move = W
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [from_cell, to_cell, True, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)

    is_valid = not red_moves and occupied_by_red(from_cell, cells) and unoccupied(to_cell, cells) and (
            to_cell == jump_down_left(from_cell) and occupied_by_white(down_left(from_cell), cells) or
            to_cell == jump_down_right(from_cell) and occupied_by_white(down_right(from_cell), cells)
    )
    assert rules.isValidMove(game_state, R, move_encoded) == is_valid


def test_transition_single_move(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │   │███│   │███│   │███│   │███│ 08 8
    #      9  09 │███│   │███│10 │███│11 │███│   │ 0C 12
    #      13 0D │   │███│   │███│ * │███│   │███│ 10 16
    #      17 11 │███│   │███│18 │███│19 │███│   │ 14 20
    #      21 15 │   │███│   │███│   │███│   │███│ 18 24
    #      25 19 │███│   │███│   │███│   │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0] * 32
    cells[15 - 1] = 2

    red_moves = True
    nonce = 0
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [15, 10, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move_encoded)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[10 - 1] == 2
    assert not next_move_is_red
    assert next_winner == 0

    nonce = 5
    cells[15 - 1] = 1
    red_moves = False
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [15, 11, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move_encoded)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[11 - 1] == 1
    assert next_move_is_red
    assert next_winner == 0

    nonce = 10
    cells[15 - 1] = 2
    red_moves = True
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [15, 19, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move_encoded)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[19 - 1] == 2
    assert not next_move_is_red
    assert next_winner == 0

    move = [15, 18, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move_encoded)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[18 - 1] == 2
    assert not next_move_is_red
    assert next_winner == 0


def test_transition_single_red_jump(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │   │███│ 6 │███│   │███│ 8 │███│ 08 8
    #      9  09 │███│   │███│ o │███│ o │███│   │ 0C 12
    #      13 0D │   │███│   │███│ x │███│   │███│ 10 16
    #      17 11 │███│   │███│   │███│   │███│   │ 14 20
    #      21 15 │   │███│   │███│   │███│   │███│ 18 24
    #      25 19 │███│   │███│   │███│   │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0] * 32
    cells[5] = 0

    cells[15 - 1] = 2
    cells[10 - 1] = 1
    cells[11 - 1] = 1

    nonce = 0
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=15,
                       to=6,
                       is_jump=True,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[10 - 1] == 0
    assert next_cells[11 - 1] == 1
    assert next_cells[6 - 1] == 2
    assert not next_move_is_red
    assert next_winner == 0

    move = encode_move(fr=15,
                       to=8,
                       is_jump=True,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[8 - 1] == 2
    assert next_cells[10 - 1] == 1
    assert next_cells[11 - 1] == 0
    assert not next_move_is_red
    assert next_winner == 0


def test_transition_single_white_jump(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │   │███│ 6 │███│   │███│ 8 │███│ 08 8
    #      9  09 │███│   │███│ x │███│ x │███│   │ 0C 12
    #      13 0D │   │███│   │███│ o │███│   │███│ 10 16
    #      17 11 │███│   │███│   │███│   │███│   │ 14 20
    #      21 15 │   │███│   │███│   │███│   │███│ 18 24
    #      25 19 │███│   │███│   │███│   │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0] * 32

    cells[15 - 1] = 1
    cells[10 - 1] = 2
    cells[11 - 1] = 2

    nonce = 0
    board = encode_board(cells=cells, red_moves=False)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=15,
                       to=6,
                       is_jump=True,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[10 - 1] == 0
    assert next_cells[11 - 1] == 2
    assert next_cells[6 - 1] == 1
    assert next_move_is_red
    assert next_winner == 0

    move = encode_move(fr=15,
                       to=8,
                       is_jump=True,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[8 - 1] == 1
    assert next_cells[10 - 1] == 2
    assert next_cells[11 - 1] == 0
    assert next_move_is_red
    assert next_winner == 0


def test_transition_double_red_jump(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │   │███│   │███│   │███│   │███│ 08 8
    #      9  09 │███│   │███│   │███│11 │███│   │ 0C 12
    #      13 0D │13 │███│   │███│ o │███│   │███│ 10 16
    #      17 11 │███│17 │███│18 │███│   │███│   │ 14 20
    #      21 15 │   │███│22 │███│ o │███│   │███│ 18 24
    #      25 19 │███│   │███│   │███│ x │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0] * 32

    cells[15 - 1] = 1
    cells[23 - 1] = 1
    cells[27 - 1] = 2

    nonce = 0
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=27,
                       to=18,
                       is_jump=True,
                       pass_move=False)
    assert rules.isValidMove(game_state, R, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[18 - 1] == 2
    assert next_cells[23 - 1] == 0
    assert next_cells[27 - 1] == 0
    assert next_move_is_red
    assert next_winner == 0

    board = encode_board(cells=next_cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=18,
                       to=11,
                       is_jump=True,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[18 - 1] == 0
    assert next_cells[11 - 1] == 2
    assert not next_move_is_red
    assert next_winner == 0


def mov(fr: int, to: int, is_jump: bool, pass_move: bool) -> Tuple[int, int, bool, bool]:
    return fr, to, is_jump, pass_move


def encode_move(fr: int, to: int, is_jump: bool, pass_move: bool) -> bytes:
    move = mov(fr, to, is_jump, pass_move)
    return encode_abi(MOVE_TYPES, move)


def encode_board(cells: List[int], red_moves: bool, winner: int = 0) -> bytes:
    board = [cells, red_moves, winner]
    return encode_abi(STATE_TYPES, board)


def up_left(cell: int) -> int:
    d = 1 if cell % 8 > 4 else 0
    return cell - 4 - d if cell % 8 != 5 and cell > 5 else 0


def jump_up_left(cell: int) -> int:
    return cell - 9 if cell % 8 not in [1, 5] and cell > 9 else 0


def up_right(cell: int) -> int:
    d = 1 if cell % 8 > 4 else 0
    return cell - 3 - d if cell % 8 != 4 and cell > 4 else 0


def jump_up_right(cell: int) -> int:
    return cell - 7 if cell % 8 not in [0, 4] and cell > 8 else 0


def down_left(cell: int) -> int:
    d = 1 if cell % 8 > 4 else 0
    return cell + 4 - d if cell % 8 != 5 and cell < 29 else 0


def jump_down_left(cell: int) -> int:
    return cell + 7 if cell % 8 not in [1, 5] and cell < 20 else 0


def down_right(cell: int) -> int:
    d = 1 if cell % 8 > 4 else 0
    return cell + 5 - d if cell % 8 != 4 and cell < 28 else 0


def jump_down_right(cell: int) -> int:
    return cell + 9 if cell % 8 not in [0, 4] and cell < 21 else 0


def occupied_by_red(cell: int, cells: List[int]) -> bool:
    return cells[cell - 1] == 2


def occupied_by_white(cell: int, cells: List[int]) -> bool:
    return cells[cell - 1] == 1


def unoccupied(cell: int, cells: List[int]) -> bool:
    return cells[cell - 1] == 0
