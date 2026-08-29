import yfinance as yf
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)

tk = yf.Ticker("SPY")
expiries = tk.options
print("number of expiries:", len(expiries))
print(expiries)

expiry = expiries[3]
print("\n looking at:", expiry)
spot = tk.history(period="1d")["Close"].iloc[-1]
print(spot)
chain = tk.option_chain(expiry)
print(chain.calls.head(10))
calls = chain.calls.copy()
calls["mid"]        = (calls.bid + calls.ask) / 2
calls["intrinsic"]  = (spot - calls.strike).clip(lower=0)
calls["time_value"] = calls["mid"] - calls["intrinsic"]

near = calls[(calls.strike > spot - 15) & (calls.strike < spot + 15)]
print(near[["strike", "bid", "ask", "mid", "intrinsic", "time_value", "volume", "impliedVolatility"]])