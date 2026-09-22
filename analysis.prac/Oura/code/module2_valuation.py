import numpy as np
import matplotlib.pyplot as plt
import os

def monte_carlo_dcf(simulations=10000):
    np.random.seed(42)
    units_growth = np.random.uniform(1.5, 4.0, simulations)
    monthly_churn = np.random.uniform(0.015, 0.05, simulations)
    
    valuations = units_growth * 1000 * (1 - monthly_churn) * 15 # mock formula
    return valuations

def plot_valuation(valuations):
    plt.figure(figsize=(10,6))
    plt.hist(valuations, bins=50, color='blue', alpha=0.7)
    plt.title('Monte Carlo DCF Valuation Distribution')
    plt.xlabel('Implied Enterprise Value ($B)')
    plt.ylabel('Frequency')
    
    os.makedirs('../charts', exist_ok=True)
    plt.savefig('../charts/valuation_distribution.png')
    
def public_comps():
    comps = {
        'GRMN': {'EV/Sales': 5.2, 'Gross Margin': 0.58},
        'AAPL': {'EV/Sales': 7.1, 'Gross Margin': 0.43},
        'DXCM': {'EV/Sales': 12.4, 'Gross Margin': 0.65}
    }
    return comps

if __name__ == '__main__':
    vals = monte_carlo_dcf()
    plot_valuation(vals)

