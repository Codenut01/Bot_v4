import logging
import pandas as pd
from prometheus_client import start_http_server, Gauge
from func_connections import connect_to_dydx
from constants import FIND_COINTEGRATED_PAIRS, RESOLUTION, PLACE_TRADES, MANAGE_EXITS
from func_public import construct_market_prices
from func_cointegration import store_cointegration_results
from func_entry_pairs import open_positions
from func_exit_pairs import manage_trade_exits
from func_messaging import send_message
import psutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# Set up Prometheus metrics
order_success_rate = Gauge('dydx_order_success_rate', 'Order success rate')
trade_profitability = Gauge('dydx_trade_profitability', 'Trade profitability')
resource_utilization = Gauge('dydx_resource_utilization', 'Resource utilization')

# Start the Prometheus HTTP server
start_http_server(8000)

if __name__ == "__main__":
    # Message on start
    send_message("Bot launch successful")

    # Connect to Client
    try:
        logging.info("Connecting to client...")
        client = connect_to_dydx()
    except Exception as e:
        logging.error(f"Error connected to client: {e}")
        send_message(f"Failed to connect to client {e}")
        exit(1)

    # Find Cointegrated Pairs
    if FIND_COINTEGRATED_PAIRS:
        try:
            logging.info("Fetching Market Prices, please allow 3 mins...")
            df_market_prices = construct_market_prices(client)
            logging.info("Storing cointegrated pairs...")
            store_cointegration_results(df_market_prices)
            df_csv = pd.read_csv("cointegrated_pairs.csv")
            logging.info(f"Cointegrated pairs CSV produced given {RESOLUTION} window with {len(df_csv)} results!")
        except Exception as e:
            logging.error(f"Error: {e}")
            send_message(f"Error saving cointegrated pairs {e}")
            exit(1)

    while True:
        # Measure resource utilization
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        resource_utilization.set(cpu_percent + memory_percent)

        # Manage exits and place trades
        if MANAGE_EXITS:
            try:
                logging.info("Managing exits...")
                manage_trade_exits(client)
            except Exception as e:
                logging.error(f"Error managing exiting positions: {e}")
                send_message(f"Error managing exit positions {e}")
                exit(1)

        if PLACE_TRADES:
            try:
                logging.info("Finding trading opportunities...")
                open_positions(client)
            except TypeError as e:
                logging.warning("Error: 'NoneType' object is not subscriptable")
            except Exception as e:
                logging.error(f"Error trading pairs: {e}")
                send_message(f"Error opening trades {e}")
                exit(1)
