# gamejutsu-contracts
GameJutsu framework to create on-chain arbiters for state channel based games

### Polygon mainnet contracts
Arbiter 👩🏽‍⚖️
https://polygonscan.com/address/0x91EB2BAc4946A88F0c40A4fc220E8aDbf18d378F

TicTacToeRules ❎0️⃣ 
https://polygonscan.com/address/0x461A1001D303F83eB02A921016C8A6beD0469e89

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
