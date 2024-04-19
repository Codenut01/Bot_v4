'''
Define functions will be used to calculate backtest cointegration
'''

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint, adfuller as adf

def calculate_half_life(spread):
    '''
        Calculate the half life of the spread using OLS
        Return the half life
    '''
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

def calculate_zscore(spread, window):
    spread_series = pd.Series(spread)
    mean = spread_series.rolling(window=window).mean()
    std = spread_series.rolling(window=window).std()
    x = spread_series.rolling(window=1).mean()
    zscore = (x - mean) / std
    return zscore

def calculate_cointegration(series_1, series_2):
    '''
        Calculate the cointegration of two series
        Return the cointegration flag, hedge ratio, half life, and optimal window
    '''
    series_1 = np.array(series_1).astype(np.float)
    series_2 = np.array(series_2).astype(np.float)
    coint_flag = 0

    # Determine the optimal window size using the ADF test
    spread = series_1 - series_2
    adf_result = adf(spread)
    optimal_lag = int(adf_result[2])
    optimal_window = optimal_lag + 1

    # The default coint method here from statsmodel is
    # the Augmented Engle Granger Model
    coint_res = coint(series_1, series_2, maxlag=optimal_lag, autolag=None)

    # The t-statistic of unit-root test on residuals.
    coint_t = coint_res[0]

    # MacKinnon's approximate, asymptotic p-value based on MacKinnon (1994).
    # If p_value is less than 0.05, it is cointegrated
    p_value = coint_res[1]

    # Critical values for the test statistic at the 1 %, 5 %, and 10 % levels
    # based on regression curve. This depends on the number of observations.
    critical_value = coint_res[2][1]
    model = sm.OLS(series_1, series_2).fit()
    hedge_ratio = model.params[0]
    spread = series_1 - (hedge_ratio * series_2)
    half_life = calculate_half_life(spread)

    # Check on channle for extensive conversation on t_check
    # the t_value should be less than the critical value
    t_check = coint_t < critical_value
    coint_flag = 1 if p_value < 0.05 and t_check else 0
    return coint_flag, hedge_ratio, half_life, optimal_window
