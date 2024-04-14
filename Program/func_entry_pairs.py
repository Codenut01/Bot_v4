from constants import ZSCORE_THRESH_BUY, ZSCORE_THRESH_SELL, POSITION_SIZE_PCT, MAX_LEVERAGE, USD_MIN_COLLATERAL, TOKEN_FACTOR_10, DYDX_ADDRESS
from func_utils import format_number
from func_public import get_candles_recent
from func_cointegration import calculate_zscore
from func_private import is_open_positions
from func_bot_agent import BotAgent
import pandas as pd
import json
from pprint import pprint

address = DYDX_ADDRESS

# Open positions
def open_positions(client):
    '''
        Manage finding triggers for trade entry
        Store trades for managing later on on exit function
    '''

    # Load cointegrated pairs
    df = pd.read_csv("cointegrated_pairs.csv")

    # Get markets from referencing of min order size, tick size etc
    markets = client.markets.get_perpetual_markets().data

    # Initialize container for BotAgent results
    bot_agent = []

    # Opening JSON file
    try:
        open_positions_file = open("bot_agents.json")
        open_positions_dict = json.load(open_positions_file)

        for p in open_positions_dict:
            bot_agent.append(p)
    except:
        bot_agent = []

    # Find ZSCORE triggers
    for index, row in df.iterrows():

        # Extract variables
        base_market = row["base_market"]
        quote_market = row["quote_market"]
        hedge_ratio = row["hedge_ratio"]
        half_life = row["half_life"]

        # Get prices
        series_1 = get_candles_recent(client, base_market)
        series_2 = get_candles_recent(client, quote_market)

        # Get ZScore
        if len(series_1) > 0 and len(series_1) == len(series_2):
            spread = series_1 - (hedge_ratio * series_2)
            z_score = calculate_zscore(spread).values.tolist()[-1]

            # Establish if potential trade
            if (abs(z_score) > ZSCORE_THRESH_BUY and z_score < 0) or (abs(z_score) > ZSCORE_THRESH_SELL and z_score > 0):

                # Ensure like-for-like not already open (diversify trading)
                is_base_open = is_open_positions(client, base_market)
                is_quote_open = is_open_positions(client, quote_market)

                # Place trade
                if not is_base_open and not is_quote_open:

                    # Determine side
                    base_side = "BUY" if z_score < 0 else "SELL"
                    quote_side = "BUY" if z_score > 0 else "SELL"

                    # Get acceptable price in string format with correct number of decimals
                    # If there is the needs, call the API again to get the latest price
                    base_price = series_1[-1]
                    quote_price = series_2[-1]

                    # If ZScore is less than zero meaning the base market is a "BUY"
                    # then the price needs to be higher than the current price
                    # and vice versa
                    accept_base_price = float(base_price) * 1.01 if z_score < 0 else float(base_price) * 0.99
                    accept_quote_price = float(quote_price) * 1.01 if z_score > 0 else float(quote_price) * 0.99

                    # Ridiculous failsafe price to make sure filled
                    failsafe_base_price = float(base_price) * 0.05 if z_score < 0 else float(base_price) * 1.50
                    base_tick_size = markets["markets"][base_market]["tickSize"]
                    quote_tick_size = markets["markets"][quote_market]["tickSize"]

                    # Format prices
                    accept_base_price = format_number(accept_base_price, base_tick_size)
                    accept_quote_price = format_number(accept_quote_price, quote_tick_size)
                    accept_failsafe_base_price = format_number(failsafe_base_price, base_tick_size)

                    # Get account and position size
                    account = client.account.get_subaccount(address, 0)
                    free_collateral = float(account.data["subaccount"]["freeCollateral"])
                    max_position_size = free_collateral * POSITION_SIZE_PCT
                    base_quantity = max_position_size / base_price
                    quote_quantity = max_position_size / quote_price
                    base_step_size = markets["markets"][base_market]["stepSize"]
                    quote_step_size = markets["markets"][quote_market]["stepSize"]

                    # Adjust position size based on leverage
                    base_size = format_number(base_quantity / MAX_LEVERAGE, base_step_size)
                    quote_size = format_number(quote_quantity / MAX_LEVERAGE, quote_step_size)

                    ## MODIFIED
                    for particolari in TOKEN_FACTOR_10:
                        if base_market == particolari:
                            base_quantity = float(int(base_quantity / 10) * 10)
                        if quote_market == particolari:
                            quote_quantity = float(int(quote_quantity / 10) * 10)

                    base_min_order_size = markets["markets"][base_market]["stepSize"]
                    quote_min_order_size = markets["markets"][quote_market]["stepSize"]
                    check_base = float(base_quantity) > float(base_min_order_size)
                    check_quote = float(quote_quantity) > float(quote_min_order_size)

                    # If check pass, place trades
                    if check_base and check_quote:

                        # Check account balance
                        free_collatoral = float(account.data["subaccount"]["freeCollateral"])
                        print(f'Balance: {free_collatoral} and minimum at {USD_MIN_COLLATERAL}')

                        # Guard: Ensure collateral
                        if free_collatoral < USD_MIN_COLLATERAL:
                            break

                        # Create BotAgent
                        bot_agents = BotAgent(
                            client,
                            market_1=base_market,
                            market_2=quote_market,
                            base_side=base_side,
                            base_size=base_size,
                            base_price=accept_base_price,
                            quote_side=quote_side,
                            quote_size=quote_size,
                            quote_price=accept_quote_price,
                            accept_failsafe_base_price=accept_failsafe_base_price,
                            z_score=z_score,
                            half_life=half_life,
                            hedge_ratio=hedge_ratio
                        )

                        # Open Trades
                        bot_open_dict = bot_agents.open_trades()

                        # Handles success in opening trades
                        if bot_open_dict["pair_status"] == "LIVE":

                            # Append to list of bot agents
                            bot_agent.append(bot_open_dict)
                            del(bot_open_dict)

                            # Confirm live status in trade
                            print("Trade status: Live")
                            print("---")
    # Save agents
    print(f"Success: Manage Open Trade Checked")
    if len(bot_agent) > 0:
        with open("bot_agents.json", "w") as outfile:
            json.dump(bot_agent, outfile)
