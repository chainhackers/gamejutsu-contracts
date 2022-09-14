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

/**
    @title GameJutsu Rules
    @notice "The fewer rules a coach has, the fewer rules there are for players to break." (John Madden)
    @notice ETHOnline2022 submission by ChainHackers
    @author Gene A. Tsvigun
  */
interface IGameJutsuRules {
    struct GameState {
        uint256 gameId;
        uint256 nonce;
        bytes state;
    }

    function isValidMove(GameState calldata state, uint8 playerId, bytes calldata move) external pure returns (bool);

    function transition(GameState calldata state, uint8 playerId, bytes calldata move) external pure returns (GameState memory);

    function defaultInitialGameState() external pure returns (bytes memory);
}
