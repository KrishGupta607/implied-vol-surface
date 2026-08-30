"""Black-Scholes pricing for European options, with a continuous dividend yield.

All pricing functions are vectorized: S, K, T, r, sigma and q may be scalars or
NumPy arrays / pandas Series, so a whole option chain can be priced in one call.
"""

import numpy as np
from scipy.stats import norm


def _d1_d2(S, K, T, r, sigma, q):
    """Shared intermediate terms for the call and put formulas."""
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2


def bs_call_price(S, K, T, r, sigma, q=0.0):
    """Black-Scholes price of a European call.

    S     : spot price of the underlying
    K     : strike price
    T     : time to expiry, in YEARS
    r     : risk-free rate, annualized decimal (0.04 = 4%)
    sigma : volatility, annualized decimal (0.089 = 8.9%)
    q     : continuous dividend yield, annualized decimal (0.0098 = 0.98%)
    """
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def bs_put_price(S, K, T, r, sigma, q=0.0):
    """Black-Scholes price of a European put. Arguments as above."""
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)


def implied_vol(price, S, K, T, r, option_type="C", q=0.0, lo=1e-3, hi=5.0, tol=1e-6):
    """Solve for the sigma that makes the Black-Scholes price equal `price`.

    Uses bisection, which is safe because price is strictly increasing in sigma.
    Returns NaN if no sigma in [lo, hi] can produce `price`.

    price       : observed market price of the option (use the bid/ask mid)
    option_type : "C" for a call, "P" for a put
    lo, hi      : bracket to search, as annualized decimals
    tol         : stop when the bracket is narrower than this
    """
    pricer = bs_call_price if option_type == "C" else bs_put_price

    if not (pricer(S, K, T, r, lo, q) <= price <= pricer(S, K, T, r, hi, q)):
        return np.nan

    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if pricer(S, K, T, r, mid, q) > price:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


if __name__ == "__main__":
    print(bs_call_price(769.35, 770, 5 / 365, 0.04, 0.089))  # expect ~3.0848
