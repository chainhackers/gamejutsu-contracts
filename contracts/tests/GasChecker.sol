// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "../../interfaces/IGameJutsuRules.sol";

contract GasChecker {
    bool checkResult = false;

    function callIsValidMove(
        IGameJutsuRules rules,
        IGameJutsuRules.GameState calldata gameState,
        uint8 playerId,
        bytes calldata move
    ) external {
        checkResult = rules.isValidMove(gameState, playerId, move);
    }
}
