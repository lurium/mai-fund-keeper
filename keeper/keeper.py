import logging
import logging.config
import time
import json
import requests
import threading
import math

from web3 import Web3, HTTPProvider, middleware
import eth_utils
from eth_utils import encode_hex
from eth_account import Account
from web3.middleware import construct_sign_and_send_raw_middleware, geth_poa_middleware

import config
from lib.address import Address
from lib.wad import Wad
from mcdex import Mcdex
from watcher import Watcher
from contract.amm import AMM
from contract.perpetual import Perpetual, PositionSide, Status
from contract.token import ERC20Token
from contract.fund import Fund, State
from .computation import compute_AMM_price

class Keeper:
    logger = logging.getLogger()

    def __init__(self, args: list, **kwargs):
        logging.config.dictConfig(config.LOG_CONFIG)
        self.keeper_account = None
        self.keeper_account_key = ""
        self.web3 = Web3(HTTPProvider(endpoint_uri=config.ETH_RPC_URL))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.gas_price = self.web3.toWei(10, "gwei")

        # contract 
        self.perp = Perpetual(web3=self.web3, address=Address(config.PERP_ADDRESS))
        self.token = ERC20Token(web3=self.web3, address=Address(config.COLLATERAL_TOKEN))
        self.AMM = AMM(web3=self.web3, address=Address(config.AMM_ADDRESS))
        self.fund = Fund(web3=self.web3, address=Address(config.FUND_ADDRESS))

        # mcdex for orderbook
        self.mcdex = Mcdex(config.MCDEX_URL, config.MARKET_ID)

        # watcher
        self.watcher = Watcher(self.web3)

    def get_gas_price(self):
        try:
            resp = requests.get(config.ETH_GAS_URL, timeout=30)
            if resp.status_code / 100 == 2:
                rsp = json.loads(resp.content)
                gas_price = self.web3.toWei(rsp.get(config.GAS_LEVEL) / 10, "gwei")
                self.gas_price = gas_price
                self.logger.info(f"new gas price: {self.gas_price}")
        except Exception as e:
            self.logger.fatal(f"get gas price error {e}")


    def _check_account_balance(self):
        self.get_gas_price()
        if self.token.address != Address('0x0000000000000000000000000000000000000000'):
            allowance = self.token.allowance(self.keeper_account, self.perp.address)
            self.logger.info(f"address:{self.keeper_account} allowance:{allowance}")

            if allowance.value == 0:
                self.token.approve(self.perp.address, self.keeper_account)
            margin_account = self.perp.getMarginAccount(self.keeper_account)
            self.logger.info(f"address:{self.keeper_account} cash_balance:{margin_account.cash_balance}")
            if margin_account.cash_balance.value == 0:
                self.logger.error(f"your cash balance is {margin_account.cash_balance}, please deposit enough balance in perpetual contract {self.perp.address}")
                return False
        else:
            eth_balance = self.web3.eth.getBalance(self.keeper_account.address)
            self.logger.info(f"address:{self.keeper_account} eth_balance:{eth_balance}")
            margin_account = self.perp.getMarginAccount(self.keeper_account)
            self.logger.info(f"address:{self.keeper_account} cash_balance:{margin_account.cash_balance}")
            if margin_account.cash_balance.value == 0:
                #self.perp.depositEther(100, address, self.gas_price)
                self.logger.error(f"your cash balance is {margin_account.cash_balance}, please deposit enough balance in perpetual contract {self.perp.address}")
                return False

        return True

    def _check_keeper_account(self):
        with open(config.KEEPER_KEY_FILE) as f:
            read_key = f.read().replace("\n","")

        # check account with key
        try:
            account = Account()
            acct = account.from_key(read_key)
            self.web3.middleware_onion.add(construct_sign_and_send_raw_middleware(acct))
            self.keeper_account = Address(acct.address)
            self.keeper_account_key = read_key
        except Exception as e:
            self.logger.warning(f"check private key error: {e}")
            return False
            
        return True

    def _check_keeper_account_position(self):
        # close position in amm
        if config.CLOSE_IN_AMM:
            self._close_position_in_AMM()
            return

        # close position in orderbook
        self.mcdex.set_wallet(self.keeper_account_key, self.keeper_account)
        margin_account = self.perp.getMarginAccount(self.keeper_account)
        size = int(margin_account.size)
        if size < config.POSITION_LIMIT:
            return

        # skip if active orders exist
        try:
            active_orders = self.mcdex.get_active_orders()
            if len(active_orders) > 0:
                self.logger.info(f"active orders exist. address:{self.keeper_account.address}")
                return
        except Exception as e:
            self.logger.fatal(f"close position in mcdex failed. address:{self.keeper_account.address} error:{e}")
            return
        
        side = "buy" if margin_account.side == PositionSide.SHORT else "sell"
        if config.INVERSE:
            side = "sell" if margin_account.side == PositionSide.SHORT else "buy"

        try:
            self.mcdex.place_order(str(size), "market", "0", side, 300, str(config.LEVERAGE))
        except Exception as e:
            self.logger.fatal(f"close position in mcdex failed. address:{self.keeper_account.address} error:{e}")
        return

    def _check_balance(self):
        try:
            target = self.fund.rebalanceTarget()
            if target.needRebalance:
                if int(target.amount) < config.POSITION_LIMIT:
                    self.logger.info(f"rebalance amount to small. amount:{target.amount}")
                    return

                # price_limit = self._get_rebalance_trade_price(target.side)
                price_limit = self.perp.markPrice()
                self.get_gas_price()
                side = 2 if target.side == PositionSide.LONG else 1
                tx_hash = self.fund.rebalance(target.amount, price_limit, side, self.keeper_account, self.gas_price)
                transaction_status = self._wait_transaction_receipt(tx_hash, 10)
                if transaction_status:
                    self.logger.info(f"rebalance success. amount:{target.amount}")
                else:
                    self.logger.info(f"rebalance fail. amount:{target.amount}")
        except Exception as e:
                self.logger.fatal(f"check rebalance fail. error:{e}")

    def _get_rebalance_trade_price(self, side):
        slippage = self.fund.getRebalanceSlippage()
        mark_price = self.perp.markPrice()
        price_loss = mark_price*slippage
        trade_price = mark_price
        if side == PositionSide.LONG:
            trade_price = mark_price + price_loss
        else:
            trade_price = mark_price - price_loss
        return trade_price

    def _get_redeeming_accounts(self):
        user_list = []
        query = '''
            {
                userInFunds(where: {fund: "%s", redeemingShareAmount_gt: 0}) {
                    redeemingShareAmount
                    user{
                        id
                    }
                }
            }
        ''' % (config.FUND_ADDRESS.lower())
        res = requests.post(config.FUND_GRAPH_URL, json={'query': query}, timeout=10)
        if res.status_code == 200:
            user_in_funds = res.json()['data']['userInFunds']
            for user_in_fund in user_in_funds:
                user_list.append(Address(user_in_fund['user']['id']))
        return user_list

    def _check_redeeming_accounts(self):
        fund_state = self.fund.state()
        if fund_state == State.Normal:
            try:
                fundMarginAccount = self.perp.getMarginAccount(Address(config.FUND_ADDRESS))
                redeeming_accounts = self._get_redeeming_accounts()
                for account in redeeming_accounts:
                    price_limit = self._get_redeem_trade_price(fundMarginAccount.side)
                    share_amount = self.fund.redeemingBalance(account)
                    if share_amount > Wad(0):
                        side = 2 if fundMarginAccount.side == PositionSide.LONG else 1
                        tx_hash = self.fund.bidRedeemingShare(account, share_amount, price_limit, side , self.keeper_account, self.gas_price)
                        transaction_status = self._wait_transaction_receipt(tx_hash, 10)
                        if transaction_status:
                            self.logger.info(f"bidRedeemingShare success. amount:{share_amount}")
                        else:
                            self.logger.info(f"bidRedeemingShare fail. amount:{share_amount}")
            except Exception as e:
                self.logger.fatal(f"_check_redeeming_accounts bidRedeemingShare fail. error:{e}")
        elif fund_state == State.Emergency:
            try:
                fundMarginAccount = self.perp.getMarginAccount(Address(config.FUND_ADDRESS))
                # price_limit = self._get_redeem_trade_price(fundMarginAccount.side)
                price_limit = self.perp.markPrice()
                total_supply = self.fund.total_supply()
                self.get_gas_price()
                side = 2 if fundMarginAccount.side == PositionSide.LONG else 1
                tx_hash = self.fund.bidSettledShare(total_supply, price_limit, side, self.keeper_account, self.gas_price)
                transaction_status = self._wait_transaction_receipt(tx_hash, 10)
                if transaction_status:
                    self.logger.info(f"bidSettledShare success. amount:{total_supply}")
                else:
                    self.logger.info(f"bidSettledShare fail. amount:{total_supply}")
            except Exception as e:
                self.logger.fatal(f"_check_redeeming_accounts emergency fail. error:{e}")


    def _get_redeem_trade_price(self, side):
        slippage = self.fund.getRebalanceSlippage()
        mark_price = self.perp.markPrice()
        price_loss = mark_price*slippage
        trade_price = mark_price
        if side == PositionSide.LONG:
            trade_price = mark_price - price_loss
        else:
            trade_price = mark_price + price_loss
        return trade_price


    def _wait_transaction_receipt(self, tx_hash, times):
        self.logger.info(f"tx_hash:{self.web3.toHex(tx_hash)}")
        for i in range(times):
            try:
                tx_receipt = self.web3.eth.waitForTransactionReceipt(tx_hash, config.TX_TIMEOUT)
                self.logger.info(tx_receipt)
                status = tx_receipt['status']

                if status == 0:
                    # transaction failed
                    return False
                elif status == 1:
                    # transaction success
                    return True
            except:
                try:
                    # transaction pending, set new gas price
                    self.get_gas_price()
                    tx_hash = self.web3.eth.modifyTransaction(tx_hash, gasPrice=self.gas_price)
                    self.logger.info(f"new tx_hash:{self.web3.toHex(tx_hash)} retry times:{i+1}")
                except Exception as e:
                    self.logger.info(f"set new price err: {e}")
                    time.sleep(5)
                    continue

    def _get_keeper_liquidate_amount(self, keeper_account):
        markPrice = self.perp.markPrice()
        availableMargin = self.perp.getAvailableMargin(keeper_account)
        if config.INVERSE:
            markPrice = Wad.from_number(1)/markPrice
        amount = int(availableMargin * Wad.from_number(config.LEVERAGE) * markPrice)
        amount = math.floor(amount/config.LOT_SIZE)*config.LOT_SIZE
        return Wad.from_number(amount)

    def _get_calculate_liquidate_amount(self, address):
        markPrice = self.perp.markPrice()
        cal_amount = int(self.perp.calculateLiquidateAmount(address, markPrice))
        cal_amount = math.ceil(cal_amount/config.LOT_SIZE)*config.LOT_SIZE
        return Wad.from_number(cal_amount)

    def _close_position_in_AMM(self):
        margin_account = self.perp.getMarginAccount(self.keeper_account)
        size = int(margin_account.size)
        if size < config.POSITION_LIMIT:
            return

        deadline = int(time.time()) + config.DEADLINE
        amm_available_margin = self.AMM.current_available_margin()
        self.logger.info(f"amm_available_margin:{amm_available_margin}")
        amm_position_size = self.AMM.position_size()
        self.logger.info(f"amm_position_size:{amm_position_size}")

        trade_side = PositionSide.LONG if margin_account.side == PositionSide.SHORT else PositionSide.SHORT
        try:
            trade_price = compute_AMM_price(amm_available_margin, amm_position_size, trade_side, margin_account.size)
            self.logger.info(f"compute_price:{trade_price}")
        except Exception as e:
            self.logger.fatal(f"compute amm price failed. error:{e}")
            return
        trade_price = trade_price*Wad.from_number(1 - config.PRICE_SLIPPAGE) if trade_side == PositionSide.SHORT else trade_price*Wad.from_number(1 + config.PRICE_SLIPPAGE)

        tx_hash = None
        try:
            if trade_side == PositionSide.LONG:
               tx_hash = self.AMM.buy(margin_account.size, trade_price, deadline, self.keeper_account, self.gas_price)
            else:
               tx_hash = self.AMM.sell(margin_account.size, trade_price, deadline, self.keeper_account, self.gas_price)
            self.logger.info(f"close in AMM success. price:{trade_price} size{margin_account.size}")
            # wait transaction times is 1, cause amm transaction deadline is 120s, if wait timeout, transaction will fail, no need to add gas price
            transaction_status = self._wait_transaction_receipt(tx_hash, 1)
            if transaction_status:
                self.logger.info(f"close position in AMM success. price:{trade_price} size:{margin_account.size}")
            else:
                self.logger.info(f"close position in AMM fail. price:{trade_price} amount:{margin_account.size}")
        except Exception as e:
                self.logger.fatal(f"close position in AMM failed. price:{trade_price} size:{margin_account.size} error:{e}")

    def main(self):
        if self._check_keeper_account() and self._check_account_balance():
            self.watcher.add_block_syncer(self._check_balance)
            self.watcher.add_block_syncer(self._check_redeeming_accounts)
            self.watcher.run()
