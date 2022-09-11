// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./IGameJutsuRules.sol";

/**
    @notice 2 players only
    @dev https://codesandbox.io/s/gamejutsu-moves-eip712-mvrh8v?file=/src/index.js
*/
interface IGameJutsuArbiter {
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
    //
    //    function initMoveTimeout(SignedMove calldata signedMove) payable external;
    //
    //    function resolveTimeout(SignedMove calldata signedMove) external;
    //
    //    function finalizeTimeout(uint256 gameId) external;
    //
    function getPlayers(uint256 gameId) external view returns (address[2] memory);
}
