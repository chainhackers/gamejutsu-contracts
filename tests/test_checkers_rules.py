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

from typing import List, Tuple, Generator
import pytest
from brownie import interface
from eth_abi import encode_abi, decode_abi
from random import randbytes

from brownie.test import given, strategy as st
from hypothesis import strategies


@pytest.fixture(scope='module')
def rules(CheckersRules, dev):
    # return interface.IGameJutsuRules(dev.deploy(CheckersRules))
    return dev.deploy(CheckersRules)


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
#      13 0D │   │███│   │███│   │███│   │███│ 10 16
#      17 11 │███│   │███│   │███│   │███│   │ 14 21
#      21 15 │ x │███│ x │███│ x │███│ x │███│ 18 25
#      25 19 │███│ x │███│ x │███│ x │███│ x │ 1C 28
#      29 1D │ x │███│ x │███│ x │███│ x │███│ 20 323
#             1D      1E      1F      20

@given(
    empty_cells=st('uint8[32]', max_value=0),
    from_cell=st('uint8', min_value=1, max_value=32),
    to_cell=st('uint8', min_value=1, max_value=32),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=10)
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

    move = encode_move(fr=from_cell, to=to_cell, is_jump=False, pass_move=True)
    assert not rules.isValidMove(game_state, W, move)

    is_valid = red_moves and occupied_by_red(from_cell, cells) and unoccupied(to_cell, cells) and to_cell in [
        up_left(from_cell),
        up_right(from_cell)]

    assert rules.isValidMove(game_state, R, move) == is_valid


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

    move = encode_move(fr=from_cell, to=to_cell, is_jump=False, pass_move=True)
    assert not rules.isValidMove(game_state, R, move)

    is_valid = not red_moves and occupied_by_white(from_cell, cells) and unoccupied(to_cell,
                                                                                    cells) and to_cell in [
                   down_left(from_cell), down_right(from_cell)]

    assert rules.isValidMove(game_state, W, move) == is_valid


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

    move = encode_move(fr=from_cell, to=to_cell, is_jump=False, pass_move=True)
    assert not rules.isValidMove(game_state, W, move)

    is_valid = red_moves and occupied_by_red(from_cell, cells) and unoccupied(to_cell, cells) and to_cell in [
        up_left(from_cell),
        up_right(from_cell)]

    assert rules.isValidMove(game_state, R, move) == is_valid


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
#                  1       2       3       4
#      1  01 │███│   │███│   │███│   │███│   │ 04 4
#          5  05 │   │███│ . │███│   │███│ . │███│ 08 8
#      9  09 │███│   │███│ x │███│ x │███│   │ 0C 12
#          13 0D │   │███│   │███│ o │███│   │███│ 10 16
#      17 11 │███│   │███│ x │███│ x │███│   │ 14 20
#          21 15 │   │███│ . │███│   │███│ . │███│ 18 24
#      25 19 │███│   │███│   │███│   │███│   │ 1C 28
#          29 1D │   │███│   │███│   │███│   │███│ 20 32
#             1D      1E      1F      20

# @given(
#     cells=(strategies.tuples(
#         strategies.integers(min_value=1, max_value=32),
#         strategies.booleans(),
#         strategies.booleans(),
#         strategies.booleans(),
#     ).map(
#         lambda t: [  # t is (a random index from 1 to 32, and 3 random booleans)
#             2 if j + 1 == t[0] else
#             2 if j + 1 == t[0] - 9 and t[1] or
#                  j + 1 == t[0] - 7 and t[2] or
#                  j + 1 == t[0] + 7 and t[3] or
#                  j + 1 == t[0] + 9 else
#             0 for j in range(32)])),
#     from_cell=st('uint8', min_value=1, max_value=32),
#     to_cell=st('uint8', min_value=1, max_value=32),
#     red_moves=st('bool'),
#     nonce=st('uint256', max_value=100)
# )
# def test_is_valid_jump_single_red(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
#     player_who_cannot_move = W
#     board = [cells, red_moves, 0]
#     board_encoded = encode_abi(STATE_TYPES, board)
#     game_state = [game_id, nonce, board_encoded]
#
#     move = [from_cell, to_cell, True, False]
#     move_encoded = encode_abi(MOVE_TYPES, move)
#     assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)
#
#     is_valid = not red_moves and occupied_by_red(from_cell, cells) and unoccupied(to_cell, cells) and (
#             to_cell == jump_down_left(from_cell) and occupied_by_white(down_left(from_cell), cells) or
#             to_cell == jump_down_right(from_cell) and occupied_by_white(down_right(from_cell), cells)
#     )
#     assert rules.isValidMove(game_state, R, move_encoded) == is_valid
#

def possible_moves(position: int, red: bool, king: bool) -> Generator[int, None, None]:
    row_num = position // 4
    column_num = position % 4

    rows = [row_num - 1, -1] if red else [row_num + 1, -1]
    if king:
        rows = [row_num - 1, row_num + 1]

    columns = [ (-row_num % 2) + column_num + d for d in [0, 1]]

    for ci in range(2):
        for ri in range(2):
            if (0 <= rows[ri] <= 7) and (0 <= columns[ci] <= 3):
                yield rows[ri] * 4 + columns[ci]


# 0-based
def possible_jumps(position: int, red: bool, king: bool) -> Generator[tuple[int, int], None, None]:
    row_num = position // 4
    column_num = position % 4

    target_rows = [row_num - 2, -1] if red else [row_num + 2, -1]
    eaten__rows = [row_num - 1, -1] if red else [row_num + 1, -1]
    if king:
        target_rows = [row_num - 2, row_num + 2]
        eaten__rows = [row_num - 1, row_num + 1]

    target_columns = [ci for ci in [column_num - 1, column_num + 1]]
    eaten__columns = [(-row_num % 2) + column_num + d for d in [0, 1]]

    for ci in range(2):
        for ri in range(2):
            if (0 <= target_rows[ri] <= 7) and (0 <= target_columns[ci] <= 3):
                target = target_rows[ri] * 4 + target_columns[ci]
                eaten = eaten__rows[ri] * 4 + eaten__columns[ci]
                yield target, eaten


def has_jump(cells: list[int], position: int) -> bool:
    if cells[position] == 0:
        return False

    red = cells[position] % 16 == 2
    king = cells[position] // 10 == 16

    row_num = position // 4
    column_num = position % 4

    row_t_inc = -2 if red else 2
    column_e_inc = 0 if row_num % 2 else -1
    to_eat = 1 if red else 2

    def am_eat_when_move(cells, to_eat, target, eaten):
        return 0 <= target <= 31 and cells[target] == 0 and cells[eaten] % 16 == to_eat

    def has_jump_in_direction(row_t_inc):
        row_e_inc = row_t_inc // 2
        position_t_b = (row_num + row_t_inc) * 4 + column_num
        position_e_b = (row_num + row_e_inc) * 4 + column_num
        if (am_eat_when_move(cells, to_eat, position_t_b - 1, position_e_b + column_e_inc)) \
                or am_eat_when_move(cells, to_eat, position_t_b + 1, position_e_b + column_e_inc + 1):
            return True
        return False

    return has_jump_in_direction(row_t_inc) or (king and has_jump_in_direction(-row_t_inc))


def red_eater_position_to_cells(pos: int) -> list[int]:
    cells = [0] * 32
    cells[pos] = 162
    for m in possible_moves(pos, True, False):
        cells[m] = 1
    return cells


@given(
    cells_and_pos=strategies.integers(min_value=1, max_value=32).map(lambda i: (red_eater_position_to_cells(i), i)),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_jump_single_red(rules, game_id, cells_and_pos, nonce):
    cells, zero_based_pos = cells_and_pos
    print(f"cells: {cells}")
    print(f"zero_based_pos: {zero_based_pos}")

    player_who_cannot_move = W
    red_moves = True
    winner = 0
    board = [cells, red_moves, winner]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    is_jump = True
    pass_move = True

    for jump in possible_jumps(zero_based_pos, red=True, king=True):
        target, eaten = jump
        print(f"target: {target}")
        print(f"eaten: {eaten}")
        move = [zero_based_pos + 1, target + 1, is_jump, pass_move]
        move_encoded = encode_abi(MOVE_TYPES, move)
        assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)

        print(f"occupied_by_red(zero_based_pos + 1, cells): {occupied_by_red(zero_based_pos + 1, cells)}")
        print(f"unoccupied(target + 1, cells): {unoccupied(target + 1, cells)}")
        print(f"occupied_by_white(eaten + 1, cells): {occupied_by_white(eaten + 1, cells)}")

        is_valid = occupied_by_red(zero_based_pos + 1, cells) and \
                   unoccupied(target + 1, cells) and \
                   occupied_by_white(eaten + 1, cells)

        assert rules.isValidMove(game_state, R, move_encoded) == is_valid
        # assert is_valid == has_jump(cells, zero_based_pos)


def test_red_can_not_jump_5_14(rules, game_id):
    cells = [1, 1, 0, 0, 162, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    nonce = 0
    red_moves = True
    winner = 0
    board = [cells, red_moves, winner]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    player_who_cannot_move = W
    from_cell = 5
    to_cell = 14
    is_jump = True
    pass_move = True
    move = [from_cell, to_cell, is_jump, pass_move]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)


def test_red_king_jumps_13_6_10(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │   │███│ . │███│   │███│   │███│ 08 8
    #      9  09 │███│ o │███│ o │███│   │███│   │ 0C 12
    #      13 0D │ X │███│   │███│   │███│   │███│ 10 16
    #      17 11 │███│   │███│   │███│   │███│   │ 14 20
    #      21 15 │   │███│   │███│   │███│   │███│ 18 24
    #      25 19 │███│   │███│   │███│   │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 162, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    nonce = 0
    red_moves = True
    winner = 0
    board = [cells, red_moves, winner]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    player_who_cannot_move = W
    from_cell = 13
    to_cell = 6
    is_jump = True
    pass_move = True
    move = [from_cell, to_cell, is_jump, pass_move]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)
    assert not rules.isValidMove(game_state, R, move_encoded)

    player_who_cannot_move = W
    from_cell = 13
    to_cell = 6
    is_jump = True
    pass_move = False
    move = [from_cell, to_cell, is_jump, pass_move]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)
    assert rules.isValidMove(game_state, R, move_encoded)


# cells: [0, 0, 0, 0, 1, 0, 0, 0, 162, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
# zero_based_pos: 8
# target: 1
# eaten: 4
# occupied_by_red(zero_based_pos + 1, cells): True
# unoccupied(target + 1, cells): True
# occupied_by_white(eaten + 1, cells): True

def test_red_king_jumps_9_2_5(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │ o │███│   │███│   │███│   │███│ 08 8
    #      9  09 │███│ X │███│   │███│   │███│   │ 0C 12
    #      13 0D │   │███│   │███│   │███│   │███│ 10 16
    #      17 11 │███│   │███│   │███│   │███│   │ 14 20
    #      21 15 │   │███│   │███│   │███│   │███│ 18 24
    #      25 19 │███│   │███│   │███│   │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 162, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    nonce = 0
    red_moves = True
    winner = 0
    board = [cells, red_moves, winner]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    player_who_cannot_move = W
    from_cell = 13
    to_cell = 6
    is_jump = True
    pass_move = True
    move = [from_cell, to_cell, is_jump, pass_move]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)
    assert not rules.isValidMove(game_state, R, move_encoded)


def test_red_king_jumps_10_1_6(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │ o │███│ o │███│   │███│   │███│ 08 8
    #      9  09 │███│   │███│ X │███│   │███│   │ 0C 12
    #      13 0D │   │███│   │███│   │███│   │███│ 10 16
    #      17 11 │███│   │███│   │███│   │███│   │ 14 20
    #      21 15 │   │███│   │███│   │███│   │███│ 18 24
    #      25 19 │███│   │███│   │███│   │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0, 0, 0, 0, 1, 1, 0, 0, 0, 162, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    nonce = 0
    red_moves = True
    winner = 0
    board = [cells, red_moves, winner]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    player_who_cannot_move = W
    from_cell = 10
    to_cell = 1
    is_jump = True
    pass_move = True
    move = [from_cell, to_cell, is_jump, pass_move]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)
    assert rules.isValidMove(game_state, R, move_encoded)


def test_transition_single_move(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │   │███│   │███│   │███│   │███│ 08 8
    #      9  09 │███│   │███│10 │███│11 │███│   │ 0C 12
    #      13 0D │   │███│ 14│███│ * │███│   │███│ 10 16
    #      17 11 │███│ * │███│18 │███│19 │███│   │ 14 20
    #      21 15 │ 21│███│   │███│   │███│   │███│ 18 24
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
    assert next_winner == 2  # red wins because no white pieces left

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
    assert next_winner == 1

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
    assert next_winner == 2

    move = [15, 18, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move_encoded)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[18 - 1] == 2
    assert not next_move_is_red
    assert next_winner == 2


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


def test_transition_single_white_jump(rules, game_id):  # TODO only a king can do this
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
    #      13 0D │   │███│   │███│ o │███│   │███│ 10 16
    #      17 11 │███│   │███│18 │███│   │███│   │ 14 20
    #      21 15 │   │███│   │███│ o │███│   │███│ 18 24
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
    assert next_winner == 2


def test_transition_double_white_jump(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │   │███│   │███│   │███│   │███│ 08 8
    #      9  09 │███│   │███│   │███│ o │███│   │ 0C 12
    #      13 0D │   │███│   │███│ x │███│   │███│ 10 16
    #      17 11 │███│   │███│18 │███│   │███│   │ 14 20
    #      21 15 │   │███│   │███│ x │███│   │███│ 18 24
    #      25 19 │███│   │███│   │███│27 │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0] * 32

    cells[11 - 1] = 1
    cells[15 - 1] = 2
    cells[23 - 1] = 2

    nonce = 0
    board = encode_board(cells=cells, red_moves=False)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=11,
                       to=18,
                       is_jump=True,
                       pass_move=False)
    assert rules.isValidMove(game_state, W, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[11 - 1] == 0
    assert next_cells[18 - 1] == 1
    assert next_cells[15 - 1] == 0
    assert not next_move_is_red
    assert next_winner == 0

    board = encode_board(cells=next_cells, red_moves=False)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=18,
                       to=27,
                       is_jump=True,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[18 - 1] == 0
    assert next_cells[27 - 1] == 1
    assert next_move_is_red
    assert next_winner == 1


def test_transition_red_becomes_king(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │   │███│ x │███│   │███│   │███│ 08 8
    #      9  09 │███│   │███│   │███│   │███│   │ 0C 12
    #      13 0D │   │███│   │███│   │███│   │███│ 10 16
    #      17 11 │███│   │███│   │███│   │███│   │ 14 20
    #      21 15 │   │███│   │███│   │███│   │███│ 18 24
    #      25 19 │███│   │███│   │███│   │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0] * 32
    cells[6 - 1] = 2

    nonce = 0
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=6,
                       to=1,
                       is_jump=False,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[6 - 1] == 0
    assert next_cells[1 - 1] == 162
    assert not next_move_is_red
    assert next_winner == 2

    move = encode_move(fr=6,
                       to=2,
                       is_jump=False,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[6 - 1] == 0
    assert next_cells[2 - 1] == 162
    assert not next_move_is_red
    assert next_winner == 2


def test_transition_single_white_jump_becomes_king(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │   │███│   │███│   │███│   │███│ 08 8
    #      9  09 │███│   │███│   │███│   │███│   │ 0C 12
    #      13 0D │   │███│   │███│   │███│   │███│ 10 16
    #      17 11 │███│   │███│   │███│   │███│   │ 14 20
    #      21 15 │   │███│ o │███│   │███│   │███│ 18 24
    #      25 19 │███│ x │███│ x │███│   │███│   │ 1C 28
    #      29 1D │ . │███│   │███│ . │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0] * 32

    cells[22 - 1] = 1
    cells[25 - 1] = 2
    cells[26 - 1] = 2

    nonce = 0
    board = encode_board(cells=cells, red_moves=False)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=22,
                       to=29,
                       is_jump=True,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[22 - 1] == 0
    assert next_cells[25 - 1] == 0
    assert next_cells[26 - 1] == 2
    assert next_cells[29 - 1] == 161
    assert next_move_is_red
    assert next_winner == 0

    move = encode_move(fr=22,
                       to=31,
                       is_jump=True,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[22 - 1] == 0
    assert next_cells[25 - 1] == 2
    assert next_cells[26 - 1] == 0
    assert next_cells[31 - 1] == 161
    assert next_move_is_red
    assert next_winner == 0


def test_no_more_moves(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│   │ 04 4
    #      5  05 │   │███│   │███│   │███│   │███│ 08 8
    #      9  09 │███│ o │███│ o │███│ o │███│ o │ 0C 12
    #      13 0D │ o │███│ o │███│ o │███│ o │███│ 10 16
    #      17 11 │███│ x │███│ x │███│ x │███│ x │ 14 20
    #      21 15 │ x │███│ x │███│ x │███│ x │███│ 18 24
    #      25 19 │███│   │███│   │███│   │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│ x │███│ 20 32
    #             1D      1E      1F      20
    cells = [0] * 8 + [1] * 8 + [2] * 8 + [0] * 7 + [2]
    nonce = 10
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=32,
                       to=28,
                       is_jump=False,
                       pass_move=True)
    assert rules.isValidMove(game_state, R, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[32 - 1] == 0
    assert next_cells[28 - 1] == 2
    assert not next_move_is_red
    assert next_winner == 2

    #                  1       2       3       4
    #      1  01 │███│   │███│   │███│   │███│ o │ 04 4
    #      5  05 │   │███│   │███│   │███│ . │███│ 08 8
    #      9  09 │███│   │███│   │███│ x │███│ x │ 0C 12
    #      13 0D │   │███│   │███│   │███│   │███│ 10 16
    #      17 11 │███│   │███│   │███│   │███│   │ 14 20
    #      21 15 │   │███│   │███│   │███│   │███│ 18 24
    #      25 19 │███│   │███│   │███│   │███│   │ 1C 28
    #      29 1D │   │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0] * 32
    cells[4 - 1] = 1
    cells[11 - 1] = 2
    cells[12 - 1] = 2
    nonce = 10
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=12,
                       to=8,
                       is_jump=False,
                       pass_move=True)
    assert rules.isValidMove(game_state, R, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[12 - 1] == 0
    assert next_cells[8 - 1] == 2
    assert not next_move_is_red
    assert next_winner == 2


def test_white_king_jumps(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│   │███│ o │███│   │███│   │ 04 4
    #      5  05 │ o │███│   │███│ o │███│   │███│ 08 8
    #      9  09 │███│ o │███│ o │███│   │███│ o │ 0C 12
    #      13 0D │ o │███│ o │███│ o │███│   │███│ 10 16
    #      17 11 │███│ x │███│   │███│   │███│   │ 14 20
    #      21 15 │ x │███│ x │███│ x │███│   │███│ 18 24
    #      25 19 │███│ x │███│   │███│ O │███│ x │ 1C 28
    #      29 1D │ x │███│   │███│   │███│   │███│ 20 32
    #             1D      1E      1F      20
    cells = [0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 2, 0, 0, 0, 2, 2, 2, 0, 2, 0, 161, 2, 2, 0, 0, 0]
    print(list(enumerate(cells)))
    nonce = 36
    board = encode_board(cells=cells, red_moves=False)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=27,
                       to=18,
                       is_jump=True,
                       pass_move=True)
    # assert rules._canJump(cells, 27 - 1)
    # assert not rules._canJump(cells, 18 - 1)
    assert rules.isValidMove(game_state, W, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[27 - 1] == 0
    assert next_cells[23 - 1] == 0
    assert next_cells[18 - 1] == 161
    assert next_move_is_red
    assert next_winner == 0


def test_red_jumps_23_16(rules, game_id):
    #                  1       2       3       4
    #      1  01 │███│ o │███│ o │███│ o │███│ o │ 04 4
    #      5  05 │ o │███│ o │███│ o │███│ o │███│ 08 8
    #      9  09 │███│   │███│   │███│   │███│ o │ 0C 12
    #      13 0D │   │███│ o │███│   │███│   │███│ 10 16
    #      17 11 │███│ x │███│   │███│ o │███│ x │ 14 20
    #      21 15 │ x │███│   │███│ x │███│   │███│ 18 24
    #      25 19 │███│   │███│ x │███│ x │███│ x │ 1C 28
    #      29 1D │ x │███│ x │███│ x │███│ x │███│ 20 32
    #             1D      1E      1F      20
    cells = [1, 1, 1, 1,
             1, 1, 1, 1,
             0, 0, 0, 1,
             0, 1, 0, 0,
             2, 0, 1, 2,
             2, 0, 2, 0,
             0, 2, 2, 2,
             2, 2, 2, 2]

    new_cells = (1, 1, 1, 1,
                 1, 1, 1, 1,
                 0, 0, 0, 1,
                 0, 1, 0, 2,
                 2, 0, 0, 2,
                 2, 0, 0, 0,
                 0, 2, 2, 2,
                 2, 2, 2, 2)
    nonce = 8
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=23,
                       to=16,
                       is_jump=True,
                       pass_move=False)
    assert rules._canJump(cells, 17 - 1)
    assert rules._canJump(cells, 23 - 1)
    assert rules.isValidMove(game_state, R, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells == new_cells
    assert next_cells[23 - 1] == 0
    assert next_cells[19 - 1] == 0
    assert next_cells[16 - 1] == 2
    assert next_move_is_red
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
    return cells[cell - 1] % 16 == 2


def occupied_by_white(cell: int, cells: List[int]) -> bool:
    return cells[cell - 1] % 16 == 1


def unoccupied(cell: int, cells: List[int]) -> bool:
    return cells[cell - 1] == 0
