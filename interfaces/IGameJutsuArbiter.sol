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
    /**
        @notice The way players present their moves to the Arbiter
        @custom gameId the id of the game
        @custom nonce the nonce of the move - how many moves have been made before this one, for the first move it is 0
        @custom player the address of the player making the move
        @custom oldState the state of the game before the move, the player declares it to be the actual state
        @custom newState the state of the game after the move, must be a valid transition from the oldState
        @custom move the move itself, must be consistent with the newState
      */
    struct GameMove {
        uint256 gameId;
        uint256 nonce;
        address player;
        bytes oldState;
        bytes newState;
        bytes move;
    }

    /**
        @notice Signed game move with players' signatures
        @custom gameMove GameMove struct
        @custom signatures the signatures of the players signing  `abi.encode`d gameMove
      */
    struct SignedGameMove {
        GameMove gameMove;
        bytes[] signatures;
    }

    event TimeoutStarted(uint256 gameId, address player, uint256 nonce, uint256 timeout);
    event TimeoutResolved(uint256 gameId, address player, uint256 nonce);

    function initTimeout(SignedGameMove[2] calldata signedMoves) payable external;

    function resolveTimeout(SignedGameMove calldata signedMove) external;

    function finalizeTimeout(uint256 gameId) external;

    //TODO penalize griefers for starting timeouts despite valid moves being published, needs timing in SignedGameMove

    function isValidGameMove(GameMove calldata gameMove) external view returns (bool);

    function isValidSignedMove(SignedGameMove calldata signedMove) external view returns (bool);
}
