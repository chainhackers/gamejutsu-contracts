# gamejutsu-contracts
[GameJutsu](https://github.com/chainhackers/GameJutsu) is a way to create on-chain arbiters for state channel based games, so that multiplayer games can have rules enforced by on-demand on-chain verification instead of involving a centralized server or a smart-contract to verify every move

### Polygon mainnet contracts
Arbiter 👩🏽‍⚖️
https://polygonscan.com/address/0xE3Dc7e9e1b57A4c91546b391e5Eb31f8B630122E

TicTacToeRules ❎0️⃣ 
https://polygonscan.com/address/0xC6F81d6610A0b1bcb8cC11d50602D490b7624a96

CheckersRules 🙾🙾🙾🙾
https://polygonscan.com/address/0xDcA61577312eb61f7Ee815085040A165c6F28bAf

### Entities
- The Arbiter is a contract that is deployed on the blockchain and is used to resolve disputes between players.
- Game Rules are defined by the game developer and are used by the Arbiter to determine the validity of moves and to transition the game state.
- The Game Client is a piece of software that is used by the players to play the game. It is responsible for exchanging moves with the opponent,  and for signing them. 
## Differences with Magmo's ForceMove

### Movers and turns    

ForceMove protocol: the mover is fully determined by the turn number
> definition of `State::mover` introduces an important design decision of the ForceMove protocol:
> that the mover is fully determined by the turn number. Informally, using the fact that 
> `s.turnNum` must be incremented by 1, this rule states that players must take turns in a cyclical order.

GameJutsu protocol: the mover is determined by the game rules

### Simplifications
* Outcomes: win/loss or draw, in case of a draw the funds are split between the players
* Only 2 players are supported
* The hackathon submission version of the Arbiter includes sample game service functionality - i.e. game proposals, stake collection, logging game events. Real life game services should take care of these things themselves.
* No alternate moves are not supported - i.e. the game state is not a tree, but a linear sequence of states, game clients don't offer alternate moves to each other.

[//]: # (### Memos)
[//]: # (alternate moves)
