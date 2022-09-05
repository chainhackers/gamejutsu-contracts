pragma solidity ^0.8.0;

interface IGameJutsuRules {
    function isValidMove(bytes calldata state, bytes calldata move, uint256 nonce) external pure returns (bool);

    function transition(bytes calldata state, bytes calldata move, uint256 nonce) external pure returns (bytes memory);
}
