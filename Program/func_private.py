import time
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
        return placed_order.tx_hash
        print(f"Order placed for {market}, size {size} at price {price}")
        send_message(f"Order placed for {market}, size {size} at price {price}")
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

# Get existing open positions
def is_open_positions(client, market):
    address = DYDX_ADDRESS

    # Protect API
    time.sleep(0.2)

    # Get positions
    all_positions = client.account.get_subaccount_perpetual_positions(address, 0, status="OPEN")

    # Determine if open
    if len(all_positions.data['positions']) > 0:
        return True
    else:
        return False
