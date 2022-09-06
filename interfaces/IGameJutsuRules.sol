// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IGameJutsuRules {
    struct GameState {
        bytes state;
        uint256 nonce;
    }

    function isValidMove(GameState calldata state, bytes calldata move) external pure returns (bool);

    function transition(GameState calldata state, bytes calldata move) external pure returns (GameState memory);
}
