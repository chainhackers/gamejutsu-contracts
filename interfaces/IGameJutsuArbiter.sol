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

import "./IGameJutsuRules.sol";

/**
    @title GameJutsu Arbiter
    @notice gets cheaters bang to rights
    @notice ETHOnline2022 submission by ChainHackers
    @notice 2 players only for now to make it doable during the hackathon
    @author Gene A. Tsvigun
    @dev https://codesandbox.io/s/gamejutsu-moves-eip712-mvrh8v?file=/src/index.js
  */
interface IGameJutsuArbiter {
    struct Game {
        IGameJutsuRules rules;
        uint256 stake;
        bool started;
        bool finished;
        mapping(address => uint8) players;
        address[2] playersArray;
    }

    struct GameMove {
        uint256 gameId;
        uint256 nonce;
        address player;
        bytes oldState;
        bytes newState;
        bytes move;
    }

    struct SignedGameMove {
        GameMove gameMove;
        bytes[] signatures;
    }

    function proposeGame(IGameJutsuRules rules) payable external returns (uint256 gameId);

    function acceptGame(uint256 gameId) payable external;

    function disputeMove(SignedGameMove calldata signedMove) external;

    function disputeMoveWithHistory(SignedGameMove[2] calldata signedMoves) external;

    function finishGame(SignedGameMove calldata signedMove) external;
    //
    //    function initMoveTimeout(SignedMove calldata signedMove) payable external;
    //
    //    function resolveTimeout(SignedMove calldata signedMove) external;
    //
    //    function finalizeTimeout(uint256 gameId) external;
    //

    function games(uint256 gameId) external view returns (IGameJutsuRules rules, uint256 stake, bool started, bool finished);

    function getPlayers(uint256 gameId) external view returns (address[2] memory);
}
