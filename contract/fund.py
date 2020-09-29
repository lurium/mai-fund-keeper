from web3 import Web3

from lib.address import Address
from lib.contract import Contract
from lib.wad import Wad
from enum import Enum
from .perpetual import PositionSide

class State(Enum):
     Normal = 0
     Emergency = 1
     Shutdown = 2

class RebalanceTarget():
    def __init__(self, needRebalance: bool, amount: int, side: int):
        assert(isinstance(needRebalance, bool))
        assert(isinstance(amount, int))
        assert(isinstance(side, int))

        self.needRebalance = needRebalance
        self.amount = Wad(amount)
        self.side = PositionSide(side)

class Fund(Contract):
    abi = Contract._load_abi(__name__, '../abi/Fund.abi')

    def __init__(self, web3: Web3, address: Address):
        assert(isinstance(web3, Web3))
        assert(isinstance(address, Address))

        self.web3 = web3
        self.address = address
        self.contract = self._get_contract(web3, self.abi, address)

    def total_supply(self) -> Wad:
        return Wad(self.contract.functions.totalSupply().call())

    def state(self) -> State:
        return State(self.contract.functions.state().call())

    def getRebalanceSlippage(self) -> Wad:
        description = self.contract.functions.description().call()
        return Wad(description[2])


    def rebalanceTarget(self) -> RebalanceTarget:
       targetRes = self.contract.functions.rebalanceTarget().call()
       return RebalanceTarget(targetRes[0], targetRes[1], targetRes[2])

    def rebalance(self, max_amount: Wad, price_limit: Wad, side: int, user: Address, gasPrice: int):
        tx_hash = self.contract.functions.rebalance(max_amount.value, price_limit.value, side).transact({
                    'from': user.address,
                    'gasPrice': gasPrice        
        })
        return tx_hash 

    def redeemingBalance(self, address: Address) -> Wad:
        assert isinstance(address, Address)
        return Wad(self.contract.functions.redeemingBalance(address.address).call())

    def bidRedeemingShare(self, account: Address, amount: Wad, price_limit: Wad, side: int, user: Address, gasPrice: int):
        tx_hash = self.contract.functions.bidRedeemingShare(account.address, amount.value, price_limit.value, side).transact({
                    'from': user.address,
                    'gasPrice': gasPrice                    
        })
        return tx_hash

    def bidSettledShare(self, amount: Wad, price_limit: Wad, side: int, user: Address, gasPrice: int):
        tx_hash = self.contract.functions.bidSettledShare(amount.value, price_limit.value, side).transact({
                    'from': user.address,
                    'gasPrice': gasPrice                        
        })
        return tx_hash

    def netAssetValue(self) -> Wad:
        return Wad(self.contract.functions.netAssetValue().call())

    def netAssetValuePerShare(self) -> Wad:
        return Wad(self.contract.functions.netAssetValuePerShare().call())

    def purchase(self, amount: Wad, price: Wad, share: Wad, user: Address, gasPrice: int):
        tx_hash = self.contract.functions.purchase(amount.value, price.value, share.value).transact({
                    'value': amount.value,
                    'from': user.address,
                    'gasPrice': gasPrice
                })
        return tx_hash
