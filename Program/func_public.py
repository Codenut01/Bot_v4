import requests_cache
import asyncio
import numpy as np
import pandas as pd
from func_utils import get_ISO_times
from constants import RESOLUTION

# Get revelant time periods for ISO from and to
ISO_TIMES = get_ISO_times()

# Set up caching
requests_cache.install_cache('dydx_cache', expire_after=300)

async def get_candles_historical(client, market):
    # Use cached responses
    with requests_cache.disabled():
        candles = client.markets.get_perpetual_market_candles(
            market=market,
            resolution=RESOLUTION,
            from_iso=ISO_TIMES["range_1"]["from_iso"],
            to_iso=ISO_TIMES["range_1"]["to_iso"],
            limit=100
        )
    close_prices = [candle["close"] for candle in candles.data['candles']]
    close_prices.reverse()
    return close_prices

async def get_candles_recent(client, market):
    # Use cached responses
    with requests_cache.disabled():
        candles = client.markets.get_perpetual_market_candles(
            market=market,
            resolution=RESOLUTION,
            limit=100
        )
    close_prices = [candle["close"] for candle in candles.data['candles']]
    close_prices.reverse()
    return np.array(close_prices).astype(np.float)

async def construct_market_prices(client):
    tradeable_markets = []
    markets = client.markets.get_perpetual_markets()

    for market in markets.data['markets'].keys():
        market_info = markets.data['markets'][market]
        if market_info['status'] == 'ACTIVE':
            tradeable_markets.append(market)

    tasks = []
    for market in tradeable_markets:
        tasks.append(asyncio.create_task(get_candles_historical(client, market)))
    results = await asyncio.gather(*tasks)

    df = pd.DataFrame()
    for i, market in enumerate(tradeable_markets):
        df[market] = results[i]

    nans = df.columns[df.isna().any()].tolist()
    if len(nans) > 0:
        print("Dropping columns: ")
        print(nans)
        df.drop(columns=nans, inplace=True)

    return df
