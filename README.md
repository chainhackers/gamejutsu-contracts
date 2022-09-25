# gamejutsu-contracts
GameJutsu framework to create on-chain arbiters for state channel based games

### Polygon mainnet contracts
Arbiter 👩🏽‍⚖️
https://polygonscan.com/address/0x1f0b6DB015198028d57Eb89785Fc81637f1e72F5

TicTacToeRules ❎0️⃣ 
https://polygonscan.com/address/0xC6F81d6610A0b1bcb8cC11d50602D490b7624a96

CheckersRules 🙾🙾🙾🙾
https://polygonscan.com/address/0x6eDe6F6f1ACa5e7A3bdc403EA0ca9889e2095486

### Entities
- The arbiter is a contract that is deployed on the blockchain and is used to resolve disputes between players.

## Differences with Magmo's ForceMove

### Movers and turns    

ForceMove protocol: the mover is fully determined by the turn number
> definition of `State::mover` introduces an important design decision of the ForceMove protocol:
> that the mover is fully determined by the turn number. Informally, using the fact that 
> `s.turnNum` must be incremented by 1, this rule states that players must take turns in a cyclical order.

GameJutsu protocol: the mover is determined by the game rules

### Simplifications
* Outcomes: win/loss or draw, in case of a draw the funds are split between the players

[//]: # (### Memos)
[//]: # (alternate moves)
