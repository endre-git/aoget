import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Simulating historical price data
np.random.seed(42)
price_data = np.cumsum(np.random.randn(100)) + 100

# Creating a pandas DataFrame
df = pd.DataFrame({"Price": price_data})

# Define mean and standard deviation for mean reversion
mean = df["Price"].mean()
std_dev = df["Price"].std()

# Set threshold for buying and selling signals (e.g., one standard deviation)
buy_threshold = mean - std_dev
sell_threshold = mean + std_dev

# Create signals
df["Buy_Signal"] = np.where(df["Price"] < buy_threshold, 1, 0)
df["Sell_Signal"] = np.where(df["Price"] > sell_threshold, -1, 0)

# Calculate positions based on signals
df["Position"] = df["Buy_Signal"] + df["Sell_Signal"]

# Simulate trading by applying positions to returns
df["Daily_Return"] = df["Price"].pct_change()
df["Strategy_Return"] = df["Position"].shift(1) * df["Daily_Return"]

# Calculate cumulative returns
df["Cumulative_Strategy_Return"] = (1 + df["Strategy_Return"]).cumprod()

# Plotting results
plt.figure(figsize=(12, 6))
plt.plot(df["Cumulative_Strategy_Return"], label="Mean Reversion Strategy")
plt.plot((1 + df["Daily_Return"]).cumprod(), label="Buy and Hold")
plt.legend()
plt.title("Mean Reversion Trading Strategy vs Buy and Hold")
plt.show()
