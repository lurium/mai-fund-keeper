from contract.perpetual import PositionSide
from lib.wad import Wad


def compute_AMM_amount(amm_available_margin: Wad, fair_price: Wad, amm_position_size: Wad, trade_side: int, price: Wad):
    if trade_side == PositionSide.LONG:
        if price < fair_price:
            raise Exception(f'buy price {price} is less than the amm fair price {fair_price}')
        return amm_position_size - (amm_available_margin / price)
    else:
        if price > fair_price:
            raise Exception(f'sell price {price} is greater than the amm fair price {fair_price}')
        return amm_available_margin / price - amm_position_size

def compute_AMM_inverse_price(amm_available_margin: Wad, amm_position_size: Wad, trade_side: int, amount: Wad):
    if trade_side == PositionSide.SHORT:
        if amount >= amm_position_size:
            raise Exception(f'sell inverse amount {amount} is greater than the amm position size {amm_position_size}')
        return (amm_position_size - amount) / amm_available_margin

    else:
        return (amm_position_size + amount) / amm_available_margin

def compute_AMM_price(amm_available_margin: Wad, amm_position_size: Wad, trade_side: PositionSide, amount: Wad):
    if trade_side == PositionSide.LONG:
        if amount >= amm_position_size:
            raise Exception(f'buy amount {amount} is greater than the amm position size {amm_position_size}')
        return amm_available_margin / (amm_position_size - amount)
    else:
        return amm_available_margin / (amm_position_size + amount)