from web3 import Web3
import time

from lib.address import Address
from lib.contract import Contract
from lib.wad import Wad

class AMM(Contract):
    abi = Contract._load_abi(__name__, '../abi/AMM.abi')

    def __init__(self, web3: Web3, address: Address):
        assert(isinstance(web3, Web3))
        assert(isinstance(address, Address))

        self.web3 = web3
        self.address = address
        self.contract = self._get_contract(web3, self.abi, address)

    def current_fair_price(self, user: Address) -> Wad:
        return Wad(self.contract.functions.currentFairPrice().call({'from': user.address}))

    def perpetualProxy(self, user: Address) -> Address:
        return Address(self.contract.functions.perpetualProxy().call({'from': user.address}))

    def position_size(self) -> Wad:
        return Wad(self.contract.functions.positionSize().call())

    def current_available_margin(self) -> Wad:
        return Wad(self.contract.functions.currentAvailableMargin().call())

    def buy(self, amount: Wad, price: Wad, deadline: int, user: Address, gasPrice: int):
        assert isinstance(amount, Wad)
        assert isinstance(price, Wad)
        assert isinstance(deadline, int)

        tx_hash = self.contract.functions.buy(amount.value, price.value, deadline).transact({
                    'from': user.address,
                    'gasPrice': gasPrice
                })
        return tx_hash

    def sell(self, amount: Wad, price: Wad, deadline: int, user: Address, gasPrice: int):
        assert isinstance(amount, Wad)
        assert isinstance(price, Wad)
        assert isinstance(deadline, int)

        tx_hash = self.contract.functions.sell(amount.value, price.value, deadline).transact({
                    'from': user.address,
                    'gasPrice': gasPrice
                })
        return tx_hash