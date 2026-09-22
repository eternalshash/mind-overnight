import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def fetch_garmin_data():
    grmn = yf.Ticker("GRMN")
    df = grmn.history(period="1y").dropna()
    return df

def simulate_oura_stock(days=252, simulations=1000, initial_price=100):
    mu = 0.20
    sigma = 0.45
    dt = 1 / 252
    np.random.seed(42)
    paths = np.zeros((days, simulations))
    paths[0] = initial_price
    for t in range(1, days):
        z = np.random.standard_normal(simulations)
        paths[t] = paths[t-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z)
    return paths

def backtest_comparison():
    grmn_df = fetch_garmin_data()
    grmn_df['Daily_Return'] = grmn_df['Close'].pct_change()
    grmn_cum_return = (grmn_df['Close'] / grmn_df['Close'].iloc[0]) * 100
    
    trading_days = len(grmn_df)
    oura_paths = simulate_oura_stock(days=trading_days, simulations=1000, initial_price=100)
    
    oura_mean_path = np.mean(oura_paths, axis=1)
    oura_p5 = np.percentile(oura_paths, 5, axis=1)
    oura_p95 = np.percentile(oura_paths, 95, axis=1)
    
    plt.figure(figsize=(12, 7))
    plt.plot(grmn_df.index, grmn_cum_return, label='Garmin (GRMN) Actual', color='green', linewidth=2)
    plt.plot(grmn_df.index, oura_mean_path, label='Oura (Expected Mean)', color='blue', linewidth=2, linestyle='--')
    plt.fill_between(grmn_df.index, oura_p5, oura_p95, color='blue', alpha=0.2, label='Oura 90% Confidence Interval')
    
    plt.title('Oura Predicted Post-IPO Performance vs Garmin (1-Year Backtest)')
    plt.ylabel('Normalized Value (Base = 100)')
    plt.xlabel('Date')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    os.makedirs('analysis.prac/Oura/charts', exist_ok=True)
    chart_path = 'analysis.prac/Oura/charts/oura_vs_garmin_backtest.png'
    plt.savefig(chart_path)
    
    grmn_final_return = (grmn_cum_return.iloc[-1] - 100)
    oura_expected_return = (oura_mean_path[-1] - 100)
    grmn_vol = grmn_df['Daily_Return'].std() * np.sqrt(252) * 100
    
    print("\n=== BACKTEST METRICS ===")
    print(f"Garmin (GRMN) 1-Year Actual Return: {grmn_final_return:.2f}%")
    print(f"Garmin (GRMN) Annualized Volatility: {grmn_vol:.2f}%")
    print("---------------------------------")
    print(f"Oura Simulated Expected Return: {oura_expected_return:.2f}%")
    print(f"Oura Simulated 5th Percentile (Bear): {oura_p5[-1] - 100:.2f}%")
    print(f"Oura Simulated 95th Percentile (Bull): {oura_p95[-1] - 100:.2f}%")
    print(f"\nChart saved to {chart_path}")

if __name__ == '__main__':
    backtest_comparison()
