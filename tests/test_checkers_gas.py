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


@pytest.fixture(scope='module')
def rules(CheckersRules, dev):
    return interface.IGameJutsuRules(dev.deploy(CheckersRules))


@pytest.fixture
def gas_checker(GasChecker, dev):
    return GasChecker.deploy({'from': dev})


@pytest.fixture(scope='session')
def game_id():
    return "0x" + randbytes(8).hex()


STATE_TYPES = ["uint8[32]", "bool", "uint8"]
MOVE_TYPES = ["uint8", "uint8", "bool", "bool"]

W, R = 0, 1  # playerId


def test_red_moves_4_0(rules, game_id, gas_checker):
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
    move = encode_move(fr=4, to=0, is_jump=False, pass_move=True)
    assert rules.isValidMove(game_state, R, move)
    tx = gas_checker.callIsValidMove(rules, game_state, R, move)
    print(tx.info())
    assert tx.gas_used < 100000


#     Gas Used: 60203 / 12000000 (0.5%) unoptimized

def test_red_jumps_with_multiple_red_checkers_remaining(rules, game_id, gas_checker):
    #                  0       1       2       3
    #      0  00 │███│ o │███│ o │███│ o │███│ o │ 03 3
    #      4  04 │ x │███│ x │███│ . │███│ x │███│ 07 7
    #      8  08 │███│ x │███│ o │███│ x │███│ x │ 0B 11
    #      12 0С │ x │███│ x │███│ x │███│ x │███│ 0F 15
    #      16 10 │███│ x │███│ x │███│ x │███│ x │ 13 19
    #      20 14 │ x │███│ x │███│   │███│ x │███│ 17 23
    #      24 18 │███│ x │███│ x │███│ o │███│   │ 1B 27
    #      28 1С │ x │███│ x │███│ x │███│ x │███│ 1F 31
    #             1С      1D      1E      1F
    cells = [1, 1, 1, 1,
             2, 2, 0, 2,
             2, 1, 2, 2,
             2, 2, 2, 2,
             2, 2, 2, 2,
             2, 2, 0, 2,
             2, 2, 1, 0,
             2, 2, 2, 2]
    nonce = 0
    board = encode_board(cells=cells, red_moves=True, winner=0)
    game_state = [game_id, nonce, board]
    move = encode_move(fr=13, to=6, is_jump=True, pass_move=True)
    assert not rules.isValidMove(game_state, R, move)
    tx = gas_checker.callIsValidMove(rules, game_state, R, move)
    print(tx.info())
    assert tx.gas_used < 200000
    # _canJump refactored
    # Gas Used: 102731 / 12000000 (0.9%) unoptimized

    move = encode_move(fr=13, to=6, is_jump=True, pass_move=False)
    assert rules.isValidMove(game_state, R, move)
    tx = gas_checker.callIsValidMove(rules, game_state, R, move)
    print(tx.info())
    # Gas Used: 145828 / 12000000 (1.2%) unoptimized
    # _canJump refactored
    # Gas Used: 121919 / 12000000 (1.0%)
    # Gas Used: 122531 / 12000000 (1.0%)
    assert tx.gas_used < 200000


def encode_move(fr: int, to: int, is_jump: bool, pass_move: bool) -> bytes:
    move = mov(fr, to, is_jump, pass_move)
    return encode_abi(MOVE_TYPES, move)


def encode_board(cells: List[int], red_moves: bool, winner: int = 0) -> bytes:
    board = [cells, red_moves, winner]
    return encode_abi(STATE_TYPES, board)


def mov(fr: int, to: int, is_jump: bool, pass_move: bool) -> Tuple[int, int, bool, bool]:
    return fr, to, is_jump, pass_move
