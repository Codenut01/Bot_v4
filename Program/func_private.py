from datetime import datetime, timedelta
from random import randrange
from retry import retry
from v4_client_py.clients.helpers.chain_helpers import (
    OrderExecution,
    OrderSide,
    OrderTimeInForce,
    OrderType,
)
from constants import DYDX_MNEMONIC, DYDX_ADDRESS
from v4_client_py.chain.aerial.wallet import LocalWallet
from v4_client_py.clients import Subaccount, CompositeClient
from v4_client_py.clients.constants import BECH32_PREFIX, Network
from func_messaging import send_message

class APIError(Exception):
    pass

class NetworkError(Exception):
    pass

class ExchangeError(Exception):
    pass

@retry(exceptions=(APIError, NetworkError, ExchangeError), tries=3, delay=1)
def place_market_order(client, market, side, size, price, reduce_only):
    wallet = LocalWallet.from_mnemonic(DYDX_MNEMONIC, BECH32_PREFIX)
    network = Network.config_network()
    composite_client = CompositeClient(network)

    # Implement rate limiting and backoff strategy
    try:
        server_time = client.utility.get_time()
        expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z','+00:00')) + timedelta(seconds=70)
        side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
        placed_order = composite_client.place_order(
            Subaccount(wallet, 0),
            client_id=randrange(0, 100000000),
            market=market,
            side=side,
            type=OrderType.MARKET,
            post_only=False,
            size=float(size),
            price=float(price),
            good_til_time_in_seconds=int(expiration.timestamp()),
            time_in_force=OrderTimeInForce.FOK,
            good_til_block=composite_client.get_current_block() + 20,
            execution=OrderExecution.DEFAULT,
            reduce_only=reduce_only
        )
        return placed_order
    except (APIError, NetworkError, ExchangeError) as e:
        print(f"Error placing order for {market}: {e}")
        raise e

def check_order_status(client, order_id):
    try:
        order = client.account.get_order(order_id)
        if order.data is not None and "order" in order.data.keys():
            return order.data['order']['status']
    except (APIError, NetworkError, ExchangeError) as e:
        print(f"Error checking order status for order ID {order_id}: {e}")
        raise e
    return "FAILED"

def is_open_positions(client, market):
    try:
        exchange_pos = client.account.get_subaccount_perpetual_positions(DYDX_ADDRESS, 0, status="OPEN")
        for position in exchange_pos.data["positions"]:
            if position["ticker"] == market:
                return True
    except (APIError, NetworkError, ExchangeError) as e:
        print(f"Error checking open positions for {market}: {e}")
        raise e
    return False
