import pytest
from brownie import reverts, interface, Wei
from eth_abi import abi
from eth_account.messages import SignableMessage
from brownie.convert import to_bytes

from eth_account.messages import encode_structured_data
from eth_typing import ChecksumAddress
from brownie.network.account import PublicKeyAccount

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
    tx = arbiter.proposeGame(rules, {'value': 0, 'from': player_a.address})
    assert tx.return_value == 0
    game_rules, game_stake, game_started, game_finished = arbiter.games(0)
    assert game_rules == rules
    assert game_stake == 0
    assert not game_started
    assert not game_finished
    assert arbiter.getPlayers(0) == [player_a.address, ZERO_ADDRESS]

    tx = arbiter.proposeGame(rules, {'value': Wei("1 ether"), 'from': player_b.address})
    assert tx.return_value == 1
    game_rules, game_stake, game_started, game_finished = arbiter.games(1)
    assert game_rules == rules
    assert game_stake == "1 ether"
    assert not game_started
    assert not game_finished
    assert arbiter.getPlayers(1) == [player_b.address, ZERO_ADDRESS]


def test_accept_game(arbiter, rules, player_a, player_b):
    stake = Wei("0.1 ether")
    arbiter.proposeGame(rules, {'value': stake, 'from': player_a.address})
    with reverts("Arbiter: stake mismatch"):
        arbiter.acceptGame(0, {'from': player_b.address})
    arbiter.acceptGame(0, {'value': stake, 'from': player_b.address})
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
        tx = arbiter.proposeGame(rules, {'value': stake, 'from': player_a})
        game_id = tx.return_value
        arbiter.acceptGame(game_id, {'value': stake, 'from': player_b})
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


def test_is_valid_signed_move(arbiter, rules, start_game, player_a, player_b):
    # https://codesandbox.io/s/gamejutsu-moves-eip712-no-nested-types-p5fnzf?file=/src/index.js

    game_id = start_game(
        player_a.address,
        player_b.address,
        Wei('0.1 ether')
    )

    empty_board = abi.encode(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = abi.encode(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
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


def test_is_valid_signed_move_wrong_user(arbiter, rules, start_game, player_a, player_b, player_c):
    game_id = start_game(
        player_a.address,
        player_b.address,
        Wei('0.1 ether')
    )

    empty_board = abi.encode(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = abi.encode(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])

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

    empty_board = abi.encode(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = abi.encode(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    two_cross_board = abi.encode(STATE_TYPES, [[1, 1, 0, 0, 0, 0, 0, 0, 0], False, False])
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

    empty_board = abi.encode(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = abi.encode(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    two_cross_board = abi.encode(STATE_TYPES, [[1, 1, 0, 0, 0, 0, 0, 0, 0], False, False])
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

    empty_board = abi.encode(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = abi.encode(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    two_cross_board = abi.encode(STATE_TYPES, [[1, 2, 0, 0, 0, 0, 0, 0, 0], False, False])
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

    empty_board = abi.encode(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    one_cross_board = abi.encode(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    two_cross_board = abi.encode(STATE_TYPES, [[1, 2, 0, 0, 0, 0, 0, 0, 0], False, False])
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
