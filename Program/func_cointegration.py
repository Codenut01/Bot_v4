import pandas as pd
import numpy as np
import logging
import statsmodels.api as sm
from statsmodels.tsa.vector_autoregression import VAR
from constants import MAX_HALF_LIFE, WINDOW

def calculate_half_life(spread):
    df_spread = pd.DataFrame(spread, columns=["spread"])
    spread_lag = df_spread.shift(1)
    spread_lag.iloc[0] = spread_lag.iloc[1]
    spread_ret = pd.DataFrame(df_spread.spread - spread_lag.iloc[:, 0])
    spread_ret.iloc[0] = spread_ret.iloc[1]
    spread_lag2 = sm.add_constant(spread_lag)
    model = sm.OLS(spread_ret, spread_lag2)
    res = model.fit()
    half_life = int(round(-np.log(2) / res.params[1], 0))
    return half_life

def calculate_zscore(spread):
    spread_series = pd.Series(spread)
    mean = spread_series.rolling(window=WINDOW).mean()
    std = spread_series.rolling(window=WINDOW).std()
    x = spread_series.rolling(window=1).mean()
    zscore = (x - mean) / std
    return zscore

def calculate_cointegration(series_1, series_2):
    # Use Johansen's method for cointegration analysis
    model = VAR(np.column_stack((series_1, series_2)))
    result = model.fit(maxlags=1, ic='aic')
    trace_stat, p_value, crit_values = result.test_ranking(det_order=0)
    coint_flag = 1 if p_value < 0.05 else 0

    # Calculate hedge ratio and half-life
    hedge_ratio = -result.coefs[0][1] / result.coefs[0][0]
    spread = series_1 - (hedge_ratio * series_2)
    half_life = calculate_half_life(spread)

    return coint_flag, hedge_ratio, half_life

def store_cointegration_results(df_market_prices):
    markets = df_market_prices.columns.tolist()
    criteria_met_paris = []

    logging.info("Finding Cointegrated Pairs...")
    for index, base_market in enumerate(markets[:-1]):
        series_1 = df_market_prices[base_market].values.astype(float).tolist()
        for quote_market in markets[index +1:]:
            series_2 = df_market_prices[quote_market].values.astype(float).tolist()
            coint_flag, hedge_ratio, half_life = calculate_cointegration(series_1, series_2)
            if coint_flag == 1 and half_life <= MAX_HALF_LIFE and half_life > 0:
                criteria_met_paris.append({
                    "base_market": base_market,
                    "quote_market": quote_market,
                    "hedge_ratio": hedge_ratio,
                    "half_life": half_life
                })

    logging.info("Saving Cointegrated Pairs...")
    df_criteria_met = pd.DataFrame(criteria_met_paris)
    df_criteria_met.to_csv("cointegrated_pairs.csv")
    del df_criteria_met
    logging.info("Cointegrated Pairs Successfully Saved")
    return "saved"
