// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/utils/cryptography/ECDSA.sol";
import "../interfaces/IGameJutsuRules.sol";
import "../interfaces/IGameJutsuArbiter.sol";

/**
    @notice First iteration: separate Arbiter per game
    @notice 2 players only
*/
contract Arbiter is IGameJutsuArbiter {
    struct Game {
        IGameJutsuRules rules;
        mapping(address => bool) players;
        address[] playersArray;
        uint256 stake;
        bool started;
        bool finished;
    }

    mapping(uint256 => Game) public games;
    uint256 public nextGameId;

    //TODO private game proposal - after the hackathon
    //TODO should gameId be in Game?
    function proposeGame(IGameJutsuRules rules) payable external returns (uint256 gameId) {
        gameId = nextGameId;
        games[gameId].rules = rules;
        games[gameId].players[msg.sender] = true;
        games[gameId].playersArray.push(msg.sender);
        games[gameId].stake = msg.value;
        nextGameId++;
    }


    function acceptGame(uint256 gameId) payable external {
        require(games[gameId].players[msg.sender] == false, "Arbiter: player already in game");
        require(games[gameId].started == false, "Arbiter: game already started");
        require(games[gameId].stake <= msg.value, "Arbiter: stake mismatch");
        games[gameId].players[msg.sender] = true;
        games[gameId].playersArray.push(msg.sender);
        games[gameId].stake += msg.value;
        games[gameId].started = true;
    }

    function disputeMove(SignedMove calldata signedMove) external {
        require(signedMove.signatures.length > 0, "Arbiter: no signatures");
        require(!isValidSignedMove(signedMove), "Arbiter: valid signed move disputed");

        bytes32 signedHash = ECDSA.toEthSignedMessageHash(abi.encode(signedMove.oldGameState, signedMove.newGameState, signedMove.move));
        uint256 gameId = signedMove.oldGameState.gameId;
        for (uint256 i = 0; i < 2; i++) {
            //TODO consider using other signatures
            address signer = ECDSA.recover(signedHash, signedMove.signatures[i]);
            if (games[gameId].players[signer]) {
                disqualifyPlayer(gameId, signer);
                return;
            }
        }
    }

    function initTimeout(SignedMove calldata signedMove) payable external {
        //TODO
    }

    function isValidSignedMove(SignedMove calldata signedMove) private view returns (bool) {
        uint256 gid = signedMove.oldGameState.gameId;
        return gid == signedMove.newGameState.gameId &&
        signedMove.oldGameState.nonce + 1 == signedMove.newGameState.nonce &&
        keccak256(signedMove.oldGameState.state) != keccak256(signedMove.newGameState.state) &&
        games[gid].started &&
        !games[gid].finished &&
        games[gid].rules.isValidMove(signedMove.oldGameState, signedMove.move) &&
        keccak256(games[gid].rules.transition(signedMove.oldGameState, signedMove.move).state) == keccak256(signedMove.newGameState.state);
    }

    function disqualifyPlayer(uint256 gameId, address player) private {
        require(games[gameId].players[player], "Arbiter: player not in game");
        games[gameId].finished = true;
        address winner = games[gameId].playersArray[0] == player ? games[gameId].playersArray[1] : games[gameId].playersArray[0];
        payable(winner).transfer(games[gameId].stake);
    }
}
