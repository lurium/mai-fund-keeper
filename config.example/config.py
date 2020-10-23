import os

# eth node rpc request
ETH_RPC_URL = os.environ.get('ETH_RPC_URL', 'http://localhost:8545')

# timeout for get transaction receipt(second)
TX_TIMEOUT = int(os.environ.get('TX_TIMEOUT', 300))
KEEPER_KEY_FILE = os.environ.get('KEEPER_KEY_FILE', '')

# gas price
GAS_LEVEL = os.environ.get('GAS_LEVEL', 'fast')
ETH_GAS_URL = os.environ.get('ETH_GAS_URL', 'https://ethgasstation.info/api/ethgasAPI.json')

# contract address
PERP_ADDRESS = os.environ.get('PERP_ADDRESS', '0x0D1dB4ef31ebe69c4e91BA703A829Ca0Ae49C534')
AMM_ADDRESS = os.environ.get('AMM_ADDRESS', '0x3ff04fc4aff4ba070cbb2a0cf9603919827ae78a')
COLLATERAL_TOKEN = os.environ.get('COLLATERAL_TOKEN', '0x0000000000000000000000000000000000000000')
FUND_ADDRESS = os.environ.get('FUND_ADDRESS', '0xA8cD84eE8aD8eC1c7ee19E578F2825cDe18e56d1')

#fund-graph
FUND_GRAPH_URL = os.environ.get('FUND_GRAPH_URL', 'https://api.thegraph.com/subgraphs/name/mcdexio/mcfund-mainnet')

# mcdex
MARKET_ID = os.environ.get('MARKET_ID', 'ETHPERP')
MCDEX_URL = os.environ.get('MCDEX_URL', 'https://mcdex.io/api')
POSITION_LIMIT = int(os.environ.get('POSITION_LIMIT', 12000))
LEVERAGE = float(os.environ.get('LEVERAGE', 5))
# notice, INVERSE must be True or False
INVERSE = eval(os.environ.get('INVERSE', 'True'))
LOT_SIZE = int(os.environ.get('LOT_SIZE', 10))
MIN_LIQUIDATE_SIZE = int(os.environ.get('MIN_LIQUIDATE_SIZE', 1000))
# notice, CLOSE_IN_AMM must be True or False
CLOSE_IN_AMM = eval(os.environ.get('CLOSE_IN_AMM', 'True'))
DEADLINE = int(os.environ.get('DEADLINE', 120))
PRICE_SLIPPAGE = float(os.environ.get('PRICE_SLIPPAGE', 0.01))

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "simple": {
            "format": "%(asctime)s %(levelname)-7s - %(message)s - [%(filename)s:%(lineno)d:%(funcName)s]",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "filename": "./log/fund_keeper.log",
            "maxBytes": 104857600, # 100MB
            "backupCount": 7,
            "encoding": "utf8"
        },
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console"],
    }
}