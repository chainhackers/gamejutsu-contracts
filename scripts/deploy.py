from brownie import Arbiter, TicTacToeRules, accounts


# brownie run scripts/deploy.py --network polygon-main
def main():
    deployer = accounts.load('gamejutsu_deployer')
    tic_tac_toe_rules = deployer.deploy(TicTacToeRules,
                                        publish_source=True,
                                        )
    arbiter = deployer.deploy(Arbiter,
                              publish_source=True,
                              )
