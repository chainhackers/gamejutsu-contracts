/*
  ________                           ____.       __
 /  _____/_____    _____   ____     |    |__ ___/  |_  ________ __
/   \  ___\__  \  /     \_/ __ \    |    |  |  \   __\/  ___/  |  \
\    \_\  \/ __ \|  Y Y  \  ___//\__|    |  |  /|  |  \___ \|  |  /
 \______  (____  /__|_|  /\___  >________|____/ |__| /____  >____/
        \/     \/      \/     \/                          \/
https://gamejutsu.app
*/
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/utils/cryptography/ECDSA.sol";
import "@openzeppelin/utils/Address.sol";
import "../interfaces/IGameJutsuRules.sol";
import "../interfaces/IGameJutsuArbiter.sol";

/**
    @title GameJutsu Arbiter
    @notice gets cheaters bang to rights
    @notice ETHOnline2022 submission by ChainHackers
    @notice 2 players only for now to make it doable during the hackathon
    @notice Major source of inspiration: https://magmo.com/force-move-games.pdf
    @author Gene A. Tsvigun
    @author Vic G. Larson
  */
contract Arbiter is IGameJutsuArbiter {
    /**
        @custom startTime The moment one of the players gets fed up waiting for the other to make a move
        @custom gameMove GameMove structure with the last move of the complainer
        @custom stake Put your money where your mouth is - nefarious timeouts can be penalized by not returning stake
      */
    struct Timeout {
        uint256 startTime;
        GameMove gameMove;
        uint256 stake;
    }

    uint256 public constant TIMEOUT = 5 minutes;
    /// @notice The EIP-712 typehash for the contract's domain
    bytes32 public constant DOMAIN_TYPEHASH = keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract,bytes32 salt)");
    bytes32 public immutable DOMAIN_SEPARATOR;
    /// @notice The EIP-712 typehash for the game move struct used by the contract
    bytes32 public constant GAME_MOVE_TYPEHASH = keccak256("GameMove(uint256 gameId,uint256 nonce,address player,bytes oldState,bytes newState,bytes move)");

    uint256 public DEFAULT_TIMEOUT = 5 minutes;
    uint256 public DEFAULT_TIMEOUT_STAKE = 0.1 ether;
    uint256 public NUM_PLAYERS = 2;

    mapping(uint256 => Game) public games;
    mapping(uint256 => Timeout) public timeouts;
    uint256 public nextGameId;

    modifier firstMoveSignedByAll(SignedGameMove[2] calldata signedMoves) {
        require(_isSignedByAllPlayersAndOnlyByPlayers(signedMoves[0]), "Arbiter: first move not signed by all players");
        _;
    }

    modifier lastMoveSignedByMover(SignedGameMove[2] calldata signedMoves) {
        require(_moveSignedByMover(signedMoves[1]), "Arbiter: first signature must belong to the player making the move");
        _;
    }

    modifier signedByMover(SignedGameMove calldata signedMove) {
        require(_moveSignedByMover(signedMove), "Arbiter: first signature must belong to the player making the move");
        _;
    }

    modifier onlyValidGameMove(GameMove calldata move) {
        require(_isValidGameMove(move), "Arbiter: invalid game move");
        _;
    }

    modifier onlyPlayer(SignedGameMove calldata signedMove){
        require(_playerInGame(signedMove.gameMove.gameId, signedMove.gameMove.player), "Arbiter: player not in game");
        _;
    }

    modifier movesInSequence(SignedGameMove[2] calldata moves) {
        for (uint256 i = 0; i < moves.length - 1; i++) {
            GameMove calldata currentMove = moves[i].gameMove;
            GameMove calldata nextMove = moves[i + 1].gameMove;
            require(currentMove.gameId == nextMove.gameId, "Arbiter: moves are for different games");
            require(currentMove.nonce + 1 == nextMove.nonce, "Arbiter: moves are not in sequence");
            require(keccak256(currentMove.newState) == keccak256(nextMove.oldState), "Arbiter: moves are not in sequence");
        }
        _;
    }

    modifier allValidGameMoves(SignedGameMove[2] calldata moves) {
        require(_allValidGameMoves(moves), "Arbiter: invalid game move");
        _;
    }

    modifier timeoutStarted(uint256 gameId) {
        require(_timeoutStarted(gameId), "Arbiter: timeout not started");
        _;
    }

    modifier timeoutNotStarted(uint256 gameId) {
        require(!_timeoutStarted(gameId), "Arbiter: timeout already started");
        _;
    }

    modifier timeoutExpired(uint256 gameId) {
        require(_timeoutExpired(gameId), "Arbiter: timeout not expired");
        _;
    }

    modifier timeoutNotExpired(uint256 gameId) {
        require(!_timeoutExpired(gameId), "Arbiter: timeout already expired");
        _;
    }

    constructor() {
        DOMAIN_SEPARATOR = keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256(bytes("GameJutsu")), keccak256("0.1"), 137, 0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC, bytes32(0x920dfa98b3727bbfe860dd7341801f2e2a55cd7f637dea958edfc5df56c35e4d)));
    }

    /**
        @notice Create a new game, define its rules and stake amount, put the stake on the table
        @param rules Rules contract address to use in conflict resolution
        @param sessionAddresses Addresses the proposer intends to use to sign moves
      */
    function proposeGame(IGameJutsuRules rules, address[] calldata sessionAddresses) payable external returns (uint256 gameId) {
        gameId = nextGameId;
        Game storage game = games[gameId];
        game.rules = rules;
        game.players[msg.sender] = 1;
        game.playersArray[0] = msg.sender;
        game.stake = msg.value;
        nextGameId++;
        emit GameProposed(address(rules), gameId, msg.value, msg.sender);
        if (sessionAddresses.length > 0) {
            for (uint256 i = 0; i < sessionAddresses.length; i++) {
                _registerSessionAddress(gameId, msg.sender, sessionAddresses[i]);
            }
        }
    }


    /**
        @notice Join a game, put the stake on the table
        @param gameId Game ID to join
        @param sessionAddresses Addresses the joiner intends to use to sign moves
      */
    function acceptGame(uint256 gameId, address[] calldata sessionAddresses) payable external {
        Game storage game = games[gameId];
        require(game.players[msg.sender] == 0, "Arbiter: player already in game");
        require(game.started == false, "Arbiter: game already started");
        require(game.playersArray[0] != address(0), "Arbiter: game not proposed");
        require(game.stake <= msg.value, "Arbiter: stake mismatch");
        game.players[msg.sender] = 2;
        game.playersArray[1] = msg.sender;
        game.stake += msg.value;
        game.started = true;

        emit GameStarted(address(game.rules), gameId, game.stake, game.playersArray);
        if (sessionAddresses.length > 0) {
            for (uint256 i = 0; i < sessionAddresses.length; i++) {
                _registerSessionAddress(gameId, msg.sender, sessionAddresses[i]);
            }
        }
    }

    /**
        @notice Register an additional session address to sign moves
        @notice This is useful if when changing browser sessions
        @param gameId The ID of the game being played
        @param sessionAddress Address the joiner intends to use to sign moves
      */
    function registerSessionAddress(uint256 gameId, address sessionAddress) external {
        require(games[gameId].players[msg.sender] > 0, "Arbiter: player not in game");
        require(games[gameId].started == true, "Arbiter: game not started");
        _registerSessionAddress(gameId, msg.sender, sessionAddress);
    }

    /**
        @notice Submit 2 most recent signed moves to the arbiter to finish the game
        @notice the first move must be signed by all players
        @notice the second move must be signed at least by the player making the move
        @notice the new state of the second move must be final -i.e. reported by the rules contract as such
        @param signedMoves Array of 2 signed moves
      */
    function finishGame(SignedGameMove[2] calldata signedMoves) external
    movesInSequence(signedMoves)
    returns (address winner){
        require(_isSignedByAllPlayersAndOnlyByPlayers(signedMoves[0]), "Arbiter: first move not signed by all players");
        require(_moveSignedByMover(signedMoves[1]), "Arbiter: second move not signed by mover");

        uint256 gameId = signedMoves[0].gameMove.gameId;
        require(_isGameOn(gameId), "Arbiter: game not active");
        require(signedMoves[1].gameMove.gameId == gameId, "Arbiter: game ids mismatch");
        require(_isValidGameMove(signedMoves[1].gameMove), "Arbiter: invalid game move");

        IGameJutsuRules.GameState memory newState = IGameJutsuRules.GameState(
            gameId,
            signedMoves[1].gameMove.nonce + 1,
            signedMoves[1].gameMove.newState);
        IGameJutsuRules rules = games[gameId].rules;
        require(rules.isFinal(newState), "Arbiter: game state not final");
        for (uint8 i = 0; i < NUM_PLAYERS; i++) {
            if (rules.isWin(newState, i)) {
                winner = games[gameId].playersArray[i];
                address loser = _opponent(gameId, winner);
                _finishGame(gameId, winner, loser, false);
                return winner;
            }
        }
        _finishGame(gameId, address(0), address(0), true);
        return address(0);
    }

    /**
        @notice Resign from a game and forfeit the stake
        @notice The caller's opponent wins
        @param gameId The ID of the game being played
      */
    function resign(uint256 gameId) external {
        require(_isGameOn(gameId), "Arbiter: game not active");
        require(games[gameId].players[msg.sender] != 0, "Arbiter: player not in game");
        address loser = msg.sender;
        address winner = _opponent(gameId, loser);
        _finishGame(gameId, winner, loser, false);
        emit PlayerResigned(gameId, loser);
    }

    /**
        @notice Dispute a cheat move by a player
        @param signedMove The signed move to be validated
      */
    function disputeMove(SignedGameMove calldata signedMove) external
    signedByMover(signedMove)
    {
        GameMove calldata gm = signedMove.gameMove;
        require(!_isValidGameMove(gm), "Arbiter: valid move disputed");

        Game storage game = games[gm.gameId];
        require(game.started && !game.finished, "Arbiter: game not started yet or already finished");
        require(game.players[gm.player] != 0, "Arbiter: player not in game");

        disqualifyPlayer(gm.gameId, gm.player);
    }

    function disputeMoveWithHistory(SignedGameMove[2] calldata signedMoves) external {
        //TODO add dispute move version based on comparison to previously signed moves
    }

    /**
        @notice both moves must be in sequence
        @notice first move must be signed by both players
        @notice second move must be signed at least by the player making the move
        @notice no timeout should be active for the game
       */
    function initTimeout(SignedGameMove[2] calldata moves) payable external
    firstMoveSignedByAll(moves)
    lastMoveSignedByMover(moves)
    timeoutNotStarted(moves[0].gameMove.gameId)
    movesInSequence(moves)
    allValidGameMoves(moves)
    {
        require(msg.value == DEFAULT_TIMEOUT_STAKE, "Arbiter: timeout stake mismatch");
        uint256 gameId = moves[0].gameMove.gameId;
        timeouts[gameId].stake = msg.value;
        timeouts[gameId].gameMove = moves[1].gameMove;
        timeouts[gameId].startTime = block.timestamp;
        emit TimeoutStarted(gameId, moves[1].gameMove.player, moves[1].gameMove.nonce, block.timestamp + TIMEOUT);
    }

    /**
        @notice a single valid signed move is enough to resolve the timout
        @notice the move must be signed by the player whos turn it is
        @notice the move must continue the game from the move started the timeout
       */
    function resolveTimeout(SignedGameMove calldata signedMove) external
    timeoutStarted(signedMove.gameMove.gameId)
    timeoutNotExpired(signedMove.gameMove.gameId)
    signedByMover(signedMove)
    onlyValidGameMove(signedMove.gameMove)
    onlyPlayer(signedMove)
    {
        uint256 gameId = signedMove.gameMove.gameId;
        GameMove storage timeoutMove = timeouts[gameId].gameMove;
        require(timeoutMove.gameId == signedMove.gameMove.gameId, "Arbiter: game ids mismatch");
        require(timeoutMove.nonce + 1 == signedMove.gameMove.nonce, "Arbiter: nonce mismatch");
        require(timeoutMove.player != signedMove.gameMove.player, "Arbiter: same player");
        require(keccak256(timeoutMove.newState) == keccak256(signedMove.gameMove.oldState), "Arbiter: state mismatch");
        _clearTimeout(gameId);
        emit TimeoutResolved(gameId, signedMove.gameMove.player, signedMove.gameMove.nonce);
    }

    /**
        @notice the timeout must be expired
        @notice 2 player games only
       */
    function finalizeTimeout(uint256 gameId) external
    timeoutExpired(gameId)
    {
        address loser = _opponent(gameId, timeouts[gameId].gameMove.player);
        disqualifyPlayer(gameId, loser);
        _clearTimeout(gameId);
    }

    /**
        @notice Get addresses of players in a game
        @param gameId The ID of the game being played
       */
    function getPlayers(uint256 gameId) external view returns (address[2] memory){
        return games[gameId].playersArray;
    }

    /**
        @notice Validate a game move without signatures
        @param gameMove The move to be validated
       */
    function isValidGameMove(GameMove calldata gameMove) external view returns (bool) {
        return _isValidGameMove(gameMove);
    }

    /**
        @notice Validate a signed game move
        @param signedMove The move to be validated
       */
    function isValidSignedMove(SignedGameMove calldata signedMove) external view returns (bool) {
        return _isValidSignedMove(signedMove);
    }

    function disqualifyPlayer(uint256 gameId, address cheater) private {
        require(games[gameId].players[cheater] != 0, "Arbiter: player not in game");
        games[gameId].finished = true;
        address winner = games[gameId].playersArray[0] == cheater ? games[gameId].playersArray[1] : games[gameId].playersArray[0];
        payable(winner).transfer(games[gameId].stake);
        emit GameFinished(gameId, winner, cheater, false);
        emit PlayerDisqualified(gameId, cheater);
    }

    function _finishGame(uint256 gameId, address winner, address loser, bool draw) private {
        games[gameId].finished = true;
        if (draw) {
            uint256 half = games[gameId].stake / 2;
            uint256 theOtherHalf = games[gameId].stake - half;
            payable(games[gameId].playersArray[0]).transfer(half);
            payable(games[gameId].playersArray[1]).transfer(theOtherHalf);
        } else {
            payable(winner).transfer(games[gameId].stake);
        }
        emit GameFinished(gameId, winner, loser, draw);
    }

    function _registerSessionAddress(uint256 gameId, address player, address sessionAddress) private {
        games[gameId].players[sessionAddress] = games[gameId].players[player];
        emit SessionAddressRegistered(gameId, player, sessionAddress);
    }

    function _clearTimeout(uint256 gameId) private {
        Address.sendValue(payable(timeouts[gameId].gameMove.player), timeouts[gameId].stake);
        delete timeouts[gameId];
    }

    function getSigners(SignedGameMove calldata signedMove) private view returns (address[] memory) {
        address[] memory signers = new address[](signedMove.signatures.length);
        for (uint256 i = 0; i < signedMove.signatures.length; i++) {
            signers[i] = recoverAddress(signedMove.gameMove, signedMove.signatures[i]);
        }
        return signers;
    }

    function recoverAddress(GameMove calldata gameMove, bytes calldata signature) private view returns (address){
        //        https://codesandbox.io/s/gamejutsu-moves-eip712-no-nested-types-p5fnzf?file=/src/index.js
        bytes32 structHash = keccak256(abi.encode(
                GAME_MOVE_TYPEHASH,
                gameMove.gameId,
                gameMove.nonce,
                gameMove.player,
                keccak256(gameMove.oldState),
                keccak256(gameMove.newState),
                keccak256(gameMove.move)
            ));
        bytes32 digest = ECDSA.toTypedDataHash(DOMAIN_SEPARATOR, structHash);
        return ECDSA.recover(digest, signature);
    }

    function _opponent(uint256 gameId, address player) private view returns (address){
        return games[gameId].playersArray[2 - games[gameId].players[player]];
    }

    /**
        @dev checks only state transition validity, all the signatures are checked elsewhere
    */
    function _isValidGameMove(GameMove calldata move) private view returns (bool) {
        Game storage game = games[move.gameId];
        IGameJutsuRules.GameState memory oldGameState = IGameJutsuRules.GameState(move.gameId, move.nonce, move.oldState);
        return keccak256(move.oldState) != keccak256(move.newState) &&
        game.started &&
        !game.finished &&
        game.players[move.player] != 0 &&
        game.rules.isValidMove(oldGameState, game.players[move.player] - 1, move.move) &&
        keccak256(game.rules.transition(oldGameState, game.players[move.player] - 1, move.move).state) == keccak256(move.newState);
    }

    /**
        @dev checks state transition validity and signatures, first signature must be by the player making the move
    */
    function _isValidSignedMove(SignedGameMove calldata move) private view returns (bool) {
        if (!_moveSignedByMover(move)) {
            return false;
        }

        for (uint i = 1; i < move.signatures.length; i++) {
            if (!_playerInGame(move.gameMove.gameId, recoverAddress(move.gameMove, move.signatures[i]))) {
                return false;
            }
        }
        return _isValidGameMove(move.gameMove);
    }

    function _isGameOn(uint256 gameId) private view returns (bool) {
        return games[gameId].started && !games[gameId].finished;
    }

    function _isSignedByAllPlayersAndOnlyByPlayers(SignedGameMove calldata signedMove) private view returns (bool) {
        address[] memory signers = getSigners(signedMove);
        bool[2] memory signersPresent;
        if (signers.length != NUM_PLAYERS) {
            return false;
        }
        for (uint256 i = 0; i < signers.length; i++) {
            uint8 oneBasedPlayerId = games[signedMove.gameMove.gameId].players[signers[i]];
            if (oneBasedPlayerId == 0) {
                return false;
            }
            signersPresent[oneBasedPlayerId - 1] = true;
        }
        return signersPresent[0] && signersPresent[1];
    }

    function _timeoutStarted(uint256 gameId) private view returns (bool) {
        return timeouts[gameId].startTime != 0;
    }

    function _timeoutExpired(uint256 gameId) private view returns (bool) {
        return _timeoutStarted(gameId) && timeouts[gameId].startTime + TIMEOUT < block.timestamp;
    }

    function _allValidGameMoves(SignedGameMove[2] calldata moves) private view returns (bool) {
        for (uint256 i = 0; i < moves.length; i++) {
            if (!_isValidGameMove(moves[i].gameMove)) {
                return false;
            }
        }
        return true;
    }

    function _moveSignedByMover(SignedGameMove calldata move) private view returns (bool) {
        address signer = recoverAddress(move.gameMove, move.signatures[0]);
        uint256 gameId = move.gameMove.gameId;
        return games[gameId].players[signer] == games[gameId].players[move.gameMove.player];
    }

    function _playerInGame(uint256 gameId, address player) private view returns (bool) {
        return games[gameId].players[player] != 0;
    }
}
