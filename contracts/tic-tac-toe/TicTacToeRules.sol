// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "../../../interfaces/IGameJutsuRules.sol";

contract TicTacToeRules is IGameJutsuRules {

    struct Board {
        uint8[9] cells; //TODO pack it into a single uint16
        bool crossWins;
        bool naughtWins;
    }

    type Move is uint8;

    function isValidMove(bytes calldata _state, bytes calldata _move, uint256 nonce) external pure override returns (bool) {
        Board memory b = abi.decode(_state, (Board));
        uint8 _m = abi.decode(_move, (uint8));
        Move m = Move.wrap(_m);

        return !b.crossWins && !b.naughtWins && isMoveWithinRange(m) && isCellEmpty(b, m);
    }

    function transition(bytes calldata state, bytes calldata move, uint256 nonce) external pure override returns (bytes memory) {
        return "";
    }

    function isCellEmpty(Board memory b, Move move) private pure returns (bool) {
        return b.cells[Move.unwrap(move)] == 0;
    }


    function isMoveWithinRange(Move move) private pure returns (bool){
        return Move.unwrap(move) < 9;
    }
}