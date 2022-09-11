import pytest
from brownie import reverts, interface, config, project, accounts, convert, Wei
from eth_abi import encode_abi, decode_abi
from eth_abi.packed import encode_abi_packed
from eth_account.messages import encode_defunct
from random import randbytes
from brownie.convert import to_bytes
# from eth_utils import keccak
# from eth_hash.auto import keccak as keccak_256

from eth_account import Account
from eth_account.messages import encode_structured_data
from hexbytes import HexBytes
from eth_utils import keccak

# from eip712.messages import EIP712Message, EIP712Type

ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'


@pytest.fixture(scope='module')
def rules(TicTacToeRules, dev):
    return dev.deploy(TicTacToeRules)


@pytest.fixture
def arbiter(Arbiter, dev):
    return dev.deploy(Arbiter)


@pytest.fixture(scope="module")
def player_a(accounts):
    acc = accounts.add()
    accounts[0].transfer(acc, "1 ether")
    return acc


@pytest.fixture(scope="module")
def player_b(accounts):
    acc_b = accounts.add()
    print(f"player_b: {acc_b}")
    print(f"player_b_balance: {acc_b.balance()}")
    accounts[1].transfer(acc_b, "1 ether")
    print(acc_b.balance())
    print(f"player_b_balance: {acc_b.balance()}")
    return acc_b


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
    print(player_a.balance())
    print(player_b.balance())
    player_a.transfer(player_b, "0.5 ether")
    print(player_a.balance())
    print(player_b.balance())
    print("--------------------------------------------")
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


# >>> local = accounts.add(private_key="0x416b8a7d9290502f5661da81f0cf43893e3d19cb9aea3c426cfb36e8186e9c09")
# >>> class TestSubType(EIP712Type):
# ...     inner: "uint256"
# ...
# >>> class TestMessage(EIP712Message):
# ...     _name_: "string" = "Brownie Test Message"
# ...     outer: "uint256"
# ...     sub: TestSubType
# ...
# >>> msg = TestMessage(outer=1, sub=TestSubType(inner=2))
# >>> signed = local.sign_message(msg)

def test_is_valid_signed_move(arbiter, rules, start_game):
    # https://codesandbox.io/s/gamejutsu-moves-eip712-no-nested-types-p5fnzf?file=/src/index.js
    signer = Account.create()
    player_b = Account.create()
    accounts[0].transfer(signer.address, "1 ether")
    accounts[1].transfer(player_b.address, "1 ether")
    game_id = start_game(signer.address, player_b.address, Wei('0.1 ether'))

    empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    nonce = 0
    # game_state = [game_id, nonce, empty_board]

    one_cross_board = encode_abi(STATE_TYPES, [[1, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
    # new_game_state = [game_id, nonce, one_cross_board]

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
            "player": signer.address,
            "oldState": empty_board,
            "newState": one_cross_board,
            "move": to_bytes("0x02")
        },
    }
    game_move = encode_structured_data(data)
    unencoded_game_move  = [game_id, nonce, signer.address, empty_board, one_cross_board, to_bytes("0x02")]
    print(f"game_move encoded: {game_move}")
    signature = signer.sign_message(game_move).signature
    print(f"signature: {signature.hex()}")
    signed_game_move = [   [game_id, nonce, signer.address, empty_board, one_cross_board, to_bytes("0x02")], [signature]]
    recovered_address = arbiter.recoverAddress(unencoded_game_move, signature)
    print(f"address: {signer.address}")
    print(f"unencoded address: {unencoded_game_move[2]}")
    print(f"sent address: {arbiter.getPlayerFromSignedGameMove}")
    print(f"recovered_address: {recovered_address}")
    print(f"players addresses: {arbiter.getPlayers(game_id)}")
    print("--------------------------------------------")
    arbiter.disputeMove(signed_game_move, {'from': signer.address})

    # # GameState: [
    # #       { name: "gameId", type: "uint256" },
    # #       { name: "nonce", type: "uint256" },
    # #       { name: "state", type: "bytes" }
    # #     ],
    # class GameState(EIP712Type):
    #     gameId: "uint256"
    #     nonce: "uint256"
    #     state: "bytes"
    #
    # class GameMove(EIP712Message):
    #     _name_: "string" = "Brownie Test Message"
    #     oldState: "GameState"
    #     newState: "GameState"
    #     player: "address"
    #     move: "bytes"
    #
    # msg = GameMove(
    #     oldState=GameState(
    #         gameId=game_id,
    #         nonce=0,
    #         state=empty_board),
    #     newState=GameState(
    #         gameId=game_id,
    #         nonce=1,
    #         state=one_cross_board),
    #     player=player_a.address,
    #     move=to_bytes("0x00", "bytes"))
    # signature_a = player_a.sign_message(msg)
    # signature_b = player_b.sign_message(msg)
    # print(signature_a)
    # print(signature_b)


#     signature_a = sign_move(player_a, game_state, new_game_state, 0)
#     signature_b = sign_move(player_b, game_state, new_game_state, 0)
#     assert arbiter.isValidSignedMove(
#         game_state,
#         new_game_state,
#         0,
#         [signature_a, signature_b])
# https://github.com/yearn/yearn-vaults/blob/67cf46f3/tests/conftest.py#L144-L190

#     for i in range(9):
#         assert rules.isValidMove(game_state, convert.to_bytes(i)) is True
#
#     cross_wins = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], True, False])
#     game_state = [game_id, nonce, cross_wins]
#     for i in range(9):
#         assert rules.isValidMove(game_state, convert.to_bytes(i)) is False
#
#     nought_wins = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, True])
#     game_state = [game_id, nonce, nought_wins]
#     for i in range(9):
#         assert rules.isValidMove(game_state, convert.to_bytes(i)) is False
#
#     # X1 → O5 → X9 → O3 → X7
#     # X  _  O
#     # _  O  _
#     # X  _  X
#
#     board = encode_abi(STATE_TYPES, [[1, 0, 2, 0, 2, 0, 1, 0, 1], False, False])
#     nonce = 5
#     game_state = [game_id, nonce, board]
#     assert rules.isValidMove(game_state, convert.to_bytes(0)) is False
#     assert rules.isValidMove(game_state, convert.to_bytes(1)) is True
#     assert rules.isValidMove(game_state, convert.to_bytes(2)) is False
#     assert rules.isValidMove(game_state, convert.to_bytes(3)) is True
#     assert rules.isValidMove(game_state, convert.to_bytes(4)) is False
#     assert rules.isValidMove(game_state, convert.to_bytes(5)) is True
#     assert rules.isValidMove(game_state, convert.to_bytes(6)) is False
#     assert rules.isValidMove(game_state, convert.to_bytes(7)) is True
#     assert rules.isValidMove(game_state, convert.to_bytes(8)) is False
#
#
# def test_transition(rules, game_id):
#     empty_board = encode_abi(STATE_TYPES, [[0, 0, 0, 0, 0, 0, 0, 0, 0], False, False])
#     nonce = 0
#     game_state = [game_id, nonce, empty_board]
#     for i in range(9):
#         next_game_id, next_nonce, next_state = rules.transition(game_state, convert.to_bytes(i))
#         assert next_game_id == game_id
#         assert next_nonce == 1
#         next_board = decode_abi(STATE_TYPES, next_state)
#         print(next_board)
#         expected_next_board = [0] * 9
#         expected_next_board[i] = 1
#         expected_next_board = (tuple(expected_next_board), False, False)
#         assert next_board == expected_next_board
#
#     nonce = 1
#     game_state = [game_id, nonce, empty_board]
#     for i in range(9):
#         next_game_id, next_nonce, next_state = rules.transition(game_state, convert.to_bytes(i))
#         assert next_game_id == game_id
#         assert next_nonce == 2
#         next_board = decode_abi(STATE_TYPES, next_state)
#         print(next_board)
#         expected_next_board = [0] * 9
#         expected_next_board[i] = 2
#         expected_next_board = (tuple(expected_next_board), False, False)
#         assert next_board == expected_next_board


# def sign_move(acc, game_state, new_game_state, move):
#     print(f"acc: {acc}, game_state: {game_state}, new_game_state: {new_game_state}, move: {move}")
#     return acc.sign_defunct_message(
#         to_eth_signed_message_hash(
#             game_state, new_game_state, move
#         ))


#     struct GameState {
#         uint256 gameId;
#         uint256 nonce;
#         bytes state;
#     }
# def to_eth_signed_message_hash(
#         old_game_state: tuple[int, int, bytes],
#         new_game_state: tuple[int, int, bytes],
#         move: bytes):
#     # return keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n", Strings.toString(s.length), s));
#     # signedHash = ECDSA.toEthSignedMessageHash(abi.encode(signedMove.oldGameState, signedMove.newGameState, signedMove.move));
#     # STATE_TYPES = ["uint8[9]", "bool", "bool"]
#     # struct SignedMove {
#     #     IGameJutsuRules.GameState oldGameState;
#     #     IGameJutsuRules.GameState newGameState;
#     #     bytes move;
#     #     bytes[] signatures;
#     # }
#     SIGNED_MOVE_TYPES = ["uint256", "uint256", "bytes"] * 2 + ["bytes"]
#     SIGNED_MOVE_TYPES = ["uint256", "uint256", "bytes", "uint256", "uint256", "bytes", "bytes"]
#
#     to_pack = [
#         old_game_state[0], old_game_state[1], old_game_state[2],
#         new_game_state[0], new_game_state[1], new_game_state[2],
#         to_bytes('0x00', 'bytes')]
#
#     print(f"to_pack: {to_pack}")
#     print(f"SIGNED_MOVE_TYPES: {SIGNED_MOVE_TYPES}")
#     to_sign = encode_abi(SIGNED_MOVE_TYPES, to_pack)
#     print(f"to_sign: {to_sign}")
#     print("-----------------------------------------------------------------")
#
#     prefix = encode_abi_packed(
#         ["string", "uint256"],
#         ["\x19Ethereum Signed Message:\n", len(to_sign)]
#     )
#
#     print(f"prefix: {prefix}")
#     all = prefix + to_sign
#     print(f"all: {all}")
#
#     return keccak_256(
#         all
#     )
