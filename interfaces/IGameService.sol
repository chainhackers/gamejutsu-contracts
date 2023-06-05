// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import "./IGameJutsuRules.sol";
import "./IGameJutsuArbiter.sol";

interface IGameService {
    /**
        @notice What the Arbiter knows about the game
        @custom rules the contract defining the rules of the game
        @custom stake the amount of the chain's native currency to stake for the game
        @custom started whether the game has started
        @custom finished whether the game has finished
        @custom players the players and their session addresses
        @custom playersArray both players addresses
      */
    struct Game {
        IGameJutsuRules rules;
        uint256 stake;
        bool started;
        bool finished;
        mapping(address => uint8) players;
        address[2] playersArray;
    }
    event GameProposed(address indexed rules, uint256 gameId, uint256 stake, address indexed proposer);
    event GameStarted(address indexed rules, uint256 gameId, uint256 stake, address[2] players);
    event GameFinished(uint256 gameId, address winner, address loser, bool isDraw);
    event PlayerDisqualified(uint256 gameId, address player);
    event SessionAddressRegistered(uint256 gameId, address player, address sessionAddress);
    event PlayerResigned(uint256 gameId, address player);

    function acceptGame(uint256 gameId, address[] calldata sessionAddresses) payable external;

    function disputeMove(IGameJutsuArbiter.SignedGameMove calldata signedMove) external; //TODO mark the most important methods

    function disputeMoveWithHistory(IGameJutsuArbiter.SignedGameMove[2] calldata signedMoves) external;

    function proposeGame(IGameJutsuRules rules, address[] calldata sessionAddresses) payable external returns (uint256 gameId);

    function registerSessionAddress(uint256 gameId, address sessionAddress) external;

    function resign(uint256 gameId) external;

    function games(uint256 gameId) external view returns (IGameJutsuRules rules, uint256 stake, bool started, bool finished);

    function getPlayers(uint256 gameId) external view returns (address[2] memory);

    function finishGame(IGameJutsuArbiter.SignedGameMove[2] calldata signedMoves) external returns (address winner);

}
