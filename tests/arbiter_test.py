#   ________                           ____.       __
#  /  _____/_____    _____   ____     |    |__ ___/  |_  ________ __
# /   \  ___\__  \  /     \_/ __ \    |    |  |  \   __\/  ___/  |  \
# \    \_\  \/ __ \|  Y Y  \  ___//\__|    |  |  /|  |  \___ \|  |  /
#  \______  (____  /__|_|  /\___  >________|____/ |__| /____  >____/
#         \/     \/      \/     \/                          \/
# https://gamejutsu.app
# ETHOnline2022 submission by ChainHackers
__authors__ = ["Gene A. Tsvigun", "Vic G. Larson"]
__license__ = "MIT"

import pytest
from brownie import reverts, interface, Wei
from eth_abi import encode_abi
from eth_account.messages import SignableMessage
from brownie.convert import to_bytes

from eth_account.messages import encode_structured_data
from eth_typing import ChecksumAddress
from brownie.network.account import PublicKeyAccount
from brownie import chain

ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'


@pytest.fixture(scope='module')
def rules(TicTacToeRules, dev):
    return interface.IGameJutsuRules(dev.deploy(TicTacToeRules))


@pytest.fixture
def arbiter(Arbiter, dev):
    return dev.deploy(Arbiter)


@pytest.fixture(scope="module")
def player_a(create_funded_eth_account):
    return create_funded_eth_account()


@pytest.fixture(scope="module")
def player_b(create_funded_eth_account):
    return create_funded_eth_account()


@pytest.fixture(scope="module")
def player_c(create_funded_eth_account):
    return create_funded_eth_account()


def balance(account):
    return PublicKeyAccount(account.address).balance()


STATE_TYPES = ["uint8[9]", "bool", "bool"]


def test_propose_game(arbiter, rules, player_a, player_b):
    tx = arbiter.proposeGame(rules, [], {'value': 0, 'from': player_a.address})
    assert tx.events['GameProposed']['gameId'] == 0
    game_rules, game_stake, game_started, game_finished = arbiter.games(0)
    assert game_rules == rules
    assert game_stake == 0
    assert not game_started
    assert not game_finished
    assert arbiter.getPlayers(0) == [player_a.address, ZERO_ADDRESS]

    tx = arbiter.proposeGame(rules, [], {'value': Wei("1 ether"), 'from': player_b.address})
    assert tx.events['GameProposed']['gameId'] == 1
    game_rules, game_stake, game_started, game_finished = arbiter.games(1)
    assert game_rules == rules
    assert game_stake == "1 ether"
    assert not game_started
    assert not game_finished
    assert arbiter.getPlayers(1) == [player_b.address, ZERO_ADDRESS]


def test_accept_game(arbiter, rules, player_a, player_b):
    stake = Wei("0.1 ether")
    tx = arbiter.proposeGame(rules, [], {'value': stake, 'from': player_a.address})
    game_id = tx.events['GameProposed']['gameId']
    with reverts("Arbiter: stake mismatch"):
        arbiter.acceptGame(game_id, [], {'from': player_b.address})
    arbiter.acceptGame(game_id, [], {'value': stake, 'from': player_b.address})
    game_rules, game_stake, game_started, game_finished = arbiter.games(0)
    assert game_rules == rules
    assert game_stake == "0.2 ether"
    assert game_started
    assert not game_finished
    assert arbiter.getPlayers(0) == [player_a.address, player_b.address]


@pytest.fixture
def start_game(arbiter, rules):
    def start_it(player_a, player_b, stake):
        stake_wei = Wei(f"{stake} ether")
        tx = arbiter.proposeGame(rules, [], {'value': stake, 'from': player_a})
        game_id = tx.events['GameProposed']['gameId']
        arbiter.acceptGame(game_id, [], {'value': stake, 'from': player_b})
        return game_id

    return start_it


def encode_move(
        game_id: int,
        nonce: int,
        player: ChecksumAddress,
        old_state: bytes,
        new_state: bytes,
        move: bytes) -> SignableMessage:
    data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
                {"name": "salt", "type": "bytes32"},
            ],
            "GameMove": [
                {"name": "gameId", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "player", "type": "address"},
                {"name": "oldState", "type": "bytes"},
                {"name": "newState", "type": "bytes"},
                {"name": "move", "type": "bytes"}
            ],
        },
        "domain": {
            "name": "GameJutsu",
            "version": "0.1",
            "chainId": 137,
            "verifyingContract": "0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC",
            "salt": to_bytes("0x920dfa98b3727bbfe860dd7341801f2e2a55cd7f637dea958edfc5df56c35e4d", "bytes32"),
        },
        "primaryType": "GameMove",
        "message": {
            "gameId": game_id,
            "nonce": nonce,
            "player": player,
            "oldState": old_state,
            "newState": new_state,
            "move": move
        },
    }
    return encode_structured_data(data)

def test_is_valid_finish_signed_move(arbiter, rules, start_game, player_a, player_b):
    game_id = start_game(
        player_a.address,
        player_b.address,
        Wei('0.1 ether')
    )

    almost_finished_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 2, 0, 0, 0, 0], False, False])
    finished_board = encode_abi(STATE_TYPES, [[1, 1, 1, 2, 2, 0, 0, 0, 0], True, False])
    nonce = 4
    valid_move_data = to_bytes("0x02")

    valid_move = [
        game_id,
        nonce,
        player_a.address,
        almost_finished_board,
        finished_board,
        valid_move_data
    ]
  
    signature_a = player_a.sign_message(encode_move(*valid_move)).signature
    valid_signed_game_move = [
        valid_move,
        [signature_a]
    ]

    assert arbiter.isValidGameMove(valid_move)

    with reverts():
        arbiter.disputeMove(valid_signed_game_move, {'from': player_b.address})

def test_is_valid_signed_move(arbiter, rules, start_game, player_a, player_b):
    # https://codesandbox.io/s/gamejutsu-moves-eip712-no-nested-types-p5fnzf?file=/src/index.js

    game_id = start_game(
        player_a.address,
        player_b.address,
        Wei('0.1 ether')
    )

    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = encode_abi(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    valid_move_data = to_bytes("0x00")
    invalid_move_data = to_bytes("0x01")

    valid_move = [
        game_id,
        nonce,
        player_a.address,
        empty_board,
        one_cross_board,
        valid_move_data
    ]
    invalid_move = [
        game_id,
        nonce,
        player_a.address,
        empty_board,
        one_cross_board,
        invalid_move_data
    ]

    signature_a = player_a.sign_message(encode_move(*valid_move)).signature
    valid_signed_game_move = [
        valid_move,
        [signature_a]
    ]
    with reverts():
        arbiter.disputeMove(valid_signed_game_move, {'from': player_b.address})

    signature_a = player_a.sign_message(encode_move(*invalid_move)).signature
    invalid_signed_game_move = [
        invalid_move,
        [signature_a]
    ]
    tx = arbiter.disputeMove(invalid_signed_game_move, {'from': player_b.address})
    rules, stake, started, finished = arbiter.games(game_id)
    assert finished
    assert 'GameFinished' in tx.events
    assert tx.events['GameFinished']['winner'] == player_b.address


def test_is_valid_signed_move_session_address(arbiter, rules, player_a, player_b, create_eth_account):
    # https://codesandbox.io/s/gamejutsu-moves-eip712-no-nested-types-p5fnzf?file=/src/index.js
    stake = Wei('0.1 ether')
    a_session = create_eth_account()
    tx = arbiter.proposeGame(rules, [a_session.address], {'value': stake, 'from': player_a.address})
    game_id = tx.events['GameProposed']['gameId']

    b_session = create_eth_account()
    arbiter.acceptGame(game_id, [b_session.address], {'value': stake, 'from': player_b.address})

    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = encode_abi(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    valid_move_data = to_bytes("0x00")
    invalid_move_data = to_bytes("0x01")

    valid_move = [
        game_id,
        nonce,
        player_a.address,
        empty_board,
        one_cross_board,
        valid_move_data
    ]
    assert arbiter.isValidGameMove(valid_move)

    invalid_move = [
        game_id,
        nonce,
        player_a.address,
        empty_board,
        one_cross_board,
        invalid_move_data
    ]
    assert not arbiter.isValidGameMove(invalid_move)

    signature_a = a_session.sign_message(encode_move(*valid_move)).signature
    valid_signed_game_move = [
        valid_move,
        [signature_a]
    ]
    assert arbiter.isValidSignedMove(valid_signed_game_move)

    with reverts():
        arbiter.disputeMove(valid_signed_game_move, {'from': player_b.address})

    signature_a = a_session.sign_message(encode_move(*invalid_move)).signature
    invalid_signed_game_move = [
        invalid_move,
        [signature_a]
    ]
    assert not arbiter.isValidSignedMove(invalid_signed_game_move)

    tx = arbiter.disputeMove(invalid_signed_game_move, {'from': player_b.address})
    rules, stake, started, finished = arbiter.games(game_id)
    assert finished
    assert 'GameFinished' in tx.events
    assert tx.events['GameFinished']['winner'] == player_b.address


def test_is_valid_signed_move_wrong_user(arbiter, rules, start_game, player_a, player_b, player_c):
    game_id = start_game(
        player_a.address,
        player_b.address,
        Wei('0.1 ether')
    )

    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = encode_abi(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])

    invalid_move_data = to_bytes("0x01")

    invalid_move = [
        game_id,
        nonce,
        player_a.address,
        empty_board,
        one_cross_board,
        invalid_move_data
    ]

    signature_c = player_c.sign_message(encode_move(*invalid_move)).signature
    invalid_signed_game_move = [
        invalid_move,
        [signature_c]
    ]
    with reverts():
        tx = arbiter.disputeMove(invalid_signed_game_move, {'from': player_b.address})


def test_is_valid_signed_move_x_twice(arbiter, rules, start_game, player_a, player_b):
    game_id = start_game(
        player_a.address,
        player_b.address,
        Wei('0.1 ether')
    )

    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = encode_abi(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    two_cross_board = encode_abi(STATE_TYPES, [[1, 1, 0, 0, 0, 0, 0, 0, 0], False, False])
    valid_move_data = to_bytes("0x00")
    invalid_move_data = to_bytes("0x01")

    valid_move = [
        game_id,
        nonce,
        player_a.address,
        empty_board,
        one_cross_board,
        valid_move_data
    ]
    invalid_move = [
        game_id,
        nonce + 1,
        player_a.address,
        one_cross_board,
        two_cross_board,
        invalid_move_data
    ]

    signature_a = player_a.sign_message(encode_move(*valid_move)).signature
    valid_signed_game_move = [
        valid_move,
        [signature_a]
    ]
    with reverts():
        arbiter.disputeMove(valid_signed_game_move, {'from': player_b.address})

    signature_a = player_a.sign_message(encode_move(*invalid_move)).signature
    invalid_signed_game_move = [
        invalid_move,
        [signature_a]
    ]
    tx = arbiter.disputeMove(invalid_signed_game_move, {'from': player_b.address})
    rules, stake, started, finished = arbiter.games(game_id)
    assert finished
    assert 'GameFinished' in tx.events
    assert tx.events['GameFinished']['winner'] == player_b.address


# TODO implement disputeMove with multiple moves as arguments
@pytest.mark.xfail
def test_is_valid_signed_move_x_moves_twice_with_same_nonce(arbiter, rules, start_game, player_a, player_b):
    game_id = start_game(
        player_a=player_a.address,
        player_b=player_b.address,
        stake=Wei('0.1 ether')
    )

    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = encode_abi(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    two_cross_board = encode_abi(STATE_TYPES, [[1, 1, 0, 0, 0, 0, 0, 0, 0], False, False])
    move_to_cell_0_data = to_bytes("0x00")
    move_to_cell_1_data = to_bytes("0x01")

    player_a_moves_to_cell_0 = [
        game_id,
        nonce,
        player_a.address,
        empty_board,
        one_cross_board,
        move_to_cell_0_data
    ]
    player_a_moves_to_cell_1 = [
        game_id,
        nonce,
        player_a.address,
        one_cross_board,
        two_cross_board,
        move_to_cell_1_data
    ]

    signature_a = player_a.sign_message(encode_move(*player_a_moves_to_cell_0)).signature
    valid_signed_game_move = [
        player_a_moves_to_cell_0,
        [signature_a]
    ]
    with reverts():
        arbiter.disputeMove(valid_signed_game_move, {'from': player_b.address})

    signature_a = player_a.sign_message(encode_move(*player_a_moves_to_cell_1)).signature
    invalid_signed_game_move = [
        player_a_moves_to_cell_1,
        [signature_a]
    ]
    tx = arbiter.disputeMove(invalid_signed_game_move, {'from': player_b.address})
    rules, stake, started, finished = arbiter.games(game_id)
    assert finished
    assert 'GameFinished' in tx.events
    assert tx.events['GameFinished']['winner'] == player_b.address


def test_is_valid_signed_move_x_cant_place_o(arbiter, rules, start_game, player_a, player_b):
    game_id = start_game(
        player_a.address,
        player_b.address,
        Wei('0.1 ether')
    )

    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = encode_abi(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    two_cross_board = encode_abi(STATE_TYPES, [[1, 2, 0, 0, 0, 0, 0, 0, 0], False, False])
    valid_move_data = to_bytes("0x00")
    invalid_move_data = to_bytes("0x01")

    valid_move = [
        game_id,
        nonce,
        player_a.address,
        empty_board,
        one_cross_board,
        valid_move_data
    ]
    invalid_move = [
        game_id,
        nonce + 1,
        player_a.address,
        one_cross_board,
        two_cross_board,
        invalid_move_data
    ]

    signature_a = player_a.sign_message(encode_move(*valid_move)).signature
    valid_signed_game_move = [
        valid_move,
        [signature_a]
    ]
    with reverts():
        arbiter.disputeMove(valid_signed_game_move, {'from': player_b.address})

    signature_a = player_a.sign_message(encode_move(*invalid_move)).signature
    invalid_signed_game_move = [
        invalid_move,
        [signature_a]
    ]
    tx = arbiter.disputeMove(invalid_signed_game_move, {'from': player_b.address})
    rules, stake, started, finished = arbiter.games(game_id)
    assert finished
    assert 'GameFinished' in tx.events
    assert tx.events['GameFinished']['winner'] == player_b.address


def test_is_valid_signed_players_moves_in_right_sequence(arbiter, rules, start_game, player_a, player_b):
    game_id = start_game(
        player_a.address,
        player_b.address,
        Wei('0.1 ether')
    )

    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = encode_abi(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    two_cross_board = encode_abi(STATE_TYPES, [[1, 2, 0, 0, 0, 0, 0, 0, 0], False, False])
    valid_move_data = to_bytes("0x00")
    valid_move_data2 = to_bytes("0x01")

    valid_move = [
        game_id,
        nonce,
        player_a.address,
        empty_board,
        one_cross_board,
        valid_move_data
    ]
    valid_move2 = [
        game_id,
        nonce + 1,
        player_a.address,
        one_cross_board,
        two_cross_board,
        valid_move_data2
    ]

    signature_a = player_a.sign_message(encode_move(*valid_move)).signature
    valid_signed_game_move = [
        valid_move,
        [signature_a]
    ]
    with reverts():
        arbiter.disputeMove(valid_signed_game_move, {'from': player_b.address})

    signature_b = player_b.sign_message(encode_move(*valid_move2)).signature
    valid_signed_game_move2 = [
        valid_move2,
        [signature_b]
    ]

    with reverts():
        arbiter.disputeMove(valid_signed_game_move2, {'from': player_a.address})


def test_finish_game(arbiter, rules, start_game, player_a, player_b, create_eth_account):
    stake = Wei('0.1 ether')
    a_session = create_eth_account()
    b_session = create_eth_account()
    tx = arbiter.proposeGame(rules, [a_session.address], {'value': stake, 'from': player_a.address})
    game_id = tx.events['GameProposed']['gameId']
    assert 'GameProposed' in tx.events
    assert tx.events['GameProposed']['gameId'] == game_id

    o_about_to_play_in_the_center_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 0, 0, 0, 0, 0], False, False])
    o_center_move_data = to_bytes("0x04")

    # ╭───┬───┬───╮
    # │ X │ X │ . │
    # ├───┼───┼───┤
    # │ 0 │ 0 │   │
    # ├───┼───┼───┤
    # │   │   │   │
    # ╰───┴───┴───╯

    x_almost_won_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 2, 0, 0, 0, 0], False, False])
    nonce = 4
    x_won_board = encode_abi(STATE_TYPES, [[1, 1, 1, 2, 2, 0, 0, 0, 0], True, False])
    x_winning_move_data = to_bytes("0x02")
    x_non_winning_move_data = to_bytes("0x08")
    x_not_won_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 2, 0, 0, 0, 1], False, False])

    o_center_move = [
        game_id,
        3,
        player_b.address,
        o_about_to_play_in_the_center_board,
        x_almost_won_board,
        o_center_move_data
    ]
    x_winning_move = [
        game_id,
        nonce,
        player_a.address,
        x_almost_won_board,
        x_won_board,
        x_winning_move_data
    ]
    x_non_winning_move = [
        game_id,
        nonce,
        player_a.address,
        x_almost_won_board,
        x_not_won_board,
        x_non_winning_move_data
    ]

    encoded_o_center_move = encode_move(*o_center_move)
    signature_a = a_session.sign_message(encoded_o_center_move).signature
    signature_b = b_session.sign_message(encoded_o_center_move).signature
    signed_by_both_players_move = [
        o_center_move,
        [signature_a, signature_b]
    ]

    signed_x_winning_move = [
        x_winning_move,
        [a_session.sign_message(encode_move(*x_winning_move)).signature]
    ]
    signed_x_non_winning_move = [
        x_non_winning_move,
        [player_a.sign_message(encode_move(*x_non_winning_move)).signature]
    ]

    with reverts():
        arbiter.finishGame(
            [signed_by_both_players_move, signed_x_winning_move],
            {'from': player_a.address}
        )

    arbiter.acceptGame(game_id, [b_session.address], {'value': stake, 'from': player_b.address})
    rules, stake, started, finished = arbiter.games(game_id)
    assert started
    assert not finished

    with reverts():
        arbiter.finishGame(
            [signed_by_both_players_move, signed_x_non_winning_move],
            {'from': player_a.address}
        )

    tx = arbiter.finishGame(
        [signed_by_both_players_move, signed_x_winning_move],
        {'from': player_a.address}
    )
    assert 'GameFinished' in tx.events
    e = tx.events['GameFinished']
    assert e['gameId'] == game_id
    assert e['winner'] == player_a.address
    assert e['loser'] == player_b.address
    assert not e['isDraw']
    assert 'PlayerDisqualified' not in tx.events

    rules, stake, started, finished = arbiter.games(game_id)
    assert finished


def test_resign(arbiter, rules, start_game, player_a, player_b):
    game_id = start_game(
        player_a.address,
        player_b.address,
        Wei('0.1 ether')
    )

    tx = arbiter.resign(game_id, {'from': player_a.address})
    assert 'PlayerResigned' in tx.events
    e = tx.events['PlayerResigned']
    assert e['gameId'] == game_id
    assert e['player'] == player_a.address

    rules, stake, started, finished = arbiter.games(game_id)
    assert finished


def test_timeout(arbiter, rules, start_game, player_a, player_b):
    game_id = start_game(
        player_a.address,
        player_b.address,
        Wei('0.1 ether')
    )

    # ╭───┬───┬───╮
    # │ X │   │   │
    # ├───┼───┼───┤
    # │ 0 │   │   │
    # ├───┼───┼───┤
    # │   │   │   │
    # ╰───┴───┴───╯

    two_moves_board = encode_abi(STATE_TYPES, [[1, 0, 0, 2, 0, 0, 0, 0, 0], False, False])
    x_1_move_data = to_bytes("0x01")

    # ╭───┬───┬───╮
    # │ X │ X │   │
    # ├───┼───┼───┤
    # │ 0 │   │   │
    # ├───┼───┼───┤
    # │   │   │   │
    # ╰───┴───┴───╯

    three_moves_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 0, 0, 0, 0, 0], False, False])
    o_center_move_data = to_bytes("0x04")

    # ╭───┬───┬───╮
    # │ X │ X │   │
    # ├───┼───┼───┤
    # │ 0 │ 0 │   │
    # ├───┼───┼───┤
    # │   │   │   │
    # ╰───┴───┴───╯

    four_moves_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 2, 0, 0, 0, 0], False, False])

    x_1_move = [
        game_id,
        2,
        player_a.address,
        two_moves_board,
        three_moves_board,
        x_1_move_data,
    ]
    o_center_move = [
        game_id,
        3,
        player_b.address,
        three_moves_board,
        four_moves_board,
        o_center_move_data,
    ]

    encoded_x_1_move = encode_move(*x_1_move)
    signed_x_1_move = [
        x_1_move,
        [
            player_a.sign_message(encoded_x_1_move).signature,
            player_b.sign_message(encoded_x_1_move).signature
        ]
    ]

    encoded_o_center_move = encode_move(*o_center_move)
    signed_o_center_move = [
        o_center_move,
        [
            player_b.sign_message(encoded_o_center_move).signature,
            player_a.sign_message(encoded_o_center_move).signature
        ]
    ]

    with reverts():
        arbiter.initTimeout([signed_x_1_move, signed_o_center_move],
                            {'from': player_b.address})

    tx = arbiter.initTimeout([signed_x_1_move, signed_o_center_move],
                             {'value': arbiter.DEFAULT_TIMEOUT_STAKE(), 'from': player_b.address})
    ts = chain.time()
    assert 'TimeoutStarted' in tx.events
    e = tx.events['TimeoutStarted']
    assert e['gameId'] == game_id
    assert e['player'] == player_b.address
    assert e['nonce'] == 3
    expected_timeout = ts + arbiter.TIMEOUT()
    # AssertionError: assert 1664030008 == 1664030008 ± 3.0e+00
    # Brownie quirks workaround
    assert expected_timeout <= e['timeout'] <= expected_timeout + 5
    assert arbiter.timeouts(game_id)[0] == ts

    # ╭───┬───┬───╮
    # │ X │ X │   │
    # ├───┼───┼───┤
    # │ 0 │ 0 │   │
    # ├───┼───┼───┤
    # │   │   │ X │
    # ╰───┴───┴───╯

    five_moves_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 2, 0, 0, 0, 1], False, False])
    x_8_move_data = to_bytes("0x08")

    # ╭───┬───┬───╮
    # │ X │ X │   │
    # ├───┼───┼───┤
    # │ 0 │ 0 │   │
    # ├───┼───┼───┤
    # │   │ 0 │ X │
    # ╰───┴───┴───╯
    six_moves_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 2, 0, 0, 2, 1], False, False])
    o_7_move_data = to_bytes("0x07")

    x_8_move = [
        game_id,
        4,
        player_a.address,
        four_moves_board,
        five_moves_board,
        x_8_move_data,
    ]
    assert (arbiter.isValidGameMove(x_8_move))
    encoded_x_8_move = encode_move(*x_8_move)
    signed_x_8_move = [
        x_8_move,
        [
            player_a.sign_message(encoded_x_8_move).signature,
        ]
    ]
    assert (arbiter.isValidSignedMove(signed_x_8_move))

    o_7_move = [
        game_id,
        5,
        player_b.address,
        five_moves_board,
        six_moves_board,
        o_7_move_data
    ]
    assert (arbiter.isValidGameMove(o_7_move))
    encoded_o_7_move = encode_move(*o_7_move)
    signed_o_7_move = [
        o_7_move,
        [
            player_b.sign_message(encoded_o_7_move).signature,
        ]
    ]
    assert (arbiter.isValidSignedMove(signed_o_7_move))

    with reverts():
        arbiter.resolveTimeout(signed_o_7_move, {'from': player_b.address})
    with reverts():
        arbiter.resolveTimeout(signed_o_7_move, {'from': player_a.address})

    balance_b_before_timeout_resolution = balance(player_b)
    tx = arbiter.resolveTimeout(signed_x_8_move, {'from': player_a.address})
    assert 'TimeoutResolved' in tx.events
    e = tx.events['TimeoutResolved']
    assert e['gameId'] == game_id
    assert e['player'] == player_a.address
    assert e['nonce'] == 4
    assert balance(player_b) == balance_b_before_timeout_resolution + arbiter.DEFAULT_TIMEOUT_STAKE()


def test_finalize_timeout(arbiter, rules, start_game, player_a, player_b):
    stake = Wei('0.1 ether')
    game_id = start_game(
        player_a.address,
        player_b.address,
        stake
    )

    # ╭───┬───┬───╮
    # │ X │   │   │
    # ├───┼───┼───┤
    # │ 0 │   │   │
    # ├───┼───┼───┤
    # │   │   │   │
    # ╰───┴───┴───╯

    two_moves_board = encode_abi(STATE_TYPES, [[1, 0, 0, 2, 0, 0, 0, 0, 0], False, False])
    x_1_move_data = to_bytes("0x01")

    # ╭───┬───┬───╮
    # │ X │ X │   │
    # ├───┼───┼───┤
    # │ 0 │   │   │
    # ├───┼───┼───┤
    # │   │   │   │
    # ╰───┴───┴───╯

    three_moves_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 0, 0, 0, 0, 0], False, False])
    o_center_move_data = to_bytes("0x04")

    # ╭───┬───┬───╮
    # │ X │ X │   │
    # ├───┼───┼───┤
    # │ 0 │ 0 │   │
    # ├───┼───┼───┤
    # │   │   │   │
    # ╰───┴───┴───╯

    four_moves_board = encode_abi(STATE_TYPES, [[1, 1, 0, 2, 2, 0, 0, 0, 0], False, False])

    x_1_move = [
        game_id,
        2,
        player_a.address,
        two_moves_board,
        three_moves_board,
        x_1_move_data,
    ]

    o_center_move = [
        game_id,
        3,
        player_b.address,
        three_moves_board,
        four_moves_board,
        o_center_move_data,
    ]

    encoded_x_1_move = encode_move(*x_1_move)
    signed_x_1_move = [
        x_1_move,
        [
            player_a.sign_message(encoded_x_1_move).signature,
            player_b.sign_message(encoded_x_1_move).signature
        ]
    ]

    encoded_o_center_move = encode_move(*o_center_move)
    signed_o_center_move = [
        o_center_move,
        [
            player_b.sign_message(encoded_o_center_move).signature,
        ]
    ]

    arbiter.initTimeout([signed_x_1_move, signed_o_center_move],
                        {'value': arbiter.DEFAULT_TIMEOUT_STAKE(), 'from': player_b.address})

    with reverts():
        arbiter.finalizeTimeout(game_id, {'from': player_b.address})

    with reverts():
        arbiter.finalizeTimeout(game_id, {'from': player_a.address})

    chain.sleep(arbiter.DEFAULT_TIMEOUT() + 1)

    b_balance_before_pre_finalize_timeout = balance(player_b)
    tx = arbiter.finalizeTimeout(game_id, {'from': player_b.address})
    assert balance(player_b) == arbiter.DEFAULT_TIMEOUT_STAKE() + b_balance_before_pre_finalize_timeout + 2 * stake
    assert 'GameFinished' in tx.events
    e = tx.events['GameFinished']
    assert e['gameId'] == game_id
    assert e['winner'] == player_b.address
    assert e['loser'] == player_a.address
    assert not e['isDraw']
