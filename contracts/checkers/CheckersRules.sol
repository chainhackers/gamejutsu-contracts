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

import "../../interfaces/IGameJutsuRules.sol";

/**
    @title Checkers Rules
    @notice https://www.officialgamerules.org/checkers
    @notice GameJutsu's second game example, rules defined on-chain to never be checked
    @notice except by the arbiter when a dispute arises.
    @notice ETHOnline2022 submission by ChainHackers
    @author Gene A. Tsvigun
    @dev The state encodes the board as a 3x3 array of uint8s with 0 for empty, 1 for X, and 2 for O
    @dev explicitly keeping wins as `bool crossesWin` and `bool noughtsWin`
    @dev yes we know the board can be packed more efficiently but we want to keep it simple
  */
contract CheckersRules is IGameJutsuRules {

    /**
        @custom cells 32-byte array of uint8s representing the board
        @custom redMoves says whether it is red's turn to move
        @custom winner is 0 for no winner, 1 for white, 2 for red
        @dev cells[i] values:
        @dev 0x01 is White
        @dev 0x02 is Red
        @dev 0xA1 is White King
        @dev 0xA2 is Red King
      */
    struct State {
        uint8[32] cells;
        bool redMoves;
        uint8 winner;
    }

    /**
        @custom from 1-based index of the cell to move from
        @custom to 1-based index of the cell to move to
        @custom isJump declares if the move is a jump
        @custom passMoveToOpponent declares explicitly if the next move is to be done by the opponent
      */
    struct Move {
        uint8 from;
        uint8 to;
        bool isJump;
        bool passMoveToOpponent;
    }

    //             1       2       3       4
    // 1     │███│ o │███│ o │███│ o │███│ o │ 04
    // 5     │ o │███│ o │███│ o │███│ o │███│ 08
    // 9     │███│ o │███│ o │███│ o │███│ o │ 0C
    // 13 0D │   │███│   │███│   │███│   │███│ 10
    // 17 11 │███│   │███│   │███│   │███│   │ 14
    // 21 15 │ x │███│ x │███│ x │███│ x │███│ 18
    // 25 19 │███│ x │███│ x │███│ x │███│ x │ 1C
    // 29 1D │ x │███│ x │███│ x │███│ x │███│ 20
    //        1D      1E      1F      20

    /**
        @param _state is the state of the game represented by `abi.encode`d `State` struct
        @param playerId 0 is White, player 1 is Red
        @param _move is the move represented by `abi.encode`d `Move` struct
        */
    function isValidMove(GameState calldata _state, uint8 playerId, bytes calldata _move) external pure override returns (bool) {
        State memory state = abi.decode(_state.state, (State));
        Move memory move = abi.decode(_move, (Move));
        bool isPlayerRed = playerId == 1;
        bool isInBounds = move.from > 0 && move.from <= 32 && move.to > 0 && move.to <= 32;
        bool isCorrectPlayerMove = isPlayerRed == state.redMoves;

        bool isFromOccupied = _isCellOccupied(state, move.from);
        bool isToEmpty = !_isCellOccupied(state, move.to);

        bool isCheckerRed = _isCheckerRed(state, move.from);
        bool isCheckerKing = _isCheckerKing(state, move.from);

        bool isColorCorrect = isCheckerRed == isPlayerRed;
        bool isDirectionCorrect = isCheckerKing || isCheckerRed ? move.from > move.to : move.from < move.to;

        bool isToCorrect = !move.isJump && _isMoveDestinationCorrect(move.from, move.to, isCheckerRed, isCheckerKing) ||
        move.isJump && _isJumpDestinationCorrect(move.from, move.to);
        bool isCaptureCorrect = !move.isJump || _isCaptureCorrect(state.cells, move.from, move.to, isCheckerRed);

        uint8[32] memory cells = state.cells;
        if (move.isJump) {
            cells[move.to - 1] = cells[move.from - 1];
            cells[move.from - 1] = 0;
            uint8 jumpedCell = _jumpMiddle(move.from, move.to);
            cells[jumpedCell - 1] = 0;
        }
        bool isPassMoveCorrect = !move.isJump && move.passMoveToOpponent ||
        move.isJump && move.passMoveToOpponent != _validJumpExists(cells, isPlayerRed);
        return isCorrectPlayerMove &&
        isInBounds &&
        isFromOccupied &&
        isToEmpty &&
        isColorCorrect &&
        isDirectionCorrect &&
        isFromOccupied &&
        isToEmpty &&
        isToCorrect &&
        isCaptureCorrect &&
        isPassMoveCorrect;
    }

    /**
        @param state `uint8[32]` array representing board cells, 0: empty, 01:W, 02:R, A1:WK, A2:RK
        @param cell is 1-based index of the cell checked
        */
    function _isCellOccupied(State memory state, uint8 cell) private pure returns (bool) {
        return state.cells[cell - 1] != 0;
    }

    /**
        @param cell is 1-based index of the cell checked
        */
    function _isCheckerRed(State memory state, uint8 cell) private pure returns (bool) {
        return state.cells[cell - 1] % 16 == 2;
    }

    function _isCheckerKing(State memory state, uint8 cell) private pure returns (bool) {
        return state.cells[cell - 1] / 16 == 10;
    }

    /**
        @param _from 1-based index of the cell from which the checker is moved
        @param _to 1-based index of the cell to which the checker is moved
        @param isRed is true if the checker doing the move is red
        @param isKing is true if the checker doing the move is king
        */
    function _isMoveDestinationCorrect(uint8 _from, uint8 _to, bool isRed, bool isKing) private pure returns (bool) {
        //TODO deduplicate with _canMove
        if (_from == 0 || _to == 0) {
            return false;
        }
        uint8 from = _from - 1;
        uint8 to = _to - 1;

        uint8 row = from / 4;
        uint8 col = from % 4;
        int8 rowDiff = isRed ? - 1 : int8(1);
        int8 colDiff = - (int8(row) % 2);
        int8 destination = 4 * (int8(row) + rowDiff) + int8(col) + colDiff;
        int8 backstination = 4 * (int8(row) - rowDiff) + int8(col) + colDiff;

        return _isIndexInBounds(destination) &&
        (to == uint8(destination) || to == uint8(destination) + 1) ||
        isKing && _isIndexInBounds(backstination) &&
        (to == uint8(backstination) || to == uint8(backstination) + 1);
    }
    // 1-based
    function _jumpMiddle(uint8 from, uint8 to) private pure returns (uint8){
        return (from + to + 1 - ((from - 1) / 4 % 2)) / 2;
    }

    /**
        @param cells array of 32 `uint8`s representing the board
        @param from 1-based index of the cell from which the checker is moved
        @param to 1-based index of the cell to which the checker is moved
        @param isPlayerRed is true if the player doing the move plays red
        */
    function _isCaptureCorrect(uint8[32] memory cells, uint8 from, uint8 to, bool isPlayerRed) private pure returns (bool) {
        bytes1 jump = bytes1(to);
        uint8 f2 = (from - 1) * 2;
        uint8 opponent = _opponent(isPlayerRed);
        return cells[_jumpMiddle(from, to) - 1] == opponent;
    }

    function _opponent(bool isPlayerRed) private pure returns (uint8) {
        return isPlayerRed ? 1 : 2;
    }


    function _isJumpDestinationCorrect(uint8 from, uint8 to) private pure returns (bool) {
        uint8 diff = to > from ? to - from : from - to;
        return diff == 7 || diff == 9;
    }

    /**
        @notice What the rules say happens when a particular move is made in a particular state by a particular player
        @param _state GameState struct with the current state of the game: id, nonce, encoded game-specific state
        @param playerId 0 is White, player 1 is Red
        @param _move is the move represented by `abi.encode`d `Move` struct
        */
    function transition(GameState calldata _state, uint8 playerId, bytes calldata _move) external pure override returns (GameState memory) {
        State memory state = abi.decode(_state.state, (State));
        Move memory move = abi.decode(_move, (Move));
        uint8 newCellValue = state.cells[move.from - 1];
        bool isRed = state.cells[move.from - 1] % 16 == 2;
        if (_lastRow(move.to, isRed)) {
            newCellValue = newCellValue | 0xA0;
        }
        state.cells[move.to - 1] = newCellValue;
        state.cells[move.from - 1] = 0;
        if (move.isJump) {
            state.cells[(move.from + move.to) / 2 - (move.from % 8 > 4 ? 1 : 0)] = 0;
            if (!_validJumpExists(state.cells, state.redMoves)) {
                state.redMoves = !state.redMoves;
            }
        } else {
            state.redMoves = !state.redMoves;
        }

        (bool whiteHasMoves, bool redHasMoves) = _validMovesExist(state.cells);
        if (state.redMoves && !redHasMoves && !_validJumpExists(state.cells, state.redMoves)) {//TODO test valid jumps checks for setting the winner
            state.winner = 1;
        } else if (!state.redMoves && !whiteHasMoves && !_validJumpExists(state.cells, state.redMoves)) {
            state.winner = 2;
        }
        return GameState(_state.gameId, _state.nonce + 1, abi.encode(state));
    }

    /**
        @notice returns the traditional checkers starting position
      */
    function defaultInitialGameState() external pure returns (bytes memory) {

        // 1   │███│ o │███│ o │███│ o │███│ o │
        // 5   │ o │███│ o │███│ o │███│ o │███│
        // 9   │███│ o │███│ o │███│ o │███│ o │
        // 13  │   │███│ 14│███│   │███│   │███│
        // 17  │███│   │███│ 18│███│   │███│   │
        // 21  │ x │███│ x │███│ x │███│ x │███│
        // 25  │███│ x │███│ x │███│ x │███│ x │
        // 29  │ x │███│ x │███│ x │███│ x │███│

        return abi.encode(State([
            1, 1, 1, 1,
            1, 1, 1, 1,
            1, 1, 1, 1,
            0, 0, 0, 0,
            0, 0, 0, 0,
            2, 2, 2, 2,
            2, 2, 2, 2,
            2, 2, 2, 2
            ], false, 0));
    }

    /**
        @notice Check if the destination cell belongs to the last row for the specified color
        @param to Destination cell index, 1-based
        @param isRed The color of the moving checker
        */
    function _lastRow(uint8 to, bool isRed) private pure returns (bool) {
        return isRed && to <= 4 || !isRed && to >= 29;
    }

    function _validMovesExist(uint8[32] memory cells) private pure returns (bool whiteHasValidMoves, bool redHasValidMoves) {
        whiteHasValidMoves = false;
        redHasValidMoves = false;
        for (uint8 i = 0; i < 32; i++) {
            bool isRed = cells[i] % 16 == 2;
            if (isRed) {
                redHasValidMoves = redHasValidMoves || _canMove(cells, i);
            } else {
                whiteHasValidMoves = whiteHasValidMoves || _canMove(cells, i);
            }
        }
    }

    function _validJumpExists(uint8[32] memory cells, bool forRed) public pure returns (bool) {
        for (uint8 i = 0; i < 32; i++) {
            bool isRed = cells[i] % 16 == 2;
            if (isRed == forRed && _canJump(cells, i)) {
                return true;
            }
        }
        return false;
    }

    /**
        @param from 0-based index
      */
    function _canMove(uint8[32] memory cells, uint8 from) private pure returns (bool) {
        if (cells[from] == 0)
            return false;
        bool isRed = cells[from] % 16 == 2;
        bool isKing = cells[from] / 16 == 10;
        uint8 row = from / 4;
        uint8 col = from % 4;
        int8 rowDiff = isRed ? - 1 : int8(1);
        int8 colDiff = - (int8(row) % 2);
        int8 destination = 4 * (int8(row) + rowDiff) + int8(col) + colDiff;
        int8 backstination = 4 * (int8(row) - rowDiff) + int8(col) + colDiff;

        return _isCellEmpty(cells, destination) || isKing && _isCellEmpty(cells, backstination);
    }

    //0-based
    function _isIndexInBounds(int8 i) private pure returns (bool) {
        return i >= 0 && i < 32;
    }

    function _isCellEmpty(uint8[32] memory cells, int8 i) private pure returns (bool) {
        return _isIndexInBounds(i) && cells[uint8(i)] == 0;
    }


    /**
        @param cells array of 32 `uint8`s representing the board
        @param from 0-based index
      */
    function _canJump(uint8[32] memory cells, uint8 from) public pure returns (bool) {
        if (cells[from] == 0)
            return false;
        bool isRed = cells[from] % 16 == 2;
        bool isKing = cells[from] / 16 == 10;
        uint8 row = from / 4;
        uint8 col = from % 4;
        int8 destinationRowDiff = isRed ? (- 2) : int8(2);
        int8 eatenColumnDiff = int8(row) % int8(2) == 0 ? int8(0): int8(-1);
        uint8 eatenColor = isRed ? 1 : 2;

        return _canJumpTo(cells, row, col, destinationRowDiff, eatenColumnDiff, eatenColor)
        || (isKing && _canJumpTo(cells, row, col, -destinationRowDiff, eatenColumnDiff, eatenColor));
    }

    function _canEat(uint8[32] memory cells, int8 to, int8 eaten, uint8 eatenColor) private pure returns (bool){
        return to >= 0 && to <= 31 &&
        eaten >= 0 && eaten <= 31 &&
        cells[uint8(to)] == 0 && cells[uint8(eaten)] % 16 == eatenColor;
    }

    function _canJumpTo(
        uint8[32] memory cells,
        uint8 row,
        uint8 column,
        int8 destinationRowDiff,
        int8 eatenColumnDiff,
        uint8 eatenColor)
    private pure returns (bool){
        int8 eatenRowDiff = destinationRowDiff / 2;
        if (((int8(row) + destinationRowDiff) < 0) ||
            ((int8(row) + destinationRowDiff)  > 7)) {
                return false;
            }
        if ((int8(column) - 1 < 0) || (int8(column) + 1 > 3) ) {
            return false;
        }
        int8 destinationBase = (int8(row) + destinationRowDiff) * 4 + int8(column);
        int8 eatenBase = (int8(row) + eatenRowDiff) * 4 + int8(column) + eatenColumnDiff;
        if (
            _canEat(cells, destinationBase - 1, eatenBase, eatenColor) ||
            _canEat(cells, destinationBase + 1, eatenBase + 1, eatenColor)
        ) {
            return true;
        }
        return false;
    }


    function isFinal(GameState calldata _gameState) external pure override returns (bool) {
        return _decodeState(_gameState.state).winner != 0;
    }

    function isWin(GameState calldata _gameState, uint8 playerId) external pure override returns (bool) {
        return _decodeState(_gameState.state).winner == playerId + 1;
    }

    function _decodeMove(bytes calldata move) private pure returns (Move memory) {
        return abi.decode(move, (Move));
    }

    function _decodeState(bytes calldata state) private pure returns (State memory) {
        return abi.decode(state, (State));
    }

    function _isRed(uint8 _piece) private pure returns (bool) {
        return _piece == 1;
    }

    function _isKing(uint8 _piece) private pure returns (bool) {
        return _piece % 16 == 10;
    }
}
