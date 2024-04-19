'''
Calculate max_half_life,optimal_zscore_threshold and optimal_window
'''

import pandas as pd
import numpy as np
from func_backtest_cointegration import calculate_cointegration, calculate_zscore, calculate_half_life
from func_public import construct_market_prices
from func_connections import connect_to_dydx
from constants import MAX_HALF_LIFE, WINDOW, ZSCORE_THRESH

def calculate_sharpe_ratio(spread):
    """
    Calculate the Sharpe ratio of the given spread.
    """
    returns = spread.pct_change()
    sharpe_ratio = returns.mean() / returns.std()
    return sharpe_ratio

def calculate_drawdown(spread):
    """
    Calculate the maximum drawdown of the given spread.
    """
    cumulative_returns = (1 + spread.pct_change()).cumprod()
    max_value = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - max_value) / max_value
    return drawdown.min()

if __name__ == "__main__":
    # Connect to the dYdX client
    client = connect_to_dydx()

    # Construct the market price data
    df_market_prices = construct_market_prices(client)

    # Initialize the list to store the best performing pairs
    markets = df_market_prices.columns.tolist()
    best_pairs = []

    # Iterate through all possible pairs and find the optimal parameters
    for i in range(len(markets)):
        for j in range(i + 1, len(markets)):
            base_market = markets[i]
            quote_market = markets[j]
            coint_flag, hedge_ratio, half_life, optimal_window = calculate_cointegration(df_market_prices[base_market], df_market_prices[quote_market])

            if coint_flag == 1 and half_life > 0:
                spread = df_market_prices[base_market] - (hedge_ratio * df_market_prices[quote_market])
                z_score = calculate_zscore(spread, optimal_window)
                sharpe_ratio = calculate_sharpe_ratio(spread)
                drawdown = calculate_drawdown(spread)

                best_pairs.append({
                    "base_market": base_market,
                    "quote_market": quote_market,
                    "hedge_ratio": hedge_ratio,
                    "half_life": half_life,
                    "optimal_window": optimal_window,
                    "sharpe_ratio": sharpe_ratio,
                    "drawdown": drawdown
                })

    # Calculate the optimal values
    max_half_life = max([pair['half_life'] for pair in best_pairs])
    optimal_window = max([pair['optimal_window'] for pair in best_pairs])
    optimal_zscore_thresh = max([abs(calculate_zscore(df_market_prices[pair['base_market']] - (pair['hedge_ratio'] * df_market_prices[pair['quote_market']]), pair['optimal_window']).max()) for pair in best_pairs])

    MAX_HALF_LIFE = max_half_life
    WINDOW = optimal_window
    ZSCORE_THRESH = optimal_zscore_thresh
    
    print(f"Optimal MAX_HALF_LIFE: {max_half_life}")
    print(f"Optimal WINDOW: {optimal_window}")
    print(f"Optimal ZSCORE_THRESH: {optimal_zscore_thresh}")
