// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "../interfaces/IGameJutsuRules.sol";

/**
    @notice First iteration: separate Arbiter per game
*/
contract Arbiter {
    IGameJutsuRules rules;
    bytes initialGameState;

    constructor (IGameJutsuRules _rules, bytes memory _initialGameState) {
        rules = _rules;
        initialGameState = _initialGameState;
    }

}
