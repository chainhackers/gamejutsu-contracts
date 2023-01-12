#   ________                           ____.       __
#  /  _____/_____    _____   ____     |    |__ ___/  |_  ________ __
# /   \  ___\__  \  /     \_/ __ \    |    |  |  \   __\/  ___/  |  \
# \    \_\  \/ __ \|  Y Y  \  ___//\__|    |  |  /|  |  \___ \|  |  /
#  \______  (____  /__|_|  /\___  >________|____/ |__| /____  >____/
#         \/     \/      \/     \/                          \/
# https://gamejutsu.app
# ETHOnline2022 submission by ChainHackers
__author__ = ["Gene A. Tsvigun"]
__license__ = "MIT"

from brownie import Arbiter, CheckersRules, TicTacToeRules, accounts


# brownie run scripts/deploy.py --network polygon-main
def main():
    deployer = accounts.load('gamejutsu_deployer')
    # tic_tac_toe_rules = deployer.deploy(TicTacToeRules,
    #                                     publish_source=True,
    #                                     )
    # checkers_rules = deployer.deploy(CheckersRules,
    #                                  publish_source=True,
    #                                  )
    # arbiter = deployer.deploy(Arbiter,
    #                           publish_source=True,
    #                           )
