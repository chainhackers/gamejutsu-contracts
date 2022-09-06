// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./IGameJutsuRules.sol";

interface IGameJutsuArbiter {
    struct SignedMove {
        IGameJutsuRules.GameState oldGameState;
        IGameJutsuRules.GameState newGameState;
        bytes move;
        bytes[] signatures;
    }

    function proposeGame(IGameJutsuRules rules) payable external returns (uint256 gameId);

    function acceptGame(uint256 gameId) payable external;

    function disputeMove(SignedMove calldata signedMove) external;

    function initTimeout(SignedMove calldata signedMove) payable external;
}
