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

WHITE = 1
RED = 2
WHITE_KING = 161
RED_KING = 162


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
#     bool passMoveToOpponent;
# }

STATE_TYPES = ["uint8[32]", "bool", "uint8"]
MOVE_TYPES = ["uint8", "uint8", "bool"]

W, R = 0, 1  # playerId


#                  0       1       2       3
#      0  │███│ o │███│ o │███│ o │███│ o │ 3
#      4  │ o │███│ o │███│ o │███│ o │███│ 7
#      8  │███│ o │███│ o │███│ o │███│ o │ 11
#      12 │   │███│   │███│   │███│   │███│ 15
#      16 │███│   │███│   │███│   │███│   │ 21
#      20 │ x │███│ x │███│ x │███│ x │███│ 25
#      24 │███│ x │███│ x │███│ x │███│ x │ 27
#      28 │ x │███│ x │███│ x │███│ x │███│ 31
#             1С      1D      1E      1F

@given(
    empty_cells=st('uint8[32]', max_value=0),
    from_cell=st('uint8', min_value=0, max_value=31),
    to_cell=st('uint8', min_value=0, max_value=31),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=10)
)
def test_is_valid_move_empty_board(rules, game_id, empty_cells, from_cell, to_cell, red_moves, nonce):
    empty_board = encode_board(empty_cells, red_moves=red_moves, winner=0)
    game_state = [game_id, nonce, empty_board]

    move = [from_cell, to_cell, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, R, move_encoded)
    assert not rules.isValidMove(game_state, W, move_encoded)


@given(
    cells=(strategies.integers(min_value=0, max_value=31).map(lambda i: [1 if j == i - 1 else 0 for j in range(32)])),
    from_cell=st('uint8', min_value=0, max_value=31),
    to_cell=st('uint8', min_value=0, max_value=31),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_move_single_white(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    board = encode_board(cells, red_moves, winner=0)
    game_state = [game_id, nonce, board]

    move = encode_move(from_cell, to_cell, pass_move=False)
    assert not rules.isValidMove(game_state, W, move)

    is_valid = not red_moves and cells[from_cell - 1] == 2 and from_cell // 4 < 7 and (
            (from_cell + 4) % 8 == 1 and to_cell == from_cell - 4 or
            (from_cell + 4) % 8 == 0 and to_cell == from_cell - 5 or
            (to_cell == from_cell + 4 or to_cell == from_cell + 5)
    )
    assert rules.isValidMove(game_state, R, move) == is_valid


@given(
    cells=(strategies.integers(min_value=0, max_value=31).map(lambda i: [2 if j == i - 1 else 0 for j in range(32)])),
    from_cell=st('uint8', min_value=0, max_value=31),
    to_cell=st('uint8', min_value=0, max_value=31),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_move_single_red(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = encode_move(fr=from_cell, to=to_cell, pass_move=True)
    assert not rules.isValidMove(game_state, W, move)

    is_valid = red_moves and occupied_by_red(from_cell, cells) \
               and unoccupied(to_cell, cells) \
               and to_cell in possible_moves(from_cell, red_moves, False)

    assert rules.isValidMove(game_state, R, move) == is_valid


@given(
    cells=(strategies.sets(strategies.integers(min_value=0, max_value=31), min_size=1, max_size=32).map(
        lambda s: [1 if j + 1 in s else 0 for j in range(32)])),
    from_cell=st('uint8', min_value=0, max_value=31),
    to_cell=st('uint8', min_value=0, max_value=31),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_move_multiple_white_checkers(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = encode_move(fr=from_cell, to=to_cell, pass_move=True)
    assert not rules.isValidMove(game_state, R, move)

    is_valid = not red_moves and occupied_by_white(from_cell, cells) \
               and unoccupied(to_cell, cells) \
               and to_cell in possible_moves(from_cell, False, False)
    assert rules.isValidMove(game_state, W, move) == is_valid


@given(
    cells=(strategies.sets(strategies.integers(min_value=0, max_value=31), min_size=2, max_size=32).map(
        lambda s: [2 if j + 1 in s else 0 for j in range(32)])),
    from_cell=st('uint8', min_value=0, max_value=31),
    to_cell=st('uint8', min_value=0, max_value=31),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_move_multiple_red_checkers(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = encode_move(fr=from_cell, to=to_cell, pass_move=True)
    assert not rules.isValidMove(game_state, W, move)

    is_valid = red_moves and occupied_by_red(from_cell, cells) \
               and unoccupied(to_cell, cells) \
               and to_cell in possible_moves(from_cell, red_moves, False)

    assert rules.isValidMove(game_state, R, move) == is_valid


def test_red_king_moves_2_6(rules, game_id):
    #                  0       1       2       3
    #      0  00 │███│   │███│   │███│ x │███│   │ 03 3
    #      4  04 │   │███│   │███│ . │███│   │███│ 07 7
    #      8  08 │███│   │███│   │███│   │███│   │ 0B 11
    #      12 0С │   │███│   │███│   │███│   │███│ 0F 15
    #      16 10 │███│   │███│   │███│   │███│   │ 13 19
    #      20 14 │   │███│   │███│   │███│   │███│ 17 23
    #      24 18 │███│   │███│   │███│   │███│   │ 1B 27
    #      28 1С │   │███│   │███│   │███│   │███│ 1F 31
    #             1С      1D      1E      1F
    cells = [0, 0, 162, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    nonce = 0
    board = encode_board(cells=cells, red_moves=True, winner=0)
    game_state = [game_id, nonce, board]
    move = encode_move(fr=2, to=6, pass_move=True)
    assert rules.isValidMove(game_state, R, move)


def test_red_king_jumps_back(rules, game_id):
    #               0       1       2       3
    #      0  │███│   │███│ x │███│   │███│   │ 3
    #      4  │   │███│ o │███│   │███│   │███│ 7
    #      8  │███│ . │███│   │███│   │███│   │ 11
    #      12 │   │███│ o │███│   │███│   │███│ 15
    #      16 │███│   │███│ . │███│   │███│   │ 19
    #      20 │   │███│   │███│ o │███│   │███│ 23
    #      24 │███│   │███│   │███│ . │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #           28      29      30      31
    cells = [0, 162, 0, 0,
             0, 1, 0, 0,
             0, 0, 0, 0,
             0, 1, 0, 0,
             0, 0, 0, 0,
             0, 0, 1, 0,
             0, 0, 0, 0,
             0, 0, 0, 0]
    nonce = 0
    board = encode_board(cells=cells, red_moves=True, winner=0)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=1, to=8, pass_move=False)
    assert rules.isValidMove(game_state, R, move)
    game_state_1 = [game_id_1, nonce_1, board_1] = rules.transition(game_state, R, move)
    assert game_id_1 == game_id
    assert nonce_1 == nonce + 1
    [cells_1, move_is_red_1, winner_1] = decode_abi(STATE_TYPES, board_1)
    assert cells_1[1] == 0
    assert cells_1[5] == 0
    assert cells_1[8] == RED_KING
    assert move_is_red_1
    assert winner_1 == 0

    move = encode_move(fr=8, to=17, pass_move=False)
    assert rules.isValidMove(game_state_1, R, move)
    game_state_2 = [game_id_2, nonce_2, board_2] = rules.transition(game_state_1, R, move)
    assert game_id_2 == game_id
    assert nonce_2 == nonce + 2
    [cells_2, move_is_red_2, winner_2] = decode_abi(STATE_TYPES, board_2)
    assert cells_2[8] == 0
    assert cells_2[13] == 0
    assert cells_2[17] == RED_KING
    assert move_is_red_2
    assert winner_2 == 0

    move = encode_move(fr=17, to=26, pass_move=True)
    assert rules.isValidMove(game_state_2, R, move)
    game_state_3 = [game_id_3, nonce_3, board_3] = rules.transition(game_state_2, R, move)
    assert game_id_3 == game_id
    assert nonce_3 == nonce + 3
    [cells_3, move_is_red_3, winner_3] = decode_abi(STATE_TYPES, board_3)
    assert cells_3[17] == 0
    assert cells_3[22] == 0
    assert cells_3[26] == RED_KING
    assert not move_is_red_3
    assert winner_3 == RED


def test_red_moves_4_0(rules, game_id):
    #                  0       1       2       3
    #      0  00 │███│   │███│ x │███│   │███│   │ 03 3
    #      4  04 │ x │███│   │███│   │███│   │███│ 07 7
    #      8  08 │███│   │███│   │███│   │███│   │ 0B 11
    #      12 0С │   │███│   │███│   │███│   │███│ 0F 15
    #      16 10 │███│   │███│   │███│   │███│   │ 13 19
    #      20 14 │   │███│   │███│   │███│   │███│ 17 23
    #      24 18 │███│   │███│   │███│   │███│   │ 1B 27
    #      28 1С │   │███│   │███│   │███│   │███│ 1F 31
    #             1С      1D      1E      1F
    cells = [0, 2, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    nonce = 0
    board = encode_board(cells=cells, red_moves=True, winner=0)
    game_state = [game_id, nonce, board]
    move = encode_move(fr=4, to=0, pass_move=True)
    assert rules.isValidMove(game_state, R, move)


#               0       1       2       3
#      0  │███│   │███│   │███│   │███│   │ 3
#      4  │   │███│ . │███│ 7 │███│ . │███│ 7
#      8  │███│   │███│ o │███│ o │███│   │ 11
#      12 │   │███│   │███│ x │███│   │███│ 15
#      16 │███│   │███│ o │███│ o │███│   │ 19
#      20 │   │███│ . │███│   │███│ . │███│ 23
#      24 │███│   │███│   │███│   │███│   │ 27
#      28 │   │███│   │███│   │███│   │███│ 31
#           28      29      30      31

@given(
    cells=(strategies.tuples(
        strategies.integers(min_value=0, max_value=31),
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
    from_cell=st('uint8', min_value=0, max_value=31),
    to_cell=st('uint8', min_value=0, max_value=31),
    red_moves=st('bool'),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_jump_single_white(rules, game_id, cells, from_cell, to_cell, red_moves, nonce):
    player_who_cannot_move = R
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [from_cell, to_cell, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)

    def is_valid_white_jump(jump):
        target, eaten = jump
        return occupied_by_red(eaten, cells) and to_cell == target

    has_valid_white_jump = any(map(is_valid_white_jump, possible_jumps(from_cell, red=False, king=False)))

    is_valid = not red_moves \
               and occupied_by_white(from_cell, cells) \
               and unoccupied(to_cell, cells) \
               and has_valid_white_jump

    assert rules.isValidMove(game_state, W, move_encoded) == is_valid


#           0       1       2       3
#      0  │███│   │███│   │███│   │███│   │ 3
#      4  │   │███│ . │███│   │███│ . │███│ 7
#      8  │███│   │███│ x │███│ x │███│   │ 11
#      12 │   │███│   │███│ o │███│   │███│ 15
#      16 │███│   │███│ x │███│ x │███│   │ 19
#      20 │   │███│ . │███│   │███│ . │███│ 23
#      24 │███│   │███│   │███│   │███│   │ 27
#      28 │   │███│   │███│   │███│   │███│ 31
#           28      29      30      31

def possible_moves(position: int, red: bool, king: bool) -> Generator[int, None, None]:
    row_num = position // 4
    column_num = position % 4

    rows = [row_num - 1, -1] if red else [row_num + 1, -1]
    if king:
        rows = [row_num - 1, row_num + 1]

    columns = [-(row_num % 2) + column_num + d for d in [0, 1]]

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
    eaten__columns = [-(row_num % 2) + column_num + d for d in [0, 1]]

    for ci in range(2):
        for ri in range(2):
            if (0 <= target_rows[ri] <= 7) and (0 <= target_columns[ci] <= 3):
                target = target_rows[ri] * 4 + target_columns[ci]
                eaten = eaten__rows[ri] * 4 + eaten__columns[ci]
                yield target, eaten


def red_eater_position_to_cells(pos: int) -> list[int]:
    cells = [0] * 32
    cells[pos] = 162
    for m in possible_moves(pos, True, False):
        cells[m] = 1
    return cells


@given(
    cells_and_pos=strategies.integers(min_value=0, max_value=31).map(lambda i: (red_eater_position_to_cells(i), i)),
    nonce=st('uint256', max_value=100)
)
def test_is_valid_jump_single_red(rules, game_id, cells_and_pos, nonce):
    cells, position = cells_and_pos
    print(f"cells: {cells}")
    print(f"position: {position}")

    player_who_cannot_move = W
    red_moves = True
    winner = 0
    board = [cells, red_moves, winner]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    pass_move = True

    for jump in possible_jumps(position, red=True, king=True):
        target, eaten = jump
        print(f"target: {target}")
        print(f"eaten: {eaten}")
        move = [position, target, pass_move]
        move_encoded = encode_abi(MOVE_TYPES, move)
        assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)

        print(f"occupied_by_red(position, cells): {occupied_by_red(position, cells)}")
        print(f"unoccupied(target, cells): {unoccupied(target, cells)}")
        print(f"occupied_by_white(eaten, cells): {occupied_by_white(eaten, cells)}")

        is_valid = occupied_by_red(position, cells) and \
                   unoccupied(target, cells) and \
                   occupied_by_white(eaten, cells)

        assert rules.isValidMove(game_state, R, move_encoded) == is_valid
        # assert is_valid == has_jump(cells, position) 


def test_white_cant_move_4_7(rules, game_id):
    cells = [0, 0, 0, 0,
             1, 0, 0, 0,
             0, 0, 1, 0,
             0, 0, 0, 0,
             0, 0, 0, 0,
             0, 0, 0, 0,
             0, 0, 0, 0,
             0, 1, 0, 0]
    from_cell = 4
    to_cell = 7
    red_moves = False
    nonce = 52
    winner = 0
    board = [cells, red_moves, winner]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    pass_move = True
    move = [from_cell, to_cell, pass_move]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, W, move_encoded)


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
    pass_move = True
    move = [from_cell, to_cell, pass_move]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)


def test_red_king_jumps_12_5_9(rules, game_id):
    #               0       1       2       3
    #      0  │███│   │███│   │███│   │███│   │ 3
    #      4  │   │███│ . │███│   │███│   │███│ 7
    #      8  │███│ o │███│ o │███│   │███│   │ 11
    #      12 │ X │███│   │███│   │███│   │███│ 15
    #      16 │███│   │███│   │███│   │███│   │ 19
    #      20 │   │███│   │███│   │███│   │███│ 23
    #      24 │███│   │███│   │███│   │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #           28      29      30      31
    cells = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 162, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    nonce = 0
    red_moves = True
    winner = 0
    board = [cells, red_moves, winner]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    player_who_cannot_move = W
    from_cell = 12
    to_cell = 5
    pass_move = True
    move = [from_cell, to_cell, pass_move]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)
    assert not rules.isValidMove(game_state, R, move_encoded)

    player_who_cannot_move = W
    from_cell = 12
    to_cell = 5
    pass_move = False
    move = [from_cell, to_cell, pass_move]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)
    assert rules.isValidMove(game_state, R, move_encoded)


def test_red_king_jumps_8_1_4(rules, game_id):
    #               0       1       2       3
    #      0  │███│   │███│   │███│   │███│   │ 3
    #      4  │ o │███│   │███│   │███│   │███│ 7
    #      8  │███│ X │███│   │███│   │███│   │ 11
    #      12 │   │███│   │███│   │███│   │███│ 15
    #      16 │███│   │███│   │███│   │███│   │ 19
    #      20 │   │███│   │███│   │███│   │███│ 23
    #      24 │███│   │███│   │███│   │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #           28      29      30      31
    cells = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 162, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    nonce = 0
    red_moves = True
    winner = 0
    board = [cells, red_moves, winner]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    player_who_cannot_move = W
    from_cell = 8
    to_cell = 1
    pass_move = True
    move = [from_cell, to_cell, pass_move]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, player_who_cannot_move, move_encoded)
    assert not rules.isValidMove(game_state, R, move_encoded)


def test_transition_single_move(rules, game_id):
    #               0       1       2       3
    #      0  │███│   │███│   │███│   │███│   │ 3
    #      4  │   │███│   │███│   │███│   │███│ 7
    #      8  │███│   │███│10 │███│11 │███│   │ 11
    #      12 │   │███│ 14│███│ * │███│   │███│ 15
    #      16 │███│ * │███│18 │███│19 │███│   │ 19
    #      20 │ 21│███│   │███│   │███│   │███│ 23
    #      24 │███│   │███│   │███│   │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #           28      29      30      31
    cells = [0] * 32
    cells[15 - 1] = 2

    red_moves = True
    nonce = 0
    board = [cells, red_moves, 0]
    board_encoded = encode_abi(STATE_TYPES, board)
    game_state = [game_id, nonce, board_encoded]

    move = [14, 9, False]
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

    move = [14, 10, False]
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

    move = [14, 18, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move_encoded)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[15 - 1] == 0
    assert next_cells[19 - 1] == 2
    assert not next_move_is_red
    assert next_winner == 2

    move = [14, 17, False]
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
    #               0       1       2       3
    #      0  │███│   │███│   │███│   │███│   │ 3
    #      4  │   │███│ 6 │███│   │███│ 8 │███│ 7
    #      8  │███│   │███│ o │███│ o │███│   │ 11
    #      12 │   │███│   │███│ x │███│   │███│ 15
    #      16 │███│   │███│   │███│   │███│   │ 19
    #      20 │   │███│   │███│   │███│   │███│ 23
    #      24 │███│   │███│   │███│   │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #           28      29      30      31
    cells = [0] * 32
    cells[5] = 0

    cells[15 - 1] = 2
    cells[10 - 1] = 1
    cells[11 - 1] = 1

    nonce = 0
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=14,
                       to=5,
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

    move = encode_move(fr=14,
                       to=7,
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
    #               0       1       2       3
    #      0  │███│   │███│   │███│   │███│   │ 3
    #      4  │   │███│ 6 │███│   │███│ 8 │███│ 7
    #      8  │███│   │███│ x │███│ x │███│   │ 11
    #      12 │   │███│   │███│ o │███│   │███│ 15
    #      16 │███│   │███│   │███│   │███│   │ 19
    #      20 │   │███│   │███│   │███│   │███│ 23
    #      24 │███│   │███│   │███│   │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #           28      29      30      31
    cells = [0] * 32

    cells[15 - 1] = 1
    cells[10 - 1] = 2
    cells[11 - 1] = 2

    nonce = 0
    board = encode_board(cells=cells, red_moves=False)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=14,
                       to=5,
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

    move = encode_move(fr=14,
                       to=7,
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
    #               0       1       2       3
    #      0  │███│   │███│   │███│   │███│   │ 3
    #      4  │   │███│   │███│   │███│   │███│ 7
    #      8  │███│   │███│   │███│11 │███│   │ 11
    #      12 │   │███│   │███│ o │███│   │███│ 15
    #      16 │███│   │███│18 │███│   │███│   │ 19
    #      20 │   │███│   │███│ o │███│   │███│ 23
    #      24 │███│   │███│   │███│ x │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #           28      29      30      31
    cells = [0] * 32

    cells[15 - 1] = 1
    cells[23 - 1] = 1
    cells[27 - 1] = 2

    nonce = 0
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=26,
                       to=17,
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

    move = encode_move(fr=17,
                       to=10,
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
    #               0       1       2       3
    #      0  │███│   │███│   │███│   │███│   │ 3
    #      4  │   │███│   │███│   │███│   │███│ 7
    #      8  │███│   │███│   │███│ o │███│   │ 11
    #      12 │   │███│   │███│ x │███│   │███│ 15
    #      16 │███│   │███│18 │███│   │███│   │ 19
    #      20 │   │███│   │███│ x │███│   │███│ 23
    #      24 │███│   │███│   │███│27 │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #           28      29      30      31
    cells = [0] * 32

    cells[11 - 1] = 1
    cells[15 - 1] = 2
    cells[23 - 1] = 2

    nonce = 0
    board = encode_board(cells=cells, red_moves=False)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=10,
                       to=17,
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

    move = encode_move(fr=17,
                       to=26,
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
    #               0       1       2       3
    #      0  │███│   │███│   │███│   │███│   │ 3
    #      4  │   │███│ x │███│   │███│   │███│ 7
    #      8  │███│   │███│   │███│   │███│   │ 11
    #      12 │   │███│   │███│   │███│   │███│ 15
    #      16 │███│   │███│   │███│   │███│   │ 19
    #      20 │   │███│   │███│   │███│   │███│ 23
    #      24 │███│   │███│   │███│   │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #           28      29      30      31
    cells = [0] * 32
    cells[6 - 1] = 2

    nonce = 0
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=5,
                       to=0,
                       pass_move=True)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells[6 - 1] == 0
    assert next_cells[1 - 1] == 162
    assert not next_move_is_red
    assert next_winner == 2

    move = encode_move(fr=5,
                       to=1,
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
    #                  0       1       2       3
    #      0  00 │███│   │███│   │███│   │███│   │ 03 3
    #      4  04 │   │███│   │███│   │███│   │███│ 07 7
    #      8  08 │███│   │███│   │███│   │███│   │ 0B 11
    #      12 0С │   │███│   │███│   │███│   │███│ 0F 15
    #      16 10 │███│   │███│   │███│   │███│   │ 13 19
    #      20 14 │   │███│ o │███│   │███│   │███│ 17 23
    #      24 18 │███│ x │███│ x │███│   │███│   │ 1B 27
    #      28 1С │ . │███│   │███│ . │███│   │███│ 1F 31
    #             1С      1D      1E      1F
    cells = [0] * 32

    cells[22 - 1] = 1
    cells[25 - 1] = 2
    cells[26 - 1] = 2

    nonce = 0
    board = encode_board(cells=cells, red_moves=False)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=21,
                       to=28,
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

    move = encode_move(fr=21,
                       to=30,
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
    #                  0       1       2       3
    #      0  00 │███│   │███│   │███│   │███│   │ 03 3
    #      4  04 │   │███│   │███│   │███│   │███│ 07 7
    #      8  08 │███│ o │███│ o │███│ o │███│ o │ 0B 11
    #      12 0С │ o │███│ o │███│ o │███│ o │███│ 0F 15
    #      16 10 │███│ x │███│ x │███│ x │███│ x │ 13 19
    #      20 14 │ x │███│ x │███│ x │███│ x │███│ 17 23
    #      24 18 │███│   │███│   │███│   │███│ . │ 1B 27
    #      28 1С │   │███│   │███│   │███│ x │███│ 1F 31
    #             1С      1D      1E      1F
    cells = [0] * 8 + [1] * 8 + [2] * 8 + [0] * 7 + [2]
    nonce = 10
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=31,
                       to=27,
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

    #               0       1       2       3
    #      0  │███│   │███│ o │███│   │███│   │ 3
    #      4  │   │███│ x │███│ . │███│   │███│ 7
    #      8  │███│ x │███│ x │███│ x │███│   │ 11
    #      12 │   │███│   │███│   │███│   │███│ 15
    #      16 │███│   │███│   │███│   │███│   │ 19
    #      20 │   │███│   │███│   │███│   │███│ 23
    #      24 │███│   │███│   │███│   │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #             1С      1D      1E      1F
    cells = [0] * 32
    cells[1] = 1
    cells[5] = 2
    cells[8] = 2
    cells[9] = 2
    cells[10] = 2

    nonce = 10
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=9,
                       to=6,
                       pass_move=True)
    assert rules.isValidMove(game_state, R, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)

    assert next_cells[9] == 0
    assert next_cells[6] == 2
    assert not next_move_is_red
    assert next_winner == 2

    #                  0       1       2       3
    #      0  00 │███│   │███│   │███│   │███│ o │ 03 3
    #      4  04 │   │███│   │███│   │███│ . │███│ 07 7
    #      8  08 │███│   │███│   │███│ x │███│ x │ 0B 11
    #      12 0С │   │███│   │███│   │███│   │███│ 0F 15
    #      16 10 │███│   │███│   │███│   │███│   │ 13 19
    #      20 14 │   │███│   │███│   │███│   │███│ 17 23
    #      24 18 │███│   │███│   │███│   │███│   │ 1B 27
    #      28 1С │   │███│   │███│   │███│   │███│ 1F 31
    #             1С      1D      1E      1F
    cells = [0] * 32
    cells[4 - 1] = 1
    cells[11 - 1] = 2
    cells[12 - 1] = 2
    nonce = 10
    board = encode_board(cells=cells, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=11,
                       to=7,
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
    #               0       1       2       3
    #      0  │███│   │███│ o │███│   │███│   │ 3
    #      4  │ o │███│   │███│ o │███│   │███│ 7
    #      8  │███│ o │███│ o │███│   │███│ o │ 11
    #      12 │ o │███│ o │███│ o │███│   │███│ 15
    #      16 │███│ x │███│   │███│   │███│   │ 19
    #      20 │ x │███│ x │███│ x │███│   │███│ 23
    #      24 │███│ x │███│   │███│ O │███│ x │ 27
    #      28 │ x │███│   │███│   │███│   │███│ 31
    #           28      29      30      31
    cells = [0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 2, 0, 0, 0, 2, 2, 2, 0, 2, 0, 161, 2, 2, 0, 0, 0]
    print(list(enumerate(cells)))
    nonce = 36
    board = encode_board(cells=cells, red_moves=False)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=26,
                       to=17,
                       pass_move=True)
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


def test_red_jumps_22_15(rules, game_id):
    #                  0       1       2       3
    #      0  │███│ o │███│ o │███│ o │███│ o │ 3
    #      4  │ o │███│ o │███│ o │███│ o │███│ 7
    #      8  │███│   │███│   │███│   │███│ o │ 11
    #      12 │   │███│ o │███│   │███│ . │███│ 15
    #      16 │███│ x │███│   │███│ o │███│ x │ 19
    #      20 │ x │███│   │███│ x │███│   │███│ 23
    #      24 │███│   │███│ x │███│ x │███│ x │ 27
    #      28 │ x │███│ x │███│ x │███│ x │███│ 31
    #           28      29      30      31
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

    move = encode_move(fr=22,
                       to=15,
                       pass_move=False)
    assert rules.isValidMove(game_state, R, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells == new_cells
    assert next_cells[22] == 0
    assert next_cells[18] == 0
    assert next_cells[15] == 2
    assert next_move_is_red
    assert next_winner == 0


def test_white_cant_skip_jump(rules, game_id):
    #               0       1       2       3
    #      0  │███│ o │███│ o │███│ o │███│ o │ 3
    #      4  │ o │███│   │███│   │███│   │███│ 7
    #      8  │███│   │███│ o │███│   │███│   │ 11
    #      12 │ o │███│   │███│ o │███│   │███│ 15
    #      16 │███│ x │███│ . │███│   │███│ x │ 19
    #      20 │   │███│ . │███│   │███│ x │███│ 23
    #      24 │███│ x │███│   │███│   │███│   │ 27
    #      28 │ x │███│ x │███│ x │███│ x │███│ 31
    #           28      29      30      31
    cells0 = [1, 1, 1, 1,
              1, 0, 0, 0,
              0, 1, 0, 0,
              1, 0, 1, 0,
              2, 0, 0, 2,
              0, 0, 0, 2,
              2, 0, 0, 0,
              2, 2, 2, 2]

    cell1 = (1, 1, 1, 1,
             1, 0, 0, 0,
             0, 1, 0, 0,
             1, 0, 0, 0,
             2, 1, 0, 2,
             0, 0, 0, 2,
             2, 0, 0, 0,
             2, 2, 2, 2)
    nonce = 21
    board = encode_board(cells=cells0, red_moves=False)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=14,
                       to=17,
                       pass_move=True)
    assert not rules.isValidMove(game_state, R, move)
    assert not rules.isValidMove(game_state, W, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, W, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells == cell1
    assert next_move_is_red
    assert next_winner == 0


def test_red_dont_have_to_jump_after_a_non_jump_move(rules, game_id):
    #               0       1       2       3
    #      0  │███│   │███│   │███│   │███│ o │ 3
    #      4  │   │███│   │███│   │███│   │███│ 7
    #      8  │███│   │███│ X │███│ X │███│   │ 11
    #      12 │   │███│   │███│ . │███│ o │███│ 15
    #      16 │███│   │███│ O │███│   │███│ o │ 19
    #      20 │   │███│   │███│   │███│ x │███│ 23
    #      24 │███│   │███│ o │███│ x │███│   │ 27
    #      28 │   │███│ O │███│   │███│   │███│ 31
    #           28      29      30      31
    cells0 = [0, 0, 0, 1,
              0, 0, 0, 0,
              0, 162, 162, 0,
              0, 0, 0, 1,
              0, 161, 0, 1,
              0, 0, 0, 2,
              0, 1, 2, 0,
              0, 161, 0, 0]

    cells1 = (0, 0, 0, 1,
              0, 0, 0, 0,
              0, 0, 162, 0,
              0, 0, 162, 1,
              0, 161, 0, 1,
              0, 0, 0, 2,
              0, 1, 2, 0,
              0, 161, 0, 0)
    nonce = 35
    board = encode_board(cells=cells0, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=9,
                       to=14,
                       pass_move=True)
    assert rules.isValidMove(game_state, R, move)
    assert not rules.isValidMove(game_state, W, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells == cells1
    assert not next_move_is_red
    assert next_winner == 0


def test_red_can_jump_over_white_king(rules, game_id):
    #               0       1       2       3
    #      0  │███│ X │███│ X │███│   │███│   │ 3
    #      4  │   │███│   │███│   │███│   │███│ 7
    #      8  │███│   │███│   │███│   │███│   │ 11
    #      12 │   │███│   │███│   │███│ O │███│ 15
    #      16 │███│   │███│   │███│   │███│   │ 19
    #      20 │   │███│   │███│ o │███│   │███│ 23
    #      24 │███│   │███│ x │███│   │███│   │ 27
    #      28 │   │███│   │███│   │███│   │███│ 31
    #           28      29      30      31

    cells0 = [162, 162, 0, 0,
              0, 0, 0, 0,
              0, 0, 0, 0,
              0, 0, 0, 161,
              0, 0, 0, 0,
              0, 0, 1, 0,
              0, 2, 0, 0,
              0, 0, 0, 0]

    cells1 = (162, 162, 0, 0,
              0, 0, 0, 0,
              0, 0, 0, 0,
              0, 0, 0, 161,
              0, 0, 2, 0,
              0, 0, 0, 0,
              0, 0, 0, 0,
              0, 0, 0, 0)

    nonce = 47
    board = encode_board(cells=cells0, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=25,
                       to=18,
                       pass_move=False)
    assert rules.isValidMove(game_state, R, move)
    assert not rules.isValidMove(game_state, W, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells == cells1
    assert next_move_is_red
    assert next_winner == 0


def test_red_can_jump_again_over_white_king(rules, game_id):
    #               0       1       2       3
    #      0  │███│ o │███│   │███│   │███│   │ 3
    #      4  │ o │███│ o │███│ O │███│   │███│ 7
    #      8  │███│   │███│ . │███│   │███│ o │ 11
    #      12 │   │███│ O │███│   │███│ x │███│ 15
    #      16 │███│ x │███│   │███│   │███│   │ 19
    #      20 │ x │███│   │███│   │███│ x │███│ 23
    #      24 │███│   │███│ x │███│   │███│   │ 27
    #      28 │ x │███│ x │███│ x │███│   │███│ 31
    #           28      29      30      31

    cells0 = [1, 0, 0, 0,
              1, 1, 161, 0,
              0, 0, 0, 1,
              0, 161, 0, 2,
              2, 0, 0, 0,
              2, 0, 0, 2,
              0, 2, 0, 0,
              2, 2, 2, 0]

    cells1 = (1, 0, 0, 0,
              1, 1, 161, 0,
              0, 2, 0, 1,
              0, 0, 0, 2,
              0, 0, 0, 0,
              2, 0, 0, 2,
              0, 2, 0, 0,
              2, 2, 2, 0)

    nonce = 27
    board = encode_board(cells=cells0, red_moves=True)
    game_state = [game_id, nonce, board]

    move = encode_move(fr=16,
                       to=9,
                       pass_move=False)
    assert rules.isValidMove(game_state, R, move)
    assert not rules.isValidMove(game_state, W, move)

    next_game_id, next_nonce, next_game_state = rules.transition(game_state, R, move)
    assert next_game_id == game_id
    assert next_nonce == nonce + 1
    [next_cells, next_move_is_red, next_winner] = decode_abi(STATE_TYPES, next_game_state)
    assert next_cells == cells1
    assert next_move_is_red
    assert next_winner == 0


def mov(fr: int, to: int, pass_move: bool) -> Tuple[int, int, bool]:
    return fr, to, pass_move


def encode_move(fr: int, to: int, pass_move: bool) -> bytes:
    move = mov(fr, to, pass_move)
    return encode_abi(MOVE_TYPES, move)


def encode_board(cells: List[int], red_moves: bool, winner: int = 0) -> bytes:
    board = [cells, red_moves, winner]
    return encode_abi(STATE_TYPES, board)


def occupied_by_red(cell: int, cells: List[int]) -> bool:
    return cells[cell] % 16 == 2


def occupied_by_white(cell: int, cells: List[int]) -> bool:
    return cells[cell] % 16 == 1


def unoccupied(cell: int, cells: List[int]) -> bool:
    return cells[cell] == 0
