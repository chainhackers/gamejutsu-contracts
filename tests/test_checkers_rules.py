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
from brownie import reverts, interface
from eth_abi import encode_abi
from random import randbytes

from brownie.test import given, strategy as st
from brownie.test import strategies


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
    to_cell=st('uint8', min_value=1, max_value=32)
)
def test_is_valid_move(rules, game_id, empty_cells, from_cell, to_cell):
    empty_board = [empty_cells, True, 0]
    empty_board_encoded = encode_abi(STATE_TYPES, empty_board)
    nonce = 0
    game_state = [game_id, nonce, empty_board_encoded]

    move = [from_cell, to_cell, False, False]
    move_encoded = encode_abi(MOVE_TYPES, move)
    assert not rules.isValidMove(game_state, R, move_encoded)
    assert not rules.isValidMove(game_state, W, move_encoded)
