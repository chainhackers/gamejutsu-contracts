import pytest
from brownie import reverts, interface, Wei
from eth_abi import encode_abi, decode_abi

ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'


@pytest.fixture(scope='module')
def rules(TicTacToeRules, dev):
    return dev.deploy(TicTacToeRules)


@pytest.fixture
def arbiter(Arbiter, dev):
    return dev.deploy(Arbiter)


STATE_TYPES = ["uint8[9]", "bool", "bool"]


def test_propose_game(arbiter, rules, player_a, player_b):
    tx = arbiter.proposeGame(rules, {'value': 0, 'from': player_a})
    assert tx.return_value == 0
    game_rules, game_stake, game_started, game_finished = arbiter.games(0)
    assert game_rules == rules
    assert game_stake == 0
    assert not game_started
    assert not game_finished
    assert arbiter.getPlayers(0) == [player_a, ZERO_ADDRESS]

    tx = arbiter.proposeGame(rules, {'value': Wei("1 ether"), 'from': player_b})
    assert tx.return_value == 1
    game_rules, game_stake, game_started, game_finished = arbiter.games(1)
    assert game_rules == rules
    assert game_stake == "1 ether"
    assert not game_started
    assert not game_finished
    assert arbiter.getPlayers(1) == [player_b, ZERO_ADDRESS]


def test_accept_game(arbiter, rules, player_a, player_b):
    stake = Wei("0.1 ether")
    arbiter.proposeGame(rules, {'value': stake, 'from': player_a})
    with reverts("Arbiter: stake mismatch"):
        arbiter.acceptGame(0, {'from': player_b})
    arbiter.acceptGame(0, {'value': stake, 'from': player_b})
    game_rules, game_stake, game_started, game_finished = arbiter.games(0)
    assert game_rules == rules
    assert game_stake == "0.2 ether"
    assert game_started
    assert not game_finished
    assert arbiter.getPlayers(0) == [player_a, player_b]


@pytest.fixture
def start_game(arbiter, rules):
    def start_it(a, b, stake):
        stake_wei = Wei(f"{stake} ether")
        tx = arbiter.proposeGame(rules, {'value': stake, 'from': a})
        game_id = tx.return_value
        arbiter.acceptGame(game_id, {'value': stake, 'from': b})
        return game_id

    return start_it


def test_is_valid_signed_move(arbiter, rules, player_a, player_b, start_game):
    game_id = start_game(player_a, player_b, Wei('0.1 ether'))
